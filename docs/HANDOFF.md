# AECCTX Implementation Handoff

Date: 2026-07-13
Handoff status: `0.3.0-ACX-25-COMPLETE`

## Outcome

AECCTX `0.2.0` is publicly released from immutable tag `v0.2.0`. The post-v0.2 plan governs ACX-24 through ACX-38. ACX-24 and ACX-25 are complete; ACX-26 alone is `in_progress` under ACXD-034. WoodFraming integration remains intentionally deferred and consumer-owned.

## Start here

1. Read `AGENTS.md`.
2. Read the stable package/plugin contracts and `docs/specs/aecctx-capability-expansion-spec.md` completely.
3. Read `docs/decisions/decision-log.md` and do not resolve open items silently.
4. Read `docs/specs/aecctx-post-v02-functional-debt-spec.md` and `docs/plans/post-v02-functional-debt-implementation.md` completely.
5. ACX-01 through ACX-09, ACX-11 through ACX-18 and ACX-20 through ACX-25 are complete; ACX-19 is documented `blocked`; ACX-10 remains deferred. ACX-26 is the only authorized task and is implementing `remote-https-spki-v1`.
6. Follow the definition-of-ready, work breakdown, test matrix, evidence template and promotion protocol in `docs/implementation-plan.md`.
7. Run `./scripts/verify.sh` before handoff.

## Active post-v0.2 plan

- Plan: ACX-24 through ACX-38, dependency-first.
- Completed: ACX-24 live OCI providers and ACX-25 deterministic native-profile rejection/reporting.
- Sole `in_progress`: ACX-26, optional remote/customer-managed provider protocol.
- ACX-27 through ACX-38: `pending`.
- Claim posture: `sandbox.oci-multiarch` is public `partial`; `sandbox.local-enforcement` is public `unsupported`; every later post-v0.2 entry remains a target until its owning milestone closes.
- Package posture: continue reading v0.1/v0.2 and reuse v0.2 shared evidence/extensions. Stop the affected task before any standard-field change until compatibility is governed.
- Execution boundary: ACX-26 alone is executing after explicit continuation; ACX-27 and later remain unauthorized.

## ACX-24 evidence

- Runtime contract: immutable `OCIRuntimeTarget` pairs, exact selection and Docker image ID/OS/architecture preflight with no implicit pull or build.
- Live matrix: six positive executions with equal canonical response/artifact evidence across `linux/arm64` and `linux/amd64`; fourteen exact adversarial outcomes across both architectures.
- Corpus: `conformance/v0.3/provider-multiarch-corpus.json` binds sources, requests, responses, artifacts, descriptors, images, package-lock receipts and live execution summaries.
- Local gates: 221 focused tests; 640 full tests with 10 intentional skips; live matrix, wheel/sdist, baseline and release verification green.
- Remote gate: corrected implementation `3cbf3378dffe52bed270eee7e338bb4fbfd552a5` passed CI run `29286654324` on Ubuntu, macOS and Windows after a contract-error-precedence portability defect was reproduced and fixed.
- Residuals: native macOS/Windows, other architectures/providers, registry publication, automatic image acquisition, remote execution and image signing remain unsupported and owned by later governed tasks.

## ACX-25 evidence

