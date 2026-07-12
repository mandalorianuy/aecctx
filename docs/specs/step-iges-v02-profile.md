# AECCTX v0.2 STEP/IGES Evidence Profile

Version: `0.2.0-draft.2`
Date: 2026-07-12
Status: ACX-17 normative profile
Decision authority: ACXD-014, ACXD-019 and ACXD-028

## 1. Scope and claim lifecycle

ACX-17 defines two bounded claims selected only with `aecctx_version="0.2.0"`:

- `step-iges.source-structure` preserves the bounded lexical source-entity graph and only product/assembly facts directly recoverable from enumerated STEP records;
- `step-iges.brep-geometry` preserves enumerated curve/surface/topology evidence through a reviewed native kernel and emits subordinate deterministic tessellation.

Both claims begin `experimental partial`. ACX-17 does not claim XDE label correlation, normalized styles/materials, resolved instance matrices, validation properties or unit conversion. Those facts remain in raw observed source records where present and are explicitly unknown/unsupported in normalized records. Claims become public only after every exact format/kernel/platform combination in the claim registry has live or replay evidence appropriate to the claim. A replay proves protocol, mapping and package determinism; it does not prove that a native runtime exists on the replay host.

The live ACX-17 profile is limited to an operator-built Linux arm64 OCI image containing Python 3.12, `cadquery-ocp==7.9.3.1.1` and its bundled OCCT 7.9.3 runtime. The accepted provider identity is `org.aecctx.step-iges.ocp@0.2.0`. The image tag and inspected immutable image ID are both allowlisted; mismatch or absence rejects execution. Linux x86-64, macOS, Windows, other OCP/OCCT versions and unreviewed images remain unsupported.

The bounded source profiles are:

- STEP ISO 10303-21 physical files whose sole `FILE_SCHEMA` identifier is `CONFIG_CONTROL_DESIGN` (AP203), `AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }` (AP214 IS) or `AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF { 1 0 10303 442 1 1 4 }` (AP242 edition 1 long form). ASCII whitespace inside the edition braces is normalized only for profile matching; the complete source string remains observed evidence;
- IGES 5.3 clear-text files with a valid Start, Global, Directory Entry, Parameter Data and Terminate section sequence;
- self-contained files only.

An exact schema identifier not present in the claim registry is preserved but receives `AECCTX_STEP_SCHEMA_UNCLAIMED`. Unknown STEP application protocols and non-5.3 IGES versions remain unsupported for structured extraction. Compressed, encrypted, protected, external-reference-dependent and multi-file exchange sets remain opaque or unsupported.

## 2. Kernel, provider and licensing boundary

Open CASCADE Technology is native LGPL-2.1 with the OCCT exception. OCP bindings are Apache-2.0. Neither dependency enters the Apache-2.0 core wheel, optional in-process extras or host process. They run only behind the ACX-12 `oci-docker-v1` provider boundary.

The provider image is built explicitly by an operator from a reviewed recipe. Core ingest never builds, pulls, installs or discovers it. Runtime network and telemetry are disabled; no source or extracted content is retained outside the private content-addressed workspace. The provider receives only the staged input, canonical request, fixed configuration and bounded output root.

If a runtime image is distributed, its distribution record MUST include the applicable OCP/OCCT notices, OCCT license text, corresponding-source offer or source/build instructions required by the selected LGPL distribution form, wheel/image hashes and replacement/relinking instructions. ACX-17 does not publish a container image by default. A local operator build is not a claim of publisher authenticity.

Project fixtures are authored in this repository and licensed under Apache-2.0. They contain no proprietary CAD output, confidential model, external reference or third-party geometry.

Any change to provider, Python, OCP, OCCT, base image, architecture, translator parameters or image ID creates a new runtime profile and requires a new license/security review and corpus run.

## 3. Trust and execution boundary

STEP/IGES bytes, entity graphs, labels, names, colors, layers, translator diagnostics, B-Rep objects and generated artifacts are untrusted data. The core owns source identity, limits, request digest, provider registration, output validation and package construction.

The provider MUST run with the complete ACX-12 Linux-container controls:

- no network, non-root user, read-only root filesystem, dropped capabilities and `no-new-privileges`;
- one provider process, bounded memory/CPU/open files/input/output/records/recursion and wall time;
- read-only content-addressed input/request/provider mounts, private tmpfs and one bounded writable output mount;
- immutable locale/timezone/hash behavior and normalized environment;
- complete process-tree termination and workspace cleanup;
- schema, sequence, path, symlink, size, hash, attestation and host-path validation before mapping.

