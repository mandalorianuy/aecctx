# ACX-29 acceptance evidence

Date: 2026-07-14
Status: acceptance candidate; authoritative after governed GitHub squash merge
Decision/profile: ACXD-037 and `docs/specs/ocr-v03-profile.md`

## Implemented result

- Closed `aecctx.ocr.layout.v1` event schema with exact `eng`, `spa` and `por` profiles, PSM 3/4/6 and orthogonal orientation corrections. Unknown configuration keys, executable/model/tessdata paths, unlisted language/script combinations and arbitrary PSM fail closed.
- Tesseract TSV hierarchy maps separately to inferred words, lines and blocks. `eng-table-v1` emits known topology only for the fixed equal-row/two-to-eight-column/12-pixel alignment rule; every other topology remains explicit unknown.
- Image and PDF adapters accept only digest-bound validated results and retain input-region, request, response and runtime hashes. Native text conflict remains conflicted and neither value wins. CLI replay uses the existing offline provider protocol.
- The ACX-15/24 English image and registration are unchanged. ACX-29 uses a separate reviewed operator-built recipe with exact Ubuntu Noble `eng`, `spa` and `por` data; no engine, trained data or provider image enters the wheel/sdist.

## TDD and conformance

- RED: the new suite initially failed four tests because `_configuration_v03`, `_layout` and `aecctx.ocr.layout.v1` mapping did not exist.
- Focused GREEN: `pytest tests/test_ocr_v03.py tests/test_tesseract_provider.py tests/test_inference_v02.py tests/test_pdf_image_v02.py tests/test_provider_multiarch.py -q` passes 39 tests.
- Eleven project-authored fixtures cover English, Spanish, Portuguese, rotated, multicolumn, table, blank, low-confidence, mixed-script sentinel, corrupt and PDF-raster cases. Project-authored bitmap glyphs plus stdlib PNG/PDF encoders make regeneration byte-exact; pinned Pillow supplies only the in-memory grayscale raster API.
- `scripts/ocr_v03_live.py` passed 12 live OCI executions: all six request profiles on both Linux arm64 and amd64. Canonical ProviderResult bytes are identical across architectures for every profile; the live table topology is known. Exact image IDs, response bytes and replay are bound by `conformance/v0.3/ocr-corpus.json`.
- SDK image/PDF mapping, CLI replay, schema mirror, replay validation, security negatives and package validation pass. `python scripts/check_ocr_v03_conformance.py --require-live-images` passes before the public transition.
- Final public checker passed all 11 fixtures, six profiles, 12 live executions, replay/schema mirrors and wheel/sdist restricted-artifact scans.
- `./scripts/verify.sh` passed its portable subset (253 tests), full suite (699 passed, 10 intentional skips), deterministic corpora, wheel/sdist and clean release checks, plus healthy `baseline-shared-v1` integration with zero issues. Exact-SHA GitHub CI and squash merge remain delivery acceptance evidence.
- The first published SHA exposed cross-platform drift in Pillow's environment-selected default font; the replacement SHA then exposed zlib-dependent PNG byte drift. CI correctly rejected both fixture regenerations. The final correction uses project-authored bitmap glyphs and deterministic stdlib PNG/PDF encoders, normalizes architecture-only Tesseract confidence noise to the governed three-decimal precision, and binds the regenerated corpus. Final exact-head CI is authoritative.

## Claim ceiling, security and residuals

`pdf-image.ocr-layout` is public `partial` only for the ACXD-037 matrix and Linux arm64/amd64 provider execution. Raster pixels and native PDF text remain higher-authority source evidence. OCR cannot establish identity, source geometry, hidden geometry, dimensions, CRS, validation completeness, engineering approval or consumer semantics.

Other languages/scripts, language combinations, handwriting, arbitrary orientation/deskew, arbitrary PSM/models, table spans/headers/borders/semantics, vision and reconstruction remain unsupported. Input is untrusted; corrupt/hash-invalid/out-of-bounds/oversize/configuration-invalid cases fail closed, network is disabled and caller paths cannot select provider code or models.

`/Users/facundo/desarrollo/woodframing` was not modified. ACX-30 is the sole governed successor and was not executed.
