# ACX-19 Acceptance Evidence

Status: `in_progress` — anti-claim boundary evidence only; ACX-19 is not yet accepted or closed
Date: 2026-07-12

## Governed authority

- Decision: ACXD-019 and ACXD-030 in `docs/decisions/decision-log.md`.
- Normative profile: `docs/specs/rvt-v02-blocked-profile.md`.
- Execution plan: `docs/superpowers/plans/2026-07-12-acx-19-rvt-blocked-boundary.md`.
- Task 1 commit: `8610eec879f80e1a6d519dcc1009fd2615164e1b`.

## Evidence implemented so far

- `conformance/v0.2/rvt-provider-decision.json` records the rejected provider routes, exact blocker axes and reopening requirements.
- `scripts/check_rvt_blocked_conformance.py` rejects provider selection, incomplete axes, unknown blockers, mutable/sensitive values and any RVT claim outside the exact public unsupported boundary.
- `fixtures/v0.2/rvt/not-a-real-rvt.rvt` is a project-authored text sentinel explicitly stating that it is not an Autodesk Revit RVT file. SHA-256: `a0e93c6e20f3ee4356fc8f6ecca029d95da723154f7b2f25e49ed7268d2e1a49`.
- `tests/test_rvt_blocked_profile.py` proves deterministic v0.1 opaque ingest, extension-independent CLI auto detection, explicit unknown detected format and absence of consumer mappings.
- Public claim `rvt.external-provider` is bounded to `unsupported`, `provider_scope = none` and profile `rvt-no-provider-blocked-v1`.

## Task 2 validation

- `.venv/bin/python -m pytest tests/test_rvt_blocked_profile.py tests/test_rvt_blocked_conformance.py tests/test_claim_registry.py -q`: 26 passed.
- `.venv/bin/python scripts/check_rvt_blocked_conformance.py --decision conformance/v0.2/rvt-provider-decision.json --claims conformance/v0.2/claims.json --root .`: `aecctx RVT blocked conformance: ok`.
- `shasum -a 256 fixtures/v0.2/rvt/not-a-real-rvt.rvt`: exact governed hash confirmed.
- `python3 scripts/check_spec_contract.py`: `aecctx spec contract: ok`.
- `.venv/bin/python -m pytest -q`: complete local suite passed with nine expected provider/runtime skips.

## Retained support and impact

RVT semantic extraction remains `unsupported`. Ordinary v0.1 opaque ingest preserves exact bytes, identity, provenance, capability/loss diagnostics and deterministic package identity, but emits no RVT elements, properties, relationships, geometry, units or coordinates.

## Not yet accepted

The following governed work remains pending and prevents ACX-19 closure:

- Task 3 source, wheel/sdist, dependency and portable-gate enforcement;
- Task 4 full `./scripts/verify.sh`, final acceptance evidence, remote CI evidence and task promotion;
- capability-matrix and task-ledger closure as documented `blocked`;
- promotion of ACX-20 to `pending-next`.

This incremental evidence file exists to make the public unsupported claim traceable. It is not evidence of an RVT adapter, provider, version, schema, replay or extraction capability.
