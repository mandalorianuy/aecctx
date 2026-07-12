# AECCTX Capability Matrix

Date: 2026-07-12
Status: v0.1.0 release claim registry plus non-claim expansion targets

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
| ASCII/binary DXF | `full` version/unit/layout/layer/block/handle provenance | `partial` source semantics for the ACX-14 AC1015/AC1032 profile with no automatic domain classification | `full` for normalized v0.1 entities; dynamic `partial` with exact raw-tag fallback | `partial` for enumerated ACX-14 entities/transforms plus derived tessellation | ACX-05 and ACX-14 completed |
| Vector PDF | `full` source/page identity | `partial` text and content-stream evidence | `partial` path operators per page/viewport | `unsupported` as inferred hidden geometry | ACX-06 completed |
| Raster PDF/image | `full` source/pixel identity | `partial` metadata; experimental `partial` English OCR under the exact ACX-15 local/replay profile; vision `unsupported` | `partial` raster regions with explicit calibration state; image pixels `full` | `unsupported` as inferred hidden geometry | ACX-06 and ACX-15 completed |
| OBJ/STL/glTF 2.0/GLB 2.0 | `full` source/object identity | `partial` source-declared metadata; absent units/frame/CRS stay explicit | deterministic SVG preview only | `full` preserved mesh evidence plus derived GLB; optional manual registration is `partial` | ACX-07 and ACX-16 completed |
| STEP AP203/AP214/AP242 ed1; IGES 5.3 | `full` source-file identity; `partial` lexical entity graph | `partial` direct STEP product/assembly records; normalized XDE styles/units/placements unsupported | preview only | `partial` translator-derived OCCT BREP plus deterministic tessellation | ACX-17 experimental |
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
| v0.2 shared schema substrate | Implemented by ACX-11 | dual-version validation, typed shared evidence, required-extension and query/diff/context conformance |

## Post-v0.1 expansion targets

This table is a roadmap, not a support claim. Current claims in the release registry above remain authoritative until the owning task is completed with linked conformance evidence.

| Capability gap | Current public state | Bounded target | Owning task |
|---|---|---|---|
| IFC source-native 2D | `partial`: public for IFC2X3 TC1/IFC4 Add2 TC1 explicit 2D contexts and the polyline/indexed-line/geometric-curve-set/mapped-2D profile | Additional curves, annotations, hatches/styles and later schemas remain structured loss | ACX-13 completed |
| IFC georeferencing | `partial`: public for explicit IFC4 Add2 TC1 `IfcMapConversion` + `IfcProjectedCRS` with compatible declared units and reversible transforms | IFC2X3 property sets, omitted/multiple/conflicted operations and later schemas remain unknown/unsupported/conflicted | ACX-13 completed |
| DXF source semantics | `partial`: public for AC1015/AC1032 with `ezdxf==1.4.4`, bounded dictionaries/XRECORD, extension dictionaries, XDATA/AppID, ownership, groups, attributes, materials and block structure | Other releases/objects and custom/proxy interpretation remain raw/opaque/unsupported; no consumer classification | ACX-14 completed |
| DXF 3D | `partial`: public for enumerated point/line/face/mesh/polyline, OCS/WCS and bounded insert transforms with derived tessellation/GLB | ACIS/proxy/custom/encrypted/external-reference and unlisted geometry remain explicit loss | ACX-14 completed |
| Raster OCR | `experimental partial`: English word evidence under `tesseract-5.3.4-capi-eng-psm6-v1`; `unsupported` without explicit provider/replay | Additional languages, layouts, rotation profiles and portable live-runtime matrices remain separately governed | ACX-15 completed |
| Image/PDF vision | `unsupported`; no provider or output vocabulary accepted | Future inferred candidates require a new governed profile with confidence, privacy, reproducibility and evidence links | ACX-15 completed boundary; future task required |
| Hidden/unobserved geometry | public `unsupported` boundary | Remains unsupported as source geometry; reconstruction hypotheses never become measurement authority without a future separately governed profile | ACX-15 completed |
| Mesh units and CRS | `partial`: OBJ/STL unknowns and glTF/GLB 2.0 meters/frame are explicit; manual scale, affine matrix and similarity registration produce separate manual/derived evidence | Vendor extensions, external resources, CRS lookup/validation, survey/datum authority, mesh healing and untested formats/runtimes remain unclaimed | ACX-16 completed |
| STEP/IGES | `experimental partial`: exact source profiles through reviewed OCP/OCCT Linux-arm64 OCI or portable replay | XDE correlation, normalized styles/units/placements, source-exact BREP, other schemas/versions/platforms remain unsupported; opaque fallback remains available | ACX-17 completed |
| DWG | `experimental partial`: self-contained R2000/AC1015 through reviewed LibreDWG Linux-arm64 OCI or portable replay; direct JSON objects are observed and DXF/geometry are converted | Other releases/platforms, xref traversal, ACIS/proxy/custom semantics, qualified units/CRS and complete 3D remain unsupported/unknown; opaque fallback remains available | ACX-18 completed |
| RVT | public `unsupported`; deterministic v0.1 opaque fallback is anti-claim evidence only | No provider selected under ACXD-030; future extraction requires a separately reviewed reopening profile | ACX-19 blocked |
| Package authenticity/signing | integrity only; authenticity `unsupported` | Optional governed signature verification with distinct integrity, validity, trust, and authorization states | ACX-20 |
| Restricted decoder isolation | `partial`: `oci-docker-v1` is public only for the digest-pinned Linux-container/reference-provider profile; native Linux/macOS and Windows remain `unsupported` | Additional reviewed profiles with the complete enforcement-axis corpus | ACX-12 completed; ACXB-001 residual |
| AEC delivery quality gate | `unsupported` | Deterministic policy, baseline-diff and bounded IFC IDS evaluation with explicit outcomes and evidence citations | ACX-21 |
| Codex plugin | standalone read-only MCP only | Optional `aecctx-inspector` package with inspection, revision, loss-triage and quality-gate skills; no unique semantics | ACX-22 |
