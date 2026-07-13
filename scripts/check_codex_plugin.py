#!/usr/bin/env python3
"""Validate the bounded aecctx-inspector distribution contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_COMPATIBILITY = {
    "aecctx": ">=0.1.0,<0.3.0",
    "core_optional": True,
    "marketplace_published": False,
    "mcp": ">=1.20,<2",
    "plugin_version": "0.2.0",
    "profile": "aecctx-inspector-v1",
    "python": ">=3.12",
}
EXPECTED_MCP = {
    "mcpServers": {
        "aecctx": {
            "command": "aecctx-mcp",
            "args": [],
        }
    }
}


def _load_object(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file() or path.is_symlink():
        errors.append(f"{label} must be a regular file")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append(f"{label} must contain valid UTF-8 JSON")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} must contain a JSON object")
        return None
    return value


def validate_plugin(plugin_root: Path) -> tuple[str, ...]:
    errors: list[str] = []
    if plugin_root.name != "aecctx-inspector" or not plugin_root.is_dir() or plugin_root.is_symlink():
        return ("plugin root must be a regular aecctx-inspector directory",)
    manifest = _load_object(plugin_root / ".codex-plugin" / "plugin.json", "plugin manifest", errors)
    mcp = _load_object(plugin_root / ".mcp.json", "MCP manifest", errors)
    compatibility = _load_object(plugin_root / "assets" / "compatibility.json", "compatibility metadata", errors)

    if manifest is not None:
        if manifest.get("name") != "aecctx-inspector":
            errors.append("plugin manifest name must be aecctx-inspector")
        if manifest.get("version") != "0.2.0":
            errors.append("plugin manifest version must be 0.2.0")
        if manifest.get("skills") != "./skills/":
            errors.append("plugin manifest must reference ./skills/")
        if manifest.get("mcpServers") != "./.mcp.json":
            errors.append("plugin manifest must reference ./.mcp.json")
        if manifest.get("license") != "Apache-2.0":
            errors.append("plugin manifest license must be Apache-2.0")
    if mcp is not None and mcp != EXPECTED_MCP:
        errors.append("MCP manifest must allowlist only the local aecctx-mcp stdio command")
    if compatibility is not None and compatibility != EXPECTED_COMPATIBILITY:
        errors.append("compatibility metadata does not match aecctx-inspector-v1")

    for path in plugin_root.rglob("*"):
        if path.is_symlink():
            errors.append(f"plugin distribution must not contain symlinks: {path.relative_to(plugin_root)}")
    return tuple(sorted(errors))


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) > 1:
        print("usage: check_codex_plugin.py [plugin-root]", file=sys.stderr)
        return 2
    repo_root = Path(__file__).resolve().parents[1]
    plugin_root = Path(arguments[0]).resolve() if arguments else repo_root / "plugins" / "aecctx-inspector"
    errors = validate_plugin(plugin_root)
    if errors:
        for error in errors:
            print(f"aecctx Codex plugin: {error}", file=sys.stderr)
        return 1
    print("aecctx Codex plugin: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
