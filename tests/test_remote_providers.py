from __future__ import annotations

import base64
import hashlib
import json
import ssl
import threading
from datetime import UTC, datetime, timedelta
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import aecctx.providers as providers
from aecctx.context import render_context
from aecctx.diff import diff_packages
from aecctx.query import query_package
from aecctx.validation import validate_package


PIN = "a" * 64
ORIGIN = "https://127.0.0.1:8443"
CREDENTIAL = b"Bearer conformance-secret"


def policy_dict(*, origin: str = ORIGIN, pin: str = PIN, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "allowed_regions": ["test-region"],
        "billing_consent": True,
        "endpoint_origin": origin,
        "endpoint_spki_sha256": pin,
        "expected_region": "test-region",
        "max_attempts": 2,
        "max_request_bytes": 4096,
        "max_response_bytes": 16384,
        "retention_max_seconds": 0,
        "retry_delay_seconds": 0,
        "telemetry_consent": False,
        "timeout_seconds": 1.0,
        "upload_consent": True,
    }
    value.update(overrides)
    return value


def remote_registration(*, origin: str = ORIGIN, pin: str = PIN) -> providers.ProviderRegistration:
    base = providers.reference_provider_registry().resolve("org.aecctx.reference-provider")
    descriptor = replace(
        base.descriptor,
        enforcement_profile="remote-https-spki-v1",
        network_mode="allowlisted",
        platforms=("remote",),
    )
    return replace(base, descriptor=descriptor, remote_origin=origin, remote_spki_sha256=pin)


