# AECCTX Post-v0.1 Capability Expansion Specification

Version: `0.2.0-draft.4`
Date: 2026-07-11
Status: Planning authority; no new capability claim is implied

## 1. Purpose

This specification governs the implementation path for capabilities that remain partial or unsupported after AECCTX `0.1.0`. It extends the stable package and plugin contracts without weakening their evidence, determinism, safety, value-state, licensing, or consumer boundaries.

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, and MAY are normative for work governed by ACX-11 through ACX-23. Until the owning task has accepted conformance evidence, every item in this document remains a target rather than an implemented capability.

## 2. Fixed boundaries

- AECCTX remains application-agnostic and MUST NOT contain WoodFraming, `WFDomain`, `WFImport`, or another consumer ontology.
- Source extraction, normalized interpretation, optional inference, and consumer mapping remain separate layers.
- Markdown remains a generated projection and MUST NOT become authority for identity, geometry, evidence, authenticity, or diagnostics.
- `unknown`, `unsupported`, `conflicted`, `explicit_null`, and `not_applicable` MUST remain explicit. A calibration, transform, classification, or hidden feature MUST NOT be invented.
- The core remains usable offline and without an LLM. Network or inference services are optional providers.
- Every input, decoder output, provider response, archive, and artifact is untrusted data.
- Native, GPL, commercial, and network-backed decoders MUST NOT execute through the reviewed in-process adapter path. They require the external sandbox contract in section 5.
- No task governed here authorizes source write-back or consumer acceptance.

## 3. Claim lifecycle

A capability advances only through these states:

1. `target`: specified but not implemented;
2. `experimental`: implementation exists behind an explicit opt-in and has incomplete portability or corpus evidence;
3. `partial`: a public, tested subset is supported and every excluded subset is represented in structured loss;
4. `full`: the bounded capability contract and conformance corpus pass on every supported platform/provider combination;
5. `unsupported`: the implementation cannot safely or faithfully provide the capability.

Only the existing package support levels `full`, `partial`, `opaque`, and `unsupported` appear in emitted v0.1-compatible capability reports. `target` and `experimental` are release-governance states, not package claims. Experimental output MUST report at most `partial` and MUST identify the experimental profile.

For every public claim, the owning task MUST provide:

- a minimal legally publishable positive fixture;
- a negative, degraded, or adversarial fixture;
- expected evidence, capability, loss, and diagnostic records;
- determinism or declared non-determinism evidence;
- dependency, license, and distribution evidence;
- platform/provider scope;
- a committed conformance test mapped from the claim registry.

## 4. Shared evidence extensions

ACX-11 MUST define versioned schemas for the following concepts before format tasks depend on them. The stable v0.1 schemas remain unchanged until a versioned compatibility and migration decision is accepted.

### 4.1 Observation and inference

Provider-derived OCR, vision, classification, reconstruction, or recognition output MUST be an assertion or primitive with:

- exact input artifact and region hashes;
- provider/plugin identity and version;
- model/service/runtime version when applicable;
- local or network execution mode;
- request/configuration digest and response digest;
- extraction confidence separately from interpretation confidence;
- reproducibility class: `deterministic`, `seeded`, or `non_deterministic`;
- source locator and parent evidence IDs;
- explicit verification state.

An inferred assertion MUST NOT be rewritten as source-observed evidence. Provider unavailability MUST degrade to structured `unsupported` or `partial` loss without making core ingest fail.

### 4.2 Coordinate qualification

Geometry records MUST distinguish:

- declared units from detected units and caller-supplied calibration;
- source-local coordinates from project coordinates and geographic CRS;
- exact source transforms from derived/rebased transforms;
- authoritative, derived, tessellated, rasterized, and inferred geometry;
- horizontal and vertical CRS when they differ;
- axis order, handedness, origin, scale, tolerance, and transform direction.

Caller-supplied calibration is a manual assertion with provenance. It MUST NOT overwrite source evidence. A transform chain with any unknown link remains unresolved and MUST NOT be described as globally located.

### 4.3 Representation fidelity

Every geometry artifact MUST state its fidelity class and the source representation it cites. B-Rep, parametric definitions, tessellation, 2D projection, and preview are not interchangeable. A preview or inferred reconstruction MUST NOT justify a `full` source-geometry claim.

## 5. Reviewed external sandbox provider contract

The external sandbox is a prerequisite for native, GPL, commercial, or network-backed decoders. A command path supplied by a caller is not a plugin registration mechanism.

