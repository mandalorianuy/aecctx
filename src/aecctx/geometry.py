from __future__ import annotations

from typing import Iterable, Sequence


def build_preview_descriptor(
    *,
    scope_kind: str,
    scope_id: str,
    view: str,
    artifact_path: str,
    source_record_ids: Sequence[str],
) -> dict[str, object]:
    if scope_kind not in {"scene", "level", "sheet", "page"}:
        raise ValueError(f"unsupported preview scope: {scope_kind}")
    if not scope_id or not view or not artifact_path or not source_record_ids:
        raise ValueError("preview descriptors require scope, view, artifact path, and source records")
    return {
        "artifact_path": artifact_path,
        "scope": {"id": scope_id, "kind": scope_kind},
        "source_record_ids": sorted(source_record_ids),
        "status": "derived-preview",
        "view": view,
    }


def source_to_glb_transform() -> dict[str, list[list[float]]]:
    return {
        "source_to_glb": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, -1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        "glb_to_source": [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, -1.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
    }


def _number(value: float) -> str:
    normalized = 0.0 if abs(value) < 1e-12 else value
    return f"{normalized:.6f}".rstrip("0").rstrip(".") or "0"


def _project(vertex: Sequence[float], view: str) -> tuple[float, float]:
    if view == "top":
        return float(vertex[0]), -float(vertex[1])
    if view == "front":
        return float(vertex[0]), -float(vertex[2])
    if view == "side":
        return float(vertex[1]), -float(vertex[2])
    raise ValueError(f"unsupported preview view: {view}")


def render_svg_preview(vertices: Sequence[Sequence[float]], faces: Sequence[Sequence[int]], *, view: str = "top") -> bytes:
    projected = [_project(vertex, view) for vertex in vertices]
    if not projected:
        projected = [(0.0, 0.0)]
    minimum_x = min(point[0] for point in projected)
    maximum_x = max(point[0] for point in projected)
    minimum_y = min(point[1] for point in projected)
    maximum_y = max(point[1] for point in projected)
    width = max(maximum_x - minimum_x, 1.0)
    height = max(maximum_y - minimum_y, 1.0)
    margin = max(width, height) * 0.05
    view_box = (minimum_x - margin, minimum_y - margin, width + 2 * margin, height + 2 * margin)
    polygons = []
    for face in sorted((tuple(int(index) for index in face) for face in faces)):
        points = " ".join(f"{_number(projected[index][0])},{_number(projected[index][1])}" for index in face)
        polygons.append(f'  <polygon points="{points}"/>')
    content = "\n".join(polygons)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{" ".join(_number(value) for value in view_box)}" '
        'fill="none" stroke="#111827" stroke-width="0.01" vector-effect="non-scaling-stroke">\n'
        f"{content}\n</svg>\n"
    ).encode("utf-8")


def export_deterministic_glb(meshes: Iterable[object]) -> bytes:
    try:
        import numpy
        import trimesh
    except ImportError as error:
        raise RuntimeError("Install AECCTX with the 'geometry' extra to export GLB") from error
    scene = trimesh.Scene()
    transform = numpy.array(source_to_glb_transform()["source_to_glb"], dtype=float)
    for index, source_mesh in enumerate(meshes, 1):
        mesh = source_mesh.copy()
        mesh.apply_transform(transform)
        mesh.metadata = {}
        scene.add_geometry(mesh, node_name=f"mesh-{index:04d}", geom_name=f"mesh-{index:04d}")
    scene.metadata = {}
    result = scene.export(file_type="glb")
    if not isinstance(result, bytes):
        raise TypeError("trimesh GLB exporter did not return bytes")
    return result
