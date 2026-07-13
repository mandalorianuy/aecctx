from __future__ import annotations

import hashlib
import re
import tempfile
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import __version__
from ..diff import diff_packages
from ..package import PackageReadError, PackageReader
from ..records import RecordStore, VALUE_STATES
from ..validation import ValidationResult, validate_package
from .models import (
    SEVERITIES,
    GateCheckPolicy,
    GateCheckResult,
    GateDiagnostic,
    GateError,
    GateFinding,
    GateLimits,
    GatePolicy,
    GateResult,
)
from .policy import canonical_gate_json


_UTC_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
_STATUS_PRIORITY = {"pass": 0, "waived": 1, "requires_review": 2, "fail": 3, "error": 4}
_OUTCOME_EXIT = {"pass": 0, "requires_review": 1, "fail": 1, "error": 2}
_SUPPORT_LEVEL = {"unsupported": 0, "opaque": 1, "partial": 2, "full": 3}
_SEVERITY_LEVEL = {name: index for index, name in enumerate(SEVERITIES)}
_INTEGRITY_CODES = frozenset(
    {
        "AECCTX_ARTIFACT_PATH_DUPLICATE",
        "AECCTX_ARTIFACT_MISSING",
        "AECCTX_ARTIFACT_SIZE_MISMATCH",
        "AECCTX_ARTIFACT_HASH_MISMATCH",
        "AECCTX_REQUIRED_ARTIFACT_MISSING",
        "AECCTX_LOGICAL_DIGEST_MISMATCH",
    }
)


