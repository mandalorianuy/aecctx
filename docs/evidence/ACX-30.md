# ACX-30 acceptance evidence

Date: 2026-07-14
Status: acceptance candidate; authoritative after governed GitHub squash merge
Decision/profile: ACXD-039 and `docs/specs/vision-v03-profile.md`

## Implemented result and claim table

| Claim | Profile/provider | Level | Conformance |
|---|---|---|---|
| `pdf-image.vision-inference` | `visible-raster-rules-v1`; `org.aecctx.vision.raster-rules@0.3.0` | `partial` | `v03-vision-acx30`; `tests/test_vision_v03.py`; vision checker |
| `pdf-image.reconstruction-hypothesis` | visible planar boundary over exact rectangle pixels | `partial` | same digest-bound corpus and mapper boundary tests |

The provider is project-owned Apache-2.0 code running on Python 3.12.10/PSF-2.0 through `oci-docker-v1`. It has no model, weights, network, prompt, credential, telemetry, retention or core dependency. The schema, mapper, image/PDF SDK paths and explicit CLI replay produce only inferred records/assertions with input/request/response/runtime hashes.

## Fixtures, TDD and reproducibility

Nine deterministic project-authored PGM fixtures cover positive rectangle/grid/cross/linear-dimension candidates, blank, crop, occlusion, redaction, prompt-like pixels, unsupported rotation, corrupt input and calibration-conflict posture. `fixtures/v0.3/vision/generate_fixtures.py --check` binds their exact bytes and publication origin.

RED first failed four tests because `aecctx.vision` and the worker did not exist. The adapter test then failed because `vision_result` was not accepted, and the CLI test failed because the explicit vision flags did not exist. GREEN covers mapper/schema/bounds/hash/attestation, worker rules/configuration, negative fixture matrix, image/PDF SDK and CLI replay.

The reviewed Dockerfile pins official Python `3.12.10-slim-bookworm` index digest `sha256:fd95fa...`. Live images are exact local IDs `sha256:8331cca...` for Linux arm64 and `sha256:22f267...` for Linux amd64. Both live runs emitted byte-identical canonical `ProviderResult` values containing exactly rectangle, table grid, cross and linear-dimension candidates. Replay validation passes but is not used as live evidence.

## Security, privacy, license and platform gates

- Closed configuration; no caller executable/model/module/vocabulary/threshold path.
- Network-disabled, read-only, non-root OCI execution with the existing complete enforcement axes.
- PGM dimensions, bytes, candidates, schema, coordinates, references, counts and provider attestations fail closed.
- Prompt-like source content is inert pixels; crop, occlusion, redaction and unsupported rotation do not trigger repair or invented candidates.
- Core validation/query/diff/context and ingest without explicit result remain offline and provider-free.
- Provider code/images are absent from wheel/sdist; only the public packaged schema enters artifacts.
- Positive live scope is exactly Linux arm64/amd64. Native macOS/Windows and unavailable images remain unsupported.

## Commands and evidence

- Baseline: `PATH="$PWD/.venv/bin:$PATH" ./scripts/verify_portable.sh` — 253 portable tests and 700 passed/10 skipped full tests before changes.
- RED/GREEN: `pytest tests/test_vision_v03.py -q` — sequential missing mapper/worker, adapter and CLI failures followed by 8 passed.
- Live: `python scripts/vision_v03_live.py` — 2 executions, cross-architecture canonical equality.
- Conformance: `python scripts/check_vision_v03_conformance.py --require-public --require-live-images`.
- Final local gates passed: `python3 scripts/check_spec_contract.py`; focused adapter/CLI tests; `./scripts/verify_portable.sh` with 253 portable tests, 708 passed/10 skipped full tests and wheel/sdist checks; and `AGENT_BASELINE_ROOT=/Users/facundo/desarrollo/codex-agent-baseline ./scripts/verify.sh` with healthy `baseline-shared-v1` integration and `aecctx verify: ok`. Exact-head CI and the governed squash merge remain delivery evidence.

## Capability/loss, non-scope and residual risk

Rule confidence `1.0` means only exact pixel-rule satisfaction. It does not establish semantic truth. Source pixels remain authority. All AEC identity/classification, written dimensions, physical measurement, scale, units, CRS, validation completeness, source/full/hidden geometry, occlusion repair, 3D reconstruction, compliance, engineering approval and consumer semantics remain unsupported.

Anti-aliased or learned recognition, arbitrary rotations, other raster formats at the provider boundary, remote/commercial vision services and model-based inference remain non-claims. The main residual risk is narrow corpus overfitting; the exact rule vocabulary and no-repair behavior make that ceiling explicit rather than presenting general vision support.

`/Users/facundo/desarrollo/woodframing` was not modified. ACX-31 is the sole governed successor and was not executed.
