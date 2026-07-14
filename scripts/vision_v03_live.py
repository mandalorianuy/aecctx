#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from aecctx.providers import OCIDockerProfile, ProviderLimits, ProviderRunner, VISION_CONFIGURATION, VISION_PROVIDER_ID, build_provider_request, vision_descriptor, vision_registry

ROOT = Path(__file__).resolve().parents[1]


def canonical(value: object) -> bytes: return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def verify(output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True); data = (ROOT / "fixtures/v0.3/vision/positive.pgm").read_bytes(); values = {}
    limits = ProviderLimits(wall_time_seconds=30, cpu_seconds=30)
    for architecture in ("arm64", "amd64"):
        image = f"aecctx-vision-raster-rules:0.3.0-linux-{architecture}"
        runner = ProviderRunner(registry=vision_registry(repository_root=ROOT), profile=OCIDockerProfile(image=image, platform="linux", architecture=architecture), limits=limits)
        result = runner.run(VISION_PROVIDER_ID, "extract", data, configuration=VISION_CONFIGURATION)
        if not result.ok: raise RuntimeError(f"AECCTX_VISION_LIVE_FAILED: {architecture}")
        payload = asdict(result); values[architecture] = payload; (output / f"{architecture}.json").write_bytes(canonical(payload) + b"\n")
        if architecture == "arm64":
            replay = ROOT / "fixtures/v0.3/vision/replay"; (replay / "output/artifacts").mkdir(parents=True, exist_ok=True)
            request = build_provider_request(VISION_PROVIDER_ID, "extract", data, limits=limits, configuration=VISION_CONFIGURATION)
            response = {**payload, "protocol_version": "0.2", "provider_id": VISION_PROVIDER_ID, "request_id": request["request_id"]}; response.pop("artifact_bytes", None)
            if response.get("error") is None: response.pop("error", None)
            (replay / "input.pgm").write_bytes(data); (replay / "descriptor.json").write_bytes(canonical(vision_descriptor().to_dict()) + b"\n"); (replay / "request.json").write_bytes(canonical(request) + b"\n"); (replay / "output/response.json").write_bytes(canonical(response) + b"\n")
    if canonical(values["arm64"]) != canonical(values["amd64"]): raise RuntimeError("AECCTX_VISION_ARCH_EQUIVALENCE_FAILED")
    kinds = [item["kind"] for item in values["arm64"]["events"][0]["payload"]["candidates"]]
    if kinds != ["region.rectangle", "table.grid", "symbol.cross", "dimension.linear"]: raise RuntimeError("AECCTX_VISION_VOCABULARY_FAILED")
    summary = {"architectures": ["linux/arm64", "linux/amd64"], "equivalent": True, "executions": 2, "kinds": kinds, "ok": True}; (output / "summary.json").write_bytes(canonical(summary) + b"\n"); return summary


if __name__ == "__main__": print(json.dumps(verify(ROOT / "fixtures/v0.3/vision/live"), sort_keys=True, separators=(",", ":")))
