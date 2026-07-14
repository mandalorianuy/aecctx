from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .._signing_crypto import verify_bytes
from .._signing_io import base64url_decode, base64url_encode, canonical_json_nfc, load_strict_json
from ..signing import SigningError, build_signing_statement, parse_signature_bundle
from .status import evaluate_crls
from .timestamp import evaluate_timestamp
from .x509 import evaluate_chain


class TrustError(SigningError):
    code = "AECCTX_TRUST_POLICY_INVALID"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(code or self.code, message)


def _schema() -> dict[str, Any]:
    from importlib.resources import files
    return load_strict_json(files("aecctx.schemas.v0_2").joinpath("signing-v2-policy.schema.json").read_bytes(), label="advanced trust schema", max_bytes=1_048_576)


def _result_schema() -> dict[str, Any]:
    from importlib.resources import files
    return load_strict_json(files("aecctx.schemas.v0_2").joinpath("advanced-trust-result.schema.json").read_bytes(), label="advanced trust result schema", max_bytes=1_048_576)


def _parse_policy(data: bytes) -> dict[str, Any]:
    value = load_strict_json(data, label="advanced trust policy", max_bytes=1_048_576)
    errors = sorted(Draft202012Validator(_schema()).iter_errors(value), key=lambda item: list(item.absolute_path))
    if errors:
        raise TrustError("advanced trust policy violates the closed schema")
    for field in ("signers", "timestamp_authorities"):
        kids = [item["kid"] for item in value[field]]
        if len(kids) != len(set(kids)):
            raise TrustError(f"advanced trust policy duplicates {field} kid")
    counter_targets = [(item["kid"], item["target_signature_sha256"]) for item in value["countersignatures"]]
    if len(counter_targets) != len(set(counter_targets)):
        raise TrustError("advanced trust policy duplicates a countersignature relationship")
    return value


def _instant(value: str) -> datetime:
    if not value.endswith("Z"):
        raise TrustError("advanced trust policy requires an explicit UTC Z instant")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise TrustError("advanced trust policy has invalid UTC time") from error


