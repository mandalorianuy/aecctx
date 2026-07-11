---
name: "baseline-meta-agent-sync"
description: "Sync an already integrated baseline consumer repository against the current codex-agent-baseline catalog. Historical meta-agent naming is compatibility-only; use for legacy baseline-integrated consumers, not as the future specialized-agent model."
---

# Baseline Consumer Sync

Use this skill when a consumer repo is already baseline-integrated but needs to refresh managed files, skillpack content, and the published `.agent_baseline/baseline_offer/` contract materialization.

The old `meta-agent` product concept is deprecated. This skill remains for compatibility with already integrated consumers; new specialized agents should be modeled through Agent Profile, Agent Stack Composition, PAO, Mission Control, Goal Mode, and Workbench contracts.

## Workflow

1. Run the deterministic skill wrapper from this skill directory:

```bash
python3 scripts/run-sync.py --repo-root .
```

If the repo posture is known, pass the profile explicitly so sync can reseed managed defaults without clobbering consumer customizations:

```bash
python3 scripts/run-sync.py --repo-root . --specialization-profile operator
```

2. The sync preserves supported overlay customizations, refreshes published baseline-offer manifests and latest artifacts under `.agent_baseline/baseline_offer/`, and blocks breaking bundle upgrades unless explicitly allowed.
   It also writes through an in-progress sync lock so the checker can avoid false drift while managed files are being materialized. The checker now waits up to 30 seconds for that lock to clear before it reports drift.

3. Validate immediately after sync:

```bash
python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues
```

4. Only if you need to debug the wrapper itself, fall back to the shared CLI directly:

```bash
python3 -m agent_baseline.meta_agent_tooling sync --repo-root .
```

5. Use the references only if you need to explain drift or blocked upgrades:
   - [baseline-offer.md](references/baseline-offer.md)
   - [integration-contract.md](references/integration-contract.md)
   - [update-policy.md](references/update-policy.md)

6. If the consumer needs to understand whether a baseline capability is actually landed, read the generated integration report and catalog summary instead of inferring from stale dependency notes. The report now surfaces structured capability statuses for baseline rows such as `EXC-04`, `SWR-01`, and `SCG-05`, including:
   - `delivery_class`
   - `snapshot_counting_policy`
   - `blocking_posture`

7. Treat baseline status semantics as authoritative for baseline-owned rows:
   - `implemented` rows are published as `counted` and `non-blocking`
   - `deferred` rows are published as `excluded` and `non-blocking`
   - consumers should not invent a separate prompt-side rule for whether a baseline row belongs in the active maturity denominator
