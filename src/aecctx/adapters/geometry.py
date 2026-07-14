from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from ..geometry import export_deterministic_glb, render_svg_preview, source_to_glb_transform
from ..ingest import CAPABILITIES, IngestResult, _timestamp
from ..mesh_coordinates import CoordinateProfileError, CoordinateSolution, load_coordinate_profile, solve_coordinate_profile
from ..crs import apply_datum_operation, load_crs_registry, validate_crs_identifier
from ..package import PackageArtifact, PackageWriter, canonical_json, hash_file


PLUGIN_ID = "aecctx.adapter.geometry.trimesh"
PLUGIN_VERSION = "0.1.0"


class GeometryDependencyError(RuntimeError):
    code = "AECCTX_GEOMETRY_DEPENDENCY_MISSING"


class GeometryInputError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _trimesh() -> tuple[Any, str]:
    try:
        import trimesh
    except ImportError as error:
        raise GeometryDependencyError("Install AECCTX with the 'geometry' extra to use mesh adapters") from error
    return trimesh, str(trimesh.__version__)


def _stable_id(prefix: str, source_digest: str, key: str) -> str:
    suffix = hashlib.sha256(f"{source_digest}\0{key}".encode()).hexdigest()[:24]
    return f"{prefix}_{suffix}"


def _known(value: Any) -> dict[str, Any]:
    return {"state": "known", "value": value}


def _unknown(reason: str) -> dict[str, str]:
    return {"state": "unknown", "reason_code": reason}


def _qualified_known(value: Any, authority: str) -> dict[str, Any]:
    return {"authority": authority, "state": "known", "value": value}


def _qualified_unknown(reason: str, authority: str) -> dict[str, str]:
    return {"authority": authority, "state": "unknown", "reason_code": reason}


def _provenance(instant: str, parents: list[str], runtime: str, method: str = "trimesh-extraction") -> dict[str, Any]:
    return {
        "method": method,
        "parent_record_ids": sorted(parents),
        "producer_id": PLUGIN_ID,
        "producer_version": f"{PLUGIN_VERSION}+trimesh.{runtime}",
        "recorded_at": instant,
    }


def _matrix(values: Any) -> list[list[float]]:
    return [[round(float(value), 12) for value in row] for row in values]


GLTF_FRAME = {"axes": ["+X", "+Y", "+Z"], "handedness": "right"}


def _source_coordinate_profile(suffix: str) -> tuple[str | None, Mapping[str, Any] | None, str | None]:
    if suffix in {".gltf", ".glb"}:
        return "m", GLTF_FRAME, "2.0"
    return None, None, None


def _safe_v02_scene(trimesh: Any, source: Path) -> tuple[Any, bytes]:
    data = source.read_bytes()
    suffix = source.suffix.lower()
    if suffix == ".gltf":
        try:
            document = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise GeometryInputError("AECCTX_MESH_PARSE_FAILED", f"Invalid glTF JSON: {error}") from error
        if document.get("asset", {}).get("version") != "2.0":
            raise GeometryInputError("AECCTX_MESH_FORMAT_VERSION_UNSUPPORTED", "Only glTF 2.0 is covered by the v0.2 profile")
        uris = [item.get("uri") for key in ("buffers", "images") for item in document.get(key, []) if isinstance(item, dict) and item.get("uri")]
        if any(not isinstance(uri, str) or not uri.startswith("data:") for uri in uris):
            raise GeometryInputError("AECCTX_MESH_EXTERNAL_RESOURCE_UNSUPPORTED", "External glTF resources are not opened")
    try:
        scene = trimesh.load(io.BytesIO(data), file_type=suffix.removeprefix("."), force="scene", process=False, resolver=None)
    except Exception as error:
        raise GeometryInputError("AECCTX_MESH_PARSE_FAILED", f"Mesh parsing failed: {type(error).__name__}") from error
    return scene, data


def _flatten_matrix(values: Any) -> list[float]:
    return [round(float(value), 12) for row in values for value in row]


