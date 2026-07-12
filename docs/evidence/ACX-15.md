# ACX-15 acceptance evidence

Date: 2026-07-12
Status: completed
Task: OCR, vision and reconstruction hypotheses
Decision: ACXD-020
Completion commit: `feat: complete ACX-15 bounded OCR inference profile`

## Authority and bounded outcomes

The normative authority is `docs/specs/inference-v02-profile.md`:

| Claim | Governance | Support |
|---|---|---|
| `pdf-image.ocr` | exact English Tesseract C-API/PSM-6 profile, live arm64 OCI image plus portable offline replay | `experimental`, package `partial` |
| `pdf-image.vision` | no vocabulary, model, privacy profile or provider accepted | target remains `unsupported` |
| `pdf-image.hidden-geometry` | unobserved geometry cannot be source evidence | public `unsupported` boundary |

No OCR result establishes source identity, measurements, georeferencing, geometry completeness or validation authority.

## Implementation

- ACX-12 OCI preflight now verifies a mutable local tag against an allowlisted immutable Docker image ID and rejects drift with `AECCTX_PROVIDER_IMAGE_DIGEST_MISMATCH`.
- Reviewed provider `org.aecctx.ocr.tesseract-tsv@0.2.0`: Ubuntu Noble Tesseract `5.3.4`, official C API through `ctypes`, English data, LSTM/PSM 6 and Pillow decode validation.
- The sandbox remains at `pids=1`; OpenMP is fixed to one thread. Runtime network, telemetry, downloads and workspace retention are absent.
- Provider requests allow only exact bounded configuration. Outputs are schema/hash/attestation validated before mapping.
- Each accepted word is an `inferred` v0.2 primitive with exact input/region, request, response, provider/runtime and confidence provenance.
- Native PDF text remains observed and independent. Equality is cited; disagreement emits `conflicted` evidence and neither value wins.
- `ingest_image()` and `ingest_pdf()` support explicit v0.2 SDK opt-in. CLI uses `--inference-replay` plus `--inference-entry`; it never invokes or uploads to a provider.
- Rejected/failed provider results degrade with structured diagnostics while baseline PDF/image evidence remains available.
- Default and explicit v0.1 PDF/image packages remain byte-identical.

## Fixtures and reproducibility

All raster/PDF content and glyph rendering code were authored in this repository for publication under the project license.

| Artifact | SHA-256 |
|---|---|
| `generate_fixtures.py` | `5fb7e0169f2e41e0da28f7af8127d263ccbd261442be9b9e0eb99c3dc324fb6a` |
| `native-conflict-raster.pdf` | `5cf2da012f7ac193e199a38237619654f8d64485e024c5d20e8e58341b417c7f` |
| `ocr-aecctx-15.png` | `901aea5d7dadedeaf3b0f3ae5559d511b490c14463d2b7af3d443599838f9f1b` |
| provider request | `c2374b2f3432b61879346940eb3982129ea81e634124f5786272385460ab5f41` |
| provider response | `104445dc98a7b02158ac00bd9aae385b5358e1d52a43226429b16d2a9cd441b1` |

`conformance/v0.2/inference-corpus.json` binds the input, descriptor, request, response and output root. Reproduction uses `fixtures/v0.2/inference/generate_replay.py`. Portable validation uses the same provider protocol validator as live execution.

## Validation evidence

- Focused inference/PDF/image/CLI/provider tests: passed.
- Portable replay corpus: valid, one entry, zero artifacts, exact attestation and hashes.
- Live provider: `./scripts/verify_tesseract_provider.sh` passed against image ID `sha256:6d52ebcafef0ccdf59f58beccc7483c16a6e160fc94e3c3ea59f3f10c991f492`; OCR words were `AECLCTs*` and `15` under the unchanged `pids=1` sandbox.
- Full suite: `189 passed`.
- `python scripts/check_spec_contract.py`: passed; claim registry valid with no errors; inference replay corpus valid.
- `python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues`: healthy, zero issues.
- `./scripts/verify_portable.sh`: passed; wheel and sdist built successfully.
- `./scripts/verify.sh`: passed after evidence and ACX-16 promotion; deterministic v0.1 corpus and release verification remained green.

## Security, privacy, license and platform boundary

Inputs, decoded pixels and OCR strings are untrusted data. Prompt-like text is preserved only as unverified content. The worker cannot receive caller commands, paths, environment or model settings. Runtime network is disabled; there is no implicit consent, upload, telemetry or retention.

The provider image is operator-built and excluded from core packages. Tesseract and English data are Apache-2.0; Pillow is HPND; image distribution obligations are documented in `docs/licenses/tesseract-ocr-provider.md`. The live claim is limited to the tested Linux arm64 container image. Offline replay is platform-portable mapping evidence, not proof of a live runtime elsewhere.

## Residuals and promotion

Additional languages, rotated/complex layouts, tables/symbols/dimensions, image/PDF vision, reconstruction hypotheses, portable live provider matrices and hidden geometry extraction remain unclaimed or `unsupported`. A future capability requires a new governed profile before implementation.

No WoodFraming path, `WFDomain`, `WFImport`, network service or LLM dependency was accessed or modified. ACX-15 is completed and ACX-16 is promoted to `pending-next`; ACX-16 was not executed.
