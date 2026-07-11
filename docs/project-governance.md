# Project Governance

Date: 2026-07-11
Status: Active

## Authorities

Authority is ordered as follows:

1. `AGENTS.md` for repository execution rules.
2. `docs/specs/aec-context-package-spec.md` for the package and neutral record model.
3. `docs/specs/aec-context-plugin-contract.md` for adapter behavior.
4. `docs/decisions/decision-log.md` for accepted and open decisions.
5. `docs/capability-matrix.md` for support claims.
6. `docs/implementation-plan.md` for task sequencing.

Research notes and README examples are informative and cannot override normative specifications.

## Change control

- A format-breaking change requires a decision-log entry, schema update, compatibility statement, migration policy, fixtures, and a version change.
- An adapter cannot claim support beyond the capability matrix and its emitted capability/loss report.
- An application integration cannot add consumer semantics to the neutral package contract.
- Open decisions block only the affected capability; they must not be resolved implicitly in code.

## Release gates

A release requires:

- all required schema and fixture checks passing;
- baseline integration healthy;
- capability claims matched by conformance fixtures;
- security and licensing review for every bundled adapter;
- no executable task skipped in the active implementation plan.

## CI posture

Public GitHub CI runs `scripts/verify_portable.sh`, which validates the public specification, fixture integrity, JSON syntax, and repository diff hygiene without credentials. The full `scripts/verify.sh` additionally resolves the private `codex-agent-baseline` runtime and is required locally before merge and release. The committed baseline offer and integration report remain public materializations; the private baseline repository is not exposed to CI.
