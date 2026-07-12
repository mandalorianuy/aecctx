from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import ezdxf
import pytest

from aecctx.adapters.dwg import ingest_dwg
from aecctx.dwg import DWGInputError, probe_dwg, validate_dwg_events
from aecctx.ingest import CAPABILITIES, ingest_opaque
from aecctx.package import PackageReader
from aecctx.providers.protocol import ProviderResult
from aecctx.records import RecordStore
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
FIXTURE_ROOT = ROOT / "fixtures" / "v0.2" / "dwg"
FIXTURE = FIXTURE_ROOT / "r2000-profile.dwg"
FIXED_TIME = "2026-07-12T00:00:00Z"


def _capabilities() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for name in CAPABILITIES:
        level = "partial" if name in {"identity", "properties", "relationships", "text", "2d_geometry", "materials_styles", "validation"} else "unsupported"
        result[name] = {
            "affected": ["dwg-source"],
            "fallback": "retain observed source objects and converted DXF evidence",
            "reason_codes": ["AECCTX_DWG_CONVERTED_DXF_EVIDENCE"],
            "support_level": level,
        }
    return result


def provider_result() -> ProviderResult:
    dxf = (FIXTURE_ROOT / "r2000-profile.dxf").read_bytes()
    document = ezdxf.readfile(FIXTURE_ROOT / "r2000-profile.dxf")
    objects = []
    for entity in sorted(document.entitydb.values(), key=lambda item: item.dxf.get("handle", "")):
        handle = entity.dxf.get("handle")
        if handle:
            objects.append(
                {
                    "aecctx_handle": handle.upper(),
                    "aecctx_locator": f"dwg:handle:{handle.upper()}",
                    "handle": handle.upper(),
                    "object": entity.dxftype(),
                }
            )
    source = {
        "CLASSES": [],
        "FILEHEADER": {"version": "AC1015"},
        "HEADER": {"INSUNITS": 6},
        "OBJECTS": objects,
        "aecctx_handle_conflicts": [],
        "created_by": "LibreDWG 0.13.4",
    }
    source_bytes = json.dumps(source, sort_keys=True, separators=(",", ":")).encode()
    input_sha = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    dxf_sha = hashlib.sha256(dxf).hexdigest()
    events = (
        {
            "event_type": "primitive",
            "payload": {
                "artifact_path": "artifacts/source.json",
                "artifact_sha256": source_sha,
                "dwg_version": "AC1015",
                "handle_conflicts": [],
                "input_sha256": input_sha,
                "object_count": len(objects),
                "schema": "aecctx.dwg.source.v1",
            },
            "sequence": 0,
            "source_locator": f"sha256:{input_sha}",
        },
        {
            "event_type": "primitive",
            "payload": {
                "artifact_path": "artifacts/converted-r2000.dxf",
                "artifact_sha256": dxf_sha,
                "converter": "LibreDWG dwgread 0.13.4",
                "dxf_version": "AC1015",
                "input_sha256": input_sha,
                "representation_fidelity": "converted",
                "schema": "aecctx.dwg.conversion.v1",
            },
            "sequence": 1,
            "source_locator": f"dwg-artifact:converted-dxf:sha256:{dxf_sha}",
        },
    )
    artifacts = (
        {"bytes": len(source_bytes), "media_type": "application/vnd.aecctx.libredwg+json", "path": "artifacts/source.json", "sha256": source_sha},
        {"bytes": len(dxf), "media_type": "application/dxf", "path": "artifacts/converted-r2000.dxf", "sha256": dxf_sha},
    )
    return ProviderResult(
        ok=True,
        events=events,
        artifacts=artifacts,
        artifact_bytes={"artifacts/source.json": source_bytes, "artifacts/converted-r2000.dxf": dxf},
        diagnostics=({"code": "AECCTX_DWG_CONVERTED_DXF_EVIDENCE", "severity": "info"},),
        capability_report=_capabilities(),
        resource_usage={"artifacts": 2, "events": 2, "source_objects": len(objects)},
        attestation={"provider_id": "org.aecctx.dwg.libredwg", "runtime_digest": "sha256:" + "b" * 64},
    )


