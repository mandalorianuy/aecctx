# AECCTX v0.2 OCR, Vision and Hidden-Geometry Profile

Version: `0.2.0-draft.1`
Date: 2026-07-12
Status: ACX-15 normative profile

## 1. Profile states

ACX-15 defines three separately governed outcomes:

- `pdf-image.ocr`, profile `tesseract-5.3.4-capi-eng-psm6-v1`, is `experimental` release governance and emits at most package support level `partial`;
- `pdf-image.vision` remains `target` and package support level `unsupported` because no provider vocabulary/model/privacy profile is accepted;
- `pdf-image.hidden-geometry` is a public boundary claim with package support level `unsupported`: unobserved geometry is never source evidence.

Experimental OCR is not promoted to a portable public capability until a reviewed digest-pinned provider image and executable corpus pass on every claimed provider/platform combination. Offline replay proves protocol, mapping, determinism and package behavior but is not proof that an OCR runtime exists on every host.

## 2. OCR provider

The selected provider is `org.aecctx.ocr.tesseract-tsv` version `0.2.0`, executed only through ACX-12 `oci-docker-v1`. Its bounded runtime is:

- Tesseract `5.3.4` (`tesseract-ocr=5.3.4-1build5`) through its official C API loaded with Python `ctypes` in one provider process;
- OpenMP is bounded to one thread (`OMP_NUM_THREADS=1`, `OMP_THREAD_LIMIT=1`) so the ACX-12 `pids=1` sandbox remains enforced;
- language data `eng` only;
- OCR engine mode LSTM and page segmentation mode `6`;
- TSV-equivalent word output with text, confidence, pixel bounding box and deterministic reading order;
- local execution, network disabled, no telemetry and no retained provider workspace;
- exact input bytes, request/configuration digest, response digest, runtime/image digest and resource report.

The core never installs or links Tesseract. The provider image is built or installed explicitly by an operator and must already exist. Registration identifies an allowlisted image reference and expected local image ID; preflight compares Docker's inspected immutable image ID before execution. Mismatch rejects with `AECCTX_PROVIDER_IMAGE_DIGEST_MISMATCH`. A caller cannot supply a command, worker path, shell string or source-provided argument.

## 3. Inputs, output vocabulary and budgets

OCR input in this profile is exactly one complete raster converted to canonical grayscale PGM (`P5`, decimal width/height, max value 255, LF separators, then exactly `width * height` bytes). The input artifact and region hash bind those canonical bytes, while the observed source/decoded-raster record remains a separately cited parent. This avoids encoder/backend variance across platforms without changing pixels. Cropped/rotated subregions require a future governed locator/transform profile and are not an ACX-15 claim.

Allowed configuration is limited to `language="eng"`, `page_segmentation_mode=6`, an integer `dpi` from 70 through 1200, `minimum_confidence` from 0 through 100, and explicit limits inherited from ACX-12. Unknown keys, paths, commands, callbacks, environment values, model downloads and network options are rejected.

Provider events use `aecctx.ocr.words.v1`. Each accepted word contains:

- non-empty UTF-8 text;
- confidence in `[0, 100]` as returned by the provider;
- integer pixel bounding box `[left, top, width, height]` within the input raster;
- zero-based deterministic reading-order index;
- language `eng` and source region locator.

Malformed bounds, duplicate reading order, non-finite confidence, excessive events/output, unknown vocabulary or prompt/command-like metadata remain untrusted data and fail or degrade with stable diagnostics.

## 4. AECCTX record mapping

Each OCR word becomes an `inferred` primitive, never an observed primitive. It cites the observed raster primitive and contains the shared v0.2 inference envelope with provider/runtime/model versions, local execution mode, request/response hashes, exact input/region hashes, separate extraction and interpretation confidence, deterministic reproducibility and explicit verification state.

The observed raster primitive remains unchanged. OCR pixel coordinates remain pixels unless a separately governed calibration exists. OCR text cannot establish identity, measurement authority, georeferencing, validation completeness or source geometry.

Native PDF text and OCR text remain independent records. Normalized equality produces a cited `equivalent` comparison assertion. Inequality produces a `conflicted` assertion with both native and OCR record IDs; neither value silently wins.

## 5. Replay and execution modes

The SDK accepts either:

1. a validated `ProviderResult` returned by an allowlisted ACX-12 runner; or
2. a committed/offline replay bundle containing descriptor, request, response, input and artifact hashes validated by the same protocol code.

CLI replay is explicit through `--inference-replay` plus `--inference-entry`; it never uploads data or invokes a provider. Live execution remains an SDK operation using a caller-constructed reviewed `ProviderRunner`. Provider execution/protocol failures occur before package construction and cannot mutate baseline ingest. A validated failed/rejected `ProviderResult` supplied to PDF/image ingest degrades to structured loss while retaining baseline evidence.

## 6. Vision and reconstruction boundary

No ACX-15 vision provider is accepted. Symbols, dimensions, tables, relationships and reconstruction hypotheses remain unsupported unless a future governed profile defines vocabulary, thresholds, model/runtime, privacy, reproducibility and conformance.

Occluded, cropped, redacted, behind-layer or imagined geometry remains `unsupported` as source geometry. A future reconstruction hypothesis must be `inferred`, cite visible evidence and remain excluded from identity, measurements, georeferencing, validation completeness and full geometry claims.

## 7. Compatibility and acceptance

`ingest_pdf()` and `ingest_image()` remain v0.1 by default and byte-identical to explicit `aecctx_version="0.1.0"`. v0.2 requires explicit selection. No provider is invoked unless explicitly supplied.

Acceptance requires project-authored raster/PDF fixtures; valid/equal/conflicting/empty/rejected and malformed-bound result tests; provider-disabled/unavailable boundaries; deterministic ZIP replay; prompt-like text treated as data; multilingual/rotation configuration rejection; privacy/network checks; clean core behavior without inference dependencies; stable hidden-geometry diagnostics; and mapped claim-registry entries.
