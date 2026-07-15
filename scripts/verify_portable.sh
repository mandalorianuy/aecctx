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
"$python_runtime" -m json.tool schemas/v0.2/provider-descriptor.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/provider-request.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/provider-response.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/remote-provider-policy.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/mesh-coordinate-profile.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/crs-registry.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/step-iges-provider-event.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/step-iges-xde-event.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/dwg-provider-event.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/dwg-v03-event.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/rvt-provider-decision.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/rvt-provider-decision-v03.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/signature-bundle.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/signing-key-registry.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/signing-trust-policy.schema.json >/dev/null
"$python_runtime" -m json.tool schemas/v0.2/signature-verification-result.schema.json >/dev/null
for schema in signing-v2-policy x509-chain-result certificate-status-result timestamp-result countersignature-result advanced-trust-result; do
  "$python_runtime" -m json.tool "schemas/v0.2/${schema}.schema.json" >/dev/null
done
"$python_runtime" -m json.tool conformance/v0.2/claims.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/rvt-provider-decision.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/rvt-provider-decision.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/provider-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/ifc-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/dxf-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/inference-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/mesh-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/step-iges-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/dwg-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/signing-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/gate-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/plugin-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/claims.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/provider-multiarch-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/local-enforcement-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/remote-provider-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/ifc-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/mesh-crs-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/step-iges-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/dwg-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/signing-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/gate-corpus.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.3/plugin-corpus.json >/dev/null
"$python_runtime" -m json.tool plugins/aecctx-inspector/.codex-plugin/plugin.json >/dev/null
"$python_runtime" -m json.tool plugins/aecctx-inspector/.mcp.json >/dev/null
"$python_runtime" -m json.tool plugins/aecctx-inspector/assets/compatibility.json >/dev/null
"$python_runtime" -m json.tool plugins/aecctx-inspector/assets/distribution.json >/dev/null
"$python_runtime" -m json.tool fixtures/v0.2/plugin/prompt-injection-cases.json >/dev/null
"$python_runtime" -m json.tool fixtures/v0.3/plugin/host-matrix.json >/dev/null
"$python_runtime" -m json.tool fixtures/v0.3/plugin/adversarial-cases.json >/dev/null
"$python_runtime" -m json.tool fixtures/v0.3/plugin/lifecycle-cases.json >/dev/null
"$python_runtime" -m json.tool fixtures/v0.3/local-providers/adversarial-cases.json >/dev/null
"$python_runtime" -m json.tool fixtures/v0.3/remote-providers/adversarial-cases.json >/dev/null
"$python_runtime" -m json.tool fixtures/minimal-aecctx/manifest.json >/dev/null
"$python_runtime" -m json.tool fixtures/v0.2/shared/minimal-v02/manifest.json >/dev/null
"$python_runtime" scripts/check_rvt_blocked_conformance.py
"$python_runtime" scripts/check_rvt_blocked_conformance.py --decision conformance/v0.3/rvt-provider-decision.json --claims conformance/v0.3/claims.json
"$python_runtime" fixtures/v0.2/signing/generate_fixtures.py --check
"$python_runtime" scripts/check_signing_conformance.py
"$python_runtime" fixtures/v0.3/signing/generate_fixtures.py --check
"$python_runtime" scripts/check_signing_v03_conformance.py
"$python_runtime" fixtures/v0.2/gate/generate_fixtures.py --check
"$python_runtime" scripts/check_gate_conformance.py
"$python_runtime" fixtures/v0.3/gate/generate_fixtures.py --check
"$python_runtime" scripts/check_gate_v03_conformance.py --require-public
"$python_runtime" scripts/check_codex_plugin.py
"$python_runtime" scripts/check_codex_plugin_conformance.py
"$python_runtime" scripts/build_inspector_distribution.py --check
"$python_runtime" scripts/check_inspector_v03_conformance.py --require-public
"$python_runtime" scripts/check_provider_multiarch_conformance.py
"$python_runtime" scripts/check_local_enforcement_conformance.py
"$python_runtime" scripts/check_remote_provider_conformance.py --require-public
"$python_runtime" scripts/check_ifc_v03_conformance.py --require-public
"$python_runtime" scripts/check_dxf_v03_conformance.py --require-public
"$python_runtime" scripts/check_ocr_v03_conformance.py --require-public
"$python_runtime" scripts/check_vision_v03_conformance.py --require-public
"$python_runtime" scripts/check_mesh_crs_v03_conformance.py --require-public
"$python_runtime" scripts/check_step_iges_v03_conformance.py --require-public
"$python_runtime" fixtures/v0.3/dwg/generate_fixtures.py --check
"$python_runtime" scripts/check_dwg_v03_conformance.py --require-public
"$python_runtime" -c 'from aecctx.release_conformance import validate_release_corpus; result = validate_release_corpus("conformance/v0.2/corpus.json", repository_root="."); raise SystemExit(0 if result["ok"] else "v0.2 release corpus failed")'
"$python_runtime" -m aecctx.release_v03_conformance
"$python_runtime" -c 'from aecctx.conformance import validate_claim_registry_file; result = validate_claim_registry_file("conformance/v0.2/claims.json"); raise SystemExit(0 if result.valid else "; ".join(result.errors))'
"$python_runtime" -c 'from aecctx.conformance import validate_claim_registry_file; result = validate_claim_registry_file("conformance/v0.3/claims.json"); raise SystemExit(0 if result.valid else "; ".join(result.errors))'
"$python_runtime" -c 'from aecctx.providers import validate_provider_replay_corpus; result = validate_provider_replay_corpus("conformance/v0.2/provider-corpus.json"); raise SystemExit(0 if result["ok"] else "provider replay corpus failed")'
"$python_runtime" -c 'from aecctx.providers import validate_provider_replay_corpus; result = validate_provider_replay_corpus("conformance/v0.2/inference-corpus.json"); raise SystemExit(0 if result["ok"] else "inference replay corpus failed")'
"$python_runtime" -c 'from aecctx.providers import validate_provider_replay_corpus; result = validate_provider_replay_corpus("conformance/v0.2/step-iges-corpus.json"); raise SystemExit(0 if result["ok"] else "STEP/IGES replay corpus failed")'
"$python_runtime" -c 'from aecctx.providers import validate_provider_replay_corpus; result = validate_provider_replay_corpus("conformance/v0.2/dwg-corpus.json"); raise SystemExit(0 if result["ok"] else "DWG replay corpus failed")'
"$python_runtime" -m pytest tests/test_gate_*.py tests/test_claim_registry.py tests/test_v03_claim_registry.py tests/test_provider_multiarch.py tests/test_local_provider_profiles.py tests/test_remote_providers.py tests/test_package_data.py
"$python_runtime" -m pytest
rm -rf dist
mkdir -p dist
SOURCE_DATE_EPOCH=1783987200 "$python_runtime" -m build --wheel --sdist --outdir dist
release_artifacts=(dist/aecctx-0.3.0-py3-none-any.whl dist/aecctx-0.3.0.tar.gz)
"$python_runtime" scripts/check_rvt_blocked_conformance.py --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"
"$python_runtime" scripts/check_local_enforcement_conformance.py --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"
"$python_runtime" scripts/check_remote_provider_conformance.py --require-public --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"
"$python_runtime" scripts/check_ifc_v03_conformance.py --require-public --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"
"$python_runtime" scripts/check_dxf_v03_conformance.py --require-public --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"
"$python_runtime" scripts/check_ocr_v03_conformance.py --require-public --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"
"$python_runtime" scripts/check_vision_v03_conformance.py --require-public --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"
"$python_runtime" scripts/check_mesh_crs_v03_conformance.py --require-public --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"
"$python_runtime" scripts/check_step_iges_v03_conformance.py --require-public --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"
"$python_runtime" scripts/check_dwg_v03_conformance.py --require-public --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"
"$python_runtime" scripts/check_gate_v03_conformance.py --require-public --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"
"$python_runtime" scripts/check_inspector_v03_conformance.py --require-public --artifact "${release_artifacts[0]}" --artifact "${release_artifacts[1]}"

# Baseline-owned offer snapshots include upstream EOF formatting and are checked
# byte-for-byte by the full baseline integration checker when its private runtime
# is available locally.
git diff --check -- . ':(exclude).agent_baseline/baseline_offer/**'

echo "aecctx portable verify: ok"
