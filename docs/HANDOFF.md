# AECCTX Implementation Handoff

Date: 2026-07-12
Handoff status: `0.2.0-ACX-20-PLAN-REVIEW`

## Outcome

AECCTX `0.1.0` remains implemented and released. ACX-11 through ACX-18 include the shared/provider foundation and bounded IFC/DXF/OCR/mesh/STEP/IGES/DWG profiles. ACX-19 is documented `blocked`. ACX-20 is `in_progress`: ACXD-018 accepts the amended detached JWS/Ed25519 offline signing design and `docs/plans/acx-20-implementation.md` defines the subordinate TDD cut. Implementation and the public authenticity claim remain pending explicit plan approval and conformance. WoodFraming integration remains intentionally deferred.

## Start here

1. Read `AGENTS.md`.
2. Read the stable package/plugin contracts and `docs/specs/aecctx-capability-expansion-spec.md` completely.
3. Read `docs/decisions/decision-log.md` and do not resolve open items silently.
4. ACX-01 through ACX-09 and ACX-11 through ACX-18 are complete; ACX-19 is documented `blocked`; ACX-10 remains deferred. Execute only ACX-20, currently `in_progress`.
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
- ACXD-018 accepts `docs/specs/signing-v1-profile.md`; authenticity remains unsupported until ACX-20 implementation and conformance complete.
- The ACX-21 quality gate reports policy conformance, never engineering or consumer approval.
- The ACX-22 Codex plugin remains optional, local-first and semantically subordinate to library/CLI results.

## Explicitly deferred

- WoodFraming mapping and import UX;
- direct DWG and RVT dependencies in the core; DWG remains external-only and RVT is blocked under ACX-19/ACXD-030;
- editing or round-trip mutation of source authoring formats;
- a universal AEC ontology;
- public format stabilization at `1.0`.

## Completed implementation milestone

`ACX-01` created the Python package, CLI command surface, offline schema loader, directory package validator, typed diagnostics, and packaging gates. Acceptance evidence is recorded in [`docs/evidence/ACX-01.md`](evidence/ACX-01.md).

## Next implementation task

ACX-20: review the subordinate [`docs/plans/acx-20-implementation.md`](plans/acx-20-implementation.md). After explicit approval, execute only its ACX-20 TDD cuts. The implementation MUST distinguish integrity, signature validity, signer identity, key lifecycle, trust and authorization, and MUST NOT begin quality-gate, plugin or consumer work.

Its work breakdown, test matrix and exit gate are normative in [`docs/implementation-plan.md`](implementation-plan.md). The next authorized action is implementation-plan review, not implementation. ACX-19 blocked evidence is in [`docs/evidence/ACX-19.md`](evidence/ACX-19.md).

## Consumer integration planning entry point

Another task may now begin a WoodFraming-owned integration specification from [`docs/integration/woodframing-boundary.md`](integration/woodframing-boundary.md), using the stable package/query APIs and the IFC/DXF conformance fixtures. It must be authored and accepted in the WoodFraming repository; ACX-10 remains deferred here and no WoodFraming code belongs in AECCTX.
