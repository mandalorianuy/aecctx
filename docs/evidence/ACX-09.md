# ACX-09 Acceptance Evidence

Date: 2026-07-11
Status: in progress - local release candidate validated; publication pending

## Implemented and locally validated

- Stable package/spec/schema version `0.1.0`.
- Governed seven-entry conformance corpus covering opaque, IFC, DXF, vector PDF, raster PDF, image and geometry adapters.
- Exact fixture hashes, expected capability maps, package validation and repeated byte-determinism checks.
- Python 3.12+ wheel/sdist metadata, optional extras and clean-venv install gate.
- SHA256SUMS and deterministic SPDX 2.3 SBOM generation.
- Changelog, compatibility policy, versioned release notes and release claim boundaries.
- Linux/macOS/Windows CI matrix and tag-triggered GitHub release workflow.

## Local acceptance evidence

`./scripts/verify.sh` completed with 85 tests, wheel `aecctx-0.1.0-py3-none-any.whl`, sdist `aecctx-0.1.0.tar.gz`, healthy baseline integration, seven valid/deterministic/matching corpus entries, generated checksums/SBOM, and successful clean installation/CLI validation.

## Publication gate still open

ACX-09 remains `in_progress` until the implementation branch is published, remote branch CI is green, the work is integrated to `main`, main CI is green, and tag/release `v0.1.0` completes successfully. No tag or release is claimed by this candidate evidence.
