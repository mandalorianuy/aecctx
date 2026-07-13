# ACX-23 Acceptance Evidence

Date: 2026-07-13
Status: completed

## Governed scope

ACX-23 packages the already accepted ACX-11 through ACX-22 line as reference implementation 0.2.0. It adds no format, provider, inference, trust, gate, plugin or consumer semantics. ACX-19 remains documented blocked.

## Implementation evidence

- Aggregate, digest-bound `conformance/v0.2/corpus.json` and strict claim/evidence verifier.
- Version-consistent wheel, sdist, deterministic plugin ZIP, checksums and SPDX SBOM.
- Clean core/all-extras CLI/import validation and artifact scans for restricted RVT/provider/consumer content.
- Compatibility, release, capability/evidence and supply-chain/provider/security/privacy documentation.
- Tag workflow publishing the five exact v0.2 assets only after portable and release gates pass.

## Validation evidence

Focused RED: `tests/test_v02_release.py` initially failed because `aecctx.release_conformance`, the aggregate corpus and v0.2 release documents did not exist.

`./scripts/verify.sh` passed with 624 tests, 9 intentional optional-runtime skips, the 206-case portable gate slice, wheel/sdist build, RVT restricted-artifact scan, baseline integration, v0.1 corpus, 23/23 mapped non-target v0.2 claims, one explicit target, 12 digest-bound component suites, deterministic plugin ZIP, clean core/all-extras install, checksums and SPDX SBOM.

Local artifact digests before publication:

- wheel: `f039de7cd5bd3870cd92c5957b777be9c8a8d2a83bc907577c34ff5fbece12da`;
- sdist: `44ae4e9f9b1beb622c98aecefe1d491524b32cb8d806a193366569befe9884ac`;
- plugin: `0a8ca0eb65d45f6896f5a432dd7236f3149ab1d5c3ba8e5607f894da4e0a5f73`;
- SPDX SBOM: `3563b0f52f89154956b57a552ada09de0ed2c6a64b88e8987944dc73c31cd19e`.

Candidate implementation commit `2a04d1cec49f72ff1dfd24e81ab6604795c1319d` passed [CI run 29273482180](https://github.com/mandalorianuy/aecctx/actions/runs/29273482180) on Ubuntu, macOS and Windows. ACX-23 remains `in_progress` until this evidence-bearing release commit, merged `main`, tag workflow and published assets all pass their exact gates.

## Tag workflow incident

Tag workflow `29275244351` rebuilt the exact immutable `v0.2.0` tag and passed portable verification, then exposed a GNU-tar portability defect in the release member check: `tar -tf ... | grep -q` runs under `pipefail`, so an early successful match closes the pipe and GNU tar exits on SIGPIPE. The required member was present; the gate reported it missing. The tag will not be moved or deleted. The governed recovery path is a RED regression test, a single root-cause fix on `main`, and a dispatch workflow that checks out the same tag as release source while using the reviewed corrected verifier from `main`.

## Remote integration and release evidence

- Evidence-bearing branch commit `2c15e46765a686e4146f3cb1e97050bf7a18b4d9` passed CI `29273977799` on Ubuntu, macOS and Windows.
- Merge commit `450bc4c14adeabb9b296201e806089354c0a7876` passed a fresh local `./scripts/verify.sh` and main CI `29274784620` on all three platforms before tag creation.
- The first immutable-tag workflow `29275244351` passed portable verification and exposed the GNU-tar gate defect before asset publication.
- Root-cause fix `2c75481e7900a862d3fff9f5a9a091b47671890c` passed 625 tests with 9 intentional skips, full local release verification and main CI `29276001711` on all three platforms.
- Governed recovery workflow `29277550208` checked out the exact `v0.2.0` tag as source, used the reviewed corrected verifier from `main`, passed portable and release gates, and published [AECCTX 0.2.0](https://github.com/mandalorianuy/aecctx/releases/tag/v0.2.0).
- Downloaded public `SHA256SUMS` verifies the published wheel, sdist and plugin archive. GitHub reports wheel `f039de7c...12da`, sdist `9a0e6fb8...0d77`, plugin `0a8ca0eb...5f73`, SBOM `3563b0f5...19e` and checksum file `1795db75...b173`.

ACX-23 is completed. No next task is promoted. ACX-10 remains deferred; any WoodFraming integration specification is consumer-owned and must start from `docs/integration/woodframing-boundary.md` under a separately accepted plan.

## Boundaries

No WoodFraming path, `WFDomain`, `WFImport`, proprietary runtime, credential, mandatory network or LLM dependency is authorized or distributed. Markdown remains a generated projection rather than evidence authority.
