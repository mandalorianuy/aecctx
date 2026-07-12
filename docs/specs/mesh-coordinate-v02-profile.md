# AECCTX v0.2 Mesh Coordinate Qualification Profile

Version: `0.2.0-draft.1`
Date: 2026-07-12
Status: ACX-16 normative profile
Decision authority: ACXD-016 and ACXD-027

## 1. Scope and claims

ACX-16 defines two bounded public `partial` claims selected only with `aecctx_version="0.2.0"`:

- `mesh.declared-coordinate-metadata` preserves the coordinate facts defined by the source format and keeps absent facts explicit;
- `mesh.manual-registration` accepts an explicit, provenance-bearing calibration profile and produces manual assertions plus derived geometry without rewriting source vertices, faces, transforms or hashes.

The profile covers self-contained OBJ, STL, glTF 2.0 and GLB 2.0 inputs through `trimesh==4.12.2`. Other trimesh releases, external resources, vendor coordinate extensions and later glTF versions are unclaimed.

OBJ and STL do not receive units, axes or CRS from filename, scale, common practice or `trimesh.units.units_from_metadata()`. glTF 2.0 declares meters, radians and a right-handed frame with `+Y` up and `+Z` forward; those facts are source-declared by the format specification. glTF 2.0 does not declare a geographic CRS.

## 2. Source evidence and safe loading

All inputs are untrusted data. Geometry loading uses exact source bytes with an explicit format and no filesystem or network resolver. OBJ material libraries, glTF buffer/image URIs other than embedded data URIs, scripts, callbacks, links and source-provided commands are not opened or executed. Unsupported external references remain structured loss.

The adapter preserves:

- exact source hash and immutable source record;
- original local vertices and faces;
- format/version and source-defined units/frame facts when the format defines them;
- bounded scene-graph edge transforms exposed by the reviewed trimesh API, with deterministic edge locators;
- source-to-derived GLB transforms and representation fidelity.

The adapter never calls a unit-guessing API. Missing units use `AECCTX_MESH_UNITS_NOT_DECLARED`; missing CRS uses `AECCTX_MESH_CRS_NOT_DECLARED`; absent frame metadata uses `AECCTX_MESH_FRAME_NOT_DECLARED`.

## 3. Calibration profile

The profile is a JSON object validated before geometry work. Its canonical JSON SHA-256 is recorded on every manual/derived output. It contains:

- `profile_version = "0.2.0"`;
- `mode = "scale" | "matrix" | "control_points"`;
- `author = {"id": <non-empty string>}` with optional display name;
- positive finite `tolerance`, expressed in target units;
- optional manual `source_units` and `source_frame` expectations;
- required `target_units` and `target_frame`;
- optional `target_crs` only for `matrix` and `control_points` modes; it contains a required non-empty `horizontal` identifier and optional non-empty `vertical` identifier, each bounded to 256 printable characters;
- exactly one mode payload.

Supported unit symbols are `m`, `mm`, `cm`, `in` and `ft`. A frame contains three signed, orthogonal source-axis labels chosen from `+X`, `-X`, `+Y`, `-Y`, `+Z`, `-Z`, using each absolute axis once, plus `handedness = "right" | "left"`.

If a manual source unit/frame contradicts source-declared evidence, the result is `conflicted` with both alternatives and no calibrated artifact is emitted. Unknown source metadata may be qualified manually, but the original source field remains `unknown`.

### 3.1 Scale mode

`scale` requires one positive finite uniform factor. It maps source coordinates to target coordinates about the origin. Source and target frames MUST be identical. `target_crs` is forbidden because scale alone cannot establish orientation or global location.

### 3.2 Matrix mode

`matrix` requires 16 finite row-major numbers representing an affine source-to-target matrix. The last row MUST be `[0, 0, 0, 1]`; the linear 3x3 block MUST be invertible. The inverse is calculated and both directions MUST round-trip within tolerance. Non-uniform scale or shear is allowed only because the author supplied the matrix explicitly; the result reports determinant and transform class and never becomes source evidence.

