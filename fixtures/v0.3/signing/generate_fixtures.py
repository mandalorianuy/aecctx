#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from aecctx._signing_io import base64url_encode, canonical_json_nfc
from aecctx.signing import append_signature, build_signing_statement, sign_package


REPO = Path(__file__).parents[3]
DEFAULT_ROOT = REPO / "fixtures/v0.3/signing"
DEFAULT_CORPUS = REPO / "conformance/v0.3/signing-corpus.json"
PACKAGE = REPO / "fixtures/v0.2/signing/packages/minimal-v01.aecctx"
INSTANT = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)


def der(value: object) -> str:
    return base64.b64encode(value.public_bytes(serialization.Encoding.DER)).decode("ascii")


def certificate(subject, key, issuer_name, issuer_key, issuer_ski, serial, before, after, *, ca=False, eku=None):
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)])
    ski = x509.SubjectKeyIdentifier.from_public_key(key.public_key())
    builder = (
        x509.CertificateBuilder().subject_name(name).issuer_name(issuer_name).public_key(key.public_key())
        .serial_number(serial).not_valid_before(before).not_valid_after(after)
        .add_extension(x509.BasicConstraints(ca=ca, path_length=0 if ca else None), True)
        .add_extension(x509.KeyUsage(not ca, False, False, False, False, ca, ca, False, False), True)
        .add_extension(ski, False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(issuer_ski), False)
    )
    if eku is not None:
        builder = builder.add_extension(x509.ExtendedKeyUsage([eku]), False)
    return builder.sign(issuer_key, None)


def crl(root, root_key, *, revoked_serial=None, stale=False):
    builder = (
        x509.CertificateRevocationListBuilder().issuer_name(root.subject)
        .last_update(INSTANT - timedelta(days=10 if stale else 1))
        .next_update(INSTANT - timedelta(days=1) if stale else INSTANT + timedelta(days=1))
        .add_extension(x509.CRLNumber(1), False)
    )
    if revoked_serial is not None:
        builder = builder.add_revoked_certificate(
            x509.RevokedCertificateBuilder().serial_number(revoked_serial)
            .revocation_date(INSTANT - timedelta(hours=1)).build()
        )
    return builder.sign(root_key, None)


def private_pem(key):
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())


def timestamp(tsa, tsa_key, statement_sha256, *, mutate=False):
    value = {
        "profile": "aecctx-trusted-time-v1", "kid": "test-tsa", "target_kind": "statement",
        "target_sha256": "0" * 64 if mutate else statement_sha256, "gen_time": "2026-07-14T11:00:00Z",
        "tsa_certificate_sha256": tsa.fingerprint(hashes.SHA256()).hex(),
    }
    value["signature"] = base64url_encode(tsa_key.sign(canonical_json_nfc(value, terminal_lf=False)))
    return value


def countersign(tsa_key, entry):
    value = {
        "profile": "aecctx-countersignature-v1", "kid": "test-tsa",
        "target_signature_sha256": hashlib.sha256(canonical_json_nfc(entry, terminal_lf=False)).hexdigest(),
    }
    value["signature"] = base64url_encode(tsa_key.sign(canonical_json_nfc(value, terminal_lf=False)))
    return value


