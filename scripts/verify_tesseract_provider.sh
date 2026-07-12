#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python_runtime="${PYTHON:-.venv/bin/python}"
expected_image_id="$($python_runtime -c 'from aecctx.providers import TESSERACT_OCR_IMAGE_ID; print(TESSERACT_OCR_IMAGE_ID)')"
actual_image_id="$(docker image inspect --format '{{.Id}}' aecctx-tesseract-ocr:0.2.0)"
test "$actual_image_id" = "$expected_image_id"

$python_runtime - <<'PY'
from pathlib import Path

from aecctx.providers import (
    OCIDockerProfile,
    ProviderLimits,
    ProviderRunner,
    TESSERACT_OCR_IMAGE,
    TESSERACT_OCR_PROVIDER_ID,
    tesseract_ocr_registry,
)

root = Path.cwd()
result = ProviderRunner(
    registry=tesseract_ocr_registry(repository_root=root),
    profile=OCIDockerProfile(image=TESSERACT_OCR_IMAGE),
    limits=ProviderLimits(
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
    ),
).run(
    TESSERACT_OCR_PROVIDER_ID,
    "extract",
    (root / "fixtures/v0.2/inference/ocr-aecctx-15.png").read_bytes(),
    configuration={"dpi": 300, "language": "eng", "minimum_confidence": 0, "page_segmentation_mode": 6},
)
assert result.ok
assert [word["text"] for word in result.events[0]["payload"]["words"]] == ["AECLCTs*", "15"]
PY

echo "aecctx tesseract provider verify: ok"
