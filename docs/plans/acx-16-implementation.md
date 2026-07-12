# ACX-16 Mesh Coordinate Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` and `superpowers:test-driven-development` task-by-task. Subagent dispatch is prohibited for this repository task.

**Goal:** Implement the bounded v0.2 mesh coordinate and manual registration profile without changing v0.1 output or original source evidence.

**Architecture:** A focused `mesh_coordinates` module owns schema loading, canonical profile hashing, frame/unit conflict checks, scale/matrix/similarity solving and numeric reports. The geometry adapter remains the extraction owner and consumes the module to emit observed/manual/derived v0.2 records and deterministic calibrated GLB. CLI and conformance layers only load bounded JSON and call the same SDK path.

**Tech Stack:** Python 3.12+, JSON Schema 2020-12, numpy from `trimesh==4.12.2`, existing deterministic GLB/package APIs, pytest.

## Global Constraints

- Execute only ACX-16; ACX-17 remains pending.
- `ingest_geometry()` defaults to byte-identical v0.1 behavior.
- OBJ/STL units and CRS remain unknown; glTF/GLB 2.0 declares meters and its normative frame only.
- Never call unit-guessing APIs or resolve external mesh resources.
- Source vertices/faces/hash remain observed and immutable; profiles are manual; calibrated output is derived.
- Control points solve only an orientation-preserving uniform-scale similarity.
- Matrix mode accepts explicit finite invertible affine transforms; scale mode cannot establish CRS.
- Every negative/partial outcome has a stable code and structured loss.

---

### Task 1: Profile schema and coordinate solver

**Files:**
- Create: `schemas/v0.2/mesh-coordinate-profile.schema.json`
- Create: `src/aecctx/schemas/v0_2/mesh-coordinate-profile.schema.json`
- Create: `src/aecctx/mesh_coordinates.py`
- Create: `tests/test_mesh_coordinates_v02.py`

**Interfaces:**
- Produces `CoordinateProfileError(code, message)`.
- Produces `load_coordinate_profile(value: Mapping[str, Any]) -> CoordinateProfile`.
- Produces `solve_coordinate_profile(profile, declared_units, declared_frame) -> CoordinateSolution`.
- `CoordinateSolution` exposes forward/inverse row-major matrices, determinant, transform class, residual report, configuration digest and optional conflict value.

- [ ] Write schema/loader tests for the three exact mode payloads, forbidden extra fields, unit/frame vocabulary, finite positive tolerance and bounded author/CRS strings.
- [ ] Run `pytest tests/test_mesh_coordinates_v02.py -k schema -q`; expect missing module/schema failure.
- [ ] Add mirrored schemas and schema-backed loader; run the same command and expect pass.
- [ ] Write failing tests for uniform scale, explicit affine inverse, singular/non-affine/non-finite matrices and 15-significant-digit canonicalization.
- [ ] Implement scale/matrix solving with numpy inverse/determinant and explicit stable error codes; run targeted tests.
- [ ] Write failing tests for exact/noisy similarity, insufficient/collinear/reflected pairs, tolerance failure and large coordinates.
- [ ] Implement orientation-preserving Umeyama/Kabsch similarity, residuals and round-trip checks; run `pytest tests/test_mesh_coordinates_v02.py -q`.

### Task 2: Source format qualification and safe loading

**Files:**
- Modify: `src/aecctx/adapters/geometry.py`
- Create: `tests/test_geometry_v02.py`
- Create: `fixtures/v0.2/mesh/generate_fixtures.py`
- Generate: `fixtures/v0.2/mesh/triangle-unknown.obj`, `triangle-unknown.stl`, `triangle-meters.gltf`, `triangle-meters.glb`

**Interfaces:**
- `ingest_geometry(..., aecctx_version: str = "0.1.0", coordinate_profile: Mapping[str, Any] | None = None)`.
- Internal source profile returns declared/detected units, frame, CRS, format version, external-reference diagnostics and scene-graph edges.

- [ ] Generate project-authored self-contained fixtures with one translated glTF node and exact source hashes.
- [ ] Write failing tests proving default and explicit v0.1 ZIP identity, OBJ/STL unknown states, glTF/GLB meters/frame and external URI/OBJ material non-resolution.
- [ ] Load exact bytes with explicit format and no resolver; preflight external references before trimesh; preserve graph edges with deterministic locators.
- [ ] Emit v0.2 source/primitives/entities/diagnostics with `evidence_class`, coordinate qualification and unchanged local vertices/faces.
- [ ] Run `pytest tests/test_geometry_adapter.py tests/test_geometry_v02.py -q`; expect all legacy and v0.2 source tests green.

### Task 3: Manual and derived registration records

**Files:**
- Modify: `src/aecctx/adapters/geometry.py`
- Modify: `tests/test_geometry_v02.py`
- Add: `fixtures/v0.2/mesh/profiles/*.json`

**Interfaces:**
- Adapter consumes `CoordinateSolution` from Task 1.
- Produces manual `aecctx:mesh-coordinate-registration` assertion and optional derived `CALIBRATED_MESH` primitive plus `geometry/calibrated-scene.glb`.

- [ ] Write failing scale test asserting original source primitive equality, manual profile digest and deterministic calibrated bounds/artifact.
- [ ] Implement scale mapping and derived artifact while retaining `geometry/scene.glb`.
- [ ] Write failing matrix/CRS and control-point tests asserting forward/inverse round trip, target qualification, residuals and deterministic GLB.
- [ ] Implement matrix/similarity record mapping and world-baked scene transformation.
- [ ] Write failing conflict tests for glTF meters/manual millimeters and frame mismatch; assert `conflicted` and no calibrated artifact.
- [ ] Implement conflict assertion/diagnostics without precedence; run all geometry v0.2 tests.

### Task 4: CLI, corpus and claims

**Files:**
- Modify: `src/aecctx/cli.py`
- Modify: `tests/test_cli.py`
- Create: `conformance/v0.2/mesh-corpus.json`
- Modify: `conformance/v0.2/claims.json`
- Modify: `scripts/verify_portable.sh`

**Interfaces:**
- CLI adds `--mesh-coordinate-profile PATH`, valid only with geometry and `--aecctx-version 0.2.0`.
- Corpus maps exact fixtures/profiles/hashes to claim tests.

- [ ] Write failing CLI tests for no-profile v0.2, scale profile, invalid option combinations, oversized/malformed profile and stable JSON diagnostics.
- [ ] Implement bounded JSON loading and pass the mapping to `ingest_geometry()`.
- [ ] Add portable corpus validation and exact public `partial` claims `mesh.declared-coordinate-metadata` and `mesh.manual-registration`.
- [ ] Run CLI, claim registry, corpus and deterministic ZIP tests.

### Task 5: Documentation, evidence and promotion

**Files:**
- Create: `docs/evidence/ACX-16.md`
- Modify: `README.md`, `docs/capability-matrix.md`, `docs/compatibility-v0.2.md`, `docs/HANDOFF.md`, `docs/implementation-plan.md`

**Interfaces:**
- Evidence binds claims to fixture hashes, tests, dependency/license/security notes and CI.

- [ ] Document exact support/non-support and SDK/CLI examples; keep Markdown explicitly non-authoritative.
- [ ] Run focused tests, `python scripts/check_spec_contract.py`, claim/corpus validation and baseline integration.
- [ ] Run `./scripts/verify.sh`; record exact counts and evidence.
- [ ] Mark ACX-16 completed, promote only ACX-17 to `pending-next`, and verify plan invariants again.
- [ ] Commit coherent ACX-16 milestones, push the branch and wait for Linux/macOS/Windows CI success. Do not execute ACX-17.
