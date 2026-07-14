from __future__ import annotations

import json
import hashlib
import re
import unicodedata
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass
from datetime import datetime, timezone
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
_PROTECTED_HEADERS = frozenset({"alg", "kid", "typ", "https://aecctx.dev/jws/statement-sha256"})
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}")
_UTC_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")


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
class KeyPolicyEvaluation:
    key_status: str
    trust_status: str
    authorization_status: str
    diagnostic_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_state("key_status", self.key_status, KEY_STATUSES)
        _require_state("trust_status", self.trust_status, TRUST_STATUSES)
        _require_state("authorization_status", self.authorization_status, AUTHORIZATION_STATUSES)


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
    semantic_manifest_sha256: str | None
    package_id: str | None
    logical_digest: str | None
    signatures: tuple[SignatureVerification, ...]
    diagnostics: tuple[Diagnostic, ...]
    package_diagnostic_codes: tuple[str, ...] = ()
    policy_sha256: str | None = None
    minimum_authorized_signatures: int | None = None
    authorized_kids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_state("package_integrity", self.package_integrity, frozenset({"valid", "invalid"}))
        _require_state("signature_presence", self.signature_presence, frozenset({"unsigned", "signed"}))

    def to_dict(self) -> dict[str, Any]:
        if self.statement_sha256 is None or self.semantic_manifest_sha256 is None:
            raise ValueError("a completed verification result requires statement digests")
        if self.policy_satisfied is None:
            policy_evaluation = None
        else:
            if self.policy_sha256 is None or self.minimum_authorized_signatures is None:
                raise ValueError("a policy result requires policy metadata")
            policy_evaluation = {
                "policy_sha256": self.policy_sha256,
                "minimum_authorized_signatures": self.minimum_authorized_signatures,
                "authorized_kids": list(self.authorized_kids),
                "policy_satisfied": self.policy_satisfied,
            }
        value = {
            "result_version": "1",
            "package_validation": {
                "valid": self.package_integrity == "valid",
                "package_id": self.package_id,
                "logical_digest": self.logical_digest,
                "diagnostic_codes": list(self.package_diagnostic_codes),
            },
            "statement": {
                "profile": "https://aecctx.dev/signing/v1",
                "statement_version": "1",
                "sha256": self.statement_sha256,
                "semantic_manifest_sha256": self.semantic_manifest_sha256,
            },
            "signature_presence": self.signature_presence,
            "verification_completed": self.verification_completed,
            "signatures": [
                {
                    "kid": item.kid,
                    "algorithm": item.algorithm,
                    "subject": item.subject,
                    "cryptographic_status": item.cryptographic_status,
                    "identity_status": item.identity_status,
                    "key_status": item.key_status,
                    "trust_status": item.trust_status,
                    "authorization_status": item.authorization_status,
                    "diagnostic_codes": list(item.diagnostic_codes),
                }
                for item in self.signatures
            ],
            "policy_evaluation": policy_evaluation,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }
        validate_signing_document(value, "signature-verification-result.schema.json")
        return value


def validate_signing_document(value: Any, schema_name: str) -> None:
    if schema_name not in SIGNING_SCHEMA_NAMES:
        raise SigningError("AECCTX_SIGNING_SCHEMA_UNSUPPORTED", "signing schema name is not allowlisted")
    schema = json.loads(files("aecctx.schemas.v0_2").joinpath(schema_name).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(value), key=lambda item: [str(part) for part in item.absolute_path])
    if errors:
        location = "/".join(str(part) for part in errors[0].absolute_path) or "$"
        raise SigningError("AECCTX_SIGNING_SCHEMA_INVALID", f"{schema_name} failed validation at {location}")


def _parse_utc_instant(value: str, *, code: str, label: str) -> datetime:
    if _UTC_INSTANT.fullmatch(value) is None:
        raise SigningError(code, f"{label} must be an RFC3339 UTC instant")
    try:
        instant = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise SigningError(code, f"{label} must be an RFC3339 UTC instant") from error
    if instant.tzinfo != timezone.utc:
        raise SigningError(code, f"{label} must be an RFC3339 UTC instant")
    return instant


