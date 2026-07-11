<!-- BEGIN BASELINE META-AGENT MANAGED BLOCK -->
## Baseline Meta-Agent Integration

This repository consumes `codex-agent-baseline` as the source of truth for the shared shell contract and shared contract governance.

Rules:
- Keep the baseline shell contract baseline-owned; extend through the specialization overlay only.
- Overlay location: `.agent_baseline/manifests/specialization_overlay.toml`.
- Do not fork baseline shared contracts in place inside this repo.
- Keep `contract_bundle_id = "baseline-shared-v1"` pinned unless a reviewed bundle upgrade is approved.
- Required check before merge: `python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues`.
<!-- END BASELINE META-AGENT MANAGED BLOCK -->

# AECCTX Repository Instructions

## Product boundary

- AECCTX is an application-agnostic compiler and package specification for converting AEC source files into deterministic, evidence-preserving context packages.
- It MUST NOT depend on WoodFraming, `WFDomain`, or any consumer ontology.
- `docs/specs/aec-context-package-spec.md` is the normative format authority.
- `docs/specs/aec-context-plugin-contract.md` is the normative extractor/plugin authority.
- `docs/specs/aecctx-capability-expansion-spec.md` governs post-v0.1 capability targets without promoting them to release claims.
- `docs/decisions/decision-log.md` records accepted and open design decisions. Do not silently resolve an open decision in code.
- `docs/implementation-plan.md` is the active sequencing authority. Execute only its first `pending-next` or `in_progress` task.

## Engineering rules

- Preserve extraction evidence separately from interpretation and consumer mapping.
- Markdown is a generated context projection, never the sole authoritative representation of geometry, identity, provenance, or diagnostics.
- Unknown, unsupported, conflicted, explicit-null, and not-applicable states must remain explicit; never synthesize plausible defaults.
- Every adapter must publish a machine-readable capability and loss report.
- Treat input files as untrusted data. Do not execute embedded scripts, macros, active links, or source-provided commands.
- The core must remain usable without network access or an LLM.
- GPL or commercial decoders belong behind process/plugin boundaries and must not be linked into the Apache-2.0 core without a reviewed licensing decision.

## Validation

- Run `./scripts/verify.sh` before claiming repo-level completion.
- Required baseline check: `python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues`.
- Spec or schema changes must update fixtures and the decision log or implementation plan when they change behavior or sequencing.

## Integration boundary

- Consumer-specific mappings live outside the neutral core. WoodFraming integration is deferred and governed by `docs/integration/woodframing-boundary.md`.
- A consumer may map AECCTX evidence into its own staging/canonical model, but may not reinterpret generated Markdown as higher-authority evidence.
