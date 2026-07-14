from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .providers.protocol import ProviderResult


HANDLE_RE = re.compile(r"[0-9A-F]+")


class DWGInputError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class DWGEvidence:
    source_event: Mapping[str, Any]
    conversion_event: Mapping[str, Any]
    source_json: Mapping[str, Any]
    converted_dxf: bytes
    provider_result: ProviderResult


def probe_dwg(prefix: bytes) -> dict[str, Any]:
    for version in ("AC1012", "AC1014", "AC1015"):
        if prefix.startswith(version.encode("ascii")):
            return {"confidence": 1.0, "format": "dwg", "version": version}
    return {"confidence": 0.0, "format": "unknown", "version": "unclaimed"}


def _artifact(result: ProviderResult, path: str, media_type: str, expected_sha: str) -> bytes:
    declarations = [item for item in result.artifacts if item.get("path") == path and item.get("media_type") == media_type]
    value = result.artifact_bytes.get(path)
    if len(declarations) != 1 or not isinstance(value, bytes):
        raise DWGInputError("AECCTX_DWG_ARTIFACT_INVALID", f"Missing or invalid provider artifact: {path}")
    if declarations[0].get("sha256") != expected_sha or hashlib.sha256(value).hexdigest() != expected_sha:
        raise DWGInputError("AECCTX_DWG_ARTIFACT_INVALID", f"Provider artifact hash mismatch: {path}")
    return value


def _validate_source_json(value: Any, event: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DWGInputError("AECCTX_DWG_SOURCE_INVALID", "LibreDWG source artifact must be an object")
    if not isinstance(value.get("FILEHEADER"), Mapping) or value["FILEHEADER"].get("version") != event.get("dwg_version"):
        raise DWGInputError("AECCTX_DWG_SOURCE_INVALID", "LibreDWG source version does not match event")
    if not isinstance(value.get("HEADER"), Mapping) or not isinstance(value.get("CLASSES"), list) or not isinstance(value.get("OBJECTS"), list):
        raise DWGInputError("AECCTX_DWG_SOURCE_INVALID", "LibreDWG source containers are invalid")
    objects = value["OBJECTS"]
    if len(objects) != event.get("object_count"):
        raise DWGInputError("AECCTX_DWG_SOURCE_INVALID", "LibreDWG object count does not match event")
    conflicts = value.get("aecctx_handle_conflicts")
    if not isinstance(conflicts, list) or conflicts != event.get("handle_conflicts") or conflicts != sorted(set(conflicts)):
        raise DWGInputError("AECCTX_DWG_SOURCE_INVALID", "LibreDWG handle conflicts do not match event")
    locators: set[str] = set()
    counts: dict[str, int] = {}
    for item in objects:
        if not isinstance(item, Mapping):
            raise DWGInputError("AECCTX_DWG_SOURCE_INVALID", "LibreDWG object is invalid")
        handle = item.get("aecctx_handle")
        locator = item.get("aecctx_locator")
        original_class = item.get("object", item.get("entity"))
        if not isinstance(handle, str) or not HANDLE_RE.fullmatch(handle) or not isinstance(original_class, str):
            raise DWGInputError("AECCTX_DWG_SOURCE_INVALID", "LibreDWG object handle or class is invalid")
        occurrence = counts.get(handle, 0)
        counts[handle] = occurrence + 1
        expected = f"dwg:handle:{handle}"
        if handle in conflicts:
            expected += f":occurrence:{occurrence}"
        if locator != expected or locator in locators:
            raise DWGInputError("AECCTX_DWG_SOURCE_INVALID", "LibreDWG object locator is invalid")
        locators.add(locator)
    actual_conflicts = sorted(handle for handle, count in counts.items() if count > 1)
    if actual_conflicts != conflicts:
        raise DWGInputError("AECCTX_DWG_SOURCE_INVALID", "LibreDWG duplicate handles are not declared")
    return value


def validate_dwg_events(result: ProviderResult) -> DWGEvidence:
    if not result.ok or result.attestation.get("provider_id") != "org.aecctx.dwg.libredwg":
        raise DWGInputError("AECCTX_DWG_PROVIDER_RESULT_INVALID", "Validated successful ACX-18 provider result required")
    if [item.get("sequence") for item in result.events] != [0, 1]:
        raise DWGInputError("AECCTX_DWG_EVENT_INVALID", "Provider event sequence must contain source then conversion")
    payloads = [item.get("payload") for item in result.events]
    if any(not isinstance(payload, Mapping) for payload in payloads):
        raise DWGInputError("AECCTX_DWG_EVENT_INVALID", "Provider event payload is invalid")
    event_schemas = [payload.get("schema") for payload in payloads]
    v03 = event_schemas == ["aecctx.dwg.source.v2", "aecctx.dwg.conversion.v2"]
    schema_name = "dwg-v03-event.schema.json" if v03 else "dwg-provider-event.schema.json"
    schema = json.loads(files("aecctx.schemas.v0_2").joinpath(schema_name).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for payload in payloads:
        errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
        if errors:
            location = "/".join(str(item) for item in errors[0].absolute_path) or "<root>"
            raise DWGInputError("AECCTX_DWG_EVENT_INVALID", f"Provider event invalid at {location}: {errors[0].message}")
    source_event, conversion_event = payloads
    if not v03 and (source_event.get("schema") != "aecctx.dwg.source.v1" or conversion_event.get("schema") != "aecctx.dwg.conversion.v1"):
        raise DWGInputError("AECCTX_DWG_EVENT_INVALID", "Provider source/conversion event ordering is invalid")
    if source_event.get("input_sha256") != conversion_event.get("input_sha256"):
        raise DWGInputError("AECCTX_DWG_EVENT_INVALID", "Provider conversion input hash is disconnected")
    if v03 and (
        source_event.get("profile") != conversion_event.get("profile")
        or source_event.get("dwg_version") != conversion_event.get("requested_dxf_version")
        or source_event.get("dwg_version") != conversion_event.get("observed_dxf_version")
    ):
        raise DWGInputError("AECCTX_DWG_EVENT_INVALID", "Provider v0.3 profile/version lineage is disconnected")
    source_bytes = _artifact(result, str(source_event["artifact_path"]), "application/vnd.aecctx.libredwg+json", str(source_event["artifact_sha256"]))
    converted_dxf = _artifact(result, str(conversion_event["artifact_path"]), "application/dxf", str(conversion_event["artifact_sha256"]))
    try:
        source_json = json.loads(source_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DWGInputError("AECCTX_DWG_SOURCE_INVALID", "LibreDWG source artifact is invalid JSON") from error
    validated_source = _validate_source_json(source_json, source_event)
    if v03 and (
        (validated_source.get("aecctx_units") is not None and validated_source.get("aecctx_units") != source_event.get("units"))
        or (
            validated_source.get("aecctx_unsupported_classes") is not None
            and validated_source.get("aecctx_unsupported_classes") != source_event.get("unsupported_classes")
        )
    ):
        raise DWGInputError("AECCTX_DWG_SOURCE_INVALID", "Provider v0.3 source metadata does not match event")
    return DWGEvidence(source_event, conversion_event, validated_source, converted_dxf, result)
