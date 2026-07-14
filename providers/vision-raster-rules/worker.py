from __future__ import annotations


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
