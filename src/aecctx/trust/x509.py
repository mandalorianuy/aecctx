from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ChainEvaluation:
    leaf: Any
    issuer: Any | None
    subject: str | None
    fingerprint: str | None
    lifecycle: str
    trusted: bool
    valid: bool
    diagnostics: tuple[str, ...]


def load_der(value: str, loader: Any) -> Any:
    try:
        raw = base64.b64decode(value, validate=True)
        if len(raw) > 1_048_576:
            raise ValueError
        return loader(raw)
    except (ValueError, TypeError) as error:
        raise ValueError("invalid bounded DER input") from error


def evaluate_chain(
    encoded_chain: list[str], trusted_roots: set[str], instant: datetime, expected_eku: Any
) -> ChainEvaluation:
    try:
        from cryptography import x509
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.x509.oid import ExtensionOID
    except ImportError as error:
        raise RuntimeError("AECCTX_TRUST_DEPENDENCY_UNAVAILABLE") from error
    diagnostics: list[str] = []
    if not 2 <= len(encoded_chain) <= 3:
        return ChainEvaluation(None, None, None, None, "not_evaluated", False, False, ("AECCTX_TRUST_CHAIN_LENGTH_INVALID",))
    try:
        chain = [load_der(value, x509.load_der_x509_certificate) for value in encoded_chain]
    except ValueError:
        return ChainEvaluation(None, None, None, None, "not_evaluated", False, False, ("AECCTX_TRUST_CERTIFICATE_MALFORMED",))
    leaf, root = chain[0], chain[-1]
    subject = leaf.subject.rfc4514_string()
    fingerprint = leaf.fingerprint(hashes.SHA256()).hex()
    lifecycle = "valid"
    if instant < leaf.not_valid_before_utc:
        lifecycle = "not_yet_valid"
        diagnostics.append("AECCTX_TRUST_CERTIFICATE_NOT_YET_VALID")
    elif instant >= leaf.not_valid_after_utc:
        lifecycle = "expired"
        diagnostics.append("AECCTX_TRUST_CERTIFICATE_EXPIRED")
    try:
        public_key = leaf.public_key()
        if not isinstance(public_key, Ed25519PublicKey):
            raise ValueError("leaf algorithm")
        eku = leaf.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE).value
        if expected_eku not in eku:
            raise ValueError("leaf eku")
        leaf_constraints = leaf.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS).value
        if leaf_constraints.ca:
            raise ValueError("leaf constraints")
        for index, certificate in enumerate(chain):
            issuer = chain[index + 1] if index + 1 < len(chain) else certificate
            if certificate.issuer != issuer.subject:
                raise ValueError("issuer mismatch")
            issuer_key = issuer.public_key()
            if not isinstance(issuer_key, Ed25519PublicKey):
                raise ValueError("issuer algorithm")
            issuer_key.verify(certificate.signature, certificate.tbs_certificate_bytes)
            if index > 0:
                constraints = certificate.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS).value
                usage = certificate.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE).value
                if not constraints.ca or not usage.key_cert_sign:
                    raise ValueError("ca constraints")
                ca_below = sum(
                    1 for lower in chain[1:index]
                    if lower.extensions.get_extension_for_oid(ExtensionOID.BASIC_CONSTRAINTS).value.ca
                )
                if constraints.path_length is not None and ca_below > constraints.path_length:
                    raise ValueError("path length")
                if instant < certificate.not_valid_before_utc or instant >= certificate.not_valid_after_utc:
                    raise ValueError("ca lifecycle")
    except (ValueError, x509.ExtensionNotFound, InvalidSignature):
        diagnostics.append("AECCTX_TRUST_CHAIN_INVALID")
        return ChainEvaluation(leaf, chain[1], subject, fingerprint, lifecycle, False, False, tuple(diagnostics))
    root_fingerprint = root.fingerprint(hashes.SHA256()).hex()
    trusted = root_fingerprint in trusted_roots
    if not trusted:
        diagnostics.append("AECCTX_TRUST_ROOT_UNTRUSTED")
    return ChainEvaluation(leaf, chain[1], subject, fingerprint, lifecycle, trusted, True, tuple(diagnostics))
