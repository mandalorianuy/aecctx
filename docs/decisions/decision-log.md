# AECCTX Decision Log

Date: 2026-07-12
Status: Active

## Accepted decisions

### ACXD-001: Separate public repository

- Decision: AECCTX is application-agnostic and lives independently from WoodFraming.
- Consequence: Consumer ontologies, workflows, approvals, and canonical mutations stay outside this repository.

### ACXD-002: Markdown is a projection

- Decision: JSON/JSONL records and referenced binary/vector artifacts are authoritative. Markdown is deterministically generated navigation and context.
- Consequence: No geometry, identity, provenance, confidence, or diagnostic claim may exist only in Markdown.

### ACXD-003: Evidence precedes interpretation

- Decision: Source evidence, normalized interpretation, and consumer mapping are distinct layers.
- Consequence: An adapter may extract a DXF line or IFC class but cannot claim it is a consumer-domain wall without a separate mapping authority.

### ACXD-004: Honest universal ingestion

- Decision: Every file may be registered, fingerprinted, and diagnosed, but adapters declare `full`, `partial`, `opaque`, or `unsupported` support per capability.
- Consequence: “Any file” means no silent rejection or loss, not perfect semantic conversion of every proprietary format.

### ACXD-005: Deterministic local-first core

- Decision: Core ingest, validation, query, diff, and context generation require neither network access nor an LLM.
- Consequence: Network and inference providers are optional, explicit plugins whose outputs carry provider provenance.

### ACXD-006: Python reference implementation

- Decision: The initial CLI and SDK target Python 3.12+, with JSON Schema as the cross-language contract.
- Consequence: Swift and TypeScript consumers may generate or implement bindings without making Python runtime authority part of the format.

### ACXD-007: Adapter licensing boundary

- Decision: The core is Apache-2.0. GPL and commercial decoders run behind optional process/plugin boundaries and are not bundled by default.
- Consequence: Direct DWG/RVT claims require adapter-specific licensing, execution, version, determinism, and evidence-preservation review.

### ACXD-008: Read-oriented v0.1

- Decision: v0.1 compiles and reads source context; it does not promise write-back to authoring formats.
- Consequence: Agent modifications target future reviewed patch contracts, not source files or generated Markdown in v0.1.

### ACXD-009: Builder baseline posture

- Decision: The repository consumes `baseline-shared-v1` using the `builder` specialization profile.
- Consequence: Shared shell governance remains baseline-owned and repository policy extends it only through the managed overlay and project instructions.

### ACXD-010: Open project vocabulary with external classifications

- Decision: v0.1 uses a small, versioned project registry for compact `aecctx:` neutral kinds and relation types, while allowing optional stable external classification URIs and explicit unregistered extension terms.
- Consequence: The registry improves deterministic query/context behavior without becoming a universal or consumer ontology. `original_class` remains mandatory evidence and registry membership never implies downstream acceptance.
- Evidence: `schemas/v0.1/neutral-vocabulary.json` and ACX-03 record/query conformance tests.

### ACXD-012: Source embedding policy defaults

- Decision: Generated packages default to `external`; `embedded` and `redacted` retention require an explicit caller policy.
- Consequence: Opaque ingest never copies untrusted source bytes into a package implicitly. Every policy remains recorded with the exact source hash, and embedded content is inventoried as authoritative source evidence.
- Evidence: ACX-02 conformance tests cover all policies, streaming hashing, deterministic package identity, and explicit embedding.

### ACXD-011: Package signing deferred beyond v0.1

- Decision: v0.1 standardizes SHA-256 artifact integrity and the logical package digest, but does not standardize or claim package authenticity.
- Consequence: Detached signatures may be carried only as optional namespaced extensions that do not alter v0.1 conformance. A future signing contract must decide canonical signed bytes, algorithm agility, key identity/distribution, revocation and trust policy before authenticity claims are allowed.
- Evidence: ACX-02/ACX-07 deterministic digest tests and ACX-08 security review show stable integrity inputs but no governed trust/key lifecycle.

