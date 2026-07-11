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
| IFC 2x3/4.x | Target `full` | Target `full` with unsupported preservation | Target `partial` | Target `full` tessellated plus source representation refs | ACX-04 |
| ASCII/binary DXF | Target `full` | Target `partial` evidence, no automatic domain classification | Target `full` for supported entities | Target `partial` | ACX-05 |
| Vector PDF | Target `full` | Target `partial` text/dimensions | Target `partial` per-page/viewport evidence | `unsupported` as inferred hidden geometry | ACX-06 |
| Raster PDF/image | Target `full` | Target `partial` optional OCR/vision | Target `partial` pixels/regions, calibration explicit | `unsupported` as inferred hidden geometry | ACX-06 |
| OBJ/STL/glTF | Target `full` | Target `opaque` or `partial` metadata | Target preview only | Target `full` mesh evidence | ACX-07 |
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
| Markdown context projection | Required | source references and token budget report |
| Query | Required | read-only deterministic record selection |
| Diff | Required | source, entity, relation, evidence and artifact changes |
| MCP server | Optional | cannot become the only API |
| Source mutation/write-back | Not in v0.1 | future reviewed contract |
