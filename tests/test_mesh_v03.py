from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from aecctx.adapters.geometry import ingest_geometry
from aecctx.cli import main
from aecctx.crs import (
    CRSProfileError,
    apply_datum_operation,
    build_runtime_registry_document,
    load_crs_registry,
    validate_crs_identifier,
)
from aecctx.package import PackageReader
from aecctx.records import RecordStore
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "fixtures" / "v0.3" / "mesh"
REGISTRY = FIXTURES / "crs-registry.json"
NAD83_OBJ = FIXTURES / "nad83-triangle.obj"
FIXED_TIME = "2026-07-14T00:00:00Z"


def records(path: Path) -> list[dict[str, object]]:
    return [record.raw for record in RecordStore.open(path).records.values()]


def test_runtime_registry_is_exact_offline_and_normalized() -> None:
    document = build_runtime_registry_document(author={"id": "aecctx-conformance", "type": "project"})
    registry = load_crs_registry(document)

    assert registry.profile_id == "pyproj-epsg-v11.022-offline-v1"
    assert registry.runtime == {
        "database_layout": "1.4",
        "epsg_date": "2024-11-05",
        "epsg_version": "v11.022",
        "library": "pyproj",
        "library_version": "3.7.2",
        "proj_data_version": "1.20",
        "proj_version": "9.5.1",
    }
    assert len(registry.records) == 8
    assert registry.database_sha256.startswith("sha256:")
    assert len(registry.registry_digest) == 64


def test_registry_preserves_valid_deprecated_vertical_compound_unknown_and_conflict() -> None:
    document = build_runtime_registry_document(author={"id": "aecctx-conformance", "type": "project"})
    registry = load_crs_registry(document)

    assert validate_crs_identifier(registry, "EPSG:4326").crs_type == "geographic_2d"
    assert validate_crs_identifier(registry, "EPSG:5703").crs_type == "vertical"
    assert validate_crs_identifier(registry, "EPSG:6349").crs_type == "compound"
    deprecated = validate_crs_identifier(registry, "EPSG:4328")
    assert deprecated.deprecated is True
    with pytest.raises(CRSProfileError, match="deprecated") as deprecated_error:
        validate_crs_identifier(registry, "EPSG:4328", require_current=True)
    assert deprecated_error.value.code == "AECCTX_CRS_IDENTIFIER_DEPRECATED"
    with pytest.raises(CRSProfileError, match="unknown") as unknown_error:
        validate_crs_identifier(registry, "EPSG:999999")
    assert unknown_error.value.code == "AECCTX_CRS_IDENTIFIER_UNKNOWN"

    conflicted = json.loads(json.dumps(document))
    duplicate = dict(conflicted["records"][0])
    duplicate["name"] = "conflicting name"
    conflicted["records"].append(duplicate)
    with pytest.raises(CRSProfileError, match="conflicting") as conflict_error:
        load_crs_registry(conflicted)
    assert conflict_error.value.code == "AECCTX_CRS_REGISTRY_CONFLICT"


def test_epsg_1252_transform_is_reversible_and_rejects_grids_limits_and_invalid_points() -> None:
    registry = load_crs_registry(build_runtime_registry_document(author={"id": "aecctx-conformance", "type": "project"}))
    operation = registry.operations["EPSG:1252"]
    source = ((40.0, -75.0, 12.0), (40.0001, -75.0001, 15.0), (40.0002, -75.0, 9.0))

    solution = apply_datum_operation(source, operation)

    assert solution.status == "known"
    assert solution.operation_id == "EPSG:1252"
    assert solution.source_crs == "EPSG:4269"
    assert solution.target_crs == "EPSG:4326"
    assert solution.stated_accuracy == 4.0
    assert solution.transformed_points != source
    assert solution.max_horizontal_residual <= 1e-9
    assert solution.max_vertical_residual <= 1e-6

    with pytest.raises(CRSProfileError) as grid_error:
        apply_datum_operation(source, replace(operation, required_grids=("ca_nrc_ntv2_0.tif",)))
    assert grid_error.value.code == "AECCTX_CRS_GRID_OPERATION_UNSUPPORTED"
    with pytest.raises(CRSProfileError) as invalid_error:
        apply_datum_operation(((91.0, -75.0, 0.0),), operation)
    assert invalid_error.value.code == "AECCTX_CRS_POINT_INVALID"
    with pytest.raises(CRSProfileError) as limit_error:
        apply_datum_operation(source, replace(operation, maximum_points=2))
    assert limit_error.value.code == "AECCTX_CRS_POINT_LIMIT_EXCEEDED"


