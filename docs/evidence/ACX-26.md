# ACX-26 Evidence — Optional remote provider protocol

Date: 2026-07-13
Status: accepted and completed after the governed GitHub squash merge
Profile: `remote-https-spki-v1`

## Implemented result

- strict schema-backed per-call upload, billing, endpoint/SPKI, region, retention, telemetry, byte, timeout and retry policy;
- direct HTTPS transport with TLS handshake and constant-time SPKI verification before credential/source transmission;
- fixed route, redirect denial, no proxy/discovery/ambient credential/CA trust store/wall-clock trust decision;
- canonical content-addressed envelopes, bounded strict JSON, response digest, confined artifact materialization and existing v0.2 response validation;
- terminal authentication/identity/policy failures and bounded byte-identical retries for transport/429/502/503/504;
- deterministic replay, credential redaction and repository-owned loopback TLS reference implementation/corpus;
- optional `cryptography>=45,<50` remote extra; core remains network-free.

## Local evidence completed

- `python -m pytest tests/test_remote_providers.py tests/test_package_data.py tests/test_external_providers.py tests/test_v03_claim_registry.py -q`: 60 passed after the public-claim assertion was added.
- `python -m pytest -q`: 679 tests collected; 669 passed and 10 pre-existing conditional skips.
- `python scripts/check_remote_provider_conformance.py`: passed with 16 adversarial cases, live loopback and replay.
- clean wheel/sdist build plus remote artifact scan: passed.
- `python scripts/check_spec_contract.py` and `git diff --check`: passed.
- `./scripts/verify_portable.sh`: passed; portable cut 250 passed, complete suite 669 passed/10 skipped, artifacts rebuilt and rescanned with `--require-public`.
- `./scripts/verify.sh`: passed; portable gate, healthy `baseline-shared-v1` integration with zero issues, v0.1/v0.2 release verification and clean artifact verification all green.

- GitHub Actions CI for implementation SHA `81509ace68d3af6f887f73669ab0b0665560e6c7`: passed on Ubuntu, macOS and Windows ([run 29293128932](https://github.com/mandalorianuy/aecctx/actions/runs/29293128932)).

The claim-promotion RED command `python scripts/check_remote_provider_conformance.py --require-public` failed with `AECCTX_REMOTE_CLAIM_INVALID` while the registry remained `target`. The acceptance transition promotes only the exact bounded claim after the complete evidence bundle.

## Delivery authority correction

The repository owner confirmed GitHub, not OneDev, is the delivery authority for AECCTX. The configured `origin` and authenticated `gh` account are therefore the accepted publication path. GitHub reports that `main` has no branch protection and the repository has no rulesets, so zero external approvals are required; a non-draft PR, explicit diff/check review, successful CI and squash merge remain mandatory evidence.

Acceptance transition commit `d7097cd` is delivered by non-draft [GitHub PR #1](https://github.com/mandalorianuy/aecctx/pull/1). The PR diff, exact-head checks and squash result are the delivery record; no direct-main or alternate-platform bypass is permitted.

The acceptance transition is authoritative only after its non-draft GitHub PR passes review/checks and is squash-merged. The resulting public claim is `sandbox.remote-provider`, support level `partial`, for `remote-https-spki-v1` on Python 3.12 Linux/macOS/Windows. ACX-27 alone is promoted to `pending-next` and is not executed by this task.

## Fixtures and conformance claims

- `v03-remote-provider` is project-authored Apache-2.0 fixture evidence under `fixtures/v0.3/remote-providers/`.
- `conformance/v0.3/remote-provider-corpus.json` binds the profile, six test cases and nine normative/source fixture hashes.
- The corpus checker requires 16 adversarial cases, byte-identical fixture regeneration, schema mirror equality, credential/key/native-binary absence and exact public claim lifecycle.
- Live loopback and replay are evidence for protocol behavior only; replay is never counted as third-party service availability.

## Security, privacy, licensing and platform review

- Optional `cryptography>=45,<50` is Apache-2.0 OR BSD-3-Clause and remains outside core dependencies.
- No credential, private key, native provider, GPL/commercial decoder or service SDK is distributed in wheel/sdist.
- SPKI verification precedes credential/source transmission; policy denial precedes DNS/socket creation.
- The accepted platform scope is Python 3.12 on Linux, macOS and Windows as proven by exact-SHA GitHub CI.
- `/Users/facundo/desarrollo/woodframing` was not modified.

## Residual non-claims

No third-party service availability/SLA, provider-side sandbox/deletion, jurisdictional compliance, billing accuracy, entitlement, semantic correctness, general Web PKI lifecycle, discovery, OAuth, mTLS, streaming or consumer approval is claimed. These boundaries are normative in `docs/specs/provider-remote-v03-profile.md` and ACXD-034.
