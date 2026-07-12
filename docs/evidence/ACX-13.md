# ACX-13 acceptance evidence

Date: 2026-07-12
Status: completed
Task: IFC source-native 2D and georeferencing
Decision: ACXD-025
Completion commit: `feat: complete ACX-13 IFC 2D and georeferencing`

## Authority and bounded claims

The normative profile is `docs/specs/ifc-v02-profile.md`. Public claims are `partial` and limited to project-authored IFC2X3 TC1/IFC4 Add2 TC1 fixtures with optional `ifcopenshell==0.8.5`:

| Claim | Exact profile | Support |
|---|---|---|
| `ifc.native-2d` | explicit 2D contexts/views/identifiers; supported polyline/indexed-line/geometric-curve-set/mapped-2D items | `partial` |
| `ifc.georeferencing` | explicit IFC4 `IfcMapConversion` + `IfcProjectedCRS`, finite/invertible WCS/operation, compatible declared units | `partial` |

IFC4.1/4.2/4X3, unlisted 2D items, IFC2X3 property-set georeferencing, omitted map parameters, multiple operations, inferred EPSG and universal IFC support remain unclaimed.

## Implementation

- Explicit v0.2 opt-in while default/explicit v0.1 output remains byte-identical.
- Source primitives for 2D representations/items, contexts, CRS and coordinate operations before source-level qualification.
- Separate absent, empty, unsupported, extraction-failed, incomplete and conflicted states with stable diagnostics.
- Forward/inverse source-local→project→CRS matrices and unit-conflict rejection.
- Deterministic derived SVG citing authoritative representation IDs.
- Project-authored Apache-2.0-compatible fixtures and hash-locked corpus.

## Validation

- Targeted IFC/v0.2/CLI/claims/package-data bundle: `62 passed`.
- `python scripts/check_spec_contract.py`: passed.
- Claim registry validation: valid with no errors.
- `./scripts/verify_portable.sh`: passed with `160 passed`; wheel and sdist built successfully.
- `./scripts/verify.sh`: passed with `160 passed`; wheel/sdist, baseline integration (`healthy issues=0`), deterministic v0.1 corpus and release verification all passed.

## Fixtures and hashes

All fixtures were authored in this repository for publication under the project license:

| Fixture | Schema/purpose | SHA-256 |
|---|---|---|
| `ifc2x3-native-2d-local.ifc` | IFC2X3 native Axis/FootPrint, local-only | `c3c672e3725a204411d2822aa8d16a5d9a971a79161f8e886c7e8c338712a72d` |
| `ifc4-native-2d-georef.ifc` | IFC4 native Axis/FootPrint/Annotation/mapped 2D and complete bounded CRS | `5603c0bb19ed3e195eef2ddcc8fcdbcaeeed443e3508185f266c836788d70ff6` |
| `ifc4-degraded-2d-incomplete-georef.ifc` | absent/empty/unsupported/nonfinite 2D and incomplete operation | `eba3e37d054cbb95ed4af27230ddf8bf94a863f01de58fd27ab38cb04ddeac54` |
| `ifc4-conflicting-units.ifc` | project/map unit conflict | `adade7518ddb4923e4367a47006f96a70716713c28e95dbfe6305d0c2fec6c9d` |

The hash registry is `conformance/v0.2/ifc-corpus.json`.

## Dependency and platform evidence

- Tested and governed IfcOpenShell: exactly `0.8.5`; another version requires a conformance rerun and claim update.
- Official IfcOpenShell documentation states LGPL-3.0-or-later and extensive geometry support for IFC2X3 TC1/IFC4 Add2 TC1; later families are parsing-only/unclaimed here.
- IfcOpenShell 0.8.5 does not resolve `IfcCartesianTransformationOperator2D` through `resolve_items`; ACXD-025 bounds a direct structural mapping for that exact operator and rejects other mapped profiles.
- Platform scope follows environments where the optional IfcOpenShell Python wheel/profile and the portable test corpus pass. Core install remains independent.

## Security, license and privacy

IfcOpenShell remains an optional LGPL-3.0-or-later dependency and is not bundled in the Apache-2.0 core. Input is parsed as data; no external links, commands, macros, network or LLM are executed. Fixtures contain no personal or proprietary content.

## Non-scope and residuals

No engineering validation, consumer classification, 3D projection relabeled as native 2D, source mutation, DWG/RVT/STEP/IGES work or WoodFraming integration is included.

Residuals remain governed in `docs/specs/ifc-v02-profile.md`: later IFC4 schemas; arcs/conics/trimmed/composite curves; text/hatches/styles; IFC2X3 property-set georeferencing; omitted/multiple/non-invertible operations; inferred EPSG; and unproven mapped operators. They remain structured `partial`, `unknown`, `unsupported`, or `conflicted` states.

## Promotion and repository boundary

ACX-13 is completed and ACX-14 is promoted to `pending-next`; ACX-14 was not executed. No WoodFraming path, `WFDomain`, `WFImport`, network or LLM dependency was accessed or modified.