def _identity_string(field: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise GateError("AECCTX_GATE_FINDING_IDENTITY_INVALID", f"{field} must be a non-empty string")
    return unicodedata.normalize("NFC", value)


def finding_fingerprint(
    *,
    check_id: str,
    code: str,
    subject_id: str,
    observed_state: str,
    evidence_refs: Iterable[str],
) -> str:
    normalized_check_id = _identity_string("check_id", check_id)
    normalized_code = _identity_string("code", code)
    normalized_subject_id = _identity_string("subject_id", subject_id)
    normalized_observed_state = _identity_string("observed_state", observed_state)
    if isinstance(evidence_refs, (str, bytes)):
        raise GateError(
            "AECCTX_GATE_FINDING_IDENTITY_INVALID",
            "evidence_refs must be an iterable of non-empty strings",
        )
    try:
        raw_evidence = tuple(evidence_refs)
    except TypeError as error:
        raise GateError(
            "AECCTX_GATE_FINDING_IDENTITY_INVALID",
            "evidence_refs must be an iterable of non-empty strings",
        ) from error
    if any(not isinstance(item, str) or not item for item in raw_evidence):
        raise GateError(
            "AECCTX_GATE_FINDING_IDENTITY_INVALID",
            "evidence_refs must contain only non-empty strings",
        )
    normalized_evidence = sorted({unicodedata.normalize("NFC", item) for item in raw_evidence})
    identity = {
        "check_id": normalized_check_id,
        "code": normalized_code,
        "subject_id": normalized_subject_id,
        "observed_state": normalized_observed_state,
        "evidence_refs": normalized_evidence,
    }
    return hashlib.sha256(canonical_gate_json(identity)).hexdigest()


def aggregate_gate_outcome(checks: Iterable[GateCheckResult]) -> tuple[str, int]:
    materialized = tuple(checks)
    if any(not isinstance(check, GateCheckResult) for check in materialized):
        raise TypeError("checks must contain GateCheckResult values")
    highest = max((check.status for check in materialized), key=_STATUS_PRIORITY.__getitem__, default="pass")
    outcome = "requires_review" if highest == "waived" else highest
    return outcome, _OUTCOME_EXIT[outcome]


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or _UTC_INSTANT.fullmatch(value) is None:
        raise GateError(
            "AECCTX_GATE_WAIVER_INTERVAL_INVALID",
            "waiver lifecycle requires RFC3339 UTC Z instants",
        )
    try:
        instant = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise GateError(
            "AECCTX_GATE_WAIVER_INTERVAL_INVALID",
            "waiver lifecycle requires RFC3339 UTC Z instants",
        ) from error
    if instant.tzinfo != timezone.utc:
        raise GateError(
            "AECCTX_GATE_WAIVER_INTERVAL_INVALID",
            "waiver lifecycle requires RFC3339 UTC Z instants",
        )
    return instant


def _diagnostic(*, code: str, message: str, check_id: str, waiver_id: str) -> GateDiagnostic:
    return GateDiagnostic(
        code=code,
        severity="warning",
        message=message,
        path=f"policy.waivers/{waiver_id}",
        check_id=check_id,
    )


def _validate_waiver_control(
    checks_by_id: dict[str, GateCheckResult],
    policy: GatePolicy,
) -> tuple[datetime, dict[str, tuple[datetime, datetime]]]:
    evaluation_time = _parse_utc(policy.evaluation_time)
    declared = {f"aecctx.policy.{check.check_id}" for check in policy.checks}
    seen_waiver_ids: set[str] = set()
    seen_targets: set[tuple[str, str]] = set()
    intervals: dict[str, tuple[datetime, datetime]] = {}
    for waiver in policy.waivers:
        if waiver.waiver_id in seen_waiver_ids:
            raise GateError("AECCTX_GATE_WAIVER_ID_DUPLICATE", "policy contains a duplicate waiver id")
        seen_waiver_ids.add(waiver.waiver_id)
        target = (waiver.check_id, waiver.finding_fingerprint)
        if (
            not waiver.check_id.startswith("aecctx.policy.")
            or "*" in waiver.check_id
            or waiver.check_id not in declared
        ):
            raise GateError("AECCTX_GATE_WAIVER_CHECK_INVALID", "waiver check target is invalid")
        if target in seen_targets:
            raise GateError("AECCTX_GATE_WAIVER_DUPLICATE_TARGET", "policy contains a duplicate waiver target")
        seen_targets.add(target)
        if waiver.check_id not in checks_by_id:
            raise GateError("AECCTX_GATE_WAIVER_CHECK_MISSING", "waiver target check is missing")
        issued_at = _parse_utc(waiver.issued_at)
        expires_at = _parse_utc(waiver.expires_at)
        if issued_at >= expires_at:
            raise GateError("AECCTX_GATE_WAIVER_INTERVAL_INVALID", "waiver interval must be increasing")
        intervals[waiver.waiver_id] = (issued_at, expires_at)
    return evaluation_time, intervals


def apply_waivers(
    checks: tuple[GateCheckResult, ...],
    policy: GatePolicy,
) -> tuple[tuple[GateCheckResult, ...], tuple[GateDiagnostic, ...]]:
    if not isinstance(checks, tuple) or any(not isinstance(check, GateCheckResult) for check in checks):
        raise TypeError("checks must be a tuple of GateCheckResult values")
    if not isinstance(policy, GatePolicy):
        raise TypeError("policy must be GatePolicy")
    checks_by_id = {check.check_id: check for check in checks}
    if len(checks_by_id) != len(checks):
        raise GateError("AECCTX_GATE_WAIVER_CHECK_INVALID", "check IDs must be unique before waiver application")
    evaluation_time, intervals = _validate_waiver_control(checks_by_id, policy)
    diagnostics: list[GateDiagnostic] = []
    finding_updates: dict[str, dict[int, str]] = {}
    review_floors: set[str] = set()

    for waiver in policy.waivers:
        issued_at, expires_at = intervals[waiver.waiver_id]
        if evaluation_time < issued_at:
            diagnostics.append(
                _diagnostic(
                    code="AECCTX_GATE_WAIVER_NOT_YET_VALID",
                    message="waiver is not yet valid",
                    check_id=waiver.check_id,
                    waiver_id=waiver.waiver_id,
                )
            )
            continue
        if evaluation_time >= expires_at:
            diagnostics.append(
                _diagnostic(
                    code="AECCTX_GATE_WAIVER_EXPIRED",
                    message="waiver is expired",
                    check_id=waiver.check_id,
                    waiver_id=waiver.waiver_id,
                )
            )
            continue

        check = checks_by_id[waiver.check_id]
        matching_indexes = [
            index
            for index, finding in enumerate(check.findings)
            if finding.fingerprint == waiver.finding_fingerprint
        ]
        if not matching_indexes:
            diagnostics.append(
                _diagnostic(
                    code="AECCTX_GATE_WAIVER_FINDING_MISMATCH",
                    message="active waiver does not match a current finding",
                    check_id=waiver.check_id,
                    waiver_id=waiver.waiver_id,
                )
            )
            review_floors.add(check.check_id)
            continue
        if len(matching_indexes) != 1:
            raise GateError("AECCTX_GATE_FINDING_IDENTITY_INVALID", "finding fingerprint is not unique")
        index = matching_indexes[0]
        finding = check.findings[index]
        if finding.disposition not in {"fail", "requires_review"} or finding.waiver_id is not None:
            raise GateError(
                "AECCTX_GATE_WAIVER_DISPOSITION_INVALID",
                "finding disposition cannot be waived",
            )
        finding_updates.setdefault(check.check_id, {})[index] = waiver.waiver_id

    for check_id, check in tuple(checks_by_id.items()):
        updates = finding_updates.get(check_id, {})
        if not updates and check_id not in review_floors:
            continue
        updated_findings = list(check.findings)
        for index, waiver_id in updates.items():
            updated_findings[index] = replace(
                check.findings[index],
                disposition="waived",
                waiver_id=waiver_id,
            )
        provisional = tuple(updated_findings)
        status = max(
            (item.disposition for item in provisional),
            key=_STATUS_PRIORITY.__getitem__,
            default=check.status,
        )
        if check_id in review_floors:
            status = max((status, "requires_review"), key=_STATUS_PRIORITY.__getitem__)
        checks_by_id[check_id] = replace(check, findings=provisional, status=status)

    ordered_checks = tuple(sorted(checks_by_id.values(), key=lambda item: item.check_id))
    ordered_diagnostics = tuple(
        sorted(
            diagnostics,
            key=lambda item: (item.code, item.check_id or "", item.path or "", item.message),
        )
    )
    return ordered_checks, ordered_diagnostics


def _configuration(check: GateCheckPolicy) -> dict[str, Any]:
    def thaw(value: Any) -> Any:
        if isinstance(value, tuple):
            if not value:
                return {}
            if all(
                isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
                for item in value
            ):
                return {item[0]: thaw(item[1]) for item in value}
            return [thaw(item) for item in value]
        return value

    return {key: thaw(value) for key, value in check.configuration}


def _new_finding(
    check: GateCheckPolicy,
    *,
    code: str,
    subject_id: str,
    observed_state: str,
    evidence_refs: Iterable[str],
    message: str,
    disposition: str | None = None,
) -> GateFinding:
    check_id = f"aecctx.policy.{check.check_id}"
    refs = tuple(evidence_refs)
    active_disposition = disposition or check.failure_mode
    return GateFinding(
        code=code,
        check_id=check_id,
        severity=check.severity,
        disposition=active_disposition,
        subject_id=subject_id,
        observed_state=observed_state,
        evidence_refs=refs,
        fingerprint=finding_fingerprint(
            check_id=check_id,
            code=code,
            subject_id=subject_id,
            observed_state=observed_state,
            evidence_refs=refs,
        ),
        message=message,
    )


def _check_result(
    check: GateCheckPolicy,
    findings: Iterable[GateFinding],
    *,
    evidence_refs: Iterable[str] = (),
    pass_message: str,
    failure_message: str,
) -> GateCheckResult:
    materialized = tuple(findings)
    status = max(
        (finding.disposition for finding in materialized),
        key=_STATUS_PRIORITY.__getitem__,
        default="pass",
    )
    refs = tuple(evidence_refs) + tuple(
        ref for finding in materialized for ref in finding.evidence_refs
    )
    return GateCheckResult(
        check_id=f"aecctx.policy.{check.check_id}",
        kind=check.kind,
        status=status,
        severity=check.severity,
        evidence_refs=refs,
        findings=materialized,
        message=pass_message if status == "pass" else failure_message,
    )


def evaluate_capability_check(check: GateCheckPolicy, manifest: Mapping[str, Any]) -> GateCheckResult:
    configuration = _configuration(check)
    required = configuration["capabilities"]
    observed = manifest.get("capabilities", {})
    findings: list[GateFinding] = []
    refs: list[str] = []
    for name, minimum in sorted(required.items()):
        ref = f"manifest.json#/capabilities/{name}"
        refs.append(ref)
        actual = observed.get(name)
        if actual is None:
            findings.append(
                _new_finding(
                    check,
                    code="AECCTX_GATE_CAPABILITY_MISSING",
                    subject_id=name,
                    observed_state="missing",
                    evidence_refs=(ref,),
                    message="required capability is absent",
                )
            )
        elif _SUPPORT_LEVEL[actual] < _SUPPORT_LEVEL[minimum]:
            findings.append(
                _new_finding(
                    check,
                    code="AECCTX_GATE_CAPABILITY_BELOW_MINIMUM",
                    subject_id=name,
                    observed_state=actual,
                    evidence_refs=(ref,),
                    message="capability is below the required level",
                )
            )
    return _check_result(
        check,
        findings,
        evidence_refs=refs,
        pass_message="capability minima are satisfied",
        failure_message="capability minima are not satisfied",
    )


def _diagnostic_records(store: RecordStore) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        record.raw for record in store.records.values() if record.record_type == "diagnostic"
    )


