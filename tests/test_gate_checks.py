from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any

import pytest

from aecctx.gate import (
    GateCheckPolicy,
    GateCheckResult,
    GateError,
    GateFinding,
    GatePolicy,
    GateWaiver,
    aggregate_gate_outcome,
    apply_waivers,
    finding_fingerprint,
)


FP_A = "a" * 64
FP_B = "b" * 64
FP_C = "c" * 64


def _finding(
    *,
    fingerprint: str = FP_A,
    disposition: str = "fail",
    check_id: str = "aecctx.policy.capabilities",
    code: str = "AECCTX_GATE_CAPABILITY_BELOW_MINIMUM",
    subject_id: str = "ifc.read",
    observed_state: str = "opaque",
    evidence_refs: tuple[str, ...] = ("manifest.json#/capabilities/ifc.read",),
    message: str = "capability is below the required level",
    waiver_id: str | None = None,
) -> GateFinding:
    return GateFinding(
        code=code,
        check_id=check_id,
        severity="error",
        disposition=disposition,
        subject_id=subject_id,
        observed_state=observed_state,
        evidence_refs=evidence_refs,
        fingerprint=fingerprint,
        message=message,
        waiver_id=waiver_id,
    )


def _check(
    status: str,
    *,
    check_id: str = "aecctx.policy.capabilities",
    findings: tuple[GateFinding, ...] = (),
) -> GateCheckResult:
    return GateCheckResult(
        check_id=check_id,
        kind="capability.minimum",
        status=status,
        severity="error",
        evidence_refs=tuple(ref for finding in findings for ref in finding.evidence_refs),
        findings=findings,
        message="bounded check result",
    )


def _policy_check(check_id: str) -> GateCheckPolicy:
    short_id = check_id.removeprefix("aecctx.policy.")
    return GateCheckPolicy(
        check_id=short_id,
        kind="capability.minimum",
        severity="error",
        failure_mode="fail",
        configuration=(("capabilities", (("ifc.read", "partial"),)),),
    )


def _waiver(
    *,
    waiver_id: str = "exception",
    check_id: str = "aecctx.policy.capabilities",
    fingerprint: str = FP_A,
    issued_at: str = "2026-07-01T00:00:00Z",
    expires_at: str = "2026-08-01T00:00:00Z",
) -> GateWaiver:
    return GateWaiver(
        waiver_id=waiver_id,
        check_id=check_id,
        finding_fingerprint=fingerprint,
        reason="reviewed exception",
        approved_by="delivery-authority",
        issued_at=issued_at,
        expires_at=expires_at,
    )


def _policy(
    waivers: tuple[GateWaiver, ...] = (),
    *,
    evaluation_time: str = "2026-07-13T00:00:00Z",
    check_ids: tuple[str, ...] = ("aecctx.policy.capabilities",),
) -> GatePolicy:
    return GatePolicy(
        profile="https://aecctx.dev/gate/v1",
        policy_id="delivery",
        policy_version="1.0.0",
        evaluation_time=evaluation_time,
        checks=tuple(_policy_check(check_id) for check_id in check_ids),
        waivers=waivers,
        digest="0" * 64,
        canonical_bytes=b"{}\n",
    )


def test_finding_fingerprint_has_one_canonical_identity() -> None:
    actual = finding_fingerprint(
        check_id="aecctx.policy.capabilities",
        code="AECCTX_GATE_CAPABILITY_BELOW_MINIMUM",
        subject_id="ifc.read",
        observed_state="opaque",
        evidence_refs=("z", "a", "z"),
    )
    canonical = (
        b'{"check_id":"aecctx.policy.capabilities",'
        b'"code":"AECCTX_GATE_CAPABILITY_BELOW_MINIMUM",'
        b'"evidence_refs":["a","z"],"observed_state":"opaque",'
        b'"subject_id":"ifc.read"}\n'
    )
    assert actual == hashlib.sha256(canonical).hexdigest()
    assert actual == finding_fingerprint(
        check_id="aecctx.policy.capabilities",
        code="AECCTX_GATE_CAPABILITY_BELOW_MINIMUM",
        subject_id="ifc.read",
        observed_state="opaque",
        evidence_refs=("a", "z"),
    )


def test_finding_fingerprint_normalizes_nfc_and_excludes_presentation_state() -> None:
    decomposed = finding_fingerprint(
        check_id="aecctx.policy.capabilities",
        code="AECCTX_GATE_TEST",
        subject_id="cafe\u0301",
        observed_state="opaque",
        evidence_refs=(),
    )
    composed = finding_fingerprint(
        check_id="aecctx.policy.capabilities",
        code="AECCTX_GATE_TEST",
        subject_id="caf\u00e9",
        observed_state="opaque",
        evidence_refs=(),
    )
    assert decomposed == composed
    original = _finding(fingerprint=composed, disposition="fail", message="first")
    presented = replace(original, message="different presentation")
    assert original.fingerprint == presented.fingerprint


