from __future__ import annotations

import hashlib
import json
from pathlib import Path

import ifcopenshell
import numpy

from aecctx.adapters.ifc import IFCPlugin, ingest_ifc
from aecctx.package import PackageReader
from aecctx.records import RecordStore
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
IFC4 = ROOT / "fixtures" / "v0.2" / "ifc" / "ifc4-native-2d-georef.ifc"
IFC2X3 = ROOT / "fixtures" / "v0.2" / "ifc" / "ifc2x3-native-2d-local.ifc"
DEGRADED = ROOT / "fixtures" / "v0.2" / "ifc" / "ifc4-degraded-2d-incomplete-georef.ifc"
CONFLICT = ROOT / "fixtures" / "v0.2" / "ifc" / "ifc4-conflicting-units.ifc"
FIXED_TIME = "2026-07-12T00:00:00Z"


def _records(package: Path, record_type: str) -> list[dict[str, object]]:
    store = RecordStore.open(package)
    return [record.raw for record in store.records.values() if record.record_type == record_type]


def test_v02_ifc_fixtures_are_legally_authored_minimal_schema_profiles() -> None:
    assert ifcopenshell.open(IFC4).schema == "IFC4"
    assert ifcopenshell.open(IFC2X3).schema == "IFC2X3"


def test_ifc_plugin_describes_bounded_v02_profiles_separately_from_parsing() -> None:
    descriptor = IFCPlugin().describe()

    assert descriptor["v02_public_profiles"] == {
        "georeferencing": "ifc4-add2tc1-explicit-mapconversion-projectedcrs-v1:partial",
        "native_2d": "ifc2x3-tc1-ifc4-add2tc1-native-2d-v1:partial",
    }
    assert descriptor["implementation_runtime"] == "ifcopenshell/0.8.5"


