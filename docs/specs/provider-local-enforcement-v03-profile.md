# AECCTX Local Provider Enforcement v0.3 Profile

Version: `0.3.0-draft.1`
Date: 2026-07-13
Status: Normative ACX-25 implementation profile
Decision authority: ACXD-033

## 1. Purpose and claim boundary

This profile defines the machine-readable evaluation and fail-closed execution boundary for restricted providers on native Linux, macOS and Windows hosts. It does not change the accepted `oci-docker-v1` or `sandbox.oci-multiarch` claims.

The ACX-25 claim ID is `sandbox.local-enforcement`. Its support ceiling is independently `partial` for a platform profile that passes every required axis, or public `unsupported` with executable rejection evidence when any required axis is unavailable. A profile declaration, host operating-system name or portable replay is not enforcement evidence.

No native platform profile is accepted by draft 1. The implemented result MUST reject before workspace creation or provider launch and MUST return the complete deterministic report defined below.

## 2. Required axes

Every report contains exactly the ACX-12 axes:

- `cpu`, `decompression`, `environment`, `filesystem`;
- `input_bytes`, `memory`, `network`, `open_files`;
- `output_bytes`, `process`, `process_tree`, `records`;
- `recursion`, `temporary_storage`, `user_permissions`, `wall_time`.

Each axis is `enforced` or `unavailable`. `executable` is true if and only if every axis is `enforced`. An unavailable report has one or more stable diagnostics and MUST NOT be passed to a best-effort launcher.

The content/protocol axes `decompression`, `input_bytes`, `output_bytes`, `records`, `recursion` and `wall_time` remain enforceable by the existing parent contract. They do not compensate for an unavailable native operating-system axis.

## 3. Machine-readable report

```python
@dataclass(frozen=True, slots=True)
class LocalEnforcementReport:
    profile_id: str
    platform: str
    axes: Mapping[str, Literal["enforced", "unavailable"]]
    executable: bool
    diagnostics: tuple[str, ...]
```

Canonical JSON sorts axis keys and diagnostics and contains no host path, username, timestamp, kernel build, environment value or mutable availability probe. Reports are profile decisions, not provider self-attestations.

The reviewed profile IDs and normalized platform IDs are:

| Platform | Profile | ACX-25 result |
|---|---|---|
| native Linux | `linux-native-v1` | `unsupported` |
| native macOS | `macos-app-sandbox-v1` | `unsupported` |
| native Windows | `windows-appcontainer-job-v1` | `unsupported` |

Unknown platform/profile IDs fail with `AECCTX_PROVIDER_PLATFORM_UNSUPPORTED` and cannot select a fallback.

## 4. Linux decision

Linux Landlock is an unprivileged filesystem/network access-control component and cgroup v2 supplies resource controllers, but the complete profile additionally needs reviewed namespace, process-tree, cgroup-delegation, user/permission, environment, file-descriptor and cleanup supervision. The repository has no pinned supervisor with a portable unprivileged delegation contract or hosted-CI runtime proof.

`linux-native-v1` therefore marks the six parent content/protocol axes `enforced` and every remaining axis `unavailable`, with diagnostic `AECCTX_LOCAL_LINUX_SUPERVISOR_UNAVAILABLE`. Landlock, cgroup files, namespaces, `setrlimit`, seccomp or a descriptor declaration used individually MUST NOT make the profile executable.

Official API references:

- Linux Landlock userspace API: <https://docs.kernel.org/userspace-api/landlock.html>
- Linux cgroup v2: <https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html>

## 5. macOS decision

Apple App Sandbox is an entitlement/code-signing model for a containing application and inherited helper; it is not a caller-selected arbitrary decoder launcher. The legacy `sandbox-exec` route is deprecated. Neither route supplies the complete ACX-12 aggregate CPU, memory, process-tree and cleanup contract for an arbitrary provider invocation in the current Python distribution.