def parse_signature_bundle(data: bytes, *, limits: SigningLimits | None = None) -> SignatureBundle:
    from ._signing_io import base64url_decode, canonical_json_nfc, load_strict_json

    active_limits = limits or SigningLimits()
    value = load_strict_json(data, label="signature bundle", max_bytes=active_limits.max_document_bytes)
    validate_signing_document(value, "signature-bundle.schema.json")
    signatures = value["signatures"]
    if len(signatures) > active_limits.max_signatures:
        raise SigningError("AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED", "signature bundle exceeds its signature limit")

    entries: list[SignatureEntry] = []
    for item in signatures:
        protected_bytes = base64url_decode(item["protected"])
        protected = load_strict_json(
            protected_bytes,
            label="protected header",
            max_bytes=2_048,
        )
        if not isinstance(protected, dict) or set(protected) != _PROTECTED_HEADERS:
            raise SigningError("AECCTX_SIGNING_HEADER_INVALID", "protected header set does not match profile v1")
        if canonical_json_nfc(protected, terminal_lf=False) != protected_bytes:
            raise SigningError("AECCTX_SIGNING_HEADER_INVALID", "protected header is not canonical JSON")
        algorithm = protected["alg"]
        kid = protected["kid"]
        statement_sha256 = protected["https://aecctx.dev/jws/statement-sha256"]
        if (
            algorithm != "Ed25519"
            or protected["typ"] != "aecctx-signing-statement+jws"
            or not isinstance(kid, str)
            or not isinstance(statement_sha256, str)
            or _LOWER_SHA256.fullmatch(statement_sha256) is None
        ):
            raise SigningError("AECCTX_SIGNING_HEADER_INVALID", "protected header values do not match profile v1")
        try:
            _validate_kid(kid)
        except SigningError as error:
            raise SigningError("AECCTX_SIGNING_HEADER_INVALID", "protected kid is invalid") from error
        base64url_decode(item["signature"], expected_bytes=64)
        entries.append(SignatureEntry(item["protected"], item["signature"], kid, algorithm, statement_sha256))

    kids = [entry.kid for entry in entries]
    if len(kids) != len(set(kids)):
        raise SigningError("AECCTX_SIGNING_DUPLICATE_KID", "signature bundle contains a duplicate kid")
    ordered = sorted(entries, key=lambda item: (item.kid, item.protected, item.signature))
    if entries != ordered:
        raise SigningError("AECCTX_SIGNING_BUNDLE_ORDER_INVALID", "signature bundle entries are not canonically ordered")
    return SignatureBundle(tuple(entries))


def parse_key_registry(data: bytes, *, limits: SigningLimits | None = None) -> KeyRegistry:
    from ._signing_io import base64url_decode, load_strict_json

    active_limits = limits or SigningLimits()
    value = load_strict_json(data, label="key registry", max_bytes=active_limits.max_document_bytes)
    validate_signing_document(value, "signing-key-registry.schema.json")
    records = value["keys"]
    if len(records) > active_limits.max_keys:
        raise SigningError("AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED", "key registry exceeds its key limit")

    keys: list[SigningKey] = []
    seen: set[str] = set()
    for record in records:
        kid = record["kid"]
        _validate_kid(kid)
        if kid in seen:
            raise SigningError("AECCTX_SIGNING_DUPLICATE_KID", "key registry contains a duplicate kid")
        seen.add(kid)
        base64url_decode(record["public_key"]["x"], expected_bytes=32)
        valid_from = _parse_utc_instant(
            record["valid_from"], code="AECCTX_SIGNING_REGISTRY_INVALID", label="valid_from"
        )
        valid_until = _parse_utc_instant(
            record["valid_until"], code="AECCTX_SIGNING_REGISTRY_INVALID", label="valid_until"
        )
        if valid_from >= valid_until:
            raise SigningError("AECCTX_SIGNING_REGISTRY_INVALID", "key validity interval must be non-empty")
        revoked_at_value = record.get("revoked_at")
        revoked_at = None
        if revoked_at_value is not None:
            revoked_at = _parse_utc_instant(
                revoked_at_value, code="AECCTX_SIGNING_REGISTRY_INVALID", label="revoked_at"
            )
            if revoked_at < valid_from or revoked_at >= valid_until:
                raise SigningError("AECCTX_SIGNING_REGISTRY_INVALID", "revoked_at must fall within the key interval")
        scopes = tuple(record["scopes"])
        if list(scopes) != sorted(scopes):
            raise SigningError("AECCTX_SIGNING_REGISTRY_INVALID", "key scopes must be sorted")
        keys.append(
            SigningKey(
                kid=kid,
                public_key_x=record["public_key"]["x"],
                subject=record["subject"],
                valid_from=record["valid_from"],
                valid_until=record["valid_until"],
                revocation_status=record["revocation_status"],
                revoked_at=revoked_at_value,
                scopes=scopes,
            )
        )
    return KeyRegistry(tuple(keys))