Caller commands, shell strings, Python paths, plugins, environment variables, translator resource paths and arbitrary kernel parameters are prohibited. The configuration vocabulary is fixed by this profile. OCCT dynamic resource directories are image-owned and read-only.

STEP `external_file_id_and_location`, document links, references and URI-like strings and IGES external-reference entities are recorded as data but never opened. A file requiring external content emits `AECCTX_STEP_IGES_EXTERNAL_REFERENCE_UNRESOLVED` and cannot claim complete structure or geometry.

## 4. Provider request and response

The only accepted action is `extract`. Configuration is exact canonical JSON:

```json
{
  "brep_format": "occt-ascii-brep-7.9.3",
  "linear_deflection": 0.1,
  "angular_deflection": 0.5,
  "read_shape_healing": "translator-default-observed",
  "schema_profile": "acx17-v1",
  "tessellation_units": "source"
}
```

Deflections are expressed in kernel target units after the translator's declared conversion and are fixed for this profile. Callers cannot override them. `read_shape_healing` does not claim source-exact topology: OCCT translator processing and any healing performed by its fixed resource sequence are reported explicitly.

The response uses the ACX-12 envelope and emits only:

- one ordered `primitive` event carrying the validated bounded source graph and one ordered `primitive` event carrying translator-derived shape metadata;
- content-addressed BREP and canonical triangle-mesh JSON artifacts;
- capability/loss report and provider attestation;
- bounded resource usage and exact runtime versions.

Provider stdout/stderr is not package evidence. Unexpected event types, fields, paths or artifacts reject the response.

## 5. Source identity and locators

The original source hash, byte count, media type and embedding policy remain core-owned. Stable source locators are:

- STEP entity: `step:#<positive-decimal-id>`;
- STEP header field: `step-header:<FIELD_NAME>`;
- STEP product/instance relationship: `step-relation:#<entity-id>`;
- IGES directory entity: `iges:D<odd-eight-column-sequence>`;
- IGES global field: `iges-global:<field-name>`;
- OCCT/XDE label derived from source translation: `xde:<entry>` with cited source entity locators when the kernel exposes them;
- kernel shape path: `shape:<root-index>/<deterministic-child-index>...`.

Source entity records preserve original entity number, original class/type/form, raw parameter text or a bounded lossless token representation, direct referenced entity IDs and parser diagnostics. ISO 10303-21 complex instances are preserved as `original_class = "COMPLEX_INSTANCE"` plus their ordered component class names and unmodified raw statement; no component is selected as implicit primary meaning. They are `observed`. The adapter never rewrites entity IDs or presents XDE labels as source identifiers.

Repeated source entity IDs, invalid references, malformed sections, truncated records, invalid delimiters, recursion beyond limit and oversized parameter payloads fail or degrade with stable codes. Parser recovery never creates known values.

## 6. STEP structure profile

For claimed STEP schemas the provider preserves as raw entity evidence, when present:

- `FILE_DESCRIPTION`, `FILE_NAME` and exact `FILE_SCHEMA` header values;
- product, product definition, formation and shape-definition identities;
- next-assembly-usage and context-dependent-shape relationships;
- representation/representation-item identities and relationship paths;
- direct entity references, including assembly-usage records; normalized occurrence matrices remain unsupported;
- names, descriptions, colors, visibility, layers, materials, units and validation properties only inside raw source entities; XDE correlation and normalization remain unsupported;
- enumerated B-Rep, curve, surface and topology source classes.

The enumerated STEP source classes are `PRODUCT`, `PRODUCT_DEFINITION`, `PRODUCT_DEFINITION_FORMATION` and subtypes, `NEXT_ASSEMBLY_USAGE_OCCURRENCE`, `CONTEXT_DEPENDENT_SHAPE_REPRESENTATION`, `SHAPE_DEFINITION_REPRESENTATION`, `SHAPE_REPRESENTATION` and geometric/manifold subtypes, `REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION`, `ITEM_DEFINED_TRANSFORMATION`, `AXIS2_PLACEMENT_3D`, `CARTESIAN_POINT`, `DIRECTION`, `VECTOR`, `LINE`, `CIRCLE`, `ELLIPSE`, `B_SPLINE_CURVE` subtypes, `PLANE`, `CYLINDRICAL_SURFACE`, `B_SPLINE_SURFACE` subtypes, `VERTEX_POINT`, `EDGE_CURVE`, `ORIENTED_EDGE`, `EDGE_LOOP`, `FACE_BOUND`, `FACE_OUTER_BOUND`, `ADVANCED_FACE`, `OPEN_SHELL`, `CLOSED_SHELL`, `MANIFOLD_SOLID_BREP`, `BREP_WITH_VOIDS`, `SHELL_BASED_SURFACE_MODEL`, `GEOMETRIC_CURVE_SET`, `STYLED_ITEM`, `PRESENTATION_LAYER_ASSIGNMENT`, `COLOUR_RGB`, `SI_UNIT` and `CONVERSION_BASED_UNIT`. Subtypes are accepted only when their base relationship and fields are preserved by the exact runtime and exercised by the corpus.