def valid_envelope(
    request: dict[str, object],
    descriptor: providers.ProviderDescriptor,
    request_envelope_digest: str,
) -> dict[str, object]:
    artifact_bytes = b"remote-output"
    response: dict[str, object] = {
        "artifacts": [{
            "bytes": len(artifact_bytes),
            "media_type": "application/octet-stream",
            "path": "artifacts/echo.bin",
            "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        }],
        "attestation": {
            "descriptor_digest": providers.provider_descriptor_digest(descriptor),
            "deterministic": True,
            "enforcement_profile": descriptor.enforcement_profile,
            "network_mode": "allowlisted",
            "provider_id": descriptor.provider_id,
            "provider_version": descriptor.provider_version,
            "request_digest": providers.canonical_sha256(request),
            "response_payload_digest": "0" * 64,
            "runtime_version": descriptor.runtime_version,
            "runtime_digest": descriptor.runtime_digest,
        },
        "capability_report": {
            "echo": {"affected": [], "fallback": "none", "reason_codes": [], "support_level": "full"}
        },
        "diagnostics": [],
        "events": [{"event_type": "artifact", "payload": {}, "sequence": 0, "source_locator": "input:fixture"}],
        "ok": True,
        "protocol_version": "0.2",
        "provider_id": descriptor.provider_id,
        "request_id": request["request_id"],
        "resource_usage": {"output_bytes": len(artifact_bytes)},
    }
    response["attestation"]["response_payload_digest"] = providers.provider_response_payload_digest(response)  # type: ignore[index]
    return {
        "artifacts": {"artifacts/echo.bin": base64.b64encode(artifact_bytes).decode("ascii")},
        "protocol_version": "0.3-remote",
        "provider_id": descriptor.provider_id,
        "provider_version": descriptor.provider_version,
        "region": "test-region",
        "request_digest": request_envelope_digest,
        "response": response,
        "retention_seconds": 0,
        "telemetry": False,
    }


def test_remote_policy_rejects_before_network() -> None:
    registration = remote_registration()
    for overrides, code in [
        ({"upload_consent": False}, "AECCTX_REMOTE_UPLOAD_CONSENT_REQUIRED"),
        ({"billing_consent": False}, "AECCTX_REMOTE_BILLING_CONSENT_REQUIRED"),
        ({"endpoint_origin": "https://example.invalid"}, "AECCTX_REMOTE_ENDPOINT_MISMATCH"),
        ({"expected_region": "other"}, "AECCTX_REMOTE_REGION_DENIED"),
    ]:
        policy = providers.RemoteProviderPolicy.from_dict(policy_dict(**overrides))
        called = False

        def exchange(*_: object, **__: object) -> bytes:
            nonlocal called
            called = True
            return b"{}"

        with pytest.raises(providers.ProviderExecutionError) as captured:
            providers.run_remote_provider(
                registration,
                providers.build_provider_request(registration.descriptor.provider_id, "extract", b"fixture"),
                policy,
                input_bytes=b"fixture",
                credential=CREDENTIAL,
                exchange=exchange,
            )
        assert captured.value.code == code
        assert called is False


def test_injected_transport_round_trip_is_content_addressed() -> None:
    registration = remote_registration()
    policy = providers.RemoteProviderPolicy.from_dict(policy_dict())
    request = providers.build_provider_request(registration.descriptor.provider_id, "extract", b"fixture")
    seen: list[tuple[bytes, bytes]] = []

    def exchange(body: bytes, credential: bytes, *_: object, **__: object) -> bytes:
        assert credential == CREDENTIAL
        envelope = json.loads(body)
        assert base64.b64decode(envelope["input"]["data"], validate=True) == b"fixture"
        digest = hashlib.sha256(body).hexdigest()
        seen.append((body, credential))
        return providers.canonical_json_bytes(valid_envelope(request, registration.descriptor, digest))

    first = providers.run_remote_provider(
        registration, request, policy, input_bytes=b"fixture", credential=CREDENTIAL, exchange=exchange
    )
    second = providers.run_remote_provider(
        registration, request, policy, input_bytes=b"fixture", credential=CREDENTIAL, exchange=exchange
    )

    assert first.artifact_bytes == second.artifact_bytes == {"artifacts/echo.bin": b"remote-output"}
    assert seen[0][0] == seen[1][0]
    assert CREDENTIAL not in seen[0][0]


def test_provider_runner_uses_explicit_remote_profile_without_local_workspace(tmp_path: Path) -> None:
    registration = remote_registration()
    policy = providers.RemoteProviderPolicy.from_dict(policy_dict())
    registry = providers.ProviderRegistry(allowed_worker_modules={registration.worker_module})
    registry.register(registration)

    def exchange(body: bytes, *_: object, **__: object) -> bytes:
        envelope = json.loads(body)
        return providers.canonical_json_bytes(
            valid_envelope(envelope["request"], registration.descriptor, hashlib.sha256(body).hexdigest())
        )

    runner = providers.ProviderRunner(
        registry=registry,
        profile=providers.RemoteProviderProfile(policy, credential=CREDENTIAL, exchange=exchange),
        workspace_parent=tmp_path,
    )
    result = runner.run(registration.descriptor.provider_id, "extract", b"fixture")
    assert result.ok is True
    assert list(tmp_path.iterdir()) == []


def test_loopback_tls_round_trip_is_content_addressed(tmp_path: Path) -> None:
    cryptography = pytest.importorskip("cryptography")
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AECCTX loopback")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(datetime.now(UTC) - timedelta(days=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1"))]), critical=False)
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "loopback-cert.pem"
    key_path = tmp_path / "loopback-key.pem"
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    spki = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    pin = hashlib.sha256(spki).hexdigest()

    descriptor_holder: dict[str, providers.ProviderDescriptor] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            assert self.path == "/aecctx/provider/v1/extract"
            assert self.headers["Authorization"] == CREDENTIAL.decode("ascii")
            length = int(self.headers["Content-Length"])
            body = self.rfile.read(length)
            assert self.headers["X-AECCTX-Request-SHA256"] == hashlib.sha256(body).hexdigest()
            request_envelope = json.loads(body)
            envelope = valid_envelope(request_envelope["request"], descriptor_holder["descriptor"], hashlib.sha256(body).hexdigest())
            payload = providers.canonical_json_bytes(envelope)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-AECCTX-Response-SHA256", hashlib.sha256(payload).hexdigest())
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_: object) -> None:
            return

    class QuietServer(ThreadingHTTPServer):
        daemon_threads = True
        def handle_error(self, *_: object) -> None:
            return

    server = QuietServer(("127.0.0.1", 0), Handler)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert_path, key_path)
    server.socket = tls.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"https://127.0.0.1:{server.server_port}"
    registration = remote_registration(origin=origin, pin=pin)
    descriptor_holder["descriptor"] = registration.descriptor
    policy = providers.RemoteProviderPolicy.from_dict(policy_dict(origin=origin, pin=pin))
    request = providers.build_provider_request(registration.descriptor.provider_id, "extract", b"fixture")
    try:
        result = providers.run_remote_provider(
            registration, request, policy, input_bytes=b"fixture", credential=CREDENTIAL
        )
        bad_registration = remote_registration(origin=origin, pin="f" * 64)
        bad_policy = providers.RemoteProviderPolicy.from_dict(policy_dict(origin=origin, pin="f" * 64, max_attempts=1))
        with pytest.raises(providers.ProviderExecutionError) as captured:
            providers.run_remote_provider(
                bad_registration, request, bad_policy, input_bytes=b"fixture", credential=CREDENTIAL
            )
        assert captured.value.code == "AECCTX_REMOTE_TLS_IDENTITY_FAILED"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert result.artifact_bytes == {"artifacts/echo.bin": b"remote-output"}
    assert cryptography is not None


