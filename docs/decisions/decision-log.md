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

## Open decisions

### ACXD-010: Stable neutral vocabulary registry

- Question: Should normalized `kind` and `relation_type` values use project-owned URIs, buildingSMART/bSDD references, or a hybrid registry?
- Non-blocking boundary: v0.1 accepts stable strings plus optional external classification URIs and always preserves `original_class`.
- Owner: `ACX-03`.

### ACXD-011: Package signing

- Question: Should v0.1 standardize detached signatures or defer signatures until the logical digest contract has implementation evidence?
- Non-blocking boundary: SHA-256 content integrity is required; authenticity is not claimed.
- Owner: `ACX-08`.

### ACXD-012: Source embedding policy defaults

- Question: Should generated packages default to external, embedded, or redacted source retention for different source classes?
- Non-blocking boundary: v0.1 defaults to `external`; embedding requires an explicit flag and records licensing/privacy policy.
- Owner: `ACX-02`.
