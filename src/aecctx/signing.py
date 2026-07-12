from __future__ import annotations

import json
import hashlib
import unicodedata
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from .errors import AECCTXError, Diagnostic
from .package import PackageReadError, PackageReader
from .validation import validate_package


SIGNING_SCHEMA_NAMES = frozenset(
    {
        "signature-bundle.schema.json",
        "signing-key-registry.schema.json",
        "signing-trust-policy.schema.json",
        "signature-verification-result.schema.json",
    }
)
CRYPTOGRAPHIC_STATUSES = frozenset({"valid", "invalid", "malformed", "unknown_key", "unsupported_algorithm"})
IDENTITY_STATUSES = frozenset({"resolved", "unresolved"})
KEY_STATUSES = frozenset({"valid", "not_yet_valid", "expired", "revoked", "unknown_status", "not_evaluated"})
TRUST_STATUSES = frozenset({"trusted", "untrusted", "not_evaluated"})
AUTHORIZATION_STATUSES = frozenset({"authorized", "unauthorized", "not_evaluated"})
REVOCATION_STATUSES = frozenset({"good", "revoked", "unknown"})
SIGNING_ALGORITHMS = frozenset({"Ed25519"})


class SigningError(AECCTXError):
    code = "AECCTX_SIGNING_ERROR"

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _require_state(field: str, value: str, allowed: frozenset[str]) -> None:
    if value not in allowed:
        raise ValueError(f"{field} has an ungoverned value: {value!r}")


def _freeze(value: Any) -> Any:
    if isinstance(value, MappingABC):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class SigningLimits:
    max_document_bytes: int = 1_048_576
    max_signatures: int = 64
    max_keys: int = 1_024
    max_private_key_bytes: int = 65_536
    max_password_bytes: int = 4_096

    def __post_init__(self) -> None:
        for field in self.__dataclass_fields__:
            if getattr(self, field) <= 0:
                raise ValueError(f"{field} must be positive")


@dataclass(frozen=True, slots=True)
class SigningStatement:
    data: Mapping[str, Any]
    canonical_bytes: bytes
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _freeze(self.data))


@dataclass(frozen=True, slots=True)
class SignatureEntry:
    protected: str
    signature: str
    kid: str
    algorithm: str
    statement_sha256: str


@dataclass(frozen=True, slots=True)
class SignatureBundle:
    signatures: tuple[SignatureEntry, ...]

    def __post_init__(self) -> None:
        ordered = tuple(sorted(self.signatures, key=lambda item: (item.kid, item.protected, item.signature)))
        object.__setattr__(self, "signatures", ordered)

    def to_bytes(self) -> bytes:
        from ._signing_io import canonical_json_nfc

        value = {
            "signatures": [
                {"protected": entry.protected, "signature": entry.signature}
                for entry in self.signatures
            ]
        }
        return canonical_json_nfc(value, terminal_lf=True)


@dataclass(frozen=True, slots=True)
class SigningKey:
    kid: str
    public_key_x: str
    subject: str
    valid_from: str
    valid_until: str
    revocation_status: str
    revoked_at: str | None
    scopes: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_state("revocation_status", self.revocation_status, REVOCATION_STATUSES)


@dataclass(frozen=True, slots=True)
class KeyRegistry:
    keys: tuple[SigningKey, ...]


@dataclass(frozen=True, slots=True)
class TrustPolicy:
    verification_time: str
    allowed_algorithms: tuple[str, ...]
    trusted_kids: tuple[str, ...]
    trusted_subjects: tuple[str, ...]
    required_scopes: tuple[str, ...]
    minimum_authorized_signatures: int

    def __post_init__(self) -> None:
        if not self.allowed_algorithms or any(item not in SIGNING_ALGORITHMS for item in self.allowed_algorithms):
            raise ValueError("allowed_algorithms contains an unsupported value")


@dataclass(frozen=True, slots=True)
class SignatureVerification:
    kid: str
    algorithm: str
    subject: str | None
    cryptographic_status: str
    identity_status: str
    key_status: str
    trust_status: str
    authorization_status: str
    diagnostic_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_state("cryptographic_status", self.cryptographic_status, CRYPTOGRAPHIC_STATUSES)
        _require_state("identity_status", self.identity_status, IDENTITY_STATUSES)
        _require_state("key_status", self.key_status, KEY_STATUSES)
        _require_state("trust_status", self.trust_status, TRUST_STATUSES)
        _require_state("authorization_status", self.authorization_status, AUTHORIZATION_STATUSES)


@dataclass(frozen=True, slots=True)
class PackageSignatureResult:
    package_integrity: str
    signature_presence: str
    verification_completed: bool
    policy_satisfied: bool | None
    statement_sha256: str | None
    package_id: str | None
    logical_digest: str | None
    signatures: tuple[SignatureVerification, ...]
    diagnostics: tuple[Diagnostic, ...]

    def __post_init__(self) -> None:
        _require_state("package_integrity", self.package_integrity, frozenset({"valid", "invalid"}))
        _require_state("signature_presence", self.signature_presence, frozenset({"unsigned", "signed"}))


