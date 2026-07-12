# AECCTX Implementation Handoff

Date: 2026-07-12
Handoff status: `0.2.0-ACX-15-IN-PROGRESS`

## Outcome

AECCTX `0.1.0` remains implemented and released. ACX-11 through ACX-14 completed the shared/provider/IFC/DXF expansion foundations. ACX-15 now adds the experimental opt-in English OCR profile, portable replay and public unsupported hidden-geometry boundary. Vision remains unsupported. WoodFraming integration remains intentionally deferred.

## Start here

1. Read `AGENTS.md`.
2. Read the stable package/plugin contracts and `docs/specs/aecctx-capability-expansion-spec.md` completely.
3. Read `docs/decisions/decision-log.md` and do not resolve open items silently.
4. ACX-01 through ACX-09 and ACX-11 through ACX-14 are complete; ACX-10 remains deferred. ACX-15 remains `in_progress` until portable CI passes; ACX-16 is pending and must not start.
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

ACX-16: qualify mesh coordinates and add explicit, provenance-bearing manual unit calibration and CRS registration under ACXD-021. It must preserve original mesh coordinates, keep declared/detected/manual values separate, require reversible transforms and reject incomplete/conflicted registrations. It MUST NOT begin STEP/IGES, DWG/RVT, signing, quality-gate or consumer work.

Its detailed work breakdown, threat boundary, test matrix and exit gate are normative in [`docs/implementation-plan.md`](implementation-plan.md). Do not begin it without an explicit continuation request.

## Consumer integration planning entry point

Another task may now begin a WoodFraming-owned integration specification from [`docs/integration/woodframing-boundary.md`](integration/woodframing-boundary.md), using the stable package/query APIs and the IFC/DXF conformance fixtures. It must be authored and accepted in the WoodFraming repository; ACX-10 remains deferred here and no WoodFraming code belongs in AECCTX.
