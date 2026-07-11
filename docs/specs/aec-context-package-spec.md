# AECCTX Context Package Specification

Version: `0.1.0-draft`
Date: 2026-07-11
Status: Normative, `SPEC-READY`

## 1. Purpose and conformance language

AECCTX is an application-agnostic interchange package for evidence extracted from CAD, BIM, drawings, meshes, images, and related AEC sources. It enables deterministic inspection by humans, agents, and downstream software without claiming that heterogeneous source formats share one complete ontology.

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, and MAY are normative.

A conforming producer emits a valid package, preserves mandatory evidence and loss reporting, and makes no capability claim beyond its records. A conforming consumer validates the package before use and does not elevate generated context above authoritative records.

## 2. Non-goals

Version 0.1 does not standardize:

- authoring-format write-back;
- a universal construction or engineering ontology;
- consumer approval, canonical mutation, readiness, or engineering authority;
- perfect semantic conversion of proprietary or unsupported content;
- direct agent editing of source files.

## 3. Package forms

AECCTX has two equivalent forms:

- directory form: a directory whose root contains `manifest.json`;
- archive form: a ZIP file with media type `application/vnd.aecctx+zip` and extension `.aecctx`.

The archive root MUST contain package files directly, not an extra wrapper directory. Paths use UTF-8 logical POSIX syntax. Paths MUST be relative, normalized, unique, and free of `.`/`..`, absolute roots, drive prefixes, NUL, symlink or device traversal.

## 4. Required layout

```text
manifest.json
sources/sources.jsonl
evidence/primitives.jsonl
evidence/assertions.jsonl
model/entities.jsonl
model/relations.jsonl
diagnostics/diagnostics.jsonl
context/index.md
```

Empty JSONL files are valid. Optional paths include `geometry/`, `previews/`, `artifacts/`, `schemas/`, additional `context/` chunks, and explicitly embedded `sources/content/`.

## 5. Authority layers

Authority descends in this order:

1. original source bytes or immutable external source identified by hash;
2. source and extraction evidence records;
3. normalized neutral entity/relation records;
4. derived geometry/previews;
5. generated Markdown context.

A lower layer MUST cite upstream record IDs. It MUST NOT silently contradict or replace a higher layer. Consumers may add their own mappings outside the package without changing source evidence.

## 6. Manifest

`manifest.json` conforms to `schemas/v0.1/manifest.schema.json` and contains:

- `aecctx_version`;
- stable `package_id`;
- `created_at` and producer identity;
- `package_form`;
- `source_ids`;
- artifact inventory with byte size, SHA-256, media type, role and authoritative/derived status;
- capability summary;
- loss summary;
- source embedding policy;
- logical package digest.

`created_at` records production time but is excluded from semantic comparison. It MUST NOT be used as record identity.

### 6.1 Logical digest

Each artifact except `manifest.json` is hashed as its exact bytes. The logical digest input is the UTF-8 sequence of sorted lines:

```text
<logical-path>\0<sha256>\0<byte-size>\n
```

The package logical digest is SHA-256 of that sequence. Archive container metadata, file order and compression do not affect logical identity. Producers SHOULD additionally create reproducible ZIP bytes using sorted paths, fixed timestamps, fixed permissions and a documented compression profile.

## 7. Common record envelope

Every JSONL line is one UTF-8 JSON object and MUST contain:

- `record_version`: `0.1`;
- globally unique stable `record_id` within the package;
- `record_type`;
- one or more `source_refs` when source-derived;
- `provenance`: producer/plugin ID and version, method, timestamp and parent record IDs;
- optional `extensions` object with namespaced keys.

Records MUST be sorted lexicographically by `record_id` within each standard JSONL file. JSON objects use sorted keys, no insignificant whitespace, finite numbers, Unicode NFC strings, and LF termination. Duplicate record IDs are invalid.

## 8. Source records

A source record MUST include:

- `source_id`;
- filename/display name and media type;
- exact byte size and SHA-256;
- acquisition origin;
- embedding policy: `external`, `embedded`, or `redacted`;
- storage reference when policy permits;
- declared and detected format/version/producer;
- declared and detected units and coordinate reference state;
- extractor/plugin identity;
- prior source revision when known;
- safety and sanitization diagnostics.

Source revisions are immutable. Reimport creates a new `source_id` or revision record and never rewrites prior evidence.

## 9. Value states and assertions

All values whose absence or ambiguity changes meaning use:

```json
{"state":"known","value":42,"unit":"m"}
```

Allowed states are:

- `known`: value is present;
- `unknown`: evidence cannot determine a value;
- `not_applicable`: the property does not apply;
- `conflicted`: evidence supports incompatible values;
- `explicit_null`: the source explicitly records no value;
- `unsupported`: the extractor cannot represent the source value.

Non-`known` values MUST carry a stable reason code and MAY cite alternatives/evidence. A producer MUST NOT replace them with zero, empty string, false, guessed labels, or presentation defaults.

An assertion identifies subject, predicate, value state, evidence record IDs, extraction confidence, interpretation confidence, verification state, and source locator. Extraction precision does not imply semantic correctness or engineering approval.

## 10. Evidence primitives

