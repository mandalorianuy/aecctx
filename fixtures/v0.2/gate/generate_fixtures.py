#!/usr/bin/env python3
"""Generate deterministic project-authored ACX-21 gate fixtures and corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from aecctx.adapters.ifc import ingest_ifc  # noqa: E402
from aecctx.gate import GateError, canonical_gate_json, evaluate_gate, load_gate_policy  # noqa: E402
from aecctx.package import PackageArtifact, PackageWriter, canonical_json  # noqa: E402


FIXED_TIME = "2026-07-13T00:00:00Z"
CLAIM_ID = "quality-gate.policy-ids"
PROFILE = "aecctx-gate-v1-ids-1.0-simple-v1"
DIFF_CATEGORIES = {
    "added_records": "allow",
    "removed_records": "allow",
    "changed_records": "fail",
    "artifact_changes": "allow",
    "capability_regressions": "allow",
    "loss_changes": "allow",
    "identity_changes": "allow",
    "producer_changes": "allow",
    "version_changes": "allow",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _policy(checks: list[dict[str, Any]], *, waivers: list[dict[str, Any]] | None = None) -> bytes:
    return canonical_gate_json(
        {
            "profile": "https://aecctx.dev/gate/v1",
            "policy_id": "delivery",
            "policy_version": "1.0.0",
            "evaluation_time": FIXED_TIME,
            "checks": checks,
            "waivers": waivers or [],
        }
    )


def _check(kind: str, configuration: dict[str, Any], *, failure_mode: str = "fail", check_id: str = "quality") -> dict[str, Any]:
    return {
        "check_id": check_id,
        "kind": kind,
        "severity": "error",
        "failure_mode": failure_mode,
        "configuration": configuration,
    }


def _write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _base_artifacts(*, changed: bool = False) -> list[PackageArtifact]:
    fixture = ROOT / "fixtures" / "minimal-aecctx"
    manifest = json.loads((fixture / "manifest.json").read_text(encoding="utf-8"))
    original_assertion = json.loads((fixture / "evidence/assertions.jsonl").read_text(encoding="utf-8"))
    assertions: list[dict[str, Any]] = []
    for index, state in enumerate(("known", "unknown", "unsupported", "conflicted", "explicit_null", "not_applicable")):
        record = json.loads(json.dumps(original_assertion))
        record["record_id"] = f"assert_state_{index}"
        record["value"] = {"state": state, "value": "A-WALL"} if state == "known" else {"state": state, "reason_code": "TEST_STATE"}
        assertions.append(record)
    if changed:
        assertions[0]["value"]["value"] = "A-CHANGED"

    diagnostic = json.loads((fixture / "diagnostics/diagnostics.jsonl").read_text(encoding="utf-8"))
    diagnostic["code"] = "no-3d-geometry"
    diagnostic["severity"] = "warning"
    diagnostic["affected_count"] = 1

    artifacts: list[PackageArtifact] = []
    for entry in manifest["artifacts"]:
        logical = entry["path"]
        content = (fixture / logical).read_bytes()
        if logical == "evidence/assertions.jsonl":
            content = b"".join(canonical_json(record) for record in assertions)
        elif logical == "diagnostics/diagnostics.jsonl":
            content = canonical_json(diagnostic)
        artifacts.append(
            PackageArtifact(
                path=logical,
                content=content,
                media_type=entry["media_type"],
                role=entry["role"],
                authoritative=entry["authoritative"],
            )
        )
    return artifacts


def _write_core_package(path: Path, *, changed: bool = False, package_form: str = "zip") -> None:
    fixture_manifest = json.loads((ROOT / "fixtures/minimal-aecctx/manifest.json").read_text(encoding="utf-8"))
    PackageWriter(path, package_form=package_form).write(
        package_id="pkg_gate_conformance",
        created_at=fixture_manifest["created_at"],
        source_ids=fixture_manifest["source_ids"],
        capabilities=fixture_manifest["capabilities"],
        loss_summary=["no-3d-geometry"],
        embedding_policy=fixture_manifest["source_embedding_policy"],
        producer=fixture_manifest["producer"],
        artifacts=_base_artifacts(changed=changed),
    )


def _actual(result: Any) -> dict[str, Any]:
    return {
        "outcome": result.outcome,
        "exit_code": result.exit_code,
        "check_ids": [check.check_id for check in result.checks],
        "finding_codes": [finding.code for finding in result.findings],
        "diagnostic_codes": [diagnostic.code for diagnostic in result.diagnostics],
    }


def _entry(
    case_id: str,
    *,
    operation: str,
    candidate: str,
    policy: str,
    expected: dict[str, Any],
    baseline: str | None = None,
    ids: str | None = None,
    ifc_source: str | None = None,
    comparison_candidate: str | None = None,
    origin: str = "AECCTX project-authored",
    license_name: str = "Apache-2.0",
    fixture_root: Path = ROOT,
) -> dict[str, Any]:
    configured = [candidate, policy, baseline, ids, ifc_source, comparison_candidate]
    hashes: dict[str, str] = {}
    for relative in configured:
        if relative is None:
            continue
        generated = fixture_root / relative
        resolved = generated if generated.exists() else ROOT / relative
        if resolved.is_dir():
            for member in sorted(path for path in resolved.rglob("*") if path.is_file()):
                hashes[f"{relative}/{member.relative_to(resolved).as_posix()}"] = _sha(member)
        else:
            hashes[relative] = _sha(resolved)
    return {
        "case_id": case_id,
        "claim_id": CLAIM_ID,
        "operation": operation,
        "candidate": candidate,
        "policy": policy,
        "baseline": baseline,
        "ids": ids,
        "ifc_source": ifc_source,
        "comparison_candidate": comparison_candidate,
        "origin": origin,
        "license": license_name,
        "file_sha256": dict(sorted(hashes.items())),
        "expected": expected,
    }


def _evaluate_paths(
    root: Path,
    candidate: str,
    policy: str,
    *,
    baseline: str | None = None,
    ids: str | None = None,
    ifc_source: str | None = None,
    missing_extra: bool = False,
) -> dict[str, Any]:
    def resolved(relative: str) -> Path:
        generated = root / relative
        return generated if generated.exists() else ROOT / relative

    loaded = load_gate_policy(resolved(policy).read_bytes())
    if missing_extra:
        import aecctx.gate.ids as ids_module

        original = ids_module.metadata_version

        def missing(name: str) -> str:
            if name in {"ifctester", "ifcopenshell"}:
                raise PackageNotFoundError(name)
            return original(name)

        ids_module.metadata_version = missing
        try:
            return _actual(
                evaluate_gate(
                    resolved(candidate),
                    loaded,
                    baseline_package=resolved(baseline) if baseline else None,
                    ids_document=resolved(ids) if ids else None,
                    ifc_source=resolved(ifc_source) if ifc_source else None,
                )
            )
        finally:
            ids_module.metadata_version = original
    return _actual(
        evaluate_gate(
            resolved(candidate),
            loaded,
            baseline_package=resolved(baseline) if baseline else None,
            ids_document=resolved(ids) if ids else None,
            ifc_source=resolved(ifc_source) if ifc_source else None,
        )
    )


def _generate(temp_root: Path) -> None:
    gate = temp_root / "fixtures/v0.2/gate"
    policies = gate / "policies"
    packages = gate / "packages"
    adversarial = gate / "adversarial"
    for directory in (policies, packages, adversarial):
        directory.mkdir(parents=True, exist_ok=True)

    _write_core_package(packages / "core.aecctx")
    _write_core_package(packages / "core-directory", package_form="directory")
    _write_core_package(packages / "changed.aecctx", changed=True)
    _write(packages / "invalid.aecctx", b"not an AECCTX package\n")

    _write(policies / "pass.json", _policy([]))
    capability_fail = _policy([_check("capability.minimum", {"capabilities": {"ifc.read": "full"}})])
    _write(policies / "capability-fail.json", capability_fail)
    _write(
        policies / "capability-review.json",
        _policy([_check("capability.minimum", {"capabilities": {"ifc.read": "full"}}, failure_mode="requires_review")]),
    )
    _write(policies / "loss.json", _policy([_check("loss.maximum", {"overall_max": 0})]))
    actions = {state: "allow" for state in ("unknown", "unsupported", "conflicted", "explicit_null", "not_applicable")}
    actions["unknown"] = "requires_review"
    _write(
        policies / "value-state.json",
        _policy([_check("value_state.action", {"record_types": ["assertion"], "field_path": "value", "actions": actions})]),
    )
    _write(
        policies / "diagnostic.json",
        _policy([_check("diagnostic.maximum", {"threshold": "warning", "max_count": 0})]),
    )
    _write(
        policies / "baseline.json",
        _policy([_check("diff.regression", {"categories": DIFF_CATEGORIES}, check_id="baseline")]),
    )
    _write(adversarial / "duplicate-policy.json", b'{"profile":"https://aecctx.dev/gate/v1","profile":"https://aecctx.dev/gate/v1"}\n')

    provisional = evaluate_gate(packages / "core.aecctx", load_gate_policy(capability_fail))
    fingerprint = provisional.findings[0].fingerprint
    waiver = {
        "waiver_id": "reviewed-exception",
        "check_id": "aecctx.policy.quality",
        "finding_fingerprint": fingerprint,
        "reason": "bounded project-authored conformance fixture",
        "approved_by": "AECCTX test authority",
        "issued_at": "2026-07-01T00:00:00Z",
        "expires_at": "2026-08-01T00:00:00Z",
    }
    _write(
        policies / "waiver-active.json",
        _policy([_check("capability.minimum", {"capabilities": {"ifc.read": "full"}})], waivers=[waiver]),
    )
    expired = dict(waiver, issued_at="2026-06-01T00:00:00Z", expires_at="2026-07-01T00:00:00Z")
    _write(
        policies / "waiver-expired.json",
        _policy([_check("capability.minimum", {"capabilities": {"ifc.read": "full"}})], waivers=[expired]),
    )
    invalid = dict(waiver, issued_at="2026-07-01T00:00:00Z", expires_at="2026-07-01T00:00:00Z")
    _write(
        policies / "waiver-invalid.json",
        _policy([_check("capability.minimum", {"capabilities": {"ifc.read": "full"}})], waivers=[invalid]),
    )

    active_ids = _write(
        adversarial / "active-content.ids",
        b'<!DOCTYPE ids [<!ENTITY x "boom">]><ids xmlns="http://standards.buildingsmart.org/IDS">&x;</ids>\n',
    )
    project_source = ROOT / "fixtures/v0.2/gate/ids/project-wall.ifc"
    project_candidate = packages / "ids/project-wall.aecctx"
    project_candidate.parent.mkdir(parents=True, exist_ok=True)
    project_result = ingest_ifc(project_source, project_candidate, created_at=FIXED_TIME, package_form="zip")

    def ids_policy(ids_path: Path, source_id: str) -> bytes:
        return _policy(
            [
                _check(
                    "ids.specification",
                    {"ids_sha256": _sha(ids_path), "source_id": source_id},
                    check_id="ids",
                )
            ]
        )

    for name in ("project-simple-pass.ids", "project-simple-fail.ids"):
        _write(policies / f"ids-{name.removesuffix('.ids')}.json", ids_policy(ROOT / f"fixtures/v0.2/gate/ids/{name}", project_result.source_id))
    _write(policies / "ids-active-content.json", ids_policy(active_ids, project_result.source_id))

    official_root = ROOT / "fixtures/third_party/buildingsmart-ids-1.0/cases"
    official_cases: list[tuple[str, str, Path, Path, str, str]] = []
    for facet in ("entity", "attribute", "classification", "property", "material"):
        for outcome in ("pass", "fail"):
            ids_path = next((official_root / facet).glob(f"{outcome}-*.ids"))
            ifc_path = ids_path.with_suffix(".ifc")
            candidate = packages / f"ids/official-{facet}-{outcome}.aecctx"
            result = ingest_ifc(ifc_path, candidate, created_at=FIXED_TIME, package_form="zip")
            policy_path = policies / f"ids-official-{facet}-{outcome}.json"
            _write(policy_path, ids_policy(ids_path, result.source_id))
            official_cases.append(
                (
                    facet,
                    outcome,
                    ids_path,
                    ifc_path,
                    candidate.relative_to(temp_root).as_posix(),
                    policy_path.relative_to(temp_root).as_posix(),
                )
            )

    # Evaluate against the generated tree; project/official source inputs remain repository-owned.
    entries: list[dict[str, Any]] = []
    simple = [
        ("pass-core", "evaluate", "fixtures/v0.2/gate/packages/core.aecctx", "fixtures/v0.2/gate/policies/pass.json", None),
        ("fail-capability", "evaluate", "fixtures/v0.2/gate/packages/core.aecctx", "fixtures/v0.2/gate/policies/capability-fail.json", None),
        ("review-capability", "evaluate", "fixtures/v0.2/gate/packages/core.aecctx", "fixtures/v0.2/gate/policies/capability-review.json", None),
        ("error-invalid-candidate", "evaluate", "fixtures/v0.2/gate/packages/invalid.aecctx", "fixtures/v0.2/gate/policies/pass.json", None),
        ("baseline-regression", "evaluate", "fixtures/v0.2/gate/packages/changed.aecctx", "fixtures/v0.2/gate/policies/baseline.json", "fixtures/v0.2/gate/packages/core.aecctx"),
        ("loss-maximum", "evaluate", "fixtures/v0.2/gate/packages/core.aecctx", "fixtures/v0.2/gate/policies/loss.json", None),
        ("value-state-all", "evaluate", "fixtures/v0.2/gate/packages/core.aecctx", "fixtures/v0.2/gate/policies/value-state.json", None),
        ("diagnostic-maximum", "evaluate", "fixtures/v0.2/gate/packages/core.aecctx", "fixtures/v0.2/gate/policies/diagnostic.json", None),
        ("waiver-active", "evaluate", "fixtures/v0.2/gate/packages/core.aecctx", "fixtures/v0.2/gate/policies/waiver-active.json", None),
        ("waiver-expired", "evaluate", "fixtures/v0.2/gate/packages/core.aecctx", "fixtures/v0.2/gate/policies/waiver-expired.json", None),
    ]
    for case_id, operation, candidate, policy_path, baseline in simple:
        expected = _evaluate_paths(temp_root, candidate, policy_path, baseline=baseline)
        entries.append(_entry(case_id, operation=operation, candidate=candidate, policy=policy_path, baseline=baseline, expected=expected, fixture_root=temp_root))

    equivalence_expected = _evaluate_paths(
        temp_root,
        "fixtures/v0.2/gate/packages/core.aecctx",
        "fixtures/v0.2/gate/policies/pass.json",
    )
    comparison = _evaluate_paths(
        temp_root,
        "fixtures/v0.2/gate/packages/core-directory",
        "fixtures/v0.2/gate/policies/pass.json",
    )
    equivalence_expected["comparison_equal"] = equivalence_expected == comparison
    entries.append(
        _entry(
            "directory-zip-equivalence",
            operation="equivalence",
            candidate="fixtures/v0.2/gate/packages/core.aecctx",
            comparison_candidate="fixtures/v0.2/gate/packages/core-directory",
            policy="fixtures/v0.2/gate/policies/pass.json",
            expected=equivalence_expected,
            fixture_root=temp_root,
        )
    )

    duplicate_path = "fixtures/v0.2/gate/adversarial/duplicate-policy.json"
    try:
        load_gate_policy((temp_root / duplicate_path).read_bytes())
        raise AssertionError("duplicate policy unexpectedly parsed")
    except GateError as error:
        expected_control = {"exit_code": 2, "error_code": error.code}
    entries.append(
        _entry(
            "malicious-policy-duplicate-key",
            operation="control-error",
            candidate="fixtures/v0.2/gate/packages/core.aecctx",
            policy=duplicate_path,
            expected=expected_control,
            fixture_root=temp_root,
        )
    )
    invalid_waiver_path = "fixtures/v0.2/gate/policies/waiver-invalid.json"
    try:
        load_gate_policy((temp_root / invalid_waiver_path).read_bytes())
        raise AssertionError("invalid waiver unexpectedly parsed")
    except GateError as error:
        invalid_waiver_expected = {"exit_code": 2, "error_code": error.code}
    entries.append(
        _entry(
            "waiver-invalid",
            operation="control-error",
            candidate="fixtures/v0.2/gate/packages/core.aecctx",
            policy=invalid_waiver_path,
            expected=invalid_waiver_expected,
            fixture_root=temp_root,
        )
    )

    project_candidate_rel = "fixtures/v0.2/gate/packages/ids/project-wall.aecctx"
    project_source_rel = "fixtures/v0.2/gate/ids/project-wall.ifc"
    for outcome in ("pass", "fail"):
        ids_rel = f"fixtures/v0.2/gate/ids/project-simple-{outcome}.ids"
        policy_rel = f"fixtures/v0.2/gate/policies/ids-project-simple-{outcome}.json"
        expected = _evaluate_paths(temp_root, project_candidate_rel, policy_rel, ids=ids_rel, ifc_source=project_source_rel)
        entries.append(_entry(f"ids-project-{outcome}", operation="ids", candidate=project_candidate_rel, policy=policy_rel, ids=ids_rel, ifc_source=project_source_rel, expected=expected, fixture_root=temp_root))
    active_rel = "fixtures/v0.2/gate/adversarial/active-content.ids"
    active_policy = "fixtures/v0.2/gate/policies/ids-active-content.json"
    entries.append(
        _entry(
            "ids-active-xml-error",
            operation="ids",
            candidate=project_candidate_rel,
            policy=active_policy,
            ids=active_rel,
            ifc_source=project_source_rel,
            expected=_evaluate_paths(temp_root, project_candidate_rel, active_policy, ids=active_rel, ifc_source=project_source_rel),
            fixture_root=temp_root,
        )
    )
    pass_ids = "fixtures/v0.2/gate/ids/project-simple-pass.ids"
    pass_policy = "fixtures/v0.2/gate/policies/ids-project-simple-pass.json"
    entries.append(
        _entry(
            "ids-missing-extra",
            operation="ids-missing-extra",
            candidate=project_candidate_rel,
            policy=pass_policy,
            ids=pass_ids,
            ifc_source=project_source_rel,
            expected=_evaluate_paths(temp_root, project_candidate_rel, pass_policy, ids=pass_ids, ifc_source=project_source_rel, missing_extra=True),
            fixture_root=temp_root,
        )
    )

    for facet, outcome, ids_path, ifc_path, candidate, policy_path in official_cases:
        ids_rel = ids_path.relative_to(ROOT).as_posix()
        ifc_rel = ifc_path.relative_to(ROOT).as_posix()
        expected = _evaluate_paths(temp_root, candidate, policy_path, ids=ids_rel, ifc_source=ifc_rel)
        entries.append(
            _entry(
                f"ids-official-{facet}-{outcome}",
                operation="ids",
                candidate=candidate,
                policy=policy_path,
                ids=ids_rel,
                ifc_source=ifc_rel,
                expected=expected,
                origin="buildingSMART IDS v1.0.0 unchanged inputs",
                license_name="CC-BY-ND-4.0 inputs; Apache-2.0 generated harness",
                fixture_root=temp_root,
            )
        )

    corpus = {
        "version": "1",
        "claim_id": CLAIM_ID,
        "claim_status": "public",
        "maximum_support": "partial",
        "profile": PROFILE,
        "entries": sorted(entries, key=lambda entry: entry["case_id"]),
    }
    _write(temp_root / "conformance/v0.2/gate-corpus.json", canonical_gate_json(corpus))


def _generated_files(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for base in (
        root / "fixtures/v0.2/gate/policies",
        root / "fixtures/v0.2/gate/packages",
        root / "fixtures/v0.2/gate/adversarial",
    ):
        if base.exists():
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    files[path.relative_to(root).as_posix()] = path.read_bytes()
    corpus = root / "conformance/v0.2/gate-corpus.json"
    if corpus.is_file():
        files[corpus.relative_to(root).as_posix()] = corpus.read_bytes()
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="aecctx-gate-fixtures-") as temporary:
        generated_root = Path(temporary)
        _generate(generated_root)
        generated = _generated_files(generated_root)
        if arguments.check:
            committed = _generated_files(ROOT)
            if generated != committed:
                missing = sorted(set(generated) - set(committed))
                extra = sorted(set(committed) - set(generated))
                changed = sorted(path for path in set(generated) & set(committed) if generated[path] != committed[path])
                print(json.dumps({"missing": missing, "extra": extra, "changed": changed}, sort_keys=True), file=sys.stderr)
                return 1
        else:
            for relative, data in generated.items():
                target = ROOT / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        print("aecctx gate fixtures: deterministic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