### 5.1 Trust and protocol boundary

The core MUST communicate through a versioned, bounded, schema-validated protocol with an allowlisted provider descriptor. The descriptor includes provider identity/version, decoder/runtime versions, license and redistribution posture, supported actions/formats, platform, network policy, deterministic mode, and enforceable resource axes.

Requests contain content-addressed input references, explicit limits, requested capabilities, and configuration digests. Responses contain content-addressed artifacts, ordered events, diagnostics, resource usage, capability/loss reports, and a provider attestation. Provider paths and host environment details MUST be normalized or redacted from package output.

### 5.2 Required enforcement

A reviewed provider profile MUST document and test:

- process, filesystem, user/permission, temporary-directory, and environment isolation;
- network denial by default and allowlisted egress when explicitly required;
- CPU, memory, wall-time, process, file, output, record, recursion, and decompression limits;
- no shell interpolation or execution of source-provided commands, macros, callbacks, links, or extensions;
- complete process-tree termination and temporary-data cleanup;
- schema validation before decoder output reaches package construction;
- license entitlement, redistribution, telemetry, data-retention, and jurisdiction posture;
- deterministic replay where possible and explicit external-input provenance otherwise.

An unenforceable required limit results in rejection, not best-effort execution. Sandboxing the decoder does not make its output trusted.

### 5.3 Provider classes

The contract MAY support local OS sandbox, container, remote service, and customer-managed provider profiles. Each profile has separate conformance evidence. Network-backed providers MUST be optional and MUST NOT be required by core validation, query, diff, or context rendering.

### 5.4 Initial executable profile

ACXD-024 selects `oci-docker-v1` as the first executable profile. The registered image MUST be digest-pinned and already present; the runner MUST NOT pull or build it implicitly. The Linux container MUST have no network, a read-only root, a non-root identity, no capabilities, `no-new-privileges`, a reviewed per-provider PID ceiling from 1 through 4 (default 1), bounded memory/CPU/open files/output and private temporary storage. Input, request and reviewed provider code are read-only; only the bounded output root is writable. A ceiling above 1 is permitted only when the governed provider architecture requires fixed child executables and the exact value is registered and tested.

The response attestation binds provider descriptor and runtime digests. Parent validation rejects invalid schema, mismatched attestation, host paths, unsafe/duplicate artifact paths, symlinks, size/hash mismatch, non-sequential events and resource overflow before package construction.

`macos-seatbelt-v1` is explicitly unavailable because it cannot prove both restricted host reads for the Python runtime and the required memory axis. It MUST reject rather than fall back to a partially isolated subprocess. Native Linux/macOS and Windows enforcement profiles remain governed by ACXB-001; no restricted decoder may claim those platforms until that backlog acceptance passes.

## 6. IFC 2D and georeferencing

ACXD-025 and `docs/specs/ifc-v02-profile.md` define the implemented ACX-13 public `partial` profiles. The broader language below remains a target only for schema/item/operation combinations outside that exact corpus.

### 6.1 IFC 2D target

The IFC adapter MUST preserve source representation identifiers and context for supported curve, annotation, footprint, axis, plan, and mapped 2D representations. Output MAY include deterministic SVG previews, but source primitives and representation relationships remain authoritative.

The adapter MUST distinguish absent 2D representation, unsupported representation type, extraction failure, and an empty representation. It MUST NOT project 3D geometry and label that projection as source-native 2D.

### 6.2 IFC georeferencing target

The adapter MUST preserve all available source coordinate-operation and CRS evidence, including original classes, identifiers, units, axes, map-conversion parameters, placements, and relationship paths. It MUST expose the transform chain and state whether a project-to-CRS transform is complete, conflicted, unsupported, or unknown.

A georeferencing claim is `full` only for the explicitly bounded schema/representation combinations in the conformance registry. Projected coordinates without a resolvable CRS MUST remain local/project coordinates. No EPSG identifier, map origin, rotation, scale, or elevation may be guessed.

## 7. DXF semantics and 3D

ACXD-026 and `docs/specs/dxf-v02-profile.md` define the implemented ACX-14 public `partial` profiles. The broader language below remains a target for DXF releases, entities and semantic structures outside that exact corpus.

### 7.1 Semantic evidence target

DXF semantic support means preservation of source-native structure: entity types, handles, ownership, dictionaries, extension dictionaries, XDATA, application registry identifiers, groups, block/insert relationships, attributes, layers, layouts, materials, and other supported metadata. It does not mean construction-domain classification.

