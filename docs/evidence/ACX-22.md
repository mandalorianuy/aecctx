# ACX-22 Acceptance Evidence — Candidate

## 1. Status and authority

- Status: `in_progress`; local candidate evidence is being assembled and the public claim remains `target`.
- Date: 2026-07-13.
- Authority: expansion-spec section 14, ACXD-022, ACX-22 in the parent implementation plan, and the subordinate ACX-22 execution plan.

## 2. Implemented boundary

The candidate supplies an optional `aecctx-inspector` Codex plugin with a deterministic manifest, one allowlisted local stdio `aecctx-mcp` server, compatibility metadata, five focused read-only skills, safe create-only install/exact-inventory uninstall, and an offline hash-bound conformance corpus. It adds one read-only `aecctx_gate` MCP wrapper over the authoritative ACX-21 evaluator. It adds no package semantics, write operation, provider execution, network requirement, approval authority, trust choice, waiver choice or consumer mapping.

## 3. Candidate claim and conformance mapping

| Capability | Profile | Ceiling | Current state |
|---|---|---|---|
| `codex.aecctx-inspector` | `aecctx-inspector-v1` | `partial` | `target` |

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
- Complete remote exact-SHA gates remain to be recorded before promotion.

## 5. Determinism, security and loss boundaries

The corpus hashes every referenced skill/config/fixture; the checker rejects state or byte drift. Skills validate first, preserve canonical JSON authority, require package/record/diagnostic/check citations, and treat prompt-like source content as inert data. `requires_review`, `fail` and `error` cannot be promoted to `pass` by prose. Inputs remain untrusted and the plugin exposes no shell, URL, environment override, network transport or source mutation.

## 6. Residuals and explicit non-claims

Marketplace publication, universal model behavior, third-party Codex-host behavior and any native/GPL/commercial plugin sandbox are unclaimed. The plugin does not expand the partial/unsupported states of IFC, DXF, OCR/vision, hidden geometry, meshes, STEP/IGES, DWG, RVT, signing or quality-gate capabilities.

## 7. WoodFraming boundary

No ACX-22 executable, manifest, skill, fixture or conformance payload contains WoodFraming, `WFDomain`, `WFImport` or a consumer ontology. `/Users/facundo/desarrollo/woodframing` is not modified.

## 8. Promotion conditions

Promotion to public `partial`, ACX-22 closure and ACX-23 `pending-next` require the complete local gate, exact-SHA Ubuntu/macOS/Windows CI, an atomic claim/evidence/governance update, merged-main verification and final publication evidence. Scaffolding, prose, fixtures, isolated focused tests, a local commit or an unverified push do not count as accepted progress.