def _source_qualification(declared_units: str | None, declared_frame: Mapping[str, Any] | None) -> dict[str, Any]:
    return {
        "axis_order": _qualified_known(list(declared_frame["axes"]), "source_declared") if declared_frame else _qualified_unknown("AECCTX_MESH_FRAME_NOT_DECLARED", "source_declared"),
        "declared_units": _qualified_known(declared_units, "source_declared") if declared_units else _qualified_unknown("AECCTX_MESH_UNITS_NOT_DECLARED", "source_declared"),
        "detected_units": _qualified_unknown("AECCTX_MESH_UNIT_GUESSING_PROHIBITED", "detected"),
        "global_location": _unknown("AECCTX_MESH_CRS_NOT_DECLARED"),
        "handedness": _qualified_known(declared_frame["handedness"], "source_declared") if declared_frame else _qualified_unknown("AECCTX_MESH_FRAME_NOT_DECLARED", "source_declared"),
        "transform_chain": [],
    }


def _derived_qualification(profile: Any, solution: CoordinateSolution) -> dict[str, Any]:
    global_location = (
        _known(dict(profile.target_crs))
        if profile.target_crs is not None
        else _unknown("AECCTX_MESH_CRS_NOT_DECLARED")
    )
    qualification: dict[str, Any] = {
        "axis_order": _qualified_known(list(profile.target_frame["axes"]), "manual"),
        "declared_units": _qualified_unknown("AECCTX_MESH_UNITS_NOT_SOURCE_DECLARED", "source_declared"),
        "detected_units": _qualified_unknown("AECCTX_MESH_UNIT_GUESSING_PROHIBITED", "detected"),
        "global_location": global_location,
        "handedness": _qualified_known(profile.target_frame["handedness"], "manual"),
        "manual_units": _qualified_known(profile.target_units, "manual"),
        "transform_chain": [
            {
                "from_frame": "mesh-source",
                "inverse_matrix": list(solution.inverse_matrix or ()),
                "matrix": list(solution.forward_matrix or ()),
                "state": "known",
                "to_frame": "mesh-calibrated",
            }
        ],
    }
    if profile.target_crs is not None:
        qualification["manual_crs"] = _qualified_known(dict(profile.target_crs), "manual")
    return qualification


def _registration_value(solution: CoordinateSolution) -> dict[str, Any]:
    if solution.status == "conflicted":
        return {
            "alternatives": [dict(item) for item in solution.conflicts],
            "reason_code": "AECCTX_MESH_SOURCE_MANUAL_CONFLICT",
            "state": "conflicted",
        }
    detail: dict[str, Any] = {
        "configuration_digest": solution.configuration_digest,
        "determinant": solution.determinant,
        "forward_matrix": list(solution.forward_matrix or ()),
        "inverse_matrix": list(solution.inverse_matrix or ()),
        "transform_class": solution.transform_class,
    }
    for name in ("uniform_scale", "max_residual", "rms_residual"):
        value = getattr(solution, name)
        if value is not None:
            detail[name] = value
    return _known(detail)


