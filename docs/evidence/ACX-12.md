# ACX-12 acceptance evidence

Date: 2026-07-11
Task: External sandbox/provider foundation
Decision: ACXD-024
Claim: `sandbox.external-provider`, `partial` across the roadmap and bounded to `oci-docker-v1` on `linux-container` with `org.aecctx.reference-provider@0.2.0`

## Implemented

- Public v0.2 provider descriptor, request and response/attestation schemas, mirrored in package data.
- Allowlisted provider registry with no caller-supplied command, import, callback, environment or output path.
- Deterministic content-addressed request/staging, private workspace, normalized environment and validated/captured output.
- Digest-pinned `oci-docker-v1` profile with no implicit pull/build, no network, read-only root, non-root user, dropped capabilities, `no-new-privileges`, one process, resource limits, private temporary storage and timeout cleanup.
- Structured response validation for attestation/runtime digest, capability/loss, event sequence, artifact containment/symlink/size/hash and host-path leakage.
- Publishable reference provider, portable replay corpus, threat model and provider security/license/privacy review template.
- Explicit `macos-seatbelt-v1` rejection and governed ACXB-001 backlog for additional native/Windows profiles.

## TDD and conformance

RED/GREEN cycles covered public contract presence, complete enforcement axes, registry allowlisting, deterministic request identity, unsafe configuration rejection, response/attestation validation, bounds, path/hash abuse, unavailable profiles, OCI flags, live round trip, network/filesystem denial, timeout cleanup, hostile output and cgroup memory enforcement.

The committed replay corpus validates on every supported CI host without Docker. Live OCI tests run only when the exact digest-pinned image is already installed; a missing runtime is an explicit skipped environment for those tests and an execution rejection in production, not evidence for another platform claim.

## Validation evidence

- `./scripts/verify_portable.sh`: passed; `145 passed`; claim registry and provider replay passed; wheel and sdist built successfully.
- `pytest tests/test_external_providers.py tests/test_package_data.py tests/test_claim_registry.py -q`: `41 passed`, including live OCI round trip, network/filesystem denial, timeout cleanup, hostile-output rejection and cgroup memory enforcement because the exact pinned image was present locally.
- `python scripts/check_spec_contract.py`: passed.
- `validate_claim_registry_file("conformance/v0.2/claims.json")`: valid with no errors.
- `validate_provider_replay_corpus("conformance/v0.2/provider-corpus.json")`: one valid deterministic entry and artifact.
- `./scripts/verify.sh`: passed; `145 passed`; portable build gates, baseline integration (`healthy issues=0`), deterministic v0.1 corpus and release verification all passed.

## Promotion

ACX-12 is complete and ACX-13 is promoted to `pending-next`. ACX-13 has not been executed.

## Residuals and non-claims

- ACXB-001 governs native Linux/macOS and Windows enforcement profiles; they remain `unsupported`.
- This milestone does not claim DWG, RVT, STEP/IGES, OCR/vision, network-provider, signing/authenticity or consumer integration.
- Image digest and protocol attestation provide integrity/binding, not publisher authenticity, trust or authorization.
- A provider descriptor, Docker installation/image pull, skipped live test, documentation or scaffolding alone does not count as capability evidence.
