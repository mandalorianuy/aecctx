from __future__ import annotations

from datetime import datetime
from typing import Any

from .x509 import load_der


def evaluate_crls(leaf: Any, issuer: Any, encoded_crls: list[str], instant: datetime) -> tuple[str, tuple[str, ...]]:
    try:
        from cryptography import x509
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.x509.oid import ExtensionOID
    except ImportError as error:
        raise RuntimeError("AECCTX_TRUST_DEPENDENCY_UNAVAILABLE") from error
    matching = []
    for encoded in encoded_crls:
        try:
            crl = load_der(encoded, x509.load_der_x509_crl)
            if crl.issuer != issuer.subject:
                continue
            try:
                crl.extensions.get_extension_for_oid(ExtensionOID.DELTA_CRL_INDICATOR)
            except x509.ExtensionNotFound:
                pass
            else:
                continue
            try:
                issuing = crl.extensions.get_extension_for_oid(ExtensionOID.ISSUING_DISTRIBUTION_POINT).value
            except x509.ExtensionNotFound:
                pass
            else:
                if issuing.indirect_crl:
                    continue
            key = issuer.public_key()
            if not isinstance(key, Ed25519PublicKey):
                continue
            key.verify(crl.signature, crl.tbs_certlist_bytes)
            matching.append(crl)
        except (ValueError, InvalidSignature):
            continue
    if not matching:
        return "unknown_status", ("AECCTX_TRUST_STATUS_UNKNOWN",)
    crl = max(matching, key=lambda item: item.last_update_utc)
    if crl.next_update_utc is None or instant < crl.last_update_utc or instant >= crl.next_update_utc:
        return "unknown_status", ("AECCTX_TRUST_CRL_STALE",)
    revoked = crl.get_revoked_certificate_by_serial_number(leaf.serial_number)
    if revoked is not None and revoked.revocation_date_utc <= instant:
        return "revoked", ("AECCTX_TRUST_CERTIFICATE_REVOKED",)
    return "good", ()
