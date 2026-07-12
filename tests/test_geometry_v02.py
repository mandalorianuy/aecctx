from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aecctx.adapters.geometry import ingest_geometry
from aecctx.package import PackageReader
from aecctx.records import RecordStore
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "fixtures" / "v0.2" / "mesh"
OBJ = FIXTURES / "triangle-unknown.obj"
STL = FIXTURES / "triangle-unknown.stl"
GLTF = FIXTURES / "triangle-meters.gltf"
GLB = FIXTURES / "triangle-meters.glb"
FIXED_TIME = "2026-07-12T00:00:00Z"
FRAME = {"axes": ["+X", "+Y", "+Z"], "handedness": "right"}


def profile(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / "profiles" / name).read_text(encoding="utf-8"))


def records(path: Path) -> list[dict[str, object]]:
    return [record.raw for record in RecordStore.open(path).records.values()]


def test_mesh_conformance_corpus_hashes_are_bound_to_publishable_fixtures() -> None:
    corpus = json.loads((ROOT / "conformance" / "v0.2" / "mesh-corpus.json").read_text(encoding="utf-8"))
    assert corpus["version"] == "0.2.0"
    assert len(corpus["entries"]) == 7
    for entry in corpus["entries"]:
        source = ROOT / entry["input"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == entry["input_sha256"]
        if "profile" in entry:
            coordinate_profile = ROOT / entry["profile"]
            assert hashlib.sha256(coordinate_profile.read_bytes()).hexdigest() == entry["profile_sha256"]


def test_geometry_v01_default_remains_byte_identical_to_explicit_v01(tmp_path: Path) -> None:
    default = tmp_path / "default.aecctx"
    explicit = tmp_path / "explicit.aecctx"
    ingest_geometry(OBJ, default, created_at=FIXED_TIME, package_form="zip")
    ingest_geometry(OBJ, explicit, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.1.0")
    assert default.read_bytes() == explicit.read_bytes()


@pytest.mark.parametrize("source", [OBJ, STL])
def test_obj_and_stl_v02_keep_units_frame_and_crs_unknown(tmp_path: Path, source: Path) -> None:
    output = tmp_path / source.suffix.removeprefix(".")
    ingest_geometry(source, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    assert validate_package(output).valid
    source_record = next(item for item in records(output) if item["record_type"] == "source")
    qualification = source_record["coordinate_qualification"]
    assert qualification["declared_units"] == {"authority": "source_declared", "reason_code": "AECCTX_MESH_UNITS_NOT_DECLARED", "state": "unknown"}
    assert qualification["axis_order"] == {"authority": "source_declared", "reason_code": "AECCTX_MESH_FRAME_NOT_DECLARED", "state": "unknown"}
    assert qualification["global_location"] == {"reason_code": "AECCTX_MESH_CRS_NOT_DECLARED", "state": "unknown"}
    assert source_record["declared_units"]["state"] == "unknown"
    assert all(item["record_version"] == "0.2" and "evidence_class" in item for item in records(output))


@pytest.mark.parametrize("source", [GLTF, GLB])
def test_gltf_v02_preserves_normative_meters_frame_and_scene_transform(tmp_path: Path, source: Path) -> None:
    output = tmp_path / source.suffix.removeprefix(".")
    ingest_geometry(source, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    assert validate_package(output).valid
    package_records = records(output)
    source_record = next(item for item in package_records if item["record_type"] == "source")
    qualification = source_record["coordinate_qualification"]
    assert qualification["declared_units"] == {"authority": "source_declared", "state": "known", "value": "m"}
    assert qualification["axis_order"] == {"authority": "source_declared", "state": "known", "value": ["+X", "+Y", "+Z"]}
    assert qualification["handedness"] == {"authority": "source_declared", "state": "known", "value": "right"}
    transform = next(item for item in package_records if item.get("original_class") == "MESH_SCENE_TRANSFORM")
    assert transform["matrix"] == [1.0, 0.0, 0.0, 100.0, 0.0, 1.0, 0.0, 200.0, 0.0, 0.0, 1.0, 300.0, 0.0, 0.0, 0.0, 1.0]
    assert transform["source_refs"][0]["locator"] == "scene-graph-edge:0"


def test_external_gltf_resource_is_rejected_before_resolution(tmp_path: Path) -> None:
    unsafe = FIXTURES / "unsafe-external.gltf"
    with pytest.raises(ValueError) as captured:
        ingest_geometry(unsafe, tmp_path / "unsafe", aecctx_version="0.2.0")
    assert getattr(captured.value, "code", None) == "AECCTX_MESH_EXTERNAL_RESOURCE_UNSUPPORTED"


def test_scale_registration_emits_manual_and_derived_evidence_without_changing_source_mesh(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    calibrated = tmp_path / "calibrated"
    ingest_geometry(OBJ, baseline, created_at=FIXED_TIME, aecctx_version="0.2.0")
    ingest_geometry(OBJ, calibrated, created_at=FIXED_TIME, aecctx_version="0.2.0", coordinate_profile=profile("scale-mm-to-m.json"))

    assert validate_package(calibrated).valid
    baseline_mesh = next(item for item in records(baseline) if item.get("original_class") == "OBJ_MESH" and item["record_type"] == "primitive")
    calibrated_records = records(calibrated)
    source_mesh = next(item for item in calibrated_records if item.get("original_class") == "OBJ_MESH" and item["record_type"] == "primitive")
    assert source_mesh["vertices"] == baseline_mesh["vertices"]
    assert source_mesh["faces"] == baseline_mesh["faces"]
    assertion = next(item for item in calibrated_records if item.get("predicate") == "aecctx:mesh-coordinate-registration")
    assert assertion["evidence_class"] == "manual"
    assert assertion["value"]["state"] == "known"
    assert assertion["value"]["value"]["transform_class"] == "uniform-scale"
    derived = next(item for item in calibrated_records if item.get("original_class") == "CALIBRATED_MESH")
    assert derived["evidence_class"] == "derived"
    assert derived["target_units"] == "m"
    assert derived["bounds"] == {"max": [0.004, 0.003, 0.0], "min": [0.0, 0.0, 0.0]}
    assert PackageReader(calibrated).read_bytes("geometry/calibrated-scene.glb")[:4] == b"glTF"


def test_matrix_crs_and_control_point_profiles_emit_reversible_deterministic_results(tmp_path: Path) -> None:
    matrix_output = tmp_path / "matrix"
    control_a = tmp_path / "control-a.aecctx"
    control_b = tmp_path / "control-b.aecctx"
    ingest_geometry(GLTF, matrix_output, created_at=FIXED_TIME, aecctx_version="0.2.0", coordinate_profile=profile("matrix-local-to-crs.json"))
    ingest_geometry(OBJ, control_a, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0", coordinate_profile=profile("control-points.json"))
    ingest_geometry(OBJ, control_b, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0", coordinate_profile=profile("control-points.json"))

    matrix_derived = next(item for item in records(matrix_output) if item.get("original_class") == "CALIBRATED_MESH")
    assert matrix_derived["coordinate_qualification"]["global_location"]["state"] == "known"
    assert matrix_derived["coordinate_qualification"]["manual_crs"]["value"] == {"horizontal": "EPSG:32721", "vertical": "local-height"}
    assert matrix_derived["transform"]["inverse_matrix"][3] == -500000.0
    control_assertion = next(item for item in records(control_a) if item.get("predicate") == "aecctx:mesh-coordinate-registration")
    assert control_assertion["value"]["value"]["transform_class"] == "similarity-control-points"
    assert control_assertion["value"]["value"]["max_residual"] <= 1e-12
    assert control_a.read_bytes() == control_b.read_bytes()


def test_source_manual_conflict_remains_explicit_and_emits_no_calibrated_artifact(tmp_path: Path) -> None:
    output = tmp_path / "conflicted"
    ingest_geometry(GLTF, output, created_at=FIXED_TIME, aecctx_version="0.2.0", coordinate_profile=profile("conflict-gltf-mm.json"))

    assert validate_package(output).valid
    assertion = next(item for item in records(output) if item.get("predicate") == "aecctx:mesh-coordinate-registration")
    assert assertion["value"]["state"] == "conflicted"
    assert assertion["value"]["reason_code"] == "AECCTX_MESH_SOURCE_MANUAL_CONFLICT"
    assert "geometry/calibrated-scene.glb" not in {item["path"] for item in PackageReader(output).manifest["artifacts"]}
    assert any(item.get("code") == "AECCTX_MESH_SOURCE_MANUAL_UNITS_CONFLICT" for item in records(output))