def policy(root, signer, tsa, crls, *, kid, timestamps=(), countersignatures=(), require_time=False):
    return {
        "profile": "aecctx-x509-ed25519-crl-time-v1", "verification_time": "2026-07-14T12:00:00Z",
        "trusted_root_sha256": [root.fingerprint(hashes.SHA256()).hex()],
        "trusted_subjects": ["CN=AECCTX Test Signer"], "authorized_tsa_subjects": ["CN=AECCTX Test TSA"],
        "required_scopes": ["package:approve"], "minimum_authorized_signatures": 1,
        "require_archival_time": require_time, "archival_before": "2026-07-15T00:00:00Z",
        "signers": [{"kid": kid, "chain": [der(signer), der(root)], "scopes": ["package:approve"]}],
        "timestamp_authorities": [{"kid": "test-tsa", "chain": [der(tsa), der(root)]}],
        "crls": [der(item) for item in crls], "timestamps": list(timestamps),
        "countersignatures": list(countersignatures),
    }


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def generate(root_path: Path, corpus_path: Path) -> None:
    generated_directories = ("certificates", "keys", "status", "bundles", "policies", "tokens", "countersignatures")
    for name in generated_directories:
        directory = root_path / name
        if directory.exists():
            shutil.rmtree(directory)
    root_key = Ed25519PrivateKey.from_private_bytes(b"R" * 32)
    signer_key = Ed25519PrivateKey.from_private_bytes(b"S" * 32)
    expired_key = Ed25519PrivateKey.from_private_bytes(b"E" * 32)
    rotated_key = Ed25519PrivateKey.from_private_bytes(b"O" * 32)
    tsa_key = Ed25519PrivateKey.from_private_bytes(b"T" * 32)
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AECCTX Test Root")])
    root_ski = x509.SubjectKeyIdentifier.from_public_key(root_key.public_key())
    root = certificate("AECCTX Test Root", root_key, root_name, root_key, root_ski, 1, INSTANT - timedelta(days=365), INSTANT + timedelta(days=3650), ca=True)
    signer = certificate("AECCTX Test Signer", signer_key, root.subject, root_key, root_ski, 2, INSTANT - timedelta(days=30), INSTANT + timedelta(days=30), eku=ExtendedKeyUsageOID.CLIENT_AUTH)
    expired = certificate("AECCTX Test Signer", expired_key, root.subject, root_key, root_ski, 3, INSTANT - timedelta(days=60), INSTANT - timedelta(days=1), eku=ExtendedKeyUsageOID.CLIENT_AUTH)
    rotated = certificate("AECCTX Test Signer", rotated_key, root.subject, root_key, root_ski, 4, INSTANT - timedelta(days=1), INSTANT + timedelta(days=60), eku=ExtendedKeyUsageOID.CLIENT_AUTH)
    tsa = certificate("AECCTX Test TSA", tsa_key, root.subject, root_key, root_ski, 5, INSTANT - timedelta(days=30), INSTANT + timedelta(days=30), eku=ExtendedKeyUsageOID.TIME_STAMPING)
    good_crl = crl(root, root_key)
    revoked_crl = crl(root, root_key, revoked_serial=signer.serial_number)
    stale_crl = crl(root, root_key, stale=True)
    identities = {"signer": (signer_key, signer), "expired": (expired_key, expired), "rotated": (rotated_key, rotated), "tsa": (tsa_key, tsa)}
    write(root_path / "certificates/root.der", root.public_bytes(serialization.Encoding.DER))
    for name, (key, cert) in identities.items():
        write(root_path / f"keys/test-{name}.pem", private_pem(key))
        write(root_path / f"certificates/{name}.der", cert.public_bytes(serialization.Encoding.DER))
    for name, value in {"good": good_crl, "revoked": revoked_crl, "stale": stale_crl}.items():
        write(root_path / f"status/{name}.crl", value.public_bytes(serialization.Encoding.DER))
    statement = build_signing_statement(PACKAGE)
    bundles = {}
    for name, key, kid in (("valid", signer_key, "test-signer"), ("expired", expired_key, "test-expired"), ("rotated", rotated_key, "test-rotated")):
        bundle = sign_package(PACKAGE, private_key_pem=private_pem(key), kid=kid)
        bundles[name] = bundle
        write(root_path / f"bundles/{name}.json", bundle.to_bytes())
    bundles["multi"] = append_signature(
        PACKAGE, bundles["valid"], private_key_pem=private_pem(rotated_key), kid="test-rotated"
    )
    write(root_path / "bundles/multi.json", bundles["multi"].to_bytes())
    entry = json.loads(bundles["valid"].to_bytes())["signatures"][0]
    good_time = timestamp(tsa, tsa_key, statement.sha256)
    bad_time = timestamp(tsa, tsa_key, statement.sha256, mutate=True)
    counter = countersign(tsa_key, entry)
    policies = {
        "valid": policy(root, signer, tsa, [good_crl], kid="test-signer", timestamps=[good_time], countersignatures=[counter], require_time=True),
        "revoked": policy(root, signer, tsa, [revoked_crl], kid="test-signer"),
        "stale": policy(root, signer, tsa, [stale_crl], kid="test-signer"),
        "unknown": policy(root, signer, tsa, [], kid="test-signer"),
        "expired": policy(root, expired, tsa, [good_crl], kid="test-expired"),
        "rotated": policy(root, rotated, tsa, [good_crl], kid="test-rotated"),
        "mutated-time": policy(root, signer, tsa, [good_crl], kid="test-signer", timestamps=[bad_time], require_time=True),
    }
    multi_policy = policy(root, signer, tsa, [good_crl], kid="test-signer")
    multi_policy["signers"].append({"kid": "test-rotated", "chain": [der(rotated), der(root)], "scopes": ["package:approve"]})
    multi_policy["minimum_authorized_signatures"] = 2
    policies["multi"] = multi_policy
    for name, value in policies.items():
        write(root_path / f"policies/{name}.json", canonical_json_nfc(value, terminal_lf=True))
    write(root_path / "tokens/valid.json", canonical_json_nfc(good_time, terminal_lf=True))
    write(root_path / "tokens/mutated.json", canonical_json_nfc(bad_time, terminal_lf=True))
    write(root_path / "countersignatures/valid.json", canonical_json_nfc(counter, terminal_lf=True))
    files = []
    generated_files = (
        item for name in generated_directories for item in (root_path / name).rglob("*") if item.is_file()
    )
    for path in sorted(generated_files):
        logical = Path("fixtures/v0.3/signing") / path.relative_to(root_path)
        files.append({"path": logical.as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    cases = [
        {"id": "valid-trusted-time-counter", "bundle": "bundles/valid.json", "policy": "policies/valid.json", "policy_satisfied": True, "lifecycle": "valid", "archival": "valid"},
        {"id": "revoked", "bundle": "bundles/valid.json", "policy": "policies/revoked.json", "policy_satisfied": False, "lifecycle": "revoked", "archival": "absent"},
        {"id": "stale", "bundle": "bundles/valid.json", "policy": "policies/stale.json", "policy_satisfied": False, "lifecycle": "unknown_status", "archival": "absent"},
        {"id": "unknown", "bundle": "bundles/valid.json", "policy": "policies/unknown.json", "policy_satisfied": False, "lifecycle": "unknown_status", "archival": "absent"},
        {"id": "expired", "bundle": "bundles/expired.json", "policy": "policies/expired.json", "policy_satisfied": False, "lifecycle": "expired", "archival": "absent"},
        {"id": "rotated", "bundle": "bundles/rotated.json", "policy": "policies/rotated.json", "policy_satisfied": True, "lifecycle": "valid", "archival": "absent"},
        {"id": "mutated-time", "bundle": "bundles/valid.json", "policy": "policies/mutated-time.json", "policy_satisfied": False, "lifecycle": "valid", "archival": "invalid"},
        {"id": "multi-two-of-two", "bundle": "bundles/multi.json", "policy": "policies/multi.json", "policy_satisfied": True, "lifecycle": "valid", "archival": "absent"},
    ]
    corpus = {"corpus_version": "1", "fixture_id": "v03-signing-acx35", "profile": "aecctx-x509-ed25519-crl-time-v1", "files": files, "cases": cases}
    write(corpus_path, canonical_json_nfc(corpus, terminal_lf=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        generate(DEFAULT_ROOT, DEFAULT_CORPUS)
        print("aecctx v0.3 signing fixtures: generated")
        return 0
    with tempfile.TemporaryDirectory() as temporary:
        candidate_root = Path(temporary) / "signing"
        candidate_corpus = Path(temporary) / "signing-corpus.json"
        generate(candidate_root, candidate_corpus)
        for candidate in sorted(item for item in candidate_root.rglob("*") if item.is_file()):
            relative = candidate.relative_to(candidate_root)
            committed = DEFAULT_ROOT / relative
            if not committed.is_file() or committed.read_bytes() != candidate.read_bytes():
                raise SystemExit(f"fixture drift: {relative.as_posix()}")
        candidate_value = json.loads(candidate_corpus.read_bytes())
        committed_value = json.loads(DEFAULT_CORPUS.read_bytes())
        if candidate_value["cases"] != committed_value["cases"] or candidate_value["profile"] != committed_value["profile"]:
            raise SystemExit("signing corpus semantic drift")
        expected_hashes = {Path(item["path"]).relative_to("fixtures/v0.3/signing").as_posix(): item["sha256"] for item in committed_value["files"]}
        actual_hashes = {path.relative_to(candidate_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in candidate_root.rglob("*") if path.is_file()}
        if expected_hashes != actual_hashes:
            raise SystemExit("signing corpus hash drift")
    print("aecctx v0.3 signing fixtures: deterministic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
