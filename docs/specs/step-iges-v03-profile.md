# AECCTX v0.3 STEP/IGES XDE and Recovery Profile

Date: 2026-07-14
Status: ACX-32 normative profile
Decision: ACXD-041

## 1. Functional boundary

This profile adds bounded XDE structure and per-root recovery to the immutable ACX-17 lexical and translator-derived evidence. It produces two public partial claims only after the complete ACX-32 corpus passes:

- `step-iges.xde-structure` for selected names, assembly labels, colors, layers, materials, declared units and placements;
- `step-iges.partial-recovery` for independent per-root success/failure, topology/tolerance reports and an optional, distinct healing result.

The default v0.1 opaque path and the ACX-17 v0.2 configuration remain unchanged. The v0.3 profile is selected only by the exact closed provider configuration in section 4.

## 2. Runtime, distribution and licenses

The sole runtime is Python 3.12 with `cadquery-ocp==7.9.3.1.1` and bundled OCCT 7.9.3. OCP is Apache-2.0; OCCT is LGPL-2.1-only with the OCCT exception. It executes only behind the exact ACX-24 `oci-docker-v1` Linux arm64/amd64 image registrations with network disabled. The Apache-2.0 core wheel/sdist contains no OCP, OCCT, native library or provider image.

Primary API authority is the OCCT 7.9 XDE guide and reference manual:

- <https://dev.opencascade.org/doc/occt-7.9.0/overview/html/occt_user_guides__xde.html>
- <https://dev.opencascade.org/doc/refman/html/class_s_t_e_p_c_a_f_control___reader.html>

## 3. Claimed source profiles

The format ceiling remains ACX-17: exact project-corpus AP203 `CONFIG_CONTROL_DESIGN`, AP214 IS, AP242 edition-1 long form and IGES 5.3. Other schemas, editions, IGES forms, compressed/protected sets, external files and proprietary extensions remain unsupported or opaque. A schema/runtime/platform pair is never generalized from another pair.

## 4. Closed actions and configuration

The provider accepts action `extract` only. The v0.3 configuration is exact and path-free:

```json
{"angular_deflection":0.5,"brep_format":"occt-ascii-brep-7.9.3","healing":{"enabled":false,"maximum_tolerance":0.001,"minimum_tolerance":1e-7,"precision":1e-7},"linear_deflection":0.1,"schema_profile":"acx32-xde-v1","tessellation_units":"source","xde":{"colors":true,"layers":true,"materials":true,"names":true,"placements":true,"units":true}}
```

The only alternate request changes `healing.enabled` to `true`. Unknown keys, paths, commands, environment variables, external resources, reader/writer actions and other numeric values fail with `AECCTX_STEP_IGES_CONFIGURATION_INVALID` before transfer.

## 5. Exact XDE API surface

STEP uses `STEPCAFControl_Reader`; IGES uses `IGESCAFControl_Reader`. Modes for names, colors, layers, materials and properties are explicitly enabled before `ReadFile` and `Transfer(TDocStd_Document)`. The worker reads:

- free shapes, assembly components, referred labels and shapes through `XCAFDoc_DocumentTool.ShapeTool_s` / `XCAFDoc_ShapeTool`;
- names through `TDataStd_Name`;
- generic, surface and curve colors through `XCAFDoc_ColorTool`;
- label layers through `XCAFDoc_LayerTool`;
- physical/visual material assignments only when returned by `XCAFDoc_MaterialTool` or `XCAFDoc_VisMaterialTool`;
- label locations as finite 3x4 affine matrices;
- exact source unit declarations plus the documented XDE/kernel length-unit result; absent/conflicting values remain explicit;
- topology validity through `BRepCheck_Analyzer` and min/average/max tolerances through `ShapeAnalysis_ShapeTolerance`.

No writer API is reachable from a provider request.

## 6. Events, correlation and authority

The v0.2 `aecctx.step-iges.source.v1` lexical event is retained byte-for-byte. XDE emits `aecctx.step-iges.xde.v1` with deterministic labels ordered by label entry. Each label preserves its XDE entry, kind, name state, colors, layers, materials, placement, unit state and parent/component relations.

Source correlation is allowed only when an exact retained source identifier uniquely matches an XDE identifier. The event records the method and source locator. Missing or ambiguous matches remain `unknown` or `conflicted`; no name, unit, placement, material or source ID is invented.

XDE is translator-observed evidence, not a replacement for source records. Consumer ontology, construction classification and generated Markdown remain outside this profile.

## 7. Per-root translation and healing

Each free XDE root emits `aecctx.step-iges.root.v1` with stable root ID, status, XDE label, source correlation, placement, validity, topology, bounds and tolerance summary. Successful raw translation writes `root-N.translated.brep`; failed roots have no artifact and retain a stable diagnostic. Independent roots are never discarded because one sibling fails.

With healing disabled, no healed artifact exists. With the admitted enabled profile, `ShapeFix_Shape` receives precision `1e-7`, minimum tolerance `1e-7` and maximum tolerance `1e-3`, performs once on a copy/result path and writes `root-N.healed.brep`. The event records before/after validity and tolerances. The raw BREP remains unchanged and authoritative as initial translator evidence.

Triangle JSON and core-produced GLB cite the raw translated root unless an explicit future profile selects another parent. No source-exact BREP, healing correctness, design intent or authoring write-back is claimed.

## 8. Diagnostics and loss

Stable additions are:

- `AECCTX_STEP_IGES_XDE_PARTIAL`;
- `AECCTX_STEP_IGES_XDE_CORRELATION_UNKNOWN`;
- `AECCTX_STEP_IGES_XDE_CORRELATION_CONFLICT`;
- `AECCTX_STEP_IGES_ROOT_INVALID`;
- `AECCTX_STEP_IGES_ROOT_TRANSFER_FAILED`;
- `AECCTX_STEP_IGES_TRANSFER_PARTIAL`;
- `AECCTX_STEP_IGES_HEALING_APPLIED`;
- `AECCTX_STEP_IGES_HEALING_FAILED`.

Every non-full capability has affected locators, fallback and reason codes. Partial root recovery cannot make session completeness or 3D geometry `full`.

## 9. Security, determinism and fixtures

Inputs and all metadata are untrusted data. External references are recorded but never opened; active links, macros, scripts and source commands are never executed. Existing byte, record, recursion, time, memory, output, filesystem, process and network limits remain mandatory.

The legally publishable project-authored corpus contains selected AP203/AP214/AP242 and IGES 5.3 XDE cases; positive names/colors/layers/materials/units/placements; multi-root partial success; invalid topology and tolerance cases; healing disabled/enabled pairs; external, malformed and unclaimed negatives; live Linux arm64/amd64 results and exact replay. Canonical events and artifacts must match across architectures after removing only governed architecture attestation fields.

## 10. Non-claims

AP242 PMI/GD&T, saved views, kinematics, composites, source-exact BREP, complete source/XDE correlation, implicit repair, repair correctness, geographic CRS, survey authority, external content, other runtimes/platforms and consumer semantics remain unsupported, unknown or conflicted as applicable.
