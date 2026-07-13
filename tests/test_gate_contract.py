from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from importlib.resources import files
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry

from aecctx.gate import (
    CHECK_KINDS,
    CHECK_STATUSES,
    OUTCOMES,
    SEVERITIES,
    VALUE_ACTIONS,
    GateCheckPolicy,
    GateCheckResult,
    GateDiagnostic,
    GateError,
    GateFinding,
    GateLimits,
    GatePolicy,
    GateResult,
    GateWaiver,
)


SCHEMA_NAMES = (
    "gate-check.schema.json",
    "gate-waiver.schema.json",
    "gate-policy.schema.json",
    "gate-result.schema.json",
)
SHA256 = "0" * 64


def test_gate_enums_match_the_normative_profile() -> None:
    assert CHECK_KINDS == frozenset(
        {
            "capability.minimum",
            "loss.maximum",
            "value_state.action",
            "diagnostic.maximum",
            "diff.regression",
            "ids.specification",
        }
    )
    assert CHECK_STATUSES == frozenset({"pass", "fail", "requires_review", "waived", "error"})
    assert OUTCOMES == frozenset({"pass", "fail", "requires_review", "error"})
    assert SEVERITIES == ("info", "warning", "error", "blocking")
    assert VALUE_ACTIONS == frozenset({"allow", "requires_review", "fail"})


def test_gate_limits_match_the_profile_and_reject_invalid_values() -> None:
    limits = GateLimits()
    assert limits == GateLimits(
        max_policy_bytes=1_048_576,
        max_ids_bytes=1_048_576,
        max_checks=256,
        max_waivers=1_024,
        max_ifc_bytes=268_435_456,
        max_findings=100_000,
        max_result_bytes=16_777_216,
        ids_timeout_seconds=60.0,
    )
    with pytest.raises(ValueError, match="max_checks must be positive"):
        GateLimits(max_checks=0)
    with pytest.raises(TypeError, match="max_checks must be an integer"):
        GateLimits(max_checks=1.5)  # type: ignore[arg-type]


def test_gate_finding_keeps_state_and_evidence_explicit_and_immutable() -> None:
    finding = GateFinding(
        code="AECCTX_GATE_VALUE_STATE_UNSUPPORTED",
        check_id="aecctx.policy.required-values",
        severity="error",
        subject_id="assertion:door-fire-rating",
        observed_state="unsupported",
        evidence_refs=("source:ifc", "assertion:door-fire-rating", "source:ifc"),
        fingerprint=SHA256,
        message="required value is unsupported",
    )

    assert finding.observed_state == "unsupported"
    assert finding.evidence_refs == ("assertion:door-fire-rating", "source:ifc")
    assert finding.waiver_id is None
    with pytest.raises(FrozenInstanceError):
        finding.message = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError, match="evidence_refs must be a tuple"):
        GateFinding(
            code="AECCTX_GATE_VALUE_STATE_UNSUPPORTED",
            check_id="aecctx.policy.required-values",
            severity="error",
            subject_id="assertion:door-fire-rating",
            observed_state="unsupported",
            evidence_refs=["source:ifc"],  # type: ignore[arg-type]
            fingerprint=SHA256,
            message="required value is unsupported",
        )


def test_public_models_reject_ungoverned_states_and_mutable_configuration() -> None:
    with pytest.raises(ValueError, match="severity has an ungoverned value"):
        GateDiagnostic(code="AECCTX_GATE_TEST", severity="critical", message="invalid")
    with pytest.raises(TypeError, match="configuration must be a tuple"):
        GateCheckPolicy(
            check_id="capabilities",
            kind="capability.minimum",
            severity="error",
            failure_mode="fail",
            configuration={"capabilities": {"ifc.read": "partial"}},  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="kind has an ungoverned value"):
        GateCheckPolicy(
            check_id="commands",
            kind="shell.execute",
            severity="blocking",
            failure_mode="fail",
            configuration=(),
        )


def test_gate_error_has_a_stable_code_and_safe_message() -> None:
    error = GateError("AECCTX_GATE_POLICY_INVALID", "gate policy is invalid")
    assert error.code == "AECCTX_GATE_POLICY_INVALID"
    assert str(error) == "gate policy is invalid"
    assert not hasattr(error, "raw_input")


