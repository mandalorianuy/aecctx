# ACX-06 Acceptance Evidence

Date: 2026-07-11
Status: completed

## Implemented

- Optional pypdf adapter for PDF page trees, media boxes, vector content-stream operators, extracted text, and decoded raster XObjects.
- Optional Pillow adapter for validated raster dimensions, mode, safe metadata, pixel limits, and format detection.
- Separate PDF point coordinates and raster pixel coordinates with explicit origins and units.
- Explicit `unknown` calibration for PDF raster and standalone images; pixels are never treated as construction units.
- Separate extraction and interpretation confidence on every path, text, raster, and image primitive.
- OCR/vision state is `unsupported` when no optional provider is configured; the core requires neither inference nor network access.
- Hidden 3D geometry and georeferencing remain explicit `unsupported` claims with structured diagnostics.
- Deterministic extracted raster artifacts and auto-probed CLI selection for PDF and image content.

## Conformance fixtures and commands

The public corpus includes a one-page vector/text PDF, a one-page raster-XObject PDF, and a 3x2 grayscale PGM image. All are project-authored, uncompressed minimal fixtures.

```text
uv sync --extra test
uv run pytest tests/test_pdf_image_adapters.py
./scripts/verify.sh
aecctx ingest fixtures/pdf/minimal-vector.pdf --output vector.aecctx --json
aecctx ingest fixtures/pdf/minimal-raster.pdf --output raster.aecctx --json
aecctx ingest fixtures/images/minimal-grid.pgm --output image.aecctx --json
```

Observed result: 65 total tests passed. Vector text/path, raster artifact, page viewport, pixel geometry, confidence, calibration, unsupported OCR/hidden geometry, package validation, auto-probing, and repeated deterministic ZIP output all passed.

## Licensing and scope

pypdf is BSD-3-Clause and Pillow is MIT-CMU; both are optional, separately installed extras and are not bundled into the core wheel. PDF actions/JavaScript are not executed and links are not followed. No inference provider, generic SVG/GLB preview, MCP, consumer mapping, or WoodFraming code was implemented in ACX-06.
