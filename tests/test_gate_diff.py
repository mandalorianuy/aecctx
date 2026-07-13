from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from aecctx.diff import PackageDiff
from aecctx.gate import canonical_gate_json, evaluate_gate, load_gate_policy
from aecctx.gate.diff_checks import evaluate_diff_policy


FIXTURE = Path(__file__).parents[1] / "fixtures" / "minimal-aecctx"
CATEGORIES = (
    "added_records",
    "removed_records",
    "changed_records",
    "artifact_changes",
    "capability_regressions",
    "loss_changes",
    "identity_changes",
    "producer_changes",
    "version_changes",
)


def _policy(*, checks: list[dict[str, Any]] | None = None):
    return load_gate_policy(
        canonical_gate_json(
            {
                "profile": "https://aecctx.dev/gate/v1",
                "policy_id": "delivery",
                "policy_version": "1.0.0",
                "evaluation_time": "2026-07-13T00:00:00Z",
                "checks": checks or [],
                "waivers": [],
            }
        )
    )


def _diff_policy(**actions: str):
    categories = {name: "allow" for name in CATEGORIES}
    categories.update(actions)
    return _policy(
        checks=[
            {
                "check_id": "baseline",
                "kind": "diff.regression",
                "severity": "error",
                "failure_mode": "fail",
                "configuration": {"categories": categories},
            }
        ]
    )


def _empty_diff() -> PackageDiff:
    return PackageDiff(
        before_version="0.1.0",
        after_version="0.1.0",
        before_digest="1" * 64,
        after_digest="2" * 64,
        added_records=(),
        removed_records=(),
        changed_records=(),
        artifact_changes={},
        authoritative_artifact_changes={},
        capability_changes={},
        loss_changed=False,
        loss_change=None,
        identity_changed=False,
        identity_field_changes={},
        producer_changed=False,
        producer_field_changes={},
    )


@pytest.mark.parametrize(
    ("category", "changes", "code", "subject", "evidence"),
    [
        ("added_records", {"added_records": ("entity:new",)}, "AECCTX_GATE_DIFF_ADDED_RECORD", "entity:new", "entity:new"),
        ("removed_records", {"removed_records": ("entity:old",)}, "AECCTX_GATE_DIFF_REMOVED_RECORD", "entity:old", "entity:old"),
        ("changed_records", {"changed_records": ("entity:changed",)}, "AECCTX_GATE_DIFF_CHANGED_RECORD", "entity:changed", "entity:changed"),
        (
            "artifact_changes",
            {"authoritative_artifact_changes": {"geometry/model.glb": {"before": "a", "after": "b"}}},
            "AECCTX_GATE_DIFF_ARTIFACT_CHANGED",
            "geometry/model.glb",
            "geometry/model.glb",
        ),
        (
            "capability_regressions",
            {"capability_changes": {"identity": {"before": "full", "after": "partial"}}},
            "AECCTX_GATE_CAPABILITY_REGRESSION",
            "identity",
            "manifest.json#/capabilities/identity",
        ),
        (
            "loss_changes",
            {"loss_changed": True, "loss_change": {"before": [], "after": ["LOSS"]}},
            "AECCTX_GATE_DIFF_LOSS_CHANGED",
            "manifest.loss_summary",
            "manifest.json#/loss_summary",
        ),
        (
            "identity_changes",
            {
                "identity_changed": True,
                "identity_field_changes": {"package_id": {"before": "before", "after": "after"}},
            },
            "AECCTX_GATE_DIFF_IDENTITY_CHANGED",
            "manifest.package_id",
            "manifest.json#/package_id",
        ),
        (
            "producer_changes",
            {
                "producer_changed": True,
                "producer_field_changes": {"version": {"before": "1", "after": "2"}},
            },
            "AECCTX_GATE_DIFF_PRODUCER_CHANGED",
            "manifest.producer.version",
            "manifest.json#/producer/version",
        ),
        (
            "version_changes",
            {"after_version": "0.2.0"},
            "AECCTX_GATE_DIFF_VERSION_CHANGED",
            "manifest.aecctx_version",
            "manifest.json#/aecctx_version",
        ),
    ],
)
def test_each_semantic_diff_category_has_exact_finding_and_evidence(
    category: str,
    changes: dict[str, Any],
    code: str,
    subject: str,
    evidence: str,
) -> None:
    diff = replace(_empty_diff(), **changes)
    check = evaluate_diff_policy(_diff_policy(**{category: "fail"}).checks[0], diff)

    assert check.status == "fail"
    assert len(check.findings) == 1
    finding = check.findings[0]
    assert finding.code == code
    assert finding.subject_id == subject
    assert finding.evidence_refs == tuple(
        sorted((evidence, f"candidate-package:{diff.after_digest}", f"baseline-package:{diff.before_digest}"))
    )


@pytest.mark.parametrize(
    ("action", "expected_status", "expected_findings"),
    [("allow", "pass", 0), ("requires_review", "requires_review", 1), ("fail", "fail", 1)],
)
def test_diff_category_action_is_exact(action: str, expected_status: str, expected_findings: int) -> None:
    diff = replace(_empty_diff(), added_records=("entity:new",))
    check = evaluate_diff_policy(_diff_policy(added_records=action).checks[0], diff)
    assert check.status == expected_status
    assert len(check.findings) == expected_findings
    assert "entity:new" in check.evidence_refs


