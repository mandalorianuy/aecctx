# AECCTX Implementation Handoff

Date: 2026-07-11
Handoff status: `SPEC-READY`

## Outcome

The repository is ready for a dedicated implementation task. The public contract is application-agnostic, evidence-first, deterministic, local-first, and loss-aware. WoodFraming integration is intentionally deferred.

## Start here

1. Read `AGENTS.md`.
2. Read both normative files under `docs/specs/` completely.
3. Read `docs/decisions/decision-log.md` and do not resolve open items silently.
4. Execute only `ACX-01`, the first `pending-next` task in `docs/implementation-plan.md`.
5. Run `./scripts/verify.sh` before handoff.

## Fixed decisions

- Apache-2.0 core.
- Python 3.12+ reference implementation and CLI.
- Directory and ZIP container forms.
- JSON/JSONL authority with generated Markdown projections.
- No network or LLM required for core conversion.
- Consumer mappings remain outside AECCTX.
- GPL/commercial decoders remain optional process-isolated plugins.

## Explicitly deferred

- WoodFraming mapping and import UX;
- direct DWG and RVT support in the core;
- editing or round-trip mutation of source authoring formats;
- a universal AEC ontology;
- public format stabilization at `1.0`.

## Definition of the first implementation task

`ACX-01` creates the Python package, CLI command surface, schema loader, package validator, and deterministic minimal fixture round trip. It must not implement IFC, DXF, PDF, MCP, geometry conversion, or consumer mapping.