`macos-app-sandbox-v1` therefore marks only the six parent content/protocol axes `enforced`; all other axes are `unavailable`, with diagnostics `AECCTX_LOCAL_MACOS_SIGNED_HOST_REQUIRED` and `AECCTX_LOCAL_MACOS_RESOURCE_SUPERVISOR_UNAVAILABLE`. The legacy `MacOSSeatbeltProfile` remains fail-closed.

Official API references:

- Apple App Sandbox: <https://developer.apple.com/documentation/security/app-sandbox>
- App Sandbox inheritance: <https://developer.apple.com/library/archive/documentation/Miscellaneous/Reference/EntitlementKeyReference/Chapters/EnablingAppSandbox.html>

## 6. Windows decision

AppContainer/LPAC provides token, filesystem, credential, process and network isolation. Job Objects provide process-tree management and CPU/memory/process limits. A complete profile requires a reviewed native broker that creates the profile and DACLs, launches suspended with the exact security capabilities, assigns a non-breakaway kill-on-close job before execution, monitors limits and deletes profile/workspace state. The Apache-2.0 Python distribution contains no such broker and hosted CI has no accepted exact broker/runtime fixture.

`windows-appcontainer-job-v1` therefore marks only the six parent content/protocol axes `enforced`; all other axes are `unavailable`, with diagnostic `AECCTX_LOCAL_WINDOWS_BROKER_UNAVAILABLE`. AppContainer, Job Objects or subprocess limits used separately MUST NOT make the profile executable.

Official API references:

- AppContainer isolation and launch: <https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation> and <https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer>
- Job Objects: <https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects>

## 7. Execution and diagnostics

`LocalProviderProfile.preflight()` evaluates its immutable report before `ProviderRunner` constructs a request, creates a temporary workspace or launches a process. Any unavailable axis raises `AECCTX_PROVIDER_PROFILE_UNAVAILABLE` and includes the canonical report as machine-readable error details.

`launch()` is unreachable for all draft-1 profiles and repeats the same fail-closed error if called directly. `terminate()` and `memory_bytes()` MUST NOT create a false enforcement claim.

## 8. Fixtures and conformance

`fixtures/v0.3/local-providers/adversarial-cases.json` enumerates filesystem escape, environment disclosure, network access, child-process tree, CPU/memory exhaustion, timeout, output overflow and cleanup attacks. Because no profile is executable, conformance proves that each profile rejects before any attack worker or workspace can run.

`conformance/v0.3/local-enforcement-corpus.json` binds the fixture hash and exact expected reports. The checker MUST prove:

- all 16 axes occur exactly once in every report;
- executable state is derived from the axes;
- reports and serialized error details are deterministic;
- all three profiles reject before provider launch/workspace creation;
- unknown profiles reject without fallback;
- the wheel and sdist contain no native broker, restricted decoder binary or new restricted dependency.

Success/adversarial provider execution is required only after a future profile decision makes one platform executable. Rejection evidence cannot be presented as successful sandbox execution.

## 9. Licensing, privacy and provider boundary

This profile adds no dependency or binary. It does not distribute Landlock/cgroup helpers, Apple-signed hosts, Windows brokers, GPL decoders or commercial SDKs. No source bytes leave the host and no credential, entitlement, telemetry, retention or jurisdiction claim is introduced.

A GPL or commercial decoder remains separately subject to its own accepted license, entitlement and redistribution profile even after a future local enforcement profile passes.

## 10. Reopening requirements and non-claims

A platform may move from `unsupported` only through a new accepted decision that pins the supervisor/broker/runtime, documents its license and security lifecycle, publishes legally usable build inputs, and passes live success plus every adversarial axis on the exact claimed platform.

This profile does not claim:

- native restricted-provider execution on Linux, macOS or Windows;
- Windows containers, App Store/App Sandbox host distribution or a generic command sandbox;
- equivalence between native profiles and `oci-docker-v1`;
- execution availability from a descriptor or operating-system feature probe;
- provider entitlement, semantic correctness, trust, signing or consumer approval.
