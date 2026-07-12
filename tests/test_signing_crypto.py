from __future__ import annotations

import subprocess
import sys
import tomllib
import json
import hashlib
import shutil
from importlib import import_module
from pathlib import Path

import pytest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey


ROOT = Path(__file__).parents[1]
CRYPTOGRAPHY_REQUIREMENT = "cryptography>=45,<50"
PACKAGE = ROOT / "fixtures" / "minimal-aecctx"


def _signing():
    return import_module("aecctx.signing")


def _signing_io():
    return import_module("aecctx._signing_io")


def _signing_crypto():
    return import_module("aecctx._signing_crypto")


def _private_pem(seed: bytes = b"A" * 32, *, password: bytes | None = None) -> bytes:
    encryption = serialization.BestAvailableEncryption(password) if password is not None else serialization.NoEncryption()
    return Ed25519PrivateKey.from_private_bytes(seed).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        encryption,
    )


def _package_copy(tmp_path: Path) -> Path:
    target = tmp_path / "package"
    shutil.copytree(PACKAGE, target)
    return target


def _package_hashes(package: Path) -> dict[str, str]:
    return {
        path.relative_to(package).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(package.rglob("*"))
        if path.is_file()
    }


def test_cryptography_is_an_optional_bounded_dependency() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert CRYPTOGRAPHY_REQUIREMENT not in project["dependencies"]
    assert project["optional-dependencies"]["signing"] == [CRYPTOGRAPHY_REQUIREMENT]
    assert CRYPTOGRAPHY_REQUIREMENT in project["optional-dependencies"]["all"]
    assert CRYPTOGRAPHY_REQUIREMENT in project["optional-dependencies"]["test"]


def test_signing_module_does_not_eagerly_import_crypto() -> None:
    code = "import sys, aecctx.signing; print(any(name == 'cryptography' or name.startswith('cryptography.') for name in sys.modules))"

    completed = subprocess.run([sys.executable, "-c", code], text=True, capture_output=True, check=True)

    assert completed.stdout.strip() == "False"


def test_crypto_boundary_loads_ed25519_and_verifies_signature() -> None:
    private_key = _signing_crypto().load_private_key(_private_pem(), None)
    public_key = _signing_crypto().load_public_key(private_key.public_key().public_bytes_raw())

    signature = _signing_crypto().sign_bytes(private_key, b"message")

    assert len(signature) == 64
    assert _signing_crypto().verify_bytes(public_key, signature, b"message") is True
    assert _signing_crypto().verify_bytes(public_key, signature, b"changed") is False


def test_crypto_boundary_verifies_raw_ed25519_material() -> None:
    private_key = Ed25519PrivateKey.from_private_bytes(b"A" * 32)
    public_key = private_key.public_key().public_bytes_raw()
    signature = private_key.sign(b"message")

    assert _signing_crypto().verify_ed25519(public_key, signature, b"message") is True
    assert _signing_crypto().verify_ed25519(public_key, signature, b"changed") is False


def test_crypto_boundary_maps_wrong_password_and_key_type_without_secret_echo() -> None:
    secret = b"do-not-echo-this-password"
    encrypted = _private_pem(password=secret)
    wrong_type = X25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )

    for pem, password in ((encrypted, b"wrong"), (wrong_type, None), (b"not-a-key", None)):
        with pytest.raises(_signing().SigningError) as caught:
            _signing_crypto().load_private_key(pem, password)
        assert caught.value.code == "AECCTX_SIGNING_PRIVATE_KEY_INVALID"
        assert secret.decode("ascii") not in str(caught.value)


def test_sign_package_emits_exact_detached_jws_and_valid_signature(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    private_key = Ed25519PrivateKey.from_private_bytes(b"A" * 32)

    bundle = _signing().sign_package(package, private_key_pem=_private_pem(), kid="test-a")
    encoded = json.loads(bundle.to_bytes())
    entry = bundle.signatures[0]
    protected = json.loads(_signing_io().base64url_decode(entry.protected))
    statement = _signing().build_signing_statement(package)
    signing_input = f"{entry.protected}.{_signing_io().base64url_encode(statement.canonical_bytes)}".encode("ascii")

    assert set(encoded) == {"signatures"}
    assert "payload" not in encoded
    assert protected == {
        "alg": "Ed25519",
        "https://aecctx.dev/jws/statement-sha256": statement.sha256,
        "kid": "test-a",
        "typ": "aecctx-signing-statement+jws",
    }
    assert entry.algorithm == "Ed25519"
    assert entry.statement_sha256 == statement.sha256
    private_key.public_key().verify(_signing_io().base64url_decode(entry.signature, expected_bytes=64), signing_input)
    _signing().validate_signing_document(encoded, "signature-bundle.schema.json")


def test_sign_package_is_deterministic_and_never_mutates_package(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    before = _package_hashes(package)

    first = _signing().sign_package(package, private_key_pem=_private_pem(), kid="test-a")
    second = _signing().sign_package(package, private_key_pem=_private_pem(), kid="test-a")

    assert first == second
    assert first.to_bytes() == second.to_bytes()
    assert _package_hashes(package) == before


def test_sign_package_supports_explicit_encrypted_pkcs8_password(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    password = b"test-only-password"

    bundle = _signing().sign_package(package, private_key_pem=_private_pem(password=password), password=password, kid="encrypted-a")

    assert bundle.signatures[0].kid == "encrypted-a"


@pytest.mark.parametrize("kid", ("", "e\u0301", "bad\nvalue", "x" * 257))
def test_sign_package_rejects_invalid_kid(tmp_path: Path, kid: str) -> None:
    with pytest.raises(_signing().SigningError) as caught:
        _signing().sign_package(_package_copy(tmp_path), private_key_pem=_private_pem(), kid=kid)

    assert caught.value.code == "AECCTX_SIGNING_KID_INVALID"


def test_sign_package_enforces_private_key_and_password_limits(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    limits = _signing().SigningLimits(max_private_key_bytes=8, max_password_bytes=4)

    for pem, password in ((_private_pem(), None), (_private_pem(), b"12345")):
        with pytest.raises(_signing().SigningError) as caught:
            _signing().sign_package(package, private_key_pem=pem, password=password, kid="test-a", limits=limits)
        assert caught.value.code == "AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED"


def test_append_signature_sorts_and_preserves_existing_entry(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    first = _signing().sign_package(package, private_key_pem=_private_pem(b"Z" * 32), kid="test-z")

    appended = _signing().append_signature(package, first, private_key_pem=_private_pem(b"A" * 32), kid="test-a")

    assert [entry.kid for entry in appended.signatures] == ["test-a", "test-z"]
    assert next(entry for entry in appended.signatures if entry.kid == "test-z") is first.signatures[0]
    assert json.loads(appended.to_bytes())["signatures"] == [
        {"protected": entry.protected, "signature": entry.signature} for entry in appended.signatures
    ]


def test_append_signature_rejects_duplicate_kid_and_signature_limit(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    first = _signing().sign_package(package, private_key_pem=_private_pem(), kid="test-a")

    with pytest.raises(_signing().SigningError) as duplicate:
        _signing().append_signature(package, first, private_key_pem=_private_pem(b"B" * 32), kid="test-a")
    assert duplicate.value.code == "AECCTX_SIGNING_DUPLICATE_KID"

    limits = _signing().SigningLimits(max_signatures=1)
    with pytest.raises(_signing().SigningError) as excessive:
        _signing().append_signature(package, first, private_key_pem=_private_pem(b"B" * 32), kid="test-b", limits=limits)
    assert excessive.value.code == "AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED"
