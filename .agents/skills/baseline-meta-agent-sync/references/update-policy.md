# Update Policy

If sync reports bundle drift with breaking majors:
- stop
- review the bundle delta
- only continue with an explicit breaking-upgrade decision

If repo posture drift is caused by staying on the wrong specialization profile:
- re-run sync with the intended `--specialization-profile`
- let sync reseed untouched managed defaults
- keep consumer-owned overrides explicit in the overlay

Use discovery first if the current repo posture is unclear.
