# ACX-36 Acceptance Evidence

## 1. Task status and date

- Status: `completed`; exact-head GitHub review, CI and squash-merge evidence are recorded by the delivery closeout.
- Date: 2026-07-14.
- Milestone commit: recorded by the ACX-36 delivery PR after acceptance.

## 2. Normative coverage

- Post-v0.2 functional debt spec and shared DoR/DoD.
- `docs/specs/quality-gate-v03-profile.md` and ACXD-045.
- Detailed execution authority: Task 13 in `docs/plans/post-v02-functional-debt-implementation.md`.
- Preserved base contract: `docs/specs/quality-gate-v02-profile.md` and claim `quality-gate.policy-ids`.

## 3. Functional result and claim ceiling

`quality-gate.ids-expanded` is public `partial` only for `aecctx-gate-v1-ids-1.0-expanded-v1`, IDS v1.0.0 final commit `1effec6f419798ce09617416d258a35bdc58320a`, `ifctester==0.8.5` and `ifcopenshell==0.8.5`:

- four exact `partOf` relations: aggregate, group, spatial containment and nesting;
- string pattern/enumeration plus finite numeric inclusive/exclusive bounds;
- required, optional and prohibited specification applicability cardinality;
- unchanged JSON result/outcome/exit/waiver contract with deterministic Markdown and CI projections;
- absent/simple `ids_profile` preserves the v0.2 evaluator; unknown profiles fail schema validation.

This is bounded information-requirement conformance, never source correctness, engineering approval, certification or consumer acceptance.

## 4. TDD and conformance evidence

- RED: the selected official cases exposed absent expanded preflight/worker admission; the selector schema test first rejected `ids_profile`.
- GREEN focused: `uv run python -m pytest tests/test_gate_v03.py -q` passes 54 cases.
- Regression: `uv run python -m pytest tests/test_gate_ids.py tests/test_gate_v03.py tests/test_gate_contract.py tests/test_gate_policy.py -q` passes without changing the v0.2 profile.
- `uv run python fixtures/v0.3/gate/generate_fixtures.py --check` reports deterministic project fixtures, corpus and official provenance.
- `uv run python scripts/check_gate_v03_conformance.py --require-public` validates the 45-case hash-bound corpus, runtime, license partition, claim and provenance.
- `./scripts/verify.sh` passes: 311 focused tests, 811 full tests with 13 intentional provider/runtime skips, deterministic corpora, wheel/sdist artifact checks, portable verification, baseline integration with zero issues and release verification. Exact-head GitHub CI and squash-merge evidence are recorded by the delivery closeout.

## 5. Fixtures, origin and license

- 23 unchanged buildingSMART positive/negative pairs (46 IDS/IFC files) are separately retained under CC BY-ND 4.0 with release, exact commit, upstream path and SHA-256 in `fixtures/v0.3/gate/official/ORIGIN.json`.
- 22 independent Apache-2.0 project cases and one deterministic IFC cover every selected relation, restriction and cardinality outcome under `fixtures/v0.3/gate/project/`.
- `conformance/v0.3/gate-corpus.json` binds all 45 evaluations and their expected pass/fail outcomes.
- IfcTester and IfcOpenShell remain exact optional LGPL-3.0-or-later dependencies and are not bundled into the Apache-2.0 wheel.

## 6. Security and compatibility

All IDS/IFC bytes remain bounded, regular, non-symlink, hash-bound untrusted inputs. DTD/entity/XInclude active XML, unsupported facets/restrictions/cardinalities, dependency drift, worker timeout/crash/malformed/oversized output and missing extras fail closed under existing stable codes. No schema download, URI/bSDD lookup, network, clock, host command, macro, LLM or source-provided command participates.

The v0.2 policy/result/waiver/CLI/projection contracts remain unchanged. The new schema field is optional and closed; absent policies retain their previous canonical bytes and semantics. Core install/import does not require IfcTester or IfcOpenShell.

## 7. Explicit residuals and non-claims

URI/bSDD and remote lookup, geometry and quantity-specific IDS interpretation, unlisted relations/facets/schemas/cardinalities, length/digit/whitespace restrictions, arbitrary types, complete/universal IDS behavior, source correctness, approval, construction readiness and certification remain `unsupported` or unclaimed.

## 8. WoodFraming boundary

All implementation and evidence paths are inside AECCTX. No WoodFraming, `WFDomain`, `WFImport` or consumer mapping is present or modified.

## 9. Promotion

ACX-36 closes `completed` after focused, canonical, package, baseline and exact-head GitHub delivery gates pass. ACX-37 alone becomes `pending-next`; ACX-37 is not executed by this task.