def test_ifc_v02_corpus_hashes_and_schema_profiles_are_exact() -> None:
    corpus = json.loads((ROOT / "conformance" / "v0.2" / "ifc-corpus.json").read_text(encoding="utf-8"))

    assert corpus["version"] == "0.2.0"
    assert {entry["schema"] for entry in corpus["entries"]} == {"IFC2X3", "IFC4"}
    for entry in corpus["entries"]:
        source = ROOT / entry["path"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == entry["sha256"]
        assert ifcopenshell.open(source).schema == entry["schema"]


def test_ifc4_v02_emits_complete_source_coordinate_chain(tmp_path: Path) -> None:
    output = tmp_path / "ifc4-v02"

    ingest_ifc(IFC4, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    validation = validate_package(output)
    assert validation.valid, validation.diagnostics
    manifest = PackageReader(output).manifest
    source = _records(output, "source")[0]
    qualification = source["coordinate_qualification"]
    assert manifest["aecctx_version"] == "0.2.0"
    assert manifest["capabilities"]["georeferencing"] == "partial"
    assert source["record_version"] == "0.2"
    assert source["evidence_class"] == "observed"
    assert qualification["global_location"] == {"state": "known", "value": "EPSG:32721"}
    assert source["spatial_reference"] == qualification["global_location"]
    assert [link["state"] for link in qualification["transform_chain"]] == ["known", "known"]
    assert qualification["transform_chain"][0]["from_frame"] == "ifc-source-local"
    assert qualification["transform_chain"][0]["to_frame"] == "ifc-project"
    assert qualification["transform_chain"][1]["from_frame"] == "ifc-project"
    assert qualification["transform_chain"][1]["to_frame"] == "ifc-crs:EPSG:32721"
    assert qualification["transform_chain"][1]["matrix"] == [
        0.000866025404,
        -0.0005,
        0.0,
        500000.0,
        0.0005,
        0.000866025404,
        0.0,
        6100000.0,
        0.0,
        0.0,
        0.001,
        12.5,
        0.0,
        0.0,
        0.0,
        1.0,
    ]
    assert len(qualification["transform_chain"][0]["inverse_matrix"]) == 16
    assert len(qualification["transform_chain"][1]["inverse_matrix"]) == 16


def test_ifc4_v02_preserves_native_2d_representations_and_derived_svg(tmp_path: Path) -> None:
    output = tmp_path / "ifc4-v02"

    ingest_ifc(IFC4, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    primitives = _records(output, "primitive")
    representations = [record for record in primitives if "ifc_2d_representation" in record]
    items = [record for record in primitives if "geometry_2d" in record]
    preview = next(record for record in primitives if record.get("original_class") == "AECCTXDerivedIFC2DPreview")
    identifiers = [record["ifc_2d_representation"]["identifier"] for record in representations]
    item_classes = {record["original_class"] for record in items}

    assert sorted(identifiers) == ["Annotation", "Axis", "FootPrint", "FootPrint"]
    assert item_classes >= {"IfcPolyline", "IfcIndexedPolyCurve", "IfcGeometricCurveSet", "IfcMappedItem"}
    indexed = next(record for record in items if record["original_class"] == "IfcIndexedPolyCurve")
    mapped = next(record for record in items if record["original_class"] == "IfcMappedItem")
    assert [4000.0, 200.0] in indexed["geometry_2d"]["coordinates"]
    assert len(mapped["geometry_2d"]["mapping_matrix"]) == 16
    assert mapped["geometry_2d"]["resolved_item_ids"]
    assert mapped["geometry_2d"]["mapping_source_representation_step_id"] == 35
    assert mapped["geometry_2d"]["relationship_path"] == [
        "IfcShapeRepresentation#41",
        "IfcMappedItem#39",
        "IfcRepresentationMap#36",
        "IfcShapeRepresentation#35",
    ]
    for representation in representations:
        for item_record_id in representation["ifc_2d_representation"]["item_record_ids"]:
            item = next(record for record in primitives if record["record_id"] == item_record_id)
            assert representation["record_id"] in item["ifc_2d_parent_representation_ids"]
    assert all(record["representation_fidelity"]["class"] == "source_exact" for record in representations)
    assert preview["evidence_class"] == "derived"
    assert preview["representation_fidelity"]["class"] == "preview"
    svg_ref = preview["artifact_refs"][0]
    svg = (output / svg_ref["artifact_path"]).read_text(encoding="utf-8")
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert all(source_id in svg for source_id in preview["representation_fidelity"]["source_representation_ids"])


def test_ifc_v02_degraded_profiles_remain_explicit_and_package_valid(tmp_path: Path) -> None:
    output = tmp_path / "degraded-v02"

    ingest_ifc(DEGRADED, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    validation = validate_package(output)
    assert validation.valid, validation.diagnostics
    source = _records(output, "source")[0]
    primitives = _records(output, "primitive")
    diagnostics = _records(output, "diagnostic")
    codes = {record["code"] for record in diagnostics}
    representation_states = {
        record["ifc_2d_representation"]["identifier"]: record["ifc_2d_representation"]["profile_state"]
        for record in primitives
        if "ifc_2d_representation" in record
    }
    assert source["coordinate_qualification"]["global_location"]["state"] == "unsupported"
    assert source["spatial_reference"] == source["coordinate_qualification"]["global_location"]
    assert representation_states == {"Axis": "extraction_failed", "Annotation": "unsupported", "FootPrint": "empty"}
    assert {
        "AECCTX_IFC_2D_REPRESENTATION_NOT_DECLARED",
        "AECCTX_IFC_2D_REPRESENTATION_EMPTY",
        "AECCTX_IFC_2D_ITEM_UNSUPPORTED",
        "AECCTX_IFC_2D_EXTRACTION_FAILED",
        "AECCTX_IFC_GEOREFERENCING_INCOMPLETE",
    } <= codes


def test_ifc_v02_conflicting_units_do_not_produce_global_location(tmp_path: Path) -> None:
    output = tmp_path / "conflict-v02"

    ingest_ifc(CONFLICT, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    source = _records(output, "source")[0]
    diagnostics = _records(output, "diagnostic")
    qualification = source["coordinate_qualification"]
    assert qualification["global_location"] == {
        "reason_code": "AECCTX_IFC_COORDINATE_UNITS_CONFLICT",
        "state": "conflicted",
    }
    assert source["spatial_reference"] == qualification["global_location"]
    assert qualification["transform_chain"][-1]["state"] == "conflicted"
    assert any(record["code"] == "AECCTX_IFC_COORDINATE_UNITS_CONFLICT" for record in diagnostics)


def test_ifc4_v02_preserves_crs_operation_and_context_as_source_evidence(tmp_path: Path) -> None:
    output = tmp_path / "ifc4-v02"

    ingest_ifc(IFC4, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    primitives = _records(output, "primitive")
    operation = next(record for record in primitives if record["original_class"] == "IfcMapConversion")
    crs = next(record for record in primitives if record["original_class"] == "IfcProjectedCRS")
    context = next(
        record
        for record in primitives
        if record["original_class"] == "IfcGeometricRepresentationContext"
        and record["source_refs"][0]["locator"] == "ifc-step:#10"
    )
    assert operation["coordinate_operation"] == {
        "operation_class": "IfcMapConversion",
        "parameters": {
            "eastings": 500000.0,
            "northings": 6100000.0,
            "orthogonal_height": 12.5,
            "scale": 0.001,
            "x_axis_abscissa": 0.866025403784,
            "x_axis_ordinate": 0.5,
        },
        "relationship_path": ["IfcGeometricRepresentationContext#10", "IfcMapConversion#13", "IfcProjectedCRS#12"],
        "source_crs_step_id": 10,
        "target_crs_step_id": 12,
    }
    assert crs["coordinate_reference_system"]["name"] == "EPSG:32721"
    assert crs["coordinate_reference_system"]["map_unit"] == "METRE"
    assert crs["coordinate_reference_system"]["vertical_datum"] == {
        "reason_code": "AECCTX_IFC_VERTICAL_CRS_NOT_DECLARED",
        "state": "explicit_null",
    }
    assert context["coordinate_frame"]["world_coordinate_system"]["state"] == "known"
    assert len(context["coordinate_frame"]["world_coordinate_system"]["value"]) == 16


def test_ifc2x3_v02_preserves_native_2d_but_does_not_guess_crs(tmp_path: Path) -> None:
    output = tmp_path / "ifc2x3-v02"

    ingest_ifc(IFC2X3, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    validation = validate_package(output)
    assert validation.valid, validation.diagnostics
    source = _records(output, "source")[0]
    representations = [record for record in _records(output, "primitive") if "ifc_2d_representation" in record]
    qualification = source["coordinate_qualification"]
    assert sorted(record["ifc_2d_representation"]["identifier"] for record in representations) == ["Axis", "FootPrint"]
    assert qualification["global_location"] == {
        "reason_code": "AECCTX_IFC_GEOREFERENCING_NOT_DECLARED",
        "state": "unknown",
    }
    assert [link["state"] for link in qualification["transform_chain"]] == ["known", "unknown"]
    assert "declared_crs" not in qualification


def test_ifc_v02_transform_inverses_round_trip_large_coordinates(tmp_path: Path) -> None:
    output = tmp_path / "ifc4-v02"

    ingest_ifc(IFC4, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    source = _records(output, "source")[0]
    for link in source["coordinate_qualification"]["transform_chain"]:
        forward = numpy.array(link["matrix"]).reshape((4, 4))
        inverse = numpy.array(link["inverse_matrix"]).reshape((4, 4))
        assert numpy.allclose(forward @ inverse, numpy.eye(4), rtol=0.0, atol=1e-6)


def test_ifc_v02_zip_is_deterministic_and_v01_default_is_unchanged(tmp_path: Path) -> None:
    first = tmp_path / "first.aecctx"
    second = tmp_path / "second.aecctx"
    default_v01 = tmp_path / "default-v01.aecctx"
    explicit_v01 = tmp_path / "explicit-v01.aecctx"

    ingest_ifc(IFC4, first, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0")
    ingest_ifc(IFC4, second, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0")
    ingest_ifc(IFC4, default_v01, created_at=FIXED_TIME, package_form="zip")
    ingest_ifc(IFC4, explicit_v01, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.1.0")

    assert first.read_bytes() == second.read_bytes()
    assert default_v01.read_bytes() == explicit_v01.read_bytes()
