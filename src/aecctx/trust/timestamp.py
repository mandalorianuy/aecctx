from __future__ import annotations

from datetime import datetime
from typing import Any

from .._signing_crypto import verify_bytes
from .._signing_io import base64url_decode, canonical_json_nfc
from .status import evaluate_crls
from .x509 import evaluate_chain


def evaluate_timestamp(
    token: dict[str, Any], *, statement_sha256: str, authority: dict[str, Any] | None,
    roots: set[str], crls: list[str], archival_before: datetime, authorized_subjects: set[str],
) -> tuple[str, tuple[str, ...]]:
    try:
        from cryptography.x509.oid import ExtendedKeyUsageOID
    except ImportError as error:
        raise RuntimeError("AECCTX_TRUST_DEPENDENCY_UNAVAILABLE") from error
    required = {"profile", "kid", "target_kind", "target_sha256", "gen_time", "tsa_certificate_sha256", "signature"}
    if set(token) != required or token.get("profile") != "aecctx-trusted-time-v1" or token.get("target_kind") != "statement":
        return "invalid", ("AECCTX_TRUST_TIMESTAMP_MALFORMED",)
    if authority is None:
        return "untrusted", ("AECCTX_TRUST_TIMESTAMP_AUTHORITY_UNKNOWN",)
    try:
        if not str(token["gen_time"]).endswith("Z"):
            raise ValueError
        gen_time = datetime.fromisoformat(str(token["gen_time"]).replace("Z", "+00:00"))
    except ValueError:
        return "invalid", ("AECCTX_TRUST_TIMESTAMP_MALFORMED",)
    chain = evaluate_chain(authority["chain"], roots, gen_time, ExtendedKeyUsageOID.TIME_STAMPING)
    if not chain.valid or not chain.trusted or chain.subject not in authorized_subjects or chain.fingerprint != token["tsa_certificate_sha256"]:
        return "untrusted", chain.diagnostics + ("AECCTX_TRUST_TIMESTAMP_AUTHORITY_UNTRUSTED",)
    status, codes = evaluate_crls(chain.leaf, chain.issuer, crls, gen_time)
    if status != "good":
        return "untrusted", codes
    unsigned = {key: token[key] for key in sorted(token) if key != "signature"}
    signature = base64url_decode(token["signature"], expected_bytes=64)
    if token["target_sha256"] != statement_sha256 or not verify_bytes(chain.leaf.public_key(), signature, canonical_json_nfc(unsigned, terminal_lf=False)):
        return "invalid", ("AECCTX_TRUST_TIMESTAMP_INVALID",)
    if gen_time >= archival_before:
        return "outside_policy", ("AECCTX_TRUST_TIMESTAMP_OUTSIDE_POLICY",)
    return "valid", ()
