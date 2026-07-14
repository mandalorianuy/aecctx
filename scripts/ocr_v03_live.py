#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from aecctx.providers import OCIDockerProfile, ProviderLimits, ProviderRunner, TESSERACT_OCR_PROVIDER_ID, build_provider_request, tesseract_ocr_v03_descriptor, tesseract_ocr_v03_registry
from aecctx.inference import canonical_ocr_pgm
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MATRIX = {
    "eng-auto-v1": ("multi-column.png", 0), "eng-column-v1": ("eng-block.png", 0),
    "eng-block-v1": ("rotated-90.png", 90), "spa-block-v1": ("spa-block.png", 0),
    "por-block-v1": ("por-block.png", 0), "eng-table-v1": ("table.png", 0),
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def verify(output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    registry = tesseract_ocr_v03_registry(repository_root=ROOT)
    responses: dict[str, dict[str, object]] = {}
    for architecture in ("arm64", "amd64"):
        image = f"aecctx-tesseract-ocr-layout:0.3.0-linux-{architecture}"
        limits = ProviderLimits(wall_time_seconds=30, cpu_seconds=30)
        runner = ProviderRunner(registry=registry, profile=OCIDockerProfile(image=image, platform="linux", architecture=architecture), limits=limits)
        for profile, (fixture, orientation) in MATRIX.items():
            with Image.open(ROOT / "fixtures/v0.3/ocr" / fixture) as raster:
                grayscale = raster.convert("L"); width, height = grayscale.size
                input_bytes = canonical_ocr_pgm(width, height, grayscale.tobytes())
            result = runner.run(TESSERACT_OCR_PROVIDER_ID, "extract", input_bytes, configuration={"dpi": 300, "minimum_confidence": 0, "ocr_profile": profile, "orientation_degrees": orientation})
            if not result.ok: raise RuntimeError(f"{architecture}/{profile}: provider failed")
            payload = asdict(result)
            path = output / f"{architecture}-{profile}.json"; path.write_bytes(canonical(payload) + b"\n")
            responses[f"{architecture}/{profile}"] = payload
            if architecture == "arm64" and profile == "spa-block-v1":
                replay = ROOT / "fixtures/v0.3/ocr/replay"; (replay / "output/artifacts").mkdir(parents=True, exist_ok=True)
                configuration = {"dpi": 300, "minimum_confidence": 0, "ocr_profile": profile, "orientation_degrees": orientation}
                request = build_provider_request(TESSERACT_OCR_PROVIDER_ID, "extract", input_bytes, limits=limits, configuration=configuration)
                response = {**payload, "protocol_version": "0.2", "provider_id": TESSERACT_OCR_PROVIDER_ID, "request_id": request["request_id"]}
                response.pop("artifact_bytes", None)
                if response.get("error") is None: response.pop("error", None)
                (replay / "input.pgm").write_bytes(input_bytes); (replay / "descriptor.json").write_bytes(canonical(tesseract_ocr_v03_descriptor().to_dict()) + b"\n")
                (replay / "request.json").write_bytes(canonical(request) + b"\n"); (replay / "output/response.json").write_bytes(canonical(response) + b"\n")
    for profile in MATRIX:
        left = responses[f"arm64/{profile}"]; right = responses[f"amd64/{profile}"]
        if canonical(left) != canonical(right): raise RuntimeError(f"AECCTX_OCR_ARCH_EQUIVALENCE_FAILED: {profile}")
    table = responses["arm64/eng-table-v1"]["events"][0]["payload"]
    if table["tables"][0]["topology"]["state"] != "known": raise RuntimeError("AECCTX_OCR_TABLE_LIVE_TOPOLOGY_UNKNOWN")
    summary = {"architectures": ["linux/arm64", "linux/amd64"], "profiles": sorted(MATRIX), "executions": len(responses), "equivalent": True, "ok": True}
    (output / "summary.json").write_bytes(canonical(summary) + b"\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=ROOT / "fixtures/v0.3/ocr/live")
    args = parser.parse_args(); print(json.dumps(verify(args.output), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__": raise SystemExit(main())
