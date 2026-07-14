# AECCTX Capability Matrix

Date: 2026-07-14
Status: v0.2.0 release claims plus explicit unsupported and future targets

The accepted post-v0.2 roadmap is governed by `docs/specs/aecctx-post-v02-functional-debt-spec.md` and `docs/plans/post-v02-functional-debt-implementation.md`. Its entries remain targets and do not change any support level in this matrix until the owning ACX closes with conformance evidence.

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
| ASCII/binary DXF | `full` version/unit/layout/layer/block/handle provenance; bounded xrefs remain source-separated | `partial` source semantics for exact AC1009/AC1015/AC1018/AC1021/AC1032 corpus profiles with no automatic domain classification | `partial` analytic/unbounded curve evidence with exact raw-tag fallback | `partial` selected curves/MESH/transforms plus derived tessellation; ACIS unsupported | ACX-05, ACX-14 and ACX-28 completed |
| Vector PDF | `full` source/page identity | `partial` text and content-stream evidence | `partial` path operators per page/viewport | `unsupported` as inferred hidden geometry | ACX-06 completed |
| Raster PDF/image | `full` source/pixel identity | `partial` metadata and bounded `eng`/`spa`/`por` OCR words/lines/blocks/table-grid under ACXD-037; vision `unsupported` | `partial` raster regions with explicit calibration state; image pixels `full` | `unsupported` as inferred hidden geometry | ACX-06, ACX-15 and ACX-29 completed |
| OBJ/STL/glTF 2.0/GLB 2.0 | `full` source/object identity | `partial` source-declared metadata; absent units/frame/CRS stay explicit | deterministic SVG preview only | `full` preserved mesh evidence plus derived GLB; bounded manual registration and offline datum transformation are `partial` | ACX-07, ACX-16 and ACX-31 completed |
| STEP AP203/AP214/AP242 ed1; IGES 5.3 | `full` source-file identity; `partial` lexical entity graph | `partial` direct STEP product/assembly records; normalized XDE styles/units/placements unsupported | preview only | `partial` translator-derived OCCT BREP plus deterministic tessellation | ACX-17 experimental |
| DWG | `full` source-byte/version/provider provenance for exact AC1012/AC1014/AC1015 profiles; bounded xrefs remain source-separated | `partial` direct decoder objects and explicit units when retained; no consumer classification | `partial` converted DXF simple geometry | `partial` converted point/line/polyline/face evidence; ACIS/proxy/custom remain unsupported | ACX-18, ACX-24 and ACX-33 completed |
| DGN | Adapter-specific | Adapter-specific | Adapter-specific | Adapter-specific | optional plugin, post-v0.1 |
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
| MCP server | Optional, implemented | six read-only wrappers match stable library/CLI/gate semantics |
| Source mutation/write-back | Not in v0.1 | future reviewed contract |
| v0.2 shared schema substrate | Implemented by ACX-11 | dual-version validation, typed shared evidence, required-extension and query/diff/context conformance |

## Post-v0.1 expansion targets

This table is a roadmap, not a support claim. Current claims in the release registry above remain authoritative until the owning task is completed with linked conformance evidence.

