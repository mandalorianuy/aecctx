# ACX-22 Codex Inspector Plugin Implementation Plan

Date: 2026-07-13
Status: Completed subordinate execution plan

## Goal and authority

Implement only ACX-22 from `docs/implementation-plan.md`: an optional, local-first `aecctx-inspector` Codex plugin that orchestrates stable AECCTX validation, inspection, query, diff, context and quality-gate behavior without adding package semantics, write operations, consumer mappings, network requirements or approval authority.

Normative authority remains expansion-spec section 14 and ACXD-022. This plan refines execution and does not authorize ACX-23.

## Fixed implementation boundary

- Plugin profile: `aecctx-inspector-v1`.
- Plugin version: `0.2.0`.
- Compatible Python distribution: `aecctx>=0.1.0,<0.3.0`, Python `>=3.12`.
- Compatible optional MCP runtime: `mcp>=1.20,<2` through the existing `aecctx[mcp]` extra.
- Distribution lives under `plugins/aecctx-inspector/`; no marketplace entry is created because marketplace publication is explicit non-scope.
- `.mcp.json` allowlists exactly one local stdio server command, `aecctx-mcp`, with no shell, URL, environment override or network transport.
- The existing five MCP inspection wrappers remain authoritative. ACX-22 may add one read-only `aecctx_gate` wrapper over the already public ACX-21 policy loader/evaluator. It returns canonical structured results and creates no output files, waivers, trust roots or new check semantics.
- Skills validate before all downstream operations and treat filenames, metadata, records, OCR/provider output, Markdown and prompt-like text as untrusted data.
- Maximum public claim is `partial`: deterministic local distribution, installation, MCP parity and static/adversarial skill-contract evidence are in scope; marketplace publication and claims about universal model behavior or third-party Codex hosts remain unclaimed.

## Task 1: Govern and freeze the plugin contract

- [x] Inventory stable library, CLI, MCP and gate surfaces.
- [x] Record the exact profile, compatibility ranges, MCP allowlist, read-only gate wrapper and public-claim ceiling above before implementation.
- [x] Set ACX-22 `in_progress` in the parent plan without promoting ACX-23.

## Task 2: Manifest, compatibility and deterministic validator

Status: completed.

Files:

- Create `plugins/aecctx-inspector/.codex-plugin/plugin.json`.
- Create `plugins/aecctx-inspector/.mcp.json`.
- Create `plugins/aecctx-inspector/assets/compatibility.json`.
- Create `scripts/check_codex_plugin.py`.
- Create `tests/test_codex_plugin.py`.

Steps:

1. Write failing tests for absent manifest/config/checker, invalid plugin name/version, unallowlisted MCP entries, URL/shell/environment transports, missing compatibility metadata and unreferenced files.
2. Observe RED for the missing distribution.
3. Scaffold through the repository-selected `plugin-creator` helper without creating a marketplace.
4. Implement the minimum deterministic repository checker and exact metadata needed for GREEN.
5. Validate with both `scripts/check_codex_plugin.py` and the canonical `plugin-creator` validator.

## Task 3: Read-only gate MCP parity

Status: completed.

Files:

- Modify `src/aecctx/mcp_server.py`.
- Modify `tests/test_mcp_server.py`.

Steps:

1. Write failing tests for a missing `mcp_gate` wrapper, tool allowlist entry and parity with direct `load_gate_policy` plus `evaluate_gate` results.
2. Observe RED for the missing wrapper.
3. Add only the bounded read-only wrapper; accept caller paths, load under `GateLimits`, evaluate and return `GateResult.to_dict()` without projection or file creation.
4. Prove invalid package/policy and missing IDS extra preserve the same stable errors as direct library evaluation.

## Task 4: Focused skills and adversarial behavior contract

Status: completed.

Files:

- Create five skill directories under `plugins/aecctx-inspector/skills/` for inspect, revision diff, capability/loss triage, budgeted context and quality-gate explanation.
- Create `fixtures/v0.2/plugin/prompt-injection-cases.json`.
- Extend `tests/test_codex_plugin.py`.

