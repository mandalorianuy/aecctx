# AECCTX Implementation Handoff

Date: 2026-07-13
Handoff status: `0.2.0-ACX-21-TASK-06`

## Outcome

AECCTX `0.1.0` remains implemented and released. ACX-11 through ACX-18 include the shared/provider foundation and bounded IFC/DXF/OCR/mesh/STEP/IGES/DWG profiles. ACX-19 is documented `blocked`. ACX-20 is completed with optional detached Ed25519 signing and explicit caller-owned offline registry/policy evaluation; its public claim is bounded `partial`. ACX-21 is `in_progress`: Tasks 1-6 provide closed policy/check/waiver/result schemas, strict bounded policy parsing, exact-finding waiver lifecycle, authoritative package checks, semantic baseline regression evaluation and bounded IDS 1.0 simple-value evaluation through an optional fixed worker. CLI, projections, corpus and a public quality-gate claim remain unimplemented. WoodFraming integration remains intentionally deferred.

## Start here

1. Read `AGENTS.md`.
2. Read the stable package/plugin contracts and `docs/specs/aecctx-capability-expansion-spec.md` completely.
3. Read `docs/decisions/decision-log.md` and do not resolve open items silently.
4. ACX-01 through ACX-09, ACX-11 through ACX-18 and ACX-20 are complete; ACX-19 is documented `blocked`; ACX-10 remains deferred. Execute only ACX-21, currently `in_progress`.
5. Follow the definition-of-ready, work breakdown, test matrix, evidence template and promotion protocol in `docs/implementation-plan.md`.
6. Run `./scripts/verify.sh` before handoff.

## Fixed decisions

- Apache-2.0 core.
- Python 3.12+ reference implementation and CLI.
- Directory and ZIP container forms.
- JSON/JSONL authority with generated Markdown projections.
- No network or LLM required for core conversion.
- Consumer mappings remain outside AECCTX.
- GPL/commercial decoders remain optional process-isolated plugins.

## Expansion invariants

- Targets do not change the v0.1 claim registry until conformance evidence exists.
- Hidden/unobserved geometry remains unsupported as source evidence; reconstruction can only be an inference hypothesis.
- Manual mesh calibration augments and never rewrites source coordinates.
- ACX-12 is complete only for `oci-docker-v1` on `linux-container` with the digest-pinned reference runtime; native Linux/macOS and Windows profiles remain unsupported under ACXB-001.
- ACX-13 IFC claims are partial and limited to `docs/specs/ifc-v02-profile.md`; IFC4.1/4.2/4X3 and unlisted 2D/coordinate profiles remain unclaimed.
- ACX-14 DXF claims are partial and limited to `docs/specs/dxf-v02-profile.md`; unlisted releases/entities, ACIS/proxy/custom interpretation and xref traversal remain unclaimed.
- ACX-15 OCR is experimental and partial only for the exact English Tesseract/replay profile in `docs/specs/inference-v02-profile.md`; vision and hidden geometry remain unsupported.
- ACX-16 mesh claims are partial only for self-contained OBJ/STL/glTF 2.0/GLB 2.0 through exact `trimesh==4.12.2`; manual registration remains manual/derived evidence and cannot establish survey authority.
- ACX-17 STEP/IGES claims are experimental partial only for the exact AP203/AP214/AP242 edition-1 and IGES 5.3 corpus through `org.aecctx.step-iges.ocp@0.2.0`; XDE correlation, normalized styles/units/placements, source-exact BREP and other live platforms remain unsupported.
- ACX-18 DWG is experimental partial only for self-contained `AC1015` through `org.aecctx.dwg.libredwg@0.2.0`, exact Linux-arm64 OCI or portable replay. JSON objects are observed decoder evidence; DXF/geometry are converted. Other releases/platforms, xrefs, ACIS/proxy/custom semantics, units/CRS and complete 3D remain unsupported/unknown.
- RVT is public `unsupported`; no provider is selected under ACXD-030 and deterministic v0.1 opaque fallback is anti-claim evidence only.
- ACX-20 signing is public `partial` only for `detached-jws-ed25519-offline-v1`, valid v0.1/v0.2 packages, optional `cryptography>=45,<50` and explicit caller-owned registry/policy inputs. X.509, remote discovery/revocation, timestamps, countersignatures, implicit trust and universal authorization remain unsupported.
- The ACX-21 quality gate reports policy conformance, never engineering or consumer approval.
- ACXD-023 selects `aecctx-gate-v1`, exact-finding waivers, deterministic outcomes/exits and an optional bounded IDS v1.0 subset through `ifctester==0.8.5` plus `ifcopenshell==0.8.5`; the capability remains public `unsupported` until implementation evidence closes ACX-21.
- The ACX-22 Codex plugin remains optional, local-first and semantically subordinate to library/CLI results.

