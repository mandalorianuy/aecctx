#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
provider=""
platform=""
architecture=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider) provider="$2"; shift 2 ;;
    --platform) platform="$2"; shift 2 ;;
    --architecture) architecture="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ "$platform" != "linux" || ( "$architecture" != "arm64" && "$architecture" != "amd64" ) ]]; then
  echo "platform/architecture must be linux and arm64 or amd64" >&2
  exit 2
fi
case "$provider" in
  tesseract) context="providers/tesseract-ocr"; image="aecctx-tesseract-ocr:0.3.0-linux-$architecture" ;;
  step-iges) context="providers/step-iges-ocp"; image="aecctx-step-iges-ocp:0.3.0-linux-$architecture" ;;
  dwg) context="providers/libredwg"; image="aecctx-dwg-libredwg:0.3.0-linux-$architecture" ;;
  *) echo "provider must be tesseract, step-iges or dwg" >&2; exit 2 ;;
esac

cd "$repo_root"
docker buildx build --platform "linux/$architecture" --load --pull=false --provenance=false --sbom=false --tag "$image" "$context"
PYTHONPATH=src "${PYTHON:-python3}" scripts/provider_multiarch.py receipt \
  --provider "$provider" \
  --architecture "$architecture" \
  --output "fixtures/v0.3/provider-multiarch/receipts/$provider-linux-$architecture.json"
