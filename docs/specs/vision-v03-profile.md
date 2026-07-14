# Bounded visible-raster vision profile

Version: `0.3.0`
Date: 2026-07-14
Status: Normative ACX-30 profile under ACXD-039

## 1. Provider and execution boundary

The only admitted provider is `org.aecctx.vision.raster-rules@0.3.0`, a project-owned Apache-2.0 Python 3.12 worker executed through the reviewed `oci-docker-v1` profile on exactly `linux/arm64` and `linux/amd64`. It uses only the Python standard library, accepts binary PGM (`P5`, max value 255), disables network, has no model, weights, prompt, credential, telemetry or retention path, and is not a core dependency.

The exact profile is `visible-raster-rules-v1`. Configuration is closed to `foreground_threshold=32`, `minimum_component_pixels=5`, `maximum_candidates=128` and `emit_reconstruction=true`. Callers cannot select executable paths, modules, vocabulary, thresholds or code.

## 2. Closed vocabulary

The provider may emit only:

- `region.rectangle`: one connected component whose foreground pixels are exactly a one-pixel closed axis-aligned rectangular perimeter, minimum 12 by 12 pixels;
- `table.grid`: one connected component with three through eight complete horizontal grid lines and three through eight complete vertical grid lines, each separated by at least four pixels;
- `symbol.cross`: one connected component equal to one odd-length horizontal and one odd-length vertical stroke crossing at their centres, each at least five pixels;
- `dimension.linear`: one connected component equal to one horizontal stroke with equal three- or five-pixel terminal ticks;
- `relationship.contains`: deterministic pixel-bounds containment between accepted candidates;
- `reconstruction.planar-boundary`: a hypothesis over the visible rectangle perimeter only.

Every candidate and relationship is `inferred`. `reconstruction.planar-boundary` retains pixel coordinates and may never become source geometry, a measurement, a 3D solid or hidden/unobserved geometry.

## 3. Confidence and states

Exact rule matches have interpretation confidence `1.0`; this means rule satisfaction, not semantic truth. Multiple mutually incompatible candidates over the same foreground pixels are emitted as `conflicted`, never selected. Broken, occluded, redacted, cropped, rotated or non-exact patterns are absent with stable diagnostics rather than repaired. Empty input is a successful result with no candidates and `AECCTX_VISION_NO_CANDIDATE`.

Coordinates are integer top-left pixel bounds. Calibration, unit and CRS inputs are forbidden. If an adapter has separate calibration evidence, vision output neither validates nor conflicts-resolves it.

## 4. Provider event and mapping

The provider emits exactly one `primitive` event with payload schema `aecctx.vision.candidates.v1`. The response binds input, request, response, runtime and image identity hashes through the existing provider protocol. The mapper validates the packaged schema before creating neutral records.

Provider/source prose is never interpreted. Prompt-like raster text is pixels and cannot change configuration, vocabulary or execution. Provider output is untrusted and cannot bypass schema, bounds, count, digest or attestation validation.

## 5. Reproducibility, privacy and security

The profile is deterministic: identical PGM bytes and fixed configuration produce byte-identical canonical events on both claimed architectures. Live execution, not replay alone, is required for each architecture. Input never leaves the network-disabled OCI workspace and is deleted with that workspace. No image is published by AECCTX; operators build the reviewed recipe and bind exact local image IDs.

Malformed headers, dimensions above 4096 by 4096, pixel-count mismatch, more than 128 candidates, out-of-bounds geometry, unknown fields, wrong event count/schema, provider failure, unavailable image, replay drift and digest mismatch fail closed.

## 6. Fixtures and claims

Project-authored fixtures cover exact positive patterns, ambiguity/conflict payloads, absence, crop, occlusion, redaction, prompt-like pixels, rotation, corrupt input and calibration conflict. Their generator, bytes, responses, replay and live results are content-addressed in `conformance/v0.3/vision-corpus.json`.

`pdf-image.vision-inference` and `pdf-image.reconstruction-hypothesis` may become public `partial` only after live Linux arm64/amd64 equivalence, mapper/adapter/CLI, adversarial, packaging, full repository and exact-head CI gates pass.

## 7. Non-claims

The profile does not recognize AEC object identity, room use, wall/door/window semantics, written dimensions, physical measurements, units, scale, CRS, topology beyond the exact visible grid rule, occluded content, hidden geometry, 3D shape, compliance, completeness, engineering approval or consumer semantics. Other image formats at the provider boundary, arbitrary rotations, anti-aliasing, learned models and remote vision services remain unsupported.
