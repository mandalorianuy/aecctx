#!/usr/bin/env python3
"""Validate, install or safely uninstall the local aecctx-inspector plugin."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import shutil
import sys
from pathlib import Path


MARKER = ".aecctx-inspector-install.json"
PROFILE = "aecctx-inspector-v1"
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")


class PluginManagementError(RuntimeError):
    pass


def is_compatible_aecctx_version(version: str) -> bool:
    match = VERSION_RE.fullmatch(version)
    if match is None:
        return False
    parsed = tuple(int(part) for part in match.groups())
    return (0, 1, 0) <= parsed < (0, 3, 0)


def _load_object(path: Path, label: str) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise PluginManagementError(f"{label} must be a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PluginManagementError(f"{label} must contain valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise PluginManagementError(f"{label} must contain a JSON object")
    return value


def _validate_plugin_root(plugin_root: Path) -> None:
    if plugin_root.name != "aecctx-inspector" or not plugin_root.is_dir() or plugin_root.is_symlink():
        raise PluginManagementError("plugin root must be a regular aecctx-inspector directory")
    manifest = _load_object(plugin_root / ".codex-plugin" / "plugin.json", "plugin manifest")
    compatibility = _load_object(plugin_root / "assets" / "compatibility.json", "compatibility metadata")
    if manifest.get("name") != "aecctx-inspector" or manifest.get("version") != "0.2.0":
        raise PluginManagementError("plugin manifest identity mismatch")
    if compatibility.get("profile") != PROFILE or compatibility.get("plugin_version") != "0.2.0":
        raise PluginManagementError("plugin compatibility identity mismatch")
    if any(path.is_symlink() for path in plugin_root.rglob("*")):
        raise PluginManagementError("plugin distribution must not contain symlinks")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory(plugin_root: Path) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for path in sorted(plugin_root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise PluginManagementError("plugin distribution must not contain symlinks")
        if path.is_file() and path.name != MARKER:
            inventory[path.relative_to(plugin_root).as_posix()] = _sha256(path)
    return inventory


def _installed_aecctx_version() -> str:
    try:
        version = importlib.metadata.version("aecctx")
    except importlib.metadata.PackageNotFoundError as error:
        raise PluginManagementError("compatible aecctx distribution is required") from error
    if not is_compatible_aecctx_version(version):
        raise PluginManagementError(f"installed aecctx version is incompatible: {version}")
    return version


def install(plugin_root: Path, destination: Path) -> None:
    _validate_plugin_root(plugin_root)
    core_version = _installed_aecctx_version()
    if destination.exists() or destination.is_symlink():
        raise PluginManagementError("destination already exists")
    if destination.name != "aecctx-inspector":
        raise PluginManagementError("destination must end in aecctx-inspector")
    try:
        shutil.copytree(plugin_root, destination, symlinks=False)
        marker = {
            "aecctx_version": core_version,
            "inventory": _inventory(destination),
            "plugin_version": "0.2.0",
            "profile": PROFILE,
        }
        (destination / MARKER).write_text(
            json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    except Exception:
        if destination.exists() and destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        raise


def uninstall(destination: Path) -> None:
    _validate_plugin_root(destination)
    marker = _load_object(destination / MARKER, "installation marker")
    if marker.get("profile") != PROFILE or marker.get("plugin_version") != "0.2.0":
        raise PluginManagementError("installation marker identity mismatch")
    expected = marker.get("inventory")
    if not isinstance(expected, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in expected.items()):
        raise PluginManagementError("installation marker inventory is invalid")
    if _inventory(destination) != expected:
        raise PluginManagementError("unexpected or modified content; refusing uninstall")
    shutil.rmtree(destination)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aecctx-inspector-manage")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("install", "uninstall"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--destination", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    destination = Path(arguments.destination).expanduser().resolve(strict=False)
    plugin_root = Path(__file__).resolve().parents[1]
    try:
        if arguments.command == "install":
            install(plugin_root, destination)
            print(f"aecctx-inspector installed: {destination}")
        else:
            uninstall(destination)
            print(f"aecctx-inspector uninstalled: {destination}")
    except (OSError, PluginManagementError) as error:
        print(f"aecctx-inspector: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
