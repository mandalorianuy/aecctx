from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


GATE_PROFILE = "https://aecctx.dev/gate/v1"
CHECK_KINDS = frozenset(
    {
        "capability.minimum",
        "loss.maximum",
        "value_state.action",
        "diagnostic.maximum",
        "diff.regression",
        "ids.specification",
    }
)
CHECK_STATUSES = frozenset({"pass", "fail", "requires_review", "waived", "error"})
FINDING_DISPOSITIONS = frozenset({"fail", "requires_review", "waived", "error"})
OUTCOMES = frozenset({"pass", "fail", "requires_review", "error"})
SEVERITIES = ("info", "warning", "error", "blocking")
VALUE_ACTIONS = frozenset({"allow", "requires_review", "fail"})
FAILURE_MODES = frozenset({"fail", "requires_review"})

_IDENTIFIER = re.compile(r"[a-z][a-z0-9._-]{0,63}")
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}")
_CHECK_STATUS_PRIORITY = {"pass": 0, "waived": 1, "requires_review": 2, "fail": 3, "error": 4}


class GateError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        if not isinstance(code, str) or not code:
            raise ValueError("code must be a non-empty string")
        if not isinstance(message, str) or not message:
            raise ValueError("message must be a non-empty string")
        super().__init__(message)
        self.code = code


def _require_state(field: str, value: str, allowed: frozenset[str] | tuple[str, ...]) -> None:
    if value not in allowed:
        raise ValueError(f"{field} has an ungoverned value: {value!r}")


def _require_string(field: str, value: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")


def _require_identifier(field: str, value: str) -> None:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{field} must be a governed identifier")


def _require_digest(field: str, value: str) -> None:
    if not isinstance(value, str) or _LOWER_SHA256.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")


def _require_tuple(field: str, value: object) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{field} must be a tuple")


def _require_immutable_tree(field: str, value: Any) -> None:
    if isinstance(value, tuple):
        for item in value:
            _require_immutable_tree(field, item)
        return
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    raise TypeError(f"{field} must contain only immutable tuple/scalar values")


def _sorted_unique_strings(field: str, value: tuple[str, ...]) -> tuple[str, ...]:
    _require_tuple(field, value)
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{field} must contain non-empty strings")
    return tuple(sorted(set(value)))


@dataclass(frozen=True, slots=True)
class GateLimits:
    max_policy_bytes: int = 1_048_576
    max_ids_bytes: int = 1_048_576
    max_checks: int = 256
    max_waivers: int = 1_024
    max_ifc_bytes: int = 268_435_456
    max_findings: int = 100_000
    max_result_bytes: int = 16_777_216
    ids_timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        for field in self.__dataclass_fields__:
            value = getattr(self, field)
            if field == "ids_timeout_seconds":
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise TypeError("ids_timeout_seconds must be numeric")
            elif isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{field} must be an integer")
            if value <= 0:
                raise ValueError(f"{field} must be positive")


@dataclass(frozen=True, slots=True)
class GateCheckPolicy:
    check_id: str
    kind: str
    severity: str
    failure_mode: str
    configuration: tuple[tuple[str, Any], ...]

    def __post_init__(self) -> None:
        _require_identifier("check_id", self.check_id)
        _require_state("kind", self.kind, CHECK_KINDS)
        _require_state("severity", self.severity, SEVERITIES)
        _require_state("failure_mode", self.failure_mode, FAILURE_MODES)
        _require_tuple("configuration", self.configuration)
        _require_immutable_tree("configuration", self.configuration)
        if any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not item[0]
            for item in self.configuration
        ):
            raise ValueError("configuration must contain non-empty string key/value pairs")
        keys = tuple(item[0] for item in self.configuration)
        if len(set(keys)) != len(keys):
            raise ValueError("configuration keys must be unique")
        object.__setattr__(self, "configuration", tuple(sorted(self.configuration, key=lambda item: item[0])))


@dataclass(frozen=True, slots=True)
class GateWaiver:
    waiver_id: str
    check_id: str
    finding_fingerprint: str
    reason: str
    approved_by: str
    issued_at: str
    expires_at: str

    def __post_init__(self) -> None:
        _require_identifier("waiver_id", self.waiver_id)
        if not isinstance(self.check_id, str) or not self.check_id.startswith("aecctx.policy."):
            raise ValueError("check_id must be an exact aecctx.policy result ID")
        _require_identifier("check_id", self.check_id.removeprefix("aecctx.policy."))
        _require_digest("finding_fingerprint", self.finding_fingerprint)
        for field in ("reason", "approved_by", "issued_at", "expires_at"):
            _require_string(field, getattr(self, field))