class GeometryPlugin:
    def describe(self) -> dict[str, Any]:
        runtime = "not-installed"
        try:
            _, runtime = _trimesh()
        except GeometryDependencyError:
            pass
        return {
            "deterministic": True,
            "distribution_posture": "optional-not-bundled",
            "execution_mode": "in-process-optional",
            "implementation_runtime": f"trimesh/{runtime}",
            "input_capabilities": ["OBJ", "STL", "glTF", "GLB"],
            "license_identifier": "MIT",
            "network_mode": "disabled",
            "output_capabilities": list(CAPABILITIES),
            "plugin_id": PLUGIN_ID,
            "plugin_version": PLUGIN_VERSION,
            "resource_limits": {"bytes": True, "faces": True, "records": True, "wall_time": False, "memory": False},
            "supported_extensions": [".obj", ".stl", ".gltf", ".glb"],
            "supported_media_types": ["model/obj", "model/stl", "model/gltf+json", "model/gltf-binary"],
        }

    def probe(self, prefix: bytes) -> dict[str, Any]:
        bounded = prefix[:64 * 1024]
        stripped = bounded.lstrip()
        if bounded.startswith(b"glTF"):
            detected = "glb"
        elif stripped.startswith(b"{") and b'"asset"' in bounded and b'"version"' in bounded:
            detected = "gltf"
        elif stripped.lower().startswith(b"solid") and b"facet" in bounded.lower():
            detected = "stl"
        elif any(line.startswith(b"v ") for line in bounded.splitlines()) and any(line.startswith(b"f ") for line in bounded.splitlines()):
            detected = "obj"
        else:
            detected = None
        return {
            "confidence": 1.0 if detected else 0.0,
            "format": detected or "unknown",
            "mutated": False,
            "observed_bytes": min(len(prefix), 64 * 1024),
        }

    def extract(self, source_path: str | Path, *, source_id: str) -> Iterable[dict[str, Any]]:
        trimesh, _ = _trimesh()
        scene = trimesh.load(source_path, force="scene", process=False)
        for sequence, (name, mesh) in enumerate(sorted(scene.geometry.items())):
            yield {
                "diagnostics": [],
                "event_type": "primitive",
                "event_version": "0.1",
                "extraction_confidence": {"band": "full", "method": "trimesh-load-process-false"},
                "parent_references": [],
                "payload": {"face_count": len(mesh.faces), "name": name, "vertex_count": len(mesh.vertices)},
                "sequence": sequence,
                "source_id": source_id,
                "source_locator": f"mesh:{name}",
            }

    def render(self, vertices: list[list[float]], faces: list[list[int]], *, view: str = "top") -> bytes:
        return render_svg_preview(vertices, faces, view=view)

    def finalize(self, capabilities: dict[str, str], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "capabilities": capabilities,
            "diagnostic_count": len(diagnostics),
            "network_used": False,
            "plugin_id": PLUGIN_ID,
            "sanitization": ["external-resources-not-fetched", "scripts-not-executed"],
        }