def test_retry_and_terminal_error_semantics() -> None:
    registration = remote_registration()
    policy = providers.RemoteProviderPolicy.from_dict(policy_dict(max_attempts=2))
    request = providers.build_provider_request(registration.descriptor.provider_id, "extract", b"fixture")
    attempts = 0

    def timeout(*_: object, **__: object) -> bytes:
        nonlocal attempts
        attempts += 1
        raise providers.ProviderExecutionError("AECCTX_REMOTE_TIMEOUT", "timed out")

    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.run_remote_provider(
            registration, request, policy, input_bytes=b"fixture", credential=CREDENTIAL, exchange=timeout
        )
    assert captured.value.code == "AECCTX_REMOTE_RETRY_EXHAUSTED"
    assert captured.value.details == {"attempts": 2, "last_error": "AECCTX_REMOTE_TIMEOUT"}
    assert attempts == 2

    for code in ("AECCTX_REMOTE_AUTH_FAILED", "AECCTX_REMOTE_REDIRECT_DENIED"):
        attempts = 0
        def terminal(*_: object, code: str = code, **__: object) -> bytes:
            nonlocal attempts
            attempts += 1
            raise providers.ProviderExecutionError(code, "terminal")
        with pytest.raises(providers.ProviderExecutionError) as captured:
            providers.run_remote_provider(
                registration, request, policy, input_bytes=b"fixture", credential=CREDENTIAL, exchange=terminal
            )
        assert captured.value.code == code
        assert attempts == 1


def test_remote_transport_adversarial_matrix() -> None:
    registration = remote_registration()
    request = providers.build_provider_request(registration.descriptor.provider_id, "extract", b"fixture")
    policy = providers.RemoteProviderPolicy.from_dict(policy_dict(max_response_bytes=1024))

    cases = [
        (b"not-json", "AECCTX_REMOTE_RESPONSE_INVALID"),
        (b"{" + b"x" * 2048 + b"}", "AECCTX_REMOTE_RESPONSE_LIMIT_EXCEEDED"),
    ]
    for body, code in cases:
        with pytest.raises(providers.ProviderExecutionError) as captured:
            providers.run_remote_provider(
                registration,
                request,
                policy,
                input_bytes=b"fixture",
                credential=CREDENTIAL,
                exchange=lambda *_args, body=body, **_kwargs: body,
            )
        assert captured.value.code == code
        assert "conformance-secret" not in str(captured.value)
        assert "conformance-secret" not in json.dumps(captured.value.details)

    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.run_remote_provider(
            registration,
            request,
            policy,
            input_bytes=b"fixture",
            credential=b"Bearer bad\r\nInjected: yes",
            exchange=lambda *_args, **_kwargs: b"{}",
        )
    assert captured.value.code == "AECCTX_REMOTE_CREDENTIAL_INVALID"

    redaction_policy = providers.RemoteProviderPolicy.from_dict(policy_dict(max_response_bytes=16384))
    request_body = providers.build_remote_request_envelope(request, redaction_policy, b"fixture")
    leaked = valid_envelope(request, registration.descriptor, hashlib.sha256(request_body).hexdigest())
    leaked["response"]["diagnostics"] = [{"message": CREDENTIAL.decode("ascii")}]  # type: ignore[index]
    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.run_remote_provider(
            registration,
            request,
            redaction_policy,
            input_bytes=b"fixture",
            credential=CREDENTIAL,
            exchange=lambda *_args, **_kwargs: providers.canonical_json_bytes(leaked),
        )
    assert captured.value.code == "AECCTX_REMOTE_SECRET_LEAK"


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"region": "other"}, "AECCTX_REMOTE_REGION_DENIED"),
        ({"retention_seconds": 1}, "AECCTX_REMOTE_RETENTION_DENIED"),
        ({"telemetry": True}, "AECCTX_REMOTE_TELEMETRY_DENIED"),
    ],
)
def test_response_policy_attestation_fails_closed(changes: dict[str, object], code: str) -> None:
    registration = remote_registration()
    policy = providers.RemoteProviderPolicy.from_dict(policy_dict())
    request = providers.build_provider_request(registration.descriptor.provider_id, "extract", b"fixture")
    request_body = providers.build_remote_request_envelope(request, policy, b"fixture")
    envelope = valid_envelope(request, registration.descriptor, hashlib.sha256(request_body).hexdigest())
    envelope.update(changes)
    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.replay_remote_provider(
            registration, request, policy, input_bytes=b"fixture", response_envelope=envelope
        )
    assert captured.value.code == code


