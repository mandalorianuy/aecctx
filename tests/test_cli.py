from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "fixtures" / "minimal-aecctx"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "aecctx", *args],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_validate_json_writes_only_json_to_stdout() -> None:
    completed = run_cli("validate", str(FIXTURE), "--json")

    assert completed.returncode == 0
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["data"]["package_id"] == "pkg_minimal_fixture"


def test_validate_failure_writes_diagnostic_to_stderr(tmp_path: Path) -> None:
    completed = run_cli("validate", str(tmp_path))

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "AECCTX_MANIFEST_MISSING" in completed.stderr


def test_info_json_reports_package_identity() -> None:
    completed = run_cli("info", str(FIXTURE), "--json")

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["data"]["logical_digest"] == "7ca4067f732dc1aed30c1be1257437ed009742e8d85f318a1ee1d0b6b6026b1b"
    assert payload["data"]["source_ids"] == ["src_minimal"]


def test_version_command_is_machine_readable() -> None:
    completed = run_cli("version", "--json")

    assert completed.returncode == 0
    assert json.loads(completed.stdout) == {
        "data": {"version": "0.1.0.dev0"},
        "diagnostics": [],
        "ok": True,
    }

