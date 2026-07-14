from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path

from aecctx.providers import OCIDockerProfile, ProviderLimits, ProviderRunner, build_provider_request
from aecctx.providers.step_iges import (
    STEP_IGES_OCI_TARGETS,
    STEP_IGES_PROVIDER_ID,
    STEP_IGES_XDE_CONFIGURATION,
    step_iges_descriptor,
    step_iges_registry,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = Path(__file__).resolve().parent
LIMITS = ProviderLimits(max_input_bytes=10_000_000, max_output_bytes=20_000_000, max_records=100_000, max_files=20, max_recursion_depth=64, max_decompression_ratio=20.0, wall_time_seconds=60.0, cpu_seconds=60, max_memory_bytes=1_073_741_824, max_open_files=32)
INPUTS = (
    ("ap203-xde", ROOT / "fixtures/v0.2/step-iges/ap203-part.step", False),
    ("ap214-xde", ROOT / "fixtures/v0.2/step-iges/ap214-assembly.step", False),
    ("ap242-xde", ROOT / "fixtures/v0.2/step-iges/ap242-part.step", False),
    ("iges53-xde", ROOT / "fixtures/v0.2/step-iges/iges53-part.igs", False),
    ("ap214-metadata", FIXTURE_ROOT / "ap214-xde.step", False),
    ("ap214-metadata-healed", FIXTURE_ROOT / "ap214-xde.step", True),
)


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n"


def _reference(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main() -> None:
    descriptor = step_iges_descriptor()
    (FIXTURE_ROOT / "descriptor.json").write_text(_canonical(descriptor.to_dict()), encoding="utf-8")
    requests = FIXTURE_ROOT / "requests"
    outputs = FIXTURE_ROOT / "outputs"
    requests.mkdir(exist_ok=True)
    outputs.mkdir(exist_ok=True)
    target = STEP_IGES_OCI_TARGETS[0]
    runner = ProviderRunner(
        registry=step_iges_registry(repository_root=ROOT),
        profile=OCIDockerProfile(image=target.image, platform=target.platform, architecture=target.architecture),
        limits=LIMITS,
    )
    entries = []
    for entry_id, source, healing in INPUTS:
        configuration = json.loads(json.dumps(STEP_IGES_XDE_CONFIGURATION))
        configuration["healing"]["enabled"] = healing
        source_bytes = source.read_bytes()
        request = build_provider_request(STEP_IGES_PROVIDER_ID, "extract", source_bytes, limits=LIMITS, configuration=configuration)
        request_path = requests / f"{entry_id}.json"
        request_path.write_text(_canonical(request), encoding="utf-8")
        result = runner.run(STEP_IGES_PROVIDER_ID, "extract", source_bytes, configuration=configuration)
        if not result.ok:
            raise RuntimeError(f"provider failed for {entry_id}: {result.error}")
        destination = outputs / entry_id
        if destination.exists():
            shutil.rmtree(destination)
        (destination / "artifacts").mkdir(parents=True)
        for path, content in result.artifact_bytes.items():
            artifact = destination / path
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_bytes(content)
        response = {
            "protocol_version": "0.2",
            "provider_id": STEP_IGES_PROVIDER_ID,
            "request_id": request["request_id"],
            "ok": result.ok,
            "events": list(result.events),
            "artifacts": list(result.artifacts),
            "diagnostics": list(result.diagnostics),
            "capability_report": result.capability_report,
            "resource_usage": result.resource_usage,
            "attestation": result.attestation,
        }
        (destination / "response.json").write_text(_canonical(response), encoding="utf-8")
        source_relative = source.relative_to(ROOT).as_posix()
        entries.append({"action": "extract", "configuration": configuration, "descriptor": "fixtures/v0.3/step-iges/descriptor.json", "id": entry_id, "input": source_relative, "limits": LIMITS.to_dict(), "output_root": f"fixtures/v0.3/step-iges/outputs/{entry_id}", "request": f"fixtures/v0.3/step-iges/requests/{entry_id}.json", "response": f"fixtures/v0.3/step-iges/outputs/{entry_id}/response.json"})
    (ROOT / "conformance/v0.3/step-iges-corpus.json").write_text(
        _canonical(
            {
                "entries": entries,
                "fixture": _reference(FIXTURE_ROOT / "ap214-xde.step"),
                "generator": _reference(Path(__file__).resolve()),
                "profile": _reference(ROOT / "docs/specs/step-iges-v03-profile.md"),
                "schema": _reference(ROOT / "schemas/v0.2/step-iges-xde-event.schema.json"),
                "worker": _reference(ROOT / "providers/step-iges-ocp/worker.py"),
                "version": "0.2.0",
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
