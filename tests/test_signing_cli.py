from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "fixtures" / "minimal-aecctx"


def run_cli(*args: str, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    active_environment = os.environ.copy()
    active_environment["PYTHONPATH"] = str(ROOT / "src")
    if environment:
        active_environment.update(environment)
    return subprocess.run(
        [sys.executable, "-m", "aecctx", *args],
        cwd=ROOT,
        env=active_environment,
        text=True,
        capture_output=True,
        check=False,
    )


def private_pem(seed: bytes) -> bytes:
    return Ed25519PrivateKey.from_private_bytes(seed).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def write_controls(tmp_path: Path, *signers: tuple[str, bytes], threshold: int = 1) -> tuple[Path, Path]:
    signing_io = import_module("aecctx._signing_io")
    keys = []
    kids = []
    for kid, seed in signers:
        kids.append(kid)
        public = Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes_raw()
        keys.append(
            {
                "kid": kid,
                "public_key": {"kty": "OKP", "crv": "Ed25519", "x": signing_io.base64url_encode(public)},
                "subject": "urn:aecctx:test:cli",
                "valid_from": "2026-01-01T00:00:00Z",
                "valid_until": "2027-01-01T00:00:00Z",
                "revocation_status": "good",
                "scopes": ["aecctx.package.sign"],
            }
        )
    registry = tmp_path / "registry.json"
    registry.write_bytes(signing_io.canonical_json_nfc({"registry_version": "1", "keys": keys}, terminal_lf=True))
    policy = tmp_path / "policy.json"
    policy.write_bytes(
        signing_io.canonical_json_nfc(
            {
                "policy_version": "1",
                "verification_time": "2026-07-12T00:00:00Z",
                "allowed_algorithms": ["Ed25519"],
                "trusted_kids": sorted(kids),
                "trusted_subjects": [],
                "required_scopes": ["aecctx.package.sign"],
                "minimum_authorized_signatures": threshold,
            },
            terminal_lf=True,
        )
    )
    return registry, policy


def test_signing_help_exposes_only_governed_options() -> None:
    sign = run_cli("sign", "--help")
    verify = run_cli("verify-signatures", "--help")

    assert sign.returncode == 0
    assert "--private-key" in sign.stdout
    assert "--kid" in sign.stdout
    assert "--output" in sign.stdout
    assert "--password-file" in sign.stdout
    assert "--append-to" in sign.stdout
    assert "--password " not in sign.stdout
    assert verify.returncode == 0
    assert "--signature-bundle" in verify.stdout
    assert "--key-registry" in verify.stdout
    assert "--trust-policy" in verify.stdout


def test_signing_parser_requires_explicit_inputs() -> None:
    sign = run_cli("sign", str(PACKAGE))
    verify = run_cli("verify-signatures", str(PACKAGE))

    assert sign.returncode == 2
    assert "--private-key" in sign.stderr
    assert "--kid" in sign.stderr
    assert "--output" in sign.stderr
    assert verify.returncode == 2
    assert "--key-registry" in verify.stderr


def test_sign_cli_matches_sdk_bytes_and_creates_mode_0600_output(tmp_path: Path) -> None:
    key = tmp_path / "test-a.pem"
    key.write_bytes(private_pem(b"A" * 32))
    output = tmp_path / "bundle.json"

    completed = run_cli(
        "sign",
        str(PACKAGE),
        "--private-key",
        str(key),
        "--kid",
        "test-a",
        "--output",
        str(output),
        "--json",
    )
    expected = import_module("aecctx.signing").sign_package(
        PACKAGE,
        private_key_pem=key.read_bytes(),
        kid="test-a",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout) == {
        "data": {"kids": ["test-a"], "signature_count": 1},
        "diagnostics": [],
        "ok": True,
    }
    assert output.read_bytes() == expected.to_bytes()
    if os.name != "nt":
        assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_sign_cli_append_preserves_existing_sidecar_and_sorts_output(tmp_path: Path) -> None:
    key_z = tmp_path / "test-z.pem"
    key_z.write_bytes(private_pem(b"Z" * 32))
    first = tmp_path / "first.json"
    created = run_cli(
        "sign",
        str(PACKAGE),
        "--private-key",
        str(key_z),
        "--kid",
        "test-z",
        "--output",
        str(first),
    )
    assert created.returncode == 0, created.stderr
    before = first.read_bytes()
    key_a = tmp_path / "test-a.pem"
    key_a.write_bytes(private_pem(b"A" * 32))
    appended = tmp_path / "appended.json"

    completed = run_cli(
        "sign",
        str(PACKAGE),
        "--private-key",
        str(key_a),
        "--kid",
        "test-a",
        "--append-to",
        str(first),
        "--output",
        str(appended),
        "--json",
    )
    parsed = import_module("aecctx.signing").parse_signature_bundle(appended.read_bytes())

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert first.read_bytes() == before
    assert [entry.kid for entry in parsed.signatures] == ["test-a", "test-z"]


def test_verify_cli_exit_zero_only_for_satisfied_policy(tmp_path: Path) -> None:
    key = tmp_path / "test-a.pem"
    key.write_bytes(private_pem(b"A" * 32))
    bundle = tmp_path / "bundle.json"
    signed = run_cli(
        "sign",
        str(PACKAGE),
        "--private-key",
        str(key),
        "--kid",
        "test-a",
        "--output",
        str(bundle),
    )
    assert signed.returncode == 0, signed.stderr
    registry, policy = write_controls(tmp_path, ("test-a", b"A" * 32))

    completed = run_cli(
        "verify-signatures",
        str(PACKAGE),
        "--signature-bundle",
        str(bundle),
        "--key-registry",
        str(registry),
        "--trust-policy",
        str(policy),
        "--json",
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert payload["ok"] is True
    assert payload["data"]["policy_evaluation"]["policy_satisfied"] is True
    assert payload["data"]["signatures"][0]["cryptographic_status"] == "valid"


def test_sign_cli_rejects_existing_or_same_append_output_without_mutation(tmp_path: Path) -> None:
    key = tmp_path / "test-a.pem"
    key.write_bytes(private_pem(b"A" * 32))
    output = tmp_path / "bundle.json"
    output.write_bytes(b"do-not-overwrite")

    existing = run_cli(
        "sign",
        str(PACKAGE),
        "--private-key",
        str(key),
        "--kid",
        "test-a",
        "--output",
        str(output),
        "--json",
    )
    same = run_cli(
        "sign",
        str(PACKAGE),
        "--private-key",
        str(key),
        "--kid",
        "test-a",
        "--append-to",
        str(output),
        "--output",
        str(output),
        "--json",
    )

    assert existing.returncode == 2
    assert json.loads(existing.stdout)["diagnostics"][0]["code"] == "AECCTX_SIGNING_OUTPUT_EXISTS"
    assert same.returncode == 2
    assert json.loads(same.stdout)["diagnostics"][0]["code"] == "AECCTX_SIGNING_OUTPUT_CONFLICT"
    assert output.read_bytes() == b"do-not-overwrite"


def test_sign_cli_uses_only_explicit_password_file_and_strips_one_lf(tmp_path: Path) -> None:
    password = b"explicit-test-password"
    encrypted = Ed25519PrivateKey.from_private_bytes(b"A" * 32).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(password),
    )
    key = tmp_path / "encrypted.pem"
    key.write_bytes(encrypted)
    password_file = tmp_path / "password.txt"
    password_file.write_bytes(password + b"\n")
    output = tmp_path / "bundle.json"

    explicit = run_cli(
        "sign",
        str(PACKAGE),
        "--private-key",
        str(key),
        "--password-file",
        str(password_file),
        "--kid",
        "test-a",
        "--output",
        str(output),
    )
    implicit = run_cli(
        "sign",
        str(PACKAGE),
        "--private-key",
        str(key),
        "--kid",
        "test-a",
        "--output",
        str(tmp_path / "implicit.json"),
        "--json",
        environment={"AECCTX_PASSWORD": password.decode("ascii")},
    )

    assert explicit.returncode == 0, explicit.stderr
    assert implicit.returncode == 2
    assert not (tmp_path / "implicit.json").exists()


def test_signing_failures_do_not_expose_secrets_or_absolute_input_paths(tmp_path: Path) -> None:
    secret = "do-not-print-this-secret"
    key = tmp_path / "secret-key.pem"
    key.write_bytes(b"not-a-private-key:" + secret.encode("ascii"))
    password = tmp_path / "secret-password.txt"
    password.write_text(secret + "\n", encoding="utf-8")

    completed = run_cli(
        "sign",
        str(PACKAGE),
        "--private-key",
        str(key),
        "--password-file",
        str(password),
        "--kid",
        "test-a",
        "--output",
        str(tmp_path / "failed.json"),
        "--json",
    )
    captured = completed.stdout + completed.stderr

    assert completed.returncode == 2
    assert secret not in captured
    assert str(PACKAGE) not in captured
    assert str(key) not in captured
    assert str(password) not in captured


def test_verify_cli_exit_one_for_unsigned_no_policy_and_unsatisfied(tmp_path: Path) -> None:
    registry, policy = write_controls(tmp_path, ("test-a", b"A" * 32), threshold=2)
    unsigned = run_cli(
        "verify-signatures",
        str(PACKAGE),
        "--key-registry",
        str(registry),
        "--trust-policy",
        str(policy),
        "--json",
    )
    key = tmp_path / "test-a.pem"
    key.write_bytes(private_pem(b"A" * 32))
    bundle = tmp_path / "bundle.json"
    assert run_cli(
        "sign", str(PACKAGE), "--private-key", str(key), "--kid", "test-a", "--output", str(bundle)
    ).returncode == 0
    no_policy = run_cli(
        "verify-signatures",
        str(PACKAGE),
        "--signature-bundle",
        str(bundle),
        "--key-registry",
        str(registry),
        "--json",
    )
    unsatisfied = run_cli(
        "verify-signatures",
        str(PACKAGE),
        "--signature-bundle",
        str(bundle),
        "--key-registry",
        str(registry),
        "--trust-policy",
        str(policy),
        "--json",
    )

    assert unsigned.returncode == 1
    assert json.loads(unsigned.stdout)["ok"] is True
    assert json.loads(unsigned.stdout)["data"]["signature_presence"] == "unsigned"
    assert no_policy.returncode == 1
    assert json.loads(no_policy.stdout)["data"]["policy_evaluation"] is None
    assert unsatisfied.returncode == 1
    assert json.loads(unsatisfied.stdout)["data"]["policy_evaluation"]["policy_satisfied"] is False


@pytest.mark.parametrize("control", ("registry", "bundle", "policy"))
def test_verify_cli_malformed_controls_exit_two_without_echo(tmp_path: Path, control: str) -> None:
    registry, policy = write_controls(tmp_path, ("test-a", b"A" * 32))
    malformed = tmp_path / f"malformed-{control}.json"
    malformed.write_bytes(b'{"secret":"do-not-echo"')
    arguments = ["verify-signatures", str(PACKAGE), "--key-registry", str(registry), "--trust-policy", str(policy), "--json"]
    if control == "registry":
        arguments[arguments.index(str(registry))] = str(malformed)
    elif control == "policy":
        arguments[arguments.index(str(policy))] = str(malformed)
    else:
        arguments.extend(("--signature-bundle", str(malformed)))

    completed = run_cli(*arguments)
    payload = json.loads(completed.stdout)

    assert completed.returncode == 2
    assert payload["ok"] is False
    assert payload["diagnostics"][0]["code"] == "AECCTX_SIGNING_JSON_INVALID"
    assert "do-not-echo" not in completed.stdout + completed.stderr
    assert str(malformed) not in completed.stdout + completed.stderr


def test_verify_cli_invalid_package_and_missing_crypto_exit_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry, policy = write_controls(tmp_path, ("test-a", b"A" * 32))
    invalid = run_cli(
        "verify-signatures",
        str(tmp_path / "invalid-package"),
        "--key-registry",
        str(registry),
        "--trust-policy",
        str(policy),
        "--json",
    )
    key = tmp_path / "test-a.pem"
    key.write_bytes(private_pem(b"A" * 32))
    bundle = tmp_path / "bundle.json"
    assert run_cli(
        "sign", str(PACKAGE), "--private-key", str(key), "--kid", "test-a", "--output", str(bundle)
    ).returncode == 0

    def unavailable() -> object:
        raise import_module("aecctx.signing").SigningError(
            "AECCTX_SIGNING_CRYPTO_UNAVAILABLE",
            "install aecctx[signing]",
        )

    monkeypatch.setattr(import_module("aecctx._signing_crypto"), "_serialization_modules", unavailable)
    exit_code = import_module("aecctx.cli").main(
        [
            "verify-signatures",
            str(PACKAGE),
            "--signature-bundle",
            str(bundle),
            "--key-registry",
            str(registry),
            "--trust-policy",
            str(policy),
            "--json",
        ]
    )
    missing_crypto = json.loads(capsys.readouterr().out)

    assert invalid.returncode == 2
    assert json.loads(invalid.stdout)["diagnostics"][0]["code"] == "AECCTX_SIGNING_PACKAGE_INVALID"
    assert exit_code == 2
    assert missing_crypto["diagnostics"][0]["code"] == "AECCTX_SIGNING_CRYPTO_UNAVAILABLE"


def test_atomic_sidecar_failure_removes_temporary_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "bundle.json"

    def denied(*args: object, **kwargs: object) -> object:
        raise OSError("denied")

    monkeypatch.setattr(os, "link", denied)
    with pytest.raises(import_module("aecctx.signing").SigningError) as caught:
        import_module("aecctx.cli")._write_new_sidecar(output, b"complete")

    assert caught.value.code == "AECCTX_SIGNING_OUTPUT_FAILED"
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


def test_verify_text_reports_each_status_axis_without_approval_copy(tmp_path: Path) -> None:
    key = tmp_path / "test-a.pem"
    key.write_bytes(private_pem(b"A" * 32))
    bundle = tmp_path / "bundle.json"
    assert run_cli(
        "sign", str(PACKAGE), "--private-key", str(key), "--kid", "test-a", "--output", str(bundle)
    ).returncode == 0
    registry, policy = write_controls(tmp_path, ("test-a", b"A" * 32))
    policy_value = json.loads(policy.read_text(encoding="utf-8"))
    policy_value["trusted_kids"] = []
    policy.write_bytes(import_module("aecctx._signing_io").canonical_json_nfc(policy_value, terminal_lf=True))

    completed = run_cli(
        "verify-signatures",
        str(PACKAGE),
        "--signature-bundle",
        str(bundle),
        "--key-registry",
        str(registry),
        "--trust-policy",
        str(policy),
    )

    assert completed.returncode == 1
    assert "cryptographic=valid:1" in completed.stdout
    assert "key=valid:1" in completed.stdout
    assert "trust=untrusted:1" in completed.stdout
    assert "authorization=unauthorized:1" in completed.stdout
    assert "trust=trusted" not in completed.stdout
    assert "authorization=authorized" not in completed.stdout
    assert "approv" not in completed.stdout.lower()
