from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest

from aecctx.gate import (
    GateCheckResult,
    GateDiagnostic,
    GateFinding,
    GateResult,
    canonical_gate_json,
    evaluate_gate,
    load_gate_policy,
)


ROOT = Path(__file__).parents[1]
CANDIDATE = ROOT / "fixtures" / "minimal-aecctx"
SHA256 = "a" * 64
DIFF_CATEGORIES = {
    "added_records": "allow",
    "removed_records": "allow",
    "changed_records": "allow",
    "artifact_changes": "allow",
    "capability_regressions": "allow",
    "loss_changes": "allow",
    "identity_changes": "allow",
    "producer_changes": "allow",
    "version_changes": "allow",
}


def _run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "aecctx", *arguments],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def _policy_value(
    *,
    check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "profile": "https://aecctx.dev/gate/v1",
        "policy_id": "delivery",
        "policy_version": "1.0.0",
        "evaluation_time": "2026-07-13T00:00:00Z",
        "checks": [] if check is None else [check],
        "waivers": [],
    }


def _write_policy(
    tmp_path: Path,
    *,
    outcome: str = "pass",
    baseline: bool = False,
) -> Path:
    if baseline:
        check = {
            "check_id": "baseline",
            "kind": "diff.regression",
            "severity": "error",
            "failure_mode": "fail",
            "configuration": {"categories": DIFF_CATEGORIES},
        }
    elif outcome in {"fail", "requires_review"}:
        check = {
            "check_id": "geometry",
            "kind": "capability.minimum",
            "severity": "error",
            "failure_mode": "fail" if outcome == "fail" else "requires_review",
            "configuration": {"capabilities": {"ifc.read": "full"}},
        }
    else:
        check = None
    path = tmp_path / f"{outcome}{'-baseline' if baseline else ''}.json"
    path.write_bytes(canonical_gate_json(_policy_value(check=check)))
    return path


@pytest.mark.parametrize(
    ("outcome", "expected_exit"),
    (("pass", 0), ("fail", 1), ("requires_review", 1), ("error", 2)),
)
def test_gate_cli_exit_matches_authoritative_result(
    tmp_path: Path,
    outcome: str,
    expected_exit: int,
) -> None:
    policy = _write_policy(tmp_path, outcome=outcome)
    candidate = CANDIDATE if outcome != "error" else tmp_path / "missing-package"

    completed = _run_cli("gate", str(candidate), "--policy", str(policy), "--json")
    payload = json.loads(completed.stdout)

    assert completed.returncode == expected_exit, completed.stdout + completed.stderr
    assert completed.stderr == ""
    assert payload["ok"] is True
    assert payload["data"]["outcome"] == outcome
    assert payload["data"]["exit_code"] == expected_exit
    assert payload["diagnostics"] == payload["data"]["diagnostics"]


def test_gate_cli_control_failure_has_no_result_and_does_not_echo_input(tmp_path: Path) -> None:
    policy = tmp_path / "secret-policy.json"
    policy.write_bytes(b'{"secret":"do-not-echo"')

    completed = _run_cli("gate", str(CANDIDATE), "--policy", str(policy), "--json")
    payload = json.loads(completed.stdout)

    assert completed.returncode == 2
    assert payload["ok"] is False
    assert payload["data"] is None
    assert payload["diagnostics"][0]["code"] == "AECCTX_GATE_JSON_INVALID"
    assert "do-not-echo" not in completed.stdout + completed.stderr
    assert str(policy) not in completed.stdout + completed.stderr


