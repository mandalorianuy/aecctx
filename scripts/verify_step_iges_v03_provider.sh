#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python_runtime="${PYTHON:-.venv/bin/python}"
"$python_runtime" scripts/check_step_iges_v03_conformance.py --require-public --require-live-images
AECCTX_RUN_STEP_IGES_V03_PROVIDER=1 "$python_runtime" -m pytest -q tests/test_step_iges_v03.py -k live

echo "aecctx STEP/IGES v0.3 live provider: ok"