## Explicitly deferred

- WoodFraming mapping and import UX;
- direct DWG and RVT dependencies in the core; DWG remains external-only and RVT is blocked under ACX-19/ACXD-030;
- editing or round-trip mutation of source authoring formats;
- a universal AEC ontology;
- public format stabilization at `1.0`.

## Completed implementation milestone

`ACX-01` created the Python package, CLI command surface, offline schema loader, directory package validator, typed diagnostics, and packaging gates. Acceptance evidence is recorded in [`docs/evidence/ACX-01.md`](evidence/ACX-01.md).

## ACX-21 Task 1 evidence

- RED: the contract/package-data test command failed during collection with `ModuleNotFoundError: No module named 'aecctx.gate'` before implementation.
- GREEN: `tests/test_gate_contract.py` plus `tests/test_package_data.py` pass with 27 tests.
- All eight public/packaged schema files pass `python -m json.tool`; each mirror passes byte comparison against its normative repository copy.
- `./scripts/verify.sh` passes with 430 tests, 9 intentional skips, wheel/sdist build, portable verification, release verification and baseline integration healthy.
- No dependency, fixture, CLI command, evaluator or capability claim changed.

## ACX-21 Task 2 evidence

- Governance first: profile draft.2 and ACXD-023 define v1 hard maxima, JSON depth counting, exact declared waiver result IDs and stable loader error codes before parser implementation.
- RED: `tests/test_gate_policy.py tests/test_gate_contract.py` failed during collection because `canonical_gate_json` and the Task 2 facade did not exist.
- GREEN: `tests/test_gate_policy.py tests/test_gate_contract.py tests/test_package_data.py` pass with 63 tests, including canonical digest, malicious/deep JSON, exact SemVer, schema/semantic failures, caller-reduced limits, symlink/non-regular input and waiver-target contract coverage.
- Determinism: the narrow suite runs twice and asserts the same canonical bytes and golden SHA-256 independent of object key order/whitespace while preserving array order.
- `./scripts/verify.sh` passes with 466 tests, 9 intentional skips, wheel/sdist build, portable/release verification and baseline integration healthy.
- No new dependency, fixture, CLI command, evaluator, finding aggregation or capability claim was added.

## ACX-21 Task 3 evidence

- Governance first: profile draft.3 and ACXD-023 define finding dispositions, waiver-ID invariants, per-check fingerprint uniqueness, separately ordered lifecycle diagnostics and order-independent batch application of exact waivers plus active-mismatch review floors before the final implementation.
- RED: the initial Task 3 tests failed during collection because the evaluator facade did not exist; focused follow-up regressions then failed for duplicate waiver IDs, schema/model disposition binding and exact-plus-mismatch order dependence before their production corrections.
- GREEN: `tests/test_gate_checks.py tests/test_gate_contract.py tests/test_package_data.py` pass with 60 tests covering canonical NFC fingerprints, all aggregate outcome/exit levels, exact/expired/not-yet-valid/mismatched waivers, mixed findings, unsafe control state, public/packaged schema mirrors and deterministic ordering.
- Determinism: reversing check and waiver order yields identical ordered checks/diagnostics; exact mutation and mismatch review floors are computed against the original finding set and applied once.
- `./scripts/verify.sh` passes with 497 tests, 9 intentional skips, wheel/sdist build, portable/release verification and baseline integration healthy.
- No dependency, fixture, candidate package evaluator, package-check dispatch, CLI command, result projection, corpus or capability claim was added.

## ACX-21 Task 4 evidence

