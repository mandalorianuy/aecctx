from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from aecctx.providers import ProviderLimits, build_provider_request
from aecctx.providers.dwg import DWG_CONFIGURATION, DWG_IMAGE, dwg_descriptor


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = Path(__file__).resolve().parent
WORKER = ROOT / "providers" / "libredwg" / "worker.py"
LIMITS = ProviderLimits(
    max_input_bytes=2_000_000,
    max_output_bytes=30_000_000,
    max_records=2_000,
    max_files=10,
    max_recursion_depth=64,
    max_decompression_ratio=20.0,
    wall_time_seconds=30.0,
    cpu_seconds=30,
    max_memory_bytes=1_073_741_824,
    max_open_files=32,
)


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    descriptor = dwg_descriptor()
    (FIXTURE_ROOT / "descriptor.json").write_text(canonical(descriptor.to_dict()), encoding="utf-8")
    source = FIXTURE_ROOT / "r2000-profile.dwg"
    input_bytes = source.read_bytes()
    request = build_provider_request(descriptor.provider_id, "extract", input_bytes, limits=LIMITS, configuration=DWG_CONFIGURATION)
    requests_root = FIXTURE_ROOT / "requests"
    outputs_root = FIXTURE_ROOT / "outputs"
    requests_root.mkdir(exist_ok=True)
    request_file = requests_root / "r2000-profile.json"
    request_file.write_text(canonical(request), encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="aecctx-dwg-replay-") as temporary:
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
                "--security-opt=no-new-privileges", "--user=65532:65532", "--pids-limit=2",
                "--memory=1073741824", "--cpus=1", "--ulimit=nofile=32:32",
                "--ulimit=fsize=30000000:30000000", "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16777216",
                f"--mount=type=bind,src={input_path.parent},dst=/workspace/input,readonly",
                f"--mount=type=bind,src={request_path},dst=/workspace/request.json,readonly",
                f"--mount=type=bind,src={output},dst=/workspace/output",
                f"--mount=type=bind,src={WORKER},dst=/provider/worker.py,readonly",
                "--workdir=/workspace", DWG_IMAGE, "python3", "/provider/worker.py",
            ],
            check=True,
            env={"HOME": str(workspace), "PATH": os.environ.get("PATH", "")},
        )
        destination = outputs_root / "r2000-profile"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(output, destination)
    corpus = {
        "entries": [
            {
                "action": "extract",
                "configuration": DWG_CONFIGURATION,
                "descriptor": "fixtures/v0.2/dwg/descriptor.json",
                "id": "r2000-profile",
                "input": "fixtures/v0.2/dwg/r2000-profile.dwg",
                "limits": LIMITS.to_dict(),
                "output_root": "fixtures/v0.2/dwg/outputs/r2000-profile",
                "request": "fixtures/v0.2/dwg/requests/r2000-profile.json",
                "response": "fixtures/v0.2/dwg/outputs/r2000-profile/response.json",
            }
        ],
        "version": "0.2.0",
    }
    (ROOT / "conformance" / "v0.2" / "dwg-corpus.json").write_text(canonical(corpus), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
