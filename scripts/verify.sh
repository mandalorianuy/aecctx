#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

./scripts/verify_portable.sh
if [[ "${AECCTX_VERIFY_PROVIDER_MATRIX:-0}" == "1" ]]; then
  PYTHON="${PYTHON:-python3}" ./scripts/verify_provider_matrix.sh
fi
python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues
./scripts/verify_release.sh

echo "aecctx verify: ok"