AP242 GD&T, saved views, PMI, tessellated STEP, kinematics, composite/material semantics, external documents and schema entities not enumerated by the conformance corpus remain raw/opaque/unsupported. Their presence cannot promote `properties`, `relationships`, `materials_styles`, `2d_geometry`, `3d_geometry` or `validation` to `full`.

## 7. IGES structure profile

For claimed IGES 5.3 files the provider preserves:

- Start/Global/Terminate fields needed for identity and declared version;
- directory sequence, entity type/form, parameter-data pointer, structure, line font, level, view, transform pointer, label and subscript;
- the bounded raw Global section and version flag, plus directory labels, level and transform pointers;
- type/form identity for transformations and subfigures when present; parameter/XDE interpretation remains unsupported;
- entity type/form pairs 100 circular arc, 102 composite curve, 104 conic arc forms 1–3, 110 line, 116 point, 120 surface of revolution, 122 tabulated cylinder, 124 transformation matrix, 126 rational/non-rational B-spline curve, 128 rational/non-rational B-spline surface, 142 curve on parametric surface, 143 bounded surface, 144 trimmed parametric surface, 186 manifold solid B-Rep, 190 plane surface, 192 right circular cylindrical surface, 308 subfigure definition and 408 singular subfigure instance.

IGES has weaker assembly semantics than STEP. Subfigures and directory relationships remain original IGES evidence and are not relabeled as STEP-style product assemblies. Unsupported entity types/forms remain observed opaque records with `AECCTX_IGES_ENTITY_UNSUPPORTED`.

## 8. Units, placements and coordinate authority

Source-declared unit entities remain observed raw records. Normalized units, kernel target units and declared-to-kernel scale are `unknown` in the ACX-17 implemented cut because the reviewed runtime correlation is not proven by the corpus. No model-size guess is allowed.

Instance/placement transforms are not normalized in this cut. Source placement entities and references remain observed; normalized placement stays unknown with explicit profile-partial loss. Source-local, assembly, XDE/kernel and artifact frames remain distinct.

STEP/IGES coordinates establish no geographic CRS or survey authority in this profile. `global_location` remains unknown unless a later separately governed source profile proves a complete CRS chain. ACX-16 manual registration may be applied by a caller only as a separate downstream manual/derived layer; ACX-17 does not borrow or synthesize it.

## 9. Geometry and fidelity

Source entity records describe original STEP/IGES classes and references. Kernel B-Rep artifacts are translator-derived evidence, not exact source serialization. Each BREP artifact records:

- provider/runtime/configuration digest;
- source root/entity/label references;
- OCCT shape type, topology counts, bounds and tolerance summary;
- unit/frame and source-to-kernel transform;
- transfer status, warnings, failed roots and translator/healing report;
- `representation_fidelity.class = "brep"`, `derived = true` and source representation IDs.

The provider uses fixed deflection and angular tolerance and emits canonical finite vertices/triangle indices plus their BREP parent reference. The core validates that mesh evidence and uses the existing `trimesh==4.12.2` deterministic geometry convention to create GLB. GLB is `tessellated` and derived from cited BREP records; it is not a provider/source artifact. SVG previews, if emitted, are projections and do not count as source-native 2D.

The provider MUST NOT silently sew, heal, simplify, merge, split, reorient, rescale or discard shapes. Translator-default processing that cannot be disabled without invalidating the reviewed reader is explicitly attested and reported per root. A source-exact B-Rep claim is prohibited.

Empty transfer, partial root transfer, invalid shape, mesh failure and tolerance overflow retain successful independent evidence plus structured loss. A failed B-Rep transfer cannot yield `3d_geometry = full`.

## 10. Core mapping and package behavior

The core validates the provider result before constructing records. Mapping produces:

- observed source-entity primitives;
- observed product/assembly/instance/style/unit records when backed by exact source/XDE evidence;
- neutral entities and relations that cite observed parents and retain original classes;
- derived BREP/GLB geometry records and artifacts with representation fidelity;
- structured diagnostics and capability/loss summaries.

