#!/usr/bin/env python3
"""Build and verify the deterministic ACX-37 inspector distribution."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import io
import json
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


PROFILE = "aecctx-inspector-distribution-v1"
SIGNING_PROFILE = "aecctx-inspector-distribution-signing-v1"
PLUGIN_VERSION = "0.3.0"
ROOT_NAME = "aecctx-inspector"
MANIFEST_PATH = "assets/distribution.json"
MARKER = ".aecctx-inspector-install.json"
MAX_FILES = 256
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_RATIO = 100
LOWER_SHA256 = re.compile(r"[0-9a-f]{64}")


class DistributionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DistributionResult:
    archive_path: Path
    archive_sha256: str
    archive_size: int
    inventory_sha256: str

    def statement(self) -> dict[str, Any]:
        return {
            "archive_sha256": self.archive_sha256,
            "archive_size": self.archive_size,
            "plugin_version": PLUGIN_VERSION,
            "profile": SIGNING_PROFILE,
        }


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative(path: str) -> bool:
    if not path or "\\" in path or "\x00" in path:
        return False
    value = PurePosixPath(path)
    return not value.is_absolute() and all(part not in {"", ".", ".."} for part in value.parts)


def source_inventory(plugin_root: Path) -> dict[str, dict[str, Any]]:
    if not plugin_root.is_dir() or plugin_root.is_symlink() or plugin_root.name != ROOT_NAME:
        raise DistributionError("plugin root must be a regular aecctx-inspector directory")
    files: dict[str, dict[str, Any]] = {}
    total = 0
    for path in sorted(plugin_root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(plugin_root).as_posix()
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"} or relative in {MANIFEST_PATH, MARKER}:
            continue
        if path.is_symlink():
            raise DistributionError(f"symlink is forbidden: {relative}")
        if path.is_dir():
            continue
        if not path.is_file() or not _safe_relative(relative):
            raise DistributionError(f"unsafe distribution entry: {relative}")
        data = path.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            raise DistributionError(f"distribution entry is too large: {relative}")
        total += len(data)
        files[relative] = {"bytes": len(data), "sha256": sha256_bytes(data)}
    if len(files) > MAX_FILES or total > MAX_TOTAL_BYTES:
        raise DistributionError("distribution inventory exceeds limits")
    return files


def inventory_digest(files: dict[str, dict[str, Any]]) -> str:
    return sha256_bytes(canonical_json(files))


def expected_distribution_manifest(plugin_root: Path) -> dict[str, Any]:
    files = source_inventory(plugin_root)
    compatibility = plugin_root / "assets" / "compatibility.json"
    if not compatibility.is_file() or compatibility.is_symlink():
        raise DistributionError("compatibility metadata is missing")
    return {
        "compatibility_sha256": sha256_bytes(compatibility.read_bytes()),
        "files": files,
        "inventory_sha256": inventory_digest(files),
        "package_format": "zip-fixed-v1",
        "plugin_version": PLUGIN_VERSION,
        "profile": PROFILE,
        "signature": {"required": False, "state_without_sidecar": "not_provided"},
    }


def validate_source(plugin_root: Path) -> dict[str, Any]:
    path = plugin_root / MANIFEST_PATH
    try:
        actual = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DistributionError("distribution manifest is invalid") from error
    expected = expected_distribution_manifest(plugin_root)
    if actual != expected or path.read_bytes() != canonical_json(actual):
        raise DistributionError("distribution manifest does not match source inventory")
    return actual


def build_distribution(plugin_root: Path, output: Path) -> DistributionResult:
    manifest = validate_source(plugin_root)
    paths = sorted([*manifest["files"], MANIFEST_PATH])
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        raise DistributionError("output already exists")
    with ZipFile(output, "x", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in paths:
            info = ZipInfo(f"{ROOT_NAME}/{relative}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, (plugin_root / relative).read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)
    data = output.read_bytes()
    return DistributionResult(output, sha256_bytes(data), len(data), manifest["inventory_sha256"])


def verify_archive(path: Path, expected_sha256: str) -> DistributionResult:
    data = path.read_bytes()
    if not LOWER_SHA256.fullmatch(expected_sha256) or sha256_bytes(data) != expected_sha256:
        raise DistributionError("archive checksum mismatch")
    total = 0
    with ZipFile(path) as archive:
        infos = archive.infolist()
        if not infos or len(infos) > MAX_FILES + 1 or [item.filename for item in infos] != sorted(item.filename for item in infos):
            raise DistributionError("archive inventory is invalid")
        extracted: dict[str, bytes] = {}
        for info in infos:
            name = info.filename
            if not name.startswith(f"{ROOT_NAME}/") or not _safe_relative(name):
                raise DistributionError("archive path is unsafe")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
                raise DistributionError("archive entry is not a regular file")
            relative = name.removeprefix(f"{ROOT_NAME}/")
            if info.file_size > MAX_FILE_BYTES or (info.compress_size and info.file_size > info.compress_size * MAX_RATIO):
                raise DistributionError("archive entry exceeds limits")
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise DistributionError("archive exceeds limits")
            extracted[relative] = archive.read(info)
    try:
        manifest = json.loads(extracted[MANIFEST_PATH])
    except (KeyError, UnicodeError, json.JSONDecodeError) as error:
        raise DistributionError("archive distribution manifest is invalid") from error
    files = manifest.get("files")
    actual_paths = set(extracted) - {MANIFEST_PATH}
    if not isinstance(files, dict) or set(files) != actual_paths:
        raise DistributionError("archive inventory does not match manifest")
    for relative, binding in files.items():
        content = extracted[relative]
        if binding != {"bytes": len(content), "sha256": sha256_bytes(content)}:
            raise DistributionError("archive inventory checksum mismatch")
    digest = inventory_digest(files)
    if manifest.get("inventory_sha256") != digest:
        raise DistributionError("archive inventory digest mismatch")
    return DistributionResult(path, expected_sha256, len(data), digest)


def install_distribution(
    archive_path: Path,
    expected_sha256: str,
    destination: Path,
    *,
    host_profile: str,
    mcp_version: str,
    signature: dict[str, Any] | None = None,
    public_key: Any | None = None,
) -> None:
    """Install exactly the verified archive bytes through the bundled manager."""
    result = verify_archive(archive_path, expected_sha256)
    if (signature is None) != (public_key is None):
        raise DistributionError("signature and public key must be supplied together")
    if signature is not None and not verify_distribution_signature(result, signature, public_key):
        raise DistributionError("distribution signature is invalid")
    if destination.exists() or destination.is_symlink():
        raise DistributionError("destination already exists")
    data = archive_path.read_bytes()
    if sha256_bytes(data) != expected_sha256:
        raise DistributionError("archive checksum changed before extraction")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".aecctx-inspector-archive-", dir=destination.parent) as temporary:
        root = Path(temporary)
        with ZipFile(io.BytesIO(data)) as source:
            for info in source.infolist():
                relative = info.filename.removeprefix(f"{ROOT_NAME}/")
                target = root / ROOT_NAME / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read(info))
        manager_path = root / ROOT_NAME / "scripts/manage.py"
        spec = importlib.util.spec_from_file_location("aecctx_inspector_archive_manager", manager_path)
        if spec is None or spec.loader is None:
            raise DistributionError("bundled manager cannot be loaded")
        manager = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = manager
        spec.loader.exec_module(manager)
        manager.install(root / ROOT_NAME, destination, host_profile=host_profile, mcp_version=mcp_version)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def sign_distribution(result: DistributionResult, private_key: Any) -> dict[str, Any]:
    statement = canonical_json(result.statement())
    return {"algorithm": "Ed25519", "profile": SIGNING_PROFILE, "signature": _b64url(private_key.sign(statement)), "statement": result.statement()}


def verify_distribution_signature(result: DistributionResult, signature: dict[str, Any], public_key: Any) -> bool:
    try:
        if signature.get("algorithm") != "Ed25519" or signature.get("profile") != SIGNING_PROFILE or signature.get("statement") != result.statement():
            return False
        public_key.verify(_unb64url(signature["signature"]), canonical_json(result.statement()))
    except Exception:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--plugin", type=Path, default=root / "plugins/aecctx-inspector")
    parser.add_argument("--output", type=Path, default=root / "dist/aecctx-inspector-0.3.0.zip")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--install-destination", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--host-profile")
    parser.add_argument("--mcp-version", default="1.28.1")
    args = parser.parse_args(argv)
    try:
        if args.install_destination is not None:
            if not args.expected_sha256 or not args.host_profile:
                raise DistributionError("archive install requires --expected-sha256 and --host-profile")
            install_distribution(
                args.output.resolve(),
                args.expected_sha256,
                args.install_destination.resolve(),
                host_profile=args.host_profile,
                mcp_version=args.mcp_version,
            )
            print(f"aecctx inspector distribution installed: {args.install_destination.resolve()}")
        elif args.check:
            validate_source(args.plugin.resolve())
            print("aecctx inspector distribution source: ok")
        else:
            result = build_distribution(args.plugin.resolve(), args.output.resolve())
            metadata = canonical_json({"archive_sha256": result.archive_sha256, "archive_size": result.archive_size, "inventory_sha256": result.inventory_sha256, "plugin_version": PLUGIN_VERSION, "profile": PROFILE, "signature_state": "not_provided"})
            metadata_path = args.output.with_suffix(args.output.suffix + ".json")
            if metadata_path.exists():
                raise DistributionError("metadata output already exists")
            metadata_path.write_bytes(metadata)
            print(result.archive_sha256)
    except (OSError, DistributionError) as error:
        print(f"aecctx inspector distribution: {error}", file=__import__("sys").stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