### ACXD-013: Capability expansion does not revise v0.1 claims

- Decision: Post-v0.1 gaps are governed by `docs/specs/aecctx-capability-expansion-spec.md` as targets. They remain partial or unsupported until their owning task publishes conformance evidence and updates the capability matrix.
- Consequence: Planning, experimental code, or an optional dependency cannot silently promote a public support claim.

### ACXD-014: External sandbox precedes restricted decoders

- Decision: Native, GPL, commercial, and network-backed decoders require a separately reviewed external sandbox provider contract before adapter implementation. The built-in Python worker is not sufficient merely because it is process-isolated.
- Consequence: ACX-12 is a prerequisite for STEP/IGES kernels that cannot use the permissive path and for all DWG/RVT provider work. Caller-provided commands remain prohibited.

### ACXD-015: Hidden geometry is not extractable evidence

- Decision: Geometry absent from observable source bytes or pixels remains `unsupported` as source geometry. Optional reconstruction may exist only as an inference hypothesis with provider provenance, confidence, visible-evidence citations, and no measurement or completeness authority.
- Consequence: OCR/vision work cannot turn plausible reconstruction into a `full` geometry claim.

### ACXD-016: Calibration augments but never rewrites source coordinates

- Decision: Caller-supplied mesh units, control points, transforms, or CRS are manual/derived assertions. Original coordinates and unknown/conflicted states remain preserved.
- Consequence: A calibrated artifact may become usable in a declared coordinate frame without falsifying what the source itself declared.

### ACXD-017: v0.2 schema and compatibility boundary

- Decision: Shared observation/inference, coordinate-qualification, representation-fidelity, provider-attestation, and required-extension semantics are versioned in new `schemas/v0.2` package and record schemas. A v0.2 package uses `aecctx_version = "0.2.0"` and `record_version = "0.2"`; v0.1 schemas and packages remain immutable.
- Compatibility: The v0.2 reference reader validates both v0.1 and v0.2 packages. A v0.1 reader is not required to accept v0.2. Optional namespaced extensions may be ignored while reading but remain part of package bytes; every declared required extension must be supported or validation fails with a stable diagnostic. Records within one package use the record version selected by its manifest.
- Query/diff/context: Shared v0.2 fields are authoritative structured record fields and remain queryable and diffable as normal JSON. Diff reports a record change when those fields change; context may project them but never becomes their authority. Cross-version comparison is allowed after both packages validate and reports the manifest version change explicitly.
- Consequence: Later capabilities share one typed v0.2 substrate instead of encoding normative semantics as loosely governed v0.1 extensions. Existing v0.1 package identity, query, diff, context, validation and conformance behavior remain stable.
- Evidence: `schemas/v0.2/`, `fixtures/v0.2/shared/minimal-v02`, `conformance/v0.2/claims.json`, `docs/compatibility-v0.2.md`, and `docs/evidence/ACX-11.md`.

### ACXD-021: Quality gates express policy conformance only

- Decision: The AEC Delivery Quality Gate evaluates versioned policies over authoritative AECCTX records, capabilities, loss, diagnostics, diffs, and bounded IDS requirements. Its `pass` result is not engineering approval, regulatory acceptance, construction readiness, or consumer canonical acceptance.
- Consequence: Gate results remain reproducible evidence with explicit `pass`, `fail`, `requires_review`, and `error` outcomes; unresolved states cannot be silently defaulted into success.

### ACXD-022: Codex plugin is an optional orchestration surface

- Decision: `aecctx-inspector` packages focused skills and allowlisted MCP access over stable AECCTX library/CLI behavior. It introduces no unique package semantics and keeps v0.2 MCP inspection read-only.
- Consequence: AECCTX remains usable without Codex or an LLM, source content remains untrusted data, and plugin responses cannot elevate Markdown, inference, or presentation above structured evidence and policy results.