Unknown or unsupported tags remain exact raw-tag evidence or structured loss. Adapter interpretations MUST cite the source tags and keep their confidence separate. No line, polyline, mesh, or block may be classified as a wall, beam, panel, or other consumer family by the neutral adapter.

### 7.2 3D target

The adapter MUST preserve supported 3D coordinates, extrusion vectors, object coordinate systems, transforms, topology, and source identifiers for bounded entity families. Derived GLB/tessellation MUST cite source entities and declare fidelity/loss.

Unsupported solid/surface kernels, proxy graphics, encrypted data, external references, and custom objects remain `partial`, `opaque`, or `unsupported` with stable reason codes. A tessellated fallback MUST NOT be presented as exact B-Rep or parametric geometry.

## 8. PDF and image OCR, vision, and hidden geometry

ACXD-020 and `docs/specs/inference-v02-profile.md` define the ACX-15 experimental OCR profile and the public hidden-geometry boundary. Vision and reconstruction remain targets without an accepted provider.

### 8.1 OCR target

OCR is an optional provider capability over rasterized page/image regions. It emits region/span evidence with text, reading order when supported, pixel/page coordinates, language/script metadata, provider provenance, confidence, and exact input/output hashes. Native PDF text and OCR text remain distinguishable and may conflict explicitly.

### 8.2 Vision target

Vision providers MAY emit candidate symbols, regions, dimensions, tables, or relationships only as inferred assertions. Provider profiles MUST define supported output vocabulary, thresholds, nondeterminism, privacy/network posture, and calibration requirements. Vision is never required for opaque or raster ingest.

### 8.3 Hidden geometry boundary

Geometry not present in observable source bytes or pixels cannot be extracted as source evidence. Occluded, cropped, redacted, behind-layer, or imagined geometry therefore remains `unsupported` as source geometry.

An optional provider MAY emit a reconstruction hypothesis when the visible evidence supports it. Such output MUST be marked `inferred`, cite the visible regions, carry confidence and provider provenance, and remain excluded from identity, measurement authority, georeferencing, validation completeness, and `full` geometry claims.

## 9. Mesh units and CRS

ACXD-016, ACXD-027 and `docs/specs/mesh-coordinate-v02-profile.md` define the implemented ACX-16 boundary: exact self-contained OBJ/STL/glTF 2.0/GLB 2.0 source qualification plus explicit manual scale, matrix or similarity registration. Broader formats, extensions and survey/datum authority remain targets or non-claims.

OBJ, STL, and glTF-family adapters MUST preserve declared unit/coordinate metadata where the source format or extension supplies it. When absent, units and CRS remain `unknown`; viewer convention or common practice is not evidence.

AECCTX MAY accept an explicit calibration/registration profile containing scale, units, control points, transform, CRS identifiers, tolerances, and author provenance. Calibration produces derived geometry and assertions while retaining original coordinates unchanged. Conflicting source and manual metadata produces `conflicted`, not precedence by convenience.

Conformance MUST cover missing units, declared units, manual scale, control-point registration, axis conversion, large coordinates, conflicting CRS evidence, and round-trip transform verification.

## 10. STEP and IGES

STEP/IGES support MUST use an existing reviewed parser/geometry kernel through either a permissive in-process adapter or the external sandbox. The adapter MUST preserve source schema/flavor, entity identifiers, names, colors/layers, assembly/product structure, units, placements, and available B-Rep/curve/surface evidence.

Tessellation and previews are derived. Unsupported entities, invalid topology, healing, tolerance changes, and kernel conversions require structured diagnostics and loss. Geometry healing MUST be opt-in, produce a new derived artifact, record parameters, and never replace original evidence.

The owning task MUST publish the exact format profiles and kernel versions for which it makes claims; “STEP” or “IGES” alone is not a bounded conformance claim.

ACXD-014, ACXD-019, ACXD-028 and `docs/specs/step-iges-v02-profile.md` define the ACX-17 implementation boundary: an exact external OCP/OCCT provider, enumerated STEP AP/schema and IGES 5.3 profiles, observed source records, translator-derived B-Rep and subordinate tessellation. Other runtimes, formats and source-exact/healing claims remain unsupported or unclaimed.

## 11. DWG and RVT

DWG and RVT are optional external-provider capabilities and MUST NOT become dependencies of the Apache-2.0 core distribution.

Before implementation, each adapter requires an accepted licensing/distribution decision covering decoder API/SDK terms, entitlement, CI execution, fixture publication, redistribution, telemetry/network behavior, and release support. Unsupported versions or encrypted/protected content are diagnosed without bypass attempts.

