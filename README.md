# AECCTX

AECCTX is an open, application-agnostic specification and planned local-first toolchain for compiling CAD, BIM, drawings, meshes, and related AEC files into deterministic context packages that humans, agents, and downstream applications can inspect without silently losing source evidence.

The project is currently **SPEC-READY**. Implementation has not started.

## Why this exists

AEC formats split information across proprietary files, open schemas, vector drawings, raster documents, geometry, properties, and relationships. Feeding those files directly to an agent is expensive and unreliable; flattening them into a single Markdown file destroys precision and provenance.

AECCTX instead produces a package with:

- immutable source identity and parser provenance;
- extracted evidence with explicit confidence and diagnostics;
- neutral entities and relations without consumer-specific decisions;
- geometry and previews as sidecar artifacts;
- generated, token-budgeted Markdown navigation;
- a mandatory capability and loss report.

## Status and authority

- Format specification: [`docs/specs/aec-context-package-spec.md`](docs/specs/aec-context-package-spec.md)
- Plugin contract: [`docs/specs/aec-context-plugin-contract.md`](docs/specs/aec-context-plugin-contract.md)
- Capability matrix: [`docs/capability-matrix.md`](docs/capability-matrix.md)
- Active implementation sequence: [`docs/implementation-plan.md`](docs/implementation-plan.md)
- Handoff for the implementation task: [`docs/HANDOFF.md`](docs/HANDOFF.md)

Only the first `pending-next` or `in_progress` task in the implementation plan is executable.

## Planned CLI

```bash
aecctx ingest building.ifc --output building.aecctx
aecctx validate building.aecctx
aecctx info building.aecctx --json
aecctx query building.aecctx 'entity.original_class == "IfcWall"'
aecctx context building.aecctx --profile agent --token-budget 40000
aecctx diff revision-a.aecctx revision-b.aecctx
```

These commands are specification targets, not currently implemented behavior.

## Non-goals for v0.1

- replacing IFC, Revit, AutoCAD, or authoring applications;
- claiming lossless support for every proprietary format;
- defining a universal construction ontology;
- allowing an LLM to approve or mutate source truth;
- embedding WoodFraming-specific families or rules in the public format.

## Development

```bash
./scripts/verify.sh
```

`verify.sh` includes the baseline integration gate and expects the baseline package or sibling checkout available to maintainers. Public CI runs `scripts/verify_portable.sh` so external contributors need no private dependency.

AECCTX is licensed under Apache-2.0. See [`LICENSE`](LICENSE).