def test_remote_replay_is_deterministic_and_drift_bound(tmp_path: Path) -> None:
    registration = remote_registration()
    policy = providers.RemoteProviderPolicy.from_dict(policy_dict())
    request = providers.build_provider_request(registration.descriptor.provider_id, "extract", b"fixture")
    request_body = providers.build_remote_request_envelope(request, policy, b"fixture")
    envelope = valid_envelope(request, registration.descriptor, hashlib.sha256(request_body).hexdigest())

    first = providers.replay_remote_provider(registration, request, policy, input_bytes=b"fixture", response_envelope=envelope)
    second = providers.replay_remote_provider(registration, request, policy, input_bytes=b"fixture", response_envelope=envelope)
    assert first.artifact_bytes == second.artifact_bytes

    drifted = dict(envelope, request_digest="f" * 64)
    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.replay_remote_provider(registration, request, policy, input_bytes=b"fixture", response_envelope=drifted)
    assert captured.value.code == "AECCTX_REMOTE_REQUEST_DIGEST_MISMATCH"


def test_committed_remote_replay_is_valid() -> None:
    root = Path(__file__).parents[1] / "fixtures/v0.3/remote-providers"
    descriptor = providers.ProviderDescriptor.from_dict(json.loads((root / "descriptor.json").read_text()))
    policy = providers.RemoteProviderPolicy.from_dict(json.loads((root / "policy.json").read_text()))
    request_envelope = json.loads((root / "request-envelope.json").read_text())
    registration = providers.ProviderRegistration(
        descriptor=descriptor,
        worker_module="reference-remote",
        remote_origin=policy.endpoint_origin,
        remote_spki_sha256=policy.endpoint_spki_sha256,
    )
    result = providers.replay_remote_provider(
        registration,
        request_envelope["request"],
        policy,
        input_bytes=(root / "source.bin").read_bytes(),
        response_envelope=json.loads((root / "response-envelope.json").read_text()),
        limits=providers.ProviderLimits(max_output_bytes=4096, max_records=10, max_files=4),
    )
    assert result.ok is True
    assert result.capability_report["semantics"]["support_level"] == "unsupported"


def test_core_operations_remain_network_free(monkeypatch: pytest.MonkeyPatch) -> None:
    package = Path(__file__).parents[1] / "fixtures/minimal-aecctx"
    calls: list[object] = []
    def forbidden(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))
        raise AssertionError("core attempted network access")
    monkeypatch.setattr("socket.create_connection", forbidden)
    assert validate_package(package).valid is True
    query_package(package, 'record.record_id != "missing"')
    diff_packages(package, package)
    render_context(package, token_budget=4000, chunk_token_budget=1000)
    assert calls == []


def test_remote_conformance_checker_passes() -> None:
    import subprocess
    import sys
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).parents[1] / "scripts/check_remote_provider_conformance.py")],
        cwd=Path(__file__).parents[1], capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["attack_cases"] == 16
