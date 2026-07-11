---
name: "baseline-meta-agent-bootstrap"
description: "Bootstrap a baseline-integrated consumer repository so it is immediately integrated with codex-agent-baseline. Historical meta-agent naming is compatibility-only; use for legacy integration, not as the future specialized-agent model."
---

# Baseline Consumer Bootstrap

Use this skill to initialize a baseline-integrated consumer repo with the baseline shell contract, managed overlay, governance state, consumer-local checker, and a published `.agent_baseline/baseline_offer/` materialization of baseline-owned manifests and latest artifacts.

The old `meta-agent` product concept is deprecated. This skill remains for compatibility with already integrated consumers; new specialized agents should be modeled through Agent Profile, Agent Stack Composition, PAO, Mission Control, Goal Mode, and Workbench contracts.

## Workflow

1. Run the deterministic skill wrapper from this skill directory:

```bash
python3 scripts/run-bootstrap.py --repo-root .
```

Use `--specialization-profile <profile-id>` when the consumer repo should not stay neutral. Operator-centric repos should normally bootstrap with:

```bash
python3 scripts/run-bootstrap.py --repo-root . --specialization-profile operator
```

2. If the baseline repo root is not discoverable from the consumer context, set `AGENT_BASELINE_ROOT` or pass `--baseline-root`.

3. After bootstrap, run:

```bash
python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues
```

4. Only if you need to debug the wrapper itself, fall back to the shared CLI directly:

```bash
python3 -m agent_baseline.meta_agent_tooling bootstrap --repo-root .
```

5. Read the references only when you need to explain or adjust the generated integration:
   - [baseline-offer.md](references/baseline-offer.md)
   - [integration-contract.md](references/integration-contract.md)
   - [update-policy.md](references/update-policy.md)

## Non-goals

- Do not add domain-specific commands or panels during bootstrap.
- Do not fork baseline manifests in place.
- Do not leave a consumer repo on the neutral profile when its posture is already known to be operator-, builder-, or session-centric.
