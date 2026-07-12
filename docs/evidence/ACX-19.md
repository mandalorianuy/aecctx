# ACX-19 Acceptance Evidence

## 1. Task status, commits and date

- Status: `blocked` — provider-external constraints prevent RVT extraction; this is not a capability completion.
- Date: 2026-07-12.
- Design/plan commits: `500e384`, `7fc923a`.
- Task 1 decision/schema/checker commit: `8610eec`.
- Task 2 governance and anti-claim commits: `d437ca7`, `db6606d`.
- Task 3 governance and distribution-gate commits: `e0384f1`, `a294f57`.
- Closure commit: `ccc7ab324027bb35368fb5ae6844dbe8b2894b9d`.

## 2. Normative coverage

- Expansion spec section 11, RVT, plus sections 16 security/privacy/licensing and 17 release claim gate.
- `docs/specs/rvt-v02-blocked-profile.md`, sections 1–9.
- ACXD-007, ACXD-014, ACXD-019, ACXD-024 and ACXD-030.
- Detailed execution authority: `docs/superpowers/plans/2026-07-12-acx-19-rvt-blocked-boundary.md`.

## 3. Implemented deliverables and explicit non-scope

Implemented:

- schema-backed, machine-readable no-provider decision with all evaluated candidates, blocker axes and reopening requirements;
- exact public `unsupported` anti-claim with deterministic v0.1 opaque fallback;
- project-authored invalid `.rvt` sentinel proving that a suffix has no semantic detection authority;
- source, dependency, archive-member, wheel and sdist enforcement preventing RVT scaffolding or restricted/consumer dependencies;
- portable pre-test and post-build gates.

Not implemented or claimed:

- no RVT parser, adapter, provider, descriptor, event schema, replay, version or semantic extraction;
- no Revit/APS/ODA credential, runtime, binary, network execution or fixture;
- no element, class, property, relation, geometry, unit or coordinate evidence;
- no authoring mutation, signing, quality-gate, consumer ontology or WoodFraming integration.

## 4. Claim table

| Capability | Source/profile/version | Support | Conformance tests |
|---|---|---|---|
| `rvt.external-provider` | no provider; `rvt-no-provider-blocked-v1`; no RVT version | public `unsupported` | `tests/test_rvt_blocked_profile.py::test_rvt_suffix_uses_deterministic_opaque_fallback`; `tests/test_rvt_blocked_profile.py::test_cli_auto_does_not_promote_rvt_suffix` |
| Opaque source preservation | project-authored invalid sentinel; v0.1 core opaque ingest | `full` identity/validation, other semantic capabilities `opaque` | `tests/test_rvt_blocked_profile.py::test_rvt_suffix_uses_deterministic_opaque_fallback`; `tests/test_rvt_blocked_profile.py::test_opaque_sentinel_output_contains_no_consumer_mapping` |

The first row is an unsupported boundary, not a positive RVT claim. The opaque row describes existing core behavior over arbitrary bytes, not RVT interpretation.

## 5. Fixtures, origin, license and hashes

- `fixtures/v0.2/rvt/not-a-real-rvt.rvt`: project-authored Apache-2.0 text sentinel, explicitly not an Autodesk Revit file; SHA-256 `a0e93c6e20f3ee4356fc8f6ecca029d95da723154f7b2f25e49ed7268d2e1a49`.
- No proprietary, trial, customer, Autodesk, ODA or converted RVT sample is present or used.

## 6. Commands and results

- Focused Task 2 cut: 26 passed.
- Focused Task 3 cut: 45 passed.
- `./scripts/verify_portable.sh`: 282 passed, nine expected opt-in provider/runtime skips; wheel and sdist built; post-build RVT boundary passed; final `aecctx portable verify: ok`.
- Task 1 CI `29206181392`: Ubuntu `86685908487`, macOS `86685908500`, Windows `86685908481`, all passed.
- Task 2 CI `29206921706`: Ubuntu `86687819562`, macOS `86687819565`, Windows `86687819561`, all passed.
- Task 3 CI `29207464228`: Ubuntu `86689259849`, macOS `86689259848`, Windows `86689259845`, all passed.
- Fresh closure baseline check: healthy, zero issues, bundle `baseline-shared-v1`.
- Fresh closure `./scripts/verify.sh`: 282 passed, nine expected skips, wheel/sdist and post-build RVT boundary passed, v0.1 corpus deterministic, release verification passed, final `aecctx verify: ok`.
- Closure CI `29207685331` for `ccc7ab3`: Ubuntu `86689844003`, macOS `86689844005`, Windows `86689844007`, all passed.

