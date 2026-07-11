#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python3 scripts/check_spec_contract.py
python3 -m json.tool schemas/v0.1/manifest.schema.json >/dev/null
python3 -m json.tool schemas/v0.1/record.schema.json >/dev/null
python3 -m json.tool fixtures/minimal-aecctx/manifest.json >/dev/null

# Baseline-owned offer snapshots include upstream EOF formatting and are checked
# byte-for-byte by the full baseline integration checker when its private runtime
# is available locally.
git diff --check -- . ':(exclude).agent_baseline/baseline_offer/**'

echo "aecctx portable verify: ok"
