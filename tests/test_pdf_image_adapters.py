from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from aecctx.adapters.image import ImagePlugin, ingest_image
from aecctx.adapters.pdf import PDFPlugin, ingest_pdf
from aecctx.package import PackageReader
from aecctx.records import RecordStore
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
VECTOR_PDF = ROOT / "fixtures" / "pdf" / "minimal-vector.pdf"
RASTER_PDF = ROOT / "fixtures" / "pdf" / "minimal-raster.pdf"
IMAGE_FIXTURE = ROOT / "fixtures" / "images" / "minimal-grid.pgm"
FIXED_TIME = "2026-07-11T00:00:00Z"


def test_public_pdf_and_image_fixtures_are_parseable() -> None:
    vector = PdfReader(VECTOR_PDF)
    raster = PdfReader(RASTER_PDF)
    with Image.open(IMAGE_FIXTURE) as image:
        assert image.size == (3, 2)
        assert image.mode == "L"

    assert len(vector.pages) == 1
    assert "Vector Note" in vector.pages[0].extract_text()
    assert len(raster.pages) == 1
    assert raster.pages[0].images


def test_pdf_and_image_probes_use_content_not_extension() -> None:
    pdf_prefix = VECTOR_PDF.read_bytes()[:4096]
    pdf_probe = PDFPlugin().probe(pdf_prefix)
    image_probe = ImagePlugin().probe(IMAGE_FIXTURE.read_bytes()[:4096])

    assert pdf_probe == {"confidence": 1.0, "format": "pdf", "mutated": False, "observed_bytes": len(pdf_prefix)}
    assert image_probe["confidence"] == 1.0
    assert image_probe["format"] == "PGM"


def test_pdf_and_image_plugins_publish_complete_required_lifecycle() -> None:
    for plugin in (PDFPlugin(), ImagePlugin()):
        assert all(callable(getattr(plugin, name, None)) for name in ("describe", "probe", "extract", "finalize"))


def test_vector_pdf_preserves_paths_text_viewport_and_confidence(tmp_path: Path) -> None:
    output = tmp_path / "vector-package"

    ingest_pdf(VECTOR_PDF, output, created_at=FIXED_TIME)

    assert validate_package(output).valid
    store = RecordStore.open(output)
    primitives = [record.raw for record in store.records.values() if record.record_type == "primitive"]
    path = next(item for item in primitives if item["original_class"] == "PDF_PATH")
    text = next(item for item in primitives if item["original_class"] == "PDF_TEXT")
    assert path["coordinate_system"]["unit"] == "pt"
    assert path["container"]["value"] == "page:1"
    assert path["viewport"]["media_box"] == [0.0, 0.0, 200.0, 200.0]
    assert text["value"] == {"state": "known", "value": "Vector Note"}
    assert text["extraction_confidence"]["band"] == "full"
    assert text["interpretation_confidence"]["band"] == "unknown"


def test_raster_pdf_extracts_image_evidence_without_ocr_or_hidden_geometry(tmp_path: Path) -> None:
    output = tmp_path / "raster-package"

    ingest_pdf(RASTER_PDF, output, created_at=FIXED_TIME)

    store = RecordStore.open(output)
    raster = next(record.raw for record in store.records.values() if record.raw.get("original_class") == "PDF_RASTER_IMAGE")
    assert raster["pixel_geometry"]["unit"] == "px"
    assert raster["calibration"] == {"state": "unknown", "reason_code": "AECCTX_PDF_PIXEL_CALIBRATION_NOT_DECLARED"}
    assert raster["artifact_ref"]["path"].startswith("artifacts/pdf/page-0001-image-")
    manifest = PackageReader(output).manifest
    assert manifest["capabilities"]["text"] == "unsupported"
    assert manifest["capabilities"]["3d_geometry"] == "unsupported"
    assert "AECCTX_PDF_HIDDEN_GEOMETRY_UNSUPPORTED" in manifest["loss_summary"]


def test_image_adapter_preserves_pixel_space_and_explicit_unknown_calibration(tmp_path: Path) -> None:
    output = tmp_path / "image-package"

    ingest_image(IMAGE_FIXTURE, output, created_at=FIXED_TIME)

    assert validate_package(output).valid
    store = RecordStore.open(output)
    primitive = next(record.raw for record in store.records.values() if record.record_type == "primitive")
    assert primitive["pixel_geometry"] == {"height": 2, "origin": "top-left", "unit": "px", "width": 3}
    assert primitive["calibration"] == {"state": "unknown", "reason_code": "AECCTX_IMAGE_CALIBRATION_NOT_DECLARED"}
    assert primitive["ocr"] == {"state": "unsupported", "reason_code": "AECCTX_OCR_PROVIDER_NOT_CONFIGURED"}
    assert PackageReader(output).manifest["capabilities"]["3d_geometry"] == "unsupported"


def test_pdf_and_image_outputs_are_deterministic(tmp_path: Path) -> None:
    pdf_a = tmp_path / "pdf-a.aecctx"
    pdf_b = tmp_path / "pdf-b.aecctx"
    image_a = tmp_path / "image-a.aecctx"
    image_b = tmp_path / "image-b.aecctx"

    ingest_pdf(VECTOR_PDF, pdf_a, created_at=FIXED_TIME, package_form="zip")
    ingest_pdf(VECTOR_PDF, pdf_b, created_at=FIXED_TIME, package_form="zip")
    ingest_image(IMAGE_FIXTURE, image_a, created_at=FIXED_TIME, package_form="zip")
    ingest_image(IMAGE_FIXTURE, image_b, created_at=FIXED_TIME, package_form="zip")

    assert pdf_a.read_bytes() == pdf_b.read_bytes()
    assert image_a.read_bytes() == image_b.read_bytes()