def validate_signing_document(value: Any, schema_name: str) -> None:
    if schema_name not in SIGNING_SCHEMA_NAMES:
        raise SigningError("AECCTX_SIGNING_SCHEMA_UNSUPPORTED", "signing schema name is not allowlisted")
    schema = json.loads(files("aecctx.schemas.v0_2").joinpath(schema_name).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(value), key=lambda item: [str(part) for part in item.absolute_path])
    if errors:
        location = "/".join(str(part) for part in errors[0].absolute_path) or "$"
        raise SigningError("AECCTX_SIGNING_SCHEMA_INVALID", f"{schema_name} failed validation at {location}")


def build_signing_statement(package_path: str | Path, *, limits: SigningLimits | None = None) -> SigningStatement:
    from ._signing_io import canonical_json_nfc, load_strict_json

    active_limits = limits or SigningLimits()
    validation = validate_package(package_path)
    if not validation.valid:
        raise SigningError("AECCTX_SIGNING_PACKAGE_INVALID", "package must pass structural and integrity validation before signing")
    try:
        reader = PackageReader(package_path)
        raw_manifest = reader.read_bytes("manifest.json")
    except PackageReadError as error:
        raise SigningError("AECCTX_SIGNING_PACKAGE_INVALID", "package manifest cannot be read safely") from error
    manifest = load_strict_json(raw_manifest, label="manifest", max_bytes=active_limits.max_document_bytes)
    if not isinstance(manifest, dict):
        raise SigningError("AECCTX_SIGNING_PACKAGE_INVALID", "package manifest must contain a JSON object")

    semantic_manifest = dict(manifest)
    semantic_manifest.pop("package_form", None)
    semantic_bytes = canonical_json_nfc(semantic_manifest, terminal_lf=True)
    statement_data = {
        "aecctx_version": manifest["aecctx_version"],
        "logical_digest": manifest["logical_digest"],
        "package_id": manifest["package_id"],
        "profile": "https://aecctx.dev/signing/v1",
        "required_extensions": manifest.get("required_extensions", []),
        "semantic_manifest_sha256": hashlib.sha256(semantic_bytes).hexdigest(),
        "statement_version": "1",
    }
    canonical_bytes = canonical_json_nfc(statement_data, terminal_lf=True)
    return SigningStatement(statement_data, canonical_bytes, hashlib.sha256(canonical_bytes).hexdigest())


def _validate_kid(kid: str) -> None:
    if (
        not kid
        or len(kid) > 256
        or unicodedata.normalize("NFC", kid) != kid
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in kid)
    ):
        raise SigningError("AECCTX_SIGNING_KID_INVALID", "kid must be bounded NFC text without control characters")


def sign_package(
    package_path: str | Path,
    *,
    private_key_pem: bytes,
    kid: str,
    password: bytes | None = None,
    limits: SigningLimits | None = None,
) -> SignatureBundle:
    from ._signing_crypto import load_private_key, sign_bytes
    from ._signing_io import base64url_encode, canonical_json_nfc

    active_limits = limits or SigningLimits()
    _validate_kid(kid)
    if len(private_key_pem) > active_limits.max_private_key_bytes:
        raise SigningError("AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED", "private key exceeds its byte limit")
    if password is not None and len(password) > active_limits.max_password_bytes:
        raise SigningError("AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED", "password exceeds its byte limit")

    statement = build_signing_statement(package_path, limits=active_limits)
    protected_value = {
        "alg": "Ed25519",
        "https://aecctx.dev/jws/statement-sha256": statement.sha256,
        "kid": kid,
        "typ": "aecctx-signing-statement+jws",
    }
    protected = base64url_encode(canonical_json_nfc(protected_value, terminal_lf=False))
    signing_input = f"{protected}.{base64url_encode(statement.canonical_bytes)}".encode("ascii")
    private_key = load_private_key(private_key_pem, password)
    signature = base64url_encode(sign_bytes(private_key, signing_input))
    return SignatureBundle((SignatureEntry(protected, signature, kid, "Ed25519", statement.sha256),))


def append_signature(
    package_path: str | Path,
    bundle: SignatureBundle,
    *,
    private_key_pem: bytes,
    kid: str,
    password: bytes | None = None,
    limits: SigningLimits | None = None,
) -> SignatureBundle:
    active_limits = limits or SigningLimits()
    existing_kids = [entry.kid for entry in bundle.signatures]
    if len(existing_kids) != len(set(existing_kids)) or kid in existing_kids:
        raise SigningError("AECCTX_SIGNING_DUPLICATE_KID", "signature bundle contains a duplicate kid")
    if len(bundle.signatures) >= active_limits.max_signatures:
        raise SigningError("AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED", "signature bundle exceeds its signature limit")
    new_bundle = sign_package(
        package_path,
        private_key_pem=private_key_pem,
        kid=kid,
        password=password,
        limits=active_limits,
    )
    return SignatureBundle(bundle.signatures + new_bundle.signatures)
