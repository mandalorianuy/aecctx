#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

PYTHONPATH=src "${PYTHON:-python3}" scripts/provider_multiarch.py verify \
  --output-root fixtures/v0.3/provider-multiarch/live
PYTHONPATH=src "${PYTHON:-python3}" scripts/check_provider_multiarch_conformance.py --require-live
