# AECCTX v0.3 Compatibility and Migration

Date: 2026-07-14
Status: release-candidate contract

AECCTX 0.3.0 is an implementation and conformance release over the unchanged v0.1 and v0.2 package schema lines. It does not introduce an `aecctx_version = "0.3.0"` package format.

## Compatibility matrix

| Input or producer behavior | AECCTX 0.3.0 |
|---|---|
| valid v0.1 package and records | read, validate, query, diff and render context |
| valid v0.2 package and records | read, validate, query, diff and render context |
| default writer/ingest without `--aecctx-version` | unchanged v0.1 output |
| explicit `--aecctx-version 0.2.0` | exact bounded v0.2 adapter profiles |
| `aecctx_version = "0.3.0"` package | rejected; no such schema line exists |
| unknown required extension | rejected |

The v0.1 schemas, v0.2 schemas, record versions, logical digest rules, value states, authority ordering and generated-Markdown boundary remain unchanged. No migration is required for valid v0.1 or v0.2 packages.

## Post-v0.2 capabilities

The public 0.3.0 implementation claims are the exact profiles in `conformance/v0.3/claims.json`. They add provider execution evidence, bounded IFC/DXF/OCR/vision/mesh/STEP/IGES/DWG profiles, advanced optional trust, expanded IDS and the portable inspector distribution without changing package schema semantics. Optional provider results remain readable after the provider is removed because authoritative records and artifacts are stored in the package.

Replay remains mapping evidence only. It does not establish live platform availability, provider isolation, entitlement or service behavior. ACX-34/RVT remains public `unsupported`; opaque ingest is not semantic RVT support.

## Upgrade and rollback

- Applications may upgrade the Python implementation from 0.2.0 to 0.3.0 without rewriting packages.
- Consumers that only understand v0.1 continue to reject v0.2 packages as before.
- Downgrading the implementation may make v0.3-only optional orchestration unavailable, but it does not alter existing v0.1/v0.2 package bytes.
- The inspector distribution supports AECCTX `>=0.2.0,<0.4.0`; its lifecycle contract is separate from package compatibility.

Machine evidence is bound by `conformance/v0.3/corpus.json`, which includes the immutable v0.1 and v0.2 aggregate corpora.