def _records(path: Path) -> list[dict[str, object]]:
    return [record.raw for record in RecordStore.open(path).records.values()]


def test_probe_dwg_uses_exact_bounded_content_header() -> None:
    assert probe_dwg(FIXTURE.read_bytes()[:64]) == {"confidence": 1.0, "format": "dwg", "version": "AC1015"}
    assert probe_dwg(b"AC1027something")["confidence"] == 0.0
    assert probe_dwg(b"not dwg")["format"] == "unknown"


def test_dwg_event_validation_rejects_fidelity_escalation_and_hash_mismatch() -> None:
    result = provider_result()
    events = [dict(event) for event in result.events]
    events[1]["payload"] = {**events[1]["payload"], "representation_fidelity": "source-exact"}
    with pytest.raises(DWGInputError) as fidelity:
        validate_dwg_events(replace(result, events=tuple(events)))
    assert fidelity.value.code == "AECCTX_DWG_EVENT_INVALID"

    events = [dict(event) for event in result.events]
    events[0]["payload"] = {**events[0]["payload"], "artifact_sha256": "0" * 64}
    with pytest.raises(DWGInputError) as digest:
        validate_dwg_events(replace(result, events=tuple(events)))
    assert digest.value.code == "AECCTX_DWG_ARTIFACT_INVALID"


def test_dwg_v01_is_byte_identical_to_opaque_ingest(tmp_path: Path) -> None:
    opaque = tmp_path / "opaque.aecctx"
    adapter = tmp_path / "adapter.aecctx"
    ingest_opaque(FIXTURE, opaque, created_at=FIXED_TIME, package_form="zip")
    ingest_dwg(FIXTURE, adapter, created_at=FIXED_TIME, package_form="zip")
    assert opaque.read_bytes() == adapter.read_bytes()


def test_dwg_v02_requires_validated_provider_result(tmp_path: Path) -> None:
    with pytest.raises(DWGInputError) as captured:
        ingest_dwg(FIXTURE, tmp_path / "missing", aecctx_version="0.2.0")
    assert captured.value.code == "AECCTX_DWG_RUNTIME_UNAVAILABLE"


def test_dwg_v02_maps_observed_objects_and_converted_geometry(tmp_path: Path) -> None:
    output = tmp_path / "package.aecctx"
    ingest_dwg(FIXTURE, output, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0", provider_result=provider_result())

    assert validate_package(output).valid
    package_records = _records(output)
    observed = next(item for item in package_records if item.get("original_class") == "LINE" and item.get("evidence_class") == "observed")
    derived = next(item for item in package_records if item.get("original_class") == "LINE" and item.get("evidence_class") == "derived")
    assert observed["source_refs"][0]["locator"].startswith("dwg:handle:")
    assert derived["representation_fidelity"]["class"] == "converted"
    assert observed["record_id"] in derived["parent_evidence_ids"]
    source_record = next(item for item in package_records if item["record_type"] == "source")
    assert source_record["detected_units"]["state"] == "unknown"
    assert source_record["spatial_reference"]["state"] == "unknown"
    reader = PackageReader(output)
    assert reader.read_bytes("evidence/converted-r2000.dxf") == (FIXTURE_ROOT / "r2000-profile.dxf").read_bytes()
    assert reader.manifest["capabilities"]["2d_geometry"] == "partial"


def test_dwg_v02_zip_is_deterministic(tmp_path: Path) -> None:
    outputs = [tmp_path / "first.aecctx", tmp_path / "second.aecctx"]
    for output in outputs:
        ingest_dwg(FIXTURE, output, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0", provider_result=provider_result())
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
