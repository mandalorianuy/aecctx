from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from .errors import AECCTXError, Diagnostic


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
