# Contributing

AECCTX is specification-first. Changes that affect interoperability must begin with the owning specification, decision log, capability matrix, and fixture before or alongside implementation.

## Pull request requirements

1. Identify the active task in `docs/implementation-plan.md`.
2. Keep extraction, interpretation, and consumer mapping separate.
3. Add or update deterministic fixtures for observable format behavior.
4. Document capability loss and unsupported content.
5. Run `./scripts/verify.sh`.

Proposals outside the active task should normally begin as an issue or decision-log entry rather than an implementation patch.
