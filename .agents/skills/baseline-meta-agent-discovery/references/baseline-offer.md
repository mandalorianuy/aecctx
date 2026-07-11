# Baseline Offer

`codex-agent-baseline` is the source of truth for:
- shared shell contract
- bundle-pinned shared contracts
- overlay composition model
- local-first governance and replay/audit posture
- baseline-owned integration checker for consumer repos
- operator-facing shared contracts such as `harness_session_view`

Consumer repos should:
- keep the shared shell contract baseline-owned
- contribute only through `specialization_overlay.toml`
- pin `contract_bundle_id` explicitly
- select a baseline-owned specialization profile when neutral defaults do not match the repo posture
- run the integration checker before merge
- consume baseline operator-facing contracts directly instead of recreating local harness semantics when a reusable contract already exists
