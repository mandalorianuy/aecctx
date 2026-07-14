from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from ..ingest import CAPABILITIES, IngestResult, _timestamp
from ..package import PackageArtifact, PackageWriter, canonical_json, hash_file
from ..source_bundle import SourceBundle, SourceBundleEntry, SourceBundleError, load_source_bundle, normalize_source_bundle_path


PLUGIN_ID = "aecctx.adapter.dxf.ezdxf"
PLUGIN_VERSION = "0.1.0"


def _bundle_error(code: str, message: str) -> SourceBundleError:
    return SourceBundleError(code, message)


def _safe_bundle_path(value: object):
    return normalize_source_bundle_path(value, diagnostic_prefix="DXF")


class DXFDependencyError(RuntimeError):
    code = "AECCTX_DXF_DEPENDENCY_MISSING"


class DXFParseError(ValueError):
    code = "AECCTX_DXF_PARSE_FAILED"


class DXFResourceLimitError(ValueError):
    code = "AECCTX_DXF_RESOURCE_LIMIT_EXCEEDED"


def _dxf_container(path: Path) -> str:
    with path.open("rb") as stream:
        return "binary" if stream.read(22).startswith(b"AutoCAD Binary DXF") else "ascii"


def _ezdxf() -> tuple[Any, Any, Any]:
    try:
        import ezdxf
        from ezdxf.lldxf.tagwriter import TagCollector
        from ezdxf.lldxf.const import acad_release
    except ImportError as error:
        raise DXFDependencyError("Install AECCTX with the 'dxf' extra to use the DXF adapter") from error
    return ezdxf, TagCollector, acad_release