- Contract: immutable deterministic 16-axis `LocalEnforcementReport` values for native Linux, macOS and Windows.
- Functional boundary: all three draft-1 profiles reject with structured details before workspace creation or provider launch; no best-effort fallback exists.
- Corpus/package gate: ten digest-bound adversarial cases plus wheel/sdist scan proving no native broker, restricted decoder binary or new dependency is bundled.
- Local gates: 48 focused tests and 655 full tests with 10 intentional skips; portable artifacts, release verification and baseline integration green.
- Remote gate: candidate `24b63bdef116d7e3bd1ed1d4f980a02a7abc9d13` passed CI run `29289903480` on Ubuntu, macOS and Windows.
- Claim/residual: `sandbox.local-enforcement` is public `unsupported`; native execution remains unsupported and OCI remains the only positive restricted-provider profile.

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
- ACX-12 is complete for its digest-pinned reference runtime; ACX-24 additionally proves exact Tesseract, OCP/OCCT and LibreDWG OCI targets on `linux/arm64` and `linux/amd64`. Native macOS/Windows, other architectures and unreviewed providers remain unsupported.
- ACX-13 IFC claims are partial and limited to `docs/specs/ifc-v02-profile.md`; IFC4.1/4.2/4X3 and unlisted 2D/coordinate profiles remain unclaimed.
- ACX-14 DXF claims are partial and limited to `docs/specs/dxf-v02-profile.md`; unlisted releases/entities, ACIS/proxy/custom interpretation and xref traversal remain unclaimed.
- ACX-15 OCR is experimental and partial only for the exact English Tesseract/replay profile in `docs/specs/inference-v02-profile.md`; vision and hidden geometry remain unsupported.
- ACX-16 mesh claims are partial only for self-contained OBJ/STL/glTF 2.0/GLB 2.0 through exact `trimesh==4.12.2`; manual registration remains manual/derived evidence and cannot establish survey authority.
- ACX-17 STEP/IGES claims are experimental partial only for the exact AP203/AP214/AP242 edition-1 and IGES 5.3 corpus through `org.aecctx.step-iges.ocp@0.2.0`; ACX-24 proves its exact Linux arm64/amd64 target pair. XDE correlation, normalized styles/units/placements, source-exact BREP and other live platforms remain unsupported.
- ACX-18 DWG is experimental partial only for self-contained `AC1015` through `org.aecctx.dwg.libredwg@0.2.0`, exact Linux arm64/amd64 OCI or portable replay. JSON objects are observed decoder evidence; DXF/geometry are converted. Other releases/platforms, xrefs, ACIS/proxy/custom semantics, units/CRS and complete 3D remain unsupported/unknown.
- RVT is public `unsupported`; no provider is selected under ACXD-030 and deterministic v0.1 opaque fallback is anti-claim evidence only.
- ACX-20 signing is public `partial` only for `detached-jws-ed25519-offline-v1`, valid v0.1/v0.2 packages, optional `cryptography>=45,<50` and explicit caller-owned registry/policy inputs. X.509, remote discovery/revocation, timestamps, countersignatures, implicit trust and universal authorization remain unsupported.
- The ACX-21 quality gate reports policy conformance, never engineering or consumer approval.
- ACX-21 is public `partial` only for `aecctx-gate-v1-ids-1.0-simple-v1` on Python 3.12 Linux/macOS/Windows, with optional `ifctester==0.8.5` plus `ifcopenshell==0.8.5`; unlisted combinations and all approval semantics remain unsupported.
- ACX-22 is public `partial` only for the exact optional, local-first `aecctx-inspector-v1` distribution; it remains semantically subordinate to library/CLI/MCP/gate results.

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

## ACX-21 Task 7 evidence

- Governance first: profile draft.7, ACXD-023 and the subordinate plan define canonical result/envelope bytes, provider-neutral JSONL annotations, inert Markdown records, stable CLI/output errors and rollback-capable create-only publication before production implementation.
- RED: `tests/test_gate_cli.py` produced 18 expected failures because the `gate` parser/handler, `GateResult.canonical_bytes()`, projection module and neutral atomic helper did not exist.
- GREEN: `tests/test_gate_*.py tests/test_signing_cli.py tests/test_cli.py` pass 220 tests, covering all four outcome/exit pairs, control failures, IDS/baseline errors, projection parity/mutation, hostile inert messages, exact help, collision rejection, rollback and preserved signing semantics.
- Determinism and safety: `--output` writes the raw canonical `GateResult`; Markdown and `aecctx-ci-annotations-v1` JSONL are derived only from `to_dict()`. Requested outputs are preflighted against every input and each other, staged privately, published create-only and rolled back on current-invocation failure.
- `./scripts/verify.sh` passes with 596 tests, 9 intentional skips, wheel/sdist build, portable/release verification and baseline integration healthy.
- No conformance corpus, capability-matrix promotion or public quality-gate claim was added; those remain governed by Tasks 8-9.

## ACX-21 Task 8 evidence

- RED: `tests/test_gate_conformance.py tests/test_claim_registry.py` produced seven expected failures for the missing checker, corpus, fixture/claim mapping, portable hooks and packaging boundaries.
- GREEN: the focused gate/claim/package suite passes 205 tests; its conformance/claim/package subset passes 24 tests.
- Corpus: all 27 hash-bound offline cases match exact expected results and produce byte-identical canonical bytes across two evaluations, including directory/ZIP equivalence, invalid waiver, malicious JSON/XML, missing optional dependencies and ten unchanged official IDS pairs.
- Packaging and licensing: clean core wheel inspection excludes unconditional IfcTester, IfcOpenShell, Flask and BCF dependencies; sdist includes the checker, generator, corpus, referenced fixtures and unchanged buildingSMART attribution/license files.
- Repository gates: `./scripts/verify_portable.sh` and `./scripts/verify.sh` pass with 604 tests, 9 intentional skips, wheel/sdist build, release verification and healthy baseline integration.
- Claim boundary: `quality-gate.policy-ids` remains `target`, the capability matrix remains public `unsupported`, and Task 9 alone owns acceptance/publication and any promotion.
- WoodFraming, consumer mapping, source mutation, network/LLM requirements and approval/certification semantics were not added.

## ACX-21 Task 9 evidence

