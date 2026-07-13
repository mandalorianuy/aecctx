# AECCTX v0.2 Compatibility and Migration

Date: 2026-07-12
Status: ACX-11 contract with ACX-13 through ACX-20 bounded profiles
Decision authority: ACXD-017

## Version matrix

| Producer/package | v0.1 reader | v0.2 reader |
|---|---|---|
| v0.1 package, `record_version = 0.1` | supported | supported without identity migration |
| v0.2 package, `record_version = 0.2` | not required to support | supported |
| v0.2 manifest with v0.1 records | invalid | invalid |
| unknown package version | invalid | invalid with `AECCTX_VERSION_UNSUPPORTED` |
| unknown required extension | not applicable | invalid with `AECCTX_REQUIRED_EXTENSION_UNSUPPORTED` |
| unknown optional namespaced extension | governed by v0.1 contract | accepted as package data; retained when explicitly passed through a lossless rewrite |

The reference implementation remains version `0.1.0` until the governed expansion release. Supporting v0.2 schemas in ACX-11 is a bounded compatibility capability. ACX-13 through ACX-18 add opt-in v0.2 producers for exact IFC, DXF, PDF/image inference, mesh coordinate, STEP/IGES and R2000 DWG profiles; they do not imply other DWG versions, other v0.2 format adapters, vision support, survey authority or source-exact translated BREP.

ACX-20 adds an optional detached signing sidecar profile without changing either package version. Unsigned v0.1/v0.2 packages remain valid and all existing read/query/diff/context behavior is unchanged.

## Schema boundary

v0.1 schemas under `schemas/v0.1/` are immutable. v0.2 packages use:

- `aecctx_version = "0.2.0"`;
- `record_version = "0.2"` for every standard JSONL record;
- `required_extensions`, including an empty array when none are required;
- optional namespaced manifest `extensions`;
- typed record fields for `evidence_class`, `inference`, `coordinate_qualification`, `representation_fidelity`, and `provider_attestation`.

Known transform links include both `matrix` and `inverse_matrix`, each as 16 row-major finite numbers. Semantic validation checks their round trip using the record's known positive tolerance when present, otherwise a conservative default. A forward matrix without a matching inverse is invalid.

Normative shared semantics are base v0.2 fields rather than loosely interpreted v0.1 extensions. Later tasks may add optional namespaced extensions, but they cannot redefine these fields or weaken their invariants.

## Migration rules

There is no automatic v0.1-to-v0.2 identity migration in ACX-11. A producer that intentionally recompiles or migrates a package MUST:

1. preserve original source and artifact hashes;
2. keep source evidence separate from inferred, manual and derived evidence;
3. assign `record_version = "0.2"` consistently;
4. populate `evidence_class` for every record;
5. carry optional extensions explicitly and declare required extensions;
6. recalculate artifact inventory and logical digest;
7. record the producer/version change so diff exposes it.

Changing only version strings is not a conforming migration when v0.2 semantic fields are required by the producing profile.

## Query, diff and context

- Query treats v0.2 fields as ordinary authoritative JSON paths after package validation.
- Diff compares both versions only after each package validates. It exposes `before_version`, `after_version`, and `version_changed`; changes to shared v0.2 fields remain record changes.
- Context renders the validated structured records under the selected token budget. It remains a projection and cannot replace inference, coordinate, fidelity or attestation records.

## Writer behavior

`PackageWriter` defaults to v0.1 for compatibility. A caller must explicitly request `aecctx_version="0.2.0"` and provide v0.2 record artifacts. The writer adds sorted `required_extensions` and optional `extensions`; it does not invent evidence-class, coordinate, provider or fidelity values.

`ingest_ifc()`, `ingest_dxf()`, `ingest_pdf()`, `ingest_image()`, `ingest_geometry()`, `ingest_step_iges()`, `ingest_dwg()` and `aecctx ingest --aecctx-version 0.2.0` provide the completed bounded profiles. PDF/image inference additionally requires an explicit validated `ProviderResult` in the SDK or `--inference-replay` plus `--inference-entry` in the CLI. STEP/IGES and DWG require a validated provider result or `--provider-replay` plus `--provider-entry`; CLI replay never launches Docker. Mesh registration requires a validated SDK mapping or `--mesh-coordinate-profile`; without it, the v0.2 geometry adapter preserves only source-declared facts and explicit unknowns. Omitting the version remains v0.1 and is byte-compatible with explicit `--aecctx-version 0.1.0`.

## Conformance material

- v0.1 compatibility fixture: `fixtures/minimal-aecctx`;
- v0.2 positive fixture: `fixtures/v0.2/shared/minimal-v02`;
- dynamic negative fixtures: `tests/test_v02_compatibility.py`;
- claim registry: `conformance/v0.2/claims.json`;
- bounded DXF corpus: `conformance/v0.2/dxf-corpus.json`;
- bounded OCR replay corpus: `conformance/v0.2/inference-corpus.json`;
- bounded mesh coordinate corpus: `conformance/v0.2/mesh-corpus.json`;
- bounded STEP/IGES replay corpus: `conformance/v0.2/step-iges-corpus.json`;
- bounded R2000 DWG replay corpus: `conformance/v0.2/dwg-corpus.json`;
- bounded signing corpus: `conformance/v0.2/signing-corpus.json`;
- shared compatibility evidence: `docs/evidence/ACX-11.md`;
- signing evidence: `docs/evidence/ACX-20.md`.

## Detached signing compatibility

The `detached-jws-ed25519-offline-v1` statement validates the package first, binds its logical digest and a canonical manifest with only `package_form` removed, and therefore produces the same statement for equivalent directory and ZIP forms. The signature bundle is never a package artifact, required extension, logical-digest input or Markdown authority.

Verification requires explicit caller-supplied registry and optional policy bytes. Unknown keys, lifecycle status, trust and authorization are never inferred. Repacking without semantic change preserves the statement; changing an artifact, manifest semantic field, digest, protected header or signature produces a distinct governed result.
