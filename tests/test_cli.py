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


def test_ingest_command_creates_valid_opaque_package(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"opaque")
    output = tmp_path / "source.aecctx"

    completed = run_cli(
        "ingest",
        str(source),
        "--output",
        str(output),
        "--form",
        "zip",
        "--created-at",
        "2026-07-11T00:00:00Z",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    assert output.is_file()
    assert json.loads(completed.stdout)["data"]["support"] == "opaque"


def test_validate_accepts_archive_form(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"opaque")
    output = tmp_path / "source.aecctx"
    created = run_cli("ingest", str(source), "--output", str(output), "--form", "zip", "--json")
    assert created.returncode == 0, created.stderr

    completed = run_cli("validate", str(output), "--json")

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["ok"] is True


def test_query_command_returns_record_ids() -> None:
    completed = run_cli("query", str(FIXTURE), 'entity.original_class == "LINE"', "--json")

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["data"]["record_ids"] == ["entity_line_1"]


def test_diff_command_ignores_identical_packages() -> None:
    completed = run_cli("diff", str(FIXTURE), str(FIXTURE), "--json")

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["data"]["semantic_change"] is False


def test_context_command_emits_index_json() -> None:
    completed = run_cli("context", str(FIXTURE), "--token-budget", "600", "--json")

    assert completed.returncode == 0, completed.stderr
    data = json.loads(completed.stdout)["data"]
    assert data["token_estimate"] <= 600
    assert "context/index.md" in data["files"]


def test_ingest_auto_selects_ifc_adapter(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "ifc" / "minimal-wall.ifc"
    output = tmp_path / "wall.aecctx"

    completed = run_cli(
        "ingest",
        str(fixture),
        "--output",
        str(output),
        "--form",
        "zip",
        "--created-at",
        "2026-07-11T00:00:00Z",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["data"]["adapter"] == "ifc"


def test_ingest_auto_selects_dxf_adapter(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "dxf" / "minimal-plan.dxf"
    output = tmp_path / "plan.aecctx"

    completed = run_cli(
        "ingest",
        str(fixture),
        "--output",
        str(output),
        "--form",
        "zip",
        "--created-at",
        "2026-07-11T00:00:00Z",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["data"]["adapter"] == "dxf"
