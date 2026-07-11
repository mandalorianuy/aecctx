## Baseline Meta-Agent Integration

This repository consumes `codex-agent-baseline` as the source of truth for the shared shell contract and shared contract governance.

Rules:
- Overlay location: `.agent_baseline/manifests/specialization_overlay.toml`
- Keep `contract_bundle_id = "baseline-shared-v1"` pinned unless a reviewed bundle upgrade is approved
- Required check before merge: `python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues`
