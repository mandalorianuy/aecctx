from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from aecctx.providers import ProviderLimits, build_provider_request, tesseract_ocr_descriptor


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = FIXTURE_ROOT / "ocr-output"
INPUT = FIXTURE_ROOT / "ocr-aecctx-15.png"
WORKER = ROOT / "providers" / "tesseract-ocr" / "worker.py"
IMAGE = "aecctx-tesseract-ocr:0.2.0"
CONFIGURATION = {"dpi": 300, "language": "eng", "minimum_confidence": 0, "page_segmentation_mode": 6}
LIMITS = ProviderLimits(
    max_input_bytes=1_000_000,
    max_output_bytes=1_000_000,
    max_records=100,
    max_files=10,
    max_recursion_depth=8,
    max_decompression_ratio=20.0,
    wall_time_seconds=30.0,
    cpu_seconds=30,
    max_memory_bytes=512 * 1024 * 1024,
    max_open_files=32,
)


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    input_bytes = INPUT.read_bytes()
    descriptor = tesseract_ocr_descriptor()
    request = build_provider_request(
        descriptor.provider_id,
        "extract",
        input_bytes,
        limits=LIMITS,
        configuration=CONFIGURATION,
    )
    FIXTURE_ROOT.joinpath("ocr-descriptor.json").write_text(canonical(descriptor.to_dict()), encoding="utf-8")
    FIXTURE_ROOT.joinpath("ocr-request.json").write_text(canonical(request), encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="aecctx-ocr-replay-") as temporary:
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
                "--security-opt=no-new-privileges", "--user=65532:65532", "--pids-limit=1", "--memory=536870912",
                "--cpus=1", "--ulimit=nofile=32:32", "--ulimit=fsize=1000000:1000000",
                "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16777216",
                f"--mount=type=bind,src={input_path.parent},dst=/workspace/input,readonly",
                f"--mount=type=bind,src={request_path},dst=/workspace/request.json,readonly",
                f"--mount=type=bind,src={output},dst=/workspace/output",
                f"--mount=type=bind,src={WORKER},dst=/provider/worker.py,readonly",
                "--workdir=/workspace", IMAGE, "python3", "/provider/worker.py",
            ],
            check=True,
            env={"HOME": str(workspace), "PATH": os.environ.get("PATH", "")},
        )
        if OUTPUT_ROOT.exists():
            shutil.rmtree(OUTPUT_ROOT)
        shutil.copytree(output, OUTPUT_ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
