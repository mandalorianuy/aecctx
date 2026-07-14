from __future__ import annotations

import base64
import hashlib
import hmac
import http.client
import json
import socket
import ssl
import tempfile
import time
from dataclasses import asdict, dataclass
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

from .models import ProviderExecutionError, ProviderLimits, ProviderRegistration
from .protocol import ProviderResult, canonical_json_bytes, validate_provider_response


REMOTE_ROUTE = "/aecctx/provider/v1/extract"
RETRYABLE_CODES = frozenset({"AECCTX_REMOTE_TIMEOUT", "AECCTX_REMOTE_TRANSPORT_FAILED", "AECCTX_REMOTE_RATE_LIMITED"})
Exchange = Callable[[bytes, bytes, ProviderRegistration, "RemoteProviderPolicy"], bytes]


@dataclass(frozen=True, slots=True)
class RemoteProviderPolicy:
    endpoint_origin: str
    endpoint_spki_sha256: str
    upload_consent: bool
    billing_consent: bool
    allowed_regions: tuple[str, ...]
    expected_region: str
    retention_max_seconds: int
    telemetry_consent: bool
    timeout_seconds: float
    max_attempts: int
    retry_delay_seconds: float
    max_request_bytes: int
    max_response_bytes: int

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "RemoteProviderPolicy":
        value = dict(raw)
        schema = json.loads(files("aecctx.schemas.v0_2").joinpath("remote-provider-policy.schema.json").read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.absolute_path))
        if errors:
            first = errors[0]
            location = "/".join(str(part) for part in first.absolute_path) or "<root>"
            raise ProviderExecutionError("AECCTX_REMOTE_POLICY_INVALID", f"Remote provider policy invalid at {location}: {first.message}")
        origin = normalize_remote_origin(value["endpoint_origin"])
        regions = tuple(value["allowed_regions"])
        return cls(
            endpoint_origin=origin,
            endpoint_spki_sha256=value["endpoint_spki_sha256"],
            upload_consent=value["upload_consent"],
            billing_consent=value["billing_consent"],
            allowed_regions=regions,
            expected_region=value["expected_region"],
            retention_max_seconds=value["retention_max_seconds"],
            telemetry_consent=value["telemetry_consent"],
            timeout_seconds=float(value["timeout_seconds"]),
            max_attempts=value["max_attempts"],
            retry_delay_seconds=float(value["retry_delay_seconds"]),
            max_request_bytes=value["max_request_bytes"],
            max_response_bytes=value["max_response_bytes"],
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["allowed_regions"] = list(self.allowed_regions)
        return value


def normalize_remote_origin(value: str) -> str:
    if not isinstance(value, str) or not value or not value.isascii():
        raise ProviderExecutionError("AECCTX_REMOTE_ENDPOINT_INVALID", "Remote endpoint origin must be non-empty ASCII HTTPS")
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise ProviderExecutionError("AECCTX_REMOTE_ENDPOINT_INVALID", "Remote endpoint port is invalid") from error
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ProviderExecutionError("AECCTX_REMOTE_ENDPOINT_INVALID", "Remote endpoint must be an HTTPS origin without credentials, path, query or fragment")
    host = parsed.hostname.lower()
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"https://{host}" + (f":{port}" if port is not None and port != 443 else "")


def _preflight(registration: ProviderRegistration, policy: RemoteProviderPolicy, credential: bytes) -> None:
    if not policy.upload_consent:
        raise ProviderExecutionError("AECCTX_REMOTE_UPLOAD_CONSENT_REQUIRED", "Remote upload requires explicit caller consent")
    if not policy.billing_consent:
        raise ProviderExecutionError("AECCTX_REMOTE_BILLING_CONSENT_REQUIRED", "Remote billing requires explicit caller consent")
    registered_origin = normalize_remote_origin(registration.remote_origin or "")
    if policy.endpoint_origin != registered_origin or policy.endpoint_spki_sha256 != registration.remote_spki_sha256:
        raise ProviderExecutionError("AECCTX_REMOTE_ENDPOINT_MISMATCH", "Remote policy endpoint identity does not match registration")
    if policy.expected_region not in policy.allowed_regions:
        raise ProviderExecutionError("AECCTX_REMOTE_REGION_DENIED", "Expected remote region is not allowlisted")
    if registration.descriptor.network_mode != "allowlisted" or registration.descriptor.enforcement_profile != "remote-https-spki-v1":
        raise ProviderExecutionError("AECCTX_REMOTE_REGISTRATION_INVALID", "Remote registration descriptor is not bound to remote-https-spki-v1")
    if not isinstance(credential, bytes) or not credential or any(byte < 0x20 or byte > 0x7E for byte in credential):
        raise ProviderExecutionError("AECCTX_REMOTE_CREDENTIAL_INVALID", "Remote credential must be non-empty printable ASCII")


def build_remote_request_envelope(
    request: Mapping[str, Any], policy: RemoteProviderPolicy, input_bytes: bytes
) -> bytes:
    expected = request.get("input")
    if not isinstance(expected, Mapping) or expected.get("bytes") != len(input_bytes) or expected.get("sha256") != hashlib.sha256(input_bytes).hexdigest():
        raise ProviderExecutionError("AECCTX_REMOTE_INPUT_MISMATCH", "Remote source bytes do not match provider request")
    policy_projection = policy.to_dict()
    envelope = {
        "input": {
            "bytes": len(input_bytes),
            "data": base64.b64encode(input_bytes).decode("ascii"),
            "encoding": "base64",
            "sha256": hashlib.sha256(input_bytes).hexdigest(),
        },
        "policy_digest": hashlib.sha256(canonical_json_bytes(policy_projection)).hexdigest(),
        "protocol_version": "0.3-remote",
        "request": dict(request),
    }
    body = canonical_json_bytes(envelope)
    if len(body) > policy.max_request_bytes:
        raise ProviderExecutionError("AECCTX_REMOTE_REQUEST_LIMIT_EXCEEDED", "Remote request exceeds policy byte limit")
    return body


def _strict_json(body: bytes, limit: int) -> dict[str, Any]:
    if len(body) > limit:
        raise ProviderExecutionError("AECCTX_REMOTE_RESPONSE_LIMIT_EXCEEDED", "Remote response exceeds policy byte limit")
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=pairs, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ProviderExecutionError("AECCTX_REMOTE_RESPONSE_INVALID", "Remote response is not strict JSON") from error
    if not isinstance(value, dict):
        raise ProviderExecutionError("AECCTX_REMOTE_RESPONSE_INVALID", "Remote response must be an object")
    return value


def _contains_secret(value: Any, secret: str) -> bool:
    if isinstance(value, str):
        return secret in value
    if isinstance(value, Mapping):
        return any(_contains_secret(key, secret) or _contains_secret(item, secret) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_secret(item, secret) for item in value)
    return False


def _decode_artifacts(raw: Any, response: Mapping[str, Any], root: Path, limits: ProviderLimits) -> None:
    if not isinstance(raw, Mapping) or len(raw) > limits.max_files:
        raise ProviderExecutionError("AECCTX_REMOTE_ARTIFACTS_INVALID", "Remote artifact map is invalid or exceeds file limit")
    declared = {entry.get("path"): entry for entry in response.get("artifacts", []) if isinstance(entry, Mapping)}
    if set(raw) != set(declared):
        raise ProviderExecutionError("AECCTX_REMOTE_ARTIFACTS_INVALID", "Remote artifact map does not match response declarations")
    total = 0
    for name, encoded in raw.items():
        if not isinstance(name, str) or not isinstance(encoded, str) or "\\" in name or "\x00" in name:
            raise ProviderExecutionError("AECCTX_REMOTE_ARTIFACTS_INVALID", "Remote artifact entry is invalid")
        path = PurePosixPath(name)
        if path.is_absolute() or not path.parts or path.parts[0] != "artifacts" or any(part in {"", ".", ".."} for part in path.parts):
            raise ProviderExecutionError("AECCTX_PROVIDER_ARTIFACT_PATH_UNSAFE", "Remote artifact path is unsafe")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as error:
            raise ProviderExecutionError("AECCTX_REMOTE_ARTIFACTS_INVALID", "Remote artifact is not canonical base64") from error
        if base64.b64encode(data).decode("ascii") != encoded:
            raise ProviderExecutionError("AECCTX_REMOTE_ARTIFACTS_INVALID", "Remote artifact base64 is not canonical")
        total += len(data)
        if total > limits.max_output_bytes:
            raise ProviderExecutionError("AECCTX_PROVIDER_OUTPUT_LIMIT_EXCEEDED", "Remote artifacts exceed provider output limit")
        destination = root.joinpath(*path.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)


def replay_remote_provider(
    registration: ProviderRegistration,
    request: Mapping[str, Any],
    policy: RemoteProviderPolicy,
    *,
    input_bytes: bytes,
    response_envelope: Mapping[str, Any],
    limits: ProviderLimits | None = None,
) -> ProviderResult:
    provider_limits = limits or ProviderLimits()
    request_body = build_remote_request_envelope(request, policy, input_bytes)
    request_digest = hashlib.sha256(request_body).hexdigest()
    envelope = dict(response_envelope)
    if envelope.get("protocol_version") != "0.3-remote":
        raise ProviderExecutionError("AECCTX_REMOTE_RESPONSE_INVALID", "Remote response protocol version is invalid")
    if envelope.get("request_digest") != request_digest:
        raise ProviderExecutionError("AECCTX_REMOTE_REQUEST_DIGEST_MISMATCH", "Remote response request digest mismatch")
    if envelope.get("provider_id") != registration.descriptor.provider_id or envelope.get("provider_version") != registration.descriptor.provider_version:
        raise ProviderExecutionError("AECCTX_REMOTE_RESPONSE_MISMATCH", "Remote response provider identity mismatch")
    if envelope.get("region") != policy.expected_region or envelope.get("region") not in policy.allowed_regions:
        raise ProviderExecutionError("AECCTX_REMOTE_REGION_DENIED", "Remote response region is not allowed")
    retention = envelope.get("retention_seconds")
    if not isinstance(retention, int) or isinstance(retention, bool) or retention < 0 or retention > policy.retention_max_seconds:
        raise ProviderExecutionError("AECCTX_REMOTE_RETENTION_DENIED", "Remote response retention exceeds policy")
    telemetry = envelope.get("telemetry")
    if not isinstance(telemetry, bool) or (telemetry and not policy.telemetry_consent):
        raise ProviderExecutionError("AECCTX_REMOTE_TELEMETRY_DENIED", "Remote response telemetry exceeds policy")
    response = envelope.get("response")
    if not isinstance(response, Mapping):
        raise ProviderExecutionError("AECCTX_REMOTE_RESPONSE_INVALID", "Remote response payload is missing")
    with tempfile.TemporaryDirectory(prefix="aecctx-remote-provider-") as temporary:
        output_root = Path(temporary)
        _decode_artifacts(envelope.get("artifacts"), response, output_root, provider_limits)
        return validate_provider_response(response, request, registration.descriptor, output_root, limits=provider_limits)


def _https_exchange(body: bytes, credential: bytes, registration: ProviderRegistration, policy: RemoteProviderPolicy) -> bytes:
    parsed = urlsplit(policy.endpoint_origin)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=policy.timeout_seconds, context=context)
    try:
        connection.connect()
        peer = connection.sock.getpeercert(binary_form=True) if connection.sock is not None else None
        if not peer:
            raise ProviderExecutionError("AECCTX_REMOTE_TLS_IDENTITY_FAILED", "Remote peer did not provide a certificate")
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import serialization
        except ImportError as error:
            raise ProviderExecutionError("AECCTX_REMOTE_DEPENDENCY_UNAVAILABLE", "Remote provider support requires the remote extra") from error
        certificate = x509.load_der_x509_certificate(peer)
        spki = certificate.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        if not hmac.compare_digest(hashlib.sha256(spki).hexdigest(), policy.endpoint_spki_sha256):
            raise ProviderExecutionError("AECCTX_REMOTE_TLS_IDENTITY_FAILED", "Remote peer SPKI does not match registration")
        connection.request(
            "POST",
            REMOTE_ROUTE,
            body=body,
            headers={
                "Authorization": credential.decode("ascii"),
                "Content-Type": "application/json",
                "X-AECCTX-Request-SHA256": hashlib.sha256(body).hexdigest(),
            },
        )
        response = connection.getresponse()
        payload = response.read(policy.max_response_bytes + 1)
        if 300 <= response.status < 400:
            raise ProviderExecutionError("AECCTX_REMOTE_REDIRECT_DENIED", "Remote redirects are forbidden")
        if response.status in {401, 403}:
            raise ProviderExecutionError("AECCTX_REMOTE_AUTH_FAILED", "Remote provider rejected authentication")
        if response.status in {429, 502, 503, 504}:
            raise ProviderExecutionError("AECCTX_REMOTE_RATE_LIMITED", "Remote provider is temporarily unavailable")
        if response.status != 200:
            raise ProviderExecutionError("AECCTX_REMOTE_HTTP_FAILED", f"Remote provider returned HTTP {response.status}")
        if len(payload) > policy.max_response_bytes:
            raise ProviderExecutionError("AECCTX_REMOTE_RESPONSE_LIMIT_EXCEEDED", "Remote response exceeds policy byte limit")
        received_digest = response.getheader("X-AECCTX-Response-SHA256")
        if received_digest != hashlib.sha256(payload).hexdigest():
            raise ProviderExecutionError("AECCTX_REMOTE_RESPONSE_DIGEST_MISMATCH", "Remote response body digest mismatch")
        return payload
    except (TimeoutError, socket.timeout) as error:
        raise ProviderExecutionError("AECCTX_REMOTE_TIMEOUT", "Remote provider timed out") from error
    except (OSError, http.client.HTTPException, ssl.SSLError) as error:
        raise ProviderExecutionError("AECCTX_REMOTE_TRANSPORT_FAILED", "Remote provider transport failed") from error
    finally:
        connection.close()


