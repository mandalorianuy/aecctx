# ACX-25 acceptance evidence

Status: accepted and completed.

ACX-25 is governed by `docs/specs/provider-local-enforcement-v03-profile.md` and ACXD-033. It evaluates native Linux, macOS and Windows independently against the complete ACX-12 enforcement contract.

## Implemented result

- Public immutable `LocalEnforcementReport` and fail-closed `LocalProviderProfile` APIs.
- Exact reports for `linux-native-v1`, `macos-app-sandbox-v1` and `windows-appcontainer-job-v1`, each containing all 16 required axes.
- Stable machine diagnostics and rejection through `AECCTX_PROVIDER_PROFILE_UNAVAILABLE` before request construction, workspace creation or provider launch.
- Legacy `MacOSSeatbeltProfile` delegates to the governed macOS rejection and cannot become a best-effort bypass.
- Digest-bound project-authored ten-case adversarial corpus and deterministic conformance checker.
- Portable packaging gate that requires the report module and rejects native `.dll`, `.dylib`, `.exe` or `.so` artifacts from wheel/sdist.

## Claim boundary

`sandbox.local-enforcement` is public `unsupported` for native Linux, macOS and Windows. No native profile is executable, and rejection evidence is not successful sandbox execution. The existing positive `oci-docker-v1` and `sandbox.oci-multiarch` claims are unchanged.

Linux still requires a reviewed pinned unprivileged supervisor/delegation contract. macOS requires a signed entitlement-bearing host/helper plus aggregate resource supervision. Windows requires a reviewed AppContainer/Job Object broker and lifecycle. Each reopening requires a new decision and exact-platform live success plus the complete adversarial suite.

## Validation evidence

- TDD RED 1: 13 focused tests failed before `LocalEnforcementReport`, `LocalProviderProfile`, deterministic reports and structured error details existed.
- TDD RED 2: corpus and distribution tests failed before the digest-bound checker and restricted-artifact scan existed.
- Claim-promotion RED: the corpus test expected `public` while the registry still returned `target`; promotion occurred only after local artifacts and exact-SHA three-platform CI passed.
- Focused GREEN: `pytest tests/test_local_provider_profiles.py tests/test_external_providers.py -q` passed 48 tests.
- Corpus GREEN: `scripts/check_local_enforcement_conformance.py` returned `{"attack_cases":10,"claim_status":"public","ok":true,"profiles":3}` after promotion.
- Packaging: wheel and sdist contained `aecctx/providers/local.py` and no forbidden native broker or restricted decoder artifact.
- Portable/full local gates: 655 tests passed with 10 intentional skips; wheel/sdist, release verification and baseline integration passed under `./scripts/verify.sh`.
- Candidate commit `24b63bdef116d7e3bd1ed1d4f980a02a7abc9d13` passed [CI run 29289903480](https://github.com/mandalorianuy/aecctx/actions/runs/29289903480) on Ubuntu, macOS and Windows.

## Security, licensing and privacy

No native helper, broker, decoder, GPL/commercial payload or dependency was added. No source data leaves the host, and no credential, entitlement, telemetry, retention or jurisdiction claim is introduced. GPL/commercial decoder review remains independent of local enforcement.

## Residuals and next task

Native restricted-provider execution remains unsupported on all three evaluated platforms. OCI remains the only positive restricted-provider execution profile. ACX-26 alone is promoted to `pending-next` because an optional remote/customer-managed provider protocol is the next dependency in the accepted plan. ACX-26 was not executed.

`/Users/facundo/desarrollo/woodframing` was not modified.
