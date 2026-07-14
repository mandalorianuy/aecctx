#!/usr/bin/env python3
"""Validate the ACX-37 inspector distribution, claim and safety corpus."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any


PROFILE = "aecctx-inspector-distribution-v1"
CLAIM = "codex.aecctx-inspector-distribution"
HOSTS = {"codex-local-v1-linux", "codex-local-v1-macos", "codex-local-v1-windows"}
OPERATIONS = {"aecctx_validate", "aecctx_info", "aecctx_query", "aecctx_diff", "aecctx_context", "aecctx_gate"}
FORBIDDEN_PLUGIN_TOKENS = ("subprocess", "shell=True", "docker run", "dwgread", "tesseract", "cadquery", "woodframing", "wfdomain", "wfimport")


def _load(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        errors.append(f"{label} is invalid: {error}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} must be a JSON object")
        return None
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _builder(repo: Path):
    path = repo / "scripts/build_inspector_distribution.py"
    spec = importlib.util.spec_from_file_location("aecctx_inspector_distribution_checker_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("builder cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _artifact_names(path: Path) -> tuple[str, ...]:
    if path.suffix == ".whl" or path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            return tuple(archive.namelist())
    with tarfile.open(path, "r:*") as archive:
        return tuple(member.name for member in archive.getmembers() if member.isfile())


def validate(repo: Path, corpus_path: Path, claims_path: Path, *, require_public: bool, artifacts: tuple[Path, ...]) -> tuple[str, ...]:
    errors: list[str] = []
    corpus = _load(corpus_path, "plugin corpus", errors)
    claims = _load(claims_path, "claim registry", errors)
    if corpus is None or claims is None:
        return tuple(sorted(errors))
    claim = next((item for item in claims.get("claims", []) if isinstance(item, dict) and item.get("id") == CLAIM), None)
    if claim is None:
        errors.append("distribution claim is absent")
    else:
        expected_status = "public" if require_public else corpus.get("claim_status")
        if claim.get("status") != expected_status or claim.get("profile") != PROFILE:
            errors.append("distribution claim state/profile mismatch")
        if require_public and (claim.get("support_level") != "partial" or claim.get("evidence") != "docs/evidence/ACX-37.md"):
            errors.append("public distribution claim mapping is invalid")

    if corpus.get("profile") != PROFILE or corpus.get("claim_id") != CLAIM or corpus.get("maximum_support") != "partial":
        errors.append("plugin corpus identity is invalid")
    host_matrix = _load(repo / "fixtures/v0.3/plugin/host-matrix.json", "host matrix", errors)
    if host_matrix is not None:
        hosts = host_matrix.get("hosts")
        ids = {item.get("host_profile") for item in hosts if isinstance(item, dict)} if isinstance(hosts, list) else set()
        if ids != HOSTS or any(item.get("python") != "3.12" or item.get("mcp") != "1.28.1" for item in hosts or [] if isinstance(item, dict)):
            errors.append("host matrix is incomplete or inexact")
    operations = corpus.get("operations")
    if not isinstance(operations, list) or {item.get("mcp_tool") for item in operations if isinstance(item, dict)} != OPERATIONS or len(operations) != 6:
        errors.append("six-operation parity mapping is invalid")

    bindings = corpus.get("file_sha256")
    if not isinstance(bindings, dict) or len(bindings) < 15:
        errors.append("plugin corpus file bindings are incomplete")
    else:
        for relative, expected in bindings.items():
            path = repo / relative
            if not isinstance(relative, str) or not isinstance(expected, str) or not path.is_file() or path.is_symlink():
                errors.append(f"bound file is missing or unsafe: {relative}")
            elif _sha256(path) != expected:
                errors.append(f"bound file hash mismatch: {relative}")

    try:
        _builder(repo).validate_source(repo / "plugins/aecctx-inspector")
    except Exception as error:
        errors.append(f"distribution source validation failed: {error}")
    plugin = repo / "plugins/aecctx-inspector"
    mcp = (plugin / ".mcp.json").read_text(encoding="utf-8")
    if json.loads(mcp) != {"mcpServers": {"aecctx": {"command": "aecctx-mcp", "args": []}}}:
        errors.append("MCP surface is not the fixed local stdio allowlist")
    scan = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in plugin.rglob("*") if path.is_file()).lower()
    for token in FORBIDDEN_PLUGIN_TOKENS:
        if token in scan:
            errors.append(f"plugin contains forbidden execution/consumer token: {token}")
    project = (repo / "pyproject.toml").read_text(encoding="utf-8").lower()
    wheel_section = project.split("[tool.hatch.build.targets.wheel]", 1)[1].split("[tool.hatch.build.targets.sdist]", 1)[0]
    if "plugin" in wheel_section or "codex" in wheel_section:
        errors.append("core wheel depends on plugin content")
    for artifact in artifacts:
        names = tuple(name.lower() for name in _artifact_names(artifact))
        if artifact.suffix == ".whl" and any("aecctx-inspector" in name or "/plugins/" in name for name in names):
            errors.append(f"core wheel contains plugin payload: {artifact}")
        implementation_names = tuple(name for name in names if "/src/" in name or "/plugins/aecctx-inspector/" in name)
        if any("woodframing" in name or "wfdomain" in name or "wfimport" in name for name in implementation_names):
            errors.append(f"artifact contains consumer content: {artifact}")
    return tuple(sorted(set(errors)))


def main(argv: list[str] | None = None) -> int:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=repo / "conformance/v0.3/plugin-corpus.json")
    parser.add_argument("--claims", type=Path, default=repo / "conformance/v0.3/claims.json")
    parser.add_argument("--require-public", action="store_true")
    parser.add_argument("--artifact", type=Path, action="append", default=[])
    args = parser.parse_args(argv)
    errors = validate(repo, args.corpus.resolve(), args.claims.resolve(), require_public=args.require_public, artifacts=tuple(item.resolve() for item in args.artifact))
    if errors:
        for error in errors:
            print(f"aecctx inspector v0.3 conformance: {error}", file=sys.stderr)
        return 1
    print("aecctx inspector v0.3 conformance: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
