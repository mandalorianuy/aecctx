#!/usr/bin/env python3
"""Generate deterministic, TEST ONLY ACX-20 signing conformance material."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
import zipfile
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from aecctx._signing_io import base64url_decode, base64url_encode, canonical_json_nfc  # noqa: E402
from aecctx.signing import SignatureBundle, SignatureEntry, append_signature, sign_package  # noqa: E402


README = """# ACX-20 signing conformance fixtures

Every key and signature in this directory is project-generated **TEST ONLY** material.
The private keys are deterministic corpus inputs, are not production identities or trust
roots, and MUST NOT be used outside tests. The corpus has no network, LLM, certificate,
timestamp or online revocation dependency.

Run `python fixtures/v0.2/signing/generate_fixtures.py --check` to prove byte stability.
"""


def seed(label: str) -> bytes:
    return hashlib.sha256(f"aecctx-acx20-{label}".encode("ascii")).digest()


def private_key(label: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(seed(label))


def private_pem(label: str) -> bytes:
    return private_key(label).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def public_x(label: str) -> str:
    return base64url_encode(private_key(label).public_key().public_bytes_raw())


def key_record(
    kid: str,
    label: str,
    *,
    valid_from: str = "2026-01-01T00:00:00Z",
    valid_until: str = "2027-01-01T00:00:00Z",
    revocation_status: str = "good",
    revoked_at: str | None = None,
    scopes: list[str] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "kid": kid,
        "public_key": {"kty": "OKP", "crv": "Ed25519", "x": public_x(label)},
        "subject": "urn:aecctx:test:rotation",
        "valid_from": valid_from,
        "valid_until": valid_until,
        "revocation_status": revocation_status,
        "scopes": ["aecctx.package.sign"] if scopes is None else scopes,
    }
    if revoked_at is not None:
        value["revoked_at"] = revoked_at
    return value


def registry(*keys: dict[str, object]) -> bytes:
    return canonical_json_nfc({"registry_version": "1", "keys": list(keys)}, terminal_lf=True)


def policy(*trusted_kids: str, threshold: int = 1, required_scopes: list[str] | None = None) -> bytes:
    return canonical_json_nfc(
        {
            "policy_version": "1",
            "verification_time": "2026-07-12T00:00:00Z",
            "allowed_algorithms": ["Ed25519"],
            "trusted_kids": sorted(trusted_kids),
            "trusted_subjects": [],
            "required_scopes": ["aecctx.package.sign"] if required_scopes is None else required_scopes,
            "minimum_authorized_signatures": threshold,
        },
        terminal_lf=True,
    )


def package_copy(source: Path, *, manifest_version: str | None = None, mutate_artifact: bool = False) -> dict[str, bytes]:
    files = {path.relative_to(source).as_posix(): path.read_bytes() for path in sorted(source.rglob("*")) if path.is_file()}
    if manifest_version is not None:
        manifest = json.loads(files["manifest.json"])
        manifest["producer"]["version"] = manifest_version
        files["manifest.json"] = canonical_json_nfc(manifest, terminal_lf=True)
    if mutate_artifact:
        files["context/index.md"] = b"mutated artifact\n"
    return files


def zip_package(source: Path) -> bytes:
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    manifest["package_form"] = "zip"
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = path.relative_to(source).as_posix()
            data = canonical_json_nfc(manifest, terminal_lf=True) if relative == "manifest.json" else path.read_bytes()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, data)
    return output.getvalue()


def mutate_bundle(bundle: SignatureBundle, *, signature: bytes | None = None, header: dict[str, object] | None = None) -> bytes:
    entry = bundle.signatures[0]
    protected = entry.protected
    algorithm = entry.algorithm
    statement_sha256 = entry.statement_sha256
    if header is not None:
        protected = base64url_encode(canonical_json_nfc(header, terminal_lf=False))
        algorithm = str(header.get("alg", algorithm))
        statement_sha256 = str(header.get("https://aecctx.dev/jws/statement-sha256", statement_sha256))
    changed = replace(
        entry,
        protected=protected,
        signature=base64url_encode(signature) if signature is not None else entry.signature,
        algorithm=algorithm,
        statement_sha256=statement_sha256,
    )
    return SignatureBundle((changed,)).to_bytes()


def expected_files() -> dict[Path, bytes]:
    v01 = ROOT / "fixtures" / "minimal-aecctx"
    v02 = ROOT / "fixtures" / "v0.2" / "shared" / "minimal-v02"
    outputs: dict[Path, bytes] = {FIXTURE_ROOT / "README.md": README.encode("utf-8")}
    for label in ("test-a", "test-b", "test-c"):
        outputs[FIXTURE_ROOT / "keys" / f"{label}.pem"] = private_pem(label)

    a = key_record("test-a", "test-a")
    b = key_record("test-b", "test-b")
    c = key_record("test-c", "test-c")
    outputs[FIXTURE_ROOT / "registries" / "valid.json"] = registry(a, b, c)
    outputs[FIXTURE_ROOT / "registries" / "a-only.json"] = registry(a)
    outputs[FIXTURE_ROOT / "registries" / "no-scope.json"] = registry(key_record("test-a", "test-a", scopes=[]))
    outputs[FIXTURE_ROOT / "registries" / "not-yet-valid.json"] = registry(
        key_record("test-a", "test-a", valid_from="2026-08-01T00:00:00Z", valid_until="2027-08-01T00:00:00Z")
    )
    outputs[FIXTURE_ROOT / "registries" / "expired.json"] = registry(
        key_record("test-a", "test-a", valid_from="2025-01-01T00:00:00Z", valid_until="2026-07-01T00:00:00Z")
    )
    outputs[FIXTURE_ROOT / "registries" / "revoked.json"] = registry(
        key_record("test-a", "test-a", revocation_status="revoked", revoked_at="2026-06-01T00:00:00Z")
    )
    outputs[FIXTURE_ROOT / "registries" / "unknown-status.json"] = registry(
        key_record("test-a", "test-a", revocation_status="unknown")
    )
    outputs[FIXTURE_ROOT / "policies" / "trust-a.json"] = policy("test-a")
    outputs[FIXTURE_ROOT / "policies" / "trust-none.json"] = policy()
    outputs[FIXTURE_ROOT / "policies" / "trust-ab-1.json"] = policy("test-a", "test-b", threshold=1)
    outputs[FIXTURE_ROOT / "policies" / "trust-ab-2.json"] = policy("test-a", "test-b", threshold=2)

    valid_a = sign_package(v01, private_key_pem=private_pem("test-a"), kid="test-a")
    valid_b = sign_package(v01, private_key_pem=private_pem("test-b"), kid="test-b")
    valid_c = sign_package(v01, private_key_pem=private_pem("test-c"), kid="test-c")
    multi_ab = append_signature(v01, valid_a, private_key_pem=private_pem("test-b"), kid="test-b")
    valid_v02 = sign_package(v02, private_key_pem=private_pem("test-a"), kid="test-a")
    outputs[FIXTURE_ROOT / "bundles" / "valid-a.json"] = valid_a.to_bytes()
    outputs[FIXTURE_ROOT / "bundles" / "valid-b.json"] = valid_b.to_bytes()
    outputs[FIXTURE_ROOT / "bundles" / "valid-c.json"] = valid_c.to_bytes()
    outputs[FIXTURE_ROOT / "bundles" / "valid-v02.json"] = valid_v02.to_bytes()
    outputs[FIXTURE_ROOT / "bundles" / "multi-ab.json"] = multi_ab.to_bytes()
    outputs[FIXTURE_ROOT / "bundles" / "invalid-signature.json"] = mutate_bundle(valid_a, signature=b"\0" * 64)
    header = json.loads(base64url_decode(valid_a.signatures[0].protected))
    invalid_header = dict(header)
    invalid_header["typ"] = "application/jose"
    outputs[FIXTURE_ROOT / "bundles" / "invalid-header.json"] = mutate_bundle(valid_a, header=invalid_header)
    unsupported_header = dict(header)
    unsupported_header["alg"] = "EdDSA"
    outputs[FIXTURE_ROOT / "bundles" / "unsupported-algorithm.json"] = mutate_bundle(valid_a, header=unsupported_header)
    outputs[FIXTURE_ROOT / "adversarial" / "duplicate-json.json"] = b'{"signatures":[],"signatures":[]}\n'
    outputs[FIXTURE_ROOT / "adversarial" / "oversize.json"] = b'{"padding":"' + b"A" * 1_048_576 + b'"}\n'

    artifact_package = package_copy(v01, mutate_artifact=True)
    manifest_package = package_copy(v01, manifest_version="foreign")
    for relative, data in artifact_package.items():
        outputs[FIXTURE_ROOT / "packages" / "artifact-mutated" / relative] = data
    for relative, data in manifest_package.items():
        outputs[FIXTURE_ROOT / "packages" / "manifest-mutated" / relative] = data
    outputs[FIXTURE_ROOT / "packages" / "minimal-v01.aecctx"] = zip_package(v01)
    return outputs


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def file_hashes(paths: list[Path], outputs: dict[Path, bytes]) -> dict[str, str]:
    return {relative(path): hashlib.sha256(outputs[path] if path in outputs else path.read_bytes()).hexdigest() for path in paths}


def corpus(outputs: dict[Path, bytes]) -> bytes:
    fixture = "fixtures/v0.2/signing"
    v01 = "fixtures/minimal-aecctx"
    v02 = "fixtures/v0.2/shared/minimal-v02"
    bundle = lambda name: f"{fixture}/bundles/{name}.json"
    registry_path = lambda name: f"{fixture}/registries/{name}.json"
    policy_path = lambda name: f"{fixture}/policies/{name}.json"

    def entry(case_id: str, operation: str, package: str | None, expected: dict[str, object], **controls: object) -> dict[str, object]:
        value: dict[str, object] = {"case_id": case_id, "operation": operation, "package": package, **controls, "expected": expected}
        configured: list[Path] = []
        for field in ("bundle", "registry", "policy", "comparison_package"):
            item = value.get(field)
            if isinstance(item, str):
                configured.append(ROOT / item)
        if package is not None:
            package_path = ROOT / package
            configured.append(package_path if package_path.is_file() or package_path in outputs else package_path / "manifest.json")
        value["file_sha256"] = file_hashes(configured, outputs)
        return value

    signed = {"signature_presence": "signed", "cryptographic_statuses": ["valid"]}
    entries = [
        entry("unsigned-v01", "verify", v01, {"exit": 1, "signature_presence": "unsigned", "policy_satisfied": False}, registry=registry_path("valid"), policy=policy_path("trust-a"), bundle=None),
        entry("unsigned-v02", "verify", v02, {"exit": 1, "signature_presence": "unsigned", "policy_satisfied": False}, registry=registry_path("valid"), policy=policy_path("trust-a"), bundle=None),
        entry("directory-zip-equivalence", "equivalence", v01, {"exit": 0, "signature_presence": "signed", "policy_satisfied": True, "statement_equal": True}, comparison_package=f"{fixture}/packages/minimal-v01.aecctx", bundle=bundle("valid-a"), registry=registry_path("valid"), policy=policy_path("trust-a")),
        entry("valid-authorized", "verify", v01, {"exit": 0, **signed, "key_statuses": ["valid"], "trust_statuses": ["trusted"], "authorization_statuses": ["authorized"], "policy_satisfied": True}, bundle=bundle("valid-a"), registry=registry_path("valid"), policy=policy_path("trust-a")),
        entry("invalid-signature", "verify", v01, {"exit": 1, "signature_presence": "signed", "cryptographic_statuses": ["invalid"], "policy_satisfied": False}, bundle=bundle("invalid-signature"), registry=registry_path("valid"), policy=policy_path("trust-a")),
        entry("foreign-statement", "verify", f"{fixture}/packages/manifest-mutated", {"exit": 1, "signature_presence": "signed", "cryptographic_statuses": ["invalid"], "diagnostic_codes": ["AECCTX_SIGNING_STATEMENT_BINDING_MISMATCH", "AECCTX_SIGNING_THRESHOLD_NOT_MET"], "policy_satisfied": False}, bundle=bundle("valid-a"), registry=registry_path("valid"), policy=policy_path("trust-a")),
        entry("unknown-key", "verify", v01, {"exit": 1, "signature_presence": "signed", "cryptographic_statuses": ["unknown_key"], "key_statuses": ["not_evaluated"], "policy_satisfied": False}, bundle=bundle("valid-c"), registry=registry_path("a-only"), policy=policy_path("trust-a")),
        entry("unsupported-algorithm", "parse-bundle", None, {"exit": 2, "error_code": "AECCTX_SIGNING_HEADER_INVALID"}, bundle=bundle("unsupported-algorithm")),
        entry("valid-untrusted", "verify", v01, {"exit": 1, **signed, "key_statuses": ["valid"], "trust_statuses": ["untrusted"], "authorization_statuses": ["unauthorized"], "policy_satisfied": False}, bundle=bundle("valid-a"), registry=registry_path("valid"), policy=policy_path("trust-none")),
        entry("trusted-unauthorized", "verify", v01, {"exit": 1, **signed, "key_statuses": ["valid"], "trust_statuses": ["trusted"], "authorization_statuses": ["unauthorized"], "policy_satisfied": False}, bundle=bundle("valid-a"), registry=registry_path("no-scope"), policy=policy_path("trust-a")),
        entry("not-yet-valid", "verify", v01, {"exit": 1, **signed, "key_statuses": ["not_yet_valid"], "policy_satisfied": False}, bundle=bundle("valid-a"), registry=registry_path("not-yet-valid"), policy=policy_path("trust-a")),
        entry("expired", "verify", v01, {"exit": 1, **signed, "key_statuses": ["expired"], "policy_satisfied": False}, bundle=bundle("valid-a"), registry=registry_path("expired"), policy=policy_path("trust-a")),
        entry("revoked", "verify", v01, {"exit": 1, **signed, "key_statuses": ["revoked"], "policy_satisfied": False}, bundle=bundle("valid-a"), registry=registry_path("revoked"), policy=policy_path("trust-a")),
        entry("unknown-status", "verify", v01, {"exit": 1, **signed, "key_statuses": ["unknown_status"], "policy_satisfied": False}, bundle=bundle("valid-a"), registry=registry_path("unknown-status"), policy=policy_path("trust-a")),
        entry("rotation", "verify", v01, {"exit": 0, "signature_presence": "signed", "cryptographic_statuses": ["valid", "valid"], "authorization_statuses": ["authorized", "authorized"], "policy_satisfied": True}, bundle=bundle("multi-ab"), registry=registry_path("valid"), policy=policy_path("trust-ab-2")),
        entry("threshold-1-of-n", "verify", v01, {"exit": 0, "signature_presence": "signed", "policy_satisfied": True, "authorized_kids": ["test-a", "test-b"]}, bundle=bundle("multi-ab"), registry=registry_path("valid"), policy=policy_path("trust-ab-1")),
        entry("threshold-n-of-n", "verify", v01, {"exit": 0, "signature_presence": "signed", "policy_satisfied": True, "authorized_kids": ["test-a", "test-b"]}, bundle=bundle("multi-ab"), registry=registry_path("valid"), policy=policy_path("trust-ab-2")),
        entry("artifact-mutation", "verify", f"{fixture}/packages/artifact-mutated", {"exit": 2, "error_code": "AECCTX_SIGNING_PACKAGE_INVALID"}, bundle=bundle("valid-a"), registry=registry_path("valid"), policy=policy_path("trust-a")),
        entry("manifest-mutation", "verify", f"{fixture}/packages/manifest-mutated", {"exit": 1, "diagnostic_codes": ["AECCTX_SIGNING_STATEMENT_BINDING_MISMATCH", "AECCTX_SIGNING_THRESHOLD_NOT_MET"], "policy_satisfied": False}, bundle=bundle("valid-a"), registry=registry_path("valid"), policy=policy_path("trust-a")),
        entry("header-mutation", "parse-bundle", None, {"exit": 2, "error_code": "AECCTX_SIGNING_HEADER_INVALID"}, bundle=bundle("invalid-header")),
        entry("signature-mutation", "verify", v01, {"exit": 1, "cryptographic_statuses": ["invalid"], "diagnostic_codes": ["AECCTX_SIGNING_SIGNATURE_INVALID", "AECCTX_SIGNING_THRESHOLD_NOT_MET"], "policy_satisfied": False}, bundle=bundle("invalid-signature"), registry=registry_path("valid"), policy=policy_path("trust-a")),
        entry("duplicate-json", "parse-bundle", None, {"exit": 2, "error_code": "AECCTX_SIGNING_JSON_DUPLICATE_KEY"}, bundle=f"{fixture}/adversarial/duplicate-json.json"),
        entry("oversize-input", "parse-bundle", None, {"exit": 2, "error_code": "AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED"}, bundle=f"{fixture}/adversarial/oversize.json"),
        entry("missing-extra", "packaging", v01, {"exit": 2, "error_code": "AECCTX_SIGNING_CRYPTO_UNAVAILABLE"}, bundle=None, registry=registry_path("valid"), policy=policy_path("trust-a")),
    ]
    return canonical_json_nfc({"version": "1", "entries": entries}, terminal_lf=True)


def generated_outputs() -> dict[Path, bytes]:
    outputs = expected_files()
    outputs[ROOT / "conformance" / "v0.2" / "signing-corpus.json"] = corpus(outputs)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    outputs = generated_outputs()
    if arguments.check:
        mismatches = [relative(path) for path, data in outputs.items() if not path.is_file() or path.read_bytes() != data]
        if mismatches:
            print("signing fixture drift: " + ", ".join(mismatches), file=sys.stderr)
            return 1
        print("aecctx signing fixtures: deterministic")
        return 0
    for path, data in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print("aecctx signing fixtures: generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
