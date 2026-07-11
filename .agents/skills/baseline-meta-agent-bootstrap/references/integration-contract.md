# Integration Contract

Bootstrap must leave the repo healthy under the checker.

Success conditions:
- `load_meta_agent_contract(target_repo)` works
- `load_shell_runtime(target_repo)` works
- overlay manifest is parseable
- specialization profile is declared, valid, and reflected in integration state
- AGENTS baseline-managed block is present
- checker report persists under `.agent_baseline/reports/`
