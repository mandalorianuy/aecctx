from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .providers.protocol import ProviderResult


class StepIgesInputError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class StepIgesEvidence:
    source: Mapping[str, Any]
    shape: Mapping[str, Any]
    brep: bytes
    mesh: Mapping[str, Any]
    provider_result: ProviderResult
    xde: Mapping[str, Any] = field(default_factory=dict)
    roots: tuple[Mapping[str, Any], ...] = ()
    breps: Mapping[str, bytes] = field(default_factory=dict)
    meshes: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    healed_breps: Mapping[str, bytes] = field(default_factory=dict)


def probe_step_iges(prefix: bytes) -> dict[str, Any]:
    if prefix.lstrip().startswith(b"ISO-10303-21;"):
        return {"confidence": 1.0, "format": "step"}
    sections = {chr(line[72]) for line in prefix.splitlines() if len(line) == 80 and line[72] in b"SGDPT"}
    # A bounded probe can end before the first parameter record.  The start,
    # global, and directory sections are sufficient to identify the fixed-width
    # IGES envelope without trusting a filename extension.
    if {"S", "G", "D"}.issubset(sections):
        return {"confidence": 1.0, "format": "iges"}
    return {"confidence": 0.0, "format": "unknown"}


def _artifact(result: ProviderResult, path: str, media_type: str) -> bytes:
    declarations = [item for item in result.artifacts if item.get("path") == path and item.get("media_type") == media_type]
    if len(declarations) != 1 or path not in result.artifact_bytes:
        raise StepIgesInputError("AECCTX_STEP_IGES_ARTIFACT_INVALID", f"Missing or invalid provider artifact: {path}")
    return result.artifact_bytes[path]


def _validate_mesh(result: ProviderResult, path: str) -> Mapping[str, Any]:
    mesh_bytes = _artifact(result, path, "application/vnd.aecctx.triangle-mesh+json")
    try:
        mesh = json.loads(mesh_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise StepIgesInputError("AECCTX_STEP_IGES_MESH_INVALID", "Provider mesh is invalid JSON") from error
    vertices = mesh.get("vertices") if isinstance(mesh, dict) else None
    triangles = mesh.get("triangles") if isinstance(mesh, dict) else None
    if not isinstance(mesh, dict) or mesh.get("schema") != "aecctx.triangle-mesh.v1" or not isinstance(vertices, list) or not isinstance(triangles, list):
        raise StepIgesInputError("AECCTX_STEP_IGES_MESH_INVALID", "Provider mesh schema is invalid")
    if not vertices or any(not isinstance(vertex, list) or len(vertex) != 3 or any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) for value in vertex) for vertex in vertices):
        raise StepIgesInputError("AECCTX_STEP_IGES_MESH_INVALID", "Provider mesh vertices are invalid")
    if not triangles or any(not isinstance(triangle, list) or len(triangle) != 3 or any(not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= len(vertices) for index in triangle) for triangle in triangles):
        raise StepIgesInputError("AECCTX_STEP_IGES_MESH_INVALID", "Provider mesh triangle indices are invalid")
    return mesh


