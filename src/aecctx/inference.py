from __future__ import annotations

import hashlib
import math
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .providers.protocol import ProviderResult


class InferenceMappingError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class OCRMapping:
    primitives: tuple[dict[str, Any], ...]
    assertions: tuple[dict[str, Any], ...]
    diagnostics: tuple[dict[str, Any], ...]


def canonical_ocr_pgm(width: int, height: int, grayscale_pixels: bytes) -> bytes:
    if width < 1 or height < 1 or len(grayscale_pixels) != width * height:
        raise ValueError("canonical OCR pixels must exactly match positive dimensions")
    return f"P5\n{width} {height}\n255\n".encode("ascii") + grayscale_pixels


def _stable_id(prefix: str, source_id: str, key: str) -> str:
    digest = hashlib.sha256(f"{source_id}\0{key}".encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def _known(value: Any) -> dict[str, Any]:
    return {"state": "known", "value": value}


def _provider_attestation(attestation: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "provider_id",
        "provider_version",
        "runtime_version",
        "network_mode",
        "deterministic",
        "request_digest",
        "response_payload_digest",
    )
    if any(field not in attestation for field in required):
        raise InferenceMappingError("AECCTX_OCR_ATTESTATION_INVALID", "OCR result is missing provider attestation fields")
    if attestation["network_mode"] != "disabled":
        raise InferenceMappingError("AECCTX_OCR_NETWORK_POLICY_INVALID", "The selected OCR profile requires disabled network mode")
    return {
        "deterministic": bool(attestation["deterministic"]),
        "execution_mode": "local",
        "network_mode": "disabled",
        "provider_id": str(attestation["provider_id"]),
        "provider_version": str(attestation["provider_version"]),
        "request_digest": str(attestation["request_digest"]),
        "response_digest": str(attestation["response_payload_digest"]),
        "runtime_version": str(attestation["runtime_version"]),
    }


def _word_events(result: ProviderResult) -> tuple[Mapping[str, Any], list[Mapping[str, Any]]]:
    matching = [event for event in result.events if event.get("event_type") == "primitive" and event.get("payload", {}).get("schema") == "aecctx.ocr.words.v1"]
    if len(matching) != 1:
        raise InferenceMappingError("AECCTX_OCR_EVENT_PROFILE_INVALID", "OCR response requires exactly one aecctx.ocr.words.v1 event")
    payload = matching[0]["payload"]
    words = payload.get("words")
    if not isinstance(words, list) or any(not isinstance(word, Mapping) for word in words):
        raise InferenceMappingError("AECCTX_OCR_EVENT_PROFILE_INVALID", "OCR words must be an array of objects")
    return payload, list(words)


def map_ocr_result(
    result: ProviderResult,
    *,
    input_bytes: bytes,
    source_id: str,
    parent_record_id: str,
    source_locator: str,
    width: int,
    height: int,
    recorded_at: str,
    input_region_sha256: str | None = None,
    native_text_records: Iterable[Mapping[str, Any]] = (),
) -> OCRMapping:
    if not result.ok:
        raise InferenceMappingError("AECCTX_OCR_PROVIDER_FAILED", "OCR provider did not return a successful result")
    if width < 1 or height < 1:
        raise InferenceMappingError("AECCTX_OCR_INPUT_DIMENSIONS_INVALID", "OCR input dimensions must be positive")
    attestation = _provider_attestation(result.attestation)
    payload, words = _word_events(result)
    language = payload.get("language")
    if language != "eng" or payload.get("page_segmentation_mode") != 6:
        raise InferenceMappingError("AECCTX_OCR_EVENT_PROFILE_INVALID", "OCR response is outside the governed language/PSM profile")
    orders = [word.get("reading_order") for word in words]
    if orders != list(range(len(words))):
        raise InferenceMappingError("AECCTX_OCR_READING_ORDER_INVALID", "OCR reading order must be unique, contiguous and zero-based")

    input_digest = hashlib.sha256(input_bytes).hexdigest()
    event_locator = next(event["source_locator"] for event in result.events if event.get("event_type") == "primitive" and event.get("payload", {}).get("schema") == "aecctx.ocr.words.v1")
    if event_locator != f"sha256:{input_digest}":
        raise InferenceMappingError("AECCTX_OCR_INPUT_HASH_MISMATCH", "OCR response does not attest the supplied input bytes")
    region_digest = input_region_sha256 or input_digest
    primitives: list[dict[str, Any]] = []
    for word in words:
        text = word.get("text")
        confidence = word.get("confidence")
        bbox = word.get("bbox")
        if not isinstance(text, str) or not text:
            raise InferenceMappingError("AECCTX_OCR_WORD_INVALID", "OCR word text must be non-empty")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not math.isfinite(float(confidence)) or not 0 <= float(confidence) <= 100:
            raise InferenceMappingError("AECCTX_OCR_WORD_CONFIDENCE_INVALID", "OCR confidence must be finite and between 0 and 100")
        if not isinstance(bbox, list) or len(bbox) != 4 or any(not isinstance(value, int) or isinstance(value, bool) for value in bbox):
            raise InferenceMappingError("AECCTX_OCR_WORD_BOUNDS_INVALID", "OCR bounding box must contain four integers")
        left, top, box_width, box_height = bbox
        if left < 0 or top < 0 or box_width < 1 or box_height < 1 or left + box_width > width or top + box_height > height:
            raise InferenceMappingError("AECCTX_OCR_WORD_BOUNDS_INVALID", "OCR bounding box is outside the input raster")
        order = int(word["reading_order"])
        record_id = _stable_id("prim_ocr_word", source_id, f"{source_locator}:{order}:{attestation['response_digest']}")
        interpretation_confidence = round(float(confidence) / 100.0, 6)
        primitives.append(
            {
                "container": _known(source_locator),
                "evidence_class": "inferred",
                "extraction_confidence": {"band": "full", "method": "validated-provider-response"},
                "inference": {
                    "execution_mode": "local",
                    "extraction_confidence": 1.0,
                    "input_artifact_sha256": input_digest,
                    "input_region_sha256": region_digest,
                    "interpretation_confidence": interpretation_confidence,
                    "model_version": attestation["runtime_version"],
                    "provider_id": attestation["provider_id"],
                    "provider_version": attestation["provider_version"],
                    "reproducibility": "deterministic" if attestation["deterministic"] else "non_deterministic",
                    "request_digest": attestation["request_digest"],
                    "response_digest": attestation["response_digest"],
                    "verification_state": "unverified",
                },
                "interpretation_confidence": {"band": "estimated", "method": "provider-word-confidence", "value": interpretation_confidence},
                "language": "eng",
                "original_class": "OCR_WORD",
                "pixel_geometry": {"bbox": bbox, "origin": "top-left", "unit": "px"},
                "provenance": {
                    "method": "validated-ocr-provider-mapping",
                    "parent_record_ids": [parent_record_id],
                    "producer_id": attestation["provider_id"],
                    "producer_version": attestation["provider_version"],
                    "recorded_at": recorded_at,
                },
                "provider_attestation": attestation,
                "reading_order": order,
                "record_id": record_id,
                "record_type": "primitive",
                "record_version": "0.2",
                "source_refs": [{"locator": f"{source_locator}/ocr-word:{order}", "source_id": source_id}],
                "value": _known(text),
            }
        )

    diagnostics: list[dict[str, Any]] = []
    assertions: list[dict[str, Any]] = []
    if not primitives:
        diagnostics.append(
            _diagnostic(
                source_id,
                parent_record_id,
                source_locator,
                recorded_at,
                "AECCTX_OCR_NO_TEXT_DETECTED",
                "OCR provider returned no accepted words.",
                attestation,
            )
        )

    ocr_text = _normalized_text(" ".join(record["value"]["value"] for record in primitives))
    for index, native in enumerate(native_text_records):
        native_id = native.get("record_id")
        native_state = native.get("value")
        native_text = native_state.get("value") if isinstance(native_state, Mapping) and native_state.get("state") == "known" else None
        if not isinstance(native_id, str) or not isinstance(native_text, str):
            continue
        native_normalized = _normalized_text(native_text)
        evidence_ids = [native_id, *(record["record_id"] for record in primitives)]
        equivalent = native_normalized == ocr_text
        value = _known("equivalent") if equivalent else {
            "alternatives": [native_text, ocr_text],
            "reason_code": "AECCTX_OCR_NATIVE_TEXT_CONFLICT",
            "state": "conflicted",
        }
        assertion_id = _stable_id("assert_ocr_native", source_id, f"{source_locator}:{index}:{attestation['response_digest']}")
        assertions.append(
            {
                "evidence_class": "derived",
                "evidence_record_ids": evidence_ids,
                "predicate": "aecctx:ocr-native-text-comparison",
                "provenance": {
                    "method": "deterministic-normalized-text-comparison",
                    "parent_record_ids": evidence_ids,
                    "producer_id": "aecctx.core.inference",
                    "producer_version": "0.2.0",
                    "recorded_at": recorded_at,
                },
                "record_id": assertion_id,
                "record_type": "assertion",
                "record_version": "0.2",
                "source_refs": [{"locator": source_locator, "source_id": source_id}],
                "subject_id": parent_record_id,
                "value": value,
                "verification_state": "unverified",
            }
        )
        if not equivalent:
            diagnostics.append(
                _diagnostic(
                    source_id,
                    parent_record_id,
                    source_locator,
                    recorded_at,
                    "AECCTX_OCR_NATIVE_TEXT_CONFLICT",
                    "Native PDF text and OCR text conflict; neither value was selected.",
                    attestation,
                    evidence_ids=evidence_ids,
                )
            )

    return OCRMapping(tuple(primitives), tuple(assertions), tuple(diagnostics))


def _diagnostic(
    source_id: str,
    parent_record_id: str,
    source_locator: str,
    recorded_at: str,
    code: str,
    message: str,
    attestation: Mapping[str, Any],
    *,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    parents = evidence_ids or [parent_record_id]
    return {
        "affected_count": 1,
        "capability": "text",
        "code": code,
        "evidence_class": "derived",
        "evidence_record_ids": parents,
        "fallback": "Inspect native text, source pixels and inferred OCR records independently.",
        "message": message,
        "provenance": {
            "method": "ocr-result-validation",
            "parent_record_ids": parents,
            "producer_id": "aecctx.core.inference",
            "producer_version": "0.2.0",
            "recorded_at": recorded_at,
        },
        "record_id": _stable_id("diag_ocr", source_id, f"{source_locator}:{code}"),
        "record_type": "diagnostic",
        "record_version": "0.2",
        "severity": "warning" if code == "AECCTX_OCR_NATIVE_TEXT_CONFLICT" else "info",
        "source_refs": [{"locator": source_locator, "source_id": source_id}],
        "support_level": "partial",
    }
