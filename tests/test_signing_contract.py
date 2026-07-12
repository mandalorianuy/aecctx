from __future__ import annotations

import json
import hashlib
import shutil
import zipfile
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


def _signing_io():
    return import_module("aecctx._signing_io")


def _copy_package(tmp_path: Path, *, version: str = "0.1") -> Path:
    source = ROOT / ("fixtures/minimal-aecctx" if version == "0.1" else "fixtures/v0.2/shared/minimal-v02")
    target = tmp_path / f"package-{version.replace('.', '')}"
    shutil.copytree(source, target)
    return target


def _manifest(path: Path) -> dict:
    return json.loads((path / "manifest.json").read_text(encoding="utf-8"))


def _write_manifest(path: Path, manifest: dict) -> None:
    (path / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def _zip_package(directory: Path, archive: Path) -> Path:
    manifest = _manifest(directory)
    manifest["package_form"] = "zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(directory).as_posix()
            if relative == "manifest.json":
                data = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            else:
                data = path.read_bytes()
            output.writestr(relative, data)
    return archive


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


def test_strict_json_rejects_duplicate_names() -> None:
    with pytest.raises(_signing().SigningError) as caught:
        _signing_io().load_strict_json(b'{"kid":"a","kid":"b"}', label="registry", max_bytes=1_024)

    assert caught.value.code == "AECCTX_SIGNING_JSON_DUPLICATE_KEY"


def test_strict_json_rejects_keys_that_collide_after_nfc() -> None:
    value = '{"\u00e9":1,"e\u0301":2}'.encode("utf-8")

    with pytest.raises(_signing().SigningError) as caught:
        _signing_io().load_strict_json(value, label="policy", max_bytes=1_024)

    assert caught.value.code == "AECCTX_SIGNING_JSON_DUPLICATE_KEY"


@pytest.mark.parametrize("value", (b'"\xff"', b'{"value":NaN}', b'{"value":Infinity}'))
def test_strict_json_rejects_invalid_utf8_and_non_finite_numbers(value: bytes) -> None:
    with pytest.raises(_signing().SigningError) as caught:
        _signing_io().load_strict_json(value, label="bundle", max_bytes=1_024)

    assert caught.value.code == "AECCTX_SIGNING_JSON_INVALID"


def test_strict_json_enforces_byte_limit_before_parsing() -> None:
    with pytest.raises(_signing().SigningError) as caught:
        _signing_io().load_strict_json(b'{"value":1}', label="policy", max_bytes=4)

    assert caught.value.code == "AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED"


def test_canonical_json_normalizes_nfc_and_terminal_lf() -> None:
    canonical = _signing_io().canonical_json_nfc({"z": "e\u0301", "a": 1}, terminal_lf=True)

    assert canonical == '{"a":1,"z":"\u00e9"}\n'.encode("utf-8")
    assert _signing_io().canonical_json_nfc({"a": 1}, terminal_lf=False) == b'{"a":1}'


def test_base64url_round_trip_is_unpadded_and_length_checked() -> None:
    encoded = _signing_io().base64url_encode(b"aecctx")

    assert encoded == "YWVjY3R4"
    assert _signing_io().base64url_decode(encoded, expected_bytes=6) == b"aecctx"
    with pytest.raises(_signing().SigningError) as caught:
        _signing_io().base64url_decode(encoded, expected_bytes=7)
    assert caught.value.code == "AECCTX_SIGNING_BASE64URL_INVALID"


@pytest.mark.parametrize("value", ("YQ==", "AB", "a b", ""))
def test_base64url_rejects_padding_noncanonical_and_invalid_values(value: str) -> None:
    with pytest.raises(_signing().SigningError) as caught:
        _signing_io().base64url_decode(value)

    assert caught.value.code == "AECCTX_SIGNING_BASE64URL_INVALID"


def test_bounded_file_reader_accepts_only_regular_non_symlink_files(tmp_path: Path) -> None:
    regular = tmp_path / "policy.json"
    regular.write_bytes(b"{}")
    assert _signing_io().read_bounded_regular_file(regular, max_bytes=2, label="policy") == b"{}"

    symlink = tmp_path / "policy-link.json"
    symlink.symlink_to(regular)
    for invalid in (symlink, tmp_path):
        with pytest.raises(_signing().SigningError) as caught:
            _signing_io().read_bounded_regular_file(invalid, max_bytes=2, label="policy")
        assert caught.value.code == "AECCTX_SIGNING_FILE_UNSAFE"


def test_bounded_file_reader_rejects_oversize_before_read(tmp_path: Path) -> None:
    path = tmp_path / "bundle.json"
    path.write_bytes(b"12345")

    with pytest.raises(_signing().SigningError) as caught:
        _signing_io().read_bounded_regular_file(path, max_bytes=4, label="bundle")

    assert caught.value.code == "AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED"


def test_signing_statement_has_exact_v01_fields_and_terminal_lf(tmp_path: Path) -> None:
    package = _copy_package(tmp_path)
    manifest = _manifest(package)
    semantic = {key: value for key, value in manifest.items() if key != "package_form"}
    semantic_bytes = _signing_io().canonical_json_nfc(semantic, terminal_lf=True)

    statement = _signing().build_signing_statement(package)

    assert statement.data["aecctx_version"] == "0.1.0"
    assert statement.data["logical_digest"] == manifest["logical_digest"]
    assert statement.data["package_id"] == manifest["package_id"]
    assert statement.data["profile"] == "https://aecctx.dev/signing/v1"
    assert statement.data["required_extensions"] == ()
    assert statement.data["semantic_manifest_sha256"] == hashlib.sha256(semantic_bytes).hexdigest()
    assert statement.data["statement_version"] == "1"
    assert statement.canonical_bytes.endswith(b"\n")
    assert not statement.canonical_bytes.endswith(b"\n\n")
    assert statement.sha256 == hashlib.sha256(statement.canonical_bytes).hexdigest()


def test_signing_statement_data_is_recursively_immutable(tmp_path: Path) -> None:
    statement = _signing().build_signing_statement(_copy_package(tmp_path))

    with pytest.raises(TypeError):
        statement.data["package_id"] = "mutated"
    with pytest.raises(AttributeError):
        statement.data["required_extensions"].append("org.example.invalid@1")


def test_signing_statement_preserves_v02_required_extensions(tmp_path: Path) -> None:
    package = _copy_package(tmp_path, version="0.2")
    manifest = _manifest(package)

    statement = _signing().build_signing_statement(package)

    assert statement.data["aecctx_version"] == "0.2.0"
    assert statement.data["required_extensions"] == tuple(manifest["required_extensions"])


def test_signing_statement_is_deterministic(tmp_path: Path) -> None:
    package = _copy_package(tmp_path)

    first = _signing().build_signing_statement(package)
    second = _signing().build_signing_statement(package)

    assert first == second


def test_directory_and_zip_equivalents_have_same_statement(tmp_path: Path) -> None:
    directory = _copy_package(tmp_path)
    archive = _zip_package(directory, tmp_path / "package.aecctx")

    assert _signing().build_signing_statement(directory) == _signing().build_signing_statement(archive)


def test_package_form_is_the_only_ignored_manifest_field(tmp_path: Path) -> None:
    original = _copy_package(tmp_path)
    form_only = tmp_path / "form-only"
    shutil.copytree(original, form_only)
    form_manifest = _manifest(form_only)
    form_manifest["package_form"] = "zip"
    _write_manifest(form_only, form_manifest)

    producer_changed = tmp_path / "producer-changed"
    shutil.copytree(original, producer_changed)
    producer_manifest = _manifest(producer_changed)
    producer_manifest["producer"]["version"] = "different"
    _write_manifest(producer_changed, producer_manifest)

    baseline = _signing().build_signing_statement(original)
    assert _signing().build_signing_statement(form_only) == baseline
    assert _signing().build_signing_statement(producer_changed) != baseline


def test_signing_statement_rejects_duplicate_manifest_names(tmp_path: Path) -> None:
    package = _copy_package(tmp_path)
    manifest_path = package / "manifest.json"
    raw = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text('{"package_id":"shadow",' + raw.lstrip()[1:], encoding="utf-8")

    with pytest.raises(_signing().SigningError) as caught:
        _signing().build_signing_statement(package)

    assert caught.value.code == "AECCTX_SIGNING_JSON_DUPLICATE_KEY"


def test_signing_statement_rejects_invalid_package_integrity(tmp_path: Path) -> None:
    package = _copy_package(tmp_path)
    (package / "context/index.md").write_text("mutated", encoding="utf-8")

    with pytest.raises(_signing().SigningError) as caught:
        _signing().build_signing_statement(package)

    assert caught.value.code == "AECCTX_SIGNING_PACKAGE_INVALID"
