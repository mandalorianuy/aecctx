from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from ..geometry import export_deterministic_glb, render_svg_preview, source_to_glb_transform
from ..ingest import CAPABILITIES, IngestResult, _timestamp
from ..package import PackageArtifact, PackageWriter, canonical_json, hash_file


PLUGIN_ID = "aecctx.adapter.geometry.trimesh"
PLUGIN_VERSION = "0.1.0"


class GeometryDependencyError(RuntimeError):
    code = "AECCTX_GEOMETRY_DEPENDENCY_MISSING"


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
) -> IngestResult:
    trimesh, runtime = _trimesh()
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("source_path must be a regular mesh file")
    if embedding_policy not in {"external", "embedded", "redacted"}:
        raise ValueError("embedding_policy must be external, embedded, or redacted")
    source_digest, source_bytes = hash_file(source)
    identity = source_digest[:24]
    source_id = f"src_{identity}"
    package_id = f"pkg_{identity}"
    instant = _timestamp(created_at)
    scene = trimesh.load(source, force="scene", process=False)
    named_meshes = sorted(scene.geometry.items())
    if not named_meshes:
        raise ValueError("mesh source contains no geometry")
    if sum(len(mesh.faces) for _, mesh in named_meshes) > max_faces:
        raise ValueError("mesh face count exceeds safety limit")

    transformed_meshes = [mesh for _, mesh in named_meshes]
    combined = scene.to_geometry()
    vertices = [[round(float(value), 12) for value in row] for row in combined.vertices.tolist()]
    faces = [[int(value) for value in row] for row in combined.faces.tolist()]
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
            "units": _unknown("AECCTX_MESH_UNITS_NOT_DECLARED"),
        },
        {
            "artifact_path": svg_top_path,
            "dimensionality": 2,
            "media_type": "image/svg+xml",
            "representation_role": "top-preview",
            "sha256": hashlib.sha256(svg_top).hexdigest(),
            "status": "preview",
            "units": _unknown("AECCTX_MESH_UNITS_NOT_DECLARED"),
        },
        {
            "artifact_path": svg_front_path,
            "dimensionality": 2,
            "media_type": "image/svg+xml",
            "representation_role": "front-preview",
            "sha256": hashlib.sha256(svg_front).hexdigest(),
            "status": "preview",
            "units": _unknown("AECCTX_MESH_UNITS_NOT_DECLARED"),
        },
    ]

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
                "record_version": "0.1",
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
                "record_version": "0.1",
                "source_local_identifiers": {"mesh_index": index, "mesh_name": name},
                "source_refs": [{"locator": f"mesh:{name}", "source_id": source_id}],
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
    reasons = {
        "hierarchy": "AECCTX_MESH_HIERARCHY_PARTIAL",
        "properties": "AECCTX_MESH_PROPERTIES_PARTIAL",
        "relationships": "AECCTX_MESH_RELATIONSHIPS_OPAQUE",
        "text": "AECCTX_MESH_TEXT_UNSUPPORTED",
        "2d_geometry": "AECCTX_MESH_2D_PREVIEW_ONLY",
        "materials_styles": "AECCTX_MESH_MATERIALS_PARTIAL",
        "georeferencing": "AECCTX_MESH_GEOREFERENCING_UNSUPPORTED",
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
                "record_version": "0.1",
                "severity": "info",
                "source_refs": [{"locator": "mesh-scene", "source_id": source_id}],
                "support_level": level,
            }
        )
    diagnostics.append(
        {
            "affected_count": len(named_meshes),
            "capability": "3d_geometry",
            "code": "AECCTX_MESH_UNITS_NOT_DECLARED",
            "fallback": "Supply explicit source-unit calibration in a reviewed adapter configuration.",
            "message": "Mesh coordinates are preserved but construction units are not declared by this OBJ fixture.",
            "provenance": _provenance(instant, [source_id], runtime),
            "record_id": _stable_id("diag_mesh_units", source_digest, "units"),
            "record_type": "diagnostic",
            "record_version": "0.1",
            "severity": "warning",
            "source_refs": [{"locator": "mesh-scene", "source_id": source_id}],
            "support_level": "partial",
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
            "record_version": "0.1",
            "severity": "info",
            "source_refs": [{"locator": "mesh-scene", "source_id": source_id}],
        }
    )
    diagnostics.sort(key=lambda item: item["record_id"])
    loss_summary = [reasons[name] for name in CAPABILITIES if capabilities[name] != "full"] + ["AECCTX_MESH_UNITS_NOT_DECLARED"]
    storage_ref = f"sources/content/{source.name}" if embedding_policy == "embedded" else None
    media_type = {".obj": "model/obj", ".stl": "model/stl", ".gltf": "model/gltf+json", ".glb": "model/gltf-binary"}.get(source.suffix.lower(), "application/octet-stream")
    source_record: dict[str, Any] = {
        "acquisition_origin": "local-file",
        "byte_size": source_bytes,
        "declared_format": _known(source.suffix.removeprefix(".").upper()),
        "declared_units": _unknown("AECCTX_MESH_UNITS_NOT_DECLARED"),
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
        "record_version": "0.1",
        "safety_diagnostics": ["AECCTX_MESH_INPUT_TREATED_AS_DATA", "AECCTX_EXTERNAL_RESOURCES_NOT_FETCHED", "AECCTX_FACE_LIMIT_ENFORCED"],
        "sha256": source_digest,
        "source_id": source_id,
        "source_refs": [],
        "spatial_reference": _unknown("AECCTX_MESH_GEOREFERENCING_UNSUPPORTED"),
    }
    if storage_ref:
        source_record["storage_ref"] = storage_ref
    elif embedding_policy == "redacted":
        source_record["redaction_reason"] = "AECCTX_SOURCE_CONTENT_REDACTED_BY_POLICY"
    record_sets = {
        "sources/sources.jsonl": [source_record],
        "evidence/primitives.jsonl": primitives,
        "evidence/assertions.jsonl": [],
        "model/entities.jsonl": entities,
        "model/relations.jsonl": [],
        "diagnostics/diagnostics.jsonl": diagnostics,
    }
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
    context = (
        f"# Geometry AECCTX package\n\nPackage `{package_id}` preserves {len(named_meshes)} mesh objects, {len(vertices)} vertices, and {len(faces)} triangles. "
        "GLB and SVG files are derived previews; source vertices/faces and provenance remain authoritative. Units and CRS are unresolved.\n"
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
    )
    return IngestResult(package_id, source_id, manifest["logical_digest"], output)
