from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from aecctx.providers.protocol import ProviderResult


ROOT = Path(__file__).parents[1]
INPUT = b"v03-project-authored-raster"
INPUT_SHA = hashlib.sha256(INPUT).hexdigest()


def _worker():
    path = ROOT / "providers/tesseract-ocr/worker.py"
    spec = importlib.util.spec_from_file_location("aecctx_test_tesseract_v03_worker", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _result(payload: dict[str, object]) -> ProviderResult:
    return ProviderResult(
        ok=True,
        events=({"event_type": "primitive", "payload": payload, "sequence": 0, "source_locator": f"sha256:{INPUT_SHA}"},),
        artifacts=(), artifact_bytes={}, diagnostics=(),
        capability_report={"text": {"affected": [], "fallback": "source pixels", "reason_codes": [], "support_level": "partial"}},
        resource_usage={"events": 1},
        attestation={
            "deterministic": True, "network_mode": "disabled", "provider_id": "org.aecctx.ocr.tesseract-tsv",
            "provider_version": "0.3.0", "request_digest": "1" * 64, "response_payload_digest": "2" * 64,
            "runtime_digest": "sha256:" + "3" * 64, "runtime_version": "tesseract-5.3.4+capi+eng+spa+por",
        },
    )


def _live_result(profile: str) -> ProviderResult:
    raw = json.loads((ROOT / "fixtures/v0.3/ocr/live" / f"arm64-{profile}.json").read_text(encoding="utf-8"))
    return ProviderResult(**raw)


def _payload() -> dict[str, object]:
    return {
        "schema": "aecctx.ocr.layout.v1", "profile": "eng-table-v1", "language": "eng",
        "page_segmentation_mode": 6, "orientation_degrees": 0, "width": 200, "height": 100,
        "reading_order": {"state": "known", "value": "tsv-hierarchy"},
        "words": [
            {"id": "w0", "bbox": [10, 10, 30, 10], "confidence": 90.0, "text": "A", "block": 1, "paragraph": 1, "line": 1, "word": 1, "reading_order": 0},
            {"id": "w1", "bbox": [100, 10, 30, 10], "confidence": 91.0, "text": "B", "block": 1, "paragraph": 1, "line": 1, "word": 2, "reading_order": 1},
            {"id": "w2", "bbox": [10, 40, 30, 10], "confidence": 92.0, "text": "C", "block": 1, "paragraph": 1, "line": 2, "word": 1, "reading_order": 2},
            {"id": "w3", "bbox": [100, 40, 30, 10], "confidence": 93.0, "text": "D", "block": 1, "paragraph": 1, "line": 2, "word": 2, "reading_order": 3},
        ],
        "lines": [{"id": "l0", "bbox": [10, 10, 120, 10], "block": 1, "paragraph": 1, "line": 1, "word_ids": ["w0", "w1"]}, {"id": "l1", "bbox": [10, 40, 120, 10], "block": 1, "paragraph": 1, "line": 2, "word_ids": ["w2", "w3"]}],
        "blocks": [{"id": "b0", "bbox": [10, 10, 120, 40], "block": 1, "line_ids": ["l0", "l1"]}],
        "tables": [{"id": "t0", "topology": {"state": "known", "value": {"rows": [["w0", "w1"], ["w2", "w3"]], "column_count": 2}}}],
    }


def test_worker_v03_configuration_is_closed_and_path_free() -> None:
    worker = _worker()
    request = {"configuration": {"dpi": 300, "minimum_confidence": 20, "ocr_profile": "spa-block-v1", "orientation_degrees": 90}}
    assert worker._configuration_v03(request) == (300, 20.0, "spa", 6, 90, "spa-block-v1")
    for bad in (
        {**request["configuration"], "ocr_profile": "rus-block-v1"},
        {**request["configuration"], "model_path": "/tmp/model"},
        {**request["configuration"], "orientation_degrees": 45},
    ):
        with pytest.raises(ValueError):
            worker._configuration_v03({"configuration": bad})


def test_tsv_layout_retains_hierarchy_and_only_proves_closed_table() -> None:
    worker = _worker()
    tsv = "\n".join([
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
        "5\t1\t1\t1\t1\t1\t10\t10\t30\t10\t90\tA", "5\t1\t1\t1\t1\t2\t100\t10\t30\t10\t91\tB",
        "5\t1\t1\t1\t2\t1\t10\t40\t30\t10\t92\tC", "5\t1\t1\t1\t2\t2\t100\t40\t30\t10\t93\tD",
    ])
    layout = worker._layout(tsv, 0, 200, 100, "eng-table-v1", "eng", 6, 0)
    assert [word["id"] for word in layout["words"]] == ["w0", "w1", "w2", "w3"]
    assert layout["tables"][0]["topology"]["state"] == "known"
    not_table = worker._layout(tsv, 0, 200, 100, "eng-block-v1", "eng", 6, 0)
    assert not_table["tables"] == []


def test_layout_mapping_emits_inferred_word_line_block_and_table_evidence() -> None:
    from aecctx.inference import map_ocr_result
    mapping = map_ocr_result(_result(_payload()), input_bytes=INPUT, source_id="src", parent_record_id="image", source_locator="pixel-canvas", width=200, height=100, recorded_at="2026-07-14T00:00:00Z")
    assert [item["original_class"] for item in mapping.primitives] == ["OCR_WORD"] * 4 + ["OCR_LINE"] * 2 + ["OCR_BLOCK", "OCR_TABLE"]
    assert all(item["evidence_class"] == "inferred" for item in mapping.primitives)
    assert mapping.primitives[-1]["topology"]["state"] == "known"
    assert mapping.primitives[0]["language"] == "eng"


def test_layout_mapping_rejects_mixed_script_profile_and_preserves_native_conflict() -> None:
    from aecctx.inference import InferenceMappingError, map_ocr_result
    bad = _payload(); bad["language"] = "rus"
    with pytest.raises(InferenceMappingError):
        map_ocr_result(_result(bad), input_bytes=INPUT, source_id="src", parent_record_id="image", source_locator="pixel-canvas", width=200, height=100, recorded_at="2026-07-14T00:00:00Z")
    mapping = map_ocr_result(_result(_payload()), input_bytes=INPUT, source_id="src", parent_record_id="image", source_locator="pixel-canvas", width=200, height=100, recorded_at="2026-07-14T00:00:00Z", native_text_records=[{"record_id": "native", "value": {"state": "known", "value": "different"}}])
    assert mapping.assertions[0]["value"]["state"] == "conflicted"
    malformed = _payload(); malformed["unexpected"] = "not closed"
    with pytest.raises(InferenceMappingError) as invalid:
        map_ocr_result(_result(malformed), input_bytes=INPUT, source_id="src", parent_record_id="image", source_locator="pixel-canvas", width=200, height=100, recorded_at="2026-07-14T00:00:00Z")
    assert invalid.value.code == "AECCTX_OCR_LAYOUT_INVALID"


def test_image_adapter_and_cli_accept_digest_bound_layout_replay(tmp_path: Path) -> None:
    from aecctx.adapters.image import ingest_image
    from aecctx.package import PackageReader
    from aecctx.records import RecordStore
    from aecctx.validation import validate_package
    output = tmp_path / "layout-package"
    source = ROOT / "fixtures/v0.3/ocr/spa-block.png"
    ingest_image(source, output, created_at="2026-07-14T00:00:00Z", aecctx_version="0.2.0", ocr_result=_live_result("spa-block-v1"))
    assert validate_package(output).valid
    classes = {record.raw.get("original_class") for record in RecordStore.open(output).records.values()}
    assert {"OCR_WORD", "OCR_LINE", "OCR_BLOCK"} <= classes
    assert PackageReader(output).manifest["capabilities"]["text"] == "partial"


def test_v03_replay_corpus_is_valid_and_cli_ingests_it(tmp_path: Path) -> None:
    import subprocess, sys
    from aecctx.providers import validate_provider_replay_corpus
    corpus = ROOT / "conformance/v0.3/ocr-replay-corpus.json"
    assert validate_provider_replay_corpus(corpus)["ok"] is True
    output = tmp_path / "cli-layout"
    completed = subprocess.run([sys.executable, "-m", "aecctx", "ingest", str(ROOT / "fixtures/v0.3/ocr/spa-block.png"), "--output", str(output), "--adapter", "image", "--aecctx-version", "0.2.0", "--inference-replay", str(corpus), "--inference-entry", "tesseract-ocr-v03-spa-layout"], cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr


def test_pdf_adapter_maps_the_same_layout_replay_without_promoting_pixels(tmp_path: Path) -> None:
    from aecctx.adapters.pdf import ingest_pdf
    from aecctx.records import RecordStore
    from aecctx.validation import validate_package
    output = tmp_path / "pdf-layout"
    ingest_pdf(ROOT / "fixtures/v0.3/ocr/spa-raster.pdf", output, created_at="2026-07-14T00:00:00Z", aecctx_version="0.2.0", ocr_result=_live_result("spa-block-v1"))
    assert validate_package(output).valid
    classes = {record.raw.get("original_class") for record in RecordStore.open(output).records.values()}
    assert {"PDF_RASTER_IMAGE", "OCR_WORD", "OCR_LINE", "OCR_BLOCK"} <= classes


def test_negative_blank_low_confidence_corrupt_and_unlisted_script_cases_are_explicit() -> None:
    from PIL import Image, UnidentifiedImageError
    worker = _worker()
    blank = worker._layout("", 0, 10, 10, "eng-block-v1", "eng", 6, 0)
    low = worker._layout("5\t1\t1\t1\t1\t1\t0\t0\t5\t5\t10\tfaint", 50, 10, 10, "eng-block-v1", "eng", 6, 0)
    assert blank["words"] == [] and low["words"] == []
    with pytest.raises((UnidentifiedImageError, OSError)):
        Image.open(ROOT / "fixtures/v0.3/ocr/corrupt.png").verify()
    assert (ROOT / "fixtures/v0.3/ocr/mixed-script.png").is_file()
