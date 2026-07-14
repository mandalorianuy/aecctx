# AECCTX IFC v0.3 conformance fixtures

These minimal IFC4X3 ADD2 STEP files are original, project-authored fixtures
released under Apache-2.0 with the AECCTX repository. They contain no
third-party model content.

Regenerate them with the exact optional runtime used by ACX-27:

```sh
python fixtures/v0.3/ifc/generate_fixtures.py
python fixtures/v0.3/ifc/generate_fixtures.py --check
```

The positive fixture contains only the bounded native-2D and scaled-map forms
listed by `docs/specs/ifc-v03-profile.md`. The degraded and conflict fixtures
exercise fail-closed states and do not expand the public claim.
