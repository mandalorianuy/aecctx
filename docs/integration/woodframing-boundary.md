# WoodFraming Integration Boundary

Date: 2026-07-11
Status: Planning boundary only; implementation deferred

## Ownership

AECCTX owns:

- source fingerprinting and extractor provenance;
- immutable evidence records;
- neutral entities, relations, property assertions, geometry references, previews, diagnostics, and loss reports;
- deterministic context generation and package validation.

WoodFraming owns:

- mapping neutral/source records to `WFImport` candidates;
- construction-family classification;
- alignment acceptance, matching, conflict resolution, review, and commit authorization;
- canonical identity, authority, readiness, engineering status, regeneration, and outputs.

## Required adapter direction

```text
source file -> AECCTX package -> WoodFramingAECCTXAdapter -> WFImport staging -> reviewed canonical commit
```

The public AECCTX repository must not import WoodFraming packages. The eventual adapter should live in WoodFraming or a consumer-owned bridge package.

## Mapping invariants

- AECCTX `source_id`, `record_id`, source locator, hashes, extractor version, value state, confidence, and diagnostics survive into staging evidence.
- AECCTX normalized kinds are proposals/evidence, not accepted WoodFraming families.
- Generated Markdown is never parsed as authoritative import data.
- Unsupported or opaque records remain reviewable evidence rather than disappearing.
- Reimport compares immutable AECCTX source revisions and stable source-local identities before geometric fallbacks.

## Entry gate for integration planning

Detailed WoodFraming integration specification begins only after ACX-02 proves package identity, evidence, diagnostics, and deterministic validation. IFC/DXF-specific mapping may wait for ACX-04/ACX-05 fixtures.
