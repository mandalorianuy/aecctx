from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


PROVIDER_ID = "org.aecctx.step-iges.ocp"
RUNTIME_DIGEST = "sha256:875cbbbc5198ae44e8957e3a90c9a8afd0dc541f01029fb5186a296e3d2a0d47"
CONFIGURATION = {
    "angular_deflection": 0.5,
    "brep_format": "occt-ascii-brep-7.9.3",
    "linear_deflection": 0.1,
    "read_shape_healing": "translator-default-observed",
    "schema_profile": "acx17-v1",
    "tessellation_units": "source",
}
REQUIRED_AXES = (
    "cpu", "decompression", "environment", "filesystem", "input_bytes", "memory", "network", "open_files",
    "output_bytes", "process", "process_tree", "records", "recursion", "temporary_storage", "user_permissions", "wall_time",
)
CAPABILITIES = (
    "identity", "hierarchy", "properties", "relationships", "text", "2d_geometry", "3d_geometry", "materials_styles", "georeferencing", "validation",
)


def _configuration(request: dict[str, Any]) -> dict[str, Any]:
    configured = request.get("configuration")
    if configured != CONFIGURATION:
        raise ValueError("AECCTX_STEP_IGES_CONFIGURATION_INVALID")
    return dict(CONFIGURATION)


def _probe(data: bytes) -> str:
    if data.lstrip().startswith(b"ISO-10303-21;"):
        return "step"
    lines = data.splitlines()
    sections = {chr(line[72]) for line in lines if len(line) == 80 and line[72] in b"SGDPT"}
    if {"S", "G", "D", "P", "T"}.issubset(sections):
        return "iges"
    raise ValueError("AECCTX_STEP_IGES_FORMAT_UNSUPPORTED")


def _ascii(data: bytes) -> str:
    try:
        return data.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED") from error


def _step_statements(section: str, max_recursion_depth: int) -> list[str]:
    statements: list[str] = []
    start = 0
    in_string = False
    in_comment = False
    depth = 0
    index = 0
    while index < len(section):
        pair = section[index : index + 2]
        character = section[index]
        if in_comment:
            if pair == "*/":
                in_comment = False
                index += 2
                continue
            index += 1
            continue
        if not in_string and pair == "/*":
            in_comment = True
            index += 2
            continue
        if character == "'":
            if in_string and index + 1 < len(section) and section[index + 1] == "'":
                index += 2
                continue
            in_string = not in_string
        elif not in_string:
            if character == "(":
                depth += 1
                if depth > max_recursion_depth:
                    raise ValueError("AECCTX_STEP_IGES_REFERENCE_DEPTH_EXCEEDED")
            elif character == ")":
                depth -= 1
                if depth < 0:
                    raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
            elif character == ";" and depth == 0:
                statement = section[start : index + 1].strip()
                if statement:
                    statements.append(statement)
                start = index + 1
        index += 1
    if in_string or in_comment or depth != 0 or section[start:].strip():
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    return statements


def _reference_view(value: str) -> str:
    result = list(value)
    in_string = False
    in_comment = False
    index = 0
    while index < len(value):
        pair = value[index : index + 2]
        if in_comment:
            result[index] = " "
            if pair == "*/":
                result[index + 1] = " "
                in_comment = False
                index += 2
                continue
            index += 1
            continue
        if not in_string and pair == "/*":
            result[index] = result[index + 1] = " "
            in_comment = True
            index += 2
            continue
        if value[index] == "'":
            result[index] = " "
            if in_string and index + 1 < len(value) and value[index + 1] == "'":
                result[index + 1] = " "
                index += 2
                continue
            in_string = not in_string
        elif in_string:
            result[index] = " "
        index += 1
    return "".join(result)