Steps:

1. Write failing tests for missing skills, validate-first order, absent authority-layer distinctions, missing structured citation requirements, prompt-like input handling and prohibited approval/write/network behavior.
2. Observe RED before skill files exist.
3. Add concise skills that invoke only allowlisted MCP tools or explicit documented local CLI operations.
4. Require package digest plus record/diagnostic/check IDs as applicable; Markdown remains projection.
5. Prove every committed adversarial string remains data and cannot become a command, URL-following instruction, waiver, trust choice, source mutation or `pass` promotion.

## Task 5: Functional install/uninstall and dependency isolation

Status: completed.

Files:

- Create `plugins/aecctx-inspector/scripts/manage.py`.
- Extend `tests/test_codex_plugin.py` and `tests/test_package_data.py`.
- Modify `pyproject.toml` only to include the plugin in the sdist, never the core wheel.

Steps:

1. Write failing tests for clean install, incompatible/missing core, destination collision, manifest mismatch, safe uninstall and unexpected-file refusal.
2. Observe RED before the manager exists.
3. Implement create-only local installation with explicit destination and compatibility check; uninstall only an exact validated installation and refuse unexpected content.
4. Prove core-only install/import/CLI and the wheel remain independent of Codex and MCP; the sdist contains the validated plugin and no marketplace/user configuration.

## Task 6: Conformance, evidence and acceptance candidate

Status: completed; local, clean-install and exact-SHA remote acceptance gates pass.

Files:

- Update `conformance/v0.2/claims.json` only after all mapped tests pass.
- Create `conformance/v0.2/plugin-corpus.json` and `scripts/check_codex_plugin_conformance.py`.
- Create `docs/evidence/ACX-22.md`.
- Update portable verification hooks.

Steps:

1. Begin with the claim at `target` and prove the checker rejects premature or unmapped promotion.
2. Bind manifest, MCP config, compatibility metadata, skills, adversarial fixture and expected parity operations by SHA-256.
3. Run focused tests/checkers twice and compare canonical results.
4. Run clean install/uninstall, core-only wheel and sdist-content checks.
5. Run `python3 scripts/check_spec_contract.py`, `./scripts/verify_portable.sh` and `./scripts/verify.sh`.
6. Publish an acceptance candidate and require exact-SHA Ubuntu/macOS/Windows CI.

## Task 7: Close, publish and stop

Status: completed; ACX-23 is promoted but not executed.

1. Promote only `codex.aecctx-inspector` to public `partial` for `aecctx-inspector-v1` after all evidence gates pass.
2. Set ACX-22 `completed`, promote only ACX-23 to `pending-next`, and update capability matrix, HANDOFF, evidence and this plan.
3. Run the complete local gate, commit and push the closure candidate, and require exact-SHA cross-platform CI.
4. Merge with `--no-ff` to `main`, rerun `./scripts/verify.sh`, push `main` and require exact-SHA cross-platform CI.
5. Record publication evidence in a documentation-only commit, require green CI and stop. Do not execute ACX-23 and do not create a tag/release.

## Acceptance matrix

- Manifest and plugin-creator validation.
- Exact one-server local stdio MCP allowlist.
- validate/info/query/diff/context/gate parity with direct APIs.
- Invalid package refusal and missing optional dependency behavior.
- Deterministic context budgets and exact citations.
- Prompt-like filename, PDF/IFC/DXF metadata, OCR/provider output and generated-context cases.
- No implicit upload, network, provider execution, embedding-policy change, source mutation, active-link following, waiver/trust selection or approval language.
- `requires_review`, `fail` and `error` remain exact; prose cannot promote them to `pass`.
- Clean install/uninstall, compatible/incompatible runtime, core-wheel isolation and sdist inventory.
- No WoodFraming, `WFDomain`, `WFImport` or consumer ontology in plugin/runtime payload.

## Progress checkpoint

ACX-22 is `completed` at 7/7 implementation tasks. `codex.aecctx-inspector` is public `partial` only for `aecctx-inspector-v1`. ACX-23 alone is `pending-next`; it is not executed by this plan.