def parse_trust_policy(data: bytes, *, limits: SigningLimits | None = None) -> TrustPolicy:
    from ._signing_io import load_strict_json

    active_limits = limits or SigningLimits()
    value = load_strict_json(data, label="trust policy", max_bytes=active_limits.max_document_bytes)
    validate_signing_document(value, "signing-trust-policy.schema.json")
    _parse_utc_instant(
        value["verification_time"], code="AECCTX_SIGNING_POLICY_INVALID", label="verification_time"
    )
    required_scopes = tuple(value["required_scopes"])
    if list(required_scopes) != sorted(required_scopes):
        raise SigningError("AECCTX_SIGNING_POLICY_INVALID", "required scopes must be sorted")
    return TrustPolicy(
        verification_time=value["verification_time"],
        allowed_algorithms=tuple(value["allowed_algorithms"]),
        trusted_kids=tuple(value["trusted_kids"]),
        trusted_subjects=tuple(value["trusted_subjects"]),
        required_scopes=required_scopes,
        minimum_authorized_signatures=value["minimum_authorized_signatures"],
    )


def evaluate_key(key: SigningKey | None, policy: TrustPolicy | None) -> KeyPolicyEvaluation:
    if key is None or policy is None:
        return KeyPolicyEvaluation("not_evaluated", "not_evaluated", "not_evaluated", ())

    verification_time = _parse_utc_instant(
        policy.verification_time,
        code="AECCTX_SIGNING_POLICY_INVALID",
        label="verification_time",
    )
    valid_from = _parse_utc_instant(
        key.valid_from,
        code="AECCTX_SIGNING_REGISTRY_INVALID",
        label="valid_from",
    )
    valid_until = _parse_utc_instant(
        key.valid_until,
        code="AECCTX_SIGNING_REGISTRY_INVALID",
        label="valid_until",
    )
    if verification_time < valid_from:
        key_status = "not_yet_valid"
    elif verification_time >= valid_until:
        key_status = "expired"
    elif key.revocation_status == "revoked":
        if key.revoked_at is None:
            raise SigningError("AECCTX_SIGNING_REGISTRY_INVALID", "revoked key requires revoked_at")
        revoked_at = _parse_utc_instant(
            key.revoked_at,
            code="AECCTX_SIGNING_REGISTRY_INVALID",
            label="revoked_at",
        )
        key_status = "revoked" if verification_time >= revoked_at else "valid"
    elif key.revocation_status == "unknown":
        key_status = "unknown_status"
    else:
        key_status = "valid"

    selected = key.kid in policy.trusted_kids or key.subject in policy.trusted_subjects
    trust_status = "trusted" if key_status == "valid" and selected else "untrusted"
    scopes_satisfied = set(policy.required_scopes).issubset(key.scopes)
    authorization_status = "authorized" if trust_status == "trusted" and scopes_satisfied else "unauthorized"

    key_codes = {
        "not_yet_valid": "AECCTX_SIGNING_KEY_NOT_YET_VALID",
        "expired": "AECCTX_SIGNING_KEY_EXPIRED",
        "revoked": "AECCTX_SIGNING_KEY_REVOKED",
        "unknown_status": "AECCTX_SIGNING_KEY_STATUS_UNKNOWN",
    }
    codes: list[str] = []
    if key_status in key_codes:
        codes.append(key_codes[key_status])
    if trust_status == "untrusted":
        codes.append("AECCTX_SIGNING_KEY_UNTRUSTED")
    if authorization_status == "unauthorized":
        codes.append("AECCTX_SIGNING_SIGNER_UNAUTHORIZED")
    return KeyPolicyEvaluation(key_status, trust_status, authorization_status, tuple(codes))


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