@dataclass(frozen=True, slots=True)
class GatePolicy:
    profile: str
    policy_id: str
    policy_version: str
    evaluation_time: str
    checks: tuple[GateCheckPolicy, ...]
    waivers: tuple[GateWaiver, ...]
    digest: str
    canonical_bytes: bytes

    def __post_init__(self) -> None:
        if self.profile != GATE_PROFILE:
            raise ValueError("profile has an ungoverned value")
        _require_identifier("policy_id", self.policy_id)
        _require_string("policy_version", self.policy_version)
        _require_string("evaluation_time", self.evaluation_time)
        _require_tuple("checks", self.checks)
        _require_tuple("waivers", self.waivers)
        if any(not isinstance(item, GateCheckPolicy) for item in self.checks):
            raise TypeError("checks must contain GateCheckPolicy values")
        if any(not isinstance(item, GateWaiver) for item in self.waivers):
            raise TypeError("waivers must contain GateWaiver values")
        _require_digest("digest", self.digest)
        if not isinstance(self.canonical_bytes, bytes):
            raise TypeError("canonical_bytes must be bytes")


@dataclass(frozen=True, slots=True)
class GateFinding:
    code: str
    check_id: str
    severity: str
    disposition: str
    subject_id: str
    observed_state: str
    evidence_refs: tuple[str, ...]
    fingerprint: str
    message: str
    waiver_id: str | None = None

    def __post_init__(self) -> None:
        for field in ("code", "check_id", "subject_id", "observed_state", "message"):
            _require_string(field, getattr(self, field))
        _require_state("severity", self.severity, SEVERITIES)
        _require_state("disposition", self.disposition, FINDING_DISPOSITIONS)
        _require_digest("fingerprint", self.fingerprint)
        if self.disposition == "waived" and self.waiver_id is None:
            raise ValueError("waived disposition requires waiver_id")
        if self.disposition != "waived" and self.waiver_id is not None:
            raise ValueError("non-waived disposition requires null waiver_id")
        if self.waiver_id is not None:
            _require_identifier("waiver_id", self.waiver_id)
        object.__setattr__(self, "evidence_refs", _sorted_unique_strings("evidence_refs", self.evidence_refs))

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "check_id": self.check_id,
            "severity": self.severity,
            "disposition": self.disposition,
            "subject_id": self.subject_id,
            "observed_state": self.observed_state,
            "evidence_refs": list(self.evidence_refs),
            "fingerprint": self.fingerprint,
            "message": self.message,
            "waiver_id": self.waiver_id,
        }