def validate_step_iges_events(result: ProviderResult) -> StepIgesEvidence:
    if not result.ok or result.attestation.get("provider_id") != "org.aecctx.step-iges.ocp":
        raise StepIgesInputError("AECCTX_STEP_IGES_PROVIDER_RESULT_INVALID", "Validated successful ACX-17 or ACX-32 provider result required")
    if [item.get("sequence") for item in result.events] != list(range(len(result.events))):
        raise StepIgesInputError("AECCTX_STEP_IGES_EVENT_INVALID", "Provider event sequence is not contiguous")
    sources = [item.get("payload") for item in result.events if item.get("payload", {}).get("schema") == "aecctx.step-iges.source.v1"]
    shapes = [item.get("payload") for item in result.events if item.get("payload", {}).get("schema") == "aecctx.step-iges.shape.v1"]
    xde_events = [item.get("payload") for item in result.events if item.get("payload", {}).get("schema") == "aecctx.step-iges.xde.v1"]
    roots = [item.get("payload") for item in result.events if item.get("payload", {}).get("schema") == "aecctx.step-iges.root.v1"]
    if len(sources) != 1 or not isinstance(sources[0], Mapping):
        raise StepIgesInputError("AECCTX_STEP_IGES_EVENT_INVALID", "Provider result requires exactly one lexical source event")
    legacy = len(shapes) == 1 and not xde_events and not roots
    expanded = not shapes and len(xde_events) == 1 and bool(roots)
    if not legacy and not expanded:
        raise StepIgesInputError("AECCTX_STEP_IGES_EVENT_INVALID", "Provider result must use exactly one legacy shape or one XDE document with per-root events")
    source = sources[0]
    shape = shapes[0] if legacy else next((item for item in roots if isinstance(item, Mapping) and item.get("status") == "success"), None)
    if not isinstance(shape, Mapping):
        raise StepIgesInputError("AECCTX_STEP_IGES_EVENT_INVALID", "Provider result has no successful STEP/IGES root")
    schema = json.loads(files("aecctx.schemas.v0_2").joinpath("step-iges-provider-event.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    for payload in (source, *shapes):
        errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
        if errors:
            location = "/".join(str(item) for item in errors[0].absolute_path) or "<root>"
            raise StepIgesInputError("AECCTX_STEP_IGES_EVENT_INVALID", f"Provider event invalid at {location}: {errors[0].message}")
    if expanded:
        expanded_schema = json.loads(files("aecctx.schemas.v0_2").joinpath("step-iges-xde-event.schema.json").read_text(encoding="utf-8"))
        expanded_validator = Draft202012Validator(expanded_schema)
        for payload in (*xde_events, *roots):
            errors = sorted(expanded_validator.iter_errors(payload), key=lambda error: list(error.absolute_path))
            if errors:
                location = "/".join(str(item) for item in errors[0].absolute_path) or "<root>"
                raise StepIgesInputError("AECCTX_STEP_IGES_EVENT_INVALID", f"Provider XDE/root event invalid at {location}: {errors[0].message}")
        failed = [item for item in roots if isinstance(item, Mapping) and item.get("status") == "failed"]
        completeness = xde_events[0].get("session_completeness") if isinstance(xde_events[0], Mapping) else None
        if (bool(failed) and completeness != "partial") or (not failed and completeness != "complete"):
            raise StepIgesInputError("AECCTX_STEP_IGES_EVENT_INVALID", "XDE session completeness does not match per-root outcomes")
    if source.get("format") not in {"step", "iges"} or shape.get("format") != source.get("format") or any(isinstance(item, Mapping) and item.get("format") != source.get("format") for item in (*xde_events, *roots)):
        raise StepIgesInputError("AECCTX_STEP_IGES_EVENT_INVALID", "Source and shape format mismatch")
    source_items = source.get("entities", source.get("directory", []))
    identifiers = [item.get("id", item.get("sequence")) for item in source_items]
    if len(identifiers) != len(set(identifiers)):
        raise StepIgesInputError("AECCTX_STEP_IGES_EVENT_INVALID", "Provider source identifiers are duplicated")
    if source.get("format") == "step":
        identifier_set = set(identifiers)
        if any(not set(item.get("references", [])).issubset(identifier_set) for item in source_items):
            raise StepIgesInputError("AECCTX_STEP_IGES_EVENT_INVALID", "Provider STEP reference is unresolved")
    successful_roots = [shape] if legacy else [item for item in roots if isinstance(item, Mapping) and item.get("status") == "success"]
    breps: dict[str, bytes] = {}
    meshes: dict[str, Mapping[str, Any]] = {}
    healed_breps: dict[str, bytes] = {}
    for index, root in enumerate(successful_roots, 1):
        root_id = str(root.get("root_id", f"root:{index}"))
        brep_path = root.get("artifact_path")
        mesh_path = root.get("mesh_artifact_path")
        if not isinstance(brep_path, str) or not isinstance(mesh_path, str):
            raise StepIgesInputError("AECCTX_STEP_IGES_ARTIFACT_INVALID", "Successful root requires BREP and mesh artifact paths")
        root_brep = _artifact(result, brep_path, "model/vnd.opencascade.brep")
        if not root_brep.startswith(b"DBRep_DrawableShape"):
            raise StepIgesInputError("AECCTX_STEP_IGES_BREP_INVALID", "Provider BREP header is invalid")
        breps[root_id] = root_brep
        meshes[root_id] = _validate_mesh(result, mesh_path)
        healing = root.get("healing")
        if isinstance(healing, Mapping) and healing.get("applied") is True:
            healed_path = healing.get("artifact_path")
            if not isinstance(healed_path, str):
                raise StepIgesInputError("AECCTX_STEP_IGES_ARTIFACT_INVALID", "Applied healing requires a distinct artifact")
            healed = _artifact(result, healed_path, "model/vnd.opencascade.brep")
            if not healed.startswith(b"DBRep_DrawableShape") or healed_path == brep_path:
                raise StepIgesInputError("AECCTX_STEP_IGES_BREP_INVALID", "Healed BREP must be valid and distinct from raw translator evidence")
            healed_breps[root_id] = healed
    first_id = str(shape.get("root_id", "root:1"))
    return StepIgesEvidence(source, shape, breps[first_id], meshes[first_id], result, xde_events[0] if expanded else {}, tuple(roots) if expanded else (shape,), breps, meshes, healed_breps)
