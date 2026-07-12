# ACX-14 acceptance evidence

Date: 2026-07-12
Status: completed
Task: DXF source-native semantics and bounded 3D
Decision: ACXD-026
Completion commit: `feat: complete ACX-14 DXF semantics and bounded 3D`

## Authority and bounded claims

The normative profile is `docs/specs/dxf-v02-profile.md`. The public claims remain `partial` and are limited to project-authored AC1015/AC1032 ASCII/binary fixtures with optional `ezdxf==1.4.4`:

| Claim | Exact profile | Support |
|---|---|---|
| `dxf.source-semantics` | handles/owners, dictionaries/XRECORD, extension dictionaries, XDATA/AppID, groups, attributes, materials, layouts/layers and block/insert structure | `partial` |
| `dxf.bounded-3d` | listed point/line/face/mesh/polyline, OCS/WCS and bounded nested-insert transforms with derived tessellation/GLB | `partial` |

Other ezdxf/DXF versions, unlisted entities, ACIS exact geometry, proxy/custom interpretation, xref traversal, encrypted/protected content and universal CAD semantics remain unclaimed.

## Implementation

- Explicit v0.2 SDK/CLI opt-in while default and explicit v0.1 output remain byte-identical.
- Source primitives for graphical entities, objects and application table records with ordered raw tags, stable handles/owners and source locators.
- Dictionaries, XRECORD payloads, extension dictionaries, XDATA/AppID, groups, ATTRIB/ATTDEF, materials and block/insert evidence.
- Bounded 3D coordinates/topology for POINT, LINE, 3DFACE, MESH and the enumerated POLYLINE modes; explicit OCS/WCS and INSERT matrices.
- Cycle-detecting nested inserts capped at 32 levels and configurable byte/record limits.
- Deterministic derived triangle JSON and GLB with source IDs, transform, tolerance and `tessellated` fidelity.
- Stable parse/resource/cycle/ACIS/proxy/xref/export diagnostics without opening external references.
- Neutral vocabulary tests rejecting construction-family inference from names or geometry.

## Validation

- Targeted DXF v0.2/v0.1/CLI bundle: passed.
- Full test suite: `168 passed`.
- `python scripts/check_spec_contract.py`: passed.
- Claim registry validation: valid with no errors.
- `./scripts/verify_portable.sh`: passed with `168 passed`; wheel and sdist built successfully.
- `./scripts/verify.sh`: passed with `168 passed`; wheel/sdist, baseline integration (`healthy issues=0`), deterministic v0.1 corpus and release verification all passed.

## Fixtures and hashes

All fixtures and their generator were authored in this repository for publication under the project license:

| Fixture | Container/profile | SHA-256 |
|---|---|---|
| `r2018-semantics-3d-ascii.dxf` | AC1032 ASCII positive/degraded | `e1ef17ad68911a744a9e87a5d59d11d99cadab6793829903d63b698d2d25cc49` |
| `r2018-semantics-3d-binary.dxf` | AC1032 binary equivalent | `1a9b6003f159a001fe661d726dcaabe2b9f527a1d0e5a3bb051e9ea2cdb7e1c0` |
| `r2000-cyclic-inserts.dxf` | AC1015 adversarial cycle | `31c1e3bbfffec7f5b4f9403d4274d4a5aef395c9e6c3e8fc7340111f25ef6a4e` |
| `malformed-tags.dxf` | malformed tag stream | `d0d6126f97e924ead43292ce66165d121519a289d14f2a23c155c4a5824ee66b` |

The hash/origin registry is `conformance/v0.2/dxf-corpus.json`.

## Dependency, platform, security, license and privacy

- Governed parser: exactly `ezdxf==1.4.4`, MIT, optional and separately installed; another version requires a new conformance decision.
- Derived GLB uses the existing optional `trimesh>=4.12,<5` geometry extra and degrades without erasing source evidence.
- Platform scope follows Python environments where the optional dependencies and corpus pass; the core wheel remains independent.
- DXF inputs, tags, object data, xref paths and embedded payloads are untrusted data. The adapter performs no command, link, xref, network or LLM execution.
- Fixtures contain no personal, proprietary or third-party-authored content.

## Capability/loss evidence and residual risks

The adapter keeps both public claims `partial`. `AECCTX_DXF_3D_PROFILE_PARTIAL`, ACIS/proxy/xref exclusions, parse/resource failures and transform/cycle degradation are machine-readable diagnostics; raw tags remain available whenever parsing safely succeeds.

Residuals: unlisted DXF releases/entities; ACIS/SAT/SAB exact-kernel geometry; proxy/custom objects; encrypted/protected sources; external-reference traversal; additional curve/surface tessellation; and environments without optional GLB dependencies. None is represented as known or full support.

## Repository boundary and promotion

No WoodFraming path, `WFDomain`, `WFImport`, network or LLM dependency was accessed or modified. ACX-14 is completed and ACX-15 is promoted to `pending-next`; ACX-15 was not executed.
