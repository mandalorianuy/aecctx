# External provider security, license and privacy review

Use one completed copy per provider/version/runtime digest. A descriptor or passing happy-path run alone is not approval.

## Identity and distribution

- Provider ID and version:
- Runtime/decoder versions and immutable digest:
- Supported formats/actions/platforms:
- Distribution owner and update channel:
- SPDX license(s), copyright owner and notices:
- Core linkage: confirm no GPL/commercial library is linked into the Apache-2.0 core:
- Redistribution rights for code, models, runtime and fixtures:
- Commercial entitlement acquisition, expiry and offline/unavailable behavior:

## Data and network posture

- Local-only or network-backed:
- Exact egress destinations/protocols, if any:
- User consent surface and default-deny behavior:
- Fields/content transmitted and minimization/redaction:
- Provider retention/deletion policy:
- Telemetry and opt-out behavior:
- Processing/storage jurisdiction and subprocessors:
- Secrets source, lifetime and proof they cannot enter package output:

## Enforcement profile

- Profile ID and claimed platform:
- Filesystem, user/permission, environment and temporary-storage evidence:
- Network denial or reviewed allowlist evidence:
- CPU, memory, wall-time, process-tree, open-file and output evidence:
- Input, decompression, recursion, record and artifact bounds:
- Timeout/cancellation process-tree termination and cleanup evidence:
- Unavailable-axis rejection behavior:

## Protocol and loss behavior

- Descriptor/request/response schema version:
- Content-addressed transport and attestation evidence:
- Determinism/replay result or explicit nondeterminism sources:
- Capability/loss table with reason codes and fallbacks:
- Invalid JSON, crash, partial output and provider-unavailable behavior:
- Traversal, symlink, forged hash, duplicate event and host-path abuse results:
- Legally publishable conformance fixtures and claim-registry IDs:

## Decision

- Decision: approved / blocked / bounded exception
- Exact provider/version/runtime/platform scope:
- Reviewer/date:
- Residuals promoted to spec/plan/backlog:
- Expiry or re-review trigger:
