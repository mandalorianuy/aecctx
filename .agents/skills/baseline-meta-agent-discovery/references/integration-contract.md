# Integration Contract

Required consumer files:
- `.agent_baseline/manifests/specialization_overlay.toml`
- `.agent_baseline/meta_agent_baseline_integration.toml`
- `.agent_baseline/reports/latest-baseline-integration-report.json`
- `scripts/check_meta_agent_baseline_integration.py`
- `AGENTS.md` baseline-managed block

Discovery should call out:
- which specialization profile is selected
- which baseline-owned profiles are available
- which operator-facing baseline contracts are consumable from the current catalog
- whether the current profile is plausibly misaligned with repo posture

Discovery is audit-only by default. Use bootstrap or sync for mutations.
