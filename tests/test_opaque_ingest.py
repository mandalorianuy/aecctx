from __future__ import annotations

import json
from pathlib import Path

from aecctx.ingest import ingest_opaque
from aecctx.package import PackageReader
from aecctx.validation import validate_package


FIXED_TIME = "2026-07-11T00:00:00Z"
PUBLIC_OPAQUE_FIXTURE = Path(__file__).parents[1] / "fixtures" / "sources" / "opaque-sample.bin"
CAPABILITY_KEYS = {
    "identity",
    "hierarchy",
    "properties",
    "relationships",
    "text",
    "2d_geometry",
    "3d_geometry",
    "materials_styles",
    "georeferencing",
    "validation",
}


def test_public_opaque_fixture_has_stable_identity() -> None:
    from aecctx.package import hash_file

    digest, byte_size = hash_file(PUBLIC_OPAQUE_FIXTURE)

    assert digest == "57a002b24a829c4859749bb2661ec282123b172f424c3b2c8a0507c4b35a1594"
    assert byte_size == 35


def test_opaque_ingest_registers_source_without_interpretation(tmp_path: Path) -> None:
    source = tmp_path / "unknown.bin"
    source.write_bytes(b"opaque source bytes\x00\xff")
    package = tmp_path / "opaque-package"

    result = ingest_opaque(source, package, created_at=FIXED_TIME)

    assert result.package_id.startswith("pkg_")
    validation = validate_package(package)
    assert validation.valid, validation.diagnostics
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source_embedding_policy"] == "external"
    assert set(manifest["capabilities"]) == CAPABILITY_KEYS
    assert manifest["capabilities"]["identity"] == "full"
    assert manifest["capabilities"]["properties"] == "opaque"
    assert len(manifest["loss_summary"]) == 8
    assert not (package / "sources" / "content").exists()
    assert (package / "model" / "entities.jsonl").read_text(encoding="utf-8") == ""
    diagnostics = [json.loads(line) for line in (package / "diagnostics" / "diagnostics.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {item["capability"] for item in diagnostics} == CAPABILITY_KEYS - {"identity", "validation"}


def test_opaque_ingest_embeds_only_with_explicit_policy(tmp_path: Path) -> None:
    source = tmp_path / "source.dat"
    source.write_bytes(b"licensed-for-fixture")
    package = tmp_path / "embedded-package"

    ingest_opaque(source, package, created_at=FIXED_TIME, embedding_policy="embedded")

    embedded = package / "sources" / "content" / "source.dat"
    assert embedded.read_bytes() == source.read_bytes()
    source_record = json.loads((package / "sources" / "sources.jsonl").read_text(encoding="utf-8"))
    assert source_record["embedding_policy"] == "embedded"
    assert source_record["storage_ref"] == "sources/content/source.dat"


def test_repeated_zip_ingest_is_byte_reproducible(tmp_path: Path) -> None:
    source = tmp_path / "drawing.unknown"
    source.write_bytes(b"same bytes")
    first = tmp_path / "first.aecctx"
    second = tmp_path / "second.aecctx"

    ingest_opaque(source, first, created_at=FIXED_TIME, package_form="zip")
    ingest_opaque(source, second, created_at=FIXED_TIME, package_form="zip")

    assert first.read_bytes() == second.read_bytes()
    assert PackageReader(first).manifest["logical_digest"] == PackageReader(second).manifest["logical_digest"]


def test_directory_and_zip_have_same_logical_digest(tmp_path: Path) -> None:
    source = tmp_path / "drawing.unknown"
    source.write_bytes(b"same bytes")
    directory = tmp_path / "package-dir"
    archive = tmp_path / "package.aecctx"

    ingest_opaque(source, directory, created_at=FIXED_TIME)
    ingest_opaque(source, archive, created_at=FIXED_TIME, package_form="zip")

    assert PackageReader(directory).manifest["logical_digest"] == PackageReader(archive).manifest["logical_digest"]