_VERIFICATION_DIAGNOSTIC_MESSAGES = {
    "AECCTX_SIGNING_STATEMENT_BINDING_MISMATCH": "signature is bound to a different package statement",
    "AECCTX_SIGNING_SIGNATURE_INVALID": "Ed25519 signature verification failed",
    "AECCTX_SIGNING_UNKNOWN_KEY": "signature key id is absent from the supplied registry",
    "AECCTX_SIGNING_ALGORITHM_UNSUPPORTED": "signature algorithm is not supported by profile v1",
    "AECCTX_SIGNING_KEY_NOT_YET_VALID": "signing key is not yet valid at policy time",
    "AECCTX_SIGNING_KEY_EXPIRED": "signing key is expired at policy time",
    "AECCTX_SIGNING_KEY_REVOKED": "signing key is revoked at policy time",
    "AECCTX_SIGNING_KEY_STATUS_UNKNOWN": "signing key revocation status is unknown",
    "AECCTX_SIGNING_KEY_UNTRUSTED": "signing key is not trusted by the supplied policy",
    "AECCTX_SIGNING_SIGNER_UNAUTHORIZED": "signing key does not satisfy policy authorization",
    "AECCTX_SIGNING_THRESHOLD_NOT_MET": "authorized signature threshold was not met",
}


def _policy_sha256(policy: TrustPolicy) -> str:
    from ._signing_io import canonical_json_nfc

    value = {
        "allowed_algorithms": list(policy.allowed_algorithms),
        "minimum_authorized_signatures": policy.minimum_authorized_signatures,
        "policy_version": "1",
        "required_scopes": list(policy.required_scopes),
        "trusted_kids": list(policy.trusted_kids),
        "trusted_subjects": list(policy.trusted_subjects),
        "verification_time": policy.verification_time,
    }
    return hashlib.sha256(canonical_json_nfc(value, terminal_lf=True)).hexdigest()


def _verification_diagnostics(codes: list[str]) -> tuple[Diagnostic, ...]:
    seen: set[str] = set()
    diagnostics: list[Diagnostic] = []
    for code in codes:
        if code in seen:
            continue
        seen.add(code)
        diagnostics.append(Diagnostic(code, _VERIFICATION_DIAGNOSTIC_MESSAGES[code]))
    return tuple(diagnostics)


