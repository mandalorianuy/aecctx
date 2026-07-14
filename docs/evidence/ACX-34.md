# ACX-34 Acceptance Evidence

## 1. Task status, commit and date

- Status: `blocked` — missing human/provider evidence prevents RVT extraction; this is not capability completion.
- Date: 2026-07-14.
- Milestone commit: recorded by the ACX-34 delivery PR.

## 2. Normative coverage

- Post-v0.2 functional debt spec section 17 and shared DoR/DoD.
- `docs/specs/rvt-v02-blocked-profile.md`, including section 10 renewal.
- ACXD-030 and ACXD-043.
- Detailed execution authority: Task 11 in `docs/plans/post-v02-functional-debt-implementation.md`.

## 3. Deliverables and explicit non-scope

Delivered:

- immutable-predecessor-bound `conformance/v0.3/rvt-provider-decision.json` covering both governed reopening routes and every required axis;
- schema and dual-version checker that reject unauthorized route selection, positive claims, scaffolding, restricted artifacts and consumer leakage;
- public v0.3 `unsupported` claim mapped to the unchanged invalid v0.2 anti-claim sentinel and opaque fallback tests;
- portable/spec/package gates for the renewed material.

Not delivered or claimed:

- no RVT adapter, provider descriptor, extraction event, replay, semantic mapping, converted IFC, runtime or credentials;
- no real, proprietary, trial or customer RVT fixture;
- no element/property/relation/view/geometry/unit/coordinate evidence;
- no WoodFraming or consumer mapping.

## 4. Claim table

| Capability | Source/profile/version | Support | Conformance tests |
|---|---|---|---|
| `rvt.external-provider` | no provider; `rvt-no-provider-blocked-v03`; no RVT version | public `unsupported` | `tests/test_rvt_v03.py`; existing opaque fallback tests |

This is an executable anti-claim, not a positive RVT capability.

## 5. Fixtures, origin, license and hashes

- Reused immutable `fixtures/v0.2/rvt/not-a-real-rvt.rvt`: project-authored Apache-2.0 text sentinel, explicitly not an RVT file; SHA-256 `a0e93c6e20f3ee4356fc8f6ecca029d95da723154f7b2f25e49ed7268d2e1a49`.
- Immutable predecessor decision SHA-256: `d7bc7e0b8f14b9c41e4914675fddb967d1e14d934bd33dd0c8decc05e46f4fa8`.
- No `fixtures/v0.3/rvt/` directory exists because a positive directory requires a legally publishable real RVT fixture and accepted provider.

## 6. Commands and results

- RED: `.venv/bin/python -m pytest tests/test_rvt_v03.py -q` failed 4 tests for the absent decision/checker/claim/gate behavior.
- Focused GREEN: `.venv/bin/python -m pytest tests/test_rvt_v03.py tests/test_rvt_blocked_conformance.py tests/test_rvt_blocked_profile.py tests/test_package_data.py -q` passed 48 tests.
- Focused checker/spec: both v0.3 blocked conformance and spec contract passed.
- `./scripts/verify_portable.sh`: 255 focused gate tests and 747 full tests passed with 13 intentional provider/runtime skips; wheel/sdist and every conformance checker passed; final `aecctx portable verify: ok`.
- `./scripts/verify.sh`: repeated the portable result, baseline integration was healthy with zero issues and `baseline-shared-v1`, v0.1/v0.2 release verification passed, and final `aecctx verify: ok`.
- Exact-head GitHub CI and squash-merge evidence are recorded by the delivery closeout.

## 7. Determinism and reproducibility

The v0.3 record binds the immutable v0.2 decision hash. Canonical JSON/schema checks, exact claim mapping and the existing repeated opaque ZIP test are network-free and deterministic. No replay is presented as provider availability.

## 8. Capability, loss and diagnostics

RVT semantic extraction remains `unsupported`; arbitrary bytes retain the existing deterministic opaque fallback. Missing route selection, entitlement, exact version, automation, enforcement, CI, fixture, privacy, billing/retention/jurisdiction and lifecycle evidence stay explicit in the decision axes and blocker codes.

## 9. Dependency, license, security, privacy and platform review

- Autodesk desktop API remains installed with Revit and in-process; no licensed runtime, automation entitlement or admitted native sandbox exists.
- APS Automation remains an account-backed remote service with paid usage; no credentials, consent, retention/deletion, region/jurisdiction or billing authorization exists.
- ODA BimRv remains separately commercial; no module entitlement or redistribution/CI/fixture rights exist.
- Core wheel/sdist remain free of Revit, Autodesk APS, ODA, proprietary runtime and consumer dependencies.

## 10. Residual risks and unsupported cases

Every real RVT version and semantic/geometry capability remains unsupported. A future reopening requires the exact human route selection and complete evidence listed by ACXD-043; provider product availability or portable replay is insufficient.

## 11. WoodFraming boundary proof

All task paths are under `/Users/facundo/desarrollo/aecctx`. Executable-source, generated-output and artifact checks reject `woodframing`, `WFDomain` and `WFImport`; `/Users/facundo/desarrollo/woodframing` was not modified.

## 12. Promotion and exact reopening decision

ACX-34 closes documented `blocked`; `rvt.external-provider` remains public `unsupported`. ACX-35 alone is promoted to `pending-next`.

Reopening requires the human owner to select exactly one route and provide its written entitlement, exact runtime/RVT versions, automation rights, complete enforcement, live CI, real publishable fixtures, privacy/telemetry, billing/retention/jurisdiction and lifecycle evidence before decoder code.