- Governance first: profile draft.4 and ACXD-023 define nullable identity only for invalid-candidate errors, a revalidated private snapshot, fixed validation/integrity partitioning, exact loss/value/diagnostic semantics, bounded overflow errors and fail-closed later-task checks before implementation.
- RED: `tests/test_gate_checks.py tests/test_gate_contract.py` failed during collection with `ImportError: cannot import name 'evaluate_gate' from 'aecctx.gate'` before the evaluator facade existed.
- GREEN: the focused gate/policy/contract/validation/record suite passes 127 tests, covering invalid hash/digest/schema, symlink rejection, capability ordering/missing keys, loss evidence/counts, all five non-known states plus allow/review/fail, closed field paths, diagnostic severity/code budgets, later-task fail-closed behavior and finding/result limits.
- Determinism and safety: equivalent directory/ZIP candidates produce byte-identical canonical result JSON; valid evidence is read only from a copied and revalidated temporary snapshot, and invalid packages never reach `RecordStore` or receive invented identity.
- `./scripts/verify.sh` passes with 525 tests, 9 intentional skips, wheel/sdist build, portable/release verification and baseline integration healthy.
- No dependency, fixture, baseline diff, IDS worker, CLI command, result projection, corpus or capability claim was added.

## ACX-21 Task 5 evidence

- Governance first: profile draft.5 and ACXD-023 define the fixed baseline system check, independent baseline snapshots, nine exact semantic-diff categories, authoritative artifact boundaries, capability improvement/regression semantics, stable error codes and role-qualified baseline/candidate evidence before the final implementation.
- RED: `tests/test_gate_diff.py tests/test_query_diff_context.py` failed during collection with `ModuleNotFoundError: No module named 'aecctx.gate.diff_checks'` before the diff-check module existed.
- GREEN: `tests/test_gate_diff.py tests/test_query_diff_context.py tests/test_v02_compatibility.py` pass with 41 tests; the expanded gate/policy/contract/diff suite passes with 153 tests.
- Determinism and authority: every supplied baseline is copied and revalidated independently; all nine governed categories map exact allow/review/fail actions, capability upgrades/additions remain visible non-regressions, and Markdown plus non-authoritative artifacts do not create semantic findings.
- `./scripts/verify.sh` passes with 550 tests, 9 intentional skips, wheel/sdist build, portable/release verification and baseline integration healthy.
- No dependency, fixture, IDS worker, CLI command, result projection, corpus or capability claim was added.

## ACX-21 Task 6 evidence

- Governance first: profile draft.6, ACXD-023 and the subordinate plan define IDS v1.0 provenance/version binding, inert schema-location handling, exact selected cases, hard structural/entity limits and stable input/worker/finding codes before the final implementation.
- RED: `tests/test_gate_ids.py` failed during collection with `ModuleNotFoundError: No module named 'aecctx.gate.ids'` before the evaluator/worker existed.
- GREEN: `tests/test_gate_ids.py` passes 28 tests; the expanded gate/policy/contract/diff/package/compatibility suite passes 182 tests. All ten selected official positive/negative pairs and the project-authored entity/attribute/classification/property/material cases match their governed outcomes.
- Safety and determinism: IDS/IFC files are bounded regular non-symlink inputs bound to exact policy/source hashes; active XML, unsupported namespace/facets/restrictions, version/dependency drift and bounded worker timeout/crash/malformed/overflow paths have stable outcomes. The worker command is fixed, shell-free, isolated with `-I`, content-addressed snapshots and bounded canonical JSON.
- Packaging boundary: a clean `aecctx-0.1.0` wheel installs and runs core IDS fail-closed behavior without IfcTester, IfcOpenShell, Flask or BCF client. The optional test/IDS environment verifies exact `ifctester==0.8.5` and `ifcopenshell==0.8.5` plus IfcTester LGPL metadata.
- The full repository gate result is recorded by the Task 6 merge commit. No CLI, projection, conformance corpus or public capability claim was added.

## Next implementation task

ACX-21 Task 7: implement the gate CLI, canonical output and derived Markdown/CI projections exactly as specified in [`docs/plans/acx-21-implementation.md`](plans/acx-21-implementation.md). Begin with failing parser/exit/parity/safe-output tests and stop at that task's checkpoint.

The normative behavior remains fixed in [`docs/specs/quality-gate-v02-profile.md`](specs/quality-gate-v02-profile.md) and ACXD-023. Task 6 added no CLI, projection, corpus or public capability claim. Do not execute ACX-21 Task 7 until a new continuation request. Do not execute ACX-22 until ACX-21 fully closes and promotes it.

## Consumer integration planning entry point

Another task may now begin a WoodFraming-owned integration specification from [`docs/integration/woodframing-boundary.md`](integration/woodframing-boundary.md), using the stable package/query APIs and the IFC/DXF conformance fixtures. It must be authored and accepted in the WoodFraming repository; ACX-10 remains deferred here and no WoodFraming code belongs in AECCTX.
