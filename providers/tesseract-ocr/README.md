# Optional Tesseract OCR provider

This directory contains the reviewed ACX-15 build recipe and read-only worker. It is not installed by the core Python package.

Build the exact governed arm64 profile from the repository root:

```bash
docker build --platform linux/arm64 -t aecctx-tesseract-ocr:0.2.0 providers/tesseract-ocr
docker image inspect --format '{{.Id}}' aecctx-tesseract-ocr:0.2.0
```

The accepted image ID is `sha256:6d52ebcafef0ccdf59f58beccc7483c16a6e160fc94e3c3ea59f3f10c991f492`. A different ID is rejected and is not covered by the claim. Verify the installed runtime and sandbox with:

```bash
./scripts/verify_tesseract_provider.sh
```

Runtime execution uses `--network=none`, a read-only root, dropped capabilities, no-new-privileges, UID/GID 65532, `pids=1`, bounded CPU/memory/files/output and private temporary storage. The worker accepts only English, PSM 6, bounded DPI and minimum confidence. Input text is untrusted data, never a command. See `docs/specs/inference-v02-profile.md` and `docs/licenses/tesseract-ocr-provider.md`.