### ACXD-024: External provider protocol and first enforcement profile

- Decision: ACX-12 uses a versioned JSON file protocol over a private content-addressed workspace. Callers select only an allowlisted `provider_id`; registrations own immutable launch targets, runtime roots, license/network posture, supported actions and enforcement claims. Provider output is schema-validated and hash-checked before it reaches package construction.
- Reference profile: The first executable enforcement profile is `oci-docker-v1`. It requires an allowlisted, digest-pinned image already present in a reviewed Docker-compatible runtime and launches with no network, read-only root filesystem, non-root user, dropped capabilities, `no-new-privileges`, bounded memory/CPU/PIDs/files, private tmpfs, read-only content-addressed input and a single bounded output mount. The runner never pulls an image implicitly.
- Rejected alternative: `macos-seatbelt-v1` remains unavailable for restricted decoders. Conformance showed that the Python runtime requires host-wide reads under Seatbelt and macOS does not provide a usable per-process address-space rlimit for this profile. Allowing broad host reads or silently omitting the memory axis would violate the contract.
- Portability: Protocol/schema/registry validation is portable. A host without a reviewed complete enforcement profile rejects execution with `AECCTX_PROVIDER_PROFILE_UNAVAILABLE`; it does not fall back to the in-process worker or an unconfined subprocess.
- Consequence: ACX-12 claims the digest-pinned Linux-container provider environment wherever the reviewed Docker runtime passes preflight. Native host profiles and Windows-container execution remain blocked by ACXB-001.
- Evidence owner: ACX-12 protocol schemas, Linux-container reference provider corpus, threat model, tests and acceptance evidence.

### ACXD-025: Bounded IFC v0.2 profile and opt-in emission

- Decision: ACX-13 implements only the source-native 2D and coordinate profiles enumerated in `docs/specs/ifc-v02-profile.md`, using optional `ifcopenshell==0.8.5`. Public fixtures/claims are limited to IFC2X3 TC1 and IFC4 Add2 TC1. A different IfcOpenShell version or later IFC family remains unclaimed until separately proven.
- 2D boundary: Only explicitly 2D contexts/views/identifiers and the listed polyline/indexed-line/geometric-curve-set/mapped-item profiles are normalized. Unsupported curves, text, hatch, styling and other items remain source evidence and structured loss; 3D projection can never be relabeled source-native.
- IfcOpenShell 0.8.5 mapped-2D limitation: `resolve_items()` does not yield a usable matrix for `IfcCartesianTransformationOperator2D`; ACX-13 therefore performs bounded structural extraction of the explicit mapping source/origin/target attributes for that operator only. Other mapped operators remain unsupported rather than falling back to 3D projection.
- Coordinate boundary: A complete global link requires one explicit IFC4 `IfcMapConversion` to one `IfcProjectedCRS`, finite/invertible WCS and operation matrices, explicit non-zero axes/positive scale, compatible declared project/map units and a non-empty source CRS name. IFC defaults, EPSG IDs or missing parameters are not synthesized for a public complete claim.
- Compatibility: `ingest_ifc()` remains v0.1 by default. ACX-13 behavior is explicitly selected with `aecctx_version="0.2.0"`; v0.1 fixture/package identity stays unchanged.
- Consequence: both IFC 2D and georeferencing remain public `partial` claims with exact schema/item/operation scope and explicit absent/empty/unsupported/failure/conflict states.
- Evidence owner: ACX-13 fixtures, claim mappings, deterministic SVG/replay tests and acceptance evidence.

### ACXD-026: Bounded DXF v0.2 profiles and opt-in emission

