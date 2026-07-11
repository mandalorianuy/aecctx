# AECCTX Capability Matrix

Date: 2026-07-11
Status: Normative claim registry

## Support levels

| Level | Meaning |
|---|---|
| `full` | Required v0.1 fields and semantics for the capability are emitted with passing conformance fixtures. |
| `partial` | Some content is extracted; omissions and degradation are enumerated in the loss report. |
| `opaque` | Content identity and location are preserved but not interpreted. |
| `unsupported` | The adapter cannot safely process the capability and emits a diagnostic. |

## Planned format capabilities

Opaque fallback ingest is implemented in the core. Format-specific adapter values remain targets until their owning tasks complete.

| Source | Identity/provenance | Properties/semantics | 2D geometry | 3D geometry | Planned task |
|---|---|---|---|---|---|
| Unknown binary/text | `full` registration | `opaque` with structured loss | `opaque` with structured loss | `opaque` with structured loss | ACX-02 completed |
| IFC 2x3/4.x | `full` schema/GUID/class provenance | `full` when representable; dynamic `partial` with unsupported preservation | `partial` with native refs | `full` for successfully tessellated representations; dynamic `partial` on failures | ACX-04 completed |
| ASCII/binary DXF | `full` version/unit/layout/layer/block/handle provenance | `partial` evidence with no automatic domain classification | `full` for normalized supported entities; dynamic `partial` with exact raw-tag fallback | `partial` | ACX-05 completed |
| Vector PDF | `full` source/page identity | `partial` text and content-stream evidence | `partial` path operators per page/viewport | `unsupported` as inferred hidden geometry | ACX-06 completed |
| Raster PDF/image | `full` source/pixel identity | `partial` metadata; OCR/vision `unsupported` without provider | `partial` raster regions with explicit calibration state; image pixels `full` | `unsupported` as inferred hidden geometry | ACX-06 completed |
| OBJ/STL/glTF | `full` source/object identity | `partial` metadata with explicit unknown units | deterministic SVG preview only | `full` preserved mesh evidence plus derived GLB with reversible transform | ACX-07 completed |
| STEP/IGES | Target `full` | Target `partial` names/colors/assembly metadata | Target preview only | Target `full` B-Rep plus tessellation where supported | post-v0.1 |
| DWG/DGN | Adapter-specific | Adapter-specific | Adapter-specific | Adapter-specific | optional plugin, post-v0.1 |
| RVT/proprietary BIM | Adapter-specific | Adapter-specific | Adapter-specific | Adapter-specific | optional plugin, post-v0.1 |

## Core capabilities

| Capability | v0.1 target | Gate |
|---|---|---|
| Package directory validation | Implemented | JSON Schema plus logical integrity tests |
| Deterministic ZIP package | Implemented | repeated builds produce identical bytes and logical digest |
| Source registration and hashing | Implemented | SHA-256 streaming conformance fixture |
| Explicit value states | Implemented for opaque ingest | schema and semantic tests |
| Capability/loss report | Implemented for opaque ingest | all non-full claims have structured diagnostics |
| Markdown context projection | Implemented | source locations, chunks, profiles and token budget report |
| Query | Implemented | read-only deterministic record selection with package digest |
| Diff | Implemented | identity, record, artifact, capability, loss and producer changes |
| MCP server | Optional, implemented | five read-only wrappers match stable library/CLI semantics |
| Source mutation/write-back | Not in v0.1 | future reviewed contract |
