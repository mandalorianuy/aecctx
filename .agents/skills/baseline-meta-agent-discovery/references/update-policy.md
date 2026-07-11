# Update Policy

Use discovery to decide whether the repo needs:
- `bootstrap`: repo is not yet baseline-integrated
- `sync`: repo is integrated but drifted
- `none`: repo is healthy

Do not patch contracts or shell manifests in place inside the consumer repo.
If the repo is healthy structurally but sits on the wrong specialization profile, discovery should still recommend `sync`.
