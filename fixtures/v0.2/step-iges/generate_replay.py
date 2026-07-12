from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from aecctx.providers import ProviderLimits, build_provider_request
from aecctx.providers.step_iges import STEP_IGES_CONFIGURATION, STEP_IGES_IMAGE, step_iges_descriptor


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = Path(__file__).resolve().parent
WORKER = ROOT / "providers" / "step-iges-ocp" / "worker.py"
INPUTS = ("ap203-part.step", "ap214-assembly.step", "ap242-part.step", "iges53-part.igs")
LIMITS = ProviderLimits(
    max_input_bytes=10_000_000,
    max_output_bytes=10_000_000,
    max_records=100_000,
    max_files=10,
    max_recursion_depth=64,
    max_decompression_ratio=20.0,
    wall_time_seconds=60.0,
    cpu_seconds=60,
    max_memory_bytes=1_073_741_824,
    max_open_files=32,
)


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    descriptor = step_iges_descriptor()
    (FIXTURE_ROOT / "descriptor.json").write_text(canonical(descriptor.to_dict()), encoding="utf-8")
    requests_root = FIXTURE_ROOT / "requests"
    outputs_root = FIXTURE_ROOT / "outputs"
    requests_root.mkdir(exist_ok=True)
    entries = []
    for filename in INPUTS:
        entry_id = filename.rsplit(".", 1)[0]
        source = FIXTURE_ROOT / filename
        input_bytes = source.read_bytes()
        request = build_provider_request(
            descriptor.provider_id,
            "extract",
            input_bytes,
            limits=LIMITS,
            configuration=STEP_IGES_CONFIGURATION,
        )
        request_file = requests_root / f"{entry_id}.json"
        request_file.write_text(canonical(request), encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="aecctx-step-iges-replay-") as temporary:
            workspace = Path(temporary)
            input_path = workspace / request["input"]["path"]
            output = workspace / "output"
            input_path.parent.mkdir(parents=True)
            output.mkdir()
            output.chmod(0o777)
            input_path.write_bytes(input_bytes)
            input_path.chmod(0o444)
            request_path = workspace / "request.json"
            request_path.write_text(json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            request_path.chmod(0o444)
            subprocess.run(
                [
                    "/usr/local/bin/docker", "run", "--rm", "--network=none", "--read-only", "--cap-drop=ALL",
                    "--security-opt=no-new-privileges", "--user=65532:65532", "--pids-limit=1",
                    "--memory=1073741824", "--cpus=1", "--ulimit=nofile=32:32",
                    "--ulimit=fsize=10000000:10000000", "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=67108864",
                    f"--mount=type=bind,src={input_path.parent},dst=/workspace/input,readonly",
                    f"--mount=type=bind,src={request_path},dst=/workspace/request.json,readonly",
                    f"--mount=type=bind,src={output},dst=/workspace/output",
                    f"--mount=type=bind,src={WORKER},dst=/provider/worker.py,readonly",
                    "--workdir=/workspace", STEP_IGES_IMAGE, "python3", "/provider/worker.py",
                ],
                check=True,
                env={"HOME": str(workspace), "PATH": os.environ.get("PATH", "")},
            )
            destination = outputs_root / entry_id
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(output, destination)
        entries.append(
            {
                "action": "extract",
                "configuration": STEP_IGES_CONFIGURATION,
                "descriptor": "fixtures/v0.2/step-iges/descriptor.json",
                "id": entry_id,
                "input": f"fixtures/v0.2/step-iges/{filename}",
                "limits": LIMITS.to_dict(),
                "output_root": f"fixtures/v0.2/step-iges/outputs/{entry_id}",
                "request": f"fixtures/v0.2/step-iges/requests/{entry_id}.json",
                "response": f"fixtures/v0.2/step-iges/outputs/{entry_id}/response.json",
            }
        )
    (ROOT / "conformance" / "v0.2" / "step-iges-corpus.json").write_text(
        canonical({"entries": entries, "version": "0.2.0"}), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

