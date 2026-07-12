from __future__ import annotations

import hashlib
import json
import tracemalloc
import zipfile
from pathlib import Path

import pytest

from aecctx.package import PackageArtifact, PackageReadError, PackageReader, PackageWriter, SafetyLimits, hash_file


def test_hash_file_streams_large_inputs(tmp_path: Path) -> None:
    source = tmp_path / "large.bin"
    block = b"aecctx-streaming\0" * 4096
    with source.open("wb") as handle:
        for _ in range(128):
            handle.write(block)

    tracemalloc.start()
    digest, byte_size = hash_file(source, chunk_size=64 * 1024)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert digest == hashlib.sha256(source.read_bytes()).hexdigest()
    assert byte_size == source.stat().st_size
    assert peak < 2 * 1024 * 1024


def test_reader_opens_directory_and_archive_forms(minimal_package: Path, tmp_path: Path) -> None:
    archive = tmp_path / "fixture.aecctx"
    with zipfile.ZipFile(archive, "w") as output:
        for path in sorted(minimal_package.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(minimal_package).as_posix())

    directory_manifest = PackageReader(minimal_package).manifest
    archive_manifest = PackageReader(archive).manifest

    assert directory_manifest["package_id"] == "pkg_minimal_fixture"
    assert archive_manifest["package_id"] == "pkg_minimal_fixture"


def test_reader_rejects_archive_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "malicious.aecctx"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../escape", b"payload")
        output.writestr("manifest.json", b"{}")

    with pytest.raises(PackageReadError) as captured:
        PackageReader(archive)

    assert captured.value.code == "AECCTX_ARCHIVE_PATH_UNSAFE"


def test_reader_rejects_excessive_decompression_ratio(tmp_path: Path) -> None:
    archive = tmp_path / "compression-bomb.aecctx"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        output.writestr("manifest.json", b"0" * 100_000)

    with pytest.raises(PackageReadError) as captured:
        PackageReader(archive, limits=SafetyLimits(max_decompression_ratio=2))

    assert captured.value.code == "AECCTX_ARCHIVE_RATIO_EXCEEDED"


def test_reader_rejects_member_count_limit(tmp_path: Path) -> None:
    archive = tmp_path / "too-many.aecctx"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("manifest.json", b"{}")
        output.writestr("extra", b"x")

    with pytest.raises(PackageReadError) as captured:
        PackageReader(archive, limits=SafetyLimits(max_members=1))

    assert captured.value.code == "AECCTX_ARCHIVE_MEMBER_LIMIT_EXCEEDED"


def test_public_writer_builds_valid_directory_package(minimal_package: Path, tmp_path: Path) -> None:
    source_manifest = json.loads((minimal_package / "manifest.json").read_text(encoding="utf-8"))
    artifacts = [
        PackageArtifact(
            path=item["path"],
            content=minimal_package / item["path"],
            media_type=item["media_type"],
            role=item["role"],
            authoritative=item["authoritative"],
        )
        for item in source_manifest["artifacts"]
    ]
    output = tmp_path / "written"

    manifest = PackageWriter(output).write(
        package_id=source_manifest["package_id"],
        created_at=source_manifest["created_at"],
        source_ids=source_manifest["source_ids"],
        capabilities=source_manifest["capabilities"],
        loss_summary=source_manifest["loss_summary"],
        embedding_policy=source_manifest["source_embedding_policy"],
        producer=source_manifest["producer"],
        artifacts=artifacts,
    )

    assert manifest["logical_digest"] == source_manifest["logical_digest"]
    assert PackageReader(output).manifest == manifest


def test_public_writer_builds_valid_v02_package(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "v0.2" / "shared" / "minimal-v02"
    source_manifest = json.loads((fixture / "manifest.json").read_text(encoding="utf-8"))
    artifacts = [
        PackageArtifact(
            path=item["path"],
            content=fixture / item["path"],
            media_type=item["media_type"],
            role=item["role"],
            authoritative=item["authoritative"],
        )
        for item in source_manifest["artifacts"]
    ]
    output = tmp_path / "written-v02"

    manifest = PackageWriter(output).write(
        package_id=source_manifest["package_id"],
        created_at=source_manifest["created_at"],
        source_ids=source_manifest["source_ids"],
        capabilities=source_manifest["capabilities"],
        loss_summary=source_manifest["loss_summary"],
        embedding_policy=source_manifest["source_embedding_policy"],
        producer=source_manifest["producer"],
        artifacts=artifacts,
        aecctx_version="0.2.0",
        required_extensions=[],
        extensions=source_manifest["extensions"],
    )

    assert manifest["aecctx_version"] == "0.2.0"
    assert manifest["required_extensions"] == []
    assert PackageReader(output).manifest == manifest
