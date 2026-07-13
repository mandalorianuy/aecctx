from __future__ import annotations

import socket
import time
import hashlib
import json
import shutil
from dataclasses import replace
from importlib import import_module
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "fixtures" / "minimal-aecctx"


def _signing():
    return import_module("aecctx.signing")


def _key(**changes: object):
    value = _signing().SigningKey(
        kid="test-a",
        public_key_x="A" * 43,
        subject="urn:aecctx:test:a",
        valid_from="2026-01-01T00:00:00Z",
        valid_until="2027-01-01T00:00:00Z",
        revocation_status="good",
        revoked_at=None,
        scopes=("aecctx.package.sign",),
    )
    return replace(value, **changes)


def _policy(verification_time: str = "2026-07-12T00:00:00Z", **changes: object):
    value = _signing().TrustPolicy(
        verification_time=verification_time,
        allowed_algorithms=("Ed25519",),
        trusted_kids=("test-a",),
        trusted_subjects=(),
        required_scopes=("aecctx.package.sign",),
        minimum_authorized_signatures=1,
    )
    return replace(value, **changes)


@pytest.mark.parametrize(
    ("instant", "expected"),
    (
        ("2025-12-31T23:59:59Z", "not_yet_valid"),
        ("2026-01-01T00:00:00Z", "valid"),
        ("2026-12-31T23:59:59Z", "valid"),
        ("2027-01-01T00:00:00Z", "expired"),
    ),
)
def test_key_lifecycle_uses_inclusive_start_and_exclusive_end(instant: str, expected: str) -> None:
    evaluation = _signing().evaluate_key(_key(), _policy(instant))

    assert evaluation.key_status == expected
    assert evaluation.trust_status == ("trusted" if expected == "valid" else "untrusted")
    assert evaluation.authorization_status == ("authorized" if expected == "valid" else "unauthorized")


def test_revocation_boundary_is_valid_before_and_revoked_at_instant() -> None:
    key = _key(revocation_status="revoked", revoked_at="2026-06-01T00:00:00Z")

    before = _signing().evaluate_key(key, _policy("2026-05-31T23:59:59Z"))
    at = _signing().evaluate_key(key, _policy("2026-06-01T00:00:00Z"))

    assert (before.key_status, before.trust_status, before.authorization_status) == (
        "valid",
        "trusted",
        "authorized",
    )
    assert (at.key_status, at.trust_status, at.authorization_status) == (
        "revoked",
        "untrusted",
        "unauthorized",
    )
    assert at.diagnostic_codes == (
        "AECCTX_SIGNING_KEY_REVOKED",
        "AECCTX_SIGNING_KEY_UNTRUSTED",
        "AECCTX_SIGNING_SIGNER_UNAUTHORIZED",
    )


def test_unknown_revocation_status_is_explicit_and_not_not_evaluated() -> None:
    evaluation = _signing().evaluate_key(_key(revocation_status="unknown"), _policy())

    assert evaluation.key_status == "unknown_status"
    assert evaluation.trust_status == "untrusted"
    assert evaluation.authorization_status == "unauthorized"
    assert evaluation.diagnostic_codes[0] == "AECCTX_SIGNING_KEY_STATUS_UNKNOWN"


def test_lifecycle_trust_and_authorization_failures_remain_separate() -> None:
    expired_untrusted = _signing().evaluate_key(
        _key(),
        _policy("2030-01-01T00:00:00Z", trusted_kids=(), trusted_subjects=()),
    )
    trusted_missing_scope = _signing().evaluate_key(
        _key(scopes=()),
        _policy(),
    )

    assert (expired_untrusted.key_status, expired_untrusted.trust_status) == ("expired", "untrusted")
    assert trusted_missing_scope.key_status == "valid"
    assert trusted_missing_scope.trust_status == "trusted"
    assert trusted_missing_scope.authorization_status == "unauthorized"


def test_subject_allowlist_is_resolved_only_from_registry_key() -> None:
    evaluation = _signing().evaluate_key(
        _key(kid="rotation-b"),
        _policy(trusted_kids=(), trusted_subjects=("urn:aecctx:test:a",)),
    )

    assert evaluation.trust_status == "trusted"
    assert evaluation.authorization_status == "authorized"


@pytest.mark.parametrize(
    ("key", "policy"),
    (
        (None, _policy()),
        (_key(), None),
        (None, None),
    ),
)
def test_missing_key_or_policy_is_not_evaluated(key: object, policy: object) -> None:
    evaluation = _signing().evaluate_key(key, policy)

    assert evaluation.key_status == "not_evaluated"
    assert evaluation.trust_status == "not_evaluated"
    assert evaluation.authorization_status == "not_evaluated"
    assert evaluation.diagnostic_codes == ()