Extraction, kernel translation, neutral interpretation and any future consumer mapping remain separate modules. No product name, layer, color, geometry or STEP/IGES class is interpreted as a wall, beam, panel, manufacturing feature or consumer family.

`ingest_step_iges()` is v0.1 opaque by default. The bounded provider profile requires explicit v0.2 SDK selection and a validated `ProviderResult` or exact replay entry. CLI replay uses `--provider-replay` and `--provider-entry`; CLI never launches or installs the native provider implicitly.

If the provider is absent or rejected before a validated result exists, the caller may choose normal opaque ingest. The result MUST identify that fallback as opaque and MUST NOT advertise either ACX-17 claim. A validated partial provider response may produce a package only when every retained event/artifact remains independently valid and all omitted/failed content is represented in loss.

## 11. Diagnostics

Stable diagnostics include:

- `AECCTX_STEP_IGES_FORMAT_UNSUPPORTED`;
- `AECCTX_STEP_SCHEMA_UNCLAIMED`;
- `AECCTX_IGES_VERSION_UNCLAIMED`;
- `AECCTX_STEP_IGES_PARSE_FAILED`;
- `AECCTX_STEP_IGES_EXTERNAL_REFERENCE_UNRESOLVED`;
- `AECCTX_STEP_IGES_ENTITY_LIMIT_EXCEEDED`;
- `AECCTX_STEP_IGES_REFERENCE_DEPTH_EXCEEDED`;
- `AECCTX_STEP_IGES_UNIT_UNKNOWN`;
- `AECCTX_STEP_IGES_UNIT_CONFLICT`;
- `AECCTX_STEP_IGES_PLACEMENT_UNRESOLVED`;
- `AECCTX_STEP_IGES_TRANSFER_PARTIAL`;
- `AECCTX_STEP_IGES_TRANSFER_FAILED`;
- `AECCTX_STEP_IGES_TRANSLATOR_PROCESSING_APPLIED`;
- `AECCTX_STEP_IGES_BREP_INVALID`;
- `AECCTX_STEP_IGES_TESSELLATION_FAILED`;
- `AECCTX_STEP_IGES_RUNTIME_UNAVAILABLE`;
- inherited ACX-12 registration, digest, sandbox, timeout, resource, protocol, attestation and cleanup failures.

A stable diagnostic never converts an unknown or failed fact into a plausible default.

## 12. Conformance corpus

The ACX-17 completion corpus covers:

- STEP `CONFIG_CONTROL_DESIGN`, AP214 IS tuple `{ 1 0 10303 214 1 1 1 1 }` and AP242 edition-1 long-form tuple `{ 1 0 10303 442 1 1 4 }`, plus unknown/multiple schema identifiers;
- IGES 5.3 and unclaimed version;
- generated part/assembly source graphs for each claimed STEP schema and a generated IGES 5.3 solid;
- raw name, color, layer, unit and placement entities present in generated files, without normalized XDE/unit/placement claims;
- external-reference, unknown-schema and malformed negative fixtures exercised by scanner/provider failure tests;
- BREP topology/bounds/tolerance report and deterministic GLB;
- replay determinism and live OCI/replay parity for event/artifact hashes;
- inherited ACX-12 runtime enforcement plus STEP/IGES entity and recursion limits;
- default/explicit v0.1 opaque compatibility;
- repository/package scans proving no OCCT binary in core distributions and no WoodFraming/consumer vocabulary.

Every fixture, request, response, artifact and provider descriptor is content-addressed in `conformance/v0.2/step-iges-corpus.json`. Public claims map to exact test IDs and `docs/evidence/ACX-17.md`.

## 13. Residuals and non-claims

The following remain explicit residuals rather than implied support:

- schemas, application protocols and IGES versions/forms outside the corpus;
- AP242 PMI/GD&T, saved views, tessellated STEP, kinematics and composite semantics;
- external files, compressed exchange sets and proprietary extensions;
- source-exact B-Rep, authoring write-back, healing correctness and geometric repair;
- CRS/geographic/survey authority;
- live execution outside the exact Linux arm64 OCI image;
- provider image publisher authenticity or trust;
- XDE label/source correlation, normalized colors/layers/materials, units/conversion scales, resolved placements, per-root tolerance summaries and partial-root recovery;
- classification into construction, manufacturing or consumer ontologies.

A residual requires a new or amended governed profile, decision and conformance corpus before implementation or claim promotion.