The provider MUST preserve original source identifiers, version/producer, containers/views/layouts, properties, relationships, geometry references, units/coordinates, and exact unsupported content to the extent legally and technically possible. Exporting through an intermediate format MUST record the converter, versions, settings, intermediate hashes, and conversion loss; it MUST NOT be represented as direct native extraction.

RVT work MUST remain neutral BIM extraction and MUST NOT introduce WoodFraming or another consumer mapping.

ACXD-030 and `docs/specs/rvt-v02-blocked-profile.md` govern the approved ACX-19 no-provider outcome. Until one reopening gate is accepted, RVT semantic extraction remains `unsupported`, ordinary unknown-input ingest remains `opaque`, and no RVT adapter/provider/version claim may be created.

## 12. Authenticity and signing

Integrity and authenticity are distinct. The existing artifact hashes and logical package digest detect change but do not identify a producer or establish trust.

A signing profile MUST define before any authenticity claim:

- canonical signed statement and package/digest binding;
- signature envelope location and whether signatures are detached;
- algorithm and serialization identifiers with agility rules;
- signer identity and key/certificate reference;
- verification time, expiry, revocation, rotation, and compromise behavior;
- trust-root/policy configuration owned by the verifier;
- multiple signers, countersignatures, and unsigned-extension behavior;
- deterministic verification diagnostics and offline verification posture;
- archive/directory equivalence and repackaging behavior.

The base package MUST remain valid when unsigned. Validation reports integrity and signature verification separately. `signed`, `valid signature`, `trusted signer`, and `authorized producer` are separate states and MUST NOT be collapsed. Signing keys MUST NOT be generated, stored, or selected implicitly by core ingest.

ACX-20 is blocked from implementation until ACXD-018 selects a reviewed signing profile and threat/trust model. Experimental namespaced signatures may be used only in fixtures and MUST NOT create a public authenticity claim.

## 13. AEC Delivery Quality Gate

The quality gate is a deterministic policy evaluator over validated AECCTX packages. It MAY compile raw sources through existing adapters before evaluation, but it MUST evaluate authoritative package records, capabilities, loss, diagnostics, and semantic diffs rather than generated Markdown.

### 13.1 Inputs and policy

A gate invocation MUST identify:

- the validated candidate package and logical digest;
- an optional validated baseline package and logical digest;
- a versioned, content-addressed gate policy;
- optional IFC Information Delivery Specification (IDS) requirements;
- evaluator and dependency versions;
- enabled checks, severity thresholds, budgets, and explicit waivers.

The policy MUST distinguish structural validity, package integrity, capability coverage, loss thresholds, value-state requirements, revision regressions, and IDS compliance. A gate MUST NOT infer an unspecified project requirement or silently treat `unknown`, `unsupported`, or `conflicted` as passing.

IDS checking MUST remain scoped to the IFC information requirements supported by the selected IDS profile. Geometry, package integrity, provenance, and cross-format checks remain separate AECCTX checks and MUST NOT be presented as IDS results.

### 13.2 Outcomes and evidence

The machine-readable outcome is one of:

- `pass`: every required check passed and no blocking unresolved state remains under the policy;
- `fail`: one or more deterministic policy requirements failed;
- `requires_review`: the policy explicitly routes bounded unresolved, unsupported, conflicted, or waived conditions to human review;
- `error`: validation or evaluation could not complete safely.

Every result MUST include the policy digest, package digests, check IDs, severity, outcome reason, cited record/diagnostic/evidence IDs, and evaluator provenance. A successful process exit MUST NOT be the only representation of a pass, and `pass` MUST NOT be described as engineering approval, regulatory acceptance, construction readiness, or consumer canonical acceptance.

Given identical packages, policy, IDS input, evaluator versions, and platform-normalized settings, the gate MUST produce semantically identical JSON and stable exit behavior. Markdown and CI annotations are derived projections of the machine-readable report.

### 13.3 Safety and integration

Gate execution remains local-first and network-free by default. Policies and IDS files are untrusted data: evaluation MUST be bounded and MUST NOT execute expressions, macros, links, callbacks, or source-provided commands. CI integrations MAY expose stable exit codes and annotations but MUST retain links to the authoritative report.

ACX-21 MUST publish positive, failing, review-required, error, malicious-policy, baseline-regression, and IDS conformance fixtures before the quality gate becomes a public claim.