## 7. Determinism and reproducibility

Two v0.1 ZIP packages produced from the sentinel with the same timestamp are byte-identical and share the logical digest. Source bytes, size and SHA-256 are exact. CLI `auto` and explicit opaque ingest preserve unknown detected format and never infer RVT semantics. Decision, claim and distribution checks require no network or proprietary runtime.

## 8. Capability, loss and diagnostics

RVT semantic support remains `unsupported`. Opaque ingest reports identity and validation `full`; hierarchy, properties, relationships, text, 2D/3D geometry, materials/styles and georeferencing remain `opaque` with existing `AECCTX_OPAQUE_*` losses. Detected format remains explicit `unknown` with `AECCTX_NO_FORMAT_ADAPTER`. No value is promoted from unknown/unsupported to a plausible default.

## 9. Dependency, license, security, privacy and platform review

Evaluated official routes on 2026-07-12:

- [Autodesk Revit desktop API](https://help.autodesk.com/cloudhelp/2018/ENU/Revit-API/Revit_API_Developers_Guide/Introduction/Getting_Started/Welcome_to_the_Revit_Platform_API/Installation.html): licensed Windows Revit runtime unavailable.
- [Autodesk APS Automation](https://aps.autodesk.com/en/docs/design-automation/v3/developers_guide/overview/) and [business model](https://aps.autodesk.com/blog/aps-business-model-evolution): credentials, billing, egress, source transfer, retention and jurisdiction unapproved.
- [ODA BimRv FAQ](https://www.opendesign.com/faq/bimrv) and [product](https://www.opendesign.com/products/bimrv): separate commercial module entitlement/runtime/redistribution unavailable.
- [Autodesk Revit IFC exporter](https://github.com/Autodesk/revit-ifc): not a standalone parser and still requires Revit/proprietary assemblies.

Core dependency metadata contains none of those runtimes. Wheel/sdist checks reject prohibited dependencies, native binaries, unsafe/symlink/hardlink members, RVT adapter/provider/event-schema paths and every `.rvt` except the exact sentinel. The checker is portable across the three CI operating systems.

## 10. Residual risks and unsupported cases

- Every real RVT version, producer, document/link, category/class, property/type/material, hierarchy/relation, view/level, geometry, unit and coordinate capability remains unsupported.
- A local commercial route still requires written automation/redistribution entitlement, exact runtime/RVT versions, a complete ACX-12 enforcement profile, private provider CI, publishable project-authored fixture rights, security history and lifecycle support.
- APS still requires human approval of credentials, billing, upload consent, storage, retention/jurisdiction, regions, telemetry, timeouts/retries/rate limits and an ACX-12 network-provider profile.
- Offline opaque behavior does not demonstrate decoder availability or semantic correctness.

## 11. WoodFraming boundary proof

All ACX-19 changed paths are within `/Users/facundo/desarrollo/aecctx`. The executable-source and generated-output tests reject `woodframing`, `WFDomain` and `WFImport`. No file under `/Users/facundo/desarrollo/woodframing` was modified, and no consumer dependency or mapping entered AECCTX.

## 12. Promotion and exact reopening decision

ACX-19 closes as documented `blocked`; RVT stays public `unsupported` with opaque fallback. ACX-20 alone is promoted to `pending-next`; ACX-21 through ACX-23 remain `pending` and ACX-10 remains `deferred`.

Reopening requires a human to choose and authorize exactly one route before any implementation-plan or decoder change:

1. licensed local runtime with all entitlement, sandbox, CI, fixture and lifecycle evidence listed in section 10; or
2. APS network provider with all credential, billing, upload, retention/jurisdiction and network-profile approvals listed in section 10.

Absent that decision and evidence, an adapter, descriptor, replay, mock success, proprietary sample or renamed `.rvt` file does not count as progress.