- RED: the acceptance transition produced three expected failures while the claim registry and corpus still said `target` and the tests required public state.
- GREEN: the atomic registry/corpus/generator/checker/test transition passes 14 focused claim/conformance tests; the focused gate/claim/package suite passes 205 tests.
- Acceptance matrix: all 27 hash-bound corpus cases are unique, exact and byte-deterministic; clean core and `gate-ids` installs preserve dependency isolation with exact `ifctester==0.8.5` and `ifcopenshell==0.8.5` pins.
- Repository gate: `./scripts/verify.sh` passes with 604 tests, 9 intentional skips, deterministic fixtures, wheel/sdist build, release verification and healthy baseline integration.
- Publication boundary: only `aecctx-gate-v1-ids-1.0-simple-v1` is public `partial` on Python 3.12 Linux/macOS/Windows. Unlisted IDS combinations, approval/certification and consumer mappings remain unsupported.
- The Task 9 acceptance candidate passed [CI run 29264614149](https://github.com/mandalorianuy/aecctx/actions/runs/29264614149); closure `0c78566b832973190358e5fcde44e15506d47666` passed [CI run 29265890899](https://github.com/mandalorianuy/aecctx/actions/runs/29265890899); merge `8515a9675055ed7dcd851a989a2cde9a78fe5744` passed [CI run 29266798432](https://github.com/mandalorianuy/aecctx/actions/runs/29266798432), each on Ubuntu, macOS and Windows.
- `/Users/facundo/desarrollo/woodframing` was not modified.

## ACX-22 acceptance evidence

- RED/GREEN: absent distribution, gate wrapper, skills, install manager, corpus, claim transition and portable hooks were observed failing before their bounded implementations.
- Local: focused closure suite passed 22 tests; full repository gate passed 619 tests with 9 intentional skips, deterministic corpora, wheel/sdist, release and baseline checks.
- Packaging: clean core wheel install and CLI passed without plugin payload; sdist contained the optional distribution; create-only install and exact-inventory uninstall passed in a fresh environment.
- Remote: candidate `dec94a158f120285f802aa7c0b5f87cf9334eef5` passed CI 29269632838, closure `dbaa2957bb75d819f8aef654689d03ee95fbd8ac` passed CI 29270583453 and merge `32959fb72a87d014ab4d45c55dd58225c5281d25` passed CI 29271291135, each on Ubuntu, macOS and Windows.
- Claim: only `aecctx-inspector-v1` is public `partial`; marketplace, universal/third-party host behavior, unique semantics and native/GPL/commercial sandbox approval remain unclaimed.
- `/Users/facundo/desarrollo/woodframing` was not modified.

## ACX-23 release evidence

- Local closure: 625 tests passed with 9 intentional skips; wheel/sdist, 23/23 mapped claims, 12 digest-bound suites, clean core/all-extras install, signing/gate/plugin corpora, checksums, SPDX SBOM, restricted-artifact scan and baseline integration passed.
- Remote: candidate CI `29273482180`, evidence CI `29273977799`, merged-main CI `29274784620` and GNU-tar fix CI `29276001711` passed on Ubuntu, macOS and Windows.
- Release: immutable tag `v0.2.0` targets merge commit `450bc4c14adeabb9b296201e806089354c0a7876`. Initial tag workflow `29275244351` exposed a GNU-tar/pipefail false negative before publication; fix `2c75481e7900a862d3fff9f5a9a091b47671890c` and recovery workflow `29277550208` preserved the tag, rebuilt from it, passed the corrected release gate and published the release.
- Public assets: wheel, sdist, deterministic plugin ZIP, `SHA256SUMS` and SPDX SBOM are available at [AECCTX 0.2.0](https://github.com/mandalorianuy/aecctx/releases/tag/v0.2.0); downloaded checksums pass.
- Residuals remain exact in `docs/capability-matrix.md` and `conformance/v0.2/claims.json`; no unsupported or target profile was promoted.
- `/Users/facundo/desarrollo/woodframing` was not modified.

## Next implementation task

ACX-26 is the sole `in_progress` task in the active post-v0.2 plan because the accepted dependency line places the optional remote/customer-managed provider protocol after local enforcement decisions. ACXD-034 governs its closed HTTPS/SPKI, consent, credential, retry and replay contract. ACX-27 and later remain `pending`.

The repository owner corrected ACX-26 delivery authority to GitHub. The configured `origin` and authenticated `gh` account are admissible; GitHub reports no branch protection or repository rulesets, so zero external approvals are required. ACX-26 still remains `in_progress` and its claim remains `target` until a non-draft PR receives explicit diff/check review, green CI and a verified squash merge. Do not promote ACX-27 before that delivery completes.

## Consumer integration planning entry point

Another task may now begin a WoodFraming-owned integration specification from [`docs/integration/woodframing-boundary.md`](integration/woodframing-boundary.md), using the stable package/query APIs and the IFC/DXF conformance fixtures. It must be authored and accepted in the WoodFraming repository; ACX-10 remains deferred here and no WoodFraming code belongs in AECCTX.