def test_gate_result_to_dict_is_authoritative_and_deterministically_ordered() -> None:
    finding = GateFinding(
        code="AECCTX_GATE_CAPABILITY_BELOW_MINIMUM",
        check_id="aecctx.policy.capabilities",
        severity="error",
        subject_id="ifc.read",
        observed_state="opaque",
        evidence_refs=("manifest.json#/capabilities/ifc.read",),
        fingerprint=SHA256,
        message="capability is below the required level",
    )
    check = GateCheckResult(
        check_id="aecctx.policy.capabilities",
        kind="capability.minimum",
        status="fail",
        severity="error",
        evidence_refs=("manifest.json#/capabilities/ifc.read",),
        findings=(finding,),
        message="capability policy did not pass",
    )
    result = GateResult(
        evaluator_version="0.1.0",
        evaluator_dependencies=(("python", "3.12"), ("aecctx", "0.1.0")),
        candidate_package_id="candidate",
        candidate_logical_digest="1" * 64,
        policy_id="delivery",
        policy_version="1.0.0",
        policy_digest="2" * 64,
        outcome="fail",
        exit_code=1,
        checks=(check,),
        findings=(finding,),
        diagnostics=(GateDiagnostic(code="AECCTX_GATE_TEST", severity="info", message="bounded"),),
    )

    assert result.evaluator_dependencies == (("aecctx", "0.1.0"), ("python", "3.12"))
    assert result.to_dict() == {
        "profile": "https://aecctx.dev/gate/v1",
        "result_version": "1",
        "evaluator": {
            "version": "0.1.0",
            "dependencies": [
                {"name": "aecctx", "version": "0.1.0"},
                {"name": "python", "version": "3.12"},
            ],
        },
        "candidate": {"package_id": "candidate", "logical_digest": "1" * 64},
        "baseline": None,
        "policy": {"policy_id": "delivery", "policy_version": "1.0.0", "digest": "2" * 64},
        "ids_input": None,
        "outcome": "fail",
        "exit_code": 1,
        "checks": [check.to_dict()],
        "findings": [finding.to_dict()],
        "diagnostics": [
            {
                "code": "AECCTX_GATE_TEST",
                "severity": "info",
                "message": "bounded",
                "path": None,
                "check_id": None,
            }
        ],
    }


def test_policy_models_preserve_caller_order_and_are_frozen() -> None:
    check = GateCheckPolicy(
        check_id="capabilities",
        kind="capability.minimum",
        severity="error",
        failure_mode="fail",
        configuration=(("capabilities", (("ifc.read", "partial"),)),),
    )
    waiver = GateWaiver(
        waiver_id="reviewed-exception",
        check_id="aecctx.policy.capabilities",
        finding_fingerprint=SHA256,
        reason="reviewed exception",
        approved_by="delivery-authority",
        issued_at="2026-07-01T00:00:00Z",
        expires_at="2026-08-01T00:00:00Z",
    )
    policy = GatePolicy(
        profile="https://aecctx.dev/gate/v1",
        policy_id="delivery",
        policy_version="1.0.0",
        evaluation_time="2026-07-13T00:00:00Z",
        checks=(check,),
        waivers=(waiver,),
        digest=SHA256,
        canonical_bytes=b"{}\n",
    )

    assert policy.checks == (check,)
    assert policy.waivers == (waiver,)
    with pytest.raises(FrozenInstanceError):
        policy.policy_id = "other"  # type: ignore[misc]


@pytest.mark.parametrize("check_id", ["capabilities", "aecctx.system.validation"])
def test_waiver_model_requires_exact_policy_result_id(check_id: str) -> None:
    with pytest.raises(ValueError, match="aecctx.policy"):
        GateWaiver(
            waiver_id="reviewed-exception",
            check_id=check_id,
            finding_fingerprint=SHA256,
            reason="reviewed exception",
            approved_by="delivery-authority",
            issued_at="2026-07-01T00:00:00Z",
            expires_at="2026-08-01T00:00:00Z",
        )


def _load_public_schema(name: str) -> dict[str, object]:
    path = Path(__file__).parents[1] / "schemas" / "v0.2" / name
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_store() -> dict[str, dict[str, object]]:
    return {schema["$id"]: schema for schema in (_load_public_schema(name) for name in SCHEMA_NAMES)}


def test_gate_schemas_are_valid_closed_draft_202012_documents() -> None:
    for name in SCHEMA_NAMES:
        schema = _load_public_schema(name)
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False


def test_public_and_packaged_gate_schemas_are_byte_identical() -> None:
    repository = Path(__file__).parents[1] / "schemas" / "v0.2"
    packaged = files("aecctx.schemas.v0_2")

    for name in SCHEMA_NAMES:
        assert repository.joinpath(name).read_bytes() == packaged.joinpath(name).read_bytes()


def test_gate_check_schema_closes_kind_specific_configuration() -> None:
    schema = _load_public_schema("gate-check.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    valid = {
        "check_id": "capabilities",
        "kind": "capability.minimum",
        "severity": "error",
        "failure_mode": "fail",
        "configuration": {"capabilities": {"ifc.read": "partial"}},
    }
    validator.validate(valid)

    errors = list(validator.iter_errors({**valid, "configuration": {"command": "curl example.test"}}))
    assert errors
    errors = list(validator.iter_errors({**valid, "unexpected": True}))
    assert errors