@pytest.mark.parametrize(
    ("before", "after", "expected_findings"),
    [
        ("full", "partial", 1),
        ("partial", None, 1),
        ("partial", "full", 0),
        (None, "unsupported", 0),
    ],
)
def test_capability_diff_preserves_missing_and_distinguishes_improvement(
    before: str | None,
    after: str | None,
    expected_findings: int,
) -> None:
    diff = replace(
        _empty_diff(),
        capability_changes={"identity": {"before": before, "after": after}},
    )
    check = evaluate_diff_policy(
        _diff_policy(capability_regressions="fail").checks[0],
        diff,
    )
    assert len(check.findings) == expected_findings
    assert "manifest.json#/capabilities/identity" in check.evidence_refs
    if after is None and expected_findings:
        assert check.findings[0].observed_state == "partial->missing"


def test_unmapped_semantic_diff_is_error() -> None:
    inconsistent = replace(_empty_diff(), identity_changed=True)
    check = evaluate_diff_policy(_diff_policy().checks[0], inconsistent)
    assert check.status == "error"
    assert check.findings[0].code == "AECCTX_GATE_DIFF_CATEGORY_UNHANDLED"


def _rehash(package: Path) -> None:
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest_lines: list[bytes] = []
    for artifact in manifest["artifacts"]:
        data = (package / artifact["path"]).read_bytes()
        artifact["bytes"] = len(data)
        artifact["sha256"] = hashlib.sha256(data).hexdigest()
        digest_lines.append(f"{artifact['path']}\0{artifact['sha256']}\0{artifact['bytes']}\n".encode())
    manifest["logical_digest"] = hashlib.sha256(b"".join(sorted(digest_lines))).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")


def _copy_package(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copytree(FIXTURE, target)
    return target


def test_missing_required_baseline_is_system_error(minimal_package: Path) -> None:
    result = evaluate_gate(minimal_package, _diff_policy())
    assert result.outcome == "error"
    assert result.baseline_package_id is None
    assert any(
        check.check_id == "aecctx.system.baseline" and check.status == "error"
        for check in result.checks
    )
    assert result.diagnostics[0].code == "AECCTX_GATE_BASELINE_MISSING"


def test_invalid_baseline_is_error_without_invented_identity(tmp_path: Path, minimal_package: Path) -> None:
    baseline = _copy_package(tmp_path, "invalid-baseline")
    (baseline / "evidence" / "assertions.jsonl").write_bytes(b"corrupt\n")
    result = evaluate_gate(minimal_package, _diff_policy(), baseline_package=baseline)
    assert result.outcome == "error"
    assert result.candidate_package_id == "pkg_minimal_fixture"
    assert result.baseline_package_id is None
    assert result.diagnostics[0].code == "AECCTX_GATE_BASELINE_INVALID"


def test_supplied_unused_baseline_is_recorded_without_policy_check(minimal_package: Path) -> None:
    result = evaluate_gate(minimal_package, _policy(), baseline_package=minimal_package)
    assert result.outcome == "pass"
    assert result.baseline_package_id == "pkg_minimal_fixture"
    assert result.baseline_logical_digest == result.candidate_logical_digest
    assert any(check.check_id == "aecctx.system.baseline" for check in result.checks)
    assert not any(check.kind == "diff.regression" for check in result.checks)


def test_capability_downgrade_cites_both_package_digests(tmp_path: Path) -> None:
    baseline = _copy_package(tmp_path, "baseline")
    candidate = _copy_package(tmp_path, "candidate")
    for package, level in ((baseline, "full"), (candidate, "partial")):
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["capabilities"]["identity"] = level
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        _rehash(package)

    result = evaluate_gate(
        candidate,
        _diff_policy(capability_regressions="fail"),
        baseline_package=baseline,
    )
    finding = next(item for item in result.findings if item.code == "AECCTX_GATE_CAPABILITY_REGRESSION")
    assert result.outcome == "fail"
    assert finding.evidence_refs == tuple(
        sorted(
            (
                "manifest.json#/capabilities/identity",
                f"candidate-package:{result.candidate_logical_digest}",
                f"baseline-package:{result.baseline_logical_digest}",
            )
        )
    )


def test_generated_markdown_and_archive_metadata_do_not_regress(tmp_path: Path) -> None:
    candidate = _copy_package(tmp_path, "candidate")
    (candidate / "context" / "index.md").write_text("generated projection changed\n", encoding="utf-8")
    _rehash(candidate)
    result = evaluate_gate(candidate, _diff_policy(artifact_changes="fail"), baseline_package=FIXTURE)
    assert result.outcome == "pass"

    archive = tmp_path / "candidate.aecctx"
    with zipfile.ZipFile(archive, "w") as output:
        for path in sorted(FIXTURE.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(FIXTURE).as_posix())
    archive_result = evaluate_gate(archive, _diff_policy(), baseline_package=FIXTURE)
    assert archive_result.outcome == "pass"


def test_ids_input_without_policy_or_source_is_explicit_system_error(minimal_package: Path) -> None:
    result = evaluate_gate(minimal_package, _policy(), ids_document=b"<ids/>")
    assert result.outcome == "error"
    assert result.diagnostics[0].code == "AECCTX_GATE_IDS_INPUT_PAIR_REQUIRED"