def verify_package_signatures(
    package_path: str | Path,
    *,
    bundle: SignatureBundle | None,
    registry: KeyRegistry,
    policy: TrustPolicy | None = None,
    limits: SigningLimits | None = None,
) -> PackageSignatureResult:
    from ._signing_crypto import verify_ed25519
    from ._signing_io import base64url_decode, base64url_encode

    active_limits = limits or SigningLimits()
    statement = build_signing_statement(package_path, limits=active_limits)
    package_id = str(statement.data["package_id"])
    logical_digest = str(statement.data["logical_digest"])
    semantic_manifest_sha256 = str(statement.data["semantic_manifest_sha256"])
    policy_digest = _policy_sha256(policy) if policy is not None else None

    if bundle is None:
        codes = ["AECCTX_SIGNING_THRESHOLD_NOT_MET"] if policy is not None else []
        result = PackageSignatureResult(
            package_integrity="valid",
            signature_presence="unsigned",
            verification_completed=True,
            policy_satisfied=False if policy is not None else None,
            statement_sha256=statement.sha256,
            semantic_manifest_sha256=semantic_manifest_sha256,
            package_id=package_id,
            logical_digest=logical_digest,
            signatures=(),
            diagnostics=_verification_diagnostics(codes),
            policy_sha256=policy_digest,
            minimum_authorized_signatures=(policy.minimum_authorized_signatures if policy is not None else None),
        )
        result.to_dict()
        return result

    if len(bundle.signatures) > active_limits.max_signatures:
        raise SigningError("AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED", "signature bundle exceeds its signature limit")
    kids = [entry.kid for entry in bundle.signatures]
    if len(kids) != len(set(kids)):
        raise SigningError("AECCTX_SIGNING_DUPLICATE_KID", "signature bundle contains a duplicate kid")
    key_by_kid: dict[str, SigningKey] = {}
    for key in registry.keys:
        if key.kid in key_by_kid:
            raise SigningError("AECCTX_SIGNING_DUPLICATE_KID", "key registry contains a duplicate kid")
        key_by_kid[key.kid] = key

    results: list[SignatureVerification] = []
    all_codes: list[str] = []
    encoded_statement = base64url_encode(statement.canonical_bytes)
    for entry in bundle.signatures:
        if entry.statement_sha256 != statement.sha256:
            codes = ("AECCTX_SIGNING_STATEMENT_BINDING_MISMATCH",)
            result = SignatureVerification(
                entry.kid,
                entry.algorithm,
                None,
                "invalid",
                "unresolved",
                "not_evaluated",
                "not_evaluated",
                "not_evaluated",
                codes,
            )
            results.append(result)
            all_codes.extend(codes)
            continue

        key = key_by_kid.get(entry.kid)
        if key is None:
            codes = ("AECCTX_SIGNING_UNKNOWN_KEY",)
            result = SignatureVerification(
                entry.kid,
                entry.algorithm,
                None,
                "unknown_key",
                "unresolved",
                "not_evaluated",
                "not_evaluated",
                "not_evaluated",
                codes,
            )
            results.append(result)
            all_codes.extend(codes)
            continue

        evaluation = evaluate_key(key, policy)
        if entry.algorithm not in SIGNING_ALGORITHMS or (
            policy is not None and entry.algorithm not in policy.allowed_algorithms
        ):
            codes = ("AECCTX_SIGNING_ALGORITHM_UNSUPPORTED",)
            result = SignatureVerification(
                entry.kid,
                entry.algorithm,
                key.subject,
                "unsupported_algorithm",
                "resolved",
                evaluation.key_status,
                evaluation.trust_status,
                evaluation.authorization_status,
                codes,
            )
            results.append(result)
            all_codes.extend(codes)
            continue

        signature = base64url_decode(entry.signature, expected_bytes=64)
        public_key = base64url_decode(key.public_key_x, expected_bytes=32)
        signing_input = f"{entry.protected}.{encoded_statement}".encode("ascii")
        valid = verify_ed25519(public_key, signature, signing_input)
        crypto_codes = () if valid else ("AECCTX_SIGNING_SIGNATURE_INVALID",)
        codes = evaluation.diagnostic_codes + crypto_codes
        result = SignatureVerification(
            entry.kid,
            entry.algorithm,
            key.subject,
            "valid" if valid else "invalid",
            "resolved",
            evaluation.key_status,
            evaluation.trust_status,
            evaluation.authorization_status,
            codes,
        )
        results.append(result)
        all_codes.extend(codes)

    authorized = tuple(
        sorted(
            {
                item.kid
                for item in results
                if item.cryptographic_status == "valid"
                and item.key_status == "valid"
                and item.trust_status == "trusted"
                and item.authorization_status == "authorized"
            }
        )
    )
    policy_satisfied = None
    if policy is not None:
        policy_satisfied = len(authorized) >= policy.minimum_authorized_signatures
        if not policy_satisfied:
            all_codes.append("AECCTX_SIGNING_THRESHOLD_NOT_MET")
    result = PackageSignatureResult(
        package_integrity="valid",
        signature_presence="signed",
        verification_completed=True,
        policy_satisfied=policy_satisfied,
        statement_sha256=statement.sha256,
        semantic_manifest_sha256=semantic_manifest_sha256,
        package_id=package_id,
        logical_digest=logical_digest,
        signatures=tuple(results),
        diagnostics=_verification_diagnostics(all_codes),
        policy_sha256=policy_digest,
        minimum_authorized_signatures=(policy.minimum_authorized_signatures if policy is not None else None),
        authorized_kids=authorized,
    )
    result.to_dict()
    return result


def verify_advanced_trust(package_path: str | Path, *, bundle: bytes, policy: bytes) -> dict[str, Any]:
    """Evaluate the optional ACX-35 trust profile without importing it into core startup."""
    from .trust import evaluate_advanced_trust

    return evaluate_advanced_trust(package_path, bundle, policy)
