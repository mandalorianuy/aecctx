# Compatibility Policy

## Format v0.1

- `aecctx_version` is `0.1.0`; consumers reject unknown major versions and unknown required extensions.
- Patch releases preserve required v0.1 fields and semantic behavior. New optional fields may be added only when older consumers can safely ignore and retain them.
- A format-breaking change requires a decision entry, schema/version change, migration notes, fixtures and conformance evidence.
- JSON/JSONL and referenced artifacts are authoritative; Markdown remains a generated projection across compatible releases.

## Python package

- AECCTX 0.1.0 supports Python 3.12 and newer.
- The core wheel requires only JSON Schema validation dependencies. Format adapters and MCP remain extras.
- Public CLI JSON envelopes, diagnostic codes and read-only library result shapes are compatibility surfaces for the 0.1 line.

## Adapter claims

Capability support is per input and emitted package, not a blanket promise for every file version or construct. Any degradation must remain structured as `partial`, `opaque` or `unsupported` with evidence and fallback guidance.

## v0.2 development line

The governed development compatibility and migration contract is [`compatibility-v0.2.md`](compatibility-v0.2.md). Its shared schemas do not promote later adapter targets to release claims.