def test_policy_evaluation_is_deterministic_without_host_clock_or_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("host clock or network access is forbidden")

    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)

    first = _signing().evaluate_key(_key(), _policy())
    second = _signing().evaluate_key(_key(), _policy())

    assert first == second


def _private_pem(seed: bytes) -> bytes:
    return Ed25519PrivateKey.from_private_bytes(seed).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _package_copy(tmp_path: Path, name: str = "package") -> Path:
    target = tmp_path / name
    shutil.copytree(PACKAGE, target)
    return target


def _registry_key(kid: str, seed: bytes, **changes: object):
    public_key = Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes_raw()
    value = _signing().SigningKey(
        kid=kid,
        public_key_x=import_module("aecctx._signing_io").base64url_encode(public_key),
        subject="urn:aecctx:test:signer",
        valid_from="2026-01-01T00:00:00Z",
        valid_until="2027-01-01T00:00:00Z",
        revocation_status="good",
        revoked_at=None,
        scopes=("aecctx.package.sign",),
    )
    return replace(value, **changes)


def _verification_policy(*kids: str, threshold: int = 1, **changes: object):
    value = _signing().TrustPolicy(
        verification_time="2026-07-12T00:00:00Z",
        allowed_algorithms=("Ed25519",),
        trusted_kids=tuple(kids),
        trusted_subjects=(),
        required_scopes=("aecctx.package.sign",),
        minimum_authorized_signatures=threshold,
    )
    return replace(value, **changes)


def _signed_bundle(package: Path, *signers: tuple[str, bytes]):
    bundle = None
    for kid, seed in signers:
        if bundle is None:
            bundle = _signing().sign_package(package, private_key_pem=_private_pem(seed), kid=kid)
        else:
            bundle = _signing().append_signature(
                package,
                bundle,
                private_key_pem=_private_pem(seed),
                kid=kid,
            )
    assert bundle is not None
    return bundle


