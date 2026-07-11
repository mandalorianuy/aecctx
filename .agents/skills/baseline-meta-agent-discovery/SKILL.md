---
name: "baseline-meta-agent-discovery"
description: "Audit an existing baseline-integrated consumer repository against codex-agent-baseline. Historical meta-agent naming is compatibility-only; use for legacy consumers, not as the future specialized-agent model."
---

# Baseline Consumer Discovery

Use this skill when a baseline-integrated consumer repo needs a baseline integration brief without mutating the repo by default.

The old `meta-agent` product concept is deprecated. This skill remains for compatibility with already integrated consumers; new specialized agents should be resolved through Agent Profile and Agent Stack Composition.

## Workflow

1. Run the deterministic skill wrapper from this skill directory:

```bash
python3 scripts/run-discovery.py --repo-root . --format markdown
```

2. Only if you need to debug the wrapper itself, fall back to the shared CLI directly:

```bash
python3 -m agent_baseline.meta_agent_tooling check-integration --repo-root . --format markdown
```

3. Use the checker output as the primary brief. Only after that, read references for deeper context:
   - [baseline-offer.md](references/baseline-offer.md)
   - [integration-contract.md](references/integration-contract.md)
   - [update-policy.md](references/update-policy.md)

## Output

Produce a short actionable brief with:
- baseline offer and default bundle pin
- published baseline-offer files under `.agent_baseline/baseline_offer/` when the repo is already synced
- selected specialization profile and available baseline-owned profiles
- consumable operator-facing contracts exposed by baseline, especially `harness_session_view` when present
- current integration posture
- detected gaps
- one recommended next action: `bootstrap`, `sync`, or `none`