@pytest.mark.parametrize(
    "overrides",
    [
        {"check_id": ""},
        {"code": ""},
        {"subject_id": ""},
        {"observed_state": ""},
        {"evidence_refs": ("",)},
        {"evidence_refs": (1,)},
    ],
)
def test_finding_fingerprint_rejects_incomplete_identity(overrides: dict[str, Any]) -> None:
    values: dict[str, Any] = {
        "check_id": "aecctx.policy.capabilities",
        "code": "AECCTX_GATE_TEST",
        "subject_id": "ifc.read",
        "observed_state": "opaque",
        "evidence_refs": (),
    }
    values.update(overrides)
    with pytest.raises(GateError) as caught:
        finding_fingerprint(**values)
    assert caught.value.code == "AECCTX_GATE_FINDING_IDENTITY_INVALID"


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ((), ("pass", 0)),
        (("pass",), ("pass", 0)),
        (("pass", "requires_review"), ("requires_review", 1)),
        (("waived",), ("requires_review", 1)),
        (("requires_review", "fail"), ("fail", 1)),
        (("fail", "error"), ("error", 2)),
    ],
)
def test_aggregate_precedence(statuses: tuple[str, ...], expected: tuple[str, int]) -> None:
    assert aggregate_gate_outcome(tuple(_check(status) for status in statuses)) == expected
    assert aggregate_gate_outcome(tuple(_check(status) for status in reversed(statuses))) == expected


def test_active_waiver_changes_only_exact_finding_and_recomputes_mixed_check() -> None:
    failing = _finding(fingerprint=FP_A, disposition="fail", message="must remain")
    review = _finding(
        fingerprint=FP_B,
        disposition="requires_review",
        code="AECCTX_GATE_CAPABILITY_MISSING_EVIDENCE",
        subject_id="ifc.write",
    )
    check = _check("fail", findings=(review, failing))

    checks, diagnostics = apply_waivers((check,), _policy((_waiver(),)))

    assert diagnostics == ()
    assert checks[0].status == "requires_review"
    waived = next(item for item in checks[0].findings if item.fingerprint == FP_A)
    assert waived.disposition == "waived"
    assert waived.waiver_id == "exception"
    assert waived.message == "must remain"
    assert waived.observed_state == failing.observed_state
    assert waived.evidence_refs == failing.evidence_refs
    assert waived.fingerprint == failing.fingerprint
    assert next(item for item in checks[0].findings if item.fingerprint == FP_B) == review


@pytest.mark.parametrize("disposition", ["fail", "requires_review"])
def test_exact_active_waiver_makes_single_finding_check_waived(disposition: str) -> None:
    finding = _finding(disposition=disposition)
    check = _check(disposition, findings=(finding,))
    checks, diagnostics = apply_waivers((check,), _policy((_waiver(),)))

    assert diagnostics == ()
    assert checks[0].status == "waived"
    assert checks[0].findings[0].disposition == "waived"
    assert aggregate_gate_outcome(checks) == ("requires_review", 1)


@pytest.mark.parametrize(
    ("issued_at", "expires_at", "code"),
    [
        ("2026-06-01T00:00:00Z", "2026-07-13T00:00:00Z", "AECCTX_GATE_WAIVER_EXPIRED"),
        ("2026-07-14T00:00:00Z", "2026-08-01T00:00:00Z", "AECCTX_GATE_WAIVER_NOT_YET_VALID"),
    ],
)
def test_inactive_waiver_retains_original_check_and_emits_warning(
    issued_at: str,
    expires_at: str,
    code: str,
) -> None:
    check = _check("fail", findings=(_finding(),))
    waiver = _waiver(issued_at=issued_at, expires_at=expires_at)

    checks, diagnostics = apply_waivers((check,), _policy((waiver,)))

    assert checks == (check,)
    assert tuple(item.code for item in diagnostics) == (code,)
    assert diagnostics[0].severity == "warning"
    assert diagnostics[0].check_id == check.check_id


def test_active_waiver_is_inclusive_at_issued_at() -> None:
    waiver = _waiver(issued_at="2026-07-13T00:00:00Z")
    checks, diagnostics = apply_waivers(
        (_check("fail", findings=(_finding(),)),),
        _policy((waiver,)),
    )
    assert diagnostics == ()
    assert checks[0].status == "waived"


def test_active_mismatched_waiver_forces_review_instead_of_silent_pass() -> None:
    check = _check("pass")
    checks, diagnostics = apply_waivers((check,), _policy((_waiver(),)))

    assert checks[0].status == "requires_review"
    assert tuple(item.code for item in diagnostics) == ("AECCTX_GATE_WAIVER_FINDING_MISMATCH",)
    assert diagnostics[0].severity == "warning"
    assert aggregate_gate_outcome(checks) == ("requires_review", 1)


