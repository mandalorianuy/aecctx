# ACX-23 Acceptance Evidence

Date: 2026-07-13
Status: in progress

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

Final local, candidate CI, merged-main CI, tag workflow and published-asset evidence will be appended only after each gate succeeds.

## Boundaries

No WoodFraming path, `WFDomain`, `WFImport`, proprietary runtime, credential, mandatory network or LLM dependency is authorized or distributed. Markdown remains a generated projection rather than evidence authority.