def _scan_step(data: bytes, *, max_records: int, max_recursion_depth: int) -> dict[str, Any]:
    text = _ascii(data)
    if not text.lstrip().startswith("ISO-10303-21;") or "END-ISO-10303-21;" not in text:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    header_start = text.find("HEADER;")
    data_start = text.find("DATA;", header_start + 7)
    if header_start < 0 or data_start < 0:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    header_end = text.find("ENDSEC;", header_start + 7)
    data_end = text.find("ENDSEC;", data_start + 5)
    if header_end < 0 or data_end < 0 or header_end > data_start:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    header = text[header_start + 7 : header_end]
    schema_match = re.search(r"FILE_SCHEMA\s*\(\s*\((.*?)\)\s*\)\s*;", header, flags=re.DOTALL)
    if schema_match is None:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    schemas = [item.replace("''", "'") for item in re.findall(r"'((?:[^']|'')*)'", schema_match.group(1))]
    if not schemas:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    entities: list[dict[str, Any]] = []
    identifiers: set[int] = set()
    statements = _step_statements(text[data_start + 5 : data_end], max_recursion_depth)
    if len(statements) > max_records:
        raise ValueError("AECCTX_STEP_IGES_ENTITY_LIMIT_EXCEEDED")
    for statement in statements:
        match = re.fullmatch(r"#([1-9][0-9]*)\s*=\s*([A-Z][A-Z0-9_]*)\s*\((.*)\)\s*;", statement, flags=re.DOTALL)
        complex_match = None if match is not None else re.fullmatch(r"#([1-9][0-9]*)\s*=\s*\((.*)\)\s*;", statement, flags=re.DOTALL)
        if match is None and complex_match is None:
            raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
        selected = match or complex_match
        assert selected is not None
        identifier = int(selected.group(1))
        if identifier in identifiers:
            raise ValueError("AECCTX_STEP_IGES_ENTITY_DUPLICATE")
        identifiers.add(identifier)
        payload = match.group(3) if match is not None else complex_match.group(2)  # type: ignore[union-attr]
        visible_payload = _reference_view(payload)
        references = sorted({int(value) for value in re.findall(r"#([1-9][0-9]*)", visible_payload)})
        entity = {
            "id": identifier,
            "original_class": match.group(2) if match is not None else "COMPLEX_INSTANCE",
            "raw": statement,
            "references": references,
        }
        if complex_match is not None:
            component_classes = re.findall(r"(?:^|\s)([A-Z][A-Z0-9_]*)\s*\(", visible_payload)
            if len(component_classes) < 2:
                raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
            entity["component_classes"] = component_classes
        entities.append(entity)
    referenced = {reference for entity in entities for reference in entity["references"]}
    if not referenced.issubset(identifiers):
        raise ValueError("AECCTX_STEP_IGES_REFERENCE_INVALID")
    entities.sort(key=lambda item: item["id"])
    return {
        "entities": entities,
        "external_references": any(item["original_class"] == "EXTERNAL_FILE_ID_AND_LOCATION" for item in entities),
        "format": "step",
        "headers": {"FILE_SCHEMA": schemas},
        "schemas": schemas,
    }


def _iges_int(value: bytes, *, default: int = 0) -> int:
    stripped = value.strip()
    if not stripped:
        return default
    try:
        return int(stripped)
    except ValueError as error:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED") from error


def _scan_iges(data: bytes, *, max_records: int, max_recursion_depth: int) -> dict[str, Any]:
    del max_recursion_depth
    lines = data.splitlines()
    if not lines or any(len(line) != 80 or line[72] not in b"SGDPT" for line in lines):
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    by_section = {section: [line for line in lines if line[72:73] == section] for section in (b"S", b"G", b"D", b"P", b"T")}
    if any(not by_section[section] for section in by_section) or len(by_section[b"D"]) % 2:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    if len(by_section[b"D"]) // 2 > max_records:
        raise ValueError("AECCTX_STEP_IGES_ENTITY_LIMIT_EXCEEDED")
    directory: list[dict[str, Any]] = []
    for index in range(0, len(by_section[b"D"]), 2):
        first = by_section[b"D"][index]
        second = by_section[b"D"][index + 1]
        first_sequence = _iges_int(first[73:80])
        second_sequence = _iges_int(second[73:80])
        entity_type = _iges_int(first[0:8])
        if first_sequence <= 0 or second_sequence != first_sequence + 1 or _iges_int(second[0:8]) != entity_type:
            raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
        directory.append(
            {
                "entity_type": entity_type,
                "form": _iges_int(second[32:40]),
                "label": second[56:64].decode("ascii").strip(),
                "level": _iges_int(first[32:40]),
                "parameter_pointer": _iges_int(first[8:16]),
                "sequence": first_sequence,
                "subscript": _iges_int(second[64:72]),
                "transform_pointer": _iges_int(first[48:56]),
            }
        )
    directory.sort(key=lambda item: item["sequence"])
    return {
        "directory": directory,
        "external_references": any(item["entity_type"] == 416 for item in directory),
        "format": "iges",
        "global_raw": b"".join(line[:72] for line in by_section[b"G"]).decode("ascii").rstrip(),
        "version": "5.3",
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def descriptor() -> dict[str, Any]:
    return {
        "actions": ["extract"],
        "deterministic": True,
        "distribution": "operator-built-oci-image",
        "enforced_axes": {axis: True for axis in REQUIRED_AXES},
        "enforcement_profile": "oci-docker-v1",
        "formats": ["model/step", "model/iges"],
        "license_spdx": "Apache-2.0 AND LGPL-2.1-only WITH OCCT-exception",
        "network_mode": "disabled",
        "platforms": ["linux-container"],
        "protocol_version": "0.2",
        "provider_id": PROVIDER_ID,
        "provider_version": "0.2.0",
        "runtime_digest": RUNTIME_DIGEST,
        "runtime_version": "python-3.12+cadquery-ocp-7.9.3.1.1+occt-7.9.3",
    }


def _capability_report(ok: bool) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name in CAPABILITIES:
        if name == "identity" and ok:
            result[name] = {"affected": [], "fallback": "none", "reason_codes": [], "support_level": "full"}
        elif name in {"hierarchy", "properties", "relationships", "3d_geometry", "materials_styles", "validation"} and ok:
            reasons = ["AECCTX_STEP_IGES_TRANSLATOR_PROCESSING_APPLIED"] if name == "3d_geometry" else ["AECCTX_STEP_IGES_PROFILE_PARTIAL"]
            result[name] = {
                "affected": ["step-iges-source"],
                "fallback": "retain source entity evidence and translator diagnostics",
                "reason_codes": reasons,
                "support_level": "partial",
            }
        else:
            result[name] = {
                "affected": ["step-iges-source"],
                "fallback": "retain opaque source evidence",
                "reason_codes": ["AECCTX_STEP_IGES_CAPABILITY_UNSUPPORTED"],
                "support_level": "unsupported",
            }
    return result


def _topology(shape: Any) -> dict[str, int]:
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX, TopAbs_WIRE
    from OCP.TopExp import TopExp_Explorer

    result: dict[str, int] = {}
    for name, kind in (
        ("vertices", TopAbs_VERTEX),
        ("edges", TopAbs_EDGE),
        ("wires", TopAbs_WIRE),
        ("faces", TopAbs_FACE),
        ("shells", TopAbs_SHELL),
        ("solids", TopAbs_SOLID),
    ):
        explorer = TopExp_Explorer(shape, kind)
        count = 0
        while explorer.More():
            count += 1
            explorer.Next()
        result[name] = count
    return result


def _bounds(shape: Any) -> dict[str, list[float]]:
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box

    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box, True)
    values = box.Get()
    return {
        "max": [round(float(values[index]), 12) for index in (3, 4, 5)],
        "min": [round(float(values[index]), 12) for index in (0, 1, 2)],
    }


