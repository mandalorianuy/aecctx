"""Generate project-authored ACX-16 mesh and calibration fixtures."""

from __future__ import annotations

import base64
import json
import struct
from pathlib import Path


ROOT = Path(__file__).parent
PROFILES = ROOT / "profiles"
VERTICES = ((0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (0.0, 3.0, 0.0))
FACES = ((0, 1, 2),)
FRAME = {"axes": ["+X", "+Y", "+Z"], "handedness": "right"}


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n"


def gltf_document(uri: str) -> dict[str, object]:
    return {
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "max": [4, 3, 0], "min": [0, 0, 0], "type": "VEC3"},
            {"bufferView": 1, "componentType": 5123, "count": 3, "max": [2], "min": [0], "type": "SCALAR"},
        ],
        "asset": {"generator": "AECCTX project-authored fixture", "version": "2.0"},
        "bufferViews": [
            {"buffer": 0, "byteLength": 36, "byteOffset": 0, "target": 34962},
            {"buffer": 0, "byteLength": 6, "byteOffset": 36, "target": 34963},
        ],
        "buffers": [{"byteLength": 42, "uri": uri}],
        "meshes": [{"name": "TriangleMeters", "primitives": [{"attributes": {"POSITION": 0}, "indices": 1, "mode": 4}]}],
        "nodes": [{"mesh": 0, "name": "TranslatedTriangle", "translation": [100.0, 200.0, 300.0]}],
        "scene": 0,
        "scenes": [{"name": "FixtureScene", "nodes": [0]}],
    }


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    PROFILES.mkdir(parents=True, exist_ok=True)
    obj = "o TriangleUnknown\nv 0 0 0\nv 4 0 0\nv 0 3 0\nf 1 2 3\n"
    stl = "solid TriangleUnknown\n  facet normal 0 0 1\n    outer loop\n      vertex 0 0 0\n      vertex 4 0 0\n      vertex 0 3 0\n    endloop\n  endfacet\nendsolid TriangleUnknown\n"
    binary = b"".join(struct.pack("<3f", *vertex) for vertex in VERTICES) + struct.pack("<3H", *FACES[0])
    embedded = "data:application/octet-stream;base64," + base64.b64encode(binary).decode("ascii")
    gltf = gltf_document(embedded)
    json_bytes = json.dumps(gltf, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    json_padded = json_bytes + b" " * ((-len(json_bytes)) % 4)
    binary_padded = binary + b"\0" * ((-len(binary)) % 4)
    glb_header = struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(json_padded) + 8 + len(binary_padded))
    glb = glb_header + struct.pack("<I4s", len(json_padded), b"JSON") + json_padded + struct.pack("<I4s", len(binary_padded), b"BIN\0") + binary_padded
    glb_gltf = gltf_document("")
    glb_gltf["buffers"] = [{"byteLength": len(binary_padded)}]
    glb_json = json.dumps(glb_gltf, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    glb_json += b" " * ((-len(glb_json)) % 4)
    glb = struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(glb_json) + 8 + len(binary_padded)) + struct.pack("<I4s", len(glb_json), b"JSON") + glb_json + struct.pack("<I4s", len(binary_padded), b"BIN\0") + binary_padded

    (ROOT / "triangle-unknown.obj").write_text(obj, encoding="ascii")
    (ROOT / "triangle-unknown.stl").write_text(stl, encoding="ascii")
    (ROOT / "triangle-meters.gltf").write_text(canonical(gltf), encoding="utf-8")
    (ROOT / "triangle-meters.glb").write_bytes(glb)
    unsafe = gltf_document("external-buffer.bin")
    (ROOT / "unsafe-external.gltf").write_text(canonical(unsafe), encoding="utf-8")

    profiles = {
        "scale-mm-to-m.json": {
            "author": {"id": "fixture:author"}, "mode": "scale", "profile_version": "0.2.0", "scale": 0.001,
            "source_frame": FRAME, "source_units": "mm", "target_frame": FRAME, "target_units": "m", "tolerance": 1e-9,
        },
        "matrix-local-to-crs.json": {
            "author": {"id": "fixture:author"}, "matrix": [1, 0, 0, 500000, 0, 1, 0, 6100000, 0, 0, 1, 25, 0, 0, 0, 1],
            "mode": "matrix", "profile_version": "0.2.0", "source_frame": FRAME, "source_units": "m",
            "target_crs": {"horizontal": "EPSG:32721", "vertical": "local-height"}, "target_frame": FRAME, "target_units": "m", "tolerance": 1e-7,
        },
        "control-points.json": {
            "author": {"id": "fixture:author"}, "control_points": [
                {"id": "a", "source": [0, 0, 0], "target": [100, 200, 300]},
                {"id": "b", "source": [4, 0, 0], "target": [100, 208, 300]},
                {"id": "c", "source": [0, 3, 0], "target": [94, 200, 300]},
                {"id": "d", "source": [0, 0, 2], "target": [100, 200, 304]},
            ], "mode": "control_points", "profile_version": "0.2.0", "source_frame": FRAME, "source_units": "m",
            "target_crs": {"horizontal": "LOCAL:CONTROL"}, "target_frame": FRAME, "target_units": "m", "tolerance": 1e-8,
        },
        "conflict-gltf-mm.json": {
            "author": {"id": "fixture:author"}, "mode": "scale", "profile_version": "0.2.0", "scale": 0.001,
            "source_frame": FRAME, "source_units": "mm", "target_frame": FRAME, "target_units": "m", "tolerance": 1e-9,
        },
    }
    for name, profile in profiles.items():
        (PROFILES / name).write_text(canonical(profile), encoding="utf-8")


if __name__ == "__main__":
    main()
