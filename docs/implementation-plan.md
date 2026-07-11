# AECCTX Implementation Plan

Date: 2026-07-11
Status: Active implementation authority
Specification readiness: `SPEC-READY`

## Execution rule

Execute only the first task with status `pending-next` or `in_progress`. Update this plan and attach acceptance evidence before advancing. A later task may not borrow scope from an earlier task.

## Task ledger

| Task | Status | Outcome |
|---|---|---|
| ACX-00 | completed | Repository, research, normative specs, schemas, fixture, governance, validation and implementation handoff |
| ACX-01 | pending-next | Python package/CLI scaffold and schema-backed validator |
| ACX-02 | pending | Deterministic package reader/writer, hashes, source registration and opaque fallback |
| ACX-03 | pending | Neutral record APIs, query, diff and budgeted Markdown context renderer |
| ACX-04 | pending | IFC adapter via IfcOpenShell |
| ACX-05 | pending | DXF adapter via ezdxf |
| ACX-06 | pending | Vector/raster PDF and image evidence adapters |
| ACX-07 | pending | Geometry artifact normalization and deterministic previews |
| ACX-08 | pending | Plugin isolation, security limits, optional MCP and signing decision |
| ACX-09 | pending | Cross-platform conformance corpus, packaging and `0.1.0` release |
| ACX-10 | deferred | Consumer integration template; WoodFraming-specific plan remains consumer-owned |

## ACX-00: Specification and repository foundation

Acceptance:

- public contract is application-agnostic;
- package and plugin specs are normative and versioned;
- schemas validate the minimal fixture;
- baseline integration and project checks pass;
- implementation handoff names exactly one next task.

Evidence: repository initial commit and `./scripts/verify.sh`.

## ACX-01: Core scaffold and validator

Scope:

- create a Python 3.12+ `src/aecctx` package and `aecctx` CLI;
- add `validate`, `info`, and version commands;
- load bundled schemas without network access;
- validate directory-form packages and the committed fixture;
- define typed errors and JSON output envelopes;
- establish unit, CLI, and package-data tests.

Non-scope:

- no format adapters;
- no package writer;
- no query/diff/context/MCP;
- no WoodFraming code.

Acceptance:

- `aecctx validate fixtures/minimal-aecctx` succeeds;
- malformed fixture tests fail with stable machine-readable codes;
- CLI stdout is JSON when `--json` is selected and diagnostics use stderr otherwise;
- package build contains schemas;
- `./scripts/verify.sh` passes.

## ACX-02: Deterministic package and opaque ingest

Implement directory/ZIP reading and writing, logical digest, source hashing, artifact inventory, explicit embedding policy, safety limits, and an opaque fallback that registers any unsupported file without claiming interpretation.

Acceptance includes repeated-build logical digest equality, archive traversal/decompression defenses, large-file streaming behavior, and exact capability/loss reporting.

## ACX-03: Neutral records and agent context

Implement record models, stable ordering, read-only query/diff, context profiles, source citations, chunk indexes, and token-estimate reporting. Resolve ACXD-010 without creating a consumer ontology.

## ACX-04: IFC adapter

Use IfcOpenShell behind the plugin contract. Preserve IFC schema, GUID, class, spatial/type/property/material/relationship evidence, placements, representation references, unsupported data, validation diagnostics, and tessellated artifacts without flattening IFC semantics into mesh-only records.

## ACX-05: DXF adapter

Use ezdxf. Preserve versions, units, layouts, layers, blocks/inserts, xrefs, handles, text, dimensions, hatches, supported geometry and unknown tags. Do not infer walls or other domain families from raw CAD primitives.

## ACX-06: PDF and image adapters

Separate vector extraction, raster/OCR/vision evidence, viewport calibration, coordinates, extraction confidence, interpretation confidence, and unsupported hidden geometry. Inference providers remain optional.

## ACX-07: Geometry and previews

Define deterministic SVG/GLB conventions, coordinate metadata, mesh provenance, bounds, level/sheet previews and rendering diagnostics. Geometry sidecars remain subordinate to source evidence.

## ACX-08: Isolation and agent tools

Harden plugin processes and resource policies. Decide signing. Add an optional MCP wrapper over stable library/CLI functions; MCP must not introduce unique semantics.

## ACX-09: Release

Publish conformance fixtures, compatibility policy, installable artifacts, checksums, SBOM, changelog, versioned documentation and release automation. Only verified capabilities may appear in release claims.

## ACX-10: Consumer template

After the neutral core is proven, define a generic consumer adapter template. WoodFraming mapping, staging, UI and canonical commit specifications are authored and accepted in the WoodFraming repository.
