# ACX-23 Expansion Release Implementation Plan

Status: `release-ready`; candidate CI green, merged-main/tag publication pending
Authority: `docs/implementation-plan.md` ACX-23 and `docs/specs/aecctx-capability-expansion-spec.md` section 17
Release: reference implementation `0.2.0`, package format support remains `0.1.0` and `0.2.0`

This execution cut adds no capability. It packages only the claims already accepted by ACX-11 through ACX-22, preserves ACX-19 as documented `blocked`, and keeps every unsupported or target profile out of positive release claims.

## Governed slices

1. **Release contract and RED tests.** Add tests that require an aggregate v0.2 corpus, one-to-one claim evidence mappings, version-consistent artifacts, release metadata, and tag workflow inputs.
2. **Conformance aggregation.** Add `conformance/v0.2/corpus.json` plus a deterministic checker that validates every public/experimental/unsupported claim and rejects unmapped positive claims, duplicate IDs, absent fixtures/tests/evidence, or target claims presented as implemented.
3. **Artifact and supply-chain gate.** Build wheel, sdist, and plugin archive; generate deterministic checksums and SPDX SBOM; scan artifact contents, dependencies, licenses, restricted provider binaries, credentials, and consumer-specific terms.
4. **Compatibility and release documentation.** Publish v0.2 migration notes, release notes, capability/evidence index, provider/security/privacy boundaries, README/changelog/version updates, and exact residuals.
5. **Local and remote release proof.** Run focused checks and `./scripts/verify.sh`, push the candidate branch, require Linux/macOS/Windows CI green on the exact SHA, merge without rewriting history, re-run gates on `main`, then tag `v0.2.0` and verify the published release assets/checksums.
6. **Immutable-tag incident recovery.** If the tag workflow exposes a release-gate portability defect after the tag is public, preserve the tag, add a failing regression test and root-cause fix on `main`, then use a governed recovery workflow that rebuilds from that exact tag and executes the corrected verifier from reviewed `main`. Never move or delete the published tag.

## Boundaries

- No new adapter, provider, inference, signing, gate, plugin semantic, or consumer mapping is authorized.
- ACX-19 remains `blocked`; vision/reconstruction and all unlisted profiles remain target/unsupported.
- Provider replays are portable conformance evidence; live native/GPL providers retain their exact reviewed platform scopes.
- No WoodFraming, `WFDomain`, `WFImport`, proprietary binary, credential, network requirement, or LLM requirement may enter the distribution.
- The tag is created only from an exact green commit reachable from `main`.

## Acceptance evidence

- Focused release-contract tests demonstrate RED before implementation and GREEN afterward.
- `conformance/v0.2/corpus.json` and generated release reports are deterministic.
- Clean core and optional-extra artifact matrices pass, including v0.1 compatibility and v0.2 signing/gate/plugin corpora.
- `./scripts/verify.sh` passes before ACX-23 closure.
- Candidate, merged-main, and tag workflow runs are green for their exact SHAs; published assets match `SHA256SUMS`.
