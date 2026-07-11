from __future__ import annotations

import json
from pathlib import Path

import trimesh

from aecctx.adapters.geometry import GeometryPlugin, ingest_geometry
from aecctx.geometry import build_preview_descriptor, render_svg_preview, source_to_glb_transform
from aecctx.package import PackageReader
from aecctx.records import RecordStore
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "fixtures" / "geometry" / "minimal-triangle.obj"
FIXED_TIME = "2026-07-11T00:00:00Z"


def test_public_obj_fixture_is_a_real_mesh() -> None:
    scene = trimesh.load(FIXTURE, force="scene", process=False)

    assert len(scene.geometry) == 1
    mesh = next(iter(scene.geometry.values()))
    assert len(mesh.vertices) == 3
    assert len(mesh.faces) == 1


def test_geometry_plugin_probe_and_descriptor_are_explicit() -> None:
    plugin = GeometryPlugin()
    probe = plugin.probe(FIXTURE.read_bytes())
    descriptor = plugin.describe()

    assert probe["format"] == "obj"
    assert probe["confidence"] == 1.0
    assert descriptor["license_identifier"] == "MIT"
    assert descriptor["network_mode"] == "disabled"
    assert all(callable(getattr(plugin, name, None)) for name in ("describe", "probe", "extract", "finalize", "render"))


def test_coordinate_transform_is_reversible_and_explicit() -> None:
    transform = source_to_glb_transform()

    assert transform["source_to_glb"] == [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, -1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    assert transform["glb_to_source"] == [[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, -1.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def test_svg_preview_is_deterministic_and_metadata_free() -> None:
    vertices = [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0], [0.0, 3.0, 0.0]]
    faces = [[0, 1, 2]]

    first = render_svg_preview(vertices, faces, view="top")
    second = render_svg_preview(vertices, faces, view="top")

    assert first == second
    assert b'<svg xmlns="http://www.w3.org/2000/svg"' in first
    assert b"viewBox=" in first
    assert b"timestamp" not in first.lower()


def test_preview_descriptor_supports_scene_level_and_sheet_scopes() -> None:
    descriptor = build_preview_descriptor(
        scope_kind="sheet",
        scope_id="Sheet A",
        view="plan",
        artifact_path="previews/sheet-a.svg",
        source_record_ids=["entity_sheet_a"],
    )

    assert descriptor == {
        "artifact_path": "previews/sheet-a.svg",
        "scope": {"id": "Sheet A", "kind": "sheet"},
        "source_record_ids": ["entity_sheet_a"],
        "status": "derived-preview",
        "view": "plan",
    }


def test_geometry_ingest_emits_valid_glb_svg_bounds_and_provenance(tmp_path: Path) -> None:
    output = tmp_path / "geometry-package"

    ingest_geometry(FIXTURE, output, created_at=FIXED_TIME)

    assert validate_package(output).valid
    reader = PackageReader(output)
    store = RecordStore.open(output)
    entity = next(record.raw for record in store.records.values() if record.record_type == "entity")
    refs = {item["media_type"]: item for item in entity["geometry_refs"]}
    assert "model/gltf-binary" in refs
    assert "image/svg+xml" in refs
    assert refs["model/gltf-binary"]["units"] == {"state": "unknown", "reason_code": "AECCTX_MESH_UNITS_NOT_DECLARED"}
    assert refs["model/gltf-binary"]["source_to_artifact_transform"] == source_to_glb_transform()["source_to_glb"]
    assert entity["bounds"] == {"max": [4.0, 3.0, 0.0], "min": [0.0, 0.0, 0.0]}
    glb = reader.read_bytes(refs["model/gltf-binary"]["artifact_path"])
    svg = reader.read_bytes(refs["image/svg+xml"]["artifact_path"])
    assert glb[:4] == b"glTF"
    assert svg.startswith(b"<svg")
    loaded = trimesh.load(Path(output) / refs["model/gltf-binary"]["artifact_path"], force="scene", process=False)
    assert loaded.geometry
    diagnostics = [json.loads(line) for line in reader.read_bytes("diagnostics/diagnostics.jsonl").splitlines()]
    rendered = next(item for item in diagnostics if item["code"] == "AECCTX_PREVIEW_RENDERED")
    assert rendered["artifact_paths"] == ["previews/scene-front.svg", "previews/scene-top.svg"]


def test_geometry_capability_report_and_output_are_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.aecctx"
    second = tmp_path / "second.aecctx"

    ingest_geometry(FIXTURE, first, created_at=FIXED_TIME, package_form="zip")
    ingest_geometry(FIXTURE, second, created_at=FIXED_TIME, package_form="zip")

    assert first.read_bytes() == second.read_bytes()
    manifest = PackageReader(first).manifest
    assert manifest["capabilities"]["3d_geometry"] == "full"
    assert manifest["capabilities"]["2d_geometry"] == "partial"
    assert "AECCTX_MESH_UNITS_NOT_DECLARED" in manifest["loss_summary"]
