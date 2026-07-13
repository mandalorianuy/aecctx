# ACX-26 Evidence — Optional remote provider protocol

Date: 2026-07-13
Status: `in_progress`; this file is not accepted capability evidence
Profile: `remote-https-spki-v1`

## Implemented candidate

- strict schema-backed per-call upload, billing, endpoint/SPKI, region, retention, telemetry, byte, timeout and retry policy;
- direct HTTPS transport with TLS handshake and constant-time SPKI verification before credential/source transmission;
- fixed route, redirect denial, no proxy/discovery/ambient credential/CA trust store/wall-clock trust decision;
- canonical content-addressed envelopes, bounded strict JSON, response digest, confined artifact materialization and existing v0.2 response validation;
- terminal authentication/identity/policy failures and bounded byte-identical retries for transport/429/502/503/504;
- deterministic replay, credential redaction and repository-owned loopback TLS reference implementation/corpus;
- optional `cryptography>=45,<50` remote extra; core remains network-free.

## Local evidence completed

- `python -m pytest tests/test_remote_providers.py tests/test_package_data.py tests/test_external_providers.py tests/test_v03_claim_registry.py -q`: passed.
- `python -m pytest -q`: 678 tests collected; 668 passed and 10 pre-existing conditional skips.
- `python scripts/check_remote_provider_conformance.py`: passed with 16 adversarial cases, live loopback and replay.
- clean wheel/sdist build plus remote artifact scan: passed.
- `python scripts/check_spec_contract.py` and `git diff --check`: passed.
- `./scripts/verify_portable.sh`: passed; portable cut 249 passed, complete suite 668 passed/10 skipped, artifacts rebuilt and rescanned.
- `./scripts/verify.sh`: passed; portable gate, healthy `baseline-shared-v1` integration with zero issues, v0.1/v0.2 release verification and clean artifact verification all green.

Exact branch CI is run after the implementation commit. It must be green before acceptance.

## Delivery blocker

The checkout exposes only the GitHub `origin` remote and contains no OneDev URL, project identifier, delivery contract, credential source or callable OneDev integration. Therefore a OneDev PR, required review and squash merge cannot be created or verified without inventing a bypass. The exact missing human input is the repository's OneDev base URL/project path plus an authorized credential or configured remote/tool and the applicable review rule.

Until that input exists, ACX-26 remains `in_progress`, `sandbox.remote-provider` remains `target`, ACX-27 remains `pending`, and the accepted-plan count does not advance.

## Residual non-claims

No third-party service availability/SLA, provider-side sandbox/deletion, jurisdictional compliance, billing accuracy, entitlement, semantic correctness, general Web PKI lifecycle, discovery, OAuth, mTLS, streaming or consumer approval is claimed. These boundaries are normative in `docs/specs/provider-remote-v03-profile.md` and ACXD-034.