def _triangle_mesh(shape: Any) -> dict[str, Any]:
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    from OCP.TopLoc import TopLoc_Location

    mesher = BRepMesh_IncrementalMesh(shape, 0.1, False, 0.5, False)
    if not mesher.IsDone():
        raise ValueError("AECCTX_STEP_IGES_TESSELLATION_FAILED")
    vertices: list[list[float]] = []
    vertex_index: dict[tuple[float, float, float], int] = {}
    triangles: list[list[int]] = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = TopoDS.Face_s(explorer.Current())
        location = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation_s(face, location)
        if triangulation is None or triangulation.NbTriangles() < 1:
            explorer.Next()
            continue
        local_to_global: dict[int, int] = {}
        transform = location.Transformation()
        for local_index in range(1, triangulation.NbNodes() + 1):
            point = triangulation.Node(local_index)
            point.Transform(transform)
            key = tuple(0.0 if abs(float(value)) < 1e-12 else round(float(value), 12) for value in (point.X(), point.Y(), point.Z()))
            if key not in vertex_index:
                vertex_index[key] = len(vertices)
                vertices.append(list(key))
            local_to_global[local_index] = vertex_index[key]
        for triangle_index in range(1, triangulation.NbTriangles() + 1):
            node_indices = list(triangulation.Triangle(triangle_index).Get())
            if face.Orientation() == TopAbs_REVERSED:
                node_indices[1], node_indices[2] = node_indices[2], node_indices[1]
            triangles.append([local_to_global[index] for index in node_indices])
        explorer.Next()
    if not vertices or not triangles:
        raise ValueError("AECCTX_STEP_IGES_TESSELLATION_FAILED")
    return {"schema": "aecctx.triangle-mesh.v1", "triangles": sorted(triangles), "vertices": vertices}


def _transfer(source_path: Path, format_name: str) -> Any:
    from OCP.IFSelect import IFSelect_RetDone

    if format_name == "step":
        from OCP.STEPControl import STEPControl_Reader

        reader = STEPControl_Reader()
    else:
        from OCP.IGESControl import IGESControl_Reader

        reader = IGESControl_Reader()
    if reader.ReadFile(str(source_path)) != IFSelect_RetDone:
        raise ValueError("AECCTX_STEP_IGES_TRANSFER_FAILED")
    transferred = int(reader.TransferRoots())
    if transferred < 1 or int(reader.NbShapes()) < 1:
        raise ValueError("AECCTX_STEP_IGES_TRANSFER_FAILED")
    shape = reader.OneShape()
    if shape.IsNull():
        raise ValueError("AECCTX_STEP_IGES_TRANSFER_FAILED")
    return shape


