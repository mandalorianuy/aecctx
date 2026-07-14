from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "org.aecctx.vision.raster-rules"
RUNTIME_DIGEST = "sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db"
AXES = ("cpu", "decompression", "environment", "filesystem", "input_bytes", "memory", "network", "open_files", "output_bytes", "process", "process_tree", "records", "recursion", "temporary_storage", "user_permissions", "wall_time")


def configuration(request: dict[str, object]) -> tuple[int, int, int, bool]:
    value = request.get("configuration", {})
    expected = {"foreground_threshold": 32, "minimum_component_pixels": 5, "maximum_candidates": 128, "emit_reconstruction": True}
    if value != expected:
        raise ValueError("configuration must equal the closed visible-raster-rules-v1 profile")
    return 32, 5, 128, True


def _components(pixels: bytes, width: int, height: int) -> list[set[tuple[int, int]]]:
    foreground = {(x, y) for y in range(height) for x in range(width) if pixels[y * width + x] <= 32}
    output = []
    while foreground:
        seed = min(foreground, key=lambda point: (point[1], point[0])); pending = [seed]; component = set(); foreground.remove(seed)
        while pending:
            point = pending.pop(); component.add(point); x, y = point
            for other in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if other in foreground: foreground.remove(other); pending.append(other)
        output.append(component)
    return output


