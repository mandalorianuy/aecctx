from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime, timezone

from .models import GateCheckResult, GateDiagnostic, GateError, GatePolicy
from .policy import canonical_gate_json


_UTC_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
_STATUS_PRIORITY = {"pass": 0, "waived": 1, "requires_review": 2, "fail": 3, "error": 4}
_OUTCOME_EXIT = {"pass": 0, "requires_review": 1, "fail": 1, "error": 2}


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
