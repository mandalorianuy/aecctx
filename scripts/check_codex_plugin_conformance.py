#!/usr/bin/env python3
"""Verify the hash-bound aecctx-inspector conformance contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_TOOLS = {
    "aecctx_validate": "inspect-package",
    "aecctx_info": "inspect-package",
    "aecctx_query": "triage-capability-loss",
    "aecctx_diff": "compare-revisions",
    "aecctx_context": "render-agent-context",
    "aecctx_gate": "explain-quality-gate",
}
EXPECTED_SURFACES = {
    "filename", "pdf_text", "ifc_dxf_metadata", "ocr_provider_output", "generated_context"
}


def _load(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label} is not valid UTF-8 JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} must be a JSON object")
        return None
    return value


def validate(repo: Path, corpus_path: Path, claims_path: Path, plugin: Path) -> tuple[str, ...]:
    errors: list[str] = []
    corpus = _load(corpus_path, "plugin corpus", errors)
    claims = _load(claims_path, "claim registry", errors)
    if corpus is None or claims is None:
        return tuple(errors)

    claim_id = corpus.get("claim_id")
    claim_entries = claims.get("claims")
    claim = next((entry for entry in claim_entries if isinstance(entry, dict) and entry.get("id") == claim_id), None) if isinstance(claim_entries, list) else None
    if claim is None:
        errors.append("plugin claim is absent from claim registry")
    elif claim.get("status") != corpus.get("claim_status"):
        errors.append("claim status does not match corpus")
    elif claim.get("status") == "public" and (
        claim.get("support_level") != "partial"
        or claim.get("profile") != "aecctx-inspector-v1"
        or claim.get("evidence") != "docs/evidence/ACX-22.md"
    ):
        errors.append("public plugin claim mapping is invalid")

    if corpus.get("maximum_support") != "partial" or corpus.get("profile") != "aecctx-inspector-v1":
        errors.append("plugin corpus profile or maximum support is invalid")
    operations = corpus.get("operations")
    mapped = {entry.get("mcp_tool"): entry.get("skill") for entry in operations if isinstance(entry, dict)} if isinstance(operations, list) else {}
    if mapped != EXPECTED_TOOLS or len(operations or []) != len(EXPECTED_TOOLS):
        errors.append("plugin operation mapping is incomplete or non-canonical")
    if set(corpus.get("prompt_injection_surfaces", [])) != EXPECTED_SURFACES:
        errors.append("prompt-injection surface mapping is incomplete")

    hashes = corpus.get("file_sha256")
    if not isinstance(hashes, dict) or len(hashes) < 10:
        errors.append("plugin corpus must bind at least ten artifacts")
    else:
        prefix = "plugins/aecctx-inspector/"
        for relative, expected in sorted(hashes.items()):
            if not isinstance(relative, str) or not isinstance(expected, str):
                errors.append("artifact hash mapping must contain string paths and digests")
                continue
            path = plugin / relative.removeprefix(prefix) if relative.startswith(prefix) else repo / relative
            if not path.is_file() or path.is_symlink():
                errors.append(f"artifact is missing or not regular: {relative}")
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                errors.append(f"artifact hash mismatch: {relative}")
    return tuple(sorted(errors))


def main(argv: list[str] | None = None) -> int:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=repo / "conformance/v0.2/plugin-corpus.json")
    parser.add_argument("--claims", type=Path, default=repo / "conformance/v0.2/claims.json")
    parser.add_argument("--plugin", type=Path, default=repo / "plugins/aecctx-inspector")
    args = parser.parse_args(argv)
    errors = validate(repo, args.corpus.resolve(), args.claims.resolve(), args.plugin.resolve())
    if errors:
        for error in errors:
            print(f"aecctx Codex plugin conformance: {error}", file=sys.stderr)
        return 1
    print("aecctx Codex plugin conformance: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
