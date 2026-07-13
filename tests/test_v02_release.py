from __future__ import annotations

import json
from pathlib import Path

import pytest

from aecctx.release import VERSION, build_release_metadata
from aecctx.release_conformance import validate_release_corpus


ROOT = Path(__file__).parents[1]


def test_reference_release_version_is_0_2_0() -> None:
    import aecctx

    assert aecctx.__version__ == VERSION == "0.2.0"


def test_v02_release_corpus_maps_every_non_target_claim() -> None:
    result = validate_release_corpus(ROOT / "conformance/v0.2/corpus.json", repository_root=ROOT)

    assert result["ok"] is True
    assert result["version"] == "0.2.0"
    assert result["claim_count"] > 0
    assert result["mapped_claim_count"] == result["claim_count"]
    assert result["blocked_tasks"] == ["ACX-19"]


def test_release_corpus_rejects_positive_claim_without_evidence(tmp_path: Path) -> None:
    claims = json.loads((ROOT / "conformance/v0.2/claims.json").read_text(encoding="utf-8"))
    positive = next(claim for claim in claims["claims"] if claim["status"] == "public")
    positive["evidence"] = None
    claims_path = tmp_path / "claims.json"
    claims_path.write_text(json.dumps(claims), encoding="utf-8")
    corpus = json.loads((ROOT / "conformance/v0.2/corpus.json").read_text(encoding="utf-8"))
    corpus["claims"] = str(claims_path)
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(json.dumps(corpus), encoding="utf-8")

    with pytest.raises(ValueError, match="evidence"):
        validate_release_corpus(corpus_path, repository_root=ROOT)


def test_release_metadata_is_versioned_and_deterministic(tmp_path: Path) -> None:
    wheel = tmp_path / "aecctx-0.2.0-py3-none-any.whl"
    plugin = tmp_path / "aecctx-inspector-0.2.0.zip"
    wheel.write_bytes(b"wheel")
    plugin.write_bytes(b"plugin")

    first = build_release_metadata([plugin, wheel], output_directory=tmp_path)
    first_sums = Path(first["checksums"]).read_bytes()
    first_sbom = Path(first["sbom"]).read_bytes()
    second = build_release_metadata([wheel, plugin], output_directory=tmp_path)

    assert first_sums == Path(second["checksums"]).read_bytes()
    assert first_sbom == Path(second["sbom"]).read_bytes()
    assert Path(first["sbom"]).name == "aecctx-0.2.0.spdx.json"


def test_v02_release_documents_and_workflow_are_version_consistent() -> None:
    for path in (
        ROOT / "docs/releases/v0.2.0.md",
        ROOT / "docs/release/v0.2.0-evidence-index.md",
        ROOT / "docs/release/v0.2.0-supply-chain.md",
        ROOT / "docs/evidence/ACX-23.md",
    ):
        assert path.is_file()

    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    for asset in (
        "dist/aecctx-0.2.0-py3-none-any.whl",
        "dist/aecctx-0.2.0.tar.gz",
        "dist/aecctx-inspector-0.2.0.zip",
        "dist/SHA256SUMS",
        "dist/aecctx-0.2.0.spdx.json",
    ):
        assert workflow.count(asset) == 1
    assert "docs/releases/v0.2.0.md" in workflow
