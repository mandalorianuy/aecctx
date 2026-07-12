# AECCTX Implementation Handoff

Date: 2026-07-11
Handoff status: `0.2.0-EXPANSION-SPEC-READY`

## Outcome

AECCTX `0.1.0` remains implemented and released. The post-v0.1 capability expansion is now specified and sequenced without changing existing release claims. WoodFraming integration remains intentionally deferred.

## Start here

1. Read `AGENTS.md`.
2. Read the stable package/plugin contracts and `docs/specs/aecctx-capability-expansion-spec.md` completely.
3. Read `docs/decisions/decision-log.md` and do not resolve open items silently.
4. ACX-01 through ACX-09 are complete and ACX-10 remains deferred. Execute only ACX-11, currently `pending-next`.
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
- ACX-12 is required before native, GPL, commercial, or network-backed decoder work.
- DWG/RVT remain optional provider capabilities outside the Apache-2.0 core distribution.
- Authenticity remains unsupported until ACXD-018 and ACX-20 are complete.
- The ACX-21 quality gate reports policy conformance, never engineering or consumer approval.
- The ACX-22 Codex plugin remains optional, local-first and semantically subordinate to library/CLI results.

## Explicitly deferred

- WoodFraming mapping and import UX;
- direct DWG and RVT dependencies in the core; optional external-provider work is governed by ACX-18/ACX-19;
- editing or round-trip mutation of source authoring formats;
- a universal AEC ontology;
- public format stabilization at `1.0`.

## Completed implementation milestone

`ACX-01` created the Python package, CLI command surface, offline schema loader, directory package validator, typed diagnostics, and packaging gates. Acceptance evidence is recorded in [`docs/evidence/ACX-01.md`](evidence/ACX-01.md).

## Next implementation task

ACX-11: version the shared observation/inference, coordinate, fidelity, and provider-attestation contracts; resolve ACXD-017; add compatibility fixtures and the claim-to-conformance registry. It MUST NOT implement a format adapter or promote a capability claim.

Its detailed file-level deliverables, eight-step work breakdown, test matrix, non-scope and exit gate are normative in [`docs/implementation-plan.md`](implementation-plan.md). Completion requires `docs/evidence/ACX-11.md` and explicit promotion of ACX-12.

## Consumer integration planning entry point

Another task may now begin a WoodFraming-owned integration specification from [`docs/integration/woodframing-boundary.md`](integration/woodframing-boundary.md), using the stable package/query APIs and the IFC/DXF conformance fixtures. It must be authored and accepted in the WoodFraming repository; ACX-10 remains deferred here and no WoodFraming code belongs in AECCTX.
