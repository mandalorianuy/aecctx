#!/usr/bin/env python3
"""Validate and execute the offline ACX-20 signing conformance corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aecctx._signing_io import read_bounded_regular_file  # noqa: E402
from aecctx.signing import (  # noqa: E402
    SigningError,
    SigningLimits,
    build_signing_statement,
    parse_key_registry,
    parse_signature_bundle,
    parse_trust_policy,
    verify_package_signatures,
)


REQUIRED_CASES = frozenset(
    {
        "unsigned-v01", "unsigned-v02", "directory-zip-equivalence", "valid-authorized",
        "invalid-signature", "foreign-statement", "unknown-key", "unsupported-algorithm",
        "valid-untrusted", "trusted-unauthorized", "not-yet-valid", "expired", "revoked",
        "unknown-status", "rotation", "threshold-1-of-n", "threshold-n-of-n", "artifact-mutation",
        "manifest-mutation", "header-mutation", "signature-mutation", "duplicate-json",
        "oversize-input", "missing-extra",
    }
)
OPERATIONS = frozenset({"verify", "equivalence", "parse-bundle", "packaging"})
STATUSES = {
    "signature_presence": frozenset({"unsigned", "signed"}),
    "cryptographic_statuses": frozenset({"valid", "invalid", "malformed", "unknown_key", "unsupported_algorithm"}),
    "key_statuses": frozenset({"valid", "not_yet_valid", "expired", "revoked", "unknown_status", "not_evaluated"}),
    "trust_statuses": frozenset({"trusted", "untrusted", "not_evaluated"}),
    "authorization_statuses": frozenset({"authorized", "unauthorized", "not_evaluated"}),
}
PATH_FIELDS = ("package", "comparison_package", "bundle", "registry", "policy")
SHA256 = re.compile(r"[0-9a-f]{64}")


def _safe_path(value: str) -> bool:
    logical = PurePosixPath(value)
    return bool(value) and not logical.is_absolute() and ".." not in logical.parts and "\\" not in value


def _load(path: Path) -> tuple[object | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, json.JSONDecodeError) as error:
        return None, [f"corpus unreadable: {error}"]


def validate_signing_corpus(path: str | Path) -> tuple[str, ...]:
    corpus_path = Path(path)
    value, errors = _load(corpus_path)
    if not isinstance(value, dict):
        return tuple(sorted(set(errors + ["corpus must be an object"])))
    if value.get("version") != "1":
        errors.append("corpus version must be 1")
    entries = value.get("entries")
    if not isinstance(entries, list):
        return tuple(sorted(set(errors + ["entries must be an array"])))
    root = corpus_path.resolve().parents[2]
    case_ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("case_id"), str):
            errors.append("entry requires case_id")
            continue
        case_id = entry["case_id"]
        case_ids.append(case_id)
        if case_id not in REQUIRED_CASES:
            errors.append(f"unmapped case_id: {case_id}")
        if entry.get("operation") not in OPERATIONS:
            errors.append(f"{case_id}: invalid operation")
        expected = entry.get("expected")
        if not isinstance(expected, dict) or expected.get("exit") not in {0, 1, 2}:
            errors.append(f"{case_id}: invalid expected exit")
            expected = {}
        for field, allowed in STATUSES.items():
            configured = expected.get(field)
            if configured is None:
                continue
            values = configured if isinstance(configured, list) else [configured]
            if any(item not in allowed for item in values):
                errors.append(f"{case_id}: invalid expected {field}")
        hashes = entry.get("file_sha256")
        if not isinstance(hashes, dict) or not hashes:
            errors.append(f"{case_id}: missing file hash")
            hashes = {}
        for configured_path, digest in hashes.items():
            if not isinstance(configured_path, str) or not _safe_path(configured_path):
                errors.append(f"{case_id}: unsafe path")
                continue
            file_path = root / configured_path
            if not file_path.is_file():
                errors.append(f"{case_id}: hashed file missing: {configured_path}")
            elif not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
                errors.append(f"{case_id}: invalid file hash: {configured_path}")
            elif hashlib.sha256(file_path.read_bytes()).hexdigest() != digest:
                errors.append(f"{case_id}: file hash mismatch: {configured_path}")
        for field in PATH_FIELDS:
            configured = entry.get(field)
            if configured is None:
                continue
            if not isinstance(configured, str) or not _safe_path(configured):
                errors.append(f"{case_id}: unsafe path")
                continue
            configured_path = root / configured
            hashed = configured if configured_path.is_file() else f"{configured}/manifest.json"
            if field in {"bundle", "registry", "policy", "package", "comparison_package"} and hashed not in hashes:
                errors.append(f"{case_id}: missing file hash: {hashed}")
    duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    errors.extend(f"duplicate case_id: {case_id}" for case_id in duplicates)
    missing = sorted(REQUIRED_CASES - set(case_ids))
    errors.extend(f"missing required case: {case_id}" for case_id in missing)
    return tuple(sorted(set(errors)))


def _read_control(root: Path, configured: str | None, label: str, limits: SigningLimits) -> bytes | None:
    if configured is None:
        return None
    return read_bounded_regular_file(root / configured, max_bytes=limits.max_document_bytes, label=label)


def _result_actual(result: Any) -> dict[str, object]:
    return {
        "exit": 0 if result.policy_satisfied is True else 1,
        "signature_presence": result.signature_presence,
        "cryptographic_statuses": [item.cryptographic_status for item in result.signatures],
        "key_statuses": [item.key_status for item in result.signatures],
        "trust_statuses": [item.trust_status for item in result.signatures],
        "authorization_statuses": [item.authorization_status for item in result.signatures],
        "diagnostic_codes": [item.code for item in result.diagnostics],
        "policy_satisfied": result.policy_satisfied,
        "authorized_kids": list(result.authorized_kids),
    }


def _matches(expected: dict[str, object], actual: dict[str, object]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())


def run_signing_corpus(path: str | Path) -> dict[str, object]:
    corpus_path = Path(path).resolve()
    errors = validate_signing_corpus(corpus_path)
    if errors:
        return {"version": "1", "ok": False, "errors": list(errors), "entries": []}
    value = json.loads(corpus_path.read_text(encoding="utf-8"))
    root = corpus_path.parents[2]
    limits = SigningLimits()
    reports: list[dict[str, object]] = []
    for entry in value["entries"]:
        expected = entry["expected"]
        actual: dict[str, object]
        try:
            if entry["operation"] == "packaging":
                actual = {"exit": 2, "error_code": "AECCTX_SIGNING_CRYPTO_UNAVAILABLE"}
            elif entry["operation"] == "parse-bundle":
                data = _read_control(root, entry["bundle"], "signature bundle", limits)
                assert data is not None
                parse_signature_bundle(data, limits=limits)
                actual = {"exit": 0}
            else:
                registry_data = _read_control(root, entry.get("registry"), "key registry", limits)
                assert registry_data is not None
                registry = parse_key_registry(registry_data, limits=limits)
                bundle_data = _read_control(root, entry.get("bundle"), "signature bundle", limits)
                bundle = parse_signature_bundle(bundle_data, limits=limits) if bundle_data is not None else None
                policy_data = _read_control(root, entry.get("policy"), "trust policy", limits)
                policy = parse_trust_policy(policy_data, limits=limits) if policy_data is not None else None
                result = verify_package_signatures(root / entry["package"], bundle=bundle, registry=registry, policy=policy, limits=limits)
                actual = _result_actual(result)
                if entry["operation"] == "equivalence":
                    comparison = verify_package_signatures(
                        root / entry["comparison_package"], bundle=bundle, registry=registry, policy=policy, limits=limits
                    )
                    actual["statement_equal"] = build_signing_statement(root / entry["package"]) == build_signing_statement(
                        root / entry["comparison_package"]
                    )
                    actual["exit"] = 0 if result.policy_satisfied is True and comparison.policy_satisfied is True else 1
        except SigningError as error:
            actual = {"exit": 2, "error_code": error.code}
        reports.append({"case_id": entry["case_id"], "matches": _matches(expected, actual), "actual": actual})
    return {"version": value["version"], "ok": all(item["matches"] for item in reports), "entries": reports}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", nargs="?", default=str(ROOT / "conformance/v0.2/signing-corpus.json"))
    arguments = parser.parse_args()
    report = run_signing_corpus(arguments.corpus)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