def test_geometry_adapter_preserves_source_and_emits_separate_manual_derived_evidence(tmp_path: Path) -> None:
    output = tmp_path / "mesh"
    profile = json.loads(REGISTRY.read_text(encoding="utf-8"))

    ingest_geometry(
        NAD83_OBJ,
        output,
        created_at=FIXED_TIME,
        aecctx_version="0.2.0",
        crs_profile=profile,
    )

    assert validate_package(output).valid
    package_records = records(output)
    source = next(item for item in package_records if item["record_type"] == "source")
    observed = next(item for item in package_records if item["record_type"] == "primitive" and item.get("original_class") == "OBJ_MESH")
    assertion = next(item for item in package_records if item.get("predicate") == "aecctx:mesh-datum-operation")
    derived = next(item for item in package_records if item.get("original_class") == "DATUM_TRANSFORMED_MESH")
    assert source["spatial_reference"] == {"reason_code": "AECCTX_MESH_CRS_NOT_DECLARED", "state": "unknown"}
    assert source["coordinate_qualification"]["detected_units"]["reason_code"] == "AECCTX_MESH_UNIT_GUESSING_PROHIBITED"
    assert observed["vertices"] == [[40.0, -75.0, 12.0], [40.0001, -75.0001, 15.0], [40.0002, -75.0, 9.0]]
    assert assertion["evidence_class"] == "manual"
    assert derived["evidence_class"] == "derived"
    assert derived["vertices"] != observed["vertices"]
    assert derived["faces"] == observed["faces"]
    extension = derived["extensions"]["aecctx.mesh_crs.v1"]
    assert extension["operation_id"] == "EPSG:1252"
    assert extension["survey_authority"] == {"reason_code": "AECCTX_MESH_SURVEY_AUTHORITY_NOT_ESTABLISHED", "state": "unknown"}
    assert PackageReader(output).manifest["capabilities"]["georeferencing"] == "partial"


def test_cli_validates_registry_and_ingests_explicit_mesh_crs_profile(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["crs-validate", str(REGISTRY), "EPSG:4326", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["identifier"] == "EPSG:4326"

    output = tmp_path / "cli-mesh"
    assert main([
        "ingest",
        str(NAD83_OBJ),
        "--output",
        str(output),
        "--adapter",
        "geometry",
        "--aecctx-version",
        "0.2.0",
        "--mesh-crs-profile",
        str(REGISTRY),
        "--created-at",
        FIXED_TIME,
        "--json",
    ]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    assert validate_package(output).valid


def test_crs_profile_is_mutually_exclusive_with_existing_manual_coordinate_profile(tmp_path: Path) -> None:
    profile = json.loads(REGISTRY.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="mutually exclusive"):
        ingest_geometry(
            NAD83_OBJ,
            tmp_path / "invalid",
            aecctx_version="0.2.0",
            coordinate_profile={"mode": "scale"},
            crs_profile=profile,
        )


def test_mesh_crs_ingest_is_deterministic_and_never_enables_network(tmp_path: Path) -> None:
    profile = json.loads(REGISTRY.read_text(encoding="utf-8"))
    first = tmp_path / "first"
    second = tmp_path / "second"
    ingest_geometry(NAD83_OBJ, first, created_at=FIXED_TIME, aecctx_version="0.2.0", crs_profile=profile)
    ingest_geometry(NAD83_OBJ, second, created_at=FIXED_TIME, aecctx_version="0.2.0", crs_profile=profile)

    assert PackageReader(first).manifest["logical_digest"] == PackageReader(second).manifest["logical_digest"]
    assert (first / "geometry/datum-transformed-mesh.json").read_bytes() == (second / "geometry/datum-transformed-mesh.json").read_bytes()
    import pyproj

    assert pyproj.network.is_network_enabled() is False


def test_core_import_and_help_do_not_require_pyproj() -> None:
    script = """
import builtins, sys
real_import = builtins.__import__
def blocked(name, *args, **kwargs):
    if name == 'pyproj' or name.startswith('pyproj.'):
        raise ImportError('blocked optional dependency')
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocked
import aecctx
from aecctx.cli import build_parser
assert build_parser().prog == 'aecctx'
assert 'pyproj' not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_crs_registry_and_operation_do_not_require_geometry_numpy() -> None:
    script = """
import builtins, json
real_import = builtins.__import__
def blocked(name, *args, **kwargs):
    if name == 'numpy' or name.startswith('numpy.'):
        raise ImportError('blocked geometry dependency')
    return real_import(name, *args, **kwargs)
builtins.__import__ = blocked
from aecctx.crs import apply_datum_operation, load_crs_registry
document = json.loads(open('fixtures/v0.3/mesh/crs-registry.json', encoding='utf-8').read())
registry = load_crs_registry(document)
solution = apply_datum_operation(((40.0, -75.0, 12.0),), registry.operations['EPSG:1252'])
assert solution.status == 'known'
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
