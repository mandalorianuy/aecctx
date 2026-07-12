from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from aecctx.package import PackageReader


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
    assert payload["data"]["logical_digest"] == "a28454b8afdbc42b791df4a9c928020d69235d65bbb7b9bd26e96c239a8473a9"
    assert payload["data"]["source_ids"] == ["src_minimal"]


def test_version_command_is_machine_readable() -> None:
    completed = run_cli("version", "--json")

    assert completed.returncode == 0
    assert json.loads(completed.stdout) == {
        "data": {"version": "0.1.0"},
        "diagnostics": [],
        "ok": True,
    }


def test_root_help_registers_signing_without_removing_existing_commands() -> None:
    completed = run_cli("--help")

    assert completed.returncode == 0
    for command in ("validate", "info", "version", "ingest", "query", "diff", "context", "sign", "verify-signatures"):
        assert command in completed.stdout


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


def test_ingest_ifc_v02_is_explicitly_available_from_cli(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "v0.2" / "ifc" / "ifc4-native-2d-georef.ifc"
    output = tmp_path / "ifc-v02.aecctx"

    completed = run_cli(
        "ingest",
        str(fixture),
        "--output",
        str(output),
        "--aecctx-version",
        "0.2.0",
        "--created-at",
        "2026-07-12T00:00:00Z",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    assert PackageReader(output).manifest["aecctx_version"] == "0.2.0"
    assert json.loads(completed.stdout)["data"]["aecctx_version"] == "0.2.0"


def test_ingest_dxf_v02_is_explicitly_available_from_cli(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "v0.2" / "dxf" / "r2018-semantics-3d-ascii.dxf"
    output = tmp_path / "dxf-v02"

    completed = run_cli(
        "ingest",
        str(fixture),
        "--output",
        str(output),
        "--adapter",
        "dxf",
        "--aecctx-version",
        "0.2.0",
        "--created-at",
        "2026-07-12T00:00:00Z",
        "--json",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["data"]["adapter"] == "dxf"
    assert payload["data"]["aecctx_version"] == "0.2.0"
    assert PackageReader(output).manifest["aecctx_version"] == "0.2.0"


def test_ingest_v02_rejects_adapter_without_governed_v02_profile(tmp_path: Path) -> None:
    fixture = tmp_path / "opaque.bin"
    fixture.write_bytes(b"opaque")

    completed = run_cli(
        "ingest",
        str(fixture),
        "--output",
        str(tmp_path / "opaque-v02.aecctx"),
        "--adapter",
        "opaque",
        "--aecctx-version",
        "0.2.0",
        "--json",
    )

    assert completed.returncode == 2
    assert json.loads(completed.stdout)["diagnostics"][0]["code"] == "AECCTX_INGEST_VERSION_UNSUPPORTED"


def test_ingest_geometry_v02_accepts_coordinate_profile_from_cli(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "v0.2" / "mesh" / "triangle-unknown.obj"
    coordinate_profile = ROOT / "fixtures" / "v0.2" / "mesh" / "profiles" / "scale-mm-to-m.json"
    output = tmp_path / "mesh-v02"

    completed = run_cli(
        "ingest",
        str(fixture),
        "--output",
        str(output),
        "--adapter",
        "geometry",
        "--aecctx-version",
        "0.2.0",
        "--mesh-coordinate-profile",
        str(coordinate_profile),
        "--created-at",
        "2026-07-12T00:00:00Z",
        "--json",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert PackageReader(output).manifest["aecctx_version"] == "0.2.0"
    assert "geometry/calibrated-scene.glb" in {item["path"] for item in PackageReader(output).manifest["artifacts"]}


def test_mesh_coordinate_profile_is_rejected_outside_geometry_v02(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "v0.2" / "mesh" / "triangle-unknown.obj"
    coordinate_profile = ROOT / "fixtures" / "v0.2" / "mesh" / "profiles" / "scale-mm-to-m.json"
    completed = run_cli(
        "ingest",
        str(fixture),
        "--output",
        str(tmp_path / "mesh-v01"),
        "--adapter",
        "geometry",
        "--mesh-coordinate-profile",
        str(coordinate_profile),
        "--json",
    )

    assert completed.returncode == 2
    assert json.loads(completed.stdout)["diagnostics"][0]["code"] == "AECCTX_INGEST_FAILED"


def test_ingest_image_v02_accepts_explicit_validated_inference_replay(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "v0.2" / "inference" / "ocr-aecctx-15.png"
    corpus = ROOT / "conformance" / "v0.2" / "inference-corpus.json"
    output = tmp_path / "image-ocr-v02"

    completed = run_cli(
        "ingest",
        str(fixture),
        "--output",
        str(output),
        "--adapter",
        "image",
        "--aecctx-version",
        "0.2.0",
        "--inference-replay",
        str(corpus),
        "--inference-entry",
        "tesseract-ocr-aecctx-15",
        "--created-at",
        "2026-07-12T00:00:00Z",
        "--json",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout)["data"]["aecctx_version"] == "0.2.0"
    assert PackageReader(output).manifest["capabilities"]["text"] == "partial"


def test_ingest_step_iges_v02_accepts_explicit_validated_provider_replay(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "v0.2" / "step-iges" / "ap214-assembly.step"
    corpus = ROOT / "conformance" / "v0.2" / "step-iges-corpus.json"
    output = tmp_path / "step-v02.aecctx"

    completed = run_cli(
        "ingest", str(fixture), "--output", str(output), "--aecctx-version", "0.2.0",
        "--provider-replay", str(corpus), "--provider-entry", "ap214-assembly",
        "--created-at", "2026-07-12T00:00:00Z", "--form", "zip", "--json",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout)["data"]["adapter"] == "step-iges"
    assert PackageReader(output).manifest["capabilities"]["3d_geometry"] == "partial"


def test_ingest_step_iges_replay_options_are_paired_and_v02_only(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "v0.2" / "step-iges" / "ap214-assembly.step"
    corpus = ROOT / "conformance" / "v0.2" / "step-iges-corpus.json"
    missing = run_cli("ingest", str(fixture), "--output", str(tmp_path / "missing"), "--provider-replay", str(corpus), "--json")
    v01 = run_cli(
        "ingest", str(fixture), "--output", str(tmp_path / "v01"), "--provider-replay", str(corpus),
        "--provider-entry", "ap214-assembly", "--json",
    )
    assert missing.returncode == 2
    assert v01.returncode == 2


def test_ingest_dwg_v02_accepts_explicit_validated_provider_replay(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "v0.2" / "dwg" / "r2000-profile.dwg"
    corpus = ROOT / "conformance" / "v0.2" / "dwg-corpus.json"
    output = tmp_path / "dwg-v02.aecctx"

    completed = run_cli(
        "ingest", str(fixture), "--output", str(output), "--aecctx-version", "0.2.0",
        "--provider-replay", str(corpus), "--provider-entry", "r2000-profile",
        "--created-at", "2026-07-12T00:00:00Z", "--form", "zip", "--json",
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout)["data"]["adapter"] == "dwg"
    assert PackageReader(output).manifest["capabilities"]["2d_geometry"] == "partial"


def test_ingest_dwg_replay_is_v02_only_and_provider_scoped(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "v0.2" / "dwg" / "r2000-profile.dwg"
    corpus = ROOT / "conformance" / "v0.2" / "dwg-corpus.json"
    v01 = run_cli(
        "ingest", str(fixture), "--output", str(tmp_path / "v01"), "--provider-replay", str(corpus),
        "--provider-entry", "r2000-profile", "--json",
    )
    wrong = run_cli(
        "ingest", str(fixture), "--output", str(tmp_path / "wrong"), "--adapter", "step-iges",
        "--aecctx-version", "0.2.0", "--provider-replay", str(corpus), "--provider-entry", "r2000-profile", "--json",
    )
    assert v01.returncode == 2
    assert wrong.returncode == 2


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


def test_ingest_auto_selects_pdf_and_image_adapters(tmp_path: Path) -> None:
    cases = [
        (ROOT / "fixtures" / "pdf" / "minimal-vector.pdf", "pdf"),
        (ROOT / "fixtures" / "images" / "minimal-grid.pgm", "image"),
    ]
    for index, (fixture, adapter) in enumerate(cases):
        output = tmp_path / f"output-{index}.aecctx"
        completed = run_cli("ingest", str(fixture), "--output", str(output), "--form", "zip", "--json")
        assert completed.returncode == 0, completed.stderr
        assert json.loads(completed.stdout)["data"]["adapter"] == adapter


def test_ingest_auto_selects_geometry_adapter(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures" / "geometry" / "minimal-triangle.obj"
    output = tmp_path / "mesh.aecctx"

    completed = run_cli("ingest", str(fixture), "--output", str(output), "--form", "zip", "--json")

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["data"]["adapter"] == "geometry"
