from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..diff import PackageDiff
from .evaluator import finding_fingerprint
from .models import GateCheckPolicy, GateCheckResult, GateFinding


_STATUS_PRIORITY = {"pass": 0, "waived": 1, "requires_review": 2, "fail": 3, "error": 4}
_SUPPORT_LEVEL = {"unsupported": 0, "opaque": 1, "partial": 2, "full": 3}


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


def _finding(
    check: GateCheckPolicy,
    *,
    code: str,
    subject_id: str,
    observed_state: str,
    evidence_refs: Iterable[str],
    disposition: str,
    message: str,
) -> GateFinding:
    check_id = f"aecctx.policy.{check.check_id}"
    refs = tuple(evidence_refs)
    return GateFinding(
        code=code,
        check_id=check_id,
        severity=check.severity,
        disposition=disposition,
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


def evaluate_diff_policy(check: GateCheckPolicy, diff: PackageDiff) -> GateCheckResult:
    if not isinstance(check, GateCheckPolicy) or check.kind != "diff.regression":
        raise TypeError("check must be a diff.regression GateCheckPolicy")
    if not isinstance(diff, PackageDiff):
        raise TypeError("diff must be PackageDiff")
    actions = _configuration(check)["categories"]
    package_refs = (
        f"baseline-package:{diff.before_digest}",
        f"candidate-package:{diff.after_digest}",
    )
    findings: list[GateFinding] = []
    evidence: list[str] = list(package_refs)
    handled = False
    allowed = 0
    improvements = 0

    def observe(
        *,
        category: str,
        code: str,
        subject_id: str,
        observed_state: str,
        evidence_ref: str,
        message: str,
    ) -> None:
        nonlocal handled, allowed
        handled = True
        evidence.append(evidence_ref)
        action = actions[category]
        if action == "allow":
            allowed += 1
            return
        findings.append(
            _finding(
                check,
                code=code,
                subject_id=subject_id,
                observed_state=observed_state,
                evidence_refs=(*package_refs, evidence_ref),
                disposition=action,
                message=message,
            )
        )

    for record_id in diff.added_records:
        observe(
            category="added_records",
            code="AECCTX_GATE_DIFF_ADDED_RECORD",
            subject_id=record_id,
            observed_state="added",
            evidence_ref=record_id,
            message="baseline diff contains an added record",
        )
    for record_id in diff.removed_records:
        observe(
            category="removed_records",
            code="AECCTX_GATE_DIFF_REMOVED_RECORD",
            subject_id=record_id,
            observed_state="removed",
            evidence_ref=record_id,
            message="baseline diff contains a removed record",
        )
    for record_id in diff.changed_records:
        observe(
            category="changed_records",
            code="AECCTX_GATE_DIFF_CHANGED_RECORD",
            subject_id=record_id,
            observed_state="changed",
            evidence_ref=record_id,
            message="baseline diff contains a changed record",
        )
    for path in sorted(diff.authoritative_artifact_changes):
        observe(
            category="artifact_changes",
            code="AECCTX_GATE_DIFF_ARTIFACT_CHANGED",
            subject_id=path,
            observed_state="changed",
            evidence_ref=path,
            message="baseline diff contains an authoritative artifact change",
        )
    for capability, change in sorted(diff.capability_changes.items()):
        handled = True
        evidence_ref = f"manifest.json#/capabilities/{capability}"
        evidence.append(evidence_ref)
        before = change.get("before")
        after = change.get("after")
        is_regression = before in _SUPPORT_LEVEL and (
            after is None or (after in _SUPPORT_LEVEL and _SUPPORT_LEVEL[after] < _SUPPORT_LEVEL[before])
        )
        if not is_regression:
            improvements += 1
            continue
        action = actions["capability_regressions"]
        if action == "allow":
            allowed += 1
            continue
        after_state = "missing" if after is None else str(after)
        findings.append(
            _finding(
                check,
                code="AECCTX_GATE_CAPABILITY_REGRESSION",
                subject_id=capability,
                observed_state=f"{before}->{after_state}",
                evidence_refs=(*package_refs, evidence_ref),
                disposition=action,
                message="baseline diff contains a capability regression",
            )
        )
    if diff.loss_change is not None:
        observe(
            category="loss_changes",
            code="AECCTX_GATE_DIFF_LOSS_CHANGED",
            subject_id="manifest.loss_summary",
            observed_state="changed",
            evidence_ref="manifest.json#/loss_summary",
            message="baseline diff contains a loss-summary change",
        )
    for field in sorted(diff.identity_field_changes):
        observe(
            category="identity_changes",
            code="AECCTX_GATE_DIFF_IDENTITY_CHANGED",
            subject_id=f"manifest.{field}",
            observed_state="changed",
            evidence_ref=f"manifest.json#/{field}",
            message="baseline diff contains an identity change",
        )
    for field in sorted(diff.producer_field_changes):
        observe(
            category="producer_changes",
            code="AECCTX_GATE_DIFF_PRODUCER_CHANGED",
            subject_id=f"manifest.producer.{field}",
            observed_state="changed",
            evidence_ref=f"manifest.json#/producer/{field}",
            message="baseline diff contains a producer change",
        )
    if diff.version_changed:
        observe(
            category="version_changes",
            code="AECCTX_GATE_DIFF_VERSION_CHANGED",
            subject_id="manifest.aecctx_version",
            observed_state=f"{diff.before_version}->{diff.after_version}",
            evidence_ref="manifest.json#/aecctx_version",
            message="baseline diff contains a package-version change",
        )

    inconsistent = (
        (diff.loss_changed and diff.loss_change is None)
        or (diff.identity_changed and not diff.identity_field_changes)
        or (diff.producer_changed and not diff.producer_field_changes)
    )
    if inconsistent or (diff.semantic_change and not handled):
        evidence_ref = "diff:semantic"
        evidence.append(evidence_ref)
        findings.append(
            _finding(
                check,
                code="AECCTX_GATE_DIFF_CATEGORY_UNHANDLED",
                subject_id="diff.semantic",
                observed_state="unhandled",
                evidence_refs=(*package_refs, evidence_ref),
                disposition="error",
                message="semantic diff contains an unhandled category",
            )
        )

    materialized = tuple(findings)
    status = max(
        (finding.disposition for finding in materialized),
        key=_STATUS_PRIORITY.__getitem__,
        default="pass",
    )
    details = []
    if allowed:
        details.append(f"{allowed} change(s) explicitly allowed")
    if improvements:
        details.append(f"{improvements} capability improvement(s) observed")
    message = (
        "baseline semantic diff satisfies policy"
        if status == "pass"
        else "baseline semantic diff requires policy action"
    )
    if details:
        message = f"{message}; " + "; ".join(details)
    return GateCheckResult(
        check_id=f"aecctx.policy.{check.check_id}",
        kind=check.kind,
        status=status,
        severity=check.severity,
        evidence_refs=tuple(evidence),
        findings=materialized,
        message=message,
    )
