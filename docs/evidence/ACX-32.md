# ACX-32 Acceptance Evidence

Status: acceptance complete locally; PR review, exact-head CI and squash merge are the immutable delivery record
Decision: ACXD-041
Profile: `step-iges-xde-recovery-v03`

## Acceptance mapping

- `step-iges.xde-structure`: exact OCP/OCCT XDE names, assembly/component labels, colors, layers, physical materials, millimetre unit declarations, placements and exact unique-name source correlation for the bounded AP203/AP214/AP242 edition-1 and IGES 5.3 profiles.
- `step-iges.partial-recovery`: deterministic per-root success/failure, topology/validity/tolerance evidence and the fixed opt-in ShapeFix profile with distinct raw and healed BREP artifacts.
- The ACX-17 lexical graph remains observed authority. XDE is translator-observed; raw BREP, healed BREP and GLB are distinct derived representations. No source-exact BREP or repair correctness is claimed.

## Evidence owners

- Normative profile: `docs/specs/step-iges-v03-profile.md`
- Schemas: `schemas/v0.2/step-iges-xde-event.schema.json` and packaged mirror
- Provider: `providers/step-iges-ocp/worker.py` under the unchanged ACX-24 OCI boundary
- Corpus: `conformance/v0.3/step-iges-corpus.json`
- Fixtures: `fixtures/v0.3/step-iges/` plus exact ACX-17 sources by digest
- Tests: `tests/test_step_iges_v03.py`
- Gate: `scripts/check_step_iges_v03_conformance.py`

## TDD and current evidence

- RED: the initial focused run failed six tests because the XDE schema, closed configuration, event validation and separate mapping did not exist.
- GREEN so far: focused portable contract/provider/adapter suites pass; exact OCP images are locally bound for Linux arm64/amd64; five source profiles produce byte-equivalent events/artifacts across both architectures; disabled/enabled healing pairs preserve identical raw translator BREP and add only distinct healed artifacts.
- Focused: `pytest -q tests/test_step_iges_v03.py tests/test_step_iges_provider.py tests/test_step_iges_adapter.py tests/test_provider_multiarch.py tests/test_v03_claim_registry.py tests/test_package_data.py` passes with only the inherited opt-in skips.
- Live: `./scripts/verify_step_iges_v03_provider.sh` passes the exact local image bindings, five-input arm64/amd64 equality and two-architecture disabled/enabled healing pair.
- Conformance: `python scripts/check_step_iges_v03_conformance.py --require-public --require-live-images` passes two claims, six replays and two healed roots.
- Canonical: `./scripts/verify.sh` passes 726 tests with 12 intentional provider skips; portable verification, wheel/sdist checks, baseline integration and release verification are green.

## Fixtures and rights

`ap214-xde.step` and its generator are project-authored Apache-2.0 box/metadata fixtures. The v0.3 replay corpus contains six exact requests/responses: AP203, AP214, AP242 edition 1, IGES 5.3, AP214 metadata and AP214 metadata with healing. Every provider artifact is content-addressed by the provider protocol; the corpus additionally binds the profile, schema, generator and XDE fixture hashes.

## Security, licensing and platform boundary

Inputs and XDE metadata remain untrusted data. Only action `extract` and the two exact path-free configurations are admitted; external references, network, commands and writer actions remain unreachable. OCP Apache-2.0 and OCCT LGPL-2.1 with exception stay in operator-built OCI images and do not enter the Apache-2.0 wheel/sdist. Live claims are exact Linux arm64/amd64 plus portable replay; other platforms/runtimes remain unsupported.

## Residual non-claims

Unlisted schemas/editions/forms; AP242 PMI/GD&T, saved views, kinematics and composites; external/protected/multifile content; complete source/XDE correlation; source-exact BREP; implicit or correct healing; geographic CRS/survey authority; authoring write-back; provider image publisher authenticity; and consumer semantics remain unsupported, unknown or conflicted as governed by the profile.

## Neutrality

No WoodFraming repository, dependency, vocabulary or consumer mapping is part of ACX-32. `/Users/facundo/desarrollo/woodframing` is outside this worktree and is not modified.
