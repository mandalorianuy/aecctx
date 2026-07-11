# ACX-09 Acceptance Evidence

Date: 2026-07-11
Status: completed

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

## Remote integration and publication authorization

The public branch `codex/aecctx-implementation` passed Linux/macOS/Windows CI in run `29163959936`. It was integrated to `main` by fast-forward, and `main` passed the same matrix in run `29164030669`. The commit containing this completed evidence is the authorized target for signed repository tag/release `v0.1.0`; the tag workflow re-runs portable and release gates before publishing artifacts.