def test_gate_cli_requires_ids_and_ifc_source_as_a_pair(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path)
    ids = tmp_path / "requirements.ids"
    ids.write_text("inert", encoding="utf-8")

    completed = _run_cli(
        "gate", str(CANDIDATE), "--policy", str(policy), "--ids", str(ids), "--json"
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 2
    assert payload["ok"] is True
    assert payload["data"]["outcome"] == "error"
    assert payload["diagnostics"][0]["code"] == "AECCTX_GATE_IDS_INPUT_PAIR_REQUIRED"


def test_gate_cli_missing_required_baseline_is_authoritative_error(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path, baseline=True)

    completed = _run_cli("gate", str(CANDIDATE), "--policy", str(policy), "--json")
    payload = json.loads(completed.stdout)

    assert completed.returncode == 2
    assert payload["ok"] is True
    assert payload["data"]["outcome"] == "error"
    assert payload["diagnostics"][0]["code"] == "AECCTX_GATE_BASELINE_MISSING"


def test_gate_result_canonical_bytes_are_the_authoritative_dictionary() -> None:
    policy = load_gate_policy(canonical_gate_json(_policy_value()))
    result = evaluate_gate(CANDIDATE, policy)

    assert result.canonical_bytes() == canonical_gate_json(result.to_dict())
    assert result.canonical_bytes().endswith(b"\n")
    assert not result.canonical_bytes().endswith(b"\n\n")


def test_gate_cli_writes_raw_result_and_all_derived_outputs(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path, outcome="fail")
    result_path = tmp_path / "result.json"
    markdown_path = tmp_path / "result.md"
    annotations_path = tmp_path / "annotations.jsonl"

    completed = _run_cli(
        "gate",
        str(CANDIDATE),
        "--policy",
        str(policy),
        "--output",
        str(result_path),
        "--markdown",
        str(markdown_path),
        "--ci-annotations",
        str(annotations_path),
        "--json",
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert result_path.read_bytes() == canonical_gate_json(payload["data"])
    assert markdown_path.read_bytes().endswith(b"\n")
    assert annotations_path.read_bytes().endswith(b"\n")


def _projection_result() -> GateResult:
    message = '<script>alert("x")</script> [follow](https://invalid.example)\n::error::boom'
    finding = GateFinding(
        code="AECCTX_GATE_TEST",
        check_id="aecctx.policy.geometry",
        severity="error",
        disposition="fail",
        subject_id="entity:test",
        observed_state="unsupported",
        evidence_refs=("entity:test", "manifest.json#/capabilities/3d_geometry"),
        fingerprint=SHA256,
        message=message,
    )
    check = GateCheckResult(
        check_id="aecctx.policy.geometry",
        kind="capability.minimum",
        status="fail",
        severity="error",
        evidence_refs=finding.evidence_refs,
        findings=(finding,),
        message=message,
    )
    return GateResult(
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
        diagnostics=(
            GateDiagnostic(
                code="AECCTX_GATE_TEST_DIAGNOSTIC",
                severity="warning",
                message=message,
                check_id=check.check_id,
            ),
        ),
    )


def test_markdown_and_ci_projection_preserve_authoritative_identity_as_inert_data() -> None:
    projection = import_module("aecctx.gate.projection")
    result = _projection_result()
    authoritative = result.to_dict()

    markdown = projection.render_gate_markdown(result).decode("utf-8")
    markdown_records = [json.loads(line[4:]) for line in markdown.splitlines() if line.startswith("    {")]
    annotations = [
        json.loads(line)
        for line in projection.render_ci_annotations(result).decode("utf-8").splitlines()
    ]

    assert "does not mean engineering approval" in markdown
    assert "<script>" not in markdown
    assert "[follow](" not in markdown
    assert all(item["annotation_version"] == "aecctx-ci-annotations-v1" for item in annotations)
    assert not any(line.startswith("::") for line in projection.render_ci_annotations(result).decode().splitlines())
    assert markdown_records[0]["outcome"] == authoritative["outcome"]
    assert annotations[0]["outcome"] == authoritative["outcome"]
    assert {item["check_id"] for item in markdown_records if "check_id" in item} == {
        item["check_id"] for item in authoritative["checks"]
    }
    assert {item["check_id"] for item in annotations if item["kind"] == "check"} == {
        item["check_id"] for item in authoritative["checks"]
    }
    assert {item["fingerprint"] for item in markdown_records if "fingerprint" in item} == {
        item["fingerprint"] for item in authoritative["findings"]
    }
    assert {item["fingerprint"] for item in annotations if item["kind"] == "finding"} == {
        item["fingerprint"] for item in authoritative["findings"]
    }
    assert {
        evidence
        for item in annotations
        for evidence in item.get("evidence_refs", [])
    } >= set(authoritative["findings"][0]["evidence_refs"])


def test_mutating_projection_text_cannot_change_reevaluation() -> None:
    projection = import_module("aecctx.gate.projection")
    policy = load_gate_policy(canonical_gate_json(_policy_value()))
    before = evaluate_gate(CANDIDATE, policy).canonical_bytes()
    mutated = bytearray(projection.render_gate_markdown(evaluate_gate(CANDIDATE, policy)))
    mutated.extend(b"\n# pretend outcome: fail\n")

    after = evaluate_gate(CANDIDATE, policy).canonical_bytes()

    assert mutated != projection.render_gate_markdown(evaluate_gate(CANDIDATE, policy))
    assert after == before


@pytest.mark.parametrize("target_kind", ("file", "directory", "symlink"))
def test_gate_outputs_never_replace_existing_targets(tmp_path: Path, target_kind: str) -> None:
    policy = _write_policy(tmp_path)
    output = tmp_path / "result.json"
    if target_kind == "file":
        output.write_bytes(b"preserve")
    elif target_kind == "directory":
        output.mkdir()
    else:
        target = tmp_path / "target.json"
        target.write_bytes(b"preserve")
        output.symlink_to(target)

    completed = _run_cli(
        "gate", str(CANDIDATE), "--policy", str(policy), "--output", str(output), "--json"
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 2
    assert payload["ok"] is False
    assert payload["diagnostics"][0]["code"] == "AECCTX_GATE_OUTPUT_EXISTS"
    if target_kind == "file":
        assert output.read_bytes() == b"preserve"


def test_gate_rejects_output_input_and_pairwise_collisions_before_publication(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path)
    shared = tmp_path / "shared.out"

    input_collision = _run_cli(
        "gate", str(CANDIDATE), "--policy", str(policy), "--output", str(policy), "--json"
    )
    pairwise_collision = _run_cli(
        "gate",
        str(CANDIDATE),
        "--policy",
        str(policy),
        "--output",
        str(shared),
        "--markdown",
        str(shared),
        "--json",
    )

    assert json.loads(input_collision.stdout)["diagnostics"][0]["code"] == "AECCTX_GATE_OUTPUT_CONFLICT"
    assert json.loads(pairwise_collision.stdout)["diagnostics"][0]["code"] == "AECCTX_GATE_OUTPUT_CONFLICT"
    assert not shared.exists()


def test_atomic_multi_output_failure_rolls_back_current_invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    atomic = import_module("aecctx._atomic")
    first = tmp_path / "first.out"
    second = tmp_path / "second.out"
    real_link = os.link
    calls = 0

    def fail_second(source: object, target: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("denied")
        real_link(source, target)

    monkeypatch.setattr(os, "link", fail_second)
    with pytest.raises(atomic.AtomicCreateError) as caught:
        atomic.atomic_create_many(((first, b"first"), (second, b"second")))

    assert caught.value.reason == "failed"
    assert not first.exists()
    assert not second.exists()
    assert list(tmp_path.iterdir()) == []


def test_gate_text_is_concise_projection_without_approval_language(tmp_path: Path) -> None:
    policy = _write_policy(tmp_path, outcome="requires_review")

    completed = _run_cli("gate", str(CANDIDATE), "--policy", str(policy))

    assert completed.returncode == 1
    assert "outcome=requires_review" in completed.stdout
    assert "projection only" in completed.stdout
    assert "approv" not in completed.stdout.lower()
    assert completed.stderr == ""


def test_root_help_registers_exact_gate_arguments() -> None:
    root = _run_cli("--help")
    gate = _run_cli("gate", "--help")

    assert root.returncode == 0
    assert "gate" in root.stdout
    for argument in (
        "--policy",
        "--baseline",
        "--ids",
        "--ifc-source",
        "--output",
        "--markdown",
        "--ci-annotations",
        "--json",
    ):
        assert argument in gate.stdout
