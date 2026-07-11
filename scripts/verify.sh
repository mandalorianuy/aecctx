#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

./scripts/verify_portable.sh
python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues
./scripts/verify_release.sh

echo "aecctx verify: ok"
