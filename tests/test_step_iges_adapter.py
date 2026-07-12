from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from aecctx.adapters.step_iges import ingest_step_iges
from aecctx.ingest import ingest_opaque
from aecctx.package import PackageReader
from aecctx.providers.protocol import ProviderResult
from aecctx.records import RecordStore
from aecctx.step_iges import StepIgesInputError, probe_step_iges, validate_step_iges_events
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "fixtures" / "v0.2" / "step-iges" / "ap214-assembly.step"
FIXED_TIME = "2026-07-12T00:00:00Z"


def _capabilities() -> dict[str, dict[str, object]]:
    result = {}
    for name in ("identity", "hierarchy", "properties", "relationships", "text", "2d_geometry", "3d_geometry", "materials_styles", "georeferencing", "validation"):
        level = "full" if name == "identity" else ("partial" if name in {"hierarchy", "properties", "relationships", "3d_geometry", "validation"} else "unsupported")
        result[name] = {
            "affected": [] if level == "full" else ["step-iges-source"],
            "fallback": "none" if level == "full" else "retain source evidence",
            "reason_codes": [] if level == "full" else ["AECCTX_STEP_IGES_PROFILE_PARTIAL"],
            "support_level": level,
        }
    return result


def provider_result(*, invalid_triangle: bool = False) -> ProviderResult:
    brep = b"DBRep_DrawableShape\nfixture"
    mesh = {
        "schema": "aecctx.triangle-mesh.v1",
        "triangles": [[0, 1, 9] if invalid_triangle else [0, 1, 2]],
        "vertices": [[0.0, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 20.0, 0.0]],
    }
    mesh_bytes = json.dumps(mesh, sort_keys=True, separators=(",", ":")).encode()
    source_payload = {
        "entities": [
            {"id": 1, "original_class": "PRODUCT", "raw": "#1=PRODUCT('assembly','Assembly','',());", "references": []},
            {"id": 2, "original_class": "PRODUCT", "raw": "#2=PRODUCT('part','Part','',());", "references": []},
            {"id": 3, "original_class": "NEXT_ASSEMBLY_USAGE_OCCURRENCE", "raw": "#3=NEXT_ASSEMBLY_USAGE_OCCURRENCE('1','','',#1,#2,$);", "references": [1, 2]},
        ],
        "external_references": False,
        "format": "step",
        "headers": {"FILE_SCHEMA": ["AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }"]},
        "schema": "aecctx.step-iges.source.v1",
        "schemas": ["AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }"],
    }
    events = (
        {"event_type": "primitive", "payload": source_payload, "sequence": 0, "source_locator": "sha256:" + "a" * 64},
        {
            "event_type": "primitive",
            "payload": {
                "artifact_path": "artifacts/root-1.brep",
                "bounds": {"max": [10.0, 20.0, 0.0], "min": [0.0, 0.0, 0.0]},
                "format": "step",
                "mesh_artifact_path": "artifacts/scene-mesh.json",
                "representation_fidelity": "brep-translator-derived",
                "schema": "aecctx.step-iges.shape.v1",
                "topology": {"edges": 3, "faces": 1, "shells": 1, "solids": 1, "vertices": 3, "wires": 1},
                "translator_processing": "translator-default-observed",
            },
            "sequence": 1,
            "source_locator": "shape:1",
        },
    )
    artifacts = (
        {"bytes": len(brep), "media_type": "model/vnd.opencascade.brep", "path": "artifacts/root-1.brep", "sha256": hashlib.sha256(brep).hexdigest()},
        {"bytes": len(mesh_bytes), "media_type": "application/vnd.aecctx.triangle-mesh+json", "path": "artifacts/scene-mesh.json", "sha256": hashlib.sha256(mesh_bytes).hexdigest()},
    )
    return ProviderResult(
        ok=True,
        events=events,
        artifacts=artifacts,
        artifact_bytes={"artifacts/root-1.brep": brep, "artifacts/scene-mesh.json": mesh_bytes},
        diagnostics=({"code": "AECCTX_STEP_IGES_TRANSLATOR_PROCESSING_APPLIED", "severity": "info"},),
        capability_report=_capabilities(),
        resource_usage={"artifacts": 2, "events": 2, "source_entities": 3},
        attestation={"provider_id": "org.aecctx.step-iges.ocp", "runtime_digest": "sha256:" + "b" * 64},
    )


