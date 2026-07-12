# AECCTX v0.2 Compatibility and Migration

Date: 2026-07-11
Status: ACX-11 compatibility contract
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

The reference implementation remains version `0.1.0` until the governed expansion release. Supporting v0.2 schemas in ACX-11 is a bounded compatibility capability, not a claim that later v0.2 format adapters exist.

## Schema boundary

v0.1 schemas under `schemas/v0.1/` are immutable. v0.2 packages use:

- `aecctx_version = "0.2.0"`;
- `record_version = "0.2"` for every standard JSONL record;
- `required_extensions`, including an empty array when none are required;
- optional namespaced manifest `extensions`;
- typed record fields for `evidence_class`, `inference`, `coordinate_qualification`, `representation_fidelity`, and `provider_attestation`.

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

## Conformance material

- v0.1 compatibility fixture: `fixtures/minimal-aecctx`;
- v0.2 positive fixture: `fixtures/v0.2/shared/minimal-v02`;
- dynamic negative fixtures: `tests/test_v02_compatibility.py`;
- claim registry: `conformance/v0.2/claims.json`;
- acceptance evidence: `docs/evidence/ACX-11.md`.
