from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from aecctx._signing_io import base64url_encode, canonical_json_nfc
from aecctx.signing import build_signing_statement, sign_package


ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "fixtures/v0.2/signing/packages/minimal-v01.aecctx"


def _der(value: object) -> str:
    return base64.b64encode(value.public_bytes(serialization.Encoding.DER)).decode("ascii")


def _certificate(
    *,
    subject: str,
    key: Ed25519PrivateKey,
    issuer_name: x509.Name,
    issuer_key: Ed25519PrivateKey,
    issuer_ski: x509.SubjectKeyIdentifier,
    serial: int,
    not_before: datetime,
    not_after: datetime,
    ca: bool,
    eku: x509.ObjectIdentifier | None = None,
) -> x509.Certificate:
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)])
    ski = x509.SubjectKeyIdentifier.from_public_key(key.public_key())
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(issuer_name)
        .public_key(key.public_key())
        .serial_number(serial)
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=ca, path_length=0 if ca else None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=not ca,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=ca,
                crl_sign=ca,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(ski, critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(issuer_ski), critical=False)
    )
    if eku is not None:
        builder = builder.add_extension(x509.ExtendedKeyUsage([eku]), critical=False)
    return builder.sign(issuer_key, algorithm=None)


def _pki(*, revoked: bool = False, stale: bool = False) -> dict[str, object]:
    instant = datetime(2026, 7, 14, 12, tzinfo=timezone.utc)
    root_key = Ed25519PrivateKey.from_private_bytes(b"R" * 32)
    signer_key = Ed25519PrivateKey.from_private_bytes(b"S" * 32)
    tsa_key = Ed25519PrivateKey.from_private_bytes(b"T" * 32)
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AECCTX Test Root")])
    root_ski = x509.SubjectKeyIdentifier.from_public_key(root_key.public_key())
    root = _certificate(
        subject="AECCTX Test Root", key=root_key, issuer_name=root_name, issuer_key=root_key,
        issuer_ski=root_ski, serial=1, not_before=instant - timedelta(days=365),
        not_after=instant + timedelta(days=3650), ca=True,
    )
    signer = _certificate(
        subject="AECCTX Test Signer", key=signer_key, issuer_name=root.subject, issuer_key=root_key,
        issuer_ski=root_ski, serial=2, not_before=instant - timedelta(days=30),
        not_after=instant + timedelta(days=30), ca=False, eku=ExtendedKeyUsageOID.CLIENT_AUTH,
    )
    tsa = _certificate(
        subject="AECCTX Test TSA", key=tsa_key, issuer_name=root.subject, issuer_key=root_key,
        issuer_ski=root_ski, serial=3, not_before=instant - timedelta(days=30),
        not_after=instant + timedelta(days=30), ca=False, eku=ExtendedKeyUsageOID.TIME_STAMPING,
    )
    crl_builder = (
        x509.CertificateRevocationListBuilder()
        .issuer_name(root.subject)
        .last_update(instant - timedelta(days=10 if stale else 1))
        .next_update(instant - timedelta(days=1) if stale else instant + timedelta(days=1))
        .add_extension(x509.CRLNumber(1), critical=False)
    )
    if revoked:
        crl_builder = crl_builder.add_revoked_certificate(
            x509.RevokedCertificateBuilder().serial_number(signer.serial_number)
            .revocation_date(instant - timedelta(hours=1)).build()
        )
    crl = crl_builder.sign(root_key, algorithm=None)
    return {"instant": instant, "root": root, "signer": signer, "tsa": tsa, "signer_key": signer_key, "tsa_key": tsa_key, "crl": crl}


def _policy(pki: dict[str, object], *, timestamp: dict[str, object] | None = None, countersignature: dict[str, object] | None = None) -> bytes:
    root = pki["root"]
    value = {
        "profile": "aecctx-x509-ed25519-crl-time-v1",
        "verification_time": pki["instant"].isoformat().replace("+00:00", "Z"),
        "trusted_root_sha256": [root.fingerprint(hashlib_to_crypto()).hex()],
        "trusted_subjects": ["CN=AECCTX Test Signer"],
        "authorized_tsa_subjects": ["CN=AECCTX Test TSA"],
        "required_scopes": ["package:approve"],
        "minimum_authorized_signatures": 1,
        "require_archival_time": True,
        "archival_before": "2026-07-15T00:00:00Z",
        "signers": [{"kid": "test-signer", "chain": [_der(pki["signer"]), _der(root)], "scopes": ["package:approve"]}],
        "timestamp_authorities": [{"kid": "test-tsa", "chain": [_der(pki["tsa"]), _der(root)]}],
        "crls": [_der(pki["crl"])],
        "timestamps": [] if timestamp is None else [timestamp],
        "countersignatures": [] if countersignature is None else [countersignature],
    }
    return canonical_json_nfc(value, terminal_lf=True)


def hashlib_to_crypto():
    from cryptography.hazmat.primitives import hashes
    return hashes.SHA256()


def _signed_inputs(pki: dict[str, object]):
    private = pki["signer_key"].private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    bundle = sign_package(PACKAGE, private_key_pem=private, kid="test-signer")
    return bundle, build_signing_statement(PACKAGE)


def _timestamp(pki: dict[str, object], target_sha256: str) -> dict[str, object]:
    value = {
        "profile": "aecctx-trusted-time-v1", "kid": "test-tsa", "target_kind": "statement",
        "target_sha256": target_sha256, "gen_time": "2026-07-14T11:00:00Z",
        "tsa_certificate_sha256": pki["tsa"].fingerprint(hashlib_to_crypto()).hex(),
    }
    value["signature"] = base64url_encode(pki["tsa_key"].sign(canonical_json_nfc(value, terminal_lf=False)))
    return value


