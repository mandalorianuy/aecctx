from __future__ import annotations

import json
from pathlib import Path

from aecctx import __version__
from aecctx.conformance import run_corpus
from aecctx.release import build_release_metadata


ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "conformance" / "v0.1" / "corpus.json"


def test_public_version_and_schema_are_stable_0_1_0() -> None:
    schema = json.loads((ROOT / "schemas" / "v0.1" / "manifest.schema.json").read_text(encoding="utf-8"))

    assert __version__ == "0.1.0"
    assert schema["properties"]["aecctx_version"] == {"const": "0.1.0"}


def test_governed_conformance_corpus_proves_every_release_claim() -> None:
    report = run_corpus(CORPUS)

    assert report["ok"] is True
    assert report["version"] == "0.1.0"
    assert {entry["adapter"] for entry in report["entries"]} == {"opaque", "ifc", "dxf", "pdf", "image", "geometry"}
    assert all(entry["valid"] and entry["deterministic"] and entry["claims_match"] for entry in report["entries"])


def test_release_metadata_contains_checksums_and_spdx_sbom(tmp_path: Path) -> None:
    artifact = tmp_path / "aecctx-0.1.0-py3-none-any.whl"
    artifact.write_bytes(b"wheel fixture")

    result = build_release_metadata([artifact], output_directory=tmp_path)

    checksums = (tmp_path / "SHA256SUMS").read_text(encoding="utf-8")
    sbom = json.loads((tmp_path / "aecctx-0.1.0.spdx.json").read_text(encoding="utf-8"))
    assert artifact.name in checksums
    assert result["checksums"] == str(tmp_path / "SHA256SUMS")
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert any(package["name"] == "aecctx" and package["versionInfo"] == "0.1.0" for package in sbom["packages"])


def test_release_documentation_and_automation_exist() -> None:
    required = [
        ROOT / "CHANGELOG.md",
        ROOT / "docs" / "compatibility.md",
        ROOT / "docs" / "releases" / "v0.1.0.md",
        ROOT / "scripts" / "verify_release.sh",
        ROOT / ".github" / "workflows" / "release.yml",
    ]

    assert all(path.is_file() for path in required)
    release_notes = (ROOT / "docs" / "releases" / "v0.1.0.md").read_text(encoding="utf-8")
    assert "pip install aecctx==0.1.0" not in release_notes
    assert "releases/download/v0.1.0/aecctx-0.1.0-py3-none-any.whl" in release_notes


def test_release_workflow_uploads_each_asset_once() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "dist/aecctx-0.1.0*" not in workflow
    for asset in (
        "dist/aecctx-0.1.0-py3-none-any.whl",
        "dist/aecctx-0.1.0.tar.gz",
        "dist/SHA256SUMS",
        "dist/aecctx-0.1.0.spdx.json",
    ):
        assert workflow.count(asset) == 1