| Capability gap | Current public state | Bounded target | Owning task |
|---|---|---|---|
| IFC source-native 2D | `partial`: public for the ACX-13 IFC2X3 TC1/IFC4 Add2 TC1 profile and the ACX-27 IFC4X3 ADD2 structural circle/ellipse/parameter-trim/composite/indexed line-arc/text/fill/direct-style profile | Glyph and hatch rendering, topology, B-splines, offsets, spirals, arbitrary trims, external presentation resources, other schemas/editions and unlisted forms remain structured loss | ACX-13 and ACX-27 completed |
| IFC georeferencing | `partial`: public for explicit ACX-13 IFC4 Add2 TC1 `IfcMapConversion` and ACX-27 IFC4X3 ADD2 `IfcMapConversionScaled`, each with one projected CRS, compatible units and reversible transforms | IFC2X3 property sets, implicit/default factors, omitted/multiple/conflicted operations, CRS validation, survey authority, other schemas/operations and false EPSG cues remain unknown/unsupported/conflicted | ACX-13 and ACX-27 completed |
| DXF source semantics | `partial`: public for exact AC1009/AC1015/AC1018/AC1021/AC1032 corpus cases with `ezdxf==1.4.4`; adds ELLIPSE/SPLINE/HELIX/RAY/XLINE/MLINE/MESH evidence and content-addressed source-separated xrefs | Intermediate/unlisted releases and objects, ambient/network xrefs, external images/underlays and custom/proxy interpretation remain raw/opaque/unsupported; no consumer classification | ACX-14 and ACX-28 completed |
| DXF 3D | `partial`: public for enumerated point/line/face/mesh/polyline, selected analytic curves, OCS/WCS and bounded insert/xref transforms with derived tessellation/GLB | ACIS/SAT/SAB exact surfaces/B-Rep, proxy/custom/encrypted content, DWG xrefs and unlisted geometry remain explicit loss | ACX-14 and ACX-28 completed |
| Raster OCR | `experimental partial`: English word evidence under `tesseract-5.3.4-capi-eng-psm6-v1`; `unsupported` without explicit provider/replay | Additional languages, layouts, rotation profiles and portable live-runtime matrices remain separately governed | ACX-15 completed |
| Image/PDF vision | `partial`: exact visible rectangle/grid/cross/linear-dimension candidates and containment under ACXD-039 on Linux arm64/amd64; inferred only | Learned/general recognition, arbitrary rotation, semantic AEC classification and remote services remain unsupported | ACX-15 boundary and ACX-30 completed |
| Hidden/unobserved geometry | source geometry remains public `unsupported`; visible planar-boundary reconstruction hypotheses are `partial` inferred evidence only | Hypotheses never become measurement, source/full/hidden geometry, 3D reconstruction or approval authority | ACX-15 boundary and ACX-30 completed |
| Mesh units and CRS | `partial`: OBJ/STL unknowns and glTF/GLB 2.0 meters/frame remain explicit; manual scale/affine/similarity registration plus the exact offline eight-record EPSG v11.022 registry and grid-free EPSG:1252 operation produce separate manual/derived evidence | Network/dynamic lookup, grids, external/vendor extensions, unlisted CRS/operations, coordinate epochs, survey/datum authority, mesh healing and untested formats/runtimes remain unclaimed | ACX-16 and ACX-31 completed; `mesh.crs-registry`, `mesh.datum-transform` |
| STEP/IGES | `partial`: exact ACX-17 source/BREP plus ACX-32 XDE labels, selected names/colors/layers/materials/units/placements, per-root validity/tolerance/recovery and fixed opt-in healing on reviewed OCP/OCCT OCI `linux/arm64`/`linux/amd64`, or portable replay | Correlation remains exact-unique only; source-exact BREP, implicit/correct healing, external content and other schemas/versions/runtimes/platforms remain unsupported; opaque fallback remains available | ACX-17, ACX-24 and ACX-32 completed |
| DWG | public `partial`: AC1012/R13, AC1014/R14 and AC1015/R2000 through exact LibreDWG 0.13.4 OCI on `linux/arm64` and `linux/amd64`, or portable replay; explicit units and content-addressed xrefs are bounded; direct JSON is observed and DXF/3D are converted | R12, R2004+, encryption, ambient/network xrefs, ACIS/proxy/custom semantics, CRS, complete 3D, writers and other providers/platforms remain unsupported/unknown; opaque fallback remains available | ACX-18, ACX-24 and ACX-33 completed; `dwg.external-provider.v03` |
| RVT | public `unsupported`; deterministic v0.1 opaque fallback is anti-claim evidence only | ACXD-043 renews the blocker: neither local licensed nor APS remote route has human authorization plus complete entitlement/version/enforcement/CI/fixture/privacy/lifecycle evidence | ACX-19 and ACX-34 blocked; `rvt.external-provider` remains unsupported |
| Package authenticity/signing | public `partial`: ACX-20 detached JWS plus ACX-35 exact explicit Ed25519 X.509 paths, complete offline base CRLs, closed AECCTX trusted-time tokens and exact-target countersignatures; integrity, crypto, identity, lifecycle, trust, authorization and archival time remain distinct | RFC 3161/CMS, OCSP, delta/indirect CRLs, online/host discovery, production key custody, hardware keys, legal/qualified signatures, transparency and universal trust remain unsupported | ACX-20 and ACX-35 completed; `package.advanced-trust-signing` |
| Restricted decoder isolation | `partial`: `oci-docker-v1` is public only for the digest-pinned Linux-container/reference-provider profile; deterministic complete reports make native Linux/macOS/Windows explicitly `unsupported` and fail closed before workspace or launch | A future native profile requires a reviewed supervisor/broker plus live success and all-axis adversarial evidence | ACX-12 and ACX-25 completed; `sandbox.local-enforcement` public `unsupported` |
| OCI provider multi-architecture execution | public `partial`: exact Tesseract, OCP/OCCT and LibreDWG targets on `linux/arm64` and `linux/amd64`, with architecture-bound image IDs, equal canonical results and live adversarial evidence | Native macOS/Windows, other architectures/providers, registry publication, automatic pull/build, remote execution and image signing remain unsupported | ACX-24 completed; `sandbox.oci-multiarch` |
| Optional remote provider protocol | public `partial`: exact `remote-https-spki-v1` customer-selected HTTPS/SPKI protocol with explicit per-call policy, bounded canonical envelopes, repository-owned TLS loopback and deterministic replay on Python 3.12 Linux/macOS/Windows | Third-party service availability, provider-side sandboxing/deletion, billing, jurisdiction, entitlement, semantic correctness, Web PKI lifecycle, discovery, OAuth, mTLS, streaming and consumer approval remain unsupported | ACX-26 completed; `sandbox.remote-provider` |
| AEC delivery quality gate | public `partial`: deterministic core policy gate plus optional bounded IDS 1.0 simple and expanded profiles; ACX-36 adds exact aggregate/group/containment/nesting `partOf`, string pattern/enumeration, numeric inclusive/exclusive bounds and required/optional/prohibited specification cardinality on Python 3.12 Linux/macOS/Windows | URI/bSDD, geometry/quantity interpretation, remote validation, unlisted IDS versions/schemas/facets/relations/restrictions/cardinalities and all approval/certification semantics remain unsupported | ACX-21 and ACX-36 completed; `quality-gate.ids-expanded` |
| Codex plugin | public `partial`: ACX-22 semantics plus deterministic `aecctx-inspector-distribution-v1`, exact Python 3.12 Linux/macOS/Windows local-host matrix with MCP 1.28.1, checksum/inventory, optional explicit Ed25519 signature and rollback-safe lifecycle | Marketplace/host-product publication, publisher trust, universal model behavior, hosted/third-party hosts, unique semantics and provider shell execution remain unclaimed | ACX-22 and ACX-37 completed; `codex.aecctx-inspector-distribution` |
