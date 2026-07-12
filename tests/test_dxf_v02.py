from __future__ import annotations

import json
from pathlib import Path

import ezdxf
import pytest

from aecctx.adapters.dxf import DXFPlugin, ingest_dxf
from aecctx.package import PackageReader
from aecctx.records import RecordStore
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
ASCII = ROOT / "fixtures" / "v0.2" / "dxf" / "r2018-semantics-3d-ascii.dxf"
BINARY = ROOT / "fixtures" / "v0.2" / "dxf" / "r2018-semantics-3d-binary.dxf"
CYCLE = ROOT / "fixtures" / "v0.2" / "dxf" / "r2000-cyclic-inserts.dxf"
MALFORMED = ROOT / "fixtures" / "v0.2" / "dxf" / "malformed-tags.dxf"
FIXED_TIME = "2026-07-12T00:00:00Z"


def _records(package: Path, record_type: str) -> list[dict[str, object]]:
    store = RecordStore.open(package)
    return [record.raw for record in store.records.values() if record.record_type == record_type]


def test_dxf_v02_corpus_hashes_formats_and_publication_origin_are_exact() -> None:
    corpus = json.loads((ROOT / "conformance" / "v0.2" / "dxf-corpus.json").read_text(encoding="utf-8"))

    assert corpus["version"] == "0.2.0"
    assert corpus["origin"] == "project-authored Apache-2.0 fixture corpus"
    for entry in corpus["entries"]:
        source = ROOT / entry["path"]
        assert source.is_file()
        assert __import__("hashlib").sha256(source.read_bytes()).hexdigest() == entry["sha256"]
    assert {entry["container"] for entry in corpus["entries"]} >= {"ascii", "binary", "malformed"}


