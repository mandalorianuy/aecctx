# ACX-24 provider multi-architecture fixtures

This directory contains deterministic receipts and live execution summaries for the project-authored v0.2 OCR, STEP/IGES and DWG fixtures executed on reviewed `linux/arm64` and `linux/amd64` OCI targets. The sources and replay outputs remain in `fixtures/v0.2`; the v0.3 corpus binds them by SHA-256 rather than duplicating evidence.

`receipts/` records the exact local image identity, platform manifest, build inputs, resolved package lock and licensing boundary. `live/executions/` records the source, response-semantic and artifact digests observed for each target. `live/verification-summary.json` records equivalence and sandbox adversarial outcomes. None of these files is an OCI image or permission to redistribute one.

Regenerate local evidence only with `scripts/build_provider_matrix.sh` and `scripts/verify_provider_matrix.sh`. Portable validation checks committed hashes without claiming Docker availability; claim promotion requires the live script with no skips.
