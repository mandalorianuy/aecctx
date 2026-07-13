# ACX-21 Acceptance Evidence — Implementation Candidate

## 1. Task status, commits and date

- Status: `in_progress`; Tasks 1-8 form an implementation candidate. Task 9 acceptance and public claim promotion remain pending.
- Date: 2026-07-13.
- Task 8 implementation commit/merge identify the candidate only; Task 9 owns acceptance, exact-SHA publication evidence and any claim promotion.

## 2. Normative coverage

- `docs/specs/quality-gate-v02-profile.md`, sections 1-16, under ACXD-021 and ACXD-023.
- ACX-21 in `docs/implementation-plan.md` and Tasks 1-9 in `docs/plans/acx-21-implementation.md`.
- Canonical JSON remains authority; Markdown and `aecctx-ci-annotations-v1` are derived projections only.

## 3. Implemented deliverables and explicit non-scope

The candidate contains closed schemas/models, strict bounded policy parsing, deterministic checks/waivers/outcomes, validated baseline diff, bounded IDS 1.0 evaluation, CLI/projections and a hash-bound offline conformance corpus. It does not implement workflow approval, regulatory certification, construction readiness, consumer canonical acceptance, source mutation, network/LLM evaluation or WoodFraming mapping.

## 4. Claim table

| Candidate capability | Profile | Candidate ceiling | Current public state |
|---|---|---|---|
| `quality-gate.policy-ids` | `aecctx-gate-v1-ids-1.0-simple-v1` | bounded `partial` only after Task 9 acceptance | `target` / public `unsupported` |

The candidate ceiling covers core policy checks and only the selected IDS v1.0 simple-value cases. It is not a support promotion.

## 5. Fixtures, origin, license and hashes

- `conformance/v0.2/gate-corpus.json` binds every configured package, policy, baseline, IDS and IFC path to SHA-256.
- Project-authored package/policy/adversarial fixtures are Apache-2.0 and regenerate byte-for-byte through `fixtures/v0.2/gate/generate_fixtures.py --check`.
- Ten selected buildingSMART IDS inputs are unchanged from v1.0.0 commit `1effec6f419798ce09617416d258a35bdc58320a`, remain under CC-BY-ND-4.0 and are separated from the Apache-2.0 generated harness.

## 6. Commands and local results

Task 8 local evidence:

- initial RED: seven expected failures for the missing checker, corpus, fixture/claim mapping, portable hooks and packaging boundaries;
- deterministic fixture regeneration: `aecctx gate fixtures: deterministic`;
- corpus replay: 27/27 cases matched exact expected results and produced byte-identical canonical bytes across two evaluations;
- focused gate/claim/package suite: 205 tests passed;
- conformance/claim/package subset: 24 tests passed;
- portable repository gate: 604 tests passed, 9 intentional skips; wheel/sdist and release checks passed;
- full repository gate: 604 tests passed, 9 intentional skips; portable/release verification and baseline integration were healthy;
- spec contract: `aecctx spec contract: ok`.

Commands:

```text
python -m pytest tests/test_gate_*.py tests/test_claim_registry.py tests/test_package_data.py
python scripts/check_gate_conformance.py
python scripts/check_spec_contract.py
./scripts/verify_portable.sh
./scripts/verify.sh
```

## 7. Determinism and reproducibility

Every corpus case evaluates twice and requires byte-identical canonical results. The generator checks deterministic package ZIPs, policies and corpus bytes. Policy evaluation has no implicit clock, random identifier, network or host path authority.

## 8. Capability, loss and diagnostics

The corpus covers pass/fail/review/error, equivalent directory/ZIP candidates, all five explicit non-known value states, capability/loss/diagnostic budgets, active/expired/invalid waiver behavior, semantic baseline regression, malformed duplicate-key JSON, active XML, project IDS positive/negative cases, missing optional dependencies and all ten selected official IDS positive/negative inputs. Outcomes retain exact check IDs, finding codes and diagnostic codes.

## 9. Dependency, license, security, privacy and platform review

- Core metadata has no unconditional IfcTester, IfcOpenShell, Flask or BCF client dependency.
- IDS remains optional at exactly `ifctester==0.8.5` plus `ifcopenshell==0.8.5`; selected upstream fixtures retain their original license.
- Inputs are hash-bound, path-safe and offline; hostile JSON/XML is inert and no source text, host path or traceback enters stable diagnostics.
- Portable CI is required on Python 3.12 Linux, macOS and Windows before Task 9 promotion.

## 10. Residual risks and unsupported cases

Unlisted IDS versions, schemas, facets, restrictions and cardinality combinations remain unsupported. `partOf`, URI/bSDD lookup, geometry/quantity interpretations, remote validation, approval/certification semantics and provider-native workflow commands remain out of scope. A passing gate is only conformance to caller-supplied policy and evidence.

## 11. WoodFraming boundary proof

Task 8 paths are confined to AECCTX fixtures, corpus, checker, tests, packaging documentation and governance. The executable/distribution boundary contains no `woodframing`, `WFDomain`, `WFImport`, consumer ontology or mapping. `/Users/facundo/desarrollo/woodframing` is not modified.

## 12. Promotion and publication conditions

Task 9 must run the complete local/clean-install matrix, audit every mapped profile combination, prove non-claims, require exact-SHA Ubuntu/macOS/Windows CI, and only then may change the claim from `target` to public `partial`. Until then the capability matrix remains `unsupported`; fixtures, docs, a green happy path or Task 8 merge alone do not count as public support.
