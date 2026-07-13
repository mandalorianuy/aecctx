#!/usr/bin/env python3
"""Deterministic repository-level checks for the AECCTX specification foundation."""

from __future__ import annotations

import json
import hashlib
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/aec-context-package-spec.md"
PLUGIN_SPEC = ROOT / "docs/specs/aec-context-plugin-contract.md"
EXPANSION_SPEC = ROOT / "docs/specs/aecctx-capability-expansion-spec.md"
POST_V02_SPEC = ROOT / "docs/specs/aecctx-post-v02-functional-debt-spec.md"
PLAN = ROOT / "docs/implementation-plan.md"
FIXTURE = ROOT / "fixtures/minimal-aecctx"


def fail(message: str) -> None:
    raise SystemExit(f"aecctx spec contract: {message}")


def load_json(path: pathlib.Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"invalid JSON at {path.relative_to(ROOT)}: {error}")


def check_required_files() -> None:
    required = [
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / "LICENSE",
        ROOT / "SECURITY.md",
        ROOT / "docs/HANDOFF.md",
        ROOT / "docs/project-governance.md",
        ROOT / "docs/capability-matrix.md",
        ROOT / "docs/decisions/decision-log.md",
        ROOT / "docs/integration/woodframing-boundary.md",
        SPEC,
        PLUGIN_SPEC,
        EXPANSION_SPEC,
        POST_V02_SPEC,
        PLAN,
        ROOT / "schemas/v0.1/manifest.schema.json",
        ROOT / "schemas/v0.1/record.schema.json",
        ROOT / "schemas/v0.1/neutral-vocabulary.json",
        ROOT / "schemas/v0.2/manifest.schema.json",
        ROOT / "schemas/v0.2/record.schema.json",
        ROOT / "schemas/v0.2/provider-descriptor.schema.json",
        ROOT / "schemas/v0.2/provider-request.schema.json",
        ROOT / "schemas/v0.2/provider-response.schema.json",
        ROOT / "schemas/v0.2/mesh-coordinate-profile.schema.json",
        ROOT / "schemas/v0.2/step-iges-provider-event.schema.json",
        ROOT / "schemas/v0.2/dwg-provider-event.schema.json",
        ROOT / "schemas/v0.2/rvt-provider-decision.schema.json",
        ROOT / "scripts/verify_portable.sh",
        ROOT / "scripts/verify_release.sh",
        ROOT / ".github/workflows/release-recovery.yml",
        ROOT / "conformance/v0.1/corpus.json",
        ROOT / "conformance/v0.2/claims.json",
        ROOT / "conformance/v0.3/claims.json",
        ROOT / "conformance/v0.3/provider-multiarch-corpus.json",
        ROOT / "conformance/v0.2/corpus.json",
        ROOT / "conformance/v0.2/provider-corpus.json",
        ROOT / "conformance/v0.2/ifc-corpus.json",
        ROOT / "conformance/v0.2/dxf-corpus.json",
        ROOT / "conformance/v0.2/mesh-corpus.json",
        ROOT / "conformance/v0.2/step-iges-corpus.json",
        ROOT / "conformance/v0.2/dwg-corpus.json",
        ROOT / "conformance/v0.2/rvt-provider-decision.json",
        ROOT / "conformance/v0.2/signing-corpus.json",
        ROOT / "scripts/check_rvt_blocked_conformance.py",
        ROOT / "scripts/check_signing_conformance.py",
        ROOT / "fixtures/v0.2/providers/reference-descriptor.json",
        ROOT / "fixtures/v0.2/providers/reference-request.json",
        ROOT / "fixtures/v0.2/providers/reference-output/response.json",
        ROOT / "fixtures/v0.2/ifc/ifc2x3-native-2d-local.ifc",
        ROOT / "fixtures/v0.2/ifc/ifc4-native-2d-georef.ifc",
        ROOT / "fixtures/v0.2/ifc/ifc4-degraded-2d-incomplete-georef.ifc",
        ROOT / "fixtures/v0.2/ifc/ifc4-conflicting-units.ifc",
        ROOT / "docs/security/external-provider-threat-model.md",
        ROOT / "docs/providers/provider-review-template.md",
        ROOT / "docs/specs/ifc-v02-profile.md",
        ROOT / "docs/specs/dxf-v02-profile.md",
        ROOT / "docs/specs/mesh-coordinate-v02-profile.md",
        ROOT / "docs/specs/step-iges-v02-profile.md",
        ROOT / "docs/specs/dwg-v02-profile.md",
        ROOT / "docs/specs/rvt-v02-blocked-profile.md",
        ROOT / "docs/specs/signing-v1-profile.md",
        ROOT / "docs/specs/provider-oci-multiarch-v03-profile.md",
        ROOT / "docs/specs/provider-local-enforcement-v03-profile.md",
        ROOT / "docs/security/signing-threat-model.md",
        ROOT / "docs/plans/acx-20-implementation.md",
        ROOT / "fixtures/v0.2/dxf/r2018-semantics-3d-ascii.dxf",
        ROOT / "fixtures/v0.2/dxf/r2018-semantics-3d-binary.dxf",
        ROOT / "fixtures/v0.2/dxf/r2000-cyclic-inserts.dxf",
        ROOT / "fixtures/v0.2/dxf/malformed-tags.dxf",
        ROOT / "fixtures/v0.2/shared/minimal-v02/manifest.json",
        ROOT / "fixtures/v0.2/rvt/not-a-real-rvt.rvt",
        ROOT / "fixtures/v0.2/signing/README.md",
        ROOT / "fixtures/v0.2/signing/generate_fixtures.py",
        ROOT / "fixtures/v0.2/signing/bundles/valid-a.json",
        ROOT / "fixtures/v0.2/signing/registries/valid.json",
        ROOT / "fixtures/v0.2/signing/policies/trust-a.json",
        ROOT / "CHANGELOG.md",
        ROOT / "docs/compatibility.md",
        ROOT / "docs/compatibility-v0.2.md",
        ROOT / "docs/releases/v0.1.0.md",
        ROOT / "docs/releases/v0.2.0.md",
        ROOT / "docs/release/v0.2.0-evidence-index.md",
        ROOT / "docs/release/v0.2.0-supply-chain.md",
        ROOT / "docs/evidence/ACX-23.md",
        ROOT / "docs/plans/acx-23-implementation.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        fail(f"missing required files: {', '.join(missing)}")


def check_authorities() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    for phrase in [
        "Markdown context projection",
        "Capability and loss reporting",
        "Value states and assertions",
        "Consumer boundary",
        "application-agnostic",
    ]:
        if phrase not in spec:
            fail(f"package spec missing authority phrase: {phrase}")

    plugin = PLUGIN_SPEC.read_text(encoding="utf-8")
    for phrase in ["Capability and loss report", "Determinism", "Safety", "Failure behavior"]:
        if phrase not in plugin:
            fail(f"plugin spec missing authority phrase: {phrase}")

    expansion = EXPANSION_SPEC.read_text(encoding="utf-8")
    for phrase in [
        "Claim lifecycle",
        "Reviewed external sandbox provider contract",
        "Hidden geometry boundary",
        "Authenticity and signing",
        "AEC Delivery Quality Gate",
        "Codex plugin",
        "no new capability claim is implied",
    ]:
        if phrase not in expansion:
            fail(f"expansion spec missing authority phrase: {phrase}")

    post_v02 = POST_V02_SPEC.read_text(encoding="utf-8")
    for phrase in ["Functional result", "Gates and non-claims", "ACX-24", "ACX-38"]:
        if phrase not in post_v02:
            fail(f"post-v0.2 spec missing authority phrase: {phrase}")

    signing = (ROOT / "docs/specs/signing-v1-profile.md").read_text(encoding="utf-8")
    for phrase in [
        "Integrity, cryptographic validity, signer identity, verifier trust and policy authorization",
        "Detached JWS envelope",
        "Algorithm profile and agility",
        "Claim boundary",
    ]:
        if phrase not in signing:
            fail(f"signing profile missing authority phrase: {phrase}")

    signing_plan = (ROOT / "docs/plans/acx-20-implementation.md").read_text(encoding="utf-8")
    for phrase in [
        "Strict JSON, canonical statement and package binding",
        "Optional Ed25519 signing and deterministic bundle append",
        "Multi-signature verification and separated result records",
        "Publishable signing corpus, portable gates and packaging proof",
    ]:
        if phrase not in signing_plan:
            fail(f"signing implementation plan missing execution slice: {phrase}")

    plan = PLAN.read_text(encoding="utf-8")
    for phrase in [
        "Status and promotion protocol",
        "Definition of ready",
        "Definition of done",
        "Acceptance evidence template",
        "Specification traceability",
        "Verification cadence",
        "ACX-23: Expansion release",
    ]:
        if phrase not in plan:
            fail(f"implementation plan missing execution detail: {phrase}")
    ledger = {
        task: status
        for task, status in re.findall(r"^\| (ACX-\d{2}) \| ([a-z_-]+) \|", plan, re.MULTILINE)
    }
    if ledger.get("ACX-00") != "completed" or ledger.get("ACX-10") != "deferred":
        fail("implementation plan boundary tasks have invalid status")
    executable = [f"ACX-{number:02d}" for number in range(1, 10)] + [
        f"ACX-{number:02d}" for number in range(11, 39)
    ]
    missing_tasks = [task for task in executable if task not in ledger]
    if missing_tasks:
        fail(f"implementation plan missing executable tasks: {', '.join(missing_tasks)}")
    pending_next = [task for task in executable if ledger.get(task) == "pending-next"]
    in_progress = [task for task in executable if ledger.get(task) == "in_progress"]
    if not pending_next and not in_progress:
        if any(ledger.get(task) not in {"completed", "blocked"} for task in executable):
            fail("implementation plan without an active task requires every executable task completed or blocked")
        return
    if len(pending_next) + len(in_progress) != 1:
        fail("implementation plan must contain exactly one pending-next or in_progress task")
    active = (pending_next + in_progress)[0]
    active_index = executable.index(active)
    if any(ledger.get(task) not in {"completed", "blocked"} for task in executable[:active_index]):
        fail("tasks before the active task must be completed or documented blocked")
    if any(ledger.get(task) != "pending" for task in executable[active_index + 1 :]):
        fail("tasks after the active task must remain pending")


def check_fixture() -> None:
    required_paths = [
        "manifest.json",
        "sources/sources.jsonl",
        "evidence/primitives.jsonl",
        "evidence/assertions.jsonl",
        "model/entities.jsonl",
        "model/relations.jsonl",
        "diagnostics/diagnostics.jsonl",
        "context/index.md",
    ]
    for relative in required_paths:
        if not (FIXTURE / relative).is_file():
            fail(f"fixture missing {relative}")

    manifest = load_json(FIXTURE / "manifest.json")
    if not isinstance(manifest, dict) or manifest.get("aecctx_version") != "0.1.0":
        fail("fixture manifest version mismatch")
    if manifest.get("source_ids") != ["src_minimal"]:
        fail("fixture source identity mismatch")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        fail("fixture manifest requires a non-empty artifact inventory")
    digest_lines: list[bytes] = []
    inventoried_paths: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            fail("fixture artifact entry must be an object")
        relative = artifact.get("path")
        if not isinstance(relative, str) or relative in inventoried_paths:
            fail(f"invalid or duplicate artifact path: {relative!r}")
        artifact_path = FIXTURE / relative
        if not artifact_path.is_file():
            fail(f"inventoried fixture artifact is missing: {relative}")
        data = artifact_path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        if artifact.get("sha256") != sha256 or artifact.get("bytes") != len(data):
            fail(f"fixture artifact integrity mismatch: {relative}")
        inventoried_paths.add(relative)
        digest_lines.append(f"{relative}\0{sha256}\0{len(data)}\n".encode("utf-8"))
    logical_digest = hashlib.sha256(b"".join(digest_lines)).hexdigest()
    if manifest.get("logical_digest") != logical_digest:
        fail("fixture logical digest mismatch")

    if inventoried_paths != set(required_paths[1:]):
        fail("fixture artifact inventory must cover every required non-manifest file")

    record_ids: set[str] = set()
    for path in sorted(FIXTURE.glob("**/*.jsonl")):
        previous = ""
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except json.JSONDecodeError as error:
                fail(f"invalid JSONL at {path.relative_to(ROOT)}:{line_number}: {error}")
            record_id = record.get("record_id")
            if not isinstance(record_id, str) or not record_id:
                fail(f"missing record_id at {path.relative_to(ROOT)}:{line_number}")
            if record_id in record_ids:
                fail(f"duplicate record_id: {record_id}")
            if previous and record_id < previous:
                fail(f"records not sorted at {path.relative_to(ROOT)}:{line_number}")
            previous = record_id
            record_ids.add(record_id)

    if "prim_line_1" not in record_ids or "entity_line_1" not in record_ids:
        fail("fixture does not prove evidence-to-neutral-record layering")


def main() -> int:
    check_required_files()
    check_authorities()
    check_fixture()
    print("aecctx spec contract: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