### 3.3 Control-points mode

`control_points` requires at least three uniquely identified source/target 3D point pairs. Source points and target points MUST each be non-collinear. The solver computes the least-squares orientation-preserving 3D similarity transform: one uniform positive scale, one proper rotation and one translation. Reflection, shear and non-uniform scale are forbidden. The result records maximum and RMS target-space residuals and fails with `AECCTX_MESH_REGISTRATION_TOLERANCE_EXCEEDED` when maximum residual exceeds tolerance.

The solver uses the Umeyama/Kabsch SVD formulation through the numpy runtime already required by the optional geometry extra. Inputs and outputs are finite. Matrix values and residuals use deterministic 15-significant-digit JSON numbers; no formatted value may become non-finite.

## 4. Records and authority

Every v0.2 record carries `evidence_class` and `record_version = "0.2"`.

- Source mesh primitives remain `observed` and retain their original coordinates.
- Scene-graph transforms extracted from the format remain `observed` primitives.
- The accepted profile becomes a `manual` assertion citing all affected observed mesh records, its author, mode and configuration digest.
- A calibrated mesh record and artifact are `derived`, cite the manual assertion and source mesh records, carry forward/inverse matrices, target units/frame/CRS, residual report and `representation_fidelity`.
- A conflict becomes a manual assertion with value state `conflicted`; no derived artifact is emitted.

`coordinate_qualification` keeps `declared_units`, `detected_units`, `manual_units`, source/manual CRS, frame facts and transform chain distinct. `spatial_reference` on the observed source is never overwritten. `global_location` is known only when an accepted matrix/control-point profile supplies a target CRS and every transform link is known and reversible.

## 5. SDK and CLI

`ingest_geometry()` remains v0.1 by default and byte-identical to explicit `aecctx_version="0.1.0"`. v0.2 is explicit and accepts either:

- `coordinate_profile=<validated mapping>` in the SDK; or
- `aecctx ingest ... --adapter geometry --aecctx-version 0.2.0 --mesh-coordinate-profile <json-path>` in the CLI.

The CLI file is bounded, parsed as data and cannot contain callbacks, expressions, environment settings, commands or paths to additional resources. No profile means the v0.2 package preserves declared metadata and explicit unknowns without producing manual/derived registration records.

## 6. Derived geometry and determinism

The existing source evidence GLB and SVG previews remain subordinate to observed records. A successful calibration additionally emits `geometry/calibrated-scene.glb` from world-baked source scene geometry transformed by the accepted source-to-target matrix. It does not replace `geometry/scene.glb` or any source primitive.

Repeated ingestion with identical source bytes, profile bytes and timestamp MUST produce identical JSONL, GLB, ZIP bytes and logical digest. The source SHA-256 and observed vertex/face arrays MUST match v0.2 ingestion without calibration.

## 7. Diagnostics and non-claims

Stable failures include invalid schema/configuration, unknown unit, invalid frame, source/manual conflict, insufficient or collinear points, reflection, singular/non-affine matrix, non-finite input, tolerance failure, unsafe external resource and face/input limits. A rejected profile does not silently fall back to a known calibration.

This profile does not claim survey authority, CRS identifier validity beyond preserving the supplied string, datum transformation, geoid/vertical correction, EPSG lookup, best-fit engineering acceptance, mesh healing or source-format write-back. It uses neither network nor LLM and introduces no consumer ontology.

## 8. Conformance

Project-authored fixtures cover OBJ/STL unknown metadata, glTF/GLB declared meters/frame and embedded transforms, scale/matrix/control-point modes, source/manual conflicts, insufficient/collinear points, reflection, singular matrix, tolerance failure, axis mismatch, large/small coordinates, reversible round trips, deterministic output and immutable source evidence.

The claim registry maps each implemented claim to fixtures, tests and `docs/evidence/ACX-16.md`. Other format versions, vendor extensions, external resources, unit guesses and untested trimesh releases remain unclaimed.
