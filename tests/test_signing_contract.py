from __future__ import annotations

import json
from importlib import import_module
from importlib.resources import files
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SCHEMA_NAMES = (
    "signature-bundle.schema.json",
    "signing-key-registry.schema.json",
    "signing-trust-policy.schema.json",
    "signature-verification-result.schema.json",
)


def _signing():
    return import_module("aecctx.signing")


def test_signing_limits_are_normative() -> None:
    limits = _signing().SigningLimits()

    assert limits.max_document_bytes == 1_048_576
    assert limits.max_signatures == 64
    assert limits.max_keys == 1_024
    assert limits.max_private_key_bytes == 65_536
    assert limits.max_password_bytes == 4_096


def test_signature_result_keeps_axes_separate() -> None:
    result = _signing().SignatureVerification(
        kid="test-a",
        algorithm="Ed25519",
        subject="urn:aecctx:test:a",
        cryptographic_status="valid",
        identity_status="resolved",
        key_status="expired",
        trust_status="untrusted",
        authorization_status="unauthorized",
        diagnostic_codes=(),
    )

    assert result.cryptographic_status == "valid"
    assert result.key_status == "expired"
    assert result.trust_status == "untrusted"
    assert result.authorization_status == "unauthorized"


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("cryptographic_status", "trusted"),
        ("identity_status", "unknown"),
        ("key_status", "untrusted"),
        ("trust_status", "expired"),
        ("authorization_status", "approved"),
    ),
)
def test_signature_result_rejects_ungoverned_states(field: str, invalid: str) -> None:
    values = {
        "kid": "test-a",
        "algorithm": "Ed25519",
        "subject": "urn:aecctx:test:a",
        "cryptographic_status": "valid",
        "identity_status": "resolved",
        "key_status": "valid",
        "trust_status": "trusted",
        "authorization_status": "authorized",
        "diagnostic_codes": (),
    }
    values[field] = invalid

    with pytest.raises(ValueError, match=field):
        _signing().SignatureVerification(**values)


def test_signing_key_rejects_ungoverned_revocation_status() -> None:
    with pytest.raises(ValueError, match="revocation_status"):
        _signing().SigningKey(
            kid="test-a",
            public_key_x="A" * 43,
            subject="urn:aecctx:test:a",
            valid_from="2026-01-01T00:00:00Z",
            valid_until="2027-01-01T00:00:00Z",
            revocation_status="maybe",
            revoked_at=None,
            scopes=("aecctx.package.sign",),
        )


def test_trust_policy_rejects_disallowed_algorithm() -> None:
    with pytest.raises(ValueError, match="allowed_algorithms"):
        _signing().TrustPolicy(
            verification_time="2026-07-12T00:00:00Z",
            allowed_algorithms=("EdDSA",),
            trusted_kids=(),
            trusted_subjects=(),
            required_scopes=(),
            minimum_authorized_signatures=1,
        )


def test_public_and_packaged_signing_schemas_are_byte_identical() -> None:
    packaged_root = files("aecctx.schemas.v0_2")
    for name in SCHEMA_NAMES:
        public = (ROOT / "schemas" / "v0.2" / name).read_bytes()
        assert packaged_root.joinpath(name).read_bytes() == public


def test_signing_schemas_are_closed_and_versioned() -> None:
    for name in SCHEMA_NAMES:
        schema = json.loads((ROOT / "schemas" / "v0.2" / name).read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"] == f"https://aecctx.dev/schemas/v0.2/{name}"
        assert schema["additionalProperties"] is False


def test_signature_bundle_schema_rejects_payload_and_unprotected_headers() -> None:
    signing = _signing()
    valid = {"signatures": [{"protected": "e30", "signature": "A" * 86}]}
    signing.validate_signing_document(valid, "signature-bundle.schema.json")

    for invalid in (
        {**valid, "payload": "e30"},
        {"signatures": [{**valid["signatures"][0], "header": {"kid": "test-a"}}]},
    ):
        with pytest.raises(signing.SigningError) as caught:
            signing.validate_signing_document(invalid, "signature-bundle.schema.json")
        assert caught.value.code == "AECCTX_SIGNING_SCHEMA_INVALID"


def test_registry_schema_requires_exact_ed25519_jwk_and_revocation_time() -> None:
    signing = _signing()
    key = {
        "kid": "test-a",
        "public_key": {"kty": "OKP", "crv": "Ed25519", "x": "A" * 43},
        "subject": "urn:aecctx:test:a",
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": "2027-01-01T00:00:00Z",
        "revocation_status": "revoked",
        "revoked_at": "2026-06-01T00:00:00Z",
        "scopes": ["aecctx.package.sign"],
    }
    signing.validate_signing_document({"registry_version": "1", "keys": [key]}, "signing-key-registry.schema.json")

    invalid = {"registry_version": "1", "keys": [{name: value for name, value in key.items() if name != "revoked_at"}]}
    with pytest.raises(signing.SigningError) as caught:
        signing.validate_signing_document(invalid, "signing-key-registry.schema.json")
    assert caught.value.code == "AECCTX_SIGNING_SCHEMA_INVALID"


def test_trust_policy_and_result_schemas_preserve_distinct_statuses() -> None:
    signing = _signing()
    policy = {
        "policy_version": "1",
        "verification_time": "2026-07-12T00:00:00Z",
        "allowed_algorithms": ["Ed25519"],
        "trusted_kids": ["test-a"],
        "trusted_subjects": [],
        "required_scopes": ["aecctx.package.sign"],
        "minimum_authorized_signatures": 1,
    }
    signing.validate_signing_document(policy, "signing-trust-policy.schema.json")

    result = {
        "result_version": "1",
        "package_validation": {
            "valid": True,
            "package_id": "pkg_minimal_fixture",
            "logical_digest": "a" * 64,
            "diagnostic_codes": [],
        },
        "statement": {
            "profile": "https://aecctx.dev/signing/v1",
            "statement_version": "1",
            "sha256": "b" * 64,
            "semantic_manifest_sha256": "c" * 64,
        },
        "signature_presence": "signed",
        "verification_completed": True,
        "signatures": [
            {
                "kid": "test-a",
                "algorithm": "Ed25519",
                "subject": "urn:aecctx:test:a",
                "cryptographic_status": "valid",
                "identity_status": "resolved",
                "key_status": "expired",
                "trust_status": "untrusted",
                "authorization_status": "unauthorized",
                "diagnostic_codes": ["AECCTX_SIGNING_KEY_EXPIRED"],
            }
        ],
        "policy_evaluation": {
            "policy_sha256": "d" * 64,
            "minimum_authorized_signatures": 1,
            "authorized_kids": [],
            "policy_satisfied": False,
        },
        "diagnostics": [{"code": "AECCTX_SIGNING_THRESHOLD_NOT_MET", "message": "threshold not met", "severity": "error"}],
    }
    signing.validate_signing_document(result, "signature-verification-result.schema.json")


def test_schema_loader_rejects_names_outside_fixed_allowlist() -> None:
    signing = _signing()

    with pytest.raises(signing.SigningError) as caught:
        signing.validate_signing_document({}, "../../manifest.schema.json")

    assert caught.value.code == "AECCTX_SIGNING_SCHEMA_UNSUPPORTED"
