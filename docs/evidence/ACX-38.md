# ACX-38 Aggregate Conformance and 0.3.0 Release Evidence

Date: 2026-07-14
Status: Completed; immutable v0.3.0 release published and verified
Release commit: `d9c68d7d8a0b07efa8f87c2097571ba872e7d26f`

## Governed scope

This milestone implements only post-v0.2 aggregate conformance, compatibility verification, reproducible packaging and release publication. It consumes ACX-24 through ACX-37, preserves ACX-34 as documented `blocked`, and adds no package schema, adapter semantics, provider profile or consumer mapping.

Normative authority: post-v0.2 functional-debt spec section 21, implementation-plan ACX-38 and Task 15 of the detailed plan. No new decision was required.

## Deliverables and claims

- `conformance/v0.3/corpus.json` binds 17 component/compatibility suites, 14 task outcomes and all 19 claims.
- `src/aecctx/release_v03_conformance.py` rejects missing/duplicate/unmapped claims, digest drift, target/blocked promotion, replay-only positive claims and restricted/consumer artifact leakage.
- The implementation version is 0.3.0; package schemas remain exactly v0.1 and v0.2 and default output remains v0.1.
- Wheel, sdist and inspector ZIP are reproducible under the fixed release build epoch; checksums and SPDX 2.3 SBOM are deterministic.

The 17 bounded positive claims and two public `unsupported` outcomes are unchanged from their owning evidence. ACX-38 promotes no capability.

## Fixtures and origin

The aggregate references existing legally reviewed fixtures without copying or mutating them. Component hashes are listed in `conformance/v0.3/corpus.json`; v0.1 and v0.2 aggregate corpus hashes are included as compatibility evidence. Origins and licenses remain in each owning ACX evidence file and `docs/licenses/`.

## Validation plan and local evidence

The required commands are:

```text
python -m pytest tests/test_v03_release.py -q
python -m aecctx.release_v03_conformance
python scripts/check_spec_contract.py
./scripts/verify_portable.sh
./scripts/verify.sh
./scripts/verify_release.sh
python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues
```

TDD RED was observed as `ModuleNotFoundError: No module named 'aecctx.release_v03_conformance'` before implementation. The focused release suite passes 7 tests; the release-focused compatibility/package suite passes 56 tests; `./scripts/verify_portable.sh` passes 311 focused tests and 828 complete tests with 13 intentional skips. Repeated fixed-epoch wheel/sdist builds and repeated inspector builds are byte-identical; clean core and all-extras installations, artifact scan, SHA-256 verification and SPDX generation pass.

## Delivery and publication receipts

- Candidate commit `6b8ab606f4d204e8125680bafd695cb550b580a6` was independently approved on [PR #13](https://github.com/mandalorianuy/aecctx/pull/13); all six push/PR Linux, macOS and Windows checks passed.
- Reviewed squash merge `d9c68d7d8a0b07efa8f87c2097571ba872e7d26f` passed merged-main [CI run 29378117244](https://github.com/mandalorianuy/aecctx/actions/runs/29378117244) on Linux, macOS and Windows.
- Immutable annotated tag `v0.3.0` resolves to that exact merge commit. Tag [CI run 29378575104](https://github.com/mandalorianuy/aecctx/actions/runs/29378575104) and [release run 29378575118](https://github.com/mandalorianuy/aecctx/actions/runs/29378575118) passed.
- [AECCTX 0.3.0](https://github.com/mandalorianuy/aecctx/releases/tag/v0.3.0) is public, non-draft and non-prerelease. Downloaded wheel, sdist and inspector ZIP pass `SHA256SUMS` and are byte-identical to the locally verified fixed-epoch artifacts.
- Published SHA-256: wheel `0d247a0b9ce61603be4c9b768d0808a0a9b440d8083c32befa8c08ef78d00352`; sdist `11a11353ce9f58f6223713f2e384f3e35f51cb16de3f2ec9d731a974265e04a3`; inspector `ad138eb615ffa8b0143864fec81e1692ca27f3ca7a251a407ea6c79171f56fd3`; SPDX SBOM `1b3e01160e7500c3f2fc3aa8463a44d50f9ea2996114f95b2164239e5ec4d200`.

## Security, privacy, licensing and platforms

The release contains no native/GPL/commercial provider runtime, OCI image, RVT semantic implementation, credential, production key or consumer integration. Public Python CI covers Linux, macOS and Windows; live provider claims remain limited to their already recorded exact Linux arm64/amd64 evidence. Core remains offline and LLM-independent.

## Residuals and boundary

All residuals remain in `docs/capability-matrix.md` and the owning ACX evidence. Replay does not become live evidence; unsupported and blocked outcomes do not become positive capabilities. Marketplace/product-host behavior, universal trust, hidden source geometry, survey authority and engineering/consumer approval remain non-claims.

`/Users/facundo/desarrollo/woodframing` was not modified. ACX-10 remains deferred; consumer-owned planning begins only from `docs/integration/woodframing-boundary.md` under a separately accepted plan.
