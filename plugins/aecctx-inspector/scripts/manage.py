#!/usr/bin/env python3
"""Validate and manage the local integrity-bound aecctx-inspector plugin."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path


MARKER = ".aecctx-inspector-install.json"
PROFILE = "aecctx-inspector-distribution-v1"
LEGACY_PROFILE = "aecctx-inspector-v1"
PLUGIN_VERSION = "0.3.0"
HOST_PROFILES = frozenset({"codex-local-v1-linux", "codex-local-v1-macos", "codex-local-v1-windows"})
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][0-9A-Za-z.-]+)?$")


class PluginManagementError(RuntimeError):
    pass


def _version(value: str) -> tuple[int, int, int] | None:
    match = VERSION_RE.fullmatch(value)
    return tuple(int(part) for part in match.groups()) if match else None


def is_compatible_aecctx_version(version: str) -> bool:
    """Retain the v0.2 helper contract for legacy source installations."""
    parsed = _version(version)
    return parsed is not None and (0, 1, 0) <= parsed < (0, 3, 0)


def is_compatible_v03_core_version(version: str) -> bool:
    parsed = _version(version)
    return parsed is not None and (0, 2, 0) <= parsed < (0, 4, 0)


def is_compatible_mcp_version(version: str) -> bool:
    parsed = _version(version)
    return parsed is not None and (1, 20, 0) <= parsed < (2, 0, 0)


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory(plugin_root: Path, *, distribution_binding: bool = False) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for path in sorted(plugin_root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(plugin_root).as_posix()
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"} or relative == MARKER:
            continue
        if distribution_binding and relative == "assets/distribution.json":
            continue
        if path.is_symlink():
            raise PluginManagementError("plugin distribution must not contain symlinks")
        if path.is_file():
            inventory[relative] = _sha256(path)
        elif not path.is_dir():
            raise PluginManagementError("plugin distribution must contain regular files only")
    return inventory


def _validate_plugin_root(plugin_root: Path) -> tuple[str, dict[str, object]]:
    if plugin_root.name != "aecctx-inspector" or not plugin_root.is_dir() or plugin_root.is_symlink():
        raise PluginManagementError("plugin root must be a regular aecctx-inspector directory")
    manifest = _load_object(plugin_root / ".codex-plugin/plugin.json", "plugin manifest")
    compatibility = _load_object(plugin_root / "assets/compatibility.json", "compatibility metadata")
    distribution = _load_object(plugin_root / "assets/distribution.json", "distribution metadata")
    version = manifest.get("version")
    if manifest.get("name") != "aecctx-inspector" or version != PLUGIN_VERSION:
        raise PluginManagementError("plugin manifest identity mismatch")
    if compatibility.get("profile") != PROFILE or compatibility.get("plugin_version") != PLUGIN_VERSION:
        raise PluginManagementError("plugin compatibility identity mismatch")
    if distribution.get("profile") != PROFILE or distribution.get("plugin_version") != PLUGIN_VERSION:
        raise PluginManagementError("distribution metadata identity mismatch")
    expected_files = distribution.get("files")
    actual = _inventory(plugin_root, distribution_binding=True)
    if not isinstance(expected_files, dict) or set(expected_files) != set(actual):
        raise PluginManagementError("distribution metadata inventory mismatch")
    for relative, binding in expected_files.items():
        path = plugin_root / relative
        if not isinstance(binding, dict) or binding != {"bytes": path.stat().st_size, "sha256": actual[relative]}:
            raise PluginManagementError("distribution metadata inventory mismatch")
    canonical = (json.dumps(distribution, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if (plugin_root / "assets/distribution.json").read_bytes() != canonical:
        raise PluginManagementError("distribution metadata must be canonical JSON")
    return str(version), compatibility


def _installed_aecctx_version() -> str:
    try:
        version = importlib.metadata.version("aecctx")
    except importlib.metadata.PackageNotFoundError as error:
        raise PluginManagementError("compatible aecctx distribution is required") from error
    if not is_compatible_v03_core_version(version):
        raise PluginManagementError(f"installed aecctx version is incompatible: {version}")
    return version


def _installed_mcp_version() -> str:
    try:
        version = importlib.metadata.version("mcp")
    except importlib.metadata.PackageNotFoundError as error:
        raise PluginManagementError("compatible mcp distribution is required") from error
    if not is_compatible_mcp_version(version):
        raise PluginManagementError(f"installed mcp version is incompatible: {version}")
    return version


def _default_host_profile() -> str:
    if sys.platform.startswith("linux"):
        return "codex-local-v1-linux"
    if sys.platform == "darwin":
        return "codex-local-v1-macos"
    if sys.platform == "win32":
        return "codex-local-v1-windows"
    raise PluginManagementError(f"unsupported host platform: {sys.platform}")


def _runtime(host_profile: str | None, mcp_version: str | None) -> tuple[str, str, str]:
    core = _installed_aecctx_version()
    mcp = _installed_mcp_version() if mcp_version is None else mcp_version
    host = _default_host_profile() if host_profile is None else host_profile
    if host not in HOST_PROFILES:
        raise PluginManagementError(f"unsupported host profile: {host}")
    if not is_compatible_mcp_version(mcp):
        raise PluginManagementError(f"installed mcp version is incompatible: {mcp}")
    return core, mcp, host


def _marker(plugin_root: Path) -> dict[str, object]:
    marker = _load_object(plugin_root / MARKER, "installation marker")
    expected = marker.get("inventory")
    if marker.get("profile") not in {PROFILE, LEGACY_PROFILE} or not isinstance(expected, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in expected.items()):
        raise PluginManagementError("installation marker is invalid")
    if _inventory(plugin_root) != expected:
        raise PluginManagementError("unexpected or modified content; refusing lifecycle operation")
    return marker


def _copy_install(plugin_root: Path, destination: Path, *, core: str, mcp: str, host: str) -> None:
    shutil.copytree(plugin_root, destination, symlinks=False, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", MARKER))
    marker = {
        "aecctx_version": core,
        "host_profile": host,
        "inventory": _inventory(destination),
        "mcp_version": mcp,
        "plugin_version": PLUGIN_VERSION,
        "profile": PROFILE,
    }
    (destination / MARKER).write_text(json.dumps(marker, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def install(plugin_root: Path, destination: Path, *, host_profile: str | None = None, mcp_version: str | None = None) -> None:
    _validate_plugin_root(plugin_root)
    core, mcp, host = _runtime(host_profile, mcp_version)
    if destination.exists() or destination.is_symlink():
        raise PluginManagementError("destination already exists")
    if destination.name != "aecctx-inspector":
        raise PluginManagementError("destination must end in aecctx-inspector")
    try:
        _copy_install(plugin_root, destination, core=core, mcp=mcp, host=host)
    except Exception:
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        raise


def upgrade(plugin_root: Path, destination: Path, *, host_profile: str | None = None, mcp_version: str | None = None) -> None:
    current = _marker(destination)
    new_manifest = _load_object(plugin_root / ".codex-plugin/plugin.json", "plugin manifest")
    new_version = new_manifest.get("version")
    current_version = current.get("plugin_version")
    if not isinstance(new_version, str) or not isinstance(current_version, str) or _version(new_version) is None or _version(current_version) is None:
        raise PluginManagementError("plugin version is invalid")
    if _version(new_version) <= _version(current_version):
        raise PluginManagementError("equal-version replacement or downgrade is forbidden")
    _validate_plugin_root(plugin_root)
    core, mcp, host = _runtime(host_profile, mcp_version)
    parent = destination.parent
    stage = Path(tempfile.mkdtemp(prefix=".aecctx-inspector-stage-", dir=parent)) / "aecctx-inspector"
    backup = parent / f".aecctx-inspector-backup-{os.getpid()}"
    try:
        _copy_install(plugin_root, stage, core=core, mcp=mcp, host=host)
        _marker(stage)
        destination.rename(backup)
        try:
            stage.rename(destination)
        except Exception:
            backup.rename(destination)
            raise
        shutil.rmtree(backup)
    finally:
        if stage.parent.exists():
            shutil.rmtree(stage.parent)
        if backup.exists() and not destination.exists():
            backup.rename(destination)


def uninstall(destination: Path) -> None:
    _marker(destination)
    shutil.rmtree(destination)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aecctx-inspector-manage")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("install", "upgrade", "uninstall"):
        item = subparsers.add_parser(command)
        item.add_argument("--destination", required=True)
        if command != "uninstall":
            item.add_argument("--host-profile", choices=sorted(HOST_PROFILES))
            item.add_argument("--mcp-version")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    destination = Path(arguments.destination).expanduser().resolve(strict=False)
    plugin_root = Path(__file__).resolve().parents[1]
    try:
        if arguments.command == "install":
            install(plugin_root, destination, host_profile=arguments.host_profile, mcp_version=arguments.mcp_version)
        elif arguments.command == "upgrade":
            upgrade(plugin_root, destination, host_profile=arguments.host_profile, mcp_version=arguments.mcp_version)
        else:
            uninstall(destination)
        print(f"aecctx-inspector {arguments.command} complete: {destination}")
    except (OSError, PluginManagementError) as error:
        print(f"aecctx-inspector: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