def test_waiver_output_order_is_independent_of_check_and_policy_order() -> None:
    check_a = _check("fail", findings=(_finding(),))
    check_b_id = "aecctx.policy.secondary"
    check_b = _check(
        "fail",
        check_id=check_b_id,
        findings=(_finding(check_id=check_b_id, fingerprint=FP_B, subject_id="ifc.write"),),
    )
    waiver_a = _waiver(expires_at="2026-07-13T00:00:00Z")
    waiver_b = _waiver(
        waiver_id="secondary-exception",
        check_id=check_b_id,
        fingerprint=FP_B,
        expires_at="2026-07-13T00:00:00Z",
    )

    left = apply_waivers(
        (check_b, check_a),
        _policy((waiver_b, waiver_a), check_ids=(check_b_id, check_a.check_id)),
    )
    right = apply_waivers(
        (check_a, check_b),
        _policy((waiver_a, waiver_b), check_ids=(check_a.check_id, check_b_id)),
    )

    assert left == right
    assert tuple(item.check_id for item in left[0]) == (check_a.check_id, check_b_id)
    assert tuple((item.code, item.check_id) for item in left[1]) == (
        ("AECCTX_GATE_WAIVER_EXPIRED", check_a.check_id),
        ("AECCTX_GATE_WAIVER_EXPIRED", check_b_id),
    )


def test_exact_waiver_and_active_mismatch_apply_one_order_independent_review_floor() -> None:
    check = _check("fail", findings=(_finding(),))
    exact = _waiver(waiver_id="exact")
    mismatch = _waiver(waiver_id="mismatch", fingerprint=FP_B)

    left = apply_waivers((check,), _policy((exact, mismatch)))
    right = apply_waivers((check,), _policy((mismatch, exact)))

    assert left == right
    assert left[0][0].status == "requires_review"
    assert left[0][0].findings[0].disposition == "waived"
    assert left[0][0].findings[0].waiver_id == "exact"
    assert tuple(item.code for item in left[1]) == ("AECCTX_GATE_WAIVER_FINDING_MISMATCH",)
    assert aggregate_gate_outcome(left[0]) == ("requires_review", 1)


def test_duplicate_waiver_target_is_rejected() -> None:
    first = _waiver(waiver_id="first")
    second = _waiver(waiver_id="second")
    with pytest.raises(GateError) as caught:
        apply_waivers((_check("fail", findings=(_finding(),)),), _policy((first, second)))
    assert caught.value.code == "AECCTX_GATE_WAIVER_DUPLICATE_TARGET"


def test_duplicate_waiver_id_is_rejected_even_for_different_targets() -> None:
    secondary_id = "aecctx.policy.secondary"
    first = _waiver(waiver_id="duplicate")
    second = _waiver(
        waiver_id="duplicate",
        check_id=secondary_id,
        fingerprint=FP_B,
    )
    checks = (
        _check("fail", findings=(_finding(),)),
        _check(
            "fail",
            check_id=secondary_id,
            findings=(_finding(check_id=secondary_id, fingerprint=FP_B),),
        ),
    )
    with pytest.raises(GateError) as caught:
        apply_waivers(
            checks,
            _policy((first, second), check_ids=(checks[0].check_id, secondary_id)),
        )
    assert caught.value.code == "AECCTX_GATE_WAIVER_ID_DUPLICATE"


def test_missing_or_system_waiver_check_is_rejected() -> None:
    waiver = _waiver()
    with pytest.raises(GateError) as missing:
        apply_waivers((), _policy((waiver,)))
    assert missing.value.code == "AECCTX_GATE_WAIVER_CHECK_MISSING"

    object.__setattr__(waiver, "check_id", "aecctx.system.validation")
    with pytest.raises(GateError) as system:
        apply_waivers((_check("pass"),), _policy((waiver,)))
    assert system.value.code == "AECCTX_GATE_WAIVER_CHECK_INVALID"


@pytest.mark.parametrize(
    ("policy", "code"),
    [
        (_policy((_waiver(issued_at="2026-08-02T00:00:00Z", expires_at="2026-08-01T00:00:00Z"),)), "AECCTX_GATE_WAIVER_INTERVAL_INVALID"),
        (_policy((_waiver(),), evaluation_time="not-a-clock"), "AECCTX_GATE_WAIVER_INTERVAL_INVALID"),
    ],
)
def test_invalid_waiver_lifecycle_is_control_error(policy: GatePolicy, code: str) -> None:
    with pytest.raises(GateError) as caught:
        apply_waivers((_check("fail", findings=(_finding(),)),), policy)
    assert caught.value.code == code


@pytest.mark.parametrize(
    "finding",
    [
        _finding(disposition="error"),
        _finding(disposition="waived", waiver_id="previous"),
    ],
)
def test_error_or_already_waived_finding_cannot_be_waived(finding: GateFinding) -> None:
    with pytest.raises(GateError) as caught:
        apply_waivers((_check(finding.disposition, findings=(finding,)),), _policy((_waiver(),)))
    assert caught.value.code == "AECCTX_GATE_WAIVER_DISPOSITION_INVALID"
