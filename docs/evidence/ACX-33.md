# ACX-33 acceptance evidence

Date: 2026-07-14
Task: DWG version, xref, units and geometry expansion
Claim: `dwg.external-provider.v03` (`partial` under the exact ACXD-042 ceiling)

## Implemented result

- Exact external provider profile for LibreDWG 0.13.4 API/ABI 1 on reviewed Linux arm64 and amd64 images.
- Independently bounded AC1012/R13, AC1014/R14 and AC1015/R2000 configurations; R12 and R2004+ remain non-claims.
- Direct canonical LibreDWG JSON remains observed; DXF and simple 3D normalization remain converted/derived with content hashes and parent lineage.
- Explicit `$INSUNITS` qualification for the closed symbol set; absent units remain `unknown`.
- Shared content-addressed bundle validator with `image/vnd.dwg`, per-member provider results, separate sources and deterministic xref relations; no ambient path access.
- Closed `extract` action; writers, caller commands, encryption/protection bypass, ACIS, proxy and custom semantics remain unreachable or structured unsupported.
- Public/packaged schema, four-entry replay corpus, deterministic fixture generator, CLI multi-entry replay and package mapping.

## Evidence executed

The focused pre-change baseline passed `tests/test_dwg_provider.py`, `tests/test_dwg_adapter.py`, `tests/test_dxf_v03.py`, and the baseline integration checker. The new tests were observed RED for missing v0.3 provider configuration and later for missing bundle replay support before implementation.

Accepted focused evidence:

- `.venv/bin/python -m pytest tests/test_dwg_v03.py tests/test_dwg_provider.py tests/test_dwg_adapter.py tests/test_dxf_v03.py tests/test_package_data.py -q`;
- `AECCTX_RUN_DWG_V03_PROVIDER=1 .venv/bin/python -m pytest tests/test_dwg_v03.py -k live_v03 -q` — four inputs byte-equivalent on Linux arm64 and amd64;
- `.venv/bin/python scripts/check_dwg_v03_conformance.py --require-public --require-live-images`;
- package artifact scans through `scripts/check_dwg_v03_conformance.py --artifact ...`;
- `./scripts/verify_portable.sh`;
- `python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues`;
- `./scripts/verify.sh`.

The first full gate correctly stopped at the new package scan, which exposed a checker false positive: the permitted license-review document name matched the broad LibreDWG runtime predicate although neither wheel nor sdist contained `providers/libredwg/worker.py`. A focused RED/GREEN archive test now permits review documentation while rejecting the external runtime path. The rebuilt wheel and sdist pass the corrected scan.

Pre-push committed-blob inspection then found that the repository's general DXF text rule normalized provider-retained CRLF evidence after its digest was computed. ACXD-042's delivery amendment classifies all v0.3 DWG DXF fixtures as binary; a regression test and committed-blob digest comparison prove that clean checkouts preserve the validated bytes.

Exact-head GitHub run `29356222503` then proved that the initial fixture `--check` was not portable: Ubuntu and macOS attempted unavailable Docker/image inspection, while Windows terminated in that external generation path. The governed correction makes `--check` read-only and provider-free and keeps full exact-image regeneration under `--live-check`; neither portable replay nor this correction replaces the already executed live arm64/amd64 matrix.

Final local closure produced 255 tests in the full-dependency phase and 742 passed with 13 intentional provider/platform skips in the portable matrix. Wheel and sdist built successfully; both passed the corrected GPL-runtime scan, release verification and baseline integration. Commit, PR, exact-head CI and squash merge remain delivery evidence recorded by the task closeout.

## Claim ceiling and residuals

The claim is not generic DWG support. R12, R2004+, encryption/password handling, ACIS/SAT/SAB, exact BREP, proxy/custom/vertical semantics, complete 3D, complete xrefs, CRS/georeferencing, rendering parity, repair/write-back, unreviewed runtimes/providers/platforms and image signing remain explicit non-claims. Upstream issue #1037 has no release-specific fix-lineage proof; the sandbox remains mandatory.

WoodFraming, `WFDomain`, `WFImport` and all consumer ontology/mapping remain untouched and outside the neutral core.
