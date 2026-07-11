# AECCTX Decision Log

Date: 2026-07-11
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

### ACXD-021: Quality gates express policy conformance only

- Decision: The AEC Delivery Quality Gate evaluates versioned policies over authoritative AECCTX records, capabilities, loss, diagnostics, diffs, and bounded IDS requirements. Its `pass` result is not engineering approval, regulatory acceptance, construction readiness, or consumer canonical acceptance.
- Consequence: Gate results remain reproducible evidence with explicit `pass`, `fail`, `requires_review`, and `error` outcomes; unresolved states cannot be silently defaulted into success.

### ACXD-022: Codex plugin is an optional orchestration surface

- Decision: `aecctx-inspector` packages focused skills and allowlisted MCP access over stable AECCTX library/CLI behavior. It introduces no unique package semantics and keeps v0.2 MCP inspection read-only.
- Consequence: AECCTX remains usable without Codex or an LLM, source content remains untrusted data, and plugin responses cannot elevate Markdown, inference, or presentation above structured evidence and policy results.

## Open decisions

### ACXD-017: Post-v0.1 schema/version boundary

- Owner: ACX-11.
- Decision required: determine which observation/inference, coordinate, fidelity, and provider-attestation fields are optional v0.1 extensions and which require `0.2` schemas/events.
- Acceptance: compatibility matrix, migration rules, old/new reader fixtures, and required-extension behavior.

### ACXD-018: Signing and trust profile

- Owner: ACX-20.
- Decision required: select the canonical signed statement, envelope/serialization, algorithm agility, signer identity model, trust-root policy, offline verification, expiry/revocation, multiple-signature, and repackaging behavior.
- Blocking effect: authenticity/signing implementation and claims only; other capability tasks may proceed.

### ACXD-019: Restricted decoder distribution and entitlement

- Owner: adapter-specific ACX-17, ACX-18, or ACX-19 task before implementation.
- Decision required: for each selected STEP/IGES, DWG, or RVT provider, record license compatibility, entitlement, redistribution, CI access, fixture rights, telemetry/network behavior, supported platforms, and support lifecycle.
- Blocking effect: only the affected provider/format. An adapter may remain unsupported while other tasks continue.

### ACXD-020: Optional inference provider profiles

- Owner: ACX-15.
- Decision required: define the first local and/or network OCR/vision profiles, supported vocabulary, privacy/retention policy, nondeterminism class, thresholds, packaging extras, and conformance scope.
- Blocking effect: the affected inference profile; baseline PDF/image extraction remains available without it.

### ACXD-023: Quality-gate policy and IDS implementation profile

- Owner: ACX-21.
- Decision required: version the gate policy schema; select the reviewed IDS parser/checker or bounded implementation; enumerate supported IDS versions/facets; define stable check IDs, severities, waivers, outcome aggregation, exit codes, and official conformance-suite scope.
- Blocking effect: ACX-21 quality-gate implementation and its ACX-22 plugin workflow only; earlier format, signing, and sandbox tasks may proceed.