def evaluate_loss_check(
    check: GateCheckPolicy,
    manifest: Mapping[str, Any],
    store: RecordStore,
) -> GateCheckResult:
    configuration = _configuration(check)
    reasons = tuple(manifest.get("loss_summary", ()))
    diagnostics = _diagnostic_records(store)
    counts: dict[str, int] = {}
    findings: list[GateFinding] = []
    evidence: list[str] = ["manifest.json#/loss_summary"]
    for reason in sorted(reasons):
        matches = tuple(item for item in diagnostics if item.get("code") == reason)
        refs = tuple(str(item.get("record_id")) for item in matches if item.get("record_id"))
        evidence.extend(refs)
        if not matches:
            findings.append(
                _new_finding(
                    check,
                    code="AECCTX_GATE_LOSS_EVIDENCE_MISSING",
                    subject_id=reason,
                    observed_state="missing",
                    evidence_refs=("manifest.json#/loss_summary",),
                    message="loss reason has no authoritative diagnostic evidence",
                )
            )
            continue
        affected = tuple(item.get("affected_count") for item in matches)
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in affected):
            findings.append(
                _new_finding(
                    check,
                    code="AECCTX_GATE_LOSS_EVIDENCE_INCONSISTENT",
                    subject_id=reason,
                    observed_state="invalid_affected_count",
                    evidence_refs=refs,
                    message="loss evidence contains an invalid affected count",
                    disposition="error",
                )
            )
            continue
        counts[reason] = sum(affected)

    overall = sum(counts.values())
    overall_max = configuration.get("overall_max")
    if overall_max is not None and overall > overall_max:
        findings.append(
            _new_finding(
                check,
                code="AECCTX_GATE_LOSS_MAXIMUM_EXCEEDED",
                subject_id="loss.total",
                observed_state=str(overall),
                evidence_refs=("manifest.json#/loss_summary",),
                message="overall loss maximum is exceeded",
            )
        )
    maxima = configuration.get("reason_code_maxima")
    if isinstance(maxima, dict):
        for reason, observed_count in sorted(counts.items()):
            maximum = maxima.get(reason)
            if maximum is None or observed_count > maximum:
                findings.append(
                    _new_finding(
                        check,
                        code="AECCTX_GATE_LOSS_REASON_MAXIMUM_EXCEEDED",
                        subject_id=reason,
                        observed_state=str(observed_count),
                        evidence_refs=tuple(
                            str(item.get("record_id"))
                            for item in diagnostics
                            if item.get("code") == reason and item.get("record_id")
                        ),
                        message="loss reason maximum is exceeded or undeclared",
                    )
                )
    return _check_result(
        check,
        findings,
        evidence_refs=evidence,
        pass_message="loss evidence is within policy maxima",
        failure_message="loss evidence does not satisfy policy maxima",
    )


