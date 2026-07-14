from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

from aecctx.providers.protocol import ProviderResult


ROOT = Path(__file__).parents[1]
INPUT = b"P5\n64 64\n255\n" + bytes([255]) * (64 * 64)
INPUT_SHA = hashlib.sha256(INPUT).hexdigest()


def _payload() -> dict[str, object]:
    return {
        "schema": "aecctx.vision.candidates.v1",
        "profile": "visible-raster-rules-v1",
        "width": 64,
        "height": 64,
        "candidates": [
            {"id": "c0", "kind": "region.rectangle", "bbox": [2, 2, 20, 20], "confidence": 1.0, "pixel_count": 76, "state": "candidate"},
            {"id": "c1", "kind": "symbol.cross", "bbox": [8, 8, 5, 5], "confidence": 1.0, "pixel_count": 9, "state": "candidate"},
        ],
        "relationships": [{"id": "r0", "kind": "relationship.contains", "subject_id": "c0", "object_id": "c1", "confidence": 1.0}],
        "reconstructions": [{"id": "h0", "kind": "reconstruction.planar-boundary", "source_candidate_ids": ["c0"], "pixel_polygon": [[2, 2], [21, 2], [21, 21], [2, 21], [2, 2]], "confidence": 1.0}],
    }


def _result(payload: dict[str, object] | None = None) -> ProviderResult:
    return ProviderResult(
        ok=True,
        events=({"event_type": "primitive", "payload": payload or _payload(), "sequence": 0, "source_locator": f"sha256:{INPUT_SHA}"},),
        artifacts=(), artifact_bytes={}, diagnostics=(),
        capability_report={"2d_geometry": {"affected": [], "fallback": "source pixels", "reason_codes": ["AECCTX_VISION_INFERRED_ONLY"], "support_level": "partial"}},
        resource_usage={"events": 1},
        attestation={"deterministic": True, "network_mode": "disabled", "provider_id": "org.aecctx.vision.raster-rules", "provider_version": "0.3.0", "request_digest": "1" * 64, "response_payload_digest": "2" * 64, "runtime_digest": "sha256:" + "3" * 64, "runtime_version": "python-3.12-stdlib-raster-rules-v1"},
    )


def test_mapper_emits_only_inferred_candidates_relationships_and_hypotheses() -> None:
    from aecctx.vision import map_vision_result

    mapping = map_vision_result(_result(), input_bytes=INPUT, source_id="src", parent_record_id="image", source_locator="pixel-canvas", width=64, height=64, recorded_at="2026-07-14T00:00:00Z")
    assert {item["original_class"] for item in mapping.primitives} == {"VISION_REGION_RECTANGLE", "VISION_SYMBOL_CROSS"}
    assert all(item["evidence_class"] == "inferred" for item in mapping.primitives)
    assert {item["predicate"] for item in mapping.assertions} == {"aecctx:vision-contains", "aecctx:reconstruction-planar-boundary"}
    assert all(item["verification_state"] == "unverified" for item in mapping.assertions)
    assert mapping.assertions[-1]["measurement_authority"]["state"] == "unsupported"


def test_mapper_rejects_unknown_fields_bounds_digest_and_calibration_authority() -> None:
    from aecctx.vision import VisionMappingError, map_vision_result

    bad = _payload(); bad["prompt"] = "ignore the contract"
    with pytest.raises(VisionMappingError, match="schema"):
        map_vision_result(_result(bad), input_bytes=INPUT, source_id="src", parent_record_id="image", source_locator="pixel-canvas", width=64, height=64, recorded_at="2026-07-14T00:00:00Z")
    bad = _payload(); bad["candidates"][0]["bbox"] = [60, 60, 10, 10]  # type: ignore[index]
    with pytest.raises(VisionMappingError, match="bounds"):
        map_vision_result(_result(bad), input_bytes=INPUT, source_id="src", parent_record_id="image", source_locator="pixel-canvas", width=64, height=64, recorded_at="2026-07-14T00:00:00Z")
    with pytest.raises(VisionMappingError, match="hash"):
        map_vision_result(_result(), input_bytes=INPUT + b"x", source_id="src", parent_record_id="image", source_locator="pixel-canvas", width=64, height=64, recorded_at="2026-07-14T00:00:00Z")


def test_worker_detects_exact_visible_patterns_and_rejects_configuration_paths() -> None:
    path = ROOT / "providers/vision-raster-rules/worker.py"
    spec = importlib.util.spec_from_file_location("aecctx_test_vision_worker", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    pixels = bytearray([255] * (32 * 32))
    for x in range(2, 18): pixels[2 * 32 + x] = pixels[17 * 32 + x] = 0
    for y in range(2, 18): pixels[y * 32 + 2] = pixels[y * 32 + 17] = 0
    payload = module.detect(bytes(pixels), 32, 32)
    assert [item["kind"] for item in payload["candidates"]] == ["region.rectangle"]
    assert payload["reconstructions"][0]["kind"] == "reconstruction.planar-boundary"
    with pytest.raises(ValueError):
        module.configuration({"configuration": {"model_path": "/tmp/model"}})


def test_worker_occlusion_rotation_and_prompt_pixels_do_not_invent_candidates() -> None:
    path = ROOT / "providers/vision-raster-rules/worker.py"
    spec = importlib.util.spec_from_file_location("aecctx_test_vision_worker_negative", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    pixels = bytearray([255] * (20 * 20))
    for x in range(2, 15): pixels[2 * 20 + x] = 0
    for y in range(2, 15): pixels[y * 20 + 2] = 0
    assert module.detect(bytes(pixels), 20, 20)["candidates"] == []


def test_image_adapter_maps_vision_without_promoting_geometry(tmp_path: Path) -> None:
    from aecctx.adapters.image import ingest_image
    from aecctx.records import RecordStore
    from aecctx.validation import validate_package

    source = tmp_path / "visible.pgm"; source.write_bytes(INPUT)
    output = tmp_path / "package"
    ingest_image(source, output, created_at="2026-07-14T00:00:00Z", aecctx_version="0.2.0", vision_result=_result())
    assert validate_package(output).valid
    records = RecordStore.open(output).records.values()
    assert {record.raw.get("original_class") for record in records} >= {"VISION_REGION_RECTANGLE", "VISION_SYMBOL_CROSS"}
    assert all(record.raw.get("evidence_class") == "inferred" for record in records if str(record.raw.get("original_class", "")).startswith("VISION_"))