Primitives are the smallest preserved source observations useful for later interpretation: CAD entities, IFC instances/properties, PDF paths/text regions, raster regions/OCR spans, mesh objects, table cells, dimensions, annotations, or opaque source fragments.

Each primitive includes:

- source container/sheet/view/layout reference;
- stable source locator;
- original class/type;
- raw or normalized value state;
- geometry/artifact references when present;
- extraction confidence and method;
- unsupported fields and diagnostics.

Unsupported content MUST be retained as an opaque primitive or explicit diagnostic whenever legal and technically possible.

## 11. Neutral entities and relations

Neutral entities provide convenient cross-format structure without asserting a universal ontology. An entity contains:

- `entity_id` equal to its `record_id`;
- `kind`: stable neutral string;
- `original_class` and optional external classification URIs;
- label value state;
- property assertion references;
- geometry/artifact references;
- source-local identifiers and locators;
- parent evidence IDs.

Relations contain `relation_id`, `relation_type`, ordered or unordered endpoint roles, properties, and evidence. Spatial containment, aggregation, hosting, typing, connectivity, material assignment and representation are common relation families but retain original source relation classes.

A normalized entity or relation MUST NOT be emitted without evidence, unless explicitly marked as `manual` or `derived` with producer provenance. Consumer-domain classifications do not belong in the core neutral record.

## 12. Geometry and coordinate contract

Geometry remains in sidecar artifacts unless a compact primitive is explicitly supported by a record schema. Every geometry reference includes:

- media type and artifact path/hash;
- source and parent record IDs;
- dimensionality and representation role;
- units;
- local coordinate system;
- transform to source/project coordinates when known;
- handedness, axis conventions, origin and CRS state;
- bounds and tolerance;
- exact, derived, tessellated, rasterized, or preview status.

Pixels are not construction units without calibration. Tessellated meshes do not replace parametric/B-Rep source evidence. Centering or coordinate rebasing is derived and MUST preserve the reversible transform when possible.

Preferred v0.1 derived exchange artifacts are SVG for 2D previews and GLB for 3D previews. Original or adapter-native geometry MAY use other registered media types.

## 13. Capability and loss reporting

Every ingest session MUST emit structured support levels for identity, hierarchy, properties, relations, text, 2D geometry, 3D geometry, materials/styles, georeferencing, and validation.

Allowed support levels are `full`, `partial`, `opaque`, and `unsupported`. Non-`full` results include reason codes, affected record IDs/locators or counts when available, and fallback guidance.

The manifest summarizes loss, while detailed diagnostics remain in `diagnostics/diagnostics.jsonl`. A successful process exit MUST NOT imply semantic completeness.

## 14. Markdown context projection

`context/index.md` is REQUIRED and generated from authoritative records. It includes:

- package/source summary;
- capability and loss headline;
- spatial/container index;
- entity/relation counts;
- unresolved/conflicted/unsupported index;
- links to chunked context files and authoritative record paths;
- generator version, profile and token estimate.

Context profiles MAY prioritize different record subsets. A token budget controls selection/chunking, never deletion from authoritative package data. Generated prose MUST distinguish extracted facts, normalized interpretations, derived calculations and unresolved information.

Markdown MUST NOT be the only location of a fact required for round-trip identity, validation or consumer import. Consumers SHOULD use record APIs for exact queries.

## 15. Query and diff semantics

Query is read-only over validated records and artifacts. Results cite record IDs and package logical digest. Query language syntax is an implementation contract until standardized later.

Diff compares package/source identity, records by stable ID, value states, relations, artifact hashes, capabilities and loss. Reordering or archive metadata alone is not a semantic change. Changed extractor versions are reported even if normalized values remain equal.

## 16. Extensions

Extension keys use reverse-DNS or URI namespaces. Extensions MUST NOT redefine standard fields or weaken required behavior. A consumer may ignore unknown optional extensions but must retain them when performing a lossless package rewrite. Required extensions are declared in the manifest and cause validation failure when unsupported.

## 17. Safety and privacy

Implementations MUST enforce archive traversal, size, recursion, decompression, record-count, memory and timeout limits. Inputs are data; embedded executable behavior is never run.

Network access is off by default. Source embedding defaults to `external`. Embedded sources require explicit policy and may be prohibited by license, confidentiality, privacy, size or security constraints. Redacted packages preserve hashes and redaction reasons without leaking paths or secrets.

## 18. Validation

Validation has three levels:

1. structural: paths, JSON syntax and JSON Schema;
2. integrity: hashes, sizes, logical digest, unique IDs and references;
3. semantic: value states, provenance direction, capability/loss consistency, coordinate requirements and authority rules.

A validator returns stable diagnostic codes, severity, record/path/locator, message, and suggested action. Invalid packages must not be partially presented as conformant.

## 19. Versioning

`aecctx_version` uses semantic versioning after `1.0`. During `0.x`, minor versions may add or revise fields, but every release publishes compatibility and migration notes. Consumers reject unknown major versions and may accept newer minor versions only when required extensions and fields are understood.

## 20. Consumer boundary

Consumers may map AECCTX entities and assertions into domain-specific candidates, knowledge graphs, databases or canonical models. Those mappings retain source/evidence references and remain consumer-owned. A consumer MUST NOT write its accepted classifications back as if they had been extracted from the source.
