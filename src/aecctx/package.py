from __future__ import annotations

import hashlib
import json
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO


@dataclass(frozen=True, slots=True)
class SafetyLimits:
    max_members: int = 10_000
    max_member_bytes: int = 512 * 1024 * 1024
    max_total_bytes: int = 2 * 1024 * 1024 * 1024
    max_decompression_ratio: float = 200.0


class PackageReadError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class PackageArtifact:
    path: str
    content: bytes | Path
    media_type: str
    role: str
    authoritative: bool


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def hash_stream(handle: BinaryIO, *, chunk_size: int = 1024 * 1024) -> tuple[str, int]:
    digest = hashlib.sha256()
    byte_size = 0
    while chunk := handle.read(chunk_size):
        digest.update(chunk)
        byte_size += len(chunk)
    return digest.hexdigest(), byte_size


def hash_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> tuple[str, int]:
    with Path(path).open("rb") as handle:
        return hash_stream(handle, chunk_size=chunk_size)


def safe_logical_path(value: str) -> PurePosixPath:
    if not value or "\\" in value or "\x00" in value:
        raise PackageReadError("AECCTX_ARCHIVE_PATH_UNSAFE", f"Unsafe archive path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PackageReadError("AECCTX_ARCHIVE_PATH_UNSAFE", f"Unsafe archive path: {value!r}")
    if path.parts and ":" in path.parts[0]:
        raise PackageReadError("AECCTX_ARCHIVE_PATH_UNSAFE", f"Unsafe archive path: {value!r}")
    return path


def _deterministic_zip_info(logical_path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(logical_path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.flag_bits |= 0x800
    return info


def _copy_content(content: bytes | Path, target: BinaryIO) -> None:
    if isinstance(content, Path):
        with content.open("rb") as source:
            shutil.copyfileobj(source, target, length=1024 * 1024)
    else:
        target.write(content)


class PackageWriter:
    def __init__(self, output_path: str | Path, *, package_form: str = "directory") -> None:
        if package_form not in {"directory", "zip"}:
            raise ValueError("package_form must be directory or zip")
        self.output = Path(output_path)
        self.package_form = package_form

    def write(
        self,
        *,
        package_id: str,
        created_at: str,
        source_ids: list[str],
        capabilities: dict[str, str],
        loss_summary: list[str],
        embedding_policy: str,
        producer: dict[str, str],
        artifacts: list[PackageArtifact],
    ) -> dict[str, Any]:
        if self.output.exists():
            raise FileExistsError(self.output)
        files: dict[str, bytes | Path] = {}
        inventory: list[dict[str, Any]] = []
        digest_lines: list[bytes] = []
        for artifact in sorted(artifacts, key=lambda item: item.path):
            logical_path = safe_logical_path(artifact.path).as_posix()
            if logical_path == "manifest.json" or logical_path in files:
                raise ValueError(f"duplicate or reserved artifact path: {logical_path}")
            if isinstance(artifact.content, Path):
                digest, byte_size = hash_file(artifact.content)
            else:
                digest = hashlib.sha256(artifact.content).hexdigest()
                byte_size = len(artifact.content)
            inventory.append(
                {
                    "authoritative": artifact.authoritative,
                    "bytes": byte_size,
                    "media_type": artifact.media_type,
                    "path": logical_path,
                    "role": artifact.role,
                    "sha256": digest,
                }
            )
            digest_lines.append(f"{logical_path}\0{digest}\0{byte_size}\n".encode("utf-8"))
            files[logical_path] = artifact.content
        logical_digest = hashlib.sha256(b"".join(digest_lines)).hexdigest()
        manifest: dict[str, Any] = {
            "aecctx_version": "0.1.0-draft",
            "artifacts": inventory,
            "capabilities": capabilities,
            "created_at": created_at,
            "logical_digest": logical_digest,
            "loss_summary": loss_summary,
            "package_form": self.package_form,
            "package_id": package_id,
            "producer": producer,
            "source_embedding_policy": embedding_policy,
            "source_ids": source_ids,
        }
        files["manifest.json"] = canonical_json(manifest)
        self.output.parent.mkdir(parents=True, exist_ok=True)
        if self.package_form == "directory":
            self.output.mkdir()
            for logical_path, content in sorted(files.items()):
                target = self.output.joinpath(*safe_logical_path(logical_path).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("wb") as handle:
                    _copy_content(content, handle)
        else:
            with tempfile.NamedTemporaryFile(dir=self.output.parent, prefix=f".{self.output.name}.", delete=False) as temporary:
                temporary_path = Path(temporary.name)
            try:
                with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                    for logical_path, content in sorted(files.items()):
                        with archive.open(_deterministic_zip_info(logical_path), "w", force_zip64=True) as handle:
                            _copy_content(content, handle)
                temporary_path.replace(self.output)
            finally:
                temporary_path.unlink(missing_ok=True)
        return manifest


class PackageReader:
    def __init__(self, package_path: str | Path, *, limits: SafetyLimits | None = None) -> None:
        self.path = Path(package_path)
        self.limits = limits or SafetyLimits()
        self._archive_infos: dict[str, zipfile.ZipInfo] | None = None
        if self.path.is_dir():
            manifest_bytes = self._read_directory_member("manifest.json")
        elif self.path.is_file():
            self._archive_infos = self._inspect_archive()
            manifest_bytes = self.read_bytes("manifest.json")
        else:
            raise PackageReadError("AECCTX_PACKAGE_NOT_FOUND", f"Package not found: {self.path}")
        try:
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PackageReadError("AECCTX_JSON_INVALID", f"Invalid manifest.json: {error}") from error
        if not isinstance(manifest, dict):
            raise PackageReadError("AECCTX_JSON_INVALID", "manifest.json must contain an object")
        self.manifest: dict[str, Any] = manifest

    @property
    def is_archive(self) -> bool:
        return self._archive_infos is not None

    def _inspect_archive(self) -> dict[str, zipfile.ZipInfo]:
        try:
            archive = zipfile.ZipFile(self.path)
        except (OSError, zipfile.BadZipFile) as error:
            raise PackageReadError("AECCTX_ARCHIVE_INVALID", str(error)) from error
        with archive:
            infos = archive.infolist()
            if len(infos) > self.limits.max_members:
                raise PackageReadError("AECCTX_ARCHIVE_MEMBER_LIMIT_EXCEEDED", "Archive member count exceeds safety limit")
            result: dict[str, zipfile.ZipInfo] = {}
            total = 0
            for info in infos:
                if info.is_dir():
                    safe_logical_path(info.filename.rstrip("/"))
                    continue
                logical = safe_logical_path(info.filename).as_posix()
                if logical in result:
                    raise PackageReadError("AECCTX_ARCHIVE_PATH_DUPLICATE", f"Duplicate archive member: {logical}")
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) == stat.S_IFLNK:
                    raise PackageReadError("AECCTX_ARCHIVE_SYMLINK_UNSAFE", f"Archive symlink is forbidden: {logical}")
                if info.file_size > self.limits.max_member_bytes:
                    raise PackageReadError("AECCTX_ARCHIVE_MEMBER_SIZE_EXCEEDED", f"Archive member exceeds size limit: {logical}")
                total += info.file_size
                if total > self.limits.max_total_bytes:
                    raise PackageReadError("AECCTX_ARCHIVE_TOTAL_SIZE_EXCEEDED", "Archive uncompressed size exceeds safety limit")
                if info.file_size:
                    ratio = info.file_size / max(info.compress_size, 1)
                    if ratio > self.limits.max_decompression_ratio:
                        raise PackageReadError("AECCTX_ARCHIVE_RATIO_EXCEEDED", f"Archive member compression ratio exceeds limit: {logical}")
                result[logical] = info
        if "manifest.json" not in result:
            raise PackageReadError("AECCTX_MANIFEST_MISSING", "Archive root does not contain manifest.json")
        return result

    def _read_directory_member(self, logical_path: str) -> bytes:
        logical = safe_logical_path(logical_path)
        member = self.path.joinpath(*logical.parts)
        try:
            if member.is_symlink() or not member.is_file():
                raise PackageReadError("AECCTX_ARTIFACT_MISSING", f"Package artifact is missing: {logical_path}")
            if member.stat().st_size > self.limits.max_member_bytes:
                raise PackageReadError("AECCTX_ARTIFACT_SIZE_EXCEEDED", f"Package artifact exceeds size limit: {logical_path}")
            return member.read_bytes()
        except OSError as error:
            raise PackageReadError("AECCTX_ARTIFACT_UNREADABLE", str(error)) from error

    def read_bytes(self, logical_path: str) -> bytes:
        logical = safe_logical_path(logical_path).as_posix()
        if self._archive_infos is None:
            return self._read_directory_member(logical)
        info = self._archive_infos.get(logical)
        if info is None:
            raise PackageReadError("AECCTX_ARTIFACT_MISSING", f"Package artifact is missing: {logical}")
        try:
            with zipfile.ZipFile(self.path) as archive, archive.open(info) as handle:
                data = handle.read(self.limits.max_member_bytes + 1)
        except (OSError, zipfile.BadZipFile, RuntimeError) as error:
            raise PackageReadError("AECCTX_ARCHIVE_INVALID", str(error)) from error
        if len(data) > self.limits.max_member_bytes:
            raise PackageReadError("AECCTX_ARCHIVE_MEMBER_SIZE_EXCEEDED", f"Archive member exceeds size limit: {logical}")
        return data

    def extract_to(self, destination: str | Path) -> None:
        destination_path = Path(destination)
        destination_path.mkdir(parents=True, exist_ok=True)
        if self._archive_infos is None:
            for path in sorted(self.path.rglob("*")):
                if path.is_symlink():
                    raise PackageReadError("AECCTX_PACKAGE_SYMLINK_UNSAFE", f"Package symlink is forbidden: {path}")
                if path.is_file():
                    relative = path.relative_to(self.path).as_posix()
                    target = destination_path.joinpath(*safe_logical_path(relative).parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
            return
        for logical in sorted(self._archive_infos):
            target = destination_path.joinpath(*safe_logical_path(logical).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.read_bytes(logical))