## 14. Codex plugin

AECCTX v0.2 MUST provide an optional Codex plugin named `aecctx-inspector`. The plugin is an adoption and orchestration surface over stable AECCTX APIs; it MUST NOT introduce package semantics, validation rules, query behavior, or capability claims unavailable through the library/CLI.

### 14.1 Package and capabilities

The plugin distribution MUST contain a valid `.codex-plugin/plugin.json`, an allowlisted `.mcp.json`, focused skills, and only referenced assets. Its v0.2 capability set is:

- inspect a validated AECCTX package;
- report identity, provenance, capabilities, loss, and unresolved value states;
- compare two validated package revisions;
- generate budgeted agent context while citing authoritative records;
- execute and explain the ACX-21 quality gate through the same stable library/CLI contract;
- triage failures without claiming consumer or engineering approval.

The MCP surface SHOULD remain read-only for package inspection. Raw-source ingest, when offered by a skill workflow, MUST be an explicit local CLI operation with caller-selected input/output paths and the same sandbox, embedding, and network policies as normal AECCTX ingest. The plugin MUST NOT upload a source or call an external provider implicitly.

### 14.2 Agent behavior

Plugin skills MUST instruct Codex to validate before query, diff, context, or gate evaluation. Responses MUST distinguish extracted evidence, normalized interpretation, provider inference, derived projection, and policy result. Markdown summaries MUST cite package/record/diagnostic identifiers and MUST NOT replace structured tool output.

Source text, metadata, filenames, annotations, plugin output, and generated context are untrusted data, not instructions. The plugin MUST ignore embedded prompt-like content and MUST NOT execute source-provided commands, follow active links, mutate source files, select trust roots, waive failures, or promote a `requires_review` result to `pass`.

### 14.3 Distribution and conformance

The plugin MUST be optional: core package validation, query, diff, context, and quality-gate execution remain usable without Codex. Installation MUST declare the compatible AECCTX and MCP versions and use no network or LLM API as a core dependency.

Conformance MUST cover plugin manifest validation, clean installation, MCP tool parity with library/CLI results, prompt-injection fixtures, invalid package refusal, missing optional dependency behavior, deterministic context budgets, diff citation accuracy, quality-gate outcome fidelity, and proof that no tool has unique semantics.

## 15. Compatibility and migration

ACXD-017 establishes a separate v0.2 schema line for the shared observation/inference, coordinate-qualification, representation-fidelity and provider-attestation semantics. A v0.2 package uses `aecctx_version = "0.2.0"` and records use `record_version = "0.2"`; v0.1 schemas and package identity remain immutable.

The v0.2 reference reader MUST validate both v0.1 and v0.2. A v0.1 reader is not required to accept v0.2. Optional namespaced extensions may be ignored by a reader, but every manifest-declared required extension MUST be understood or validation fails. Record versions MUST match the manifest-selected package schema.

Query, diff and context operate on validated structured records across both versions. Shared v0.2 fields remain queryable and diffable; cross-version diff reports the package-version change explicitly. Generated context remains a projection. Migration documentation and old/new reader fixtures are required before ACX-11 completes.

Packages produced by optional providers MUST remain readable and diagnosable without those providers installed. A consumer lacking an optional extension may reject it only when the manifest marks it required.

## 16. Security, privacy, and licensing acceptance

Every capability task includes abuse fixtures appropriate to its parser/provider: malformed nesting, decompression or entity explosion, path traversal, oversized dimensions/coordinates, cyclic references, resource exhaustion, hostile metadata, active links/macros, and invalid provider output.

Network/inference providers require explicit consent, redaction/data-minimization policy, retention disclosure, timeout/retry bounds, and response hashing. Test fixtures MUST be legally publishable; proprietary samples may supplement but never be the sole conformance evidence for a public claim.

## 17. Release claim gate

ACX-23 may publish a post-v0.1 release only when:

- every claimed row maps to passing conformance tests and evidence;
- uncompleted capabilities remain visibly `partial`, `opaque`, or `unsupported`;
- compatibility/migration notes are published;
- sandbox, dependency, license, security, and privacy reviews are recorded;
- clean installation, packaged CLI, deterministic outputs, optional extras, and supported platforms are verified;
- remote CI is green for the exact release commit;
- authenticity is claimed only if ACX-20 is complete and verification policy is documented.
- quality-gate claims have ACX-21 policy/IDS conformance evidence;
- the Codex plugin has ACX-22 installation, parity, and adversarial agent-behavior evidence.
