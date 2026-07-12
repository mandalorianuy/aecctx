# ACX-16 acceptance evidence

Date: 2026-07-12
Status: completed
Task: Mesh units, calibration and CRS registration
Decisions: ACXD-016 and ACXD-027
Completion commit: `feat: complete ACX-16 mesh coordinate profile`

## Authority and bounded outcomes

The normative authority is `docs/specs/mesh-coordinate-v02-profile.md`.

| Claim | Governance | Support |
|---|---|---|
| `mesh.declared-coordinate-metadata` | self-contained OBJ/STL/glTF 2.0/GLB 2.0 through exact `trimesh==4.12.2` | public `partial` |
| `mesh.manual-registration` | explicit scale, affine matrix or orientation-preserving similarity profile | public `partial` |

OBJ/STL units, frame and CRS remain unknown. glTF/GLB 2.0 meters and normative frame are source-declared; CRS remains unknown. No source field is replaced by manual or derived evidence.

## Implementation

- A public JSON Schema and packaged schema validate bounded author, source/target units, frames, optional CRS, tolerance and exact mode payloads.
- `load_coordinate_profile()` binds canonical configuration bytes to SHA-256 and rejects non-finite or structurally invalid input.
- `solve_coordinate_profile()` emits reversible scale/affine/similarity transforms, determinant, residuals and explicit conflicts. Singular/non-affine matrices, insufficient/collinear points, reflection and tolerance failure have stable codes.
- The v0.2 geometry adapter loads exact bytes with an explicit format and no resolver. External glTF resources are rejected before resolution; unit guessing is prohibited.
- Observed source vertices/faces and scene transforms remain immutable. Accepted profiles become `manual` assertions; calibrated records and `geometry/calibrated-scene.glb` are separately `derived` with provenance and representation fidelity.
- Source/manual unit or frame disagreement stays `conflicted`, emits structured diagnostics and produces no calibrated artifact.
- SDK opt-in uses `aecctx_version="0.2.0", coordinate_profile=<mapping>`. CLI opt-in uses `--adapter geometry --aecctx-version 0.2.0 --mesh-coordinate-profile <json>` with regular-file and 1 MiB limits.
- Default and explicit v0.1 geometry packages remain byte-identical.

## Fixtures and conformance

All mesh/profile fixtures and their generator were authored in this repository for publication under Apache-2.0. `conformance/v0.2/mesh-corpus.json` binds seven positive/negative entries to exact hashes.

| Artifact | SHA-256 |
|---|---|
| `triangle-unknown.obj` | `eff920108246b8b6e87433cf4a615ba1057144e6d03ef0a265f757013ddaa355` |
| `triangle-unknown.stl` | `f721a2fd247e1f367ce181750b2fb5b18dccd2e966e3dc04ef25a9b435d9af1e` |
| `triangle-meters.gltf` | `ceffe08cc7d257d5191ea7db99b9a3ce1e869975d66ad5ff97c64cdc37001bc3` |
| `triangle-meters.glb` | `40daec8b07875b627326c2cc7cf0fd5ec4f3dfcf5d51ba28a05d4fe14b551b77` |
| `unsafe-external.gltf` | `9719181bea12f91dd2d080e037b5910358a160d6d0f7d8448ef5e72ad3358cc0` |

The public claim registry maps both claims to the corpus, focused tests and this evidence file.

## Validation evidence

- Schema/solver and geometry/CLI compatibility cut: 51 focused tests passed.
- Full local suite: `208 passed`.
- `./scripts/verify_portable.sh`: passed; wheel and sdist built successfully in isolated environments.
- `python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues`: healthy, zero issues, bundle `baseline-shared-v1`.
- `./scripts/verify.sh`: passed; the v0.1 deterministic corpus remained valid with matching claims and digests for all seven adapters.
- GitHub Actions run `29197567916`: Ubuntu, macOS and Windows `verify_portable.sh` jobs passed for implementation commit `22451c2`.

## Security and authority boundary

Inputs and profiles are untrusted data. No external resource, source callback, command, network service or LLM is invoked. The profile cannot establish survey correctness, validate CRS identifiers, apply datum/geoid transforms or become source-declared evidence. Generated Markdown and GLB remain projections/derived artifacts.

## Residuals and promotion

Vendor mesh coordinate extensions, external resources, other mesh formats/versions, unit guessing, CRS lookup/validation, survey/datum authority, mesh healing and untested trimesh releases remain explicitly unclaimed under the normative profile. They require a new governed capability profile before implementation.

No WoodFraming path, `WFDomain`, `WFImport` or consumer ontology was accessed or modified. ACX-16 is completed and ACX-17 is promoted to `pending-next`; ACX-17 was not executed.