def _response(request: dict[str, Any], source_path: Path, output_root: Path) -> dict[str, Any]:
    input_bytes = source_path.read_bytes()
    if hashlib.sha256(input_bytes).hexdigest() != request["input"]["sha256"]:
        raise ValueError("AECCTX_STEP_IGES_INPUT_HASH_MISMATCH")
    _configuration(request)
    format_name = _probe(input_bytes)
    limits = request["limits"]
    scanned = (
        _scan_step(input_bytes, max_records=limits["max_records"], max_recursion_depth=limits["max_recursion_depth"])
        if format_name == "step"
        else _scan_iges(input_bytes, max_records=limits["max_records"], max_recursion_depth=limits["max_recursion_depth"])
    )
    if scanned["external_references"]:
        raise ValueError("AECCTX_STEP_IGES_EXTERNAL_REFERENCE_UNRESOLVED")
    shape = _transfer(source_path, format_name)
    artifact_path = output_root / "artifacts" / "root-1.brep"
    from OCP.BRepTools import BRepTools

    if not BRepTools.Write_s(shape, str(artifact_path)):
        raise ValueError("AECCTX_STEP_IGES_BREP_INVALID")
    artifact_bytes = artifact_path.read_bytes()
    mesh_path = output_root / "artifacts" / "scene-mesh.json"
    mesh_path.write_bytes(_canonical(_triangle_mesh(shape)))
    mesh_bytes = mesh_path.read_bytes()
    source_locator = f"sha256:{request['input']['sha256']}"
    events = [
        {
            "event_type": "primitive",
            "payload": {**scanned, "schema": "aecctx.step-iges.source.v1"},
            "sequence": 0,
            "source_locator": source_locator,
        },
        {
            "event_type": "primitive",
            "payload": {
                "artifact_path": "artifacts/root-1.brep",
                "mesh_artifact_path": "artifacts/scene-mesh.json",
                "bounds": _bounds(shape),
                "format": format_name,
                "representation_fidelity": "brep-translator-derived",
                "schema": "aecctx.step-iges.shape.v1",
                "topology": _topology(shape),
                "translator_processing": "translator-default-observed",
            },
            "sequence": 1,
            "source_locator": "shape:1",
        },
    ]
    return {
        "artifacts": [
            {
                "bytes": len(artifact_bytes),
                "media_type": "model/vnd.opencascade.brep",
                "path": "artifacts/root-1.brep",
                "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
            },
            {
                "bytes": len(mesh_bytes),
                "media_type": "application/vnd.aecctx.triangle-mesh+json",
                "path": "artifacts/scene-mesh.json",
                "sha256": hashlib.sha256(mesh_bytes).hexdigest(),
            },
        ],
        "capability_report": _capability_report(True),
        "diagnostics": [{"code": "AECCTX_STEP_IGES_TRANSLATOR_PROCESSING_APPLIED", "severity": "info"}],
        "events": events,
        "ok": True,
        "resource_usage": {"artifacts": 2, "events": len(events), "source_entities": len(scanned.get("entities", scanned.get("directory", [])))},
    }


def main() -> int:
    workspace = Path.cwd()
    output_root = workspace / "output"
    response_path = output_root / "response.json"
    request = json.loads((workspace / "request.json").read_text(encoding="utf-8"))
    error: dict[str, str] | None = None
    try:
        if request.get("provider_id") != PROVIDER_ID or request.get("action") != "extract":
            raise ValueError("AECCTX_STEP_IGES_REQUEST_OUTSIDE_PROFILE")
        payload = _response(request, workspace / request["input"]["path"], output_root)
    except Exception as caught:
        code = str(caught) if str(caught).startswith("AECCTX_") else "AECCTX_STEP_IGES_PROVIDER_FAILED"
        error = {"code": code, "message": f"{type(caught).__name__}: STEP/IGES extraction failed"}
        payload = {
            "artifacts": [],
            "capability_report": _capability_report(False),
            "diagnostics": [{"code": code, "severity": "error"}],
            "events": [],
            "ok": False,
            "resource_usage": {"artifacts": 0, "events": 0},
        }
    described = descriptor()
    response = {
        **payload,
        "attestation": {
            "descriptor_digest": _digest(described),
            "deterministic": True,
            "enforcement_profile": "oci-docker-v1",
            "network_mode": "disabled",
            "provider_id": PROVIDER_ID,
            "provider_version": "0.2.0",
            "request_digest": _digest(request),
            "response_payload_digest": "0" * 64,
            "runtime_digest": RUNTIME_DIGEST,
            "runtime_version": "python-3.12+cadquery-ocp-7.9.3.1.1+occt-7.9.3",
        },
        "protocol_version": "0.2",
        "provider_id": PROVIDER_ID,
        "request_id": request["request_id"],
    }
    if error is not None:
        response["error"] = error
    response["attestation"]["response_payload_digest"] = _digest({key: value for key, value in response.items() if key != "attestation"})
    response_path.write_bytes(_canonical(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