@dataclass(frozen=True, slots=True)
class GateCheckResult:
    check_id: str
    kind: str
    status: str
    severity: str
    evidence_refs: tuple[str, ...]
    findings: tuple[GateFinding, ...]
    message: str

    def __post_init__(self) -> None:
        _require_string("check_id", self.check_id)
        _require_state("kind", self.kind, CHECK_KINDS | {"system"})
        _require_state("status", self.status, CHECK_STATUSES)
        _require_state("severity", self.severity, SEVERITIES)
        _require_string("message", self.message)
        object.__setattr__(self, "evidence_refs", _sorted_unique_strings("evidence_refs", self.evidence_refs))
        _require_tuple("findings", self.findings)
        if any(not isinstance(item, GateFinding) for item in self.findings):
            raise TypeError("findings must contain GateFinding values")
        if any(item.check_id != self.check_id for item in self.findings):
            raise ValueError("finding check_id must match its check result")
        fingerprints = tuple(item.fingerprint for item in self.findings)
        if len(fingerprints) != len(set(fingerprints)):
            raise ValueError("finding fingerprints must be unique within a check")
        if self.findings:
            expected_status = max(
                (item.disposition for item in self.findings),
                key=_CHECK_STATUS_PRIORITY.__getitem__,
            )
            lifecycle_review_floor = expected_status == "waived" and self.status == "requires_review"
            if self.status != expected_status and not lifecycle_review_floor:
                raise ValueError(
                    "check status must equal its highest finding disposition or its governed lifecycle review floor"
                )
        object.__setattr__(
            self,
            "findings",
            tuple(
                sorted(
                    self.findings,
                    key=lambda item: (item.code, item.subject_id, item.fingerprint, item.evidence_refs),
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "kind": self.kind,
            "status": self.status,
            "severity": self.severity,
            "evidence_refs": list(self.evidence_refs),
            "findings": [finding.to_dict() for finding in self.findings],
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class GateDiagnostic:
    code: str
    severity: str
    message: str
    path: str | None = None
    check_id: str | None = None

    def __post_init__(self) -> None:
        _require_string("code", self.code)
        _require_state("severity", self.severity, SEVERITIES)
        _require_string("message", self.message)
        if self.path is not None:
            _require_string("path", self.path)
        if self.check_id is not None:
            _require_string("check_id", self.check_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "check_id": self.check_id,
        }


@dataclass(frozen=True, slots=True)
class GateResult:
    evaluator_version: str
    evaluator_dependencies: tuple[tuple[str, str], ...]
    candidate_package_id: str | None
    candidate_logical_digest: str | None
    policy_id: str
    policy_version: str
    policy_digest: str
    outcome: str
    exit_code: int
    checks: tuple[GateCheckResult, ...]
    findings: tuple[GateFinding, ...]
    diagnostics: tuple[GateDiagnostic, ...]
    baseline_package_id: str | None = None
    baseline_logical_digest: str | None = None
    ids_digest: str | None = None
    ifc_source_id: str | None = None
    ifc_source_digest: str | None = None

    def __post_init__(self) -> None:
        for field in ("evaluator_version", "policy_id", "policy_version"):
            _require_string(field, getattr(self, field))
        candidate = (self.candidate_package_id, self.candidate_logical_digest)
        if any(item is not None for item in candidate) and not all(item is not None for item in candidate):
            raise ValueError("candidate package ID and digest must be provided together")
        if self.candidate_package_id is None:
            if self.outcome != "error":
                raise ValueError("candidate identity may be null only for error outcome")
        else:
            _require_string("candidate_package_id", self.candidate_package_id)
            _require_digest("candidate_logical_digest", self.candidate_logical_digest)  # type: ignore[arg-type]
        _require_digest("policy_digest", self.policy_digest)
        _require_state("outcome", self.outcome, OUTCOMES)
        expected_exit = {"pass": 0, "fail": 1, "requires_review": 1, "error": 2}[self.outcome]
        if self.exit_code != expected_exit:
            raise ValueError("exit_code does not match outcome")
        _require_tuple("evaluator_dependencies", self.evaluator_dependencies)
        if any(
            not isinstance(item, tuple)
            or len(item) != 2
            or any(not isinstance(value, str) or not value for value in item)
            for item in self.evaluator_dependencies
        ):
            raise ValueError("evaluator_dependencies must contain name/version string pairs")
        dependency_names = tuple(item[0] for item in self.evaluator_dependencies)
        if len(set(dependency_names)) != len(dependency_names):
            raise ValueError("evaluator dependency names must be unique")
        object.__setattr__(self, "evaluator_dependencies", tuple(sorted(self.evaluator_dependencies)))
        self._normalize_optional_inputs()
        _require_tuple("checks", self.checks)
        _require_tuple("findings", self.findings)
        _require_tuple("diagnostics", self.diagnostics)
        if any(not isinstance(item, GateCheckResult) for item in self.checks):
            raise TypeError("checks must contain GateCheckResult values")
        if any(not isinstance(item, GateFinding) for item in self.findings):
            raise TypeError("findings must contain GateFinding values")
        if any(not isinstance(item, GateDiagnostic) for item in self.diagnostics):
            raise TypeError("diagnostics must contain GateDiagnostic values")
        object.__setattr__(self, "checks", tuple(sorted(self.checks, key=lambda item: item.check_id)))
        object.__setattr__(
            self,
            "findings",
            tuple(
                sorted(
                    self.findings,
                    key=lambda item: (
                        item.check_id,
                        item.code,
                        item.subject_id,
                        item.fingerprint,
                        item.evidence_refs,
                    ),
                )
            ),
        )
        object.__setattr__(
            self,
            "diagnostics",
            tuple(sorted(self.diagnostics, key=lambda item: (item.code, item.path or "", item.check_id or ""))),
        )

    def _normalize_optional_inputs(self) -> None:
        baseline = (self.baseline_package_id, self.baseline_logical_digest)
        if any(item is not None for item in baseline) and not all(item is not None for item in baseline):
            raise ValueError("baseline package ID and digest must be provided together")
        if self.baseline_logical_digest is not None:
            _require_digest("baseline_logical_digest", self.baseline_logical_digest)
        ids = (self.ids_digest, self.ifc_source_id, self.ifc_source_digest)
        if any(item is not None for item in ids) and not all(item is not None for item in ids):
            raise ValueError("IDS digest and IFC source identity must be provided together")
        if self.ids_digest is not None:
            _require_digest("ids_digest", self.ids_digest)
            _require_string("ifc_source_id", self.ifc_source_id)  # type: ignore[arg-type]
            _require_digest("ifc_source_digest", self.ifc_source_digest)  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, Any]:
        baseline = None
        if self.baseline_package_id is not None:
            baseline = {
                "package_id": self.baseline_package_id,
                "logical_digest": self.baseline_logical_digest,
            }
        ids_input = None
        if self.ids_digest is not None:
            ids_input = {
                "ids_digest": self.ids_digest,
                "source_id": self.ifc_source_id,
                "source_digest": self.ifc_source_digest,
            }
        return {
            "profile": GATE_PROFILE,
            "result_version": "1",
            "evaluator": {
                "version": self.evaluator_version,
                "dependencies": [
                    {"name": name, "version": version}
                    for name, version in self.evaluator_dependencies
                ],
            },
            "candidate": None
            if self.candidate_package_id is None
            else {
                "package_id": self.candidate_package_id,
                "logical_digest": self.candidate_logical_digest,
            },
            "baseline": baseline,
            "policy": {
                "policy_id": self.policy_id,
                "policy_version": self.policy_version,
                "digest": self.policy_digest,
            },
            "ids_input": ids_input,
            "outcome": self.outcome,
            "exit_code": self.exit_code,
            "checks": [check.to_dict() for check in self.checks],
            "findings": [finding.to_dict() for finding in self.findings],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }
