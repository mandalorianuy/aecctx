#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python3 scripts/check_spec_contract.py
python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues
# Baseline-owned offer snapshots include upstream EOF formatting and are checked
# byte-for-byte by the baseline integration checker above.
git diff --check -- . ':(exclude).agent_baseline/baseline_offer/**'

echo "aecctx verify: ok"
