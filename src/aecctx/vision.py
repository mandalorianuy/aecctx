from __future__ import annotations

import hashlib
import importlib.resources
import json
from dataclasses import dataclass
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .providers.protocol import ProviderResult


class VisionMappingError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class VisionMapping:
    primitives: tuple[dict[str, Any], ...]
    assertions: tuple[dict[str, Any], ...]
    diagnostics: tuple[dict[str, Any], ...]


def _id(prefix: str, source_id: str, key: str) -> str:
    return f"{prefix}_{hashlib.sha256(f'{source_id}\0{key}'.encode()).hexdigest()[:24]}"


def map_vision_result(result: ProviderResult, *, input_bytes: bytes, source_id: str, parent_record_id: str, source_locator: str, width: int, height: int, recorded_at: str) -> VisionMapping:
    if not result.ok:
        raise VisionMappingError("provider failed")
    if result.attestation.get("provider_id") != "org.aecctx.vision.raster-rules" or result.attestation.get("network_mode") != "disabled" or result.attestation.get("deterministic") is not True:
        raise VisionMappingError("provider attestation invalid")
    events = [event for event in result.events if event.get("event_type") == "primitive" and event.get("payload", {}).get("schema") == "aecctx.vision.candidates.v1"]
    if len(events) != 1:
        raise VisionMappingError("vision event profile invalid")
    digest = hashlib.sha256(input_bytes).hexdigest()
    if events[0].get("source_locator") != f"sha256:{digest}":
        raise VisionMappingError("input hash mismatch")
    payload = events[0]["payload"]
    schema = json.loads(importlib.resources.files("aecctx.schemas.v0_2").joinpath("vision-candidate.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda error: list(error.absolute_path))
    if errors:
        raise VisionMappingError(f"vision schema invalid: {errors[0].message}")
    if payload["width"] != width or payload["height"] != height:
        raise VisionMappingError("vision bounds dimensions mismatch")
    response_digest = str(result.attestation["response_payload_digest"])
    common_inference = {"execution_mode": "local", "extraction_confidence": 1.0, "input_artifact_sha256": digest, "input_region_sha256": digest, "interpretation_confidence": 1.0, "model_version": str(result.attestation["runtime_version"]), "provider_id": str(result.attestation["provider_id"]), "provider_version": str(result.attestation["provider_version"]), "reproducibility": "deterministic", "request_digest": str(result.attestation["request_digest"]), "response_digest": response_digest, "verification_state": "unverified"}
    candidate_records: dict[str, str] = {}
    primitives: list[dict[str, Any]] = []
    for candidate in payload["candidates"]:
        x, y, w, h = candidate["bbox"]
        if x + w > width or y + h > height:
            raise VisionMappingError("candidate bounds outside raster")
        record_id = _id("prim_vision", source_id, f"{source_locator}:{candidate['id']}:{response_digest}")
        candidate_records[candidate["id"]] = record_id
        primitives.append({"container": {"state": "known", "value": source_locator}, "evidence_class": "inferred", "extraction_confidence": {"band": "full", "method": "validated-provider-response"}, "inference": common_inference, "interpretation_confidence": {"band": "estimated", "method": "exact-visible-rule-match", "value": 1.0}, "original_class": "VISION_" + candidate["kind"].replace(".", "_").upper(), "pixel_geometry": {"bbox": candidate["bbox"], "origin": "top-left", "unit": "px"}, "provenance": {"method": "validated-vision-provider-mapping", "parent_record_ids": [parent_record_id], "producer_id": result.attestation["provider_id"], "producer_version": result.attestation["provider_version"], "recorded_at": recorded_at}, "record_id": record_id, "record_type": "primitive", "record_version": "0.2", "source_refs": [{"locator": f"{source_locator}/vision:{candidate['id']}", "source_id": source_id}], "vision_state": candidate["state"]})
    assertions: list[dict[str, Any]] = []
    confidence_fields = {
        "extraction_confidence": {"band": "full", "method": "validated-provider-response"},
        "interpretation_confidence": {"band": "estimated", "method": "exact-visible-rule-match", "value": 1.0},
    }
    for relationship in payload["relationships"]:
        if relationship["subject_id"] not in candidate_records or relationship["object_id"] not in candidate_records:
            raise VisionMappingError("relationship references unknown candidate")
        evidence = [candidate_records[relationship["subject_id"]], candidate_records[relationship["object_id"]]]
        assertions.append({
            **confidence_fields, "evidence_class": "inferred", "evidence_record_ids": evidence, "inference": common_inference,
            "predicate": "aecctx:vision-contains", "provenance": {"method": "exact-pixel-bounds-containment", "parent_record_ids": evidence, "producer_id": result.attestation["provider_id"], "producer_version": result.attestation["provider_version"], "recorded_at": recorded_at},
            "record_id": _id("assert_vision", source_id, relationship["id"] + response_digest), "record_type": "assertion", "record_version": "0.2",
            "source_refs": [{"locator": source_locator, "source_id": source_id}], "subject_id": candidate_records[relationship["subject_id"]],
            "value": {"state": "known", "value": candidate_records[relationship["object_id"]]}, "verification_state": "unverified",
        })
    for hypothesis in payload["reconstructions"]:
        if any(value not in candidate_records for value in hypothesis["source_candidate_ids"]):
            raise VisionMappingError("reconstruction references unknown candidate")
        evidence = [candidate_records[value] for value in hypothesis["source_candidate_ids"]]
        assertions.append({
            **confidence_fields, "evidence_class": "inferred", "evidence_record_ids": evidence, "inference": common_inference,
            "measurement_authority": {"state": "unsupported", "reason_code": "AECCTX_VISION_PIXEL_HYPOTHESIS_NOT_MEASUREMENT"},
            "predicate": "aecctx:reconstruction-planar-boundary", "provenance": {"method": "visible-rectangle-rule", "parent_record_ids": evidence, "producer_id": result.attestation["provider_id"], "producer_version": result.attestation["provider_version"], "recorded_at": recorded_at},
            "record_id": _id("assert_reconstruction", source_id, hypothesis["id"] + response_digest), "record_type": "assertion", "record_version": "0.2",
            "source_refs": [{"locator": source_locator, "source_id": source_id}], "subject_id": parent_record_id,
            "value": {"state": "known", "value": {"coordinate_space": "pixel", "kind": hypothesis["kind"], "pixel_polygon": hypothesis["pixel_polygon"]}}, "verification_state": "unverified",
        })
    diagnostics = () if primitives else ({"code": "AECCTX_VISION_NO_CANDIDATE", "message": "No exact governed visible-raster candidate was detected."},)
    return VisionMapping(tuple(primitives), tuple(assertions), diagnostics)
