from __future__ import annotations

import hashlib
import json
from pathlib import Path

import ifcopenshell
import numpy

from aecctx.adapters.ifc import IFCPlugin, _geometry_2d, ingest_ifc
from aecctx.package import PackageReader
from aecctx.records import RecordStore
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "fixtures" / "v0.3" / "ifc"
POSITIVE = FIXTURES / "ifc4x3-curves-annotations-scaled.ifc"
DEGRADED = FIXTURES / "ifc4x3-degraded.ifc"
CONFLICT = FIXTURES / "ifc4x3-conflicted-georef.ifc"
V02 = ROOT / "fixtures" / "v0.2" / "ifc" / "ifc4-native-2d-georef.ifc"
FIXED_TIME = "2026-07-13T00:00:00Z"


def _records(package: Path, record_type: str) -> list[dict[str, object]]:
    store = RecordStore.open(package)
    return [record.raw for record in store.records.values() if record.record_type == record_type]


def _primitive(package: Path, ifc_class: str) -> dict[str, object]:
    return next(record for record in _records(package, "primitive") if record.get("original_class") == ifc_class)


def test_ifc_v03_corpus_hashes_schema_and_generator_are_exact() -> None:
    corpus = json.loads((ROOT / "conformance" / "v0.3" / "ifc-corpus.json").read_text(encoding="utf-8"))

    assert corpus["version"] == "0.3.0"
    assert {entry["schema"] for entry in corpus["entries"]} == {"IFC4X3"}
    assert {entry["id"] for entry in corpus["entries"]} == {
        "ifc4x3-curves-annotations-scaled",
        "ifc4x3-degraded",
        "ifc4x3-conflicted-georef",
    }
    for entry in corpus["entries"]:
        source = ROOT / entry["path"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == entry["sha256"]
        model = ifcopenshell.open(source)
        assert model.schema == entry["schema"]
        assert model.schema_identifier == entry["schema_identifier"] == "IFC4X3_ADD2"


def test_ifc_plugin_describes_bounded_v03_profiles_separately() -> None:
    assert IFCPlugin().describe()["v03_public_profiles"] == {
        "georeferencing": "ifc4x3-add2-mapconversion-scaled-v03:partial",
        "native_2d": "ifc4x3-add2-native-2d-v03:partial",
    }


def test_ifc4x3_v03_preserves_selected_curve_annotation_and_style_evidence(tmp_path: Path) -> None:
    output = tmp_path / "positive"

    ingest_ifc(POSITIVE, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    assert validate_package(output).valid
    expected = {
        "IfcCircle": "circle",
        "IfcEllipse": "ellipse",
        "IfcTrimmedCurve": "trimmed_curve",
        "IfcCompositeCurve": "composite_curve",
        "IfcIndexedPolyCurve": "indexed_polycurve",
        "IfcTextLiteral": "text_literal",
        "IfcAnnotationFillArea": "annotation_fill_area",
    }
    for ifc_class, kind in expected.items():
        source = _primitive(output, ifc_class)["ifc_v03"]["source_2d"]
        assert source["kind"] == kind
        assert source["source_step_id"] > 0
    indexed = _primitive(output, "IfcIndexedPolyCurve")["ifc_v03"]["source_2d"]
    assert [segment["kind"] for segment in indexed["segments"]] == ["line", "arc"]
    assert indexed["segments"][1]["indices"] == [2, 3, 4]
    text = _primitive(output, "IfcTextLiteral")["ifc_v03"]["source_2d"]
    assert text["literal"] == "AECCTX plan note"
    assert text["path"] == "RIGHT"
    assert text["styles"][0]["style_class"] == "IfcTextStyle"
    circle = _primitive(output, "IfcCircle")["ifc_v03"]["source_2d"]
    assert circle["styles"][0]["style_class"] == "IfcCurveStyle"
    fill = _primitive(output, "IfcAnnotationFillArea")["ifc_v03"]["source_2d"]
    assert fill["styles"][0]["style_class"] == "IfcFillAreaStyle"
    assert fill["styles"][0]["hatching"][0]["style_class"] == "IfcFillAreaStyleHatching"


def test_ifc4x3_v03_scaled_map_conversion_is_explicit_and_reversible(tmp_path: Path) -> None:
    output = tmp_path / "positive"

    ingest_ifc(POSITIVE, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    source = _records(output, "source")[0]
    link = source["coordinate_qualification"]["transform_chain"][-1]
    operation = _primitive(output, "IfcMapConversionScaled")["coordinate_operation"]
    assert operation["parameters"]["factors"] == {"x": 2.0, "y": 3.0, "z": 4.0}
    assert link["matrix"] == [
        0.002,
        -0.0,
        0.0,
        500000.0,
        0.0,
        0.003,
        0.0,
        6100000.0,
        0.0,
        0.0,
        0.004,
        12.5,
        0.0,
        0.0,
        0.0,
        1.0,
    ]
    forward = numpy.array(link["matrix"]).reshape((4, 4))
    inverse = numpy.array(link["inverse_matrix"]).reshape((4, 4))
    assert numpy.allclose(forward @ inverse, numpy.eye(4), rtol=0.0, atol=1e-6)


def test_ifc_v03_degraded_states_and_limits_are_explicit(tmp_path: Path) -> None:
    output = tmp_path / "degraded"

    ingest_ifc(DEGRADED, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    diagnostics = _records(output, "diagnostic")
    codes = {record["code"] for record in diagnostics}
    states = {
        record["ifc_2d_representation"]["identifier"]: record["ifc_2d_representation"]["profile_state"]
        for record in _records(output, "primitive")
        if "ifc_2d_representation" in record
    }
    assert states == {"Annotation": "extraction_failed", "FootPrint": "empty"}
    assert {
        "AECCTX_IFC_2D_REPRESENTATION_NOT_DECLARED",
        "AECCTX_IFC_2D_REPRESENTATION_EMPTY",
        "AECCTX_IFC_V03_2D_ITEM_UNSUPPORTED",
        "AECCTX_IFC_V03_2D_EXTRACTION_FAILED",
        "AECCTX_IFC_GEOREFERENCING_INCOMPLETE",
    } <= codes
    assert _primitive(output, "IfcTextLiteral")["ifc_v03"]["source_2d"] == {
        "reason_code": "AECCTX_IFC_V03_TEXT_LIMIT_EXCEEDED",
        "state": "unsupported",
    }


def test_ifc_v03_structural_limits_and_cycles_fail_closed() -> None:
    model = ifcopenshell.file(schema="IFC4X3_ADD2")
    origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
    placement = model.create_entity("IfcAxis2Placement2D", Location=origin)
    circle = model.create_entity("IfcCircle", Position=placement, Radius=1.0)

    points = model.create_entity(
        "IfcCartesianPointList2D",
        CoordList=[(float(index), 0.0) for index in range(4_097)],
    )
    indexed = model.create_entity(
        "IfcIndexedPolyCurve",
        Points=points,
        Segments=[model.create_entity("IfcLineIndex", (1, 2))],
        SelfIntersect=False,
    )
    assert _geometry_2d(indexed, v03=True)[0] == {
        "reason_code": "AECCTX_IFC_V03_2D_EXTRACTION_FAILED",
        "state": "unsupported",
    }

    segments = [
        model.create_entity(
            "IfcCompositeCurveSegment",
            Transition="CONTINUOUS",
            SameSense=True,
            ParentCurve=circle,
        )
        for _ in range(257)
    ]
    composite = model.create_entity("IfcCompositeCurve", Segments=segments, SelfIntersect=False)
    assert _geometry_2d(composite, v03=True)[0]["reason_code"] == "AECCTX_IFC_V03_2D_EXTRACTION_FAILED"

    nested = circle
    for _ in range(34):
        segment = model.create_entity(
            "IfcCompositeCurveSegment",
            Transition="CONTINUOUS",
            SameSense=True,
            ParentCurve=nested,
        )
        nested = model.create_entity("IfcCompositeCurve", Segments=[segment], SelfIntersect=False)
    assert _geometry_2d(nested, v03=True)[0]["reason_code"] == "AECCTX_IFC_V03_2D_EXTRACTION_FAILED"

    members = [model.create_entity("IfcCircle", Position=placement, Radius=float(index + 1)) for index in range(4_097)]
    curve_set = model.create_entity("IfcGeometricCurveSet", Elements=members)
    assert _geometry_2d(curve_set, v03=True)[0]["reason_code"] == "AECCTX_IFC_V03_2D_EXTRACTION_FAILED"


def test_ifc_v03_georeferencing_conflicts_never_guess(tmp_path: Path) -> None:
    output = tmp_path / "conflicted"

    ingest_ifc(CONFLICT, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    source = _records(output, "source")[0]
    qualification = source["coordinate_qualification"]
    assert qualification["global_location"] == {
        "reason_code": "AECCTX_IFC_GEOREFERENCING_CONFLICTED",
        "state": "conflicted",
    }
    assert "declared_crs" not in qualification
    assert qualification["transform_chain"][-1]["state"] == "conflicted"


def test_ifc_v03_preview_is_derived_and_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.aecctx"
    second = tmp_path / "second.aecctx"

    ingest_ifc(POSITIVE, first, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0")
    ingest_ifc(POSITIVE, second, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0")

    assert first.read_bytes() == second.read_bytes()
    package = PackageReader(first)
    preview = next(
        record for record in _records(first, "primitive")
        if record.get("original_class") == "AECCTXDerivedIFC2DPreview"
    )
    svg = package.read_bytes(preview["artifact_refs"][0]["artifact_path"]).decode("utf-8")
    assert preview["evidence_class"] == "derived"
    assert preview["representation_fidelity"]["class"] == "preview"
    assert preview["ifc_v03"]["approximation"] == {
        "authority": "derived-preview-only",
        "segments_per_full_curve": 32,
    }
    assert "AECCTX plan note" not in svg


def test_ifc_v03_default_v01_and_acx13_v02_are_unchanged(tmp_path: Path) -> None:
    default_v01 = tmp_path / "default.aecctx"
    explicit_v01 = tmp_path / "explicit.aecctx"
    v02 = tmp_path / "v02"

    ingest_ifc(POSITIVE, default_v01, created_at=FIXED_TIME, package_form="zip")
    ingest_ifc(POSITIVE, explicit_v01, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.1.0")
    ingest_ifc(V02, v02, created_at=FIXED_TIME, aecctx_version="0.2.0")

    assert default_v01.read_bytes() == explicit_v01.read_bytes()
    descriptor = IFCPlugin().describe()
    assert descriptor["v02_public_profiles"] == {
        "georeferencing": "ifc4-add2tc1-explicit-mapconversion-projectedcrs-v1:partial",
        "native_2d": "ifc2x3-tc1-ifc4-add2tc1-native-2d-v1:partial",
    }
    assert "ifc_v03" not in _primitive(v02, "IfcIndexedPolyCurve")