def _stable_id(prefix: str, source_digest: str, key: str) -> str:
    suffix = hashlib.sha256(f"{source_digest}\0{key}".encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{suffix}"


def _known(value: Any) -> dict[str, Any]:
    return {"state": "known", "value": value}


def _unknown(reason: str) -> dict[str, str]:
    return {"state": "unknown", "reason_code": reason}


def _explicit_null(reason: str) -> dict[str, str]:
    return {"state": "explicit_null", "reason_code": reason}


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return round(value, 12)
    if hasattr(value, "tolist"):
        return _json_value(value.tolist())
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if hasattr(value, "x") and hasattr(value, "y"):
        result = [round(float(value.x), 12), round(float(value.y), 12)]
        if hasattr(value, "z"):
            result.append(round(float(value.z), 12))
        return result
    return str(value)


def _provenance(instant: str, parents: Iterable[str], runtime_version: str, method: str = "ezdxf-extraction") -> dict[str, Any]:
    return {
        "method": method,
        "parent_record_ids": sorted(parents),
        "producer_id": PLUGIN_ID,
        "producer_version": f"{PLUGIN_VERSION}+ezdxf.{runtime_version}",
        "recorded_at": instant,
    }


def _unit_symbol(unit_code: int) -> str | None:
    return {
        1: "in",
        2: "ft",
        4: "mm",
        5: "cm",
        6: "m",
        7: "km",
    }.get(unit_code)


def _kind(dxftype: str) -> str:
    if dxftype in {"TEXT", "MTEXT", "ATTRIB", "ATTDEF", "DIMENSION"}:
        return "aecctx:annotation"
    if dxftype in {"LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE", "HELIX", "RAY", "XLINE"}:
        return "aecctx:linear-element"
    if dxftype in {"HATCH", "SOLID", "TRACE", "3DFACE"}:
        return "aecctx:surface-element"
    return "aecctx:opaque-object"


def _geometry(entity: Any) -> dict[str, Any]:
    kind = entity.dxftype()
    dxf = entity.dxf
    if kind == "LINE":
        return _known({"end": _json_value(dxf.end), "start": _json_value(dxf.start), "type": "line"})
    if kind == "LWPOLYLINE":
        return _known({"closed": entity.closed, "points": [_json_value(point) for point in entity.get_points("xyseb")], "type": "lwpolyline"})
    if kind == "CIRCLE":
        return _known({"center": _json_value(dxf.center), "radius": round(float(dxf.radius), 12), "type": "circle"})
    if kind == "ARC":
        return _known({"center": _json_value(dxf.center), "end_angle": float(dxf.end_angle), "radius": float(dxf.radius), "start_angle": float(dxf.start_angle), "type": "arc"})
    if kind in {"TEXT", "MTEXT"}:
        insert = dxf.insert if dxf.hasattr("insert") else None
        text = entity.plain_text() if kind == "MTEXT" else dxf.text
        return _known({"insert": _json_value(insert), "text": text, "type": kind.lower()})
    if kind == "INSERT":
        return _known({"block_name": dxf.name, "insert": _json_value(dxf.insert), "rotation": float(dxf.get("rotation", 0.0)), "type": "insert"})
    if kind == "DIMENSION":
        try:
            measurement = round(float(entity.get_measurement()), 12)
        except Exception:
            measurement = None
        return _known({"dimension_type": int(dxf.dimtype), "measurement": measurement, "type": "dimension"})
    if kind == "HATCH":
        return _known({"boundary_path_count": len(entity.paths), "pattern_name": dxf.pattern_name, "solid_fill": bool(dxf.solid_fill), "type": "hatch"})
    if kind in {"SOLID", "TRACE", "3DFACE"}:
        vertices = [_json_value(dxf.get(name)) for name in ("vtx0", "vtx1", "vtx2", "vtx3") if dxf.hasattr(name)]
        return _known({"type": kind.lower(), "vertices": vertices})
    if kind == "POINT":
        return _known({"location": _json_value(dxf.location), "type": "point"})
    return {"state": "unsupported", "reason_code": "AECCTX_DXF_GEOMETRY_NOT_NORMALIZED"}


def _dxf_v03_evidence(entity: Any, *, maximum_vertices: int = 4096) -> dict[str, Any] | None:
    kind = entity.dxftype()
    if kind not in {"ELLIPSE", "SPLINE", "HELIX", "RAY", "XLINE", "MLINE", "MESH"}:
        return None
    dxf = entity.dxf
    if kind == "ELLIPSE":
        source = {
            "center": _json_value(dxf.center),
            "end_param": round(float(dxf.end_param), 12),
            "extrusion": _json_value(dxf.extrusion),
            "major_axis": _json_value(dxf.major_axis),
            "ratio": round(float(dxf.ratio), 12),
            "start_param": round(float(dxf.start_param), 12),
            "type": "ellipse",
        }
    elif kind in {"SPLINE", "HELIX"}:
        source = {
            "control_points": [_json_value(point) for point in entity.control_points],
            "degree": int(dxf.degree),
            "fit_points": [_json_value(point) for point in entity.fit_points],
            "flags": int(dxf.flags),
            "knots": [round(float(value), 12) for value in entity.knots],
            "type": kind.lower(),
            "weights": [round(float(value), 12) for value in entity.weights],
        }
        if kind == "HELIX":
            source["helix"] = {
                "axis_base_point": _json_value(dxf.axis_base_point),
                "axis_vector": _json_value(dxf.axis_vector),
                "constraint": int(dxf.constrain),
                "handedness": int(dxf.handedness),
                "radius": round(float(dxf.radius), 12),
                "start_point": _json_value(dxf.start_point),
                "turn_height": round(float(dxf.turn_height), 12),
                "turns": round(float(dxf.turns), 12),
            }
    elif kind in {"RAY", "XLINE"}:
        source = {"start": _json_value(dxf.start), "type": kind.lower(), "unit_vector": _json_value(dxf.unit_vector)}
    elif kind == "MLINE":
        source = {
            "extrusion": _json_value(dxf.get("extrusion", (0.0, 0.0, 1.0))),
            "justification": int(dxf.get("justification", 0)),
            "scale_factor": round(float(dxf.get("scale_factor", 1.0)), 12),
            "style_name": str(dxf.get("style_name", "")),
            "type": "mline",
            "vertices": [
                {
                    "line_direction": _json_value(vertex.line_direction),
                    "location": _json_value(vertex.location),
                    "miter_direction": _json_value(vertex.miter_direction),
                }
                for vertex in entity.vertices
            ],
        }
    else:
        source = {
            "edges": [list(map(int, edge)) for edge in entity.edges],
            "faces": [list(map(int, face)) for face in entity.faces],
            "type": "mesh",
            "vertices": [_json_value(vertex) for vertex in entity.vertices],
        }
    result: dict[str, Any] = {"source_geometry": _known(source)}
    if kind in {"ELLIPSE", "SPLINE", "HELIX"}:
        try:
            vertices = []
            for point in entity.flattening(0.001, segments=8):
                vertices.append(_json_value(point))
                if len(vertices) > maximum_vertices:
                    raise DXFResourceLimitError("DXF sampled curve exceeds vertex limit")
            result["sampled_path"] = _known(
                {
                    "fidelity": "tessellated",
                    "max_chord_error": 0.001,
                    "minimum_segments": 8,
                    "unit": "drawing-unit",
                    "vertices": vertices,
                }
            )
        except DXFResourceLimitError:
            result["sampled_path"] = {"state": "unsupported", "reason_code": "AECCTX_DXF_CURVE_VERTEX_LIMIT_EXCEEDED"}
        except Exception:
            result["sampled_path"] = {"state": "unsupported", "reason_code": "AECCTX_DXF_CURVE_TESSELLATION_FAILED"}
    else:
        result["sampled_path"] = {"state": "not_applicable", "reason_code": "AECCTX_DXF_UNBOUNDED_OR_SEMANTIC_ENTITY"}
    return result


def _raw_tags(entity: Any, TagCollector: Any, dxfversion: str) -> list[dict[str, Any]]:
    collector = TagCollector(dxfversion=dxfversion)
    entity.export_dxf(collector)
    return [{"code": tag.code, "value": _json_value(tag.value)} for tag in collector.tags]


def _dictionary_entries(dictionary: Any) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for name, value in sorted(dictionary.items(), key=lambda item: item[0]):
        entries[name] = {
            "handle": value.dxf.get("handle") if hasattr(value, "dxf") else str(value),
            "type": value.dxftype() if hasattr(value, "dxftype") else "UNRESOLVED_HANDLE",
        }
    return entries


def _extension_dictionary(entity: Any) -> dict[str, Any]:
    if not entity.has_extension_dict:
        return _explicit_null("AECCTX_DXF_EXTENSION_DICTIONARY_NOT_PRESENT")
    extension = entity.get_extension_dict()
    dictionary = extension.dictionary
    return _known(
        {
            "entries": _dictionary_entries(dictionary),
            "handle": dictionary.dxf.get("handle"),
            "owner_handle": dictionary.dxf.get("owner"),
        }
    )


def _matrix44_values(matrix: Any) -> list[float]:
    values = [float(value) for value in matrix]
    if len(values) != 16 or not all(math.isfinite(value) for value in values):
        raise ValueError("DXF transform matrix must contain 16 finite values")
    return [round(value, 12) for value in values]


def _dxf_geometry_3d(entity: Any) -> dict[str, Any] | None:
    from ezdxf.math import Matrix44, OCS

    kind = entity.dxftype()
    dxf = entity.dxf
    if kind == "POINT":
        return {"coordinate_space": "wcs", "dimensionality": 3, "location": _json_value(dxf.location)}
    if kind == "LINE":
        return {
            "coordinate_space": "wcs",
            "dimensionality": 3,
            "end": _json_value(dxf.end),
            "start": _json_value(dxf.start),
        }
    if kind == "3DFACE":
        return {
            "coordinate_space": "wcs",
            "dimensionality": 3,
            "vertices": [_json_value(dxf.get(name)) for name in ("vtx0", "vtx1", "vtx2", "vtx3")],
        }
    if kind == "MESH":
        return {
            "coordinate_space": "wcs",
            "dimensionality": 3,
            "edges": [list(map(int, edge)) for edge in entity.edges],
            "faces": [list(map(int, face)) for face in entity.faces],
            "vertices": [_json_value(vertex) for vertex in entity.vertices],
        }
    if kind == "POLYLINE":
        vertices = [_json_value(vertex.dxf.location) for vertex in entity.vertices]
        if entity.is_3d_polyline:
            return {"coordinate_space": "wcs", "dimensionality": 3, "mode": "3d-polyline", "vertices": vertices}
        if entity.is_polygon_mesh:
            m_count = int(entity.dxf.m_count)
            n_count = int(entity.dxf.n_count)
            faces = [
                [m * n_count + n, (m + 1) * n_count + n, (m + 1) * n_count + n + 1, m * n_count + n + 1]
                for m in range(max(0, m_count - 1))
                for n in range(max(0, n_count - 1))
            ]
            return {
                "coordinate_space": "wcs",
                "dimensionality": 3,
                "faces": faces,
                "mode": "polygon-mesh",
                "vertices": vertices,
            }
        if entity.is_poly_face_mesh:
            unique_vertices: list[list[float]] = []
            index_by_vertex: dict[tuple[float, float, float], int] = {}
            faces: list[list[int]] = []
            for native_face in entity.faces():
                face: list[int] = []
                for vertex in native_face:
                    point = tuple(float(value) for value in vertex.dxf.location)
                    if face and point == tuple(unique_vertices[face[0]]) and len(face) >= 3:
                        continue
                    if point not in index_by_vertex:
                        index_by_vertex[point] = len(unique_vertices)
                        unique_vertices.append([round(value, 12) for value in point])
                    face.append(index_by_vertex[point])
                if len(face) >= 3:
                    faces.append(face)
            return {
                "coordinate_space": "wcs",
                "dimensionality": 3,
                "faces": faces,
                "mode": "polyface-mesh",
                "vertices": unique_vertices,
            }
        return None
    if kind == "INSERT":
        return {
            "block_name": dxf.name,
            "coordinate_space": "wcs",
            "dimensionality": 3,
            "extrusion": _json_value(dxf.get("extrusion", (0.0, 0.0, 1.0))),
            "insert": _json_value(dxf.insert),
            "insert_matrix": _matrix44_values(entity.matrix44()),
            "nested_instances": [],
        }
    if kind in {"CIRCLE", "ARC", "LWPOLYLINE", "SOLID", "TRACE"}:
        extrusion = dxf.get("extrusion", (0.0, 0.0, 1.0))
        ocs = OCS(extrusion)
        geometry: dict[str, Any] = {
            "coordinate_space": "ocs",
            "dimensionality": 3,
            "extrusion": _json_value(extrusion),
            "ocs_to_wcs_matrix": _matrix44_values(getattr(ocs, "matrix", Matrix44())),
        }
        if dxf.hasattr("center"):
            geometry["center_ocs"] = _json_value(dxf.center)
            geometry["center_wcs"] = _json_value(ocs.to_wcs(dxf.center))
        if dxf.hasattr("elevation"):
            geometry["elevation"] = _json_value(dxf.elevation)
        return geometry
    return None


def _triangulate_geometry(geometry: dict[str, Any]) -> tuple[list[list[float]], list[list[int]]]:
    vertices = [list(map(float, point)) for point in geometry.get("vertices", [])]
    faces = geometry.get("faces", [])
    triangles: list[list[int]] = []
    for face in faces:
        if len(face) < 3:
            continue
        triangles.extend([[int(face[0]), int(face[index]), int(face[index + 1])] for index in range(1, len(face) - 1)])
    if not faces and len(vertices) in {3, 4}:
        triangles = [[0, 1, 2]] + ([[0, 2, 3]] if len(vertices) == 4 else [])
    return vertices, triangles


class DXFPlugin:
    def describe(self) -> dict[str, Any]:
        runtime = "not-installed"
        try:
            runtime = str(_ezdxf()[0].__version__)
        except DXFDependencyError:
            pass
        return {
            "deterministic": True,
            "distribution_posture": "optional-not-bundled",
            "execution_mode": "in-process-optional",
            "implementation_runtime": f"ezdxf/{runtime}",
            "input_capabilities": ["ASCII DXF", "Binary DXF"],
            "license_identifier": "MIT",
            "network_mode": "disabled",
            "output_capabilities": list(CAPABILITIES),
            "plugin_id": PLUGIN_ID,
            "plugin_version": PLUGIN_VERSION,
            "resource_limits": {"bytes": True, "records": True, "wall_time": False, "memory": False},
            "supported_extensions": [".dxf"],
            "supported_media_types": ["application/dxf", "application/x-dxf"],
            "v02_public_profiles": {
                "bounded_3d": "dxf-r2000-r2018-bounded-3d-v1:partial",
                "source_semantics": "dxf-r2000-r2018-source-semantics-v1:partial",
            },
            "v03_public_profiles": {
                "geometry": "dxf-selected-releases-geometry-v03:partial",
                "source_semantics": "dxf-selected-releases-source-semantics-v03:partial",
                "source_bundle": "dxf-content-addressed-xref-bundle-v1:partial",
            },
        }

    def probe(self, prefix: bytes) -> dict[str, Any]:
        bounded = prefix[:64 * 1024]
        binary = bounded.startswith(b"AutoCAD Binary DXF")
        ascii_dxf = b"SECTION" in bounded and (b"$ACADVER" in bounded or b"HEADER" in bounded)
        return {
            "confidence": 1.0 if binary or ascii_dxf else 0.0,
            "format": "dxf-binary" if binary else "dxf-ascii" if ascii_dxf else "unknown",
            "mutated": False,
            "observed_bytes": min(len(prefix), 64 * 1024),
        }

    def extract(self, source_path: str | Path, *, source_id: str) -> Iterable[dict[str, Any]]:
        ezdxf, _, _ = _ezdxf()
        document = ezdxf.readfile(source_path)
        sequence = 0
        seen: set[str] = set()
        for layout in document.layouts:
            for entity in layout:
                handle = entity.dxf.get("handle", f"layout-{layout.name}-{sequence}")
                if handle in seen:
                    continue
                seen.add(handle)
                yield {
                    "diagnostics": [],
                    "event_type": "primitive",
                    "event_version": "0.1",
                    "extraction_confidence": {"band": "full", "method": "ezdxf"},
                    "parent_references": [],
                    "payload": {"dxf_type": entity.dxftype(), "handle": handle},
                    "sequence": sequence,
                    "source_id": source_id,
                    "source_locator": f"layout:{layout.name}/handle:{handle}",
                }
                sequence += 1

    def finalize(self, capabilities: dict[str, str], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "capabilities": capabilities,
            "diagnostic_count": len(diagnostics),
            "network_used": False,
            "plugin_id": PLUGIN_ID,
            "sanitization": ["links-not-followed", "commands-not-executed", "xrefs-not-opened"],
        }


def ingest_dxf(
    source_path: str | Path,
    output_path: str | Path,
    *,
    created_at: str | None = None,
    embedding_policy: str = "external",
    package_form: str = "directory",
    aecctx_version: str = "0.1.0",
    max_source_bytes: int = 512 * 1024 * 1024,
    max_records: int = 1_000_000,
    max_xref_depth: int = 8,
) -> IngestResult:
    ezdxf, TagCollector, acad_release = _ezdxf()
    requested_source = Path(source_path)
    source_bundle: SourceBundle | None = None
    if requested_source.is_dir() and not requested_source.is_symlink():
        if aecctx_version != "0.2.0":
            raise ValueError("DXF source bundles require aecctx_version=0.2.0")
        source_bundle = load_source_bundle(requested_source, max_member_bytes=max_source_bytes)
        source = source_bundle.root.path
    else:
        source = requested_source
    output = Path(output_path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("source_path must be a regular DXF file")
    if embedding_policy not in {"external", "embedded", "redacted"}:
        raise ValueError("embedding_policy must be external, embedded, or redacted")
    if aecctx_version not in {"0.1.0", "0.2.0"}:
        raise ValueError("aecctx_version must be 0.1.0 or 0.2.0")
    if max_source_bytes < 1 or max_records < 1 or not 1 <= max_xref_depth <= 8:
        raise ValueError("DXF safety limits must be positive")
    if source.stat().st_size > max_source_bytes:
        error = DXFResourceLimitError(f"DXF source exceeds {max_source_bytes} bytes")
        error.code = "AECCTX_DXF_SOURCE_SIZE_LIMIT_EXCEEDED"
        raise error
    source_digest, source_bytes = hash_file(source)
    dxf_container = _dxf_container(source)
    identity = source_digest[:24]
    source_id = f"src_{identity}"
    package_id = f"pkg_{identity}"
    instant = _timestamp(created_at)
    try:
        document = ezdxf.readfile(source)
    except Exception as error:
        raise DXFParseError(f"DXF parse failed: {type(error).__name__}: {error}") from error
    if len(document.entitydb) > max_records:
        error = DXFResourceLimitError(f"DXF entity/object count exceeds {max_records}")
        error.code = "AECCTX_DXF_RECORD_LIMIT_EXCEEDED"
        raise error
    runtime_version = str(ezdxf.__version__)
    audit = document.audit()
    unit = _unit_symbol(int(document.units))

    bundle_documents: list[tuple[SourceBundleEntry, Any]] = []
    if source_bundle is not None:
        by_path = source_bundle.by_path
        visited_documents: set[str] = set()

        def declared_xrefs(native_document: Any) -> list[str]:
            paths = {
                str(block.block.dxf.get("xref_path", ""))
                for block in native_document.blocks
                if block.block_record.is_xref and block.block.dxf.get("xref_path", "")
            }
            return sorted(paths)

        def visit(entry: SourceBundleEntry, native_document: Any, stack: tuple[str, ...]) -> None:
            if entry.logical_path in stack:
                raise _bundle_error("AECCTX_DXF_BUNDLE_XREF_CYCLE", f"DXF xref cycle at {entry.logical_path}")
            if entry.logical_path in visited_documents:
                return
            next_stack = (*stack, entry.logical_path)
            if len(next_stack) > max_xref_depth + 1:
                raise _bundle_error("AECCTX_DXF_BUNDLE_XREF_DEPTH_EXCEEDED", f"DXF xref depth exceeds {max_xref_depth}")
            bundle_documents.append((entry, native_document))
            visited_documents.add(entry.logical_path)
            for declared in declared_xrefs(native_document):
                logical = _safe_bundle_path(declared).as_posix()
                child = by_path.get(logical)
                if child is None or child.role != "xref":
                    raise _bundle_error("AECCTX_DXF_BUNDLE_XREF_UNDECLARED", f"DXF xref is not in source bundle: {logical}")
                if logical in next_stack:
                    raise _bundle_error("AECCTX_DXF_BUNDLE_XREF_CYCLE", f"DXF xref cycle at {logical}")
                try:
                    child_document = ezdxf.readfile(child.path)
                except Exception as error:
                    raise _bundle_error("AECCTX_DXF_BUNDLE_XREF_PARSE_FAILED", f"DXF xref parse failed: {logical}") from error
                visit(child, child_document, next_stack)

        visit(source_bundle.root, document, ())
        visited = {entry.logical_path for entry, _native in bundle_documents}
        undeclared = sorted(entry.logical_path for entry in source_bundle.entries if entry.role == "xref" and entry.logical_path not in visited)
        if undeclared:
            raise _bundle_error("AECCTX_DXF_BUNDLE_XREF_UNREACHABLE", f"Unreachable source-bundle xrefs: {', '.join(undeclared)}")

    container_by_handle: dict[str, str] = {}
    graphical: dict[str, Any] = {}
    for layout in document.layouts:
        for entity in layout:
            handle = entity.dxf.get("handle")
            if handle:
                graphical[handle] = entity
                container_by_handle[handle] = f"layout:{layout.name}"
            if aecctx_version == "0.2.0" and entity.dxftype() == "INSERT":
                for attribute in entity.attribs:
                    attribute_handle = attribute.dxf.get("handle")
                    if attribute_handle:
                        graphical[attribute_handle] = attribute
                        container_by_handle[attribute_handle] = f"layout:{layout.name}/insert:{handle}"
    for block in document.blocks:
        if block.block_record.is_any_layout:
            continue
        for entity in block:
            handle = entity.dxf.get("handle")
            if handle and handle not in graphical:
                graphical[handle] = entity
                container_by_handle[handle] = f"block:{block.name}"

    primitives: list[dict[str, Any]] = []
    entity_records: list[dict[str, Any]] = []
    entity_ids: dict[str, str] = {}
    unsupported_handles: list[str] = []
    for handle, entity in sorted(graphical.items()):
        primitive_id = _stable_id("prim_dxf", source_digest, handle)
        entity_id = _stable_id("entity_dxf", source_digest, handle)
        entity_ids[handle] = entity_id
        raw_tags = _raw_tags(entity, TagCollector, document.dxfversion)
        xdata: dict[str, list[dict[str, Any]]] = {}
        for appid in sorted(document.appids, key=lambda item: item.dxf.name):
            appid_name = appid.dxf.name
            if entity.has_xdata(appid_name):
                xdata[appid_name] = [{"code": tag.code, "value": _json_value(tag.value)} for tag in entity.get_xdata(appid_name)]
        geometry = _geometry(entity)
        if geometry["state"] == "unsupported":
            unsupported_handles.append(handle)
        locator = f"{container_by_handle[handle]}/handle:{handle}"
        primitive = {
            "container": _known(container_by_handle[handle]),
            "extraction_confidence": {"band": "full", "method": "ezdxf-entity-tags"},
            "geometry": geometry,
            "handle": handle,
            "layer": _known(entity.dxf.get("layer", "0")),
            "original_class": entity.dxftype(),
            "provenance": _provenance(instant, [source_id], runtime_version),
            "raw_tags": raw_tags,
            "record_id": primitive_id,
            "record_type": "primitive",
            "record_version": "0.1",
            "source_refs": [{"locator": locator, "source_id": source_id}],
        }
        if xdata:
            primitive["xdata"] = xdata
        if aecctx_version == "0.2.0":
            owner = entity.dxf.get("owner")
            material_handle = entity.dxf.get("material_handle")
            primitive["owner_handle"] = _known(owner) if owner else _unknown("AECCTX_DXF_OWNER_HANDLE_NOT_RESOLVED")
            primitive["material_handle"] = (
                _known(material_handle) if material_handle else _explicit_null("AECCTX_DXF_MATERIAL_HANDLE_NOT_PRESENT")
            )
            primitive["extension_dictionary"] = _extension_dictionary(entity)
            if entity.dxftype() in {"ATTRIB", "ATTDEF"}:
                primitive["attribute"] = {
                    "tag": entity.dxf.get("tag", ""),
                    "text": entity.dxf.get("text", ""),
                }
            geometry_3d = _dxf_geometry_3d(entity)
            if geometry_3d is not None:
                primitive["geometry_3d"] = geometry_3d
                primitive["representation_fidelity"] = {
                    "class": "source_exact",
                    "derived": False,
                    "source_representation_ids": [primitive_id],
                }
            if document.dxfversion in {"AC1009", "AC1015", "AC1018", "AC1021", "AC1032"}:
                v03 = _dxf_v03_evidence(entity)
                if v03 is not None:
                    primitive["dxf_v03"] = v03
        primitives.append(primitive)
        entity_records.append(
            {
                "entity_id": entity_id,
                "kind": _kind(entity.dxftype()),
                "label": _known(entity.dxf.get("text")) if entity.dxftype() == "TEXT" else _unknown("AECCTX_DXF_LABEL_NOT_APPLICABLE"),
                "original_class": entity.dxftype(),
                "parent_evidence_ids": [primitive_id],
                "provenance": _provenance(instant, [primitive_id], runtime_version, "dxf-neutral-index"),
                "record_id": entity_id,
                "record_type": "entity",
                "record_version": "0.1",
                "source_local_identifiers": {"dxf_handle": handle, "layout_or_block": container_by_handle[handle]},
                "source_refs": [{"locator": locator, "source_id": source_id}],
            }
        )

    if aecctx_version == "0.2.0":
        group_names = {group.dxf.handle: name for name, group in document.groups}
        dictionary_names: dict[str, str] = {document.rootdict.dxf.handle: "ROOT"}
        for dictionary in (item for item in document.objects if item.dxftype() == "DICTIONARY"):
            for name, value in dictionary.items():
                if hasattr(value, "dxf") and value.dxf.get("handle"):
                    dictionary_names.setdefault(value.dxf.handle, name)
        for native in sorted(document.objects, key=lambda item: item.dxf.get("handle", "")):
            handle = native.dxf.get("handle")
            if not handle:
                continue
            primitive_id = _stable_id("prim_dxf_object", source_digest, handle)
            locator = f"objects/handle:{handle}"
            primitive: dict[str, Any] = {
                "container": _known("objects-section"),
                "extraction_confidence": {"band": "full", "method": "ezdxf-object-tags"},
                "extension_dictionary": _extension_dictionary(native),
                "geometry": {"state": "unsupported", "reason_code": "AECCTX_DXF_OBJECT_HAS_NO_NORMALIZED_GEOMETRY"},
                "handle": handle,
                "original_class": native.dxftype(),
                "owner_handle": _known(native.dxf.get("owner")) if native.dxf.get("owner") else _unknown("AECCTX_DXF_OWNER_HANDLE_NOT_RESOLVED"),
                "provenance": _provenance(instant, [source_id], runtime_version, "ezdxf-object-extraction"),
                "raw_tags": _raw_tags(native, TagCollector, document.dxfversion),
                "record_id": primitive_id,
                "record_type": "primitive",
                "record_version": "0.2",
                "source_refs": [{"locator": locator, "source_id": source_id}],
            }
            if native.dxftype() == "DICTIONARY":
                primitive["dictionary"] = {
                    "entries": _dictionary_entries(native),
                    "hard_owned": bool(native.dxf.get("hard_owned", 0)),
                    "name": dictionary_names.get(handle, ""),
                }
            elif native.dxftype() == "XRECORD":
                primitive["xrecord_tags"] = [{"code": tag.code, "value": _json_value(tag.value)} for tag in native.tags]
            elif native.dxftype() == "GROUP":
                primitive["group"] = {
                    "description": native.dxf.get("description", ""),
                    "member_handles": sorted(native.handles()),
                    "name": group_names.get(handle, ""),
                    "selectable": bool(native.dxf.get("selectable", 1)),
                }
            elif native.dxftype() == "MATERIAL":
                primitive["material"] = {
                    "description": native.dxf.get("description", ""),
                    "handle": handle,
                    "name": native.dxf.get("name", ""),
                }
            primitives.append(primitive)

        for appid in sorted(document.appids, key=lambda item: item.dxf.name):
            handle = appid.dxf.get("handle")
            if not handle:
                continue
            primitives.append(
                {
                    "application_id": {"handle": handle, "name": appid.dxf.name},
                    "container": _known("table:APPID"),
                    "extraction_confidence": {"band": "full", "method": "ezdxf-table-record"},
                    "geometry": {"state": "not_applicable", "reason_code": "AECCTX_DXF_TABLE_RECORD_NOT_GEOMETRY"},
                    "handle": handle,
                    "original_class": "APPID",
                    "owner_handle": _known(appid.dxf.get("owner")) if appid.dxf.get("owner") else _unknown("AECCTX_DXF_OWNER_HANDLE_NOT_RESOLVED"),
                    "provenance": _provenance(instant, [source_id], runtime_version, "ezdxf-appid-extraction"),
                    "raw_tags": _raw_tags(appid, TagCollector, document.dxfversion),
                    "record_id": _stable_id("prim_dxf_appid", source_digest, handle),
                    "record_type": "primitive",
                    "record_version": "0.2",
                    "source_refs": [{"locator": f"table:APPID/handle:{handle}", "source_id": source_id}],
                }
            )

    v02_geometry_artifacts: list[PackageArtifact] = []
    v02_3d_issues: list[tuple[str, str]] = []
    if aecctx_version == "0.2.0":
        from ezdxf.math import Matrix44

        primitive_by_handle = {record.get("handle"): record for record in primitives if record.get("handle")}
        mesh_vertices: list[list[float]] = []
        mesh_faces: list[list[int]] = []
        mesh_sources: list[str] = []

        def add_mesh(entity: Any, transform: Any) -> None:
            geometry = _dxf_geometry_3d(entity)
            if geometry is None:
                return
            if entity.dxftype() == "3DFACE":
                geometry = {"vertices": geometry["vertices"]}
            vertices, faces = _triangulate_geometry(geometry)
            if not vertices or not faces:
                return
            transformed = [_json_value(transform.transform(vertex)) for vertex in vertices]
            offset = len(mesh_vertices)
            mesh_vertices.extend(transformed)
            mesh_faces.extend([[offset + index for index in face] for face in faces])
            handle = entity.dxf.get("handle")
            if handle:
                mesh_sources.append(_stable_id("prim_dxf", source_digest, handle))

        def walk_insert(root: Any, current: Any, transform: Any, block_path: list[str]) -> None:
            block_name = current.dxf.name
            if block_name in block_path:
                v02_3d_issues.append(("AECCTX_DXF_INSERT_CYCLE", current.dxf.get("handle", block_name)))
                return
            next_path = [*block_path, block_name]
            if len(next_path) > 32:
                v02_3d_issues.append(("AECCTX_DXF_INSERT_DEPTH_LIMIT", current.dxf.get("handle", block_name)))
                return
            try:
                next_transform = current.matrix44() @ transform
                _matrix44_values(next_transform)
            except Exception:
                v02_3d_issues.append(("AECCTX_DXF_INSERT_TRANSFORM_UNSUPPORTED", current.dxf.get("handle", block_name)))
                return
            try:
                block = document.blocks.get(block_name)
            except Exception:
                v02_3d_issues.append(("AECCTX_DXF_INSERT_BLOCK_MISSING", current.dxf.get("handle", block_name)))
                return
            root_record = primitive_by_handle.get(root.dxf.get("handle"))
            for child in block:
                if child.dxftype() == "INSERT":
                    walk_insert(root, child, next_transform, next_path)
                    continue
                geometry = _dxf_geometry_3d(child)
                if geometry is None:
                    continue
                if root_record is not None and child.dxftype() in {"3DFACE", "MESH", "POLYLINE"}:
                    root_record["geometry_3d"]["nested_instances"].append(
                        {
                            "block_path": next_path,
                            "entity_class": child.dxftype(),
                            "entity_handle": child.dxf.get("handle"),
                            "transform_state": "known",
                        }
                    )
                add_mesh(child, next_transform)

        identity = Matrix44()
        for entity in document.modelspace():
            if entity.dxftype() == "INSERT":
                walk_insert(entity, entity, identity, [])
            elif entity.dxftype() in {"3DFACE", "MESH", "POLYLINE"}:
                add_mesh(entity, identity)

        if mesh_faces:
            import numpy
            import trimesh

            from ..geometry import export_deterministic_glb, source_to_glb_transform

            source_ids = sorted(set(mesh_sources))
            mesh_payload = {
                "coordinate_space": "dxf-wcs",
                "faces": mesh_faces,
                "fidelity": "tessellated",
                "source_record_ids": source_ids,
                "source_to_artifact_transform": source_to_glb_transform()["source_to_glb"],
                "tolerance": {"state": "known", "value": 1e-9, "unit": unit or "drawing-unit"},
                "vertices": mesh_vertices,
            }
            mesh_bytes = canonical_json(mesh_payload)
            mesh_path = "geometry/dxf/bounded-profile-mesh.json"
            glb_path = "geometry/dxf/bounded-profile.glb"
            try:
                source_mesh = trimesh.Trimesh(
                    vertices=numpy.asarray(mesh_vertices, dtype=float),
                    faces=numpy.asarray(mesh_faces, dtype=int),
                    process=False,
                )
                glb_bytes = export_deterministic_glb([source_mesh])
            except Exception as error:
                glb_bytes = b""
                v02_3d_issues.append(("AECCTX_DXF_GLB_EXPORT_FAILED", type(error).__name__))
            v02_geometry_artifacts.append(
                PackageArtifact(mesh_path, mesh_bytes, "application/vnd.aecctx.dxf-mesh+json", "dxf-derived-tessellation", False)
            )
            artifact_refs = [
                {
                    "artifact_path": mesh_path,
                    "media_type": "application/vnd.aecctx.dxf-mesh+json",
                    "sha256": hashlib.sha256(mesh_bytes).hexdigest(),
                }
            ]
            if glb_bytes:
                v02_geometry_artifacts.append(PackageArtifact(glb_path, glb_bytes, "model/gltf-binary", "dxf-derived-glb", False))
                artifact_refs.append(
                    {
                        "artifact_path": glb_path,
                        "media_type": "model/gltf-binary",
                        "sha256": hashlib.sha256(glb_bytes).hexdigest(),
                    }
                )
            primitives.append(
                {
                    "artifact_refs": artifact_refs,
                    "container": _known("dxf-derived-geometry"),
                    "evidence_class": "derived",
                    "extraction_confidence": {"band": "full", "method": "aecctx-deterministic-dxf-tessellation"},
                    "original_class": "AECCTXDerivedDXFTessellation",
                    "provenance": _provenance(instant, source_ids, runtime_version, "aecctx-deterministic-dxf-tessellation"),
                    "record_id": _stable_id("prim_dxf_tessellation", source_digest, "bounded-profile"),
                    "record_type": "primitive",
                    "record_version": "0.2",
                    "representation_fidelity": {
                        "class": "tessellated",
                        "derived": True,
                        "source_representation_ids": source_ids,
                    },
                    "source_refs": [{"locator": "dxf-derived-geometry:bounded-profile", "source_id": source_id}],
                }
            )

    block_ids: dict[str, str] = {}
    for block in sorted(document.blocks, key=lambda item: item.name):
        if block.block_record.is_any_layout:
            continue
        block_id = _stable_id("entity_dxf_block", source_digest, block.name)
        block_ids[block.name] = block_id
        entity_records.append(
            {
                "block": {
                    "base_point": _json_value(block.block.dxf.base_point),
                    "is_anonymous": bool(block.block.is_anonymous),
                    "is_xref": bool(block.block_record.is_xref),
                    "name": block.name,
                    "xref_path": block.block.dxf.get("xref_path", ""),
                },
                "entity_id": block_id,
                "kind": "aecctx:opaque-object",
                "label": _known(block.name),
                "original_class": "DXF_BLOCK_DEFINITION",
                "parent_evidence_ids": [],
                "provenance": _provenance(instant, [source_id], runtime_version, "dxf-block-index"),
                "record_id": block_id,
                "record_type": "entity",
                "record_version": "0.1",
                "source_local_identifiers": {"block_name": block.name},
                "source_refs": [{"locator": f"block:{block.name}", "source_id": source_id}],
            }
        )

    layer_ids: dict[str, str] = {}
    for layer in sorted(document.layers, key=lambda item: item.dxf.name):
        layer_id = _stable_id("entity_dxf_layer", source_digest, layer.dxf.name)
        layer_ids[layer.dxf.name] = layer_id
        entity_records.append(
            {
                "entity_id": layer_id,
                "kind": "aecctx:opaque-object",
                "label": _known(layer.dxf.name),
                "layer": {"color": layer.color, "linetype": layer.dxf.linetype, "name": layer.dxf.name},
                "original_class": "DXF_LAYER",
                "parent_evidence_ids": [],
                "provenance": _provenance(instant, [source_id], runtime_version, "dxf-layer-index"),
                "record_id": layer_id,
                "record_type": "entity",
                "record_version": "0.1",
                "source_local_identifiers": {"layer_name": layer.dxf.name},
                "source_refs": [{"locator": f"table:LAYER/name:{layer.dxf.name}", "source_id": source_id}],
            }
        )

    relations: list[dict[str, Any]] = []
    for handle, entity in sorted(graphical.items()):
        if entity.dxftype() == "INSERT" and entity.dxf.name in block_ids:
            relation_id = _stable_id("relation_dxf_insert", source_digest, handle)
            relations.append(
                {
                    "endpoints": [
                        {"record_id": entity_ids[handle], "role": "insert"},
                        {"record_id": block_ids[entity.dxf.name], "role": "block-definition"},
                    ],
                    "evidence_record_ids": [_stable_id("prim_dxf", source_digest, handle)],
                    "original_class": "INSERT",
                    "provenance": _provenance(instant, [_stable_id("prim_dxf", source_digest, handle)], runtime_version),
                    "record_id": relation_id,
                    "record_type": "relation",
                    "record_version": "0.1",
                    "relation_id": relation_id,
                    "relation_type": "aecctx:representation",
                    "source_refs": [{"locator": f"{container_by_handle[handle]}/handle:{handle}", "source_id": source_id}],
                }
            )

    assertions: list[dict[str, Any]] = []
    for handle, entity in sorted(graphical.items()):
        layer = entity.dxf.get("layer", "0")
        assertion_id = _stable_id("assert_dxf_layer", source_digest, handle)
        assertions.append(
            {
                "evidence_record_ids": [_stable_id("prim_dxf", source_digest, handle)],
                "extraction_confidence": {"band": "full", "method": "ezdxf-dxf-namespace"},
                "interpretation_confidence": {"band": "full", "method": "dxf-layer-name-preserved"},
                "predicate": "dxf:layer",
                "provenance": _provenance(instant, [_stable_id("prim_dxf", source_digest, handle)], runtime_version),
                "record_id": assertion_id,
                "record_type": "assertion",
                "record_version": "0.1",
                "source_refs": [{"locator": f"{container_by_handle[handle]}/handle:{handle}", "source_id": source_id}],
                "subject_id": entity_ids[handle],
                "value": _known(layer),
                "verification_state": "extracted-not-domain-classified",
            }
        )

    capabilities = {name: "full" for name in CAPABILITIES}
    capabilities.update(
        {
            "properties": "partial",
            "relationships": "partial",
            "3d_geometry": "partial",
            "materials_styles": "partial",
            "georeferencing": "partial",
        }
    )
    if unsupported_handles:
        capabilities["2d_geometry"] = "partial"
    reason_codes = {
        "properties": "AECCTX_DXF_PROPERTIES_PARTIAL",
        "relationships": "AECCTX_DXF_RELATIONSHIPS_PARTIAL",
        "2d_geometry": "AECCTX_DXF_ENTITY_GEOMETRY_UNSUPPORTED",
        "3d_geometry": "AECCTX_DXF_3D_PROFILE_PARTIAL" if aecctx_version == "0.2.0" else "AECCTX_DXF_3D_GEOMETRY_PARTIAL",
        "materials_styles": "AECCTX_DXF_STYLES_PARTIAL",
        "georeferencing": "AECCTX_DXF_GEOREFERENCING_NOT_DECLARED",
    }
    diagnostics: list[dict[str, Any]] = []
    for capability in CAPABILITIES:
        if capabilities[capability] == "full":
            continue
        diagnostics.append(
            {
                "affected_count": len(unsupported_handles) if capability == "2d_geometry" else 1,
                "capability": capability,
                "code": reason_codes[capability],
                "fallback": "Inspect preserved DXF raw tags, handles, layouts, blocks, and native class names.",
                "message": f"DXF capability is partial: {capability}",
                "provenance": _provenance(instant, [source_id], runtime_version),
                "record_id": _stable_id("diag_dxf_loss", source_digest, capability),
                "record_type": "diagnostic",
                "record_version": "0.1",
                "severity": "info",
                "source_refs": [{"locator": "dxf-document", "source_id": source_id}],
                "support_level": "partial",
            }
        )
    for index, error in enumerate(audit.errors):
        diagnostics.append(
            {
                "code": "AECCTX_DXF_AUDIT_ERROR",
                "message": str(error),
                "provenance": _provenance(instant, [source_id], runtime_version, "ezdxf-audit"),
                "record_id": _stable_id("diag_dxf_audit", source_digest, str(index)),
                "record_type": "diagnostic",
                "record_version": "0.1",
                "severity": "warning",
                "source_refs": [{"locator": "dxf-document", "source_id": source_id}],
            }
        )
    if aecctx_version == "0.2.0":
        for handle, entity in sorted(graphical.items()):
            if entity.dxftype() in {"3DSOLID", "BODY", "REGION", "SURFACE"}:
                v02_3d_issues.append(("AECCTX_DXF_ACIS_KERNEL_UNSUPPORTED", handle))
            elif entity.dxftype() == "ACAD_PROXY_ENTITY":
                v02_3d_issues.append(("AECCTX_DXF_PROXY_GRAPHICS_UNSUPPORTED", handle))
        for block in sorted(document.blocks, key=lambda item: item.name):
            if block.block_record.is_xref:
                if source_bundle is None:
                    v02_3d_issues.append(("AECCTX_DXF_XREF_NOT_TRAVERSED", block.name))
    for code, locator in sorted(set(v02_3d_issues)):
        diagnostics.append(
            {
                "affected_count": 1,
                "capability": "3d_geometry",
                "code": code,
                "fallback": "Inspect preserved DXF entity tags and source transforms.",
                "message": f"DXF bounded 3D profile degraded at {locator}.",
                "provenance": _provenance(instant, [source_id], runtime_version, "dxf-v02-bounded-3d"),
                "record_id": _stable_id("diag_dxf_v02_3d", source_digest, f"{code}:{locator}"),
                "record_type": "diagnostic",
                "record_version": "0.2",
                "severity": "info",
                "source_refs": [{"locator": f"dxf-handle:{locator}", "source_id": source_id}],
                "support_level": "partial",
            }
        )
    diagnostics.sort(key=lambda item: item["record_id"])
    loss_summary = [reason_codes[name] for name in CAPABILITIES if capabilities[name] != "full"]
    storage_ref = f"sources/content/{source.name}" if embedding_policy == "embedded" else None
    source_record: dict[str, Any] = {
        "acquisition_origin": "local-file",
        "byte_size": source_bytes,
        "declared_format": _known("DXF"),
        "declared_units": _known(unit) if unit else _unknown("AECCTX_DXF_UNITS_UNITLESS"),
        "detected_format": _known(document.dxfversion),
        "detected_producer": _known(f"ezdxf/{runtime_version}"),
        "detected_units": _known(unit) if unit else _unknown("AECCTX_DXF_UNITS_UNITLESS"),
        "display_name": source.name,
        "dxf_release": acad_release.get(document.dxfversion, "unknown"),
        "embedding_policy": embedding_policy,
        "extractor": {"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
        "layouts": sorted(document.layout_names()),
        "media_type": "application/dxf",
        "prior_source_revision": _unknown("AECCTX_PRIOR_REVISION_NOT_PROVIDED"),
        "provenance": _provenance(instant, [], runtime_version),
        "record_id": source_id,
        "record_type": "source",
        "record_version": "0.1",
        "safety_diagnostics": ["AECCTX_DXF_INPUT_TREATED_AS_DATA", "AECCTX_XREFS_NOT_OPENED", "AECCTX_COMMANDS_NOT_EXECUTED"],
        "sha256": source_digest,
        "source_id": source_id,
        "source_refs": [],
        "spatial_reference": _unknown("AECCTX_DXF_GEOREFERENCING_NOT_DECLARED"),
    }
    if storage_ref:
        source_record["storage_ref"] = storage_ref
    elif embedding_policy == "redacted":
        source_record["redaction_reason"] = "AECCTX_SOURCE_CONTENT_REDACTED_BY_POLICY"

    if aecctx_version == "0.2.0":
        source_record["dxf_container"] = dxf_container
        source_records = [source_record]
        if source_bundle is not None:
            source_record["bundle_logical_path"] = source_bundle.root.logical_path
            source_record["safety_diagnostics"] = [
                "AECCTX_DXF_INPUT_TREATED_AS_DATA",
                "AECCTX_DXF_CONTENT_ADDRESSED_XREFS_ONLY",
                "AECCTX_COMMANDS_NOT_EXECUTED",
            ]
            for record in primitives:
                record["bundle_logical_path"] = source_bundle.root.logical_path
            for record in entity_records:
                block = record.get("block")
                if isinstance(block, dict) and block.get("is_xref"):
                    declared = str(block.get("xref_path", ""))
                    try:
                        logical = _safe_bundle_path(declared).as_posix()
                    except SourceBundleError:
                        logical = ""
                    if logical in source_bundle.by_path:
                        block["resolved_bundle_path"] = logical
                        block["resolved_sha256"] = source_bundle.by_path[logical].sha256

            for entry, native_document in bundle_documents:
                if entry.role == "root":
                    continue
                member_source_id = _stable_id("src_dxf_bundle", entry.sha256, entry.logical_path)
                member_unit = _unit_symbol(int(native_document.units))
                source_records.append(
                    {
                        "acquisition_origin": "content-addressed-source-bundle",
                        "bundle_logical_path": entry.logical_path,
                        "byte_size": entry.byte_size,
                        "declared_format": _known("DXF"),
                        "declared_units": _known(member_unit) if member_unit else _unknown("AECCTX_DXF_UNITS_UNITLESS"),
                        "detected_format": _known(native_document.dxfversion),
                        "detected_producer": _known(f"ezdxf/{runtime_version}"),
                        "detected_units": _known(member_unit) if member_unit else _unknown("AECCTX_DXF_UNITS_UNITLESS"),
                        "display_name": PurePosixPath(entry.logical_path).name,
                        "dxf_container": _dxf_container(entry.path),
                        "dxf_release": acad_release.get(native_document.dxfversion, "unknown"),
                        "embedding_policy": embedding_policy,
                        "evidence_class": "observed",
                        "extractor": {"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
                        "layouts": sorted(native_document.layout_names()),
                        "media_type": entry.media_type,
                        "prior_source_revision": _unknown("AECCTX_PRIOR_REVISION_NOT_PROVIDED"),
                        "provenance": _provenance(instant, [], runtime_version, "content-addressed-xref-extraction"),
                        "record_id": member_source_id,
                        "record_type": "source",
                        "record_version": "0.2",
                        "safety_diagnostics": ["AECCTX_DXF_CONTENT_ADDRESSED_XREFS_ONLY", "AECCTX_COMMANDS_NOT_EXECUTED"],
                        "sha256": entry.sha256,
                        "source_id": member_source_id,
                        "source_refs": [],
                        "spatial_reference": _unknown("AECCTX_DXF_GEOREFERENCING_NOT_DECLARED"),
                    }
                )
                if embedding_policy == "embedded":
                    source_records[-1]["storage_ref"] = f"sources/bundle/{entry.logical_path}"
                elif embedding_policy == "redacted":
                    source_records[-1]["redaction_reason"] = "AECCTX_SOURCE_CONTENT_REDACTED_BY_POLICY"
                member_entities: list[tuple[str, Any, str]] = []
                for layout in native_document.layouts:
                    for native in layout:
                        handle = native.dxf.get("handle")
                        if handle:
                            member_entities.append((handle, native, f"layout:{layout.name}"))
                for block in native_document.blocks:
                    if block.block_record.is_any_layout:
                        continue
                    for native in block:
                        handle = native.dxf.get("handle")
                        if handle:
                            member_entities.append((handle, native, f"block:{block.name}"))
                for handle, native, container in sorted(member_entities, key=lambda item: (item[0], item[2])):
                    primitive_id = _stable_id("prim_dxf_bundle", entry.sha256, f"{entry.logical_path}:{handle}:{container}")
                    v03 = _dxf_v03_evidence(native) if native_document.dxfversion in {"AC1009", "AC1015", "AC1018", "AC1021", "AC1032"} else None
                    primitive = {
                        "bundle_logical_path": entry.logical_path,
                        "container": _known(container),
                        "evidence_class": "observed",
                        "extraction_confidence": {"band": "full", "method": "ezdxf-bundle-entity-tags"},
                        "geometry": _geometry(native),
                        "handle": handle,
                        "layer": _known(native.dxf.get("layer", "0")),
                        "original_class": native.dxftype(),
                        "provenance": _provenance(instant, [member_source_id], runtime_version, "content-addressed-xref-extraction"),
                        "raw_tags": _raw_tags(native, TagCollector, native_document.dxfversion),
                        "record_id": primitive_id,
                        "record_type": "primitive",
                        "record_version": "0.2",
                        "source_refs": [{"locator": f"{container}/handle:{handle}", "source_id": member_source_id}],
                    }
                    if v03 is not None:
                        primitive["dxf_v03"] = v03
                    primitives.append(primitive)
                    if native.dxftype() in {"3DSOLID", "BODY", "REGION", "SURFACE", "EXTRUDEDSURFACE", "LOFTEDSURFACE", "REVOLVEDSURFACE", "SWEPTSURFACE"}:
                        diagnostics.append(
                            {
                                "affected_count": 1,
                                "capability": "3d_geometry",
                                "code": "AECCTX_DXF_ACIS_KERNEL_UNSUPPORTED",
                                "evidence_class": "observed",
                                "fallback": "Inspect preserved raw tags; no ACIS kernel provider is accepted.",
                                "message": f"ACIS entity remains unsupported in {entry.logical_path}.",
                                "provenance": _provenance(instant, [member_source_id], runtime_version, "dxf-v03-acis-boundary"),
                                "record_id": _stable_id("diag_dxf_bundle", entry.sha256, f"acis:{handle}:{container}"),
                                "record_type": "diagnostic",
                                "record_version": "0.2",
                                "severity": "info",
                                "source_refs": [{"locator": f"{container}/handle:{handle}", "source_id": member_source_id}],
                                "support_level": "unsupported",
                            }
                        )
            if len(primitives) + len(entity_records) + len(assertions) + len(relations) + len(diagnostics) > max_records:
                error = DXFResourceLimitError(f"DXF bundle record count exceeds {max_records}")
                error.code = "AECCTX_DXF_RECORD_LIMIT_EXCEEDED"
                raise error
        else:
            source_records = [source_record]
        for record in [*source_records, *primitives, *assertions, *entity_records, *relations, *diagnostics]:
            record.setdefault("evidence_class", "observed")
            record["record_version"] = "0.2"
    else:
        source_records = [source_record]

    record_sets = {
        "sources/sources.jsonl": source_records,
        "evidence/primitives.jsonl": primitives,
        "evidence/assertions.jsonl": assertions,
        "model/entities.jsonl": entity_records,
        "model/relations.jsonl": relations,
        "diagnostics/diagnostics.jsonl": diagnostics,
    }
    artifacts = [
        PackageArtifact(path, b"".join(canonical_json(item) for item in sorted(items, key=lambda value: value["record_id"])), "application/x-ndjson", path.split("/")[-1].removesuffix(".jsonl"), True)
        for path, items in record_sets.items()
    ]
    context = (
        f"# DXF AECCTX package\n\nPackage `{package_id}` preserves DXF `{document.dxfversion}`, {len(primitives)} graphical primitives, "
        f"{len(document.layout_names())} layouts, {len(block_ids)} block definitions, and {len(layer_ids)} layers. "
        "Layer names and entity classes are source evidence, not consumer-domain classifications.\n"
    ).encode("utf-8")
    artifacts.append(PackageArtifact("context/index.md", context, "text/markdown", "agent-context", False))
    artifacts.extend(v02_geometry_artifacts)
    if storage_ref:
        artifacts.append(PackageArtifact(storage_ref, source, "application/dxf", "embedded-source", True))
        if source_bundle is not None:
            for entry in source_bundle.entries:
                if entry.role != "root":
                    artifacts.append(PackageArtifact(f"sources/bundle/{entry.logical_path}", entry.path, entry.media_type, "embedded-xref-source", True))
    manifest = PackageWriter(output, package_form=package_form).write(
        package_id=package_id,
        created_at=instant,
        source_ids=[record["source_id"] for record in source_records],
        capabilities=capabilities,
        loss_summary=loss_summary,
        embedding_policy=embedding_policy,
        producer={"name": PLUGIN_ID, "version": f"{PLUGIN_VERSION}+ezdxf.{runtime_version}"},
        artifacts=artifacts,
        aecctx_version=aecctx_version,
    )
    return IngestResult(package_id, source_id, manifest["logical_digest"], output)
