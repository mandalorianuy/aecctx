from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aecctx.adapters.dxf import DXFPlugin, SourceBundleError, ingest_dxf, load_source_bundle
from aecctx.package import PackageReader
from aecctx.records import RecordStore
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "fixtures/v0.3/dxf"
FIXED_TIME = "2026-07-14T00:00:00Z"


def _records(package: Path, record_type: str) -> list[dict[str, object]]:
    store = RecordStore.open(package)
    return [record.raw for record in store.records.values() if record.record_type == record_type]


def test_v03_fixture_corpus_is_exact_and_reproducible() -> None:
    corpus = json.loads((ROOT / "conformance/v0.3/dxf-corpus.json").read_text(encoding="utf-8"))
    assert corpus["version"] == "0.3.0"
    assert corpus["origin"] == "project-authored Apache-2.0 fixture corpus"
    for entry in corpus["entries"]:
        path = ROOT / entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


def test_source_bundle_validates_all_members_before_use() -> None:
    bundle = load_source_bundle(FIXTURES / "xref-bundle")
    assert bundle.root.logical_path == "root.dxf"
    assert [entry.logical_path for entry in bundle.entries] == ["refs/child.dxf", "refs/nested/nested.dxf", "root.dxf"]
    assert bundle.total_bytes == sum(entry.byte_size for entry in bundle.entries)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("escape", "AECCTX_DXF_BUNDLE_PATH_UNSAFE"),
        ("digest", "AECCTX_DXF_BUNDLE_DIGEST_MISMATCH"),
        ("symlink", "AECCTX_DXF_BUNDLE_MEMBER_NOT_REGULAR"),
    ],
)
def test_source_bundle_rejects_unsafe_members_before_parser(tmp_path: Path, mutation: str, code: str) -> None:
    source = FIXTURES / "xref-bundle"
    import shutil
    shutil.copytree(source, tmp_path / "bundle")
    manifest_path = tmp_path / "bundle/source-bundle.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mutation == "escape":
        manifest["entries"][1]["path"] = "../escape.dxf"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    elif mutation == "digest":
        manifest["entries"][1]["sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    else:
        member = tmp_path / "bundle/refs/child.dxf"
        member.unlink()
        member.symlink_to(source / "refs/child.dxf")
    with pytest.raises(SourceBundleError) as caught:
        load_source_bundle(tmp_path / "bundle")
    assert caught.value.code == code


def test_v03_curves_preserve_source_and_derived_fidelity(tmp_path: Path) -> None:
    output = tmp_path / "curves.aecctx"
    ingest_dxf(FIXTURES / "r2007-curves-ascii.dxf", output, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0")
    assert validate_package(output).valid
    primitives = _records(output, "primitive")
    by_class = {record["original_class"]: record for record in primitives if record.get("original_class") in {"ELLIPSE", "SPLINE", "HELIX", "RAY", "XLINE", "MLINE", "MESH"}}
    assert set(by_class) == {"ELLIPSE", "SPLINE", "HELIX", "RAY", "XLINE", "MLINE", "MESH"}
    assert all(record["dxf_v03"]["source_geometry"]["state"] == "known" for record in by_class.values())
    for name in {"ELLIPSE", "SPLINE", "HELIX"}:
        sampled = by_class[name]["dxf_v03"]["sampled_path"]
        assert sampled["state"] == "known"
        assert sampled["value"]["fidelity"] == "tessellated"
        assert len(sampled["value"]["vertices"]) <= 4096
    assert not any(term in record["kind"].lower() for record in _records(output, "entity") for term in {"wall", "beam", "panel", "stud", "joist", "rafter"})


def test_v03_release_ascii_binary_and_default_compatibility(tmp_path: Path) -> None:
    descriptor = DXFPlugin().describe()
    assert descriptor["v03_public_profiles"] == {
        "geometry": "dxf-selected-releases-geometry-v03:partial",
        "source_semantics": "dxf-selected-releases-source-semantics-v03:partial",
        "source_bundle": "dxf-content-addressed-xref-bundle-v1:partial",
    }
    for name, version in (("r12-curves-ascii.dxf", "AC1009"), ("r2004-curves-binary.dxf", "AC1018"), ("r2007-curves-ascii.dxf", "AC1021")):
        output = tmp_path / name
        ingest_dxf(FIXTURES / name, output, created_at=FIXED_TIME, aecctx_version="0.2.0")
        assert _records(output, "source")[0]["detected_format"]["value"] == version


def test_v03_bundle_traversal_is_source_separated_and_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.aecctx"
    second = tmp_path / "second.aecctx"
    for output in (first, second):
        ingest_dxf(FIXTURES / "xref-bundle", output, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0")
    assert first.read_bytes() == second.read_bytes()
    sources = _records(first, "source")
    assert {record["bundle_logical_path"] for record in sources} == {"root.dxf", "refs/child.dxf", "refs/nested/nested.dxf"}
    assert len({record["source_id"] for record in sources}) == 3
    xref_primitives = [record for record in _records(first, "primitive") if record.get("bundle_logical_path") != "root.dxf"]
    assert {record["original_class"] for record in xref_primitives} >= {"ELLIPSE", "SPLINE"}
    assert not any(record["code"] == "AECCTX_DXF_XREF_NOT_TRAVERSED" for record in _records(first, "diagnostic"))
    assert set(PackageReader(first).manifest["source_ids"]) == {record["source_id"] for record in sources}


def test_v03_bundle_cycles_and_acis_remain_explicit(tmp_path: Path) -> None:
    import shutil
    shutil.copytree(FIXTURES / "xref-bundle", tmp_path / "cycle")
    child = tmp_path / "cycle/refs/child.dxf"
    child.write_bytes((tmp_path / "cycle/root.dxf").read_bytes())
    manifest_path = tmp_path / "cycle/source-bundle.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(item for item in manifest["entries"] if item["path"] == "refs/child.dxf")
    entry["bytes"] = child.stat().st_size
    entry["sha256"] = hashlib.sha256(child.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SourceBundleError) as caught:
        ingest_dxf(tmp_path / "cycle", tmp_path / "output", aecctx_version="0.2.0")
    assert caught.value.code == "AECCTX_DXF_BUNDLE_XREF_CYCLE"


def test_v03_cli_accepts_content_addressed_bundle(tmp_path: Path) -> None:
    from aecctx.cli import main
    output = tmp_path / "cli-output"
    assert main(["ingest", str(FIXTURES / "xref-bundle"), "--aecctx-version", "0.2.0", "--output", str(output), "--json"]) == 0
    assert validate_package(output).valid
