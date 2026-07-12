# ACX-18 acceptance evidence

Status: completed

The exact experimental profile is self-contained R2000/`AC1015` through `org.aecctx.dwg.libredwg@0.2.0`, Linux arm64 live image `sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1`, plus portable offline replay.

Committed replay binds source DWG `fe9e07cabc83eb99c3c2334d5503fbcc9ebe0f94d349581ee559d57d6a30c494`, canonical LibreDWG JSON `190545218aed4766e0d477720362098f56c41f9279c200cd2750a5674bd32183` and converted DXF `9f86d16181606a3deb2e8ae1f5a1cb95c68885e2ee3e83d180940732d9a92ffc`.

The claim is partial: direct JSON objects are observed decoder evidence; DXF and normalized geometry are converted/derived. Duplicate handles remain conflicted. Units/CRS, complete 3D, ACIS/proxy/custom semantics, xref traversal and every DWG version other than AC1015 remain unsupported or unknown.

## Implemented

- Reviewed operator-built LibreDWG 0.13.4 image with reproducible ID, no network, read-only root, non-root execution and exact two-PID ceiling.
- Project-authored deterministic R2000 DXF/DWG fixture plus wrong-version and truncated negatives.
- Direct canonical LibreDWG JSON object evidence with duplicate-handle conflict preservation.
- Converted R2000 DXF and bounded simple geometry with `representation_fidelity.class = "converted"` and complete parent/hash lineage.
- v0.2 SDK ingest, portable CLI replay and deterministic directory/ZIP packages; default and explicit v0.1 remain opaque and byte-identical.
- GPL distribution record, native-decoder threat review, structured capability/loss reporting and exact experimental claim.

## Validation

- Focused/shared regression cut: 94 passed.
- Exact live provider cut: 4 passed; `dwgread 0.13.4`; image `sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1`.
- Portable repository cut: 249 passed, 9 opt-in live tests skipped; wheel and sdist built successfully.
- `python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues`: healthy, zero issues.
- `./scripts/verify_portable.sh`: passed.
- `./scripts/verify.sh`: passed.
- GitHub Actions CI run `29205070763` on implementation commit `fd1f5ff`: passed on macOS, Ubuntu and Windows.

## Residuals

Only self-contained `AC1015` is claimed. Other DWG versions/platforms, encrypted/protected inputs, xref traversal, ACIS/proxy/custom semantics, qualified units/CRS, complete 3D and source-exact geometry remain unsupported or unknown. The upstream material-decoder issue lacks a linked fixing commit/regression test, and aggregate `alive.test` writer failures remain recorded; the sandbox is therefore mandatory. The image is not distributed by core.

## Promotion

ACX-18 is `completed`; ACX-19 is `pending-next`. No RVT, signing, quality-gate, consumer or WoodFraming implementation was started.