@pytest.mark.parametrize(
    ("kind", "configuration"),
    [
        ("capability.minimum", {"capabilities": {"ifc.read": "partial"}}),
        ("loss.maximum", {"overall_max": 0, "reason_code_maxima": {"UNOBSERVED": 0}}),
        (
            "value_state.action",
            {
                "record_types": ["assertion"],
                "field_path": "value",
                "actions": {
                    "unknown": "requires_review",
                    "unsupported": "fail",
                    "conflicted": "fail",
                    "explicit_null": "requires_review",
                    "not_applicable": "allow",
                },
            },
        ),
        ("diagnostic.maximum", {"threshold": "error", "max_count": 0, "per_code_maxima": {}}),
        (
            "diff.regression",
            {
                "categories": {
                    "added_records": "allow",
                    "removed_records": "fail",
                    "changed_records": "requires_review",
                    "artifact_changes": "requires_review",
                    "capability_regressions": "fail",
                    "loss_changes": "requires_review",
                    "identity_changes": "fail",
                    "producer_changes": "requires_review",
                    "version_changes": "requires_review",
                }
            },
        ),
        ("ids.specification", {"ids_sha256": SHA256, "source_id": "source:ifc"}),
    ],
)
def test_each_check_kind_has_one_closed_configuration(kind: str, configuration: dict[str, object]) -> None:
    validator = Draft202012Validator(_load_public_schema("gate-check.schema.json"))
    document = {
        "check_id": "bounded-check",
        "kind": kind,
        "severity": "error",
        "failure_mode": "fail",
        "configuration": configuration,
    }

    validator.validate(document)
    assert list(validator.iter_errors({**document, "configuration": {**configuration, "command": "run"}}))


def test_gate_policy_and_result_schemas_accept_only_the_closed_contract() -> None:
    store = _schema_store()
    policy_schema = store["https://aecctx.dev/schemas/v0.2/gate-policy.schema.json"]
    result_schema = store["https://aecctx.dev/schemas/v0.2/gate-result.schema.json"]
    registry = Registry().with_contents(store.items())
    policy_validator = Draft202012Validator(policy_schema, registry=registry, format_checker=FormatChecker())
    result_validator = Draft202012Validator(result_schema, registry=registry, format_checker=FormatChecker())

    policy = {
        "profile": "https://aecctx.dev/gate/v1",
        "policy_id": "delivery",
        "policy_version": "1.0.0",
        "evaluation_time": "2026-07-13T00:00:00Z",
        "checks": [],
        "waivers": [],
    }
    policy_validator.validate(policy)
    assert list(policy_validator.iter_errors({**policy, "callback": "run"}))
    assert list(policy_validator.iter_errors({**policy, "policy_version": "1.0.0-01"}))

    waiver_schema = store["https://aecctx.dev/schemas/v0.2/gate-waiver.schema.json"]
    waiver_validator = Draft202012Validator(waiver_schema, format_checker=FormatChecker())
    waiver = {
        "waiver_id": "reviewed-exception",
        "check_id": "aecctx.policy.capabilities",
        "finding_fingerprint": SHA256,
        "reason": "reviewed exception",
        "approved_by": "delivery-authority",
        "issued_at": "2026-07-01T00:00:00Z",
        "expires_at": "2026-08-01T00:00:00Z",
    }
    waiver_validator.validate(waiver)
    assert list(waiver_validator.iter_errors({**waiver, "check_id": "capabilities"}))
    assert list(waiver_validator.iter_errors({**waiver, "check_id": "aecctx.system.validation"}))

    finding = GateFinding(
        code="AECCTX_GATE_CAPABILITY_BELOW_MINIMUM",
        check_id="aecctx.policy.capabilities",
        severity="error",
        subject_id="ifc.read",
        observed_state="opaque",
        evidence_refs=("manifest.json#/capabilities/ifc.read",),
        fingerprint=SHA256,
        message="capability is below the required level",
    )
    check = GateCheckResult(
        check_id="aecctx.policy.capabilities",
        kind="capability.minimum",
        status="fail",
        severity="error",
        evidence_refs=("manifest.json#/capabilities/ifc.read",),
        findings=(finding,),
        message="capability policy did not pass",
    )
    result = GateResult(
        evaluator_version="0.1.0",
        evaluator_dependencies=(("aecctx", "0.1.0"),),
        candidate_package_id="candidate",
        candidate_logical_digest="1" * 64,
        policy_id="delivery",
        policy_version="1.0.0",
        policy_digest="2" * 64,
        outcome="fail",
        exit_code=1,
        checks=(check,),
        findings=(finding,),
        diagnostics=(),
    ).to_dict()
    result_validator.validate(result)
    assert list(result_validator.iter_errors({**result, "approved": True}))
