from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Mapping

from jsonschema import Draft202012Validator

from .package import hash_file


class SourceBundleError(ValueError):
    code = "AECCTX_DXF_BUNDLE_INVALID"

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class SourceBundleEntry:
    logical_path: str
    path: Path
    role: str
    media_type: str
    byte_size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class SourceBundle:
    directory: Path
    root: SourceBundleEntry
    entries: tuple[SourceBundleEntry, ...]
    total_bytes: int

    @property
    def by_path(self) -> Mapping[str, SourceBundleEntry]:
        return {entry.logical_path: entry for entry in self.entries}


def _code(prefix: str, suffix: str) -> str:
    return f"AECCTX_{prefix}_BUNDLE_{suffix}"


def _bundle_error(prefix: str, suffix: str, message: str) -> SourceBundleError:
    return SourceBundleError(_code(prefix, suffix), message)


def _strict_json(data: bytes, prefix: str) -> object:
    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise _bundle_error(prefix, "MANIFEST_INVALID", f"Duplicate source-bundle key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(data, object_pairs_hook=object_pairs)
    except SourceBundleError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _bundle_error(prefix, "MANIFEST_INVALID", "source-bundle.json is not strict UTF-8 JSON") from error


def _safe_bundle_path(value: object, prefix: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "://" in value or "\0" in value:
        raise _bundle_error(prefix, "PATH_UNSAFE", f"Unsafe source-bundle path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts) or (path.parts and ":" in path.parts[0]):
        raise _bundle_error(prefix, "PATH_UNSAFE", f"Unsafe source-bundle path: {value!r}")
    return path


def normalize_source_bundle_path(value: object, *, diagnostic_prefix: str = "DXF") -> PurePosixPath:
    """Normalize one inert logical path under the same closed bundle policy."""

    return _safe_bundle_path(value, diagnostic_prefix.upper())


def load_source_bundle(
    path: str | Path,
    *,
    max_files: int = 32,
    max_member_bytes: int = 512 * 1024 * 1024,
    max_total_bytes: int = 1024 * 1024 * 1024,
    allowed_media_types: set[str] | frozenset[str] | None = None,
    diagnostic_prefix: str = "DXF",
) -> SourceBundle:
    prefix = diagnostic_prefix.upper()
    if prefix not in {"DXF", "DWG"}:
        raise ValueError("source-bundle diagnostic prefix must be DXF or DWG")
    if not (1 <= max_files <= 32 and 1 <= max_member_bytes <= 512 * 1024 * 1024 and 1 <= max_total_bytes <= 1024 * 1024 * 1024):
        raise ValueError(f"{prefix} source-bundle limits must be positive and no greater than profile ceilings")
    media_types = frozenset(allowed_media_types or {"application/dxf", "application/x-dxf"})
    if not media_types or not media_types <= {"application/dxf", "application/x-dxf", "image/vnd.dwg"}:
        raise ValueError("source-bundle allowed media types are outside the governed schema")
    directory = Path(path)
    if not directory.is_dir() or directory.is_symlink():
        raise _bundle_error(prefix, "ROOT_INVALID", "source bundle must be a regular directory")
    manifest_path = directory / "source-bundle.json"
    if not manifest_path.is_file() or manifest_path.is_symlink() or manifest_path.stat().st_size > 1024 * 1024:
        raise _bundle_error(prefix, "MANIFEST_INVALID", "source-bundle.json must be a regular file no larger than 1 MiB")
    value = _strict_json(manifest_path.read_bytes(), prefix)
    schema = json.loads(files("aecctx.schemas.v0_2").joinpath("source-bundle.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        if "path" in str(first.absolute_path) or "root" in str(first.absolute_path):
            raise _bundle_error(prefix, "PATH_UNSAFE", first.message)
        raise _bundle_error(prefix, "MANIFEST_INVALID", first.message)
    assert isinstance(value, dict)
    raw_entries = value["entries"]
    assert isinstance(raw_entries, list)
    if len(raw_entries) > max_files:
        raise _bundle_error(prefix, "FILE_LIMIT_EXCEEDED", "source bundle exceeds file limit")
    root_real = directory.resolve(strict=True)
    seen: set[str] = set()
    entries: list[SourceBundleEntry] = []
    total_bytes = 0
    for raw in raw_entries:
        assert isinstance(raw, dict)
        logical = _safe_bundle_path(raw["path"], prefix).as_posix()
        if logical in seen:
            raise _bundle_error(prefix, "DUPLICATE_PATH", f"Duplicate source-bundle path: {logical}")
        seen.add(logical)
        if raw["media_type"] not in media_types:
            raise _bundle_error(prefix, "MEDIA_TYPE_INVALID", f"Source-bundle media type is not admitted: {logical}")
        member = directory.joinpath(*PurePosixPath(logical).parts)
        cursor = member
        while cursor != directory:
            if cursor.is_symlink():
                raise _bundle_error(prefix, "MEMBER_NOT_REGULAR", f"Symlink source-bundle member: {logical}")
            cursor = cursor.parent
        if not member.is_file() or member.is_symlink():
            raise _bundle_error(prefix, "MEMBER_NOT_REGULAR", f"Missing or non-regular source-bundle member: {logical}")
        try:
            member.resolve(strict=True).relative_to(root_real)
        except ValueError as error:
            raise _bundle_error(prefix, "PATH_UNSAFE", f"Source-bundle member escapes root: {logical}") from error
        actual_size = member.stat().st_size
        if actual_size != raw["bytes"]:
            raise _bundle_error(prefix, "SIZE_MISMATCH", f"Source-bundle size mismatch: {logical}")
        if actual_size > max_member_bytes:
            raise _bundle_error(prefix, "MEMBER_LIMIT_EXCEEDED", f"Source-bundle member exceeds byte limit: {logical}")
        total_bytes += actual_size
        if total_bytes > max_total_bytes:
            raise _bundle_error(prefix, "TOTAL_LIMIT_EXCEEDED", "source bundle exceeds aggregate byte limit")
        digest, _ = hash_file(member)
        if digest != raw["sha256"]:
            raise _bundle_error(prefix, "DIGEST_MISMATCH", f"Source-bundle digest mismatch: {logical}")
        entries.append(SourceBundleEntry(logical, member, str(raw["role"]), str(raw["media_type"]), actual_size, digest))
    root_logical = _safe_bundle_path(value["root"], prefix).as_posix()
    roots = [entry for entry in entries if entry.role == "root"]
    if len(roots) != 1 or roots[0].logical_path != root_logical:
        raise _bundle_error(prefix, "ROOT_INVALID", "source bundle requires exactly one matching root entry")
    return SourceBundle(directory, roots[0], tuple(sorted(entries, key=lambda entry: entry.logical_path)), total_bytes)
