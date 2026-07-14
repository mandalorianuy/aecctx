from __future__ import annotations

import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

import aecctx
from aecctx.release import VERSION, build_release_metadata
from aecctx.release_v03_conformance import scan_release_artifacts, validate_v03_release_corpus


ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "conformance/v0.3/corpus.json"


def _mutated_corpus(tmp_path: Path) -> tuple[dict[str, object], Path]:
    document = json.loads(CORPUS.read_text(encoding="utf-8"))
    path = tmp_path / "corpus.json"
    return document, path


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def test_v03_release_version_and_aggregate_are_exact() -> None:
    result = validate_v03_release_corpus(CORPUS, repository_root=ROOT)

    assert aecctx.__version__ == VERSION == "0.3.0"
    assert result == {
        "blocked_tasks": ["ACX-34"],
        "claim_count": 19,
        "completed_tasks": 13,
        "mapped_claim_count": 19,
        "ok": True,
        "positive_claim_count": 17,
        "suite_count": 17,
        "unsupported_claim_count": 2,
        "version": "0.3.0",
    }


def test_v03_release_rejects_missing_duplicate_and_unmapped_claims(tmp_path: Path) -> None:
    document, path = _mutated_corpus(tmp_path)
    document["tasks"][0]["claim_ids"].append("missing.claim")
    _write_json(path, document)
    with pytest.raises(ValueError, match="unmapped claim"):
        validate_v03_release_corpus(path, repository_root=ROOT)

    document, path = _mutated_corpus(tmp_path)
    document["suites"].append(dict(document["suites"][0]))
    _write_json(path, document)
    with pytest.raises(ValueError, match="duplicate or invalid suite"):
        validate_v03_release_corpus(path, repository_root=ROOT)


def test_v03_release_rejects_digest_drift(tmp_path: Path) -> None:
    document, path = _mutated_corpus(tmp_path)
    document["suites"][0]["sha256"] = "0" * 64
    _write_json(path, document)
    with pytest.raises(ValueError, match="suite digest mismatch"):
        validate_v03_release_corpus(path, repository_root=ROOT)


def test_v03_release_rejects_target_blocked_promotion_and_replay_as_live(tmp_path: Path) -> None:
    claims = json.loads((ROOT / "conformance/v0.3/claims.json").read_text(encoding="utf-8"))
    rvt = next(claim for claim in claims["claims"] if claim["id"] == "rvt.external-provider")
    rvt["support_level"] = "partial"
    claims_path = tmp_path / "claims.json"
    _write_json(claims_path, claims)
    document, corpus_path = _mutated_corpus(tmp_path)
    document["claims"] = str(claims_path)
    document["suites"][0]["path"] = str(claims_path)
    document["suites"][0]["sha256"] = __import__("hashlib").sha256(claims_path.read_bytes()).hexdigest()
    _write_json(corpus_path, document)
    with pytest.raises(ValueError, match="blocked task claim must remain unsupported"):
        validate_v03_release_corpus(corpus_path, repository_root=ROOT)

    claims = json.loads((ROOT / "conformance/v0.3/claims.json").read_text(encoding="utf-8"))
    live = next(claim for claim in claims["claims"] if claim["id"] == "step-iges.xde-structure")
    live["platform_scope"] = ["portable-replay"]
    _write_json(claims_path, claims)
    document, corpus_path = _mutated_corpus(tmp_path)
    document["claims"] = str(claims_path)
    document["suites"][0]["path"] = str(claims_path)
    document["suites"][0]["sha256"] = __import__("hashlib").sha256(claims_path.read_bytes()).hexdigest()
    _write_json(corpus_path, document)
    with pytest.raises(ValueError, match="replay-only"):
        validate_v03_release_corpus(corpus_path, repository_root=ROOT)


def test_v03_release_scans_restricted_and_consumer_artifact_leakage(tmp_path: Path) -> None:
    safe = tmp_path / "safe.whl"
    with zipfile.ZipFile(safe, "w") as archive:
        archive.writestr("aecctx/__init__.py", '__version__ = "0.3.0"\n')
        archive.writestr("aecctx-0.3.0.dist-info/METADATA", "Name: aecctx\nVersion: 0.3.0\n")
        archive.writestr("aecctx-0.3.0/docs/integration/woodframing-boundary.md", "consumer boundary only\n")
    assert scan_release_artifacts([safe]) == {"artifact_count": 1, "ok": True}

    consumer = tmp_path / "consumer.zip"
    with zipfile.ZipFile(consumer, "w") as archive:
        archive.writestr("aecctx/woodframing_bridge.py", "pass\n")
    with pytest.raises(ValueError, match="consumer leakage"):
        scan_release_artifacts([consumer])

    native = tmp_path / "native.tar.gz"
    with tarfile.open(native, "w:gz") as archive:
        payload = b"\x7fELF" + b"\0" * 32
        info = tarfile.TarInfo("aecctx-0.3.0/providers/libredwg/libredwg.so")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    with pytest.raises(ValueError, match="restricted binary"):
        scan_release_artifacts([native])


def test_v03_release_metadata_is_deterministic_and_spdx(tmp_path: Path) -> None:
    wheel = tmp_path / "aecctx-0.3.0-py3-none-any.whl"
    plugin = tmp_path / "aecctx-inspector-0.3.0.zip"
    wheel.write_bytes(b"wheel")
    plugin.write_bytes(b"plugin")

    first = build_release_metadata([plugin, wheel], output_directory=tmp_path)
    sums = Path(first["checksums"]).read_bytes()
    sbom = Path(first["sbom"]).read_bytes()
    second = build_release_metadata([wheel, plugin], output_directory=tmp_path)

    assert sums == Path(second["checksums"]).read_bytes()
    assert sbom == Path(second["sbom"]).read_bytes()
    assert Path(first["sbom"]).name == "aecctx-0.3.0.spdx.json"
    assert json.loads(sbom)["spdxVersion"] == "SPDX-2.3"


def test_v03_release_documents_workflow_and_compatibility_are_bound() -> None:
    for path in (
        ROOT / "docs/compatibility-v0.3.md",
        ROOT / "docs/releases/v0.3.0.md",
        ROOT / "docs/release/v0.3.0-evidence-index.md",
        ROOT / "docs/release/v0.3.0-supply-chain.md",
        ROOT / "docs/evidence/ACX-38.md",
    ):
        assert path.is_file()
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    for asset in (
        "dist/aecctx-0.3.0-py3-none-any.whl",
        "dist/aecctx-0.3.0.tar.gz",
        "dist/aecctx-inspector-0.3.0.zip",
        "dist/SHA256SUMS",
        "dist/aecctx-0.3.0.spdx.json",
    ):
        assert workflow.count(asset) == 1
    assert "docs/releases/v0.3.0.md" in workflow
    release_script = (ROOT / "scripts/verify_release.sh").read_text(encoding="utf-8")
    assert "(cd dist && sha256sum -c SHA256SUMS)" in release_script
    aggregate = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert aggregate["compatibility"] == ["conformance/v0.1/corpus.json", "conformance/v0.2/corpus.json"]
