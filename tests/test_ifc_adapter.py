from __future__ import annotations

import json
from pathlib import Path

import ifcopenshell

from aecctx.adapters.ifc import IFCPlugin, ingest_ifc
from aecctx.package import PackageReader
from aecctx.records import RecordStore
from aecctx.validation import validate_package


FIXTURE = Path(__file__).parents[1] / "fixtures" / "ifc" / "minimal-wall.ifc"
FIXED_TIME = "2026-07-11T00:00:00Z"


def test_public_ifc_fixture_is_parseable_and_exercises_required_evidence() -> None:
    model = ifcopenshell.open(FIXTURE)

    assert model.schema == "IFC4"
    assert len(model.by_type("IfcWall")) == 1
    assert model.by_type("IfcRelContainedInSpatialStructure")
    assert model.by_type("IfcPropertySet")
    assert model.by_type("IfcMaterial")


def test_ifc_plugin_descriptor_and_probe_are_explicit() -> None:
    plugin = IFCPlugin()

    descriptor = plugin.describe()
    probe = plugin.probe(FIXTURE.read_bytes()[:4096])

    assert descriptor["plugin_id"] == "aecctx.adapter.ifc.ifcopenshell"
    assert descriptor["license_identifier"] == "LGPL-3.0-or-later"
    assert descriptor["distribution_posture"] == "optional-not-bundled"
    assert descriptor["network_mode"] == "disabled"
    assert probe["format"] == "ifc-step"
    assert probe["confidence"] == 1.0


def test_ifc_plugin_events_preserve_evidence_before_normalization() -> None:
    events = list(IFCPlugin().extract(FIXTURE, source_id="src_fixture"))

    assert [event["sequence"] for event in events] == list(range(len(events)))
    primitive_positions = {
        event["payload"]["ifc_step_id"]: index
        for index, event in enumerate(events)
        if event["event_type"] == "primitive"
    }
    for index, event in enumerate(events):
        assert event["event_version"] == "0.1"
        assert event["source_id"] == "src_fixture"
        if event["event_type"] in {"entity", "relation"}:
            assert primitive_positions[event["payload"]["ifc_step_id"]] < index


def test_ifc_ingest_preserves_schema_identity_properties_relations_and_geometry(tmp_path: Path) -> None:
    output = tmp_path / "wall-package"

    ingest_ifc(FIXTURE, output, created_at=FIXED_TIME)

    validation = validate_package(output)
    assert validation.valid, validation.diagnostics
    store = RecordStore.open(output)
    source = next(record.raw for record in store.records.values() if record.record_type == "source")
    wall = next(record.raw for record in store.records.values() if record.raw.get("original_class") == "IfcWall")
    assertions = [record.raw for record in store.records.values() if record.record_type == "assertion"]
    relations = [record.raw for record in store.records.values() if record.record_type == "relation"]
    assert source["detected_format"] == {"state": "known", "value": "IFC4"}
    assert wall["source_local_identifiers"]["global_id"]
    assert wall["placement"]["state"] == "known"
    assert wall["representation_refs"]
    assert any(item["predicate"] == "ifc:Pset_WallCommon.IsExternal" and item["value"] == {"state": "known", "value": False} for item in assertions)
    assert any(item["original_class"] == "IfcRelContainedInSpatialStructure" for item in relations)
    assert any(item["relation_type"] == "aecctx:material-assignment" for item in relations)
    assert wall["geometry_refs"]
    mesh_path = wall["geometry_refs"][0]["artifact_path"]
    mesh = json.loads((output / mesh_path).read_text(encoding="utf-8"))
    assert mesh["vertices"]
    assert mesh["triangles"]
    assert mesh["source_record_id"] == wall["record_id"]


def test_ifc_capability_and_loss_report_matches_observed_fixture(tmp_path: Path) -> None:
    output = tmp_path / "wall-package"

    ingest_ifc(FIXTURE, output, created_at=FIXED_TIME)

    manifest = PackageReader(output).manifest
    assert manifest["capabilities"]["identity"] == "full"
    assert manifest["capabilities"]["properties"] == "full"
    assert manifest["capabilities"]["relationships"] == "full"
    assert manifest["capabilities"]["3d_geometry"] == "full"
    assert manifest["capabilities"]["2d_geometry"] == "partial"
    diagnostics = [json.loads(line) for line in PackageReader(output).read_bytes("diagnostics/diagnostics.jsonl").splitlines()]
    assert {item["capability"] for item in diagnostics if item.get("support_level") != "full"} >= {"2d_geometry", "georeferencing"}


def test_repeated_ifc_ingest_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.aecctx"
    second = tmp_path / "second.aecctx"

    ingest_ifc(FIXTURE, first, created_at=FIXED_TIME, package_form="zip")
    ingest_ifc(FIXTURE, second, created_at=FIXED_TIME, package_form="zip")

    assert first.read_bytes() == second.read_bytes()