def detect(pixels: bytes, width: int, height: int) -> dict[str, object]:
    if width < 1 or height < 1 or width > 4096 or height > 4096 or len(pixels) != width * height:
        raise ValueError("invalid raster dimensions")
    candidates = []
    for component in _components(pixels, width, height):
        if len(component) < 5: continue
        xs = [p[0] for p in component]; ys = [p[1] for p in component]; left, right, top, bottom = min(xs), max(xs), min(ys), max(ys)
        w, h = right - left + 1, bottom - top + 1
        horizontal = [y for y in range(top, bottom + 1) if all((x, y) in component for x in range(left, right + 1))]
        vertical = [x for x in range(left, right + 1) if all((x, y) in component for y in range(top, bottom + 1))]
        kind = None
        if w >= 12 and h >= 12 and horizontal == [top, bottom] and vertical == [left, right] and len(component) == 2 * w + 2 * h - 4: kind = "region.rectangle"
        elif 3 <= len(horizontal) <= 8 and 3 <= len(vertical) <= 8 and all(b - a >= 4 for a, b in zip(horizontal, horizontal[1:])) and all(b - a >= 4 for a, b in zip(vertical, vertical[1:])): kind = "table.grid"
        elif w == h and w >= 5 and w % 2 and len(component) == w + h - 1 and horizontal == [top + h // 2] and vertical == [left + w // 2]: kind = "symbol.cross"
        elif w >= 7 and h in {3, 5} and horizontal == [top + h // 2] and vertical == [left, right] and len(component) == w + 2 * h - 2: kind = "dimension.linear"
        if kind:
            candidates.append({"id": f"c{len(candidates)}", "kind": kind, "bbox": [left, top, w, h], "confidence": 1.0, "pixel_count": len(component), "state": "candidate"})
    relationships = []
    for outer in candidates:
        ox, oy, ow, oh = outer["bbox"]
        for inner in candidates:
            if outer is inner: continue
            ix, iy, iw, ih = inner["bbox"]
            if ox <= ix and oy <= iy and ix + iw <= ox + ow and iy + ih <= oy + oh:
                relationships.append({"id": f"r{len(relationships)}", "kind": "relationship.contains", "subject_id": outer["id"], "object_id": inner["id"], "confidence": 1.0})
    reconstructions = []
    for candidate in candidates:
        if candidate["kind"] == "region.rectangle":
            x, y, w, h = candidate["bbox"]
            reconstructions.append({"id": f"h{len(reconstructions)}", "kind": "reconstruction.planar-boundary", "source_candidate_ids": [candidate["id"]], "pixel_polygon": [[x, y], [x + w - 1, y], [x + w - 1, y + h - 1], [x, y + h - 1], [x, y]], "confidence": 1.0})
    return {"schema": "aecctx.vision.candidates.v1", "profile": "visible-raster-rules-v1", "width": width, "height": height, "candidates": candidates, "relationships": relationships, "reconstructions": reconstructions}


def descriptor() -> dict[str, Any]:
    return {"actions": ["extract"], "deterministic": True, "distribution": "operator-built-oci-image", "enforced_axes": {axis: True for axis in AXES}, "enforcement_profile": "oci-docker-v1", "formats": ["image/x-portable-graymap"], "license_spdx": "Apache-2.0 AND PSF-2.0", "network_mode": "disabled", "platforms": ["linux-container"], "protocol_version": "0.2", "provider_id": PROVIDER_ID, "provider_version": "0.3.0", "runtime_version": "python-3.12.10-stdlib-raster-rules-v1", "runtime_digest": RUNTIME_DIGEST}


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def _pgm(data: bytes) -> tuple[int, int, bytes]:
    parts = data.split(b"\n", 3)
    if len(parts) != 4 or parts[0] != b"P5" or parts[2] != b"255": raise ValueError("AECCTX_VISION_PGM_INVALID")
    dimensions = parts[1].split()
    if len(dimensions) != 2: raise ValueError("AECCTX_VISION_PGM_INVALID")
    width, height = map(int, dimensions)
    if len(parts[3]) != width * height: raise ValueError("AECCTX_VISION_PGM_INVALID")
    return width, height, parts[3]


def _capability_report() -> dict[str, dict[str, Any]]:
    names = ("identity", "hierarchy", "properties", "relationships", "text", "2d_geometry", "3d_geometry", "materials_styles", "georeferencing", "validation")
    return {name: ({"affected": [], "fallback": "source pixels", "reason_codes": ["AECCTX_VISION_INFERRED_ONLY"], "support_level": "partial"} if name in {"relationships", "2d_geometry"} else {"affected": ["visible-raster"], "fallback": "retain source pixels", "reason_codes": ["AECCTX_VISION_CAPABILITY_UNSUPPORTED"], "support_level": "unsupported"}) for name in names}


def main() -> int:
    root = Path.cwd(); output = root / "output"; request = json.loads((root / "request.json").read_text(encoding="utf-8")); desc = descriptor()
    events: list[dict[str, Any]] = []; diagnostics: list[dict[str, Any]] = []; ok = True; error = None
    try:
        configuration(request)
        data = (root / request["input"]["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != request["input"]["sha256"]: raise ValueError("AECCTX_VISION_INPUT_HASH_MISMATCH")
        width, height, pixels = _pgm(data); payload = detect(pixels, width, height)
        events.append({"event_type": "primitive", "payload": payload, "sequence": 0, "source_locator": f"sha256:{request['input']['sha256']}"})
        if not payload["candidates"]: diagnostics.append({"code": "AECCTX_VISION_NO_CANDIDATE", "severity": "warning"})
    except Exception as caught:
        ok = False; error = {"code": "AECCTX_VISION_PROVIDER_FAILED", "message": f"{type(caught).__name__}: {caught}"}; diagnostics.append({"code": "AECCTX_VISION_PROVIDER_FAILED", "severity": "error"})
    response: dict[str, Any] = {"artifacts": [], "attestation": {"descriptor_digest": hashlib.sha256(_canonical(desc)).hexdigest(), "deterministic": True, "enforcement_profile": "oci-docker-v1", "network_mode": "disabled", "provider_id": PROVIDER_ID, "provider_version": "0.3.0", "request_digest": hashlib.sha256(_canonical(request)).hexdigest(), "response_payload_digest": "0" * 64, "runtime_version": desc["runtime_version"], "runtime_digest": RUNTIME_DIGEST}, "capability_report": _capability_report(), "diagnostics": diagnostics, "events": events, "ok": ok, "protocol_version": "0.2", "provider_id": PROVIDER_ID, "request_id": request["request_id"], "resource_usage": {"artifacts": 0, "events": len(events)}}
    if error: response["error"] = error
    response["attestation"]["response_payload_digest"] = hashlib.sha256(_canonical({key: value for key, value in response.items() if key != "attestation"})).hexdigest()
    (output / "response.json").write_bytes(_canonical(response))
    return 0


if __name__ == "__main__": raise SystemExit(main())