def test_verify_authorized_signature_emits_schema_valid_deterministic_result(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    bundle = _signed_bundle(package, ("test-a", b"A" * 32))
    registry = _signing().KeyRegistry((_registry_key("test-a", b"A" * 32),))
    policy = _verification_policy("test-a")

    first = _signing().verify_package_signatures(package, bundle=bundle, registry=registry, policy=policy)
    second = _signing().verify_package_signatures(package, bundle=bundle, registry=registry, policy=policy)
    document = first.to_dict()

    assert first == second
    assert first.policy_satisfied is True
    assert first.signatures[0].cryptographic_status == "valid"
    assert first.signatures[0].identity_status == "resolved"
    assert first.signatures[0].key_status == "valid"
    assert first.signatures[0].trust_status == "trusted"
    assert first.signatures[0].authorization_status == "authorized"
    assert list(document) == [
        "result_version",
        "package_validation",
        "statement",
        "signature_presence",
        "verification_completed",
        "signatures",
        "policy_evaluation",
        "diagnostics",
    ]
    assert document["policy_evaluation"]["authorized_kids"] == ["test-a"]
    assert document["statement"]["sha256"] == _signing().build_signing_statement(package).sha256
    _signing().validate_signing_document(document, "signature-verification-result.schema.json")


def test_foreign_bundle_is_distinct_from_corrupt_signature(tmp_path: Path) -> None:
    package_a = _package_copy(tmp_path, "package-a")
    package_b = _package_copy(tmp_path, "package-b")
    manifest_path = package_b / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["producer"]["version"] = "foreign"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    bundle = _signed_bundle(package_a, ("test-a", b"A" * 32))
    corrupted_entry = replace(
        bundle.signatures[0],
        signature=import_module("aecctx._signing_io").base64url_encode(b"\0" * 64),
    )
    corrupt = _signing().SignatureBundle((corrupted_entry,))
    registry = _signing().KeyRegistry((_registry_key("test-a", b"A" * 32),))

    foreign_result = _signing().verify_package_signatures(package_b, bundle=bundle, registry=registry)
    corrupt_result = _signing().verify_package_signatures(package_a, bundle=corrupt, registry=registry)

    assert foreign_result.signatures[0].diagnostic_codes == (
        "AECCTX_SIGNING_STATEMENT_BINDING_MISMATCH",
    )
    assert corrupt_result.signatures[0].diagnostic_codes == ("AECCTX_SIGNING_SIGNATURE_INVALID",)


def test_verify_reports_unknown_key_and_unsupported_algorithm(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    signed = _signed_bundle(package, ("missing", b"A" * 32))
    unknown = _signing().verify_package_signatures(
        package,
        bundle=signed,
        registry=_signing().KeyRegistry(()),
    )
    statement = _signing().build_signing_statement(package)
    protected_value = {
        "alg": "EdDSA",
        "https://aecctx.dev/jws/statement-sha256": statement.sha256,
        "kid": "test-a",
        "typ": "aecctx-signing-statement+jws",
    }
    signing_io = import_module("aecctx._signing_io")
    protected = signing_io.base64url_encode(signing_io.canonical_json_nfc(protected_value, terminal_lf=False))
    unsupported_bundle = _signing().SignatureBundle(
        (
            _signing().SignatureEntry(
                protected,
                signed.signatures[0].signature,
                "test-a",
                "EdDSA",
                statement.sha256,
            ),
        )
    )
    unsupported = _signing().verify_package_signatures(
        package,
        bundle=unsupported_bundle,
        registry=_signing().KeyRegistry((_registry_key("test-a", b"A" * 32),)),
    )

    assert unknown.signatures[0].cryptographic_status == "unknown_key"
    assert unknown.signatures[0].identity_status == "unresolved"
    assert unknown.signatures[0].key_status == "not_evaluated"
    assert unknown.signatures[0].diagnostic_codes == ("AECCTX_SIGNING_UNKNOWN_KEY",)
    assert unsupported.signatures[0].cryptographic_status == "unsupported_algorithm"
    assert unsupported.signatures[0].diagnostic_codes == ("AECCTX_SIGNING_ALGORITHM_UNSUPPORTED",)


@pytest.mark.parametrize(
    ("key_changes", "policy_changes", "expected"),
    (
        ({}, {"trusted_kids": ()}, ("valid", "untrusted", "unauthorized")),
        ({"scopes": ()}, {}, ("valid", "trusted", "unauthorized")),
        ({"valid_from": "2026-08-01T00:00:00Z"}, {}, ("not_yet_valid", "untrusted", "unauthorized")),
        ({"valid_until": "2026-07-01T00:00:00Z"}, {}, ("expired", "untrusted", "unauthorized")),
        (
            {"revocation_status": "revoked", "revoked_at": "2026-06-01T00:00:00Z"},
            {},
            ("revoked", "untrusted", "unauthorized"),
        ),
        ({"revocation_status": "unknown"}, {}, ("unknown_status", "untrusted", "unauthorized")),
    ),
)
def test_verify_keeps_policy_status_axes_separate(
    tmp_path: Path,
    key_changes: dict[str, object],
    policy_changes: dict[str, object],
    expected: tuple[str, str, str],
) -> None:
    package = _package_copy(tmp_path)
    bundle = _signed_bundle(package, ("test-a", b"A" * 32))
    key = _registry_key("test-a", b"A" * 32, **key_changes)
    policy = _verification_policy("test-a", **policy_changes)

    result = _signing().verify_package_signatures(
        package,
        bundle=bundle,
        registry=_signing().KeyRegistry((key,)),
        policy=policy,
    )
    signature = result.signatures[0]

    assert signature.cryptographic_status == "valid"
    assert (signature.key_status, signature.trust_status, signature.authorization_status) == expected
    assert result.policy_satisfied is False
    assert result.diagnostics[-1].code == "AECCTX_SIGNING_THRESHOLD_NOT_MET"


def test_verify_without_policy_leaves_policy_axes_not_evaluated(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    bundle = _signed_bundle(package, ("test-a", b"A" * 32))
    registry = _signing().KeyRegistry((_registry_key("test-a", b"A" * 32),))

    result = _signing().verify_package_signatures(package, bundle=bundle, registry=registry)

    assert result.policy_satisfied is None
    assert result.signatures[0].cryptographic_status == "valid"
    assert result.signatures[0].key_status == "not_evaluated"
    assert result.signatures[0].trust_status == "not_evaluated"
    assert result.signatures[0].authorization_status == "not_evaluated"
    assert result.to_dict()["policy_evaluation"] is None


@pytest.mark.parametrize("with_policy", (False, True))
def test_unsigned_verification_has_no_fabricated_signature_and_no_crypto_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    with_policy: bool,
) -> None:
    package = _package_copy(tmp_path)

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("cryptography boundary must not be called")

    monkeypatch.setattr(import_module("aecctx._signing_crypto"), "verify_ed25519", forbidden, raising=False)
    policy = _verification_policy("test-a") if with_policy else None
    result = _signing().verify_package_signatures(
        package,
        bundle=None,
        registry=_signing().KeyRegistry(()),
        policy=policy,
    )

    assert result.signature_presence == "unsigned"
    assert result.signatures == ()
    assert result.policy_satisfied is (False if with_policy else None)


def test_threshold_counts_unique_authorized_kids_and_supports_rotation(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    bundle = _signed_bundle(package, ("rotation-a", b"A" * 32), ("rotation-b", b"B" * 32))
    registry = _signing().KeyRegistry(
        (
            _registry_key("rotation-a", b"A" * 32),
            _registry_key("rotation-b", b"B" * 32),
        )
    )

    one = _signing().verify_package_signatures(
        package,
        bundle=bundle,
        registry=registry,
        policy=_verification_policy("rotation-a", "rotation-b", threshold=1),
    )
    two = _signing().verify_package_signatures(
        package,
        bundle=bundle,
        registry=registry,
        policy=_verification_policy("rotation-a", "rotation-b", threshold=2),
    )

    assert one.policy_satisfied is True
    assert two.policy_satisfied is True
    assert two.to_dict()["policy_evaluation"]["authorized_kids"] == ["rotation-a", "rotation-b"]


def test_threshold_failure_duplicate_signer_and_invalid_package_are_explicit(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    bundle = _signed_bundle(package, ("test-a", b"A" * 32))
    registry = _signing().KeyRegistry((_registry_key("test-a", b"A" * 32),))
    threshold = _signing().verify_package_signatures(
        package,
        bundle=bundle,
        registry=registry,
        policy=_verification_policy("test-a", threshold=2),
    )
    duplicate = _signing().SignatureBundle((bundle.signatures[0], bundle.signatures[0]))

    assert threshold.policy_satisfied is False
    assert threshold.diagnostics[-1].code == "AECCTX_SIGNING_THRESHOLD_NOT_MET"
    with pytest.raises(_signing().SigningError) as duplicate_error:
        _signing().verify_package_signatures(package, bundle=duplicate, registry=registry)
    assert duplicate_error.value.code == "AECCTX_SIGNING_DUPLICATE_KID"

    (package / "context/index.md").write_text("mutated", encoding="utf-8")
    with pytest.raises(_signing().SigningError) as package_error:
        _signing().verify_package_signatures(package, bundle=bundle, registry=registry)
    assert package_error.value.code == "AECCTX_SIGNING_PACKAGE_INVALID"
    assert str(package) not in str(package_error.value)


def test_crypto_absence_is_operational_and_does_not_expose_key_material(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = _package_copy(tmp_path)
    bundle = _signed_bundle(package, ("test-a", b"A" * 32))
    key = _registry_key("test-a", b"A" * 32)

    def unavailable(*args: object, **kwargs: object) -> object:
        raise _signing().SigningError("AECCTX_SIGNING_CRYPTO_UNAVAILABLE", "install aecctx[signing]")

    monkeypatch.setattr(import_module("aecctx._signing_crypto"), "verify_ed25519", unavailable, raising=False)
    with pytest.raises(_signing().SigningError) as caught:
        _signing().verify_package_signatures(
            package,
            bundle=bundle,
            registry=_signing().KeyRegistry((key,)),
        )

    assert caught.value.code == "AECCTX_SIGNING_CRYPTO_UNAVAILABLE"
    assert key.public_key_x not in str(caught.value)


def test_policy_digest_is_canonical_and_result_copy_uses_no_approval_language(tmp_path: Path) -> None:
    package = _package_copy(tmp_path)
    bundle = _signed_bundle(package, ("test-a", b"A" * 32))
    policy = _verification_policy("test-a")
    result = _signing().verify_package_signatures(
        package,
        bundle=bundle,
        registry=_signing().KeyRegistry((_registry_key("test-a", b"A" * 32),)),
        policy=policy,
    )
    document = result.to_dict()
    policy_value = {
        "allowed_algorithms": ["Ed25519"],
        "minimum_authorized_signatures": 1,
        "policy_version": "1",
        "required_scopes": ["aecctx.package.sign"],
        "trusted_kids": ["test-a"],
        "trusted_subjects": [],
        "verification_time": "2026-07-12T00:00:00Z",
    }
    canonical = import_module("aecctx._signing_io").canonical_json_nfc(policy_value, terminal_lf=True)

    assert document["policy_evaluation"]["policy_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert "approv" not in json.dumps(document).lower()