def records(path: Path) -> list[dict[str, object]]:
    return [record.raw for record in RecordStore.open(path).records.values()]


def test_probe_step_iges_uses_bounded_content_not_extension() -> None:
    assert probe_step_iges(FIXTURE.read_bytes()[:64])["format"] == "step"
    assert probe_step_iges((ROOT / "fixtures" / "v0.2" / "step-iges" / "iges53-part.igs").read_bytes()[:6400])["format"] == "iges"
    assert probe_step_iges(b"not a CAD exchange")["confidence"] == 0.0


def test_step_iges_event_validation_rejects_out_of_range_mesh_indices() -> None:
    with pytest.raises(StepIgesInputError) as captured:
        validate_step_iges_events(provider_result(invalid_triangle=True))
    assert captured.value.code == "AECCTX_STEP_IGES_MESH_INVALID"


def test_step_iges_event_validation_rejects_fidelity_escalation() -> None:
    result = provider_result()
    events = [dict(event) for event in result.events]
    events[1]["payload"] = {**events[1]["payload"], "representation_fidelity": "source-exact"}
    changed = replace(result, events=tuple(events))
    with pytest.raises(StepIgesInputError) as captured:
        validate_step_iges_events(changed)
    assert captured.value.code == "AECCTX_STEP_IGES_EVENT_INVALID"


def test_step_iges_v01_is_byte_identical_to_opaque_ingest(tmp_path: Path) -> None:
    opaque = tmp_path / "opaque.aecctx"
    adapter = tmp_path / "adapter.aecctx"
    ingest_opaque(FIXTURE, opaque, created_at=FIXED_TIME, package_form="zip")
    ingest_step_iges(FIXTURE, adapter, created_at=FIXED_TIME, package_form="zip")
    assert opaque.read_bytes() == adapter.read_bytes()


def test_step_iges_v02_requires_validated_provider_result(tmp_path: Path) -> None:
    with pytest.raises(StepIgesInputError) as captured:
        ingest_step_iges(FIXTURE, tmp_path / "missing", aecctx_version="0.2.0")
    assert captured.value.code == "AECCTX_STEP_IGES_RUNTIME_UNAVAILABLE"


def test_step_iges_v02_maps_observed_structure_and_derived_geometry(tmp_path: Path) -> None:
    output = tmp_path / "package.aecctx"
    ingest_step_iges(FIXTURE, output, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0", provider_result=provider_result())

    assert validate_package(output).valid
    package_records = records(output)
    product = next(
        item
        for item in package_records
        if item.get("original_class") == "PRODUCT" and item["record_type"] == "primitive" and item.get("id") == 1
    )
    assert product["evidence_class"] == "observed"
    assert product["raw"] == "#1=PRODUCT('assembly','Assembly','',());"
    relation = next(item for item in package_records if item["record_type"] == "relation")
    assert relation["original_class"] == "NEXT_ASSEMBLY_USAGE_OCCURRENCE"
    assert relation["evidence_class"] == "observed"
    brep = next(item for item in package_records if item.get("original_class") == "OCCT_TRANSLATED_BREP")
    assert brep["evidence_class"] == "derived"
    assert brep["representation_fidelity"]["class"] == "brep"
    paths = {item["path"] for item in PackageReader(output).manifest["artifacts"]}
    assert {"geometry/root-1.brep", "geometry/scene.glb"}.issubset(paths)
    assert PackageReader(output).read_bytes("geometry/scene.glb")[:4] == b"glTF"
    assert PackageReader(output).manifest["capabilities"]["3d_geometry"] == "partial"
