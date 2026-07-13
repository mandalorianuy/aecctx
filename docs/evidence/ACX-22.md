# ACX-22 Acceptance Evidence — Completed

## 1. Status and authority

- Status: `completed`; local, clean-install and exact-SHA cross-platform acceptance pass.
- Date: 2026-07-13.
- Authority: expansion-spec section 14, ACXD-022, ACX-22 in the parent implementation plan, and the subordinate ACX-22 execution plan.

## 2. Implemented boundary

The candidate supplies an optional `aecctx-inspector` Codex plugin with a deterministic manifest, one allowlisted local stdio `aecctx-mcp` server, compatibility metadata, five focused read-only skills, safe create-only install/exact-inventory uninstall, and an offline hash-bound conformance corpus. It adds one read-only `aecctx_gate` MCP wrapper over the authoritative ACX-21 evaluator. It adds no package semantics, write operation, provider execution, network requirement, approval authority, trust choice, waiver choice or consumer mapping.

## 3. Candidate claim and conformance mapping

| Capability | Profile | Ceiling | Current state |
|---|---|---|---|
| `codex.aecctx-inspector` | `aecctx-inspector-v1` | `partial` | `public partial` |

The corpus binds ten distribution/adversarial artifacts by SHA-256 and maps six distinct read-only operations: validate, info, query, diff, budgeted context and quality gate. Five adversarial surfaces cover filename, PDF text, IFC/DXF metadata, OCR/provider output and generated context.

## 4. Validation evidence

- TDD RED covered absent distribution/checker/corpus, manifest and MCP drift, missing skills and fixture, missing manager, missing sdist payload, absent gate wrapper and missing portable hooks.
- Focused plugin, conformance, MCP and package tests pass.
- Repository and canonical plugin validators pass.
- Clean core-wheel installation reports `aecctx 0.1.0`; the wheel contains no plugin payload and makes MCP optional.
- The sdist contains the validated plugin manifest and manager.
- Plugin installation and exact-inventory uninstall pass in a fresh virtual environment.
- Focused gate/package subset: 206 tests passed.
- Full repository suite: 619 tests passed, 9 intentional skips; portable packaging, release and baseline integration gates passed.
- Candidate `dec94a158f120285f802aa7c0b5f87cf9334eef5` passed [CI run 29269632838](https://github.com/mandalorianuy/aecctx/actions/runs/29269632838) on Ubuntu, macOS and Windows.

## 5. Determinism, security and loss boundaries

The corpus hashes every referenced skill/config/fixture; the checker rejects state or byte drift. Skills validate first, preserve canonical JSON authority, require package/record/diagnostic/check citations, and treat prompt-like source content as inert data. `requires_review`, `fail` and `error` cannot be promoted to `pass` by prose. Inputs remain untrusted and the plugin exposes no shell, URL, environment override, network transport or source mutation.

## 6. Residuals and explicit non-claims

Marketplace publication, universal model behavior, third-party Codex-host behavior and any native/GPL/commercial plugin sandbox are unclaimed. The plugin does not expand the partial/unsupported states of IFC, DXF, OCR/vision, hidden geometry, meshes, STEP/IGES, DWG, RVT, signing or quality-gate capabilities.

## 7. WoodFraming boundary

No ACX-22 executable, manifest, skill, fixture or conformance payload contains WoodFraming, `WFDomain`, `WFImport` or a consumer ontology. `/Users/facundo/desarrollo/woodframing` is not modified.

## 8. Promotion conditions

The complete local and candidate exact-SHA gates passed, enabling the atomic public-partial transition. Candidate `dec94a158f120285f802aa7c0b5f87cf9334eef5` passed [CI 29269632838](https://github.com/mandalorianuy/aecctx/actions/runs/29269632838); closure `dbaa2957bb75d819f8aef654689d03ee95fbd8ac` passed [CI 29270583453](https://github.com/mandalorianuy/aecctx/actions/runs/29270583453); merge `32959fb72a87d014ab4d45c55dd58225c5281d25` passed a fresh local `./scripts/verify.sh` and [CI 29271291135](https://github.com/mandalorianuy/aecctx/actions/runs/29271291135). Each remote gate was green on Ubuntu, macOS and Windows. Scaffolding, prose, fixtures, isolated focused tests, a local commit or an unverified push do not count as accepted progress.
