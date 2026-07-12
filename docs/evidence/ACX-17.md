# ACX-17 acceptance evidence

Date: 2026-07-12
Status: completed
Task: bounded STEP/IGES external-provider profiles
Decisions: ACXD-014, ACXD-019 and ACXD-028
Implementation commits: `2aac7ed`, `3463a6f`, `27a9477`, `dd1c1d7`, `c845ce4`

## Authority and claims

The normative authority is `docs/specs/step-iges-v02-profile.md` draft 2. The accepted provider is `org.aecctx.step-iges.ocp@0.2.0`, exact local image ID `sha256:875cbbbc5198ae44e8957e3a90c9a8afd0dc541f01029fb5186a296e3d2a0d47`, Python 3.12, `cadquery-ocp==7.9.3.1.1` and OCCT 7.9.3 under ACX-12 `oci-docker-v1`.

| Claim | Exact scope | Support |
|---|---|---|
| `step-iges.source-structure` | STEP AP203 `CONFIG_CONTROL_DESIGN`, AP214 IS, AP242 edition 1 long form and IGES 5.3 lexical source graphs; direct STEP product/assembly records | experimental `partial` |
| `step-iges.brep-geometry` | OCCT translator-derived ASCII BREP and core-generated deterministic GLB for the exact corpus/runtime | experimental `partial` |

Source entities are observed. BREP is translator-derived and GLB is tessellated/derived. The default and explicit v0.1 adapter path remains byte-identical to opaque ingest.

## Implementation

- An operator-built, digest-pinned, non-root OCI provider owns every OCP/OCCT import; the Apache-2.0 core wheel has no native kernel dependency.
- Bounded STEP and fixed-width IGES scanners preserve raw identifiers/classes/references, complex-instance component order, exact schema/version evidence and reject malformed, unresolved, external-reference or unclaimed profiles with stable diagnostics.
- The provider emits validated source/shape events, OCCT ASCII BREP, canonical triangle JSON, topology/bounds, capability/loss and exact runtime attestation.
- The core validates the mirrored event schema, artifact paths/media/hashes, source references, BREP fidelity and finite indexed mesh before mapping records.
- The v0.2 adapter separates observed source records, neutral product/assembly indexing and translator-derived BREP/GLB. Unknown units/CRS and unsupported profile outcomes are not synthesized.
- CLI auto-probe gives IFC precedence over generic ISO-10303 STEP, supports explicit `step-iges`, and accepts only paired `--provider-replay/--provider-entry` for v0.2. CLI never launches Docker.

## Corpus and determinism

All source fixtures were generated/authored by this project for Apache-2.0 publication. `conformance/v0.2/step-iges-corpus.json` binds four exact requests, responses and artifact sets. Source hashes are:

| Input | SHA-256 |
|---|---|
| `ap203-part.step` | `cc1c9e3cdb0799fd2e602edb533f30051a0ea47db45ed9c0fd84dcd892498c61` |
| `ap214-assembly.step` | `ee5dabdca280453e5afcb57d89952e5cc04d904f2d6bc0683258641745c42375` |
| `ap242-part.step` | `8153a85a2b6b9d2b2958d0dcec56562989cc0e407e65a348f0f3798dd5aa8815` |
| `iges53-part.igs` | `b64f87ee6b4fea34d9d268154550a17593e587f8227670c1a78fc84b51c09321` |

Descriptor SHA-256 is `5938b1af95e0ff8d548b116ec4b7822bd8cd848d1b186de9683f45a092c09ae2`. Portable replay validation reports four valid entries with two artifacts each. Repeated provider events/artifacts and repeated v0.2 ZIP packages are byte-identical for fixed input/config/runtime/time.

## Validation evidence

- Focused STEP/IGES, CLI, opaque and v0.2 compatibility cut: 55 passed, 5 live tests skipped in portable mode.
- Exact live OCI gate `./scripts/verify_step_iges_provider.sh`: 5 passed; inspected image ID matched the reviewed digest.
- `python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues`: healthy, zero issues, bundle `baseline-shared-v1`.
- `./scripts/verify_portable.sh`: 230 passed, 5 live opt-in tests skipped; wheel and sdist built in isolated environments.
- `./scripts/verify.sh`: 230 passed, 5 live opt-in tests skipped; portable packaging and conformance gates passed.

## Security, licensing and residuals

The runtime has no network, telemetry or retention and executes with the ACX-12 read-only/non-root/resource boundary. License and redistribution analysis is in `docs/licenses/step-iges-ocp-provider.md`; threat review is in `docs/security/step-iges-provider-review.md`. The image is operator-built and not distributed by core.

XDE/source correlation, normalized colors/layers/materials, normalized units/conversion scales, resolved placements, per-root tolerance summaries, partial-root recovery, source-exact BREP, repair/healing correctness, other schemas/IGES versions, external/multifile/protected content, other OCP/OCCT versions and live platforms outside the exact Linux-arm64 OCI image remain unsupported. Portable replay does not prove native-runtime availability.

No WoodFraming path, `WFDomain`, `WFImport` or consumer ontology was accessed or modified. ACX-17 is completed and ACX-18 is promoted to `pending-next`; ACX-18 was not executed.