def test_dxf_v02_profile_is_explicit_and_v01_default_is_unchanged(tmp_path: Path) -> None:
    descriptor = DXFPlugin().describe()
    default_v01 = tmp_path / "default-v01.aecctx"
    explicit_v01 = tmp_path / "explicit-v01.aecctx"
    v02 = tmp_path / "v02"

    ingest_dxf(ASCII, default_v01, created_at=FIXED_TIME, package_form="zip")
    ingest_dxf(ASCII, explicit_v01, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.1.0")
    ingest_dxf(ASCII, v02, created_at=FIXED_TIME, aecctx_version="0.2.0")

    assert descriptor["implementation_runtime"] == "ezdxf/1.4.4"
    assert descriptor["v02_public_profiles"] == {
        "bounded_3d": "dxf-r2000-r2018-bounded-3d-v1:partial",
        "source_semantics": "dxf-r2000-r2018-source-semantics-v1:partial",
    }
    assert default_v01.read_bytes() == explicit_v01.read_bytes()
    assert PackageReader(v02).manifest["aecctx_version"] == "0.2.0"
    assert validate_package(v02).valid
    assert {record["record_version"] for kind in ("source", "primitive", "entity", "relation", "assertion", "diagnostic") for record in _records(v02, kind)} == {"0.2"}


def test_dxf_v02_preserves_source_native_semantic_evidence(tmp_path: Path) -> None:
    output = tmp_path / "semantics"

    ingest_dxf(ASCII, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    primitives = _records(output, "primitive")
    classes = {record["original_class"] for record in primitives}
    assert {"DICTIONARY", "XRECORD", "GROUP", "MATERIAL", "APPID", "ATTRIB", "ATTDEF", "INSERT"} <= classes
    line = next(record for record in primitives if record["original_class"] == "LINE" and record.get("xdata"))
    assert line["owner_handle"]["state"] == "known"
    assert line["material_handle"]["state"] == "known"
    assert line["xdata"]["AECCTX_TEST"] == [
        {"code": 1000, "value": "source-semantic-tag"},
        {"code": 1070, "value": 14},
    ]
    assert line["extension_dictionary"]["state"] == "known"
    assert "AECCTX_METADATA" in line["extension_dictionary"]["value"]["entries"]
    xrecord = next(record for record in primitives if record["original_class"] == "XRECORD" and record.get("xrecord_tags"))
    assert {tag["code"] for tag in xrecord["xrecord_tags"]} >= {1, 40, 310}
    group = next(record for record in primitives if record["original_class"] == "GROUP")
    assert group["group"]["name"] == "AECCTX_GROUP"
    assert len(group["group"]["member_handles"]) == 3
    material = next(record for record in primitives if record["original_class"] == "MATERIAL" and record.get("material", {}).get("name") == "AECCTX_TEST_MATERIAL")
    assert material["material"]["handle"] == line["material_handle"]["value"]
    attrib = next(record for record in primitives if record["original_class"] == "ATTRIB")
    assert attrib["attribute"]["tag"] == "ROLE"
    assert attrib["attribute"]["text"] == "source-attribute"
    assert all(record["raw_tags"] for record in primitives if record["evidence_class"] == "observed")

    entities = _records(output, "entity")
    forbidden = {"wall", "beam", "panel", "stud", "joist", "rafter"}
    assert not any(term in record["kind"].lower() for record in entities for term in forbidden)


def test_dxf_v02_preserves_bounded_3d_ocs_insert_transforms_and_topology(tmp_path: Path) -> None:
    output = tmp_path / "bounded-3d"

    ingest_dxf(ASCII, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    primitives = _records(output, "primitive")
    by_class: dict[str, list[dict[str, object]]] = {}
    for record in primitives:
        by_class.setdefault(str(record["original_class"]), []).append(record)
    assert {"POINT", "LINE", "3DFACE", "POLYLINE", "MESH", "CIRCLE", "INSERT"} <= {
        name for name, records in by_class.items() if any("geometry_3d" in record for record in records)
    }
    circle = next(record for record in by_class["CIRCLE"] if "geometry_3d" in record)
    assert circle["geometry_3d"]["coordinate_space"] == "ocs"
    assert circle["geometry_3d"]["extrusion"] == [0.0, 1.0, 1.0]
    assert circle["geometry_3d"]["center_ocs"] != circle["geometry_3d"]["center_wcs"]
    assert len(circle["geometry_3d"]["ocs_to_wcs_matrix"]) == 16

    mesh = next(record for record in by_class["MESH"] if "geometry_3d" in record)
    assert len(mesh["geometry_3d"]["vertices"]) == 4
    assert mesh["geometry_3d"]["faces"] == [[0, 1, 2, 3]]
    polyline_modes = {record["geometry_3d"]["mode"] for record in by_class["POLYLINE"] if "geometry_3d" in record}
    assert {"3d-polyline", "polygon-mesh", "polyface-mesh"} <= polyline_modes

    insert = next(record for record in by_class["INSERT"] if record.get("geometry_3d", {}).get("block_name") == "AECCTX_PARENT")
    assert len(insert["geometry_3d"]["insert_matrix"]) == 16
    assert insert["geometry_3d"]["nested_instances"] == [
        {
            "block_path": ["AECCTX_PARENT", "AECCTX_LEAF"],
            "entity_class": "3DFACE",
            "entity_handle": next(record["handle"] for record in by_class["3DFACE"] if record["container"]["value"] == "block:AECCTX_LEAF"),
            "transform_state": "known",
        }
    ]

    derived = next(record for record in primitives if record["original_class"] == "AECCTXDerivedDXFTessellation")
    assert derived["evidence_class"] == "derived"
    assert derived["representation_fidelity"] == {
        "class": "tessellated",
        "derived": True,
        "source_representation_ids": sorted(derived["representation_fidelity"]["source_representation_ids"]),
    }
    refs = {ref["media_type"]: ref for ref in derived["artifact_refs"]}
    assert {"application/vnd.aecctx.dxf-mesh+json", "model/gltf-binary"} <= refs.keys()
    for ref in refs.values():
        assert len(PackageReader(output).read_bytes(ref["artifact_path"])) > 0
    manifest = PackageReader(output).manifest
    assert manifest["capabilities"]["3d_geometry"] == "partial"
    assert "AECCTX_DXF_3D_PROFILE_PARTIAL" in manifest["loss_summary"]


def test_dxf_v02_binary_and_ascii_ingest_are_profile_equivalent_and_deterministic(tmp_path: Path) -> None:
    ascii_first = tmp_path / "ascii-first.aecctx"
    ascii_second = tmp_path / "ascii-second.aecctx"
    binary_output = tmp_path / "binary"

    ingest_dxf(ASCII, ascii_first, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0")
    ingest_dxf(ASCII, ascii_second, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0")
    ingest_dxf(BINARY, binary_output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    assert DXFPlugin().probe(BINARY.read_bytes()[:64 * 1024])["format"] == "dxf-binary"
    assert ascii_first.read_bytes() == ascii_second.read_bytes()
    assert validate_package(binary_output).valid
    assert _records(binary_output, "source")[0]["dxf_container"] == "binary"
    binary_classes = {record["original_class"] for record in _records(binary_output, "primitive")}
    assert {"DICTIONARY", "XRECORD", "GROUP", "MATERIAL", "MESH", "3DFACE"} <= binary_classes


def test_dxf_v02_keeps_acis_xref_and_cyclic_insert_loss_explicit(tmp_path: Path) -> None:
    profile_output = tmp_path / "profile"
    cycle_output = tmp_path / "cycle"

    ingest_dxf(ASCII, profile_output, created_at=FIXED_TIME, aecctx_version="0.2.0")
    ingest_dxf(CYCLE, cycle_output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    profile_codes = {record["code"] for record in _records(profile_output, "diagnostic")}
    cycle_codes = {record["code"] for record in _records(cycle_output, "diagnostic")}
    solid = next(record for record in _records(profile_output, "primitive") if record["original_class"] == "3DSOLID")
    assert solid["geometry"]["state"] == "unsupported"
    assert {"AECCTX_DXF_ACIS_KERNEL_UNSUPPORTED", "AECCTX_DXF_XREF_NOT_TRAVERSED"} <= profile_codes
    assert "AECCTX_DXF_INSERT_CYCLE" in cycle_codes
    assert validate_package(cycle_output).valid


def test_dxf_v02_malformed_and_record_limit_fail_with_stable_codes(tmp_path: Path) -> None:
    with pytest.raises(Exception) as malformed:
        ingest_dxf(MALFORMED, tmp_path / "malformed", aecctx_version="0.2.0")
    assert getattr(malformed.value, "code", None) == "AECCTX_DXF_PARSE_FAILED"

    with pytest.raises(Exception) as limited:
        ingest_dxf(ASCII, tmp_path / "limited", aecctx_version="0.2.0", max_records=1)
    assert getattr(limited.value, "code", None) == "AECCTX_DXF_RECORD_LIMIT_EXCEEDED"
