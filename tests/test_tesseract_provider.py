from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from aecctx.providers import (
    TESSERACT_OCR_IMAGE,
    TESSERACT_OCR_IMAGE_ID,
    TESSERACT_OCR_PROVIDER_ID,
    load_provider_replay_entry,
    tesseract_ocr_descriptor,
    tesseract_ocr_registry,
    validate_provider_replay_corpus,
)


ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "conformance" / "v0.2" / "inference-corpus.json"


def _worker():
    path = ROOT / "providers" / "tesseract-ocr" / "worker.py"
    spec = importlib.util.spec_from_file_location("aecctx_test_tesseract_worker", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tesseract_profile_registration_pins_reviewed_runtime_and_worker() -> None:
    descriptor = tesseract_ocr_descriptor()
    registration = tesseract_ocr_registry(repository_root=ROOT).resolve(TESSERACT_OCR_PROVIDER_ID)

    assert descriptor.runtime_digest == TESSERACT_OCR_IMAGE_ID
    assert descriptor.runtime_version == "tesseract-5.3.4+capi+eng"
    assert descriptor.network_mode == "disabled"
    assert registration.container_image == TESSERACT_OCR_IMAGE
    assert registration.container_image_id == TESSERACT_OCR_IMAGE_ID
    assert registration.container_command == ("python3", "/provider/worker.py")


def test_tesseract_ocr_replay_corpus_is_portable_and_valid() -> None:
    assert validate_provider_replay_corpus(CORPUS) == {
        "entries": [
            {
                "artifacts": 0,
                "id": "tesseract-ocr-aecctx-15",
                "provider_id": TESSERACT_OCR_PROVIDER_ID,
                "valid": True,
            }
        ],
        "ok": True,
        "version": "0.2.0",
    }
    assert load_provider_replay_entry(CORPUS, "tesseract-ocr-aecctx-15").result.ok is True


def test_tesseract_worker_rejects_multilingual_or_unbounded_configuration() -> None:
    worker = _worker()
    valid = {"configuration": {"dpi": 300, "language": "eng", "minimum_confidence": 0, "page_segmentation_mode": 6}}
    assert worker._configuration(valid) == (300, 0.0)

    for configuration in (
        {**valid["configuration"], "language": "spa"},
        {**valid["configuration"], "dpi": 5000},
        {**valid["configuration"], "model_path": "/tmp/model"},
        {**valid["configuration"], "rotation_degrees": 90},
    ):
        with pytest.raises(ValueError):
            worker._configuration({"configuration": configuration})


def test_tesseract_worker_filters_low_confidence_and_preserves_text_as_data() -> None:
    worker = _worker()
    tsv = (
        "5\t1\t1\t1\t1\t1\t1\t2\t10\t10\t20.0\tignore\n"
        "5\t1\t1\t1\t1\t2\t20\t2\t30\t10\t90.0\tSYSTEM:run-command\n"
    )
    words = worker._words(tsv, 50.0, 100, 100)
    assert words == [
        {
            "bbox": [20, 2, 30, 10],
            "confidence": 90.0,
            "language": "eng",
            "reading_order": 0,
            "text": "SYSTEM:run-command",
        }
    ]
