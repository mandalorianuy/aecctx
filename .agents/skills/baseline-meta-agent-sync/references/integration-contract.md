# Integration Contract

Sync must preserve:
- supported consumer edits in `specialization_overlay.toml`
- existing `[[commands]]` and `[[panels]]` overlay contributions
- consumer content outside the baseline-managed AGENTS block

If the repo needs a non-neutral posture, run sync with `--specialization-profile <profile-id>` so the managed defaults are reseeded from a baseline-owned profile instead of being inferred ad hoc.

Sync must not:
- silently upgrade to a breaking bundle major
- overwrite domain-specific contracts outside the overlay seam