def ingest_geometry(
    source_path: str | Path,
    output_path: str | Path,
    *,
    created_at: str | None = None,
    embedding_policy: str = "external",
    package_form: str = "directory",
    max_faces: int = 5_000_000,
    aecctx_version: str = "0.1.0",
    coordinate_profile: Mapping[str, Any] | None = None,
    crs_profile: Mapping[str, Any] | None = None,
) -> IngestResult:
    trimesh, runtime = _trimesh()
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("source_path must be a regular mesh file")
    if embedding_policy not in {"external", "embedded", "redacted"}:
        raise ValueError("embedding_policy must be external, embedded, or redacted")
    if aecctx_version not in {"0.1.0", "0.2.0"}:
        raise ValueError("aecctx_version must be 0.1.0 or 0.2.0")
    if coordinate_profile is not None and aecctx_version != "0.2.0":
        raise ValueError("coordinate_profile requires aecctx_version of 0.2.0")
    if crs_profile is not None and aecctx_version != "0.2.0":
        raise ValueError("crs_profile requires aecctx_version of 0.2.0")
    if coordinate_profile is not None and crs_profile is not None:
        raise ValueError("coordinate_profile and crs_profile are mutually exclusive")
    source_digest, source_bytes = hash_file(source)
    identity = source_digest[:24]
    source_id = f"src_{identity}"
    package_id = f"pkg_{identity}"
    instant = _timestamp(created_at)
    if aecctx_version == "0.2.0":
        scene, _ = _safe_v02_scene(trimesh, source)
    else:
        scene = trimesh.load(source, force="scene", process=False)
    named_meshes = sorted(scene.geometry.items())
    if not named_meshes:
        raise ValueError("mesh source contains no geometry")
    if sum(len(mesh.faces) for _, mesh in named_meshes) > max_faces:
        raise ValueError("mesh face count exceeds safety limit")

    transformed_meshes = [mesh for _, mesh in named_meshes]
    declared_units, declared_frame, format_version = _source_coordinate_profile(source.suffix.lower())
    loaded_profile = load_coordinate_profile(coordinate_profile) if coordinate_profile is not None else None
    coordinate_solution = (
        solve_coordinate_profile(loaded_profile, declared_units=declared_units, declared_frame=declared_frame)
        if loaded_profile is not None
        else None
    )
    combined = scene.to_geometry()
    vertices = [[round(float(value), 12) for value in row] for row in combined.vertices.tolist()]
    faces = [[int(value) for value in row] for row in combined.faces.tolist()]
    crs_registry = load_crs_registry(crs_profile) if crs_profile is not None else None
    datum_solution = None
    datum_operation = None
    if crs_registry is not None:
        datum_operation = crs_registry.operations["EPSG:1252"]
        validate_crs_identifier(crs_registry, datum_operation.source_crs, require_current=True)
        validate_crs_identifier(crs_registry, datum_operation.target_crs, require_current=True)
        datum_solution = apply_datum_operation(vertices, datum_operation)
    bounds = {
        "max": [round(float(value), 12) for value in combined.bounds[1].tolist()],
        "min": [round(float(value), 12) for value in combined.bounds[0].tolist()],
    }
    glb = export_deterministic_glb(transformed_meshes)
    svg_top = render_svg_preview(vertices, faces, view="top")
    svg_front = render_svg_preview(vertices, faces, view="front")
    glb_path = "geometry/scene.glb"
    svg_top_path = "previews/scene-top.svg"
    svg_front_path = "previews/scene-front.svg"
    transforms = source_to_glb_transform()
    source_units_state = _known(declared_units) if aecctx_version == "0.2.0" and declared_units else _unknown("AECCTX_MESH_UNITS_NOT_DECLARED")
    geometry_refs = [
        {
            "artifact_path": glb_path,
            "bounds": bounds,
            "dimensionality": 3,
            "glb_to_source_transform": transforms["glb_to_source"],
            "media_type": "model/gltf-binary",
            "representation_role": "normalized-exchange",
            "sha256": hashlib.sha256(glb).hexdigest(),
            "source_to_artifact_transform": transforms["source_to_glb"],
            "status": "derived",
            "units": source_units_state,
        },
        {
            "artifact_path": svg_top_path,
            "dimensionality": 2,
            "media_type": "image/svg+xml",
            "representation_role": "top-preview",
            "sha256": hashlib.sha256(svg_top).hexdigest(),
            "status": "preview",
            "units": source_units_state,
        },
        {
            "artifact_path": svg_front_path,
            "dimensionality": 2,
            "media_type": "image/svg+xml",
            "representation_role": "front-preview",
            "sha256": hashlib.sha256(svg_front).hexdigest(),
            "status": "preview",
            "units": source_units_state,
        },
    ]

    record_version = "0.2" if aecctx_version == "0.2.0" else "0.1"
    primitives = []
    entities = []
    for index, (name, mesh) in enumerate(named_meshes, 1):
        primitive_id = _stable_id("prim_mesh", source_digest, name)
        entity_id = _stable_id("entity_mesh", source_digest, name)
        local_vertices = [[round(float(value), 12) for value in row] for row in mesh.vertices.tolist()]
        local_faces = [[int(value) for value in row] for row in mesh.faces.tolist()]
        primitives.append(
            {
                "container": _known(f"mesh:{name}"),
                "extraction_confidence": {"band": "full", "method": "trimesh-process-false"},
                "faces": local_faces,
                "original_class": f"{source.suffix.removeprefix('.').upper()}_MESH",
                "provenance": _provenance(instant, [source_id], runtime),
                "record_id": primitive_id,
                "record_type": "primitive",
                "record_version": record_version,
                "source_refs": [{"locator": f"mesh:{name}", "source_id": source_id}],
                "vertices": local_vertices,
            }
        )
        entities.append(
            {
                "bounds": {
                    "max": [round(float(value), 12) for value in mesh.bounds[1].tolist()],
                    "min": [round(float(value), 12) for value in mesh.bounds[0].tolist()],
                },
                "entity_id": entity_id,
                "geometry_refs": geometry_refs,
                "kind": "aecctx:mesh-object",
                "label": _known(name),
                "original_class": f"{source.suffix.removeprefix('.').upper()}_MESH",
                "parent_evidence_ids": [primitive_id],
                "provenance": _provenance(instant, [primitive_id], runtime, "mesh-neutral-index"),
                "record_id": entity_id,
                "record_type": "entity",
                "record_version": record_version,
                "source_local_identifiers": {"mesh_index": index, "mesh_name": name},
                "source_refs": [{"locator": f"mesh:{name}", "source_id": source_id}],
            }
        )

    if aecctx_version == "0.2.0":
        for edge_index, (parent, child, edge_data) in enumerate(sorted(scene.graph.to_edgelist(), key=lambda item: (str(item[0]), str(item[1])))):
            matrix = edge_data.get("matrix") if isinstance(edge_data, Mapping) else None
            if matrix is None:
                continue
            primitives.append(
                {
                    "extraction_confidence": {"band": "full", "method": "trimesh-scene-graph"},
                    "from_node": str(parent),
                    "matrix": _flatten_matrix(matrix),
                    "original_class": "MESH_SCENE_TRANSFORM",
                    "provenance": _provenance(instant, [source_id], runtime, "trimesh-scene-transform"),
                    "record_id": _stable_id("prim_mesh_transform", source_digest, f"{parent}:{child}:{edge_index}"),
                    "record_type": "primitive",
                    "record_version": record_version,
                    "source_refs": [{"locator": f"scene-graph-edge:{edge_index}", "source_id": source_id}],
                    "to_node": str(child),
                }
            )

    assertions: list[dict[str, Any]] = []
    calibrated_glb: bytes | None = None
    datum_artifact: bytes | None = None
    if loaded_profile is not None and coordinate_solution is not None:
        assertion_id = _stable_id("assert_mesh_coordinate", source_digest, loaded_profile.configuration_digest)
        assertions.append(
            {
                "author": dict(loaded_profile.author),
                "configuration_digest": loaded_profile.configuration_digest,
                "predicate": "aecctx:mesh-coordinate-registration",
                "provenance": _provenance(instant, [source_id], runtime, "manual-coordinate-profile"),
                "record_id": assertion_id,
                "record_type": "assertion",
                "record_version": record_version,
                "source_refs": [{"locator": f"coordinate-profile:sha256:{loaded_profile.configuration_digest}", "source_id": source_id}],
                "value": _registration_value(coordinate_solution),
            }
        )
        if coordinate_solution.status == "known":
            calibrated = combined.copy()
            calibrated.apply_transform(np.asarray(coordinate_solution.forward_matrix, dtype=float).reshape((4, 4)))
            calibrated_glb = export_deterministic_glb([calibrated])
            calibrated_path = "geometry/calibrated-scene.glb"
            calibrated_bounds = {
                "max": [round(float(value), 12) for value in calibrated.bounds[1].tolist()],
                "min": [round(float(value), 12) for value in calibrated.bounds[0].tolist()],
            }
            source_mesh_ids = sorted(item["record_id"] for item in primitives if item.get("original_class", "").endswith("_MESH"))
            derived_id = _stable_id("prim_mesh_calibrated", source_digest, loaded_profile.configuration_digest)
            primitives.append(
                {
                    "artifact_ref": calibrated_path,
                    "bounds": calibrated_bounds,
                    "coordinate_qualification": _derived_qualification(loaded_profile, coordinate_solution),
                    "original_class": "CALIBRATED_MESH",
                    "provenance": _provenance(instant, [assertion_id, *source_mesh_ids], runtime, "manual-coordinate-calibration"),
                    "record_id": derived_id,
                    "record_type": "primitive",
                    "record_version": record_version,
                    "representation_fidelity": {
                        "class": "tessellated",
                        "derived": True,
                        "source_representation_ids": source_mesh_ids,
                    },
                    "source_refs": [{"locator": f"coordinate-profile:sha256:{loaded_profile.configuration_digest}", "source_id": source_id}],
                    "target_frame": dict(loaded_profile.target_frame),
                    "target_units": loaded_profile.target_units,
                    "transform": {
                        "determinant": coordinate_solution.determinant,
                        "forward_matrix": list(coordinate_solution.forward_matrix or ()),
                        "inverse_matrix": list(coordinate_solution.inverse_matrix or ()),
                        "transform_class": coordinate_solution.transform_class,
                    },
                }
            )
            geometry_refs.append(
                {
                    "artifact_path": calibrated_path,
                    "bounds": calibrated_bounds,
                    "dimensionality": 3,
                    "media_type": "model/gltf-binary",
                    "representation_role": "calibrated-exchange",
                    "sha256": hashlib.sha256(calibrated_glb).hexdigest(),
                    "status": "derived",
                    "units": _known(loaded_profile.target_units),
                }
            )

    if crs_registry is not None and datum_solution is not None and datum_operation is not None:
        assertion_id = _stable_id("assert_mesh_datum", source_digest, crs_registry.registry_digest)
        assertion_value = {
            "accuracy": datum_solution.stated_accuracy,
            "accuracy_unit": datum_solution.accuracy_unit,
            "input_digest": datum_solution.input_digest,
            "max_horizontal_residual": datum_solution.max_horizontal_residual,
            "max_vertical_residual": datum_solution.max_vertical_residual,
            "operation_id": datum_solution.operation_id,
            "output_digest": datum_solution.output_digest,
            "registry_digest": datum_solution.registry_digest,
            "source_crs": datum_solution.source_crs,
            "state": "known",
            "target_crs": datum_solution.target_crs,
        }
        assertions.append(
            {
                "author": dict(crs_registry.author),
                "predicate": "aecctx:mesh-datum-operation",
                "provenance": _provenance(instant, [source_id], runtime, "manual-crs-profile"),
                "record_id": assertion_id,
                "record_type": "assertion",
                "record_version": record_version,
                "source_refs": [{"locator": f"crs-registry:sha256:{crs_registry.registry_digest}", "source_id": source_id}],
                "value": assertion_value,
            }
        )
        source_mesh_ids = sorted(item["record_id"] for item in primitives if item.get("original_class", "").endswith("_MESH"))
        transformed_vertices = [list(point) for point in datum_solution.transformed_points or ()]
        derived_id = _stable_id("prim_mesh_datum", source_digest, crs_registry.registry_digest)
        extension = {
            **assertion_value,
            "input_axes": list(datum_solution.input_axes or ()),
            "output_axes": list(datum_solution.output_axes or ()),
            "survey_authority": _unknown("AECCTX_MESH_SURVEY_AUTHORITY_NOT_ESTABLISHED"),
        }
        primitives.append(
            {
                "artifact_ref": "geometry/datum-transformed-mesh.json",
                "extensions": {"aecctx.mesh_crs.v1": extension},
                "faces": faces,
                "original_class": "DATUM_TRANSFORMED_MESH",
                "provenance": _provenance(instant, [assertion_id, *source_mesh_ids], runtime, "offline-datum-operation"),
                "record_id": derived_id,
                "record_type": "primitive",
                "record_version": record_version,
                "representation_fidelity": {
                    "class": "tessellated",
                    "derived": True,
                    "source_representation_ids": source_mesh_ids,
                },
                "source_refs": [{"locator": f"crs-registry:sha256:{crs_registry.registry_digest}", "source_id": source_id}],
                "vertices": transformed_vertices,
            }
        )
        datum_artifact = canonical_json(
            {
                "extensions": {"aecctx.mesh_crs.v1": extension},
                "faces": faces,
                "source_primitive_ids": source_mesh_ids,
                "vertices": transformed_vertices,
            }
        )
    capabilities = {name: "full" for name in CAPABILITIES}
    capabilities.update(
        {
            "hierarchy": "partial",
            "properties": "partial",
            "relationships": "opaque",
            "text": "unsupported",
            "2d_geometry": "partial",
            "materials_styles": "partial",
            "georeferencing": "unsupported",
        }
    )
    if coordinate_solution is not None and coordinate_solution.status == "known" and loaded_profile is not None and loaded_profile.target_crs is not None:
        capabilities["georeferencing"] = "partial"
    if datum_solution is not None:
        capabilities["georeferencing"] = "partial"
    reasons = {
        "hierarchy": "AECCTX_MESH_HIERARCHY_PARTIAL",
        "properties": "AECCTX_MESH_PROPERTIES_PARTIAL",
        "relationships": "AECCTX_MESH_RELATIONSHIPS_OPAQUE",
        "text": "AECCTX_MESH_TEXT_UNSUPPORTED",
        "2d_geometry": "AECCTX_MESH_2D_PREVIEW_ONLY",
        "materials_styles": "AECCTX_MESH_MATERIALS_PARTIAL",
        "georeferencing": (
            "AECCTX_MESH_CALLER_CRS_QUALIFIED_NOT_SURVEYED"
            if datum_solution is not None
            else "AECCTX_MESH_MANUAL_CRS_UNVERIFIED"
            if capabilities["georeferencing"] == "partial"
            else "AECCTX_MESH_GEOREFERENCING_UNSUPPORTED"
        ),
    }
    diagnostics = []
    for capability in CAPABILITIES:
        level = capabilities[capability]
        if level == "full":
            continue
        diagnostics.append(
            {
                "affected_count": len(named_meshes),
                "capability": capability,
                "code": reasons[capability],
                "fallback": "Inspect preserved mesh vertices/faces, bounds, transforms, and source metadata.",
                "message": f"Mesh capability is {level}: {capability}",
                "provenance": _provenance(instant, [source_id], runtime),
                "record_id": _stable_id("diag_mesh_loss", source_digest, capability),
                "record_type": "diagnostic",
                "record_version": record_version,
                "severity": "info",
                "source_refs": [{"locator": "mesh-scene", "source_id": source_id}],
                "support_level": level,
            }
        )
    if declared_units is None:
        diagnostics.append(
            {
                "affected_count": len(named_meshes),
                "capability": "3d_geometry",
                "code": "AECCTX_MESH_UNITS_NOT_DECLARED",
                "fallback": "Supply explicit source-unit calibration in a reviewed adapter configuration.",
                "message": "Mesh coordinates are preserved but construction units are not source-declared.",
                "provenance": _provenance(instant, [source_id], runtime),
                "record_id": _stable_id("diag_mesh_units", source_digest, "units"),
                "record_type": "diagnostic",
                "record_version": record_version,
                "severity": "warning",
                "source_refs": [{"locator": "mesh-scene", "source_id": source_id}],
                "support_level": "partial",
            }
        )
    if coordinate_solution is not None and coordinate_solution.status == "conflicted":
        for conflict in coordinate_solution.conflicts:
            diagnostics.append(
                {
                    "affected_count": len(named_meshes),
                    "capability": "3d_geometry",
                    "code": conflict["reason_code"],
                    "fallback": "Correct the manual profile or preserve the conflict without calibration.",
                    "message": f"Source-declared and manual coordinate metadata conflict for {conflict['field']}.",
                    "provenance": _provenance(instant, [assertions[0]["record_id"]], runtime, "coordinate-conflict-report"),
                    "record_id": _stable_id("diag_mesh_coordinate_conflict", source_digest, str(conflict["field"])),
                    "record_type": "diagnostic",
                    "record_version": record_version,
                    "severity": "warning",
                    "source_refs": [{"locator": f"coordinate-profile:sha256:{coordinate_solution.configuration_digest}", "source_id": source_id}],
                    "support_level": "conflicted",
                }
            )
    diagnostics.append(
        {
            "artifact_paths": sorted([svg_front_path, svg_top_path]),
            "code": "AECCTX_PREVIEW_RENDERED",
            "message": "Deterministic scene top/front SVG previews were rendered from preserved mesh evidence.",
            "provenance": _provenance(instant, [source_id], runtime, "deterministic-svg-render"),
            "record_id": _stable_id("diag_preview", source_digest, "scene-svg"),
            "record_type": "diagnostic",
            "record_version": record_version,
            "severity": "info",
            "source_refs": [{"locator": "mesh-scene", "source_id": source_id}],
        }
    )
    diagnostics.sort(key=lambda item: item["record_id"])
    loss_summary = [reasons[name] for name in CAPABILITIES if capabilities[name] != "full"]
    if declared_units is None:
        loss_summary.append("AECCTX_MESH_UNITS_NOT_DECLARED")
    if coordinate_solution is not None and coordinate_solution.status == "conflicted":
        loss_summary.extend(str(item["reason_code"]) for item in coordinate_solution.conflicts)
    storage_ref = f"sources/content/{source.name}" if embedding_policy == "embedded" else None
    media_type = {".obj": "model/obj", ".stl": "model/stl", ".gltf": "model/gltf+json", ".glb": "model/gltf-binary"}.get(source.suffix.lower(), "application/octet-stream")
    source_record: dict[str, Any] = {
        "acquisition_origin": "local-file",
        "byte_size": source_bytes,
        "declared_format": _known(source.suffix.removeprefix(".").upper()),
        "declared_units": _known(declared_units) if aecctx_version == "0.2.0" and declared_units else _unknown("AECCTX_MESH_UNITS_NOT_DECLARED"),
        "detected_format": _known(source.suffix.removeprefix(".").upper()),
        "detected_producer": _known(f"trimesh/{runtime}"),
        "detected_units": _unknown("AECCTX_MESH_UNITS_NOT_DECLARED"),
        "display_name": source.name,
        "embedding_policy": embedding_policy,
        "extractor": {"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
        "media_type": media_type,
        "prior_source_revision": _unknown("AECCTX_PRIOR_REVISION_NOT_PROVIDED"),
        "provenance": _provenance(instant, [], runtime),
        "record_id": source_id,
        "record_type": "source",
        "record_version": record_version,
        "safety_diagnostics": ["AECCTX_MESH_INPUT_TREATED_AS_DATA", "AECCTX_EXTERNAL_RESOURCES_NOT_FETCHED", "AECCTX_FACE_LIMIT_ENFORCED"],
        "sha256": source_digest,
        "source_id": source_id,
        "source_refs": [],
        "spatial_reference": _unknown("AECCTX_MESH_CRS_NOT_DECLARED" if aecctx_version == "0.2.0" else "AECCTX_MESH_GEOREFERENCING_UNSUPPORTED"),
    }
    if aecctx_version == "0.2.0":
        source_record["coordinate_qualification"] = _source_qualification(declared_units, declared_frame)
        if format_version is not None:
            source_record["format_version"] = format_version
    if storage_ref:
        source_record["storage_ref"] = storage_ref
    elif embedding_policy == "redacted":
        source_record["redaction_reason"] = "AECCTX_SOURCE_CONTENT_REDACTED_BY_POLICY"
    record_sets = {
        "sources/sources.jsonl": [source_record],
        "evidence/primitives.jsonl": primitives,
        "evidence/assertions.jsonl": assertions,
        "model/entities.jsonl": entities,
        "model/relations.jsonl": [],
        "diagnostics/diagnostics.jsonl": diagnostics,
    }
    if aecctx_version == "0.2.0":
        for path, items in record_sets.items():
            evidence_class = "manual" if path == "evidence/assertions.jsonl" else "observed"
            for item in items:
                item.setdefault("evidence_class", "derived" if item.get("original_class") in {"CALIBRATED_MESH", "DATUM_TRANSFORMED_MESH"} else evidence_class)
    artifacts = [
        PackageArtifact(path, b"".join(canonical_json(item) for item in sorted(items, key=lambda value: value["record_id"])), "application/x-ndjson", path.split("/")[-1].removesuffix(".jsonl"), True)
        for path, items in record_sets.items()
    ]
    artifacts.extend(
        [
            PackageArtifact(glb_path, glb, "model/gltf-binary", "normalized-3d-geometry", False),
            PackageArtifact(svg_top_path, svg_top, "image/svg+xml", "top-preview", False),
            PackageArtifact(svg_front_path, svg_front, "image/svg+xml", "front-preview", False),
        ]
    )
    if calibrated_glb is not None:
        artifacts.append(PackageArtifact("geometry/calibrated-scene.glb", calibrated_glb, "model/gltf-binary", "calibrated-3d-geometry", False))
    if datum_artifact is not None:
        artifacts.append(PackageArtifact("geometry/datum-transformed-mesh.json", datum_artifact, "application/json", "datum-transformed-3d-geometry", True))
    unresolved = "Units and CRS are unresolved." if aecctx_version == "0.1.0" else "Coordinate authority and any manual calibration remain explicit in structured records."
    context = (
        f"# Geometry AECCTX package\n\nPackage `{package_id}` preserves {len(named_meshes)} mesh objects, {len(vertices)} vertices, and {len(faces)} triangles. "
        f"GLB and SVG files are derived previews; source vertices/faces and provenance remain authoritative. {unresolved}\n"
    ).encode()
    artifacts.append(PackageArtifact("context/index.md", context, "text/markdown", "agent-context", False))
    if storage_ref:
        artifacts.append(PackageArtifact(storage_ref, source, media_type, "embedded-source", True))
    manifest = PackageWriter(output, package_form=package_form).write(
        package_id=package_id,
        created_at=instant,
        source_ids=[source_id],
        capabilities=capabilities,
        loss_summary=loss_summary,
        embedding_policy=embedding_policy,
        producer={"name": PLUGIN_ID, "version": f"{PLUGIN_VERSION}+trimesh.{runtime}"},
        artifacts=artifacts,
        aecctx_version=aecctx_version,
    )
    return IngestResult(package_id, source_id, manifest["logical_digest"], output)
