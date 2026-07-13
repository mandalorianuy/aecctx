#!/usr/bin/env python3
"""Validate and execute the offline ACX-21 quality-gate conformance corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from importlib.metadata import PackageNotFoundError
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aecctx.gate import (  # noqa: E402
    GateError,
    canonical_gate_json,
    evaluate_gate,
    load_gate_policy,
    validate_gate_document,
)


CLAIM_ID = "quality-gate.policy-ids"
PROFILE = "aecctx-gate-v1-ids-1.0-simple-v1"
REQUIRED_CASES = frozenset(
    {
        "pass-core",
        "directory-zip-equivalence",
        "fail-capability",
        "review-capability",
        "error-invalid-candidate",
        "malicious-policy-duplicate-key",
        "baseline-regression",
        "loss-maximum",
        "value-state-all",
        "diagnostic-maximum",
        "waiver-active",
        "waiver-expired",
        "waiver-invalid",
        "ids-project-pass",
        "ids-project-fail",
        "ids-active-xml-error",
        "ids-missing-extra",
        *{
            f"ids-official-{facet}-{outcome}"
            for facet in ("entity", "attribute", "classification", "property", "material")
            for outcome in ("pass", "fail")
        },
    }
)
OPERATIONS = frozenset({"evaluate", "equivalence", "control-error", "ids", "ids-missing-extra"})
PATH_FIELDS = ("candidate", "policy", "baseline", "ids", "ifc_source", "comparison_candidate")
SHA256 = re.compile(r"[0-9a-f]{64}")
ENTRY_FIELDS = frozenset(
    {
        "case_id",
        "claim_id",
        "operation",
        "candidate",
        "policy",
        "baseline",
        "ids",
        "ifc_source",
        "comparison_candidate",
        "origin",
        "license",
        "file_sha256",
        "expected",
    }
)


def _safe_path(value: str) -> bool:
    logical = PurePosixPath(value)
    return bool(value) and not logical.is_absolute() and ".." not in logical.parts and "\\" not in value


def _claim() -> dict[str, Any] | None:
    try:
        registry = json.loads((ROOT / "conformance/v0.2/claims.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for claim in registry.get("claims", []):
        if isinstance(claim, dict) and claim.get("id") == CLAIM_ID:
            return claim
    return None


def validate_gate_corpus(path: str | Path) -> tuple[str, ...]:
    errors: list[str] = []
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return (f"corpus unreadable: {error}",)
    if not isinstance(value, dict):
        return ("corpus must be an object",)
    if set(value) != {"version", "claim_id", "claim_status", "maximum_support", "profile", "entries"}:
        errors.append("corpus root fields are not closed")
    if value.get("version") != "1":
        errors.append("corpus version must be 1")
    if value.get("claim_id") != CLAIM_ID:
        errors.append("corpus claim_id mismatch")
    if value.get("claim_status") != "public":
        errors.append("corpus claim status must be public after ACX-21 acceptance")
    if value.get("maximum_support") != "partial":
        errors.append("corpus maximum support must be partial")
    if value.get("profile") != PROFILE:
        errors.append("corpus profile mismatch")
    claim = _claim()
    if claim is None:
        errors.append("claim registry is missing quality-gate.policy-ids")
    else:
        if claim.get("status") != value.get("claim_status"):
            errors.append("claim status mismatch")
        if claim.get("profile") != value.get("profile"):
            errors.append("claim profile mismatch")

    entries = value.get("entries")
    if not isinstance(entries, list):
        return tuple(sorted(set(errors + ["entries must be an array"])))
    case_ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("entry must be an object")
            continue
        if set(entry) != ENTRY_FIELDS:
            errors.append("entry fields are not closed")
        case_id = entry.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append("entry requires case_id")
            continue
        case_ids.append(case_id)
        if case_id not in REQUIRED_CASES:
            errors.append(f"unmapped case_id: {case_id}")
        if entry.get("claim_id") != CLAIM_ID:
            errors.append(f"{case_id}: claim_id mismatch")
        if entry.get("operation") not in OPERATIONS:
            errors.append(f"{case_id}: invalid operation")
        if entry.get("origin") not in {"AECCTX project-authored", "buildingSMART IDS v1.0.0 unchanged inputs"}:
            errors.append(f"{case_id}: invalid origin")
        if entry.get("license") not in {"Apache-2.0", "CC-BY-ND-4.0 inputs; Apache-2.0 generated harness"}:
            errors.append(f"{case_id}: invalid license")
        hashes = entry.get("file_sha256")
        if not isinstance(hashes, dict) or not hashes:
            errors.append(f"{case_id}: missing file hash")
            hashes = {}
        for configured, digest in hashes.items():
            if not isinstance(configured, str) or not _safe_path(configured):
                errors.append(f"{case_id}: unsafe path")
                continue
            file_path = ROOT / configured
            if not file_path.is_file():
                errors.append(f"{case_id}: hashed file missing: {configured}")
            elif not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
                errors.append(f"{case_id}: invalid file hash: {configured}")
            elif hashlib.sha256(file_path.read_bytes()).hexdigest() != digest:
                errors.append(f"{case_id}: file hash mismatch: {configured}")
        for field in PATH_FIELDS:
            configured = entry.get(field)
            if configured is None and field in {"baseline", "ids", "ifc_source", "comparison_candidate"}:
                continue
            if not isinstance(configured, str) or not _safe_path(configured):
                errors.append(f"{case_id}: unsafe path")
            elif not any(
                hashed == configured or hashed.startswith(f"{configured}/")
                for hashed in hashes
            ):
                errors.append(f"{case_id}: missing file hash: {configured}")
        expected = entry.get("expected")
        if not isinstance(expected, dict) or expected.get("exit_code") not in {0, 1, 2}:
            errors.append(f"{case_id}: invalid expected result")
        elif entry.get("operation") == "control-error":
            if set(expected) != {"exit_code", "error_code"} or not isinstance(expected.get("error_code"), str):
                errors.append(f"{case_id}: invalid expected control error")
        else:
            required = {"outcome", "exit_code", "check_ids", "finding_codes", "diagnostic_codes"}
            if entry.get("operation") == "equivalence":
                required.add("comparison_equal")
            if set(expected) != required or expected.get("outcome") not in {"pass", "fail", "requires_review", "error"}:
                errors.append(f"{case_id}: invalid expected gate result")
            if entry.get("operation") == "equivalence" and not isinstance(expected.get("comparison_equal"), bool):
                errors.append(f"{case_id}: invalid equivalence result")
            for field in ("check_ids", "finding_codes", "diagnostic_codes"):
                if not isinstance(expected.get(field), list) or any(not isinstance(item, str) for item in expected.get(field, [])):
                    errors.append(f"{case_id}: invalid expected {field}")
    duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    errors.extend(f"duplicate case_id: {case_id}" for case_id in duplicates)
    errors.extend(f"missing required case: {case_id}" for case_id in sorted(REQUIRED_CASES - set(case_ids)))
    return tuple(sorted(set(errors)))


def _actual(result: Any) -> dict[str, Any]:
    validate_gate_document(result.to_dict(), "gate-result.schema.json")
    return {
        "outcome": result.outcome,
        "exit_code": result.exit_code,
        "check_ids": [check.check_id for check in result.checks],
        "finding_codes": [finding.code for finding in result.findings],
        "diagnostic_codes": [diagnostic.code for diagnostic in result.diagnostics],
    }


def _execute(entry: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    try:
        policy = load_gate_policy((ROOT / entry["policy"]).read_bytes())
    except GateError as error:
        actual = {"exit_code": 2, "error_code": error.code}
        return actual, canonical_gate_json(actual)
    if entry["operation"] == "control-error":
        actual = {"exit_code": 0, "error_code": "none"}
        return actual, canonical_gate_json(actual)

    def evaluate(candidate: str | None = None) -> Any:
        return evaluate_gate(
            ROOT / (candidate or entry["candidate"]),
            policy,
            baseline_package=ROOT / entry["baseline"] if entry["baseline"] else None,
            ids_document=ROOT / entry["ids"] if entry["ids"] else None,
            ifc_source=ROOT / entry["ifc_source"] if entry["ifc_source"] else None,
        )

    if entry["operation"] == "ids-missing-extra":
        import aecctx.gate.ids as ids_module

        original = ids_module.metadata_version

        def missing(name: str) -> str:
            if name in {"ifctester", "ifcopenshell"}:
                raise PackageNotFoundError(name)
            return original(name)

        ids_module.metadata_version = missing
        try:
            result = evaluate()
        finally:
            ids_module.metadata_version = original
    else:
        result = evaluate()
    actual = _actual(result)
    if entry["operation"] == "equivalence":
        comparison = evaluate(entry["comparison_candidate"])
        actual["comparison_equal"] = result.canonical_bytes() == comparison.canonical_bytes()
    return actual, result.canonical_bytes()


def run_gate_corpus(path: str | Path) -> dict[str, Any]:
    errors = validate_gate_corpus(path)
    if errors:
        return {"version": "1", "ok": False, "errors": list(errors), "entries": []}
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    reports: list[dict[str, Any]] = []
    for entry in value["entries"]:
        first, first_bytes = _execute(entry)
        second, second_bytes = _execute(entry)
        reports.append(
            {
                "case_id": entry["case_id"],
                "matches": first == entry["expected"],
                "deterministic": first == second and first_bytes == second_bytes,
                "actual": first,
            }
        )
    return {
        "version": value["version"],
        "ok": all(entry["matches"] and entry["deterministic"] for entry in reports),
        "entries": reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", nargs="?", default=str(ROOT / "conformance/v0.2/gate-corpus.json"))
    arguments = parser.parse_args()
    report = run_gate_corpus(arguments.corpus)
    sys.stdout.buffer.write(canonical_gate_json(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
