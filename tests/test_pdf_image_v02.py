from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from aecctx.adapters.image import ingest_image
from aecctx.adapters.pdf import ingest_pdf
from aecctx.package import PackageReader
from aecctx.providers import load_provider_replay_entry
from aecctx.records import RecordStore
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
IMAGE = ROOT / "fixtures" / "v0.2" / "inference" / "ocr-aecctx-15.png"
PDF = ROOT / "fixtures" / "v0.2" / "inference" / "native-conflict-raster.pdf"
CORPUS = ROOT / "conformance" / "v0.2" / "inference-corpus.json"
FIXED_TIME = "2026-07-12T00:00:00Z"


def replay():
    return load_provider_replay_entry(CORPUS, "tesseract-ocr-aecctx-15").result


def test_pdf_and_image_v01_defaults_remain_byte_identical_to_explicit_v01(tmp_path: Path) -> None:
    for name, ingest, source in (("image", ingest_image, IMAGE), ("pdf", ingest_pdf, PDF)):
        default = tmp_path / f"{name}-default.aecctx"
        explicit = tmp_path / f"{name}-explicit.aecctx"
        ingest(source, default, created_at=FIXED_TIME, package_form="zip")
        ingest(source, explicit, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.1.0")
        assert default.read_bytes() == explicit.read_bytes()


def test_image_v02_without_provider_preserves_unsupported_boundaries(tmp_path: Path) -> None:
    output = tmp_path / "image-v02"
    ingest_image(IMAGE, output, created_at=FIXED_TIME, aecctx_version="0.2.0")

    assert validate_package(output).valid
    manifest = PackageReader(output).manifest
    assert manifest["aecctx_version"] == "0.2.0"
    assert manifest["capabilities"]["text"] == "unsupported"
    assert manifest["capabilities"]["3d_geometry"] == "unsupported"
    assert all(record.raw["record_version"] == "0.2" for record in RecordStore.open(output).records.values())


def test_image_v02_maps_validated_replay_as_inferred_word_evidence(tmp_path: Path) -> None:
    output = tmp_path / "image-ocr"
    ingest_image(IMAGE, output, created_at=FIXED_TIME, aecctx_version="0.2.0", ocr_result=replay())

    assert validate_package(output).valid
    store = RecordStore.open(output)
    words = sorted((record.raw for record in store.records.values() if record.raw.get("original_class") == "OCR_WORD"), key=lambda item: item["reading_order"])
    assert [word["value"]["value"] for word in words] == ["AECLCTs*", "15"]
    assert all(word["evidence_class"] == "inferred" and word["inference"]["verification_state"] == "unverified" for word in words)
    assert PackageReader(output).manifest["capabilities"]["text"] == "partial"


def test_pdf_v02_keeps_native_ocr_conflict_explicit(tmp_path: Path) -> None:
    output = tmp_path / "pdf-ocr"
    ingest_pdf(PDF, output, created_at=FIXED_TIME, aecctx_version="0.2.0", ocr_result=replay())

    assert validate_package(output).valid
    store = RecordStore.open(output)
    comparison = next(record.raw for record in store.records.values() if record.raw.get("predicate") == "aecctx:ocr-native-text-comparison")
    assert comparison["value"]["state"] == "conflicted"
    assert comparison["value"]["reason_code"] == "AECCTX_OCR_NATIVE_TEXT_CONFLICT"
    assert any(record.raw.get("code") == "AECCTX_OCR_NATIVE_TEXT_CONFLICT" for record in store.records.values())
    assert PackageReader(output).manifest["capabilities"]["text"] == "partial"


def test_image_v02_ocr_packages_are_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.aecctx"
    second = tmp_path / "second.aecctx"
    result = replay()
    ingest_image(IMAGE, first, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0", ocr_result=result)
    ingest_image(IMAGE, second, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0", ocr_result=result)
    assert first.read_bytes() == second.read_bytes()


def test_failed_ocr_result_degrades_without_losing_baseline_image_evidence(tmp_path: Path) -> None:
    output = tmp_path / "failed-provider"
    failed = replace(replay(), ok=False, events=(), error={"code": "AECCTX_OCR_TIMEOUT", "message": "bounded provider timeout"})

    ingest_image(IMAGE, output, created_at=FIXED_TIME, aecctx_version="0.2.0", ocr_result=failed)

    assert validate_package(output).valid
    store = RecordStore.open(output)
    assert any(record.raw.get("code") == "AECCTX_OCR_PROVIDER_FAILED" for record in store.records.values())
    assert any(record.raw.get("original_class") == "RASTER_IMAGE" for record in store.records.values())
    assert PackageReader(output).manifest["capabilities"]["text"] == "unsupported"
