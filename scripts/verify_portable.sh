#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -x .venv/bin/python ]]; then
  python_runtime=".venv/bin/python"
else
  python_runtime="${PYTHON:-python3}"
fi

"$python_runtime" scripts/check_spec_contract.py
"$python_runtime" -m json.tool schemas/v0.1/manifest.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.1/record.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.1/neutral-vocabulary.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/manifest.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/record.schema.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/claims.json >/dev/null
"$python_runtime" -m json.tool fixtures/minimal-aecctx/manifest.json >/dev/null
"$python_runtime" -m json.tool fixtures/v0.2/shared/minimal-v02/manifest.json >/dev/null
"$python_runtime" -c 'from aecctx.conformance import validate_claim_registry_file; result = validate_claim_registry_file("conformance/v0.2/claims.json"); raise SystemExit(0 if result.valid else "; ".join(result.errors))'
"$python_runtime" -m pytest
"$python_runtime" -m build --wheel --sdist --outdir dist

# Baseline-owned offer snapshots include upstream EOF formatting and are checked
# byte-for-byte by the full baseline integration checker when its private runtime
# is available locally.
git diff --check -- . ':(exclude).agent_baseline/baseline_offer/**'

echo "aecctx portable verify: ok"