def _selected_values(value: Any, pointer: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        if "state" in value:
            yield pointer or "/"
        for key in sorted(value):
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from _selected_values(value[key], f"{pointer}/{escaped}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _selected_values(item, f"{pointer}/{index}")


def _exact_field(raw: Mapping[str, Any], field_path: str) -> tuple[bool, Any]:
    current: Any = raw
    for segment in field_path.split("."):
        if not isinstance(current, Mapping) or segment not in current:
            return False, None
        current = current[segment]
    return True, current


def evaluate_value_state_check(check: GateCheckPolicy, store: RecordStore) -> GateCheckResult:
    configuration = _configuration(check)
    record_types = set(configuration["record_types"])
    actions = configuration["actions"]
    field_path = configuration.get("field_path")
    findings: list[GateFinding] = []
    evidence: list[str] = []
    allowed = 0
    for record in store.records.values():
        if record.record_type not in record_types:
            continue
        evidence.append(record.record_id)
        if field_path is not None:
            present, selected = _exact_field(record.raw, field_path)
            if not present:
                findings.append(
                    _new_finding(
                        check,
                        code="AECCTX_GATE_VALUE_FIELD_MISSING",
                        subject_id=f"{record.record_id}#{field_path}",
                        observed_state="missing",
                        evidence_refs=(record.record_id,),
                        message="selected value-state field is absent",
                    )
                )
                continue
            selected_values = ((field_path, selected),)
        else:
            selected_values = tuple(_selected_values(record.raw))
        for location, selected in selected_values:
            subject = f"{record.record_id}#{location}"
            if not isinstance(selected, Mapping) or selected.get("state") not in VALUE_STATES:
                findings.append(
                    _new_finding(
                        check,
                        code="AECCTX_GATE_VALUE_STATE_INVALID",
                        subject_id=subject,
                        observed_state="invalid",
                        evidence_refs=(record.record_id,),
                        message="selected evidence is not a governed value state",
                        disposition="error",
                    )
                )
                continue
            state = str(selected["state"])
            if state == "known":
                continue
            action = actions[state]
            if action == "allow":
                allowed += 1
                continue
            code = (
                "AECCTX_GATE_VALUE_STATE_REQUIRES_REVIEW"
                if action == "requires_review"
                else "AECCTX_GATE_VALUE_STATE_FAILED"
            )
            findings.append(
                _new_finding(
                    check,
                    code=code,
                    subject_id=subject,
                    observed_state=state,
                    evidence_refs=(record.record_id,),
                    message="value state requires the policy action",
                    disposition=action,
                )
            )
    result = _check_result(
        check,
        findings,
        evidence_refs=evidence,
        pass_message="value states satisfy explicit policy actions",
        failure_message="value states require policy action",
    )
    if allowed and result.status == "pass":
        return replace(result, message=f"value states satisfy policy; {allowed} non-known value(s) explicitly allowed")
    return result


def evaluate_diagnostic_check(check: GateCheckPolicy, store: RecordStore) -> GateCheckResult:
    configuration = _configuration(check)
    threshold = configuration["threshold"]
    diagnostics = _diagnostic_records(store)
    findings: list[GateFinding] = []
    valid: list[Mapping[str, Any]] = []
    for item in diagnostics:
        code = item.get("code")
        severity = item.get("severity")
        if not isinstance(code, str) or not code or severity not in _SEVERITY_LEVEL:
            record_id = str(item.get("record_id") or "diagnostic.invalid")
            findings.append(
                _new_finding(
                    check,
                    code="AECCTX_GATE_DIAGNOSTIC_EVIDENCE_INVALID",
                    subject_id=record_id,
                    observed_state="invalid",
                    evidence_refs=(record_id,),
                    message="diagnostic evidence has invalid code or severity",
                    disposition="error",
                )
            )
        elif _SEVERITY_LEVEL[severity] >= _SEVERITY_LEVEL[threshold]:
            valid.append(item)
    refs = tuple(str(item["record_id"]) for item in valid)
    total = len(valid)
    if total > configuration["max_count"]:
        findings.append(
            _new_finding(
                check,
                code="AECCTX_GATE_DIAGNOSTIC_MAXIMUM_EXCEEDED",
                subject_id="diagnostics.total",
                observed_state=str(total),
                evidence_refs=refs,
                message="diagnostic maximum is exceeded",
            )
        )
    maxima = configuration.get("per_code_maxima")
    if isinstance(maxima, dict):
        by_code: dict[str, list[Mapping[str, Any]]] = {}
        for item in valid:
            by_code.setdefault(str(item["code"]), []).append(item)
        for code, items in sorted(by_code.items()):
            maximum = maxima.get(code)
            if maximum is not None and len(items) > maximum:
                findings.append(
                    _new_finding(
                        check,
                        code="AECCTX_GATE_DIAGNOSTIC_CODE_MAXIMUM_EXCEEDED",
                        subject_id=code,
                        observed_state=str(len(items)),
                        evidence_refs=tuple(str(item["record_id"]) for item in items),
                        message="diagnostic code maximum is exceeded",
                    )
                )
    return _check_result(
        check,
        findings,
        evidence_refs=refs,
        pass_message="diagnostic records are within policy maxima",
        failure_message="diagnostic records do not satisfy policy maxima",
    )


def _system_check(check_id: str, status: str, message: str, evidence_refs: Iterable[str] = ()) -> GateCheckResult:
    return GateCheckResult(
        check_id=check_id,
        kind="system",
        status=status,
        severity="blocking",
        evidence_refs=tuple(evidence_refs),
        findings=(),
        message=message,
    )


def _safe_diagnostic_path(path: str | None) -> str | None:
    if path is None or Path(path).is_absolute() or ".." in Path(path).parts:
        return None
    return path


def _preflight_diagnostics(validation: ValidationResult) -> tuple[GateDiagnostic, ...]:
    return tuple(
        GateDiagnostic(
            code=item.code,
            severity="error",
            message="candidate package validation failed",
            path=_safe_diagnostic_path(item.path),
            check_id=(
                "aecctx.system.integrity"
                if item.code in _INTEGRITY_CODES
                else "aecctx.system.validation"
            ),
        )
        for item in validation.diagnostics
    )


def _build_result(
    *,
    policy: GatePolicy,
    candidate_package_id: str | None,
    candidate_logical_digest: str | None,
    checks: tuple[GateCheckResult, ...],
    diagnostics: tuple[GateDiagnostic, ...],
    limits: GateLimits,
    baseline_package_id: str | None = None,
    baseline_logical_digest: str | None = None,
    evaluator_dependencies: tuple[tuple[str, str], ...] = (),
    ids_digest: str | None = None,
    ifc_source_id: str | None = None,
    ifc_source_digest: str | None = None,
) -> GateResult:
    findings = tuple(finding for check in checks for finding in check.findings)
    if len(findings) > limits.max_findings:
        raise GateError("AECCTX_GATE_FINDING_LIMIT_EXCEEDED", "gate result exceeds its finding limit")
    outcome, exit_code = aggregate_gate_outcome(checks)
    result = GateResult(
        evaluator_version=__version__,
        evaluator_dependencies=(("aecctx", __version__), *evaluator_dependencies),
        candidate_package_id=candidate_package_id,
        candidate_logical_digest=candidate_logical_digest,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        policy_digest=policy.digest,
        outcome=outcome,
        exit_code=exit_code,
        checks=checks,
        findings=findings,
        diagnostics=diagnostics,
        baseline_package_id=baseline_package_id,
        baseline_logical_digest=baseline_logical_digest,
        ids_digest=ids_digest,
        ifc_source_id=ifc_source_id,
        ifc_source_digest=ifc_source_digest,
    )
    if len(canonical_gate_json(result.to_dict())) > limits.max_result_bytes:
        raise GateError("AECCTX_GATE_RESULT_LIMIT_EXCEEDED", "gate result exceeds its byte limit")
    return result


def _invalid_candidate_result(
    policy: GatePolicy,
    validation: ValidationResult,
    limits: GateLimits,
) -> GateResult:
    diagnostics = _preflight_diagnostics(validation)
    integrity_error = any(item.code in _INTEGRITY_CODES for item in validation.diagnostics)
    validation_error = any(item.code not in _INTEGRITY_CODES for item in validation.diagnostics)
    checks = (
        _system_check(
            "aecctx.system.integrity",
            "error" if integrity_error else "pass",
            "candidate integrity validation failed" if integrity_error else "candidate integrity checks passed",
        ),
        _system_check("aecctx.system.policy", "pass", "policy validation and digest passed"),
        _system_check(
            "aecctx.system.validation",
            "error" if validation_error else "pass",
            "candidate structural validation failed" if validation_error else "candidate structural validation passed",
        ),
    )
    return _build_result(
        policy=policy,
        candidate_package_id=None,
        candidate_logical_digest=None,
        checks=checks,
        diagnostics=diagnostics,
        limits=limits,
    )


def evaluate_gate(
    candidate_package: str | Path,
    policy: GatePolicy,
    *,
    baseline_package: str | Path | None = None,
    ids_document: str | Path | bytes | None = None,
    ifc_source: str | Path | None = None,
    limits: GateLimits = GateLimits(),
) -> GateResult:
    if not isinstance(policy, GatePolicy):
        raise GateError("AECCTX_GATE_POLICY_INVALID", "policy must be a loaded GatePolicy")
    if not isinstance(limits, GateLimits):
        raise GateError("AECCTX_GATE_LIMIT_INVALID", "limits must be GateLimits")
    hard = GateLimits()
    if any(getattr(limits, field) > getattr(hard, field) for field in hard.__dataclass_fields__):
        raise GateError("AECCTX_GATE_LIMIT_INVALID", "limits exceed the v1 hard maximum")
    ids_policy_checks = tuple(check for check in policy.checks if check.kind == "ids.specification")
    ids_pair_supplied = ids_document is not None and ifc_source is not None
    ids_pair_incomplete = (ids_document is None) != (ifc_source is None)
    diff_required = any(check.kind == "diff.regression" for check in policy.checks)

    candidate_path = Path(candidate_package)
    if candidate_path.is_symlink():
        check = _system_check("aecctx.system.validation", "error", "candidate symlink root is forbidden")
        return _build_result(
            policy=policy,
            candidate_package_id=None,
            candidate_logical_digest=None,
            checks=(
                _system_check("aecctx.system.integrity", "pass", "candidate integrity checks did not run"),
                _system_check("aecctx.system.policy", "pass", "policy validation and digest passed"),
                check,
            ),
            diagnostics=(
                GateDiagnostic(
                    code="AECCTX_GATE_CANDIDATE_INVALID",
                    severity="error",
                    message="candidate symlink root is forbidden",
                    check_id="aecctx.system.validation",
                ),
            ),
            limits=limits,
        )
    initial = validate_package(candidate_path)
    if not initial.valid or initial.manifest is None:
        return _invalid_candidate_result(policy, initial, limits)

    with tempfile.TemporaryDirectory(prefix="aecctx-gate-") as temporary:
        snapshot = Path(temporary) / "candidate"
        try:
            PackageReader(candidate_path).extract_to(snapshot)
        except PackageReadError:
            return _build_result(
                policy=policy,
                candidate_package_id=None,
                candidate_logical_digest=None,
                checks=(
                    _system_check("aecctx.system.integrity", "error", "candidate changed during evaluation"),
                    _system_check("aecctx.system.policy", "pass", "policy validation and digest passed"),
                    _system_check("aecctx.system.validation", "error", "candidate changed during evaluation"),
                ),
                diagnostics=(
                    GateDiagnostic(
                        code="AECCTX_GATE_CANDIDATE_CHANGED_DURING_EVALUATION",
                        severity="error",
                        message="candidate changed during evaluation",
                        check_id="aecctx.system.validation",
                    ),
                ),
                limits=limits,
            )
        snapshot_validation = validate_package(snapshot)
        if (
            not snapshot_validation.valid
            or snapshot_validation.manifest is None
            or snapshot_validation.manifest != initial.manifest
        ):
            return _build_result(
                policy=policy,
                candidate_package_id=None,
                candidate_logical_digest=None,
                checks=(
                    _system_check("aecctx.system.integrity", "error", "candidate changed during evaluation"),
                    _system_check("aecctx.system.policy", "pass", "policy validation and digest passed"),
                    _system_check("aecctx.system.validation", "error", "candidate changed during evaluation"),
                ),
                diagnostics=(
                    GateDiagnostic(
                        code="AECCTX_GATE_CANDIDATE_CHANGED_DURING_EVALUATION",
                        severity="error",
                        message="candidate changed during evaluation",
                        check_id="aecctx.system.validation",
                    ),
                ),
                limits=limits,
            )
        store = RecordStore.open(snapshot)
        manifest = snapshot_validation.manifest
        baseline_snapshot: Path | None = None
        baseline_manifest: dict[str, Any] | None = None
        baseline_check: GateCheckResult | None = None

        def baseline_error(code: str, message: str) -> GateResult:
            return _build_result(
                policy=policy,
                candidate_package_id=str(manifest["package_id"]),
                candidate_logical_digest=str(manifest["logical_digest"]),
                checks=(
                    _system_check("aecctx.system.baseline", "error", message),
                    _system_check("aecctx.system.integrity", "pass", "candidate integrity checks passed", ("manifest.json",)),
                    _system_check("aecctx.system.policy", "pass", "policy validation and digest passed"),
                    _system_check("aecctx.system.validation", "pass", "candidate structural validation passed", ("manifest.json",)),
                ),
                diagnostics=(
                    GateDiagnostic(
                        code=code,
                        severity="error",
                        message=message,
                        check_id="aecctx.system.baseline",
                    ),
                ),
                limits=limits,
            )

        if baseline_package is None:
            if diff_required:
                return baseline_error("AECCTX_GATE_BASELINE_MISSING", "required baseline package is missing")
        else:
            baseline_path = Path(baseline_package)
            if baseline_path.is_symlink():
                return baseline_error("AECCTX_GATE_BASELINE_INVALID", "baseline package is invalid")
            baseline_initial = validate_package(baseline_path)
            if not baseline_initial.valid or baseline_initial.manifest is None:
                return baseline_error("AECCTX_GATE_BASELINE_INVALID", "baseline package is invalid")
            baseline_snapshot = Path(temporary) / "baseline"
            try:
                PackageReader(baseline_path).extract_to(baseline_snapshot)
            except PackageReadError:
                return baseline_error(
                    "AECCTX_GATE_BASELINE_CHANGED_DURING_EVALUATION",
                    "baseline changed during evaluation",
                )
            baseline_validation = validate_package(baseline_snapshot)
            if (
                not baseline_validation.valid
                or baseline_validation.manifest is None
                or baseline_validation.manifest != baseline_initial.manifest
            ):
                return baseline_error(
                    "AECCTX_GATE_BASELINE_CHANGED_DURING_EVALUATION",
                    "baseline changed during evaluation",
                )
            baseline_manifest = baseline_validation.manifest
            baseline_check = _system_check(
                "aecctx.system.baseline",
                "pass",
                "baseline structural and integrity validation passed",
                ("manifest.json",),
            )

        def ids_error(code: str, message: str) -> GateResult:
            return _build_result(
                policy=policy,
                candidate_package_id=str(manifest["package_id"]),
                candidate_logical_digest=str(manifest["logical_digest"]),
                checks=(
                    *((baseline_check,) if baseline_check is not None else ()),
                    _system_check("aecctx.system.ids-input", "error", message),
                    _system_check("aecctx.system.integrity", "pass", "candidate integrity checks passed", ("manifest.json",)),
                    _system_check("aecctx.system.policy", "pass", "policy validation and digest passed"),
                    _system_check("aecctx.system.validation", "pass", "candidate structural validation passed", ("manifest.json",)),
                ),
                diagnostics=(
                    GateDiagnostic(
                        code=code,
                        severity="error",
                        message=message,
                        check_id="aecctx.system.ids-input",
                    ),
                ),
                limits=limits,
                baseline_package_id=(str(baseline_manifest["package_id"]) if baseline_manifest is not None else None),
                baseline_logical_digest=(str(baseline_manifest["logical_digest"]) if baseline_manifest is not None else None),
            )

        if ids_pair_incomplete or (ids_policy_checks and not ids_pair_supplied):
            return ids_error("AECCTX_GATE_IDS_INPUT_PAIR_REQUIRED", "IDS document and IFC source are required together")
        if ids_pair_supplied and not ids_policy_checks:
            return ids_error("AECCTX_GATE_IDS_INPUT_INVALID", "IDS inputs require an ids.specification policy check")

        ids_path: Path | None = None
        if ids_pair_supplied:
            if isinstance(ids_document, bytes):
                if len(ids_document) > limits.max_ids_bytes:
                    return ids_error("AECCTX_GATE_IDS_LIMIT_EXCEEDED", "IDS input exceeds its byte limit")
                ids_path = Path(temporary) / "caller.ids"
                ids_path.write_bytes(ids_document)
            elif isinstance(ids_document, (str, Path)):
                ids_path = Path(ids_document)
            else:
                return ids_error("AECCTX_GATE_IDS_INPUT_INVALID", "IDS input type is invalid")
            if not isinstance(ifc_source, (str, Path)):
                return ids_error("AECCTX_GATE_IDS_INPUT_INVALID", "IFC source input type is invalid")

        policy_checks: list[GateCheckResult] = []
        ids_input_check: GateCheckResult | None = None
        ids_identity: tuple[str, str, str] | None = None
        ids_dependencies: tuple[tuple[str, str], ...] = ()
        for check in policy.checks:
            if check.kind == "capability.minimum":
                policy_checks.append(evaluate_capability_check(check, manifest))
            elif check.kind == "loss.maximum":
                policy_checks.append(evaluate_loss_check(check, manifest, store))
            elif check.kind == "value_state.action":
                policy_checks.append(evaluate_value_state_check(check, store))
            elif check.kind == "diagnostic.maximum":
                policy_checks.append(evaluate_diagnostic_check(check, store))
            elif check.kind == "diff.regression":
                if baseline_snapshot is None:
                    return baseline_error("AECCTX_GATE_BASELINE_MISSING", "required baseline package is missing")
                from .diff_checks import evaluate_diff_policy

                policy_checks.append(
                    evaluate_diff_policy(check, diff_packages(baseline_snapshot, snapshot))
                )
            elif check.kind == "ids.specification":
                from .ids import (
                    IdsEvaluationError,
                    dependency_versions,
                    evaluate_prepared_ids_check,
                    prepare_ids_input,
                )

                assert ids_path is not None and ifc_source is not None
                try:
                    prepared = prepare_ids_input(store, check, ids_path, Path(ifc_source), limits)
                    current_identity = (prepared.ids_digest, prepared.source_id, prepared.source_digest)
                    if ids_identity is not None and ids_identity != current_identity:
                        return ids_error("AECCTX_GATE_IDS_INPUT_INVALID", "IDS checks do not bind one input identity")
                    ids_identity = current_identity
                    policy_checks.append(evaluate_prepared_ids_check(check, prepared, limits))
                    if not prepared.unsupported:
                        ids_dependencies = dependency_versions()
                except IdsEvaluationError as error:
                    return ids_error(error.code, str(error))
                ids_input_check = _system_check(
                    "aecctx.system.ids-input",
                    "pass",
                    "IDS and IFC source binding checks passed",
                    (
                        f"ids:{prepared.ids_digest}",
                        f"source:{prepared.source_id}:{prepared.source_digest}",
                    ),
                )
            else:
                raise GateError("AECCTX_GATE_CHECK_NOT_IMPLEMENTED", "policy check kind is not implemented by this task")
        waived_checks, waiver_diagnostics = apply_waivers(tuple(policy_checks), policy)
        checks = (
            *((baseline_check,) if baseline_check is not None else ()),
            *((ids_input_check,) if ids_input_check is not None else ()),
            _system_check("aecctx.system.integrity", "pass", "candidate integrity checks passed", ("manifest.json",)),
            _system_check("aecctx.system.policy", "pass", "policy validation and digest passed"),
            _system_check("aecctx.system.validation", "pass", "candidate structural validation passed", ("manifest.json",)),
            *waived_checks,
        )
        return _build_result(
            policy=policy,
            candidate_package_id=str(manifest["package_id"]),
            candidate_logical_digest=str(manifest["logical_digest"]),
            checks=checks,
            diagnostics=waiver_diagnostics,
            limits=limits,
            baseline_package_id=(
                str(baseline_manifest["package_id"])
                if baseline_manifest is not None
                else None
            ),
            baseline_logical_digest=(
                str(baseline_manifest["logical_digest"])
                if baseline_manifest is not None
                else None
            ),
            evaluator_dependencies=ids_dependencies,
            ids_digest=ids_identity[0] if ids_identity is not None else None,
            ifc_source_id=ids_identity[1] if ids_identity is not None else None,
            ifc_source_digest=ids_identity[2] if ids_identity is not None else None,
        )