def evaluate_advanced_trust(package: str | Path, bundle_bytes: bytes, policy_bytes: bytes) -> dict[str, Any]:
    try:
        from cryptography.x509.oid import ExtendedKeyUsageOID
    except ImportError as error:
        raise TrustError("install aecctx[signing]", code="AECCTX_TRUST_DEPENDENCY_UNAVAILABLE") from error
    policy = _parse_policy(policy_bytes)
    bundle = parse_signature_bundle(bundle_bytes)
    statement = build_signing_statement(package)
    instant = _instant(policy["verification_time"])
    archival_before = _instant(policy["archival_before"])
    roots = set(policy["trusted_root_sha256"])
    crls = policy["crls"]
    signers = {item["kid"]: item for item in policy["signers"]}
    authorities = {item["kid"]: item for item in policy["timestamp_authorities"]}
    timestamps = policy["timestamps"]
    encoded_statement = base64url_encode(statement.canonical_bytes)
    signature_results: list[dict[str, Any]] = []
    authorized = 0
    for entry in bundle.signatures:
        config = signers.get(entry.kid)
        codes: list[str] = []
        if config is None:
            signature_results.append({
                "kid": entry.kid, "integrity_status": "valid", "cryptographic_status": "invalid",
                "identity_status": "unresolved", "lifecycle_status": "not_evaluated", "trust_status": "not_evaluated",
                "authorization_status": "not_evaluated", "archival_time_status": "not_evaluated", "subject": None,
                "diagnostic_codes": ["AECCTX_TRUST_SIGNER_UNKNOWN"],
            })
            continue
        chain = evaluate_chain(config["chain"], roots, instant, ExtendedKeyUsageOID.CLIENT_AUTH)
        codes.extend(chain.diagnostics)
        crypto = "invalid"
        if chain.valid and entry.statement_sha256 == statement.sha256:
            try:
                signature = base64url_decode(entry.signature, expected_bytes=64)
                signing_input = f"{entry.protected}.{encoded_statement}".encode("ascii")
                crypto = "valid" if verify_bytes(chain.leaf.public_key(), signature, signing_input) else "invalid"
            except ValueError:
                crypto = "malformed"
        if crypto != "valid":
            codes.append("AECCTX_TRUST_SIGNATURE_INVALID")
        lifecycle = chain.lifecycle
        if chain.valid and chain.issuer is not None and lifecycle == "valid":
            status, status_codes = evaluate_crls(chain.leaf, chain.issuer, crls, instant)
            codes.extend(status_codes)
            if status != "good":
                lifecycle = status
        trust = "trusted" if chain.valid and chain.trusted else "untrusted"
        subject_allowed = chain.subject in policy["trusted_subjects"]
        scopes_allowed = set(policy["required_scopes"]).issubset(config["scopes"])
        is_authorized = crypto == "valid" and lifecycle == "valid" and trust == "trusted" and subject_allowed and scopes_allowed
        authorization = "authorized" if is_authorized else "unauthorized"
        if not is_authorized:
            codes.append("AECCTX_TRUST_SIGNER_UNAUTHORIZED")
        signer_tokens = [item for item in timestamps if item.get("target_kind") == "statement"]
        archival = "absent"
        for token in signer_tokens:
            archival, timestamp_codes = evaluate_timestamp(
                token, statement_sha256=statement.sha256, authority=authorities.get(token.get("kid")),
                roots=roots, crls=crls, archival_before=archival_before,
                authorized_subjects=set(policy["authorized_tsa_subjects"]),
            )
            codes.extend(timestamp_codes)
            if archival == "valid":
                break
        if is_authorized:
            authorized += 1
        signature_results.append({
            "kid": entry.kid, "integrity_status": "valid", "cryptographic_status": crypto,
            "identity_status": "resolved" if chain.subject else "unresolved", "lifecycle_status": lifecycle,
            "trust_status": trust, "authorization_status": authorization, "archival_time_status": archival,
            "subject": chain.subject, "diagnostic_codes": sorted(set(codes)),
        })
    counter_results = _evaluate_countersignatures(policy["countersignatures"], bundle, authorities, roots, crls, instant)
    threshold_satisfied = authorized >= policy["minimum_authorized_signatures"]
    archival_satisfied = any(
        item["authorization_status"] == "authorized" and item["archival_time_status"] == "valid"
        for item in signature_results
    )
    result = {
        "profile": policy["profile"], "package_integrity": "valid", "statement_sha256": statement.sha256,
        "policy_satisfied": threshold_satisfied and (archival_satisfied or not policy["require_archival_time"]),
        "minimum_authorized_signatures": policy["minimum_authorized_signatures"],
        "authorized_signature_count": authorized, "signatures": signature_results,
        "timestamps": [{"kid": item["kid"], "target_sha256": item["target_sha256"]} for item in timestamps],
        "countersignatures": counter_results,
    }
    errors = list(Draft202012Validator(_result_schema()).iter_errors(result))
    if errors:
        raise TrustError("advanced trust result violates its closed schema")
    return result


def _evaluate_countersignatures(values, bundle, authorities, roots, crls, instant):
    try:
        from cryptography.x509.oid import ExtendedKeyUsageOID
    except ImportError as error:
        raise TrustError("AECCTX_TRUST_DEPENDENCY_UNAVAILABLE") from error
    targets = {
        hashlib.sha256(canonical_json_nfc({"protected": item.protected, "signature": item.signature}, terminal_lf=False)).hexdigest(): item.kid
        for item in bundle.signatures
    }
    results = []
    for value in values:
        required = {"profile", "kid", "target_signature_sha256", "signature"}
        target = value.get("target_signature_sha256")
        valid = (
            set(value) == required
            and value.get("profile") == "aecctx-countersignature-v1"
            and target in targets
            and value.get("kid") != targets.get(target)
        )
        authority = authorities.get(value.get("kid"))
        chain = evaluate_chain(authority["chain"], roots, instant, ExtendedKeyUsageOID.TIME_STAMPING) if authority else None
        if valid and chain and chain.valid and chain.trusted:
            status, _ = evaluate_crls(chain.leaf, chain.issuer, crls, instant)
            unsigned = {key: value[key] for key in sorted(value) if key != "signature"}
            try:
                valid = status == "good" and verify_bytes(chain.leaf.public_key(), base64url_decode(value["signature"], expected_bytes=64), canonical_json_nfc(unsigned, terminal_lf=False))
            except ValueError:
                valid = False
        else:
            valid = False
        results.append({
            "kid": value.get("kid"), "target_signature_sha256": value.get("target_signature_sha256"),
            "cryptographic_status": "valid" if valid else "invalid", "counts_toward_threshold": False,
        })
    return results


__all__ = ["TrustError", "evaluate_advanced_trust"]