def run_remote_provider(
    registration: ProviderRegistration,
    request: Mapping[str, Any],
    policy: RemoteProviderPolicy,
    *,
    input_bytes: bytes,
    credential: bytes,
    limits: ProviderLimits | None = None,
    exchange: Exchange | None = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> ProviderResult:
    _preflight(registration, policy, credential)
    request_body = build_remote_request_envelope(request, policy, input_bytes)
    transport = exchange or _https_exchange
    last: ProviderExecutionError | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            response_body = transport(request_body, credential, registration, policy)
            envelope = _strict_json(response_body, policy.max_response_bytes)
            if _contains_secret(envelope, credential.decode("ascii")):
                raise ProviderExecutionError("AECCTX_REMOTE_SECRET_LEAK", "Remote response contains caller credential")
            return replay_remote_provider(registration, request, policy, input_bytes=input_bytes, response_envelope=envelope, limits=limits)
        except ProviderExecutionError as error:
            last = error
            if error.code not in RETRYABLE_CODES:
                raise
            if attempt < policy.max_attempts:
                sleeper(policy.retry_delay_seconds)
    raise ProviderExecutionError(
        "AECCTX_REMOTE_RETRY_EXHAUSTED",
        "Remote provider retry budget exhausted",
        details={"attempts": policy.max_attempts, "last_error": last.code if last else "AECCTX_REMOTE_TRANSPORT_FAILED"},
    )


class RemoteProviderProfile:
    profile_id = "remote-https-spki-v1"

    def __init__(self, policy: RemoteProviderPolicy, *, credential: bytes, exchange: Exchange | None = None) -> None:
        self.policy = policy
        self._credential = credential
        self._exchange = exchange

    def preflight(self, registration: ProviderRegistration) -> None:
        _preflight(registration, self.policy, self._credential)

    def run_remote(
        self,
        registration: ProviderRegistration,
        request: Mapping[str, Any],
        input_bytes: bytes,
        limits: ProviderLimits,
    ) -> ProviderResult:
        return run_remote_provider(
            registration,
            request,
            self.policy,
            input_bytes=input_bytes,
            credential=self._credential,
            limits=limits,
            exchange=self._exchange,
        )
