from __future__ import annotations

import json
from pathlib import Path

import ezdxf

from aecctx.adapters.dxf import DXFPlugin, ingest_dxf
from aecctx.package import PackageReader
from aecctx.records import RecordStore
from aecctx.validation import validate_package


FIXTURE = Path(__file__).parents[1] / "fixtures" / "dxf" / "minimal-plan.dxf"
FIXED_TIME = "2026-07-11T00:00:00Z"


def test_public_dxf_fixture_exercises_required_structures() -> None:
    document = ezdxf.readfile(FIXTURE)
    model_types = {entity.dxftype() for entity in document.modelspace()}

    assert document.dxfversion == "AC1032"
    assert document.units == ezdxf.units.M
    assert {"LINE", "LWPOLYLINE", "CIRCLE", "TEXT", "MTEXT", "INSERT", "HATCH", "DIMENSION"} <= model_types
    assert "Sheet A" in document.layout_names()
    assert "DOOR_SYMBOL" in document.blocks
    assert document.blocks.get("XREF_SAMPLE").block_record.is_xref


def test_dxf_plugin_descriptor_and_probe_are_explicit() -> None:
    plugin = DXFPlugin()

    descriptor = plugin.describe()
    probe = plugin.probe(FIXTURE.read_bytes()[:64 * 1024])

    assert descriptor["plugin_id"] == "aecctx.adapter.dxf.ezdxf"
    assert descriptor["license_identifier"] == "MIT"
    assert descriptor["distribution_posture"] == "optional-not-bundled"
    assert descriptor["network_mode"] == "disabled"
    assert probe["format"] == "dxf-ascii"
    assert probe["confidence"] == 1.0


def test_dxf_ingest_preserves_layout_layer_block_xref_text_and_geometry(tmp_path: Path) -> None:
    output = tmp_path / "plan-package"

    ingest_dxf(FIXTURE, output, created_at=FIXED_TIME)

    validation = validate_package(output)
    assert validation.valid, validation.diagnostics
    store = RecordStore.open(output)
    source = next(record.raw for record in store.records.values() if record.record_type == "source")
    primitives = [record.raw for record in store.records.values() if record.record_type == "primitive"]
    entities = [record.raw for record in store.records.values() if record.record_type == "entity"]
    relations = [record.raw for record in store.records.values() if record.record_type == "relation"]
    assert source["detected_format"] == {"state": "known", "value": "AC1032"}
    assert source["detected_units"] == {"state": "known", "value": "m"}
    assert {item["original_class"] for item in primitives} >= {"LINE", "LWPOLYLINE", "TEXT", "MTEXT", "DIMENSION", "HATCH", "INSERT"}
    assert any(item["container"]["value"] == "layout:Sheet A" for item in primitives)
    assert any(item.get("block", {}).get("name") == "DOOR_SYMBOL" for item in entities)
    assert any(item.get("block", {}).get("is_xref") is True and item["block"]["xref_path"] == "external-reference.dxf" for item in entities)
    assert any(item["relation_type"] == "aecctx:representation" for item in relations)
    line = next(item for item in primitives if item["original_class"] == "LINE" and item.get("xdata"))
    assert any(tag["code"] == 1000 and tag["value"] == "unmapped-source-tag" for tag in line["raw_tags"])
    assert all("wall" not in item["kind"].lower() for item in entities)


def test_dxf_capability_loss_report_is_structured(tmp_path: Path) -> None:
    output = tmp_path / "plan-package"

    ingest_dxf(FIXTURE, output, created_at=FIXED_TIME)

    manifest = PackageReader(output).manifest
    assert manifest["capabilities"]["identity"] == "full"
    assert manifest["capabilities"]["2d_geometry"] == "full"
    assert manifest["capabilities"]["properties"] == "partial"
    assert manifest["capabilities"]["3d_geometry"] == "partial"
    diagnostics = [json.loads(line) for line in PackageReader(output).read_bytes("diagnostics/diagnostics.jsonl").splitlines()]
    non_full = {item["capability"] for item in diagnostics if item.get("support_level") != "full"}
    assert non_full >= {"properties", "relationships", "3d_geometry", "materials_styles", "georeferencing"}


def test_repeated_dxf_ingest_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.aecctx"
    second = tmp_path / "second.aecctx"

    ingest_dxf(FIXTURE, first, created_at=FIXED_TIME, package_form="zip")
    ingest_dxf(FIXTURE, second, created_at=FIXED_TIME, package_form="zip")

    assert first.read_bytes() == second.read_bytes()

