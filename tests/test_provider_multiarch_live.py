from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).parents[1]


@pytest.mark.skipif(os.environ.get("AECCTX_RUN_PROVIDER_MULTIARCH") != "1", reason="six-image live OCI matrix is opt-in")
def test_live_provider_matrix_is_equivalent_and_adversarially_bounded(tmp_path: Path) -> None:
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/provider_multiarch.py"), "verify", "--output-root", str(tmp_path)],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads((tmp_path / "verification-summary.json").read_text(encoding="utf-8"))["ok"] is True
    assert len(list((tmp_path / "executions").glob("*.json"))) == 6
