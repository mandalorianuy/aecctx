# AECCTX DXF v0.2 Source Semantics and Bounded 3D Profile

Version: `0.2.0-draft.1`
Date: 2026-07-12
Status: ACX-14 normative profile

## 1. Public profile and dependency boundary

ACX-14 defines two public `partial` capabilities selected only by `aecctx_version="0.2.0"`:

- `dxf.source-semantics`, profile `dxf-r2000-r2018-source-semantics-v1`;
- `dxf.bounded-3d`, profile `dxf-r2000-r2018-bounded-3d-v1`.

The profiles are proven with `ezdxf==1.4.4` and project-authored ASCII and binary DXF fixtures using `AC1015` (R2000) and `AC1032` (R2018). Other ezdxf versions and DXF releases are parseable only under the existing v0.1 adapter contract and are not ACX-14 claims.

The adapter remains an optional, in-process MIT dependency with network disabled. Derived GLB additionally requires the existing optional geometry dependencies; their absence degrades only the derived artifact and never erases source evidence.

## 2. Source-semantic evidence

For every enumerated graphical or object record exposed by ezdxf, the adapter MUST preserve the native type, handle, owner handle, source container and exported ordered raw tags. It MUST preserve these source-native structures when present:

- root and nested `DICTIONARY` entries and `XRECORD` payload tags;
- extension-dictionary ownership and entries;
- registered application IDs and entity XDATA tags;
- `GROUP` name/description/selectability and member handles;
- block definitions, nested `INSERT` relationships, attached `ATTRIB` records and `ATTDEF` definitions;
- layer, layout and material identities, native handles and entity material-handle references.

Normalized records cite the primitive that owns the source tags. Missing, dangling or cyclic references are never repaired by invented handles. Unknown or unnormalized tags remain in `raw_tags`; unsupported object classes remain raw/opaque evidence plus structured loss.

Neutral kinds describe only presentation-neutral CAD record families. Layer, block, material, group, attribute or geometry names MUST NOT cause classification as wall, beam, panel or another consumer construction family.

## 3. Bounded 3D evidence

The source-exact coordinate profile covers:

- 3D coordinates for `POINT`, `LINE` and `3DFACE`;
- `POLYLINE` in 3D-polyline, polygon-mesh and polyface-mesh modes, including topology exposed by ezdxf;
- `MESH` vertices, faces and edges exposed by ezdxf;
- `INSERT` source placement, scale, rotation, extrusion and its ezdxf `Matrix44` transform;
- non-default extrusion/OCS metadata and explicit OCS-to-WCS coordinate conversion for `POINT`, `LINE`, `CIRCLE`, `ARC`, `LWPOLYLINE`, `SOLID`, `TRACE` and `3DFACE` only where the official entity API exposes the required values;
- nested inserts through a bounded, cycle-detecting transform chain.

Every coordinate record declares its source coordinate space, dimensionality and transform state. A missing, invalid, non-finite or singular transform is `unsupported` or `conflicted`; it MUST NOT become an identity transform by convenience.

## 4. Derived tessellation and GLB

`3DFACE`, `MESH`, polygon meshes and polyface meshes MAY produce a deterministic derived triangle set. Nested insert transforms MAY be applied to that derived set only when every chain link is known and finite. The triangle artifact MUST cite source primitive IDs, retain the source-to-artifact transform, declare tolerance, and use representation fidelity `tessellated`.

A GLB is a derived preview of that triangle set. It is never exact B-Rep, ACIS, parametric or source-authoritative geometry. Empty/partial topology and exporter failure produce stable loss diagnostics while the raw source evidence remains valid.

## 5. Explicit exclusions and diagnostics

The public profiles exclude `3DSOLID`, `BODY`, `REGION`, `SURFACE`, ACIS/SAT payload interpretation, proxy graphics, custom objects, encrypted/protected content and external-reference traversal. Those records remain raw/opaque or unsupported with stable reason codes. Xref declarations are evidence; referenced files are never opened implicitly.

Nested insert traversal is bounded to 32 levels and detects repeated block paths. Entity/object processing remains subject to the core byte and record limits. Malformed tag streams fail with a stable DXF parse diagnostic rather than yielding a conformant partial package.

## 6. Compatibility and acceptance

`ingest_dxf()` remains v0.1 by default and MUST emit byte-identical output to explicit `aecctx_version="0.1.0"` for the same inputs and timestamp. ACX-14 behavior requires explicit v0.2 selection through SDK or CLI.

The claims remain `partial` because the profiles exclude unlisted releases/entities, exact solid/surface kernels, proxy/custom interpretation, xref traversal and universal semantics. Claim promotion requires the committed ASCII/binary corpus, degraded/adversarial cases, deterministic replay, package validation, capability/loss assertions and vocabulary-boundary tests named in `conformance/v0.2/claims.json`.