def _countersignature(pki: dict[str, object], target: dict[str, str]) -> dict[str, object]:
    value = {
        "profile": "aecctx-countersignature-v1", "kid": "test-tsa",
        "target_signature_sha256": hashlib.sha256(canonical_json_nfc(target, terminal_lf=False)).hexdigest(),
    }
    value["signature"] = base64url_encode(pki["tsa_key"].sign(canonical_json_nfc(value, terminal_lf=False)))
    return value


def test_v03_schemas_are_closed_and_packaged_mirrors_match() -> None:
    names = {
        "signing-v2-policy.schema.json", "x509-chain-result.schema.json", "certificate-status-result.schema.json",
        "timestamp-result.schema.json", "countersignature-result.schema.json", "advanced-trust-result.schema.json",
    }
    for name in names:
        public = (ROOT / "schemas/v0.2" / name).read_bytes()
        assert public == (ROOT / "src/aecctx/schemas/v0_2" / name).read_bytes()
        assert json.loads(public)["additionalProperties"] is False


def test_advanced_trust_keeps_all_axes_separate_and_accepts_fresh_crl_time_and_counter_signature() -> None:
    from aecctx.trust import evaluate_advanced_trust

    pki = _pki()
    bundle, statement = _signed_inputs(pki)
    target = json.loads(bundle.to_bytes())["signatures"][0]
    policy = _policy(pki, timestamp=_timestamp(pki, statement.sha256), countersignature=_countersignature(pki, target))
    result = evaluate_advanced_trust(PACKAGE, bundle.to_bytes(), policy)
    assert result["package_integrity"] == "valid"
    assert result["policy_satisfied"] is True
    assert result["signatures"][0] == {
        "kid": "test-signer", "integrity_status": "valid", "cryptographic_status": "valid",
        "identity_status": "resolved", "lifecycle_status": "valid", "trust_status": "trusted",
        "authorization_status": "authorized", "archival_time_status": "valid", "subject": "CN=AECCTX Test Signer",
        "diagnostic_codes": [],
    }
    assert result["countersignatures"][0]["cryptographic_status"] == "valid"
    assert result["countersignatures"][0]["counts_toward_threshold"] is False


@pytest.mark.parametrize(
    ("pki_args", "lifecycle", "code"),
    [({"revoked": True}, "revoked", "AECCTX_TRUST_CERTIFICATE_REVOKED"), ({"stale": True}, "unknown_status", "AECCTX_TRUST_CRL_STALE")],
)
def test_revoked_and_stale_status_never_authorize(pki_args: dict[str, bool], lifecycle: str, code: str) -> None:
    from aecctx.trust import evaluate_advanced_trust

    pki = _pki(**pki_args)
    bundle, _ = _signed_inputs(pki)
    result = evaluate_advanced_trust(PACKAGE, bundle.to_bytes(), _policy(pki))
    signer = result["signatures"][0]
    assert signer["cryptographic_status"] == "valid"
    assert signer["lifecycle_status"] == lifecycle
    assert signer["authorization_status"] == "unauthorized"
    assert code in signer["diagnostic_codes"]
    assert result["policy_satisfied"] is False


def test_algorithm_confusion_timestamp_mutation_and_unknown_status_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from aecctx.trust import TrustError, evaluate_advanced_trust

    pki = _pki()
    bundle, statement = _signed_inputs(pki)
    token = _timestamp(pki, statement.sha256)
    token["target_sha256"] = "0" * 64
    result = evaluate_advanced_trust(PACKAGE, bundle.to_bytes(), _policy(pki, timestamp=token))
    assert result["signatures"][0]["archival_time_status"] == "invalid"
    assert result["policy_satisfied"] is False
    malformed = json.loads(_policy(pki))
    malformed["algorithm"] = "none"
    with pytest.raises(TrustError, match="closed schema"):
        evaluate_advanced_trust(PACKAGE, bundle.to_bytes(), canonical_json_nfc(malformed, terminal_lf=True))


def test_cli_advanced_trust_is_offline_and_matches_sdk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import socket
    from aecctx.cli import main

    pki = _pki()
    bundle, statement = _signed_inputs(pki)
    bundle_path = tmp_path / "bundle.json"
    policy_path = tmp_path / "policy.json"
    bundle_path.write_bytes(bundle.to_bytes())
    policy_path.write_bytes(_policy(pki, timestamp=_timestamp(pki, statement.sha256)))
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: pytest.fail("network attempted"))
    assert main(["verify-advanced-trust", str(PACKAGE), "--signature-bundle", str(bundle_path), "--policy", str(policy_path), "--json"]) == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["ok"] is True
    assert envelope["data"]["policy_satisfied"] is True


def test_v03_publishable_corpus_replays_and_fixtures_are_deterministic() -> None:
    fixture_check = subprocess.run(
        [sys.executable, "fixtures/v0.3/signing/generate_fixtures.py", "--check"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert fixture_check.returncode == 0, fixture_check.stdout + fixture_check.stderr
    assert fixture_check.stdout == "aecctx v0.3 signing fixtures: deterministic\n"
    conformance = subprocess.run(
        [sys.executable, "scripts/check_signing_v03_conformance.py"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert conformance.returncode == 0, conformance.stdout + conformance.stderr
    report = json.loads(conformance.stdout)
    assert report["ok"] is True
    assert report["case_count"] == 8


def test_advanced_trust_module_is_lazy_and_uses_the_existing_optional_signing_extra() -> None:
    source = (ROOT / "src/aecctx/trust/__init__.py").read_text(encoding="utf-8")
    assert "from cryptography" not in source.split("def evaluate_advanced_trust", 1)[0]
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'signing = ["cryptography>=45,<50"]' in pyproject
    assert "asn1crypto" not in pyproject