- Decision: ACX-14 implements only the source-semantic and bounded-3D profiles enumerated in `docs/specs/dxf-v02-profile.md`, using optional `ezdxf==1.4.4`. Public fixtures are limited to project-authored `AC1015` and `AC1032` ASCII/binary inputs; other releases or ezdxf versions remain unclaimed.
- Semantic boundary: source handles/owners, dictionaries, extension dictionaries, XDATA/application IDs, groups, attributes, materials, layouts/layers and block/insert structure remain source evidence. Normalization cites those records and never infers construction families from names or geometry.
- Geometry boundary: only the listed point/line/face/mesh/polyline and insert/OCS profiles are source-normalized. GLB/triangles are derived tessellation with explicit fidelity, transforms and loss. ACIS solids/surfaces, proxy/custom objects, xref traversal and encrypted/protected content remain raw/opaque/unsupported.
- Compatibility: `ingest_dxf()` remains v0.1 by default. ACX-14 behavior is explicitly selected with `aecctx_version="0.2.0"`; v0.1 fixture/package identity remains unchanged.
- Consequence: both DXF claims remain public `partial` claims bounded by exact releases, entities, dependency version and corpus evidence.
- Evidence owner: ACX-14 fixtures, claim mappings, deterministic replay, security/loss tests and acceptance evidence.

### ACXD-020: Optional inference provider profiles

- OCR decision: ACX-15 selects experimental `org.aecctx.ocr.tesseract-tsv@0.2.0`, bounded to Ubuntu Noble `tesseract-ocr=5.3.4-1build5`, its official C API loaded through Python `ctypes`, English data `1:4.1.0-2`, LSTM and PSM 6 under ACX-12 `oci-docker-v1`. OpenMP is fixed to one thread so the existing `pids=1` sandbox is preserved. It is local, deterministic for fixed bytes/config/runtime, network-disabled and emits `aecctx.ocr.words.v1` word evidence.
- Image verification: a locally built provider image may be registered by allowlisted tag only when registration also pins its inspected immutable Docker image ID. Preflight rejects an ID mismatch; it never pulls/builds or trusts a mutable tag alone. The original digest-addressed ACX-12 path remains valid.
- Replay/claim boundary: validated offline replay is portable conformance for protocol and mapping but does not prove provider runtime availability. OCR remains release-governance `experimental` until the exact image/provider/platform execution matrix is public and green.
- Vision decision: no vision or reconstruction provider is accepted in ACX-15. Those capabilities remain `unsupported`; hidden/unobserved geometry remains unsupported as source evidence under ACXD-015.
- Privacy/licensing: the selected runtime is local with no egress, telemetry or retention; Tesseract and selected English trained data are Apache-2.0. Pillow remains an isolated provider dependency under its own license. No inference dependency enters the Apache-2.0 core wheel.
- Evidence owner: ACX-15 provider descriptor/worker/build recipe, replay corpus, mapping/adversarial tests and acceptance evidence.

## Open decisions

### ACXD-018: Signing and trust profile

- Owner: ACX-20.
- Decision required: select the canonical signed statement, envelope/serialization, algorithm agility, signer identity model, trust-root policy, offline verification, expiry/revocation, multiple-signature, and repackaging behavior.
- Blocking effect: authenticity/signing implementation and claims only; other capability tasks may proceed.

### ACXD-019: Restricted decoder distribution and entitlement

- Owner: adapter-specific ACX-17, ACX-18, or ACX-19 task before implementation.
- Decision required: for each selected STEP/IGES, DWG, or RVT provider, record license compatibility, entitlement, redistribution, CI access, fixture rights, telemetry/network behavior, supported platforms, and support lifecycle.
- Blocking effect: only the affected provider/format. An adapter may remain unsupported while other tasks continue.

### ACXD-023: Quality-gate policy and IDS implementation profile

- Owner: ACX-21.
- Decision required: version the gate policy schema; select the reviewed IDS parser/checker or bounded implementation; enumerate supported IDS versions/facets; define stable check IDs, severities, waivers, outcome aggregation, exit codes, and official conformance-suite scope.
- Blocking effect: ACX-21 quality-gate implementation and its ACX-22 plugin workflow only; earlier format, signing, and sandbox tasks may proceed.
