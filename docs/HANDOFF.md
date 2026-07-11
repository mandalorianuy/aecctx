# AECCTX Implementation Handoff

Date: 2026-07-11
Handoff status: `ACX-01-COMPLETE`

## Outcome

The repository is ready for a dedicated implementation task. The public contract is application-agnostic, evidence-first, deterministic, local-first, and loss-aware. WoodFraming integration is intentionally deferred.

## Start here

1. Read `AGENTS.md`.
2. Read both normative files under `docs/specs/` completely.
3. Read `docs/decisions/decision-log.md` and do not resolve open items silently.
4. Execute only `ACX-02`, the first `pending-next` task in `docs/implementation-plan.md`.
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

## Completed implementation milestone

`ACX-01` created the Python package, CLI command surface, offline schema loader, directory package validator, typed diagnostics, and packaging gates. Acceptance evidence is recorded in [`docs/evidence/ACX-01.md`](evidence/ACX-01.md).

## Next implementation task

`ACX-02` owns deterministic directory/ZIP reading and writing, logical digests, source hashing, embedding policy, safety limits, and opaque fallback ingest. It must not implement neutral query/diff/context, format-specific adapters, MCP, geometry conversion, or consumer mapping.
