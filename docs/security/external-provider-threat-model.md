# External provider threat model

Date: 2026-07-11
Decision: ACXD-024
Claimed profile: `oci-docker-v1` on a Linux container runtime

## Assets and trust boundaries

The parent/core owns source bytes, package identity, configuration, limits, schemas and the final decision to admit output. The Docker daemon and reviewed digest-pinned runtime are trusted enforcement dependencies. Provider code, source content, decoder libraries, emitted JSON, diagnostics and artifacts are untrusted.

The boundary is:

`untrusted source -> private content-addressed input -> isolated provider -> bounded output -> parent schema/hash/semantic validation -> package construction`

No provider output reaches package construction before validation. Markdown remains downstream generated projection and is never an authority.

## Threats and enforced controls

| Threat | Control | Conformance evidence |
|---|---|---|
| Caller command, import, callback or environment injection | allowlisted `provider_id`; immutable registration target; unsafe configuration keys and host paths rejected | registry/configuration tests |
| Source-triggered command, macro, link or extension execution | no shell; input mounted as data; reference provider performs no active-content dispatch | command construction and protocol tests |
| Input substitution | SHA-256 content address, declared byte count and deterministic request digest | request and replay-corpus tests |
| Host filesystem read/write or privilege escalation | read-only root, non-root UID/GID, all capabilities dropped, `no-new-privileges`, only output mount writable | OCI command test and outside-write adversarial test |
| Network exfiltration | `--network=none`; descriptor/attestation must say `disabled` | live socket-denial test |
| Process or fork bomb | one-PID cgroup limit and complete container removal on timeout | OCI command and timeout cleanup tests |
| CPU, memory, wall, open-file or output exhaustion | Docker CPU/memory/PID limits, wall watchdog, `nofile`/`fsize`, parent byte/file/record bounds | live memory/timeout tests and bounded-protocol tests |
| Decompression/entity/recursion explosion | request limits are provider-visible; parent limits input, configuration recursion, records, files and output; adapter-specific decompression proof remains mandatory | request/response limit tests; provider review gate |
| Traversal, absolute path, symlink or forged artifact | relative `artifacts/` paths only; resolved workspace containment; symlink prohibition; byte count and SHA-256 validation | hostile-output tests |
| Reordered/duplicate/fabricated events | JSON Schema, strict sequence and bounded count | protocol and live hostile-output tests |
| Runtime or descriptor substitution | provider descriptor digest plus digest-pinned runtime image recorded in attestation; image must already exist locally and is never implicitly pulled | preflight, attestation and replay tests |
| Wrong-architecture or substituted local image | exact `OCIRuntimeTarget`; Docker image ID, OS and architecture inspection; no implicit pull/build | ACX-24 selector tests and six-target live corpus |
| Host path or environment disclosure | private workspace, normalized client environment, no host environment passed to container, output host-path rejection | host-path tests |
| Partial/fatal extraction disguised as full | every response carries structured capability/loss; non-full entries require reasons and fallback; error response stays explicit | protocol tests and reference replay |

## Profile preconditions and rejection

`oci-docker-v1` is available only when the Docker executable reaches a Linux server and the exact registered image digest already exists. The runner never pulls or builds an image. The image is mounted with reviewed provider code read-only, private input/request mounts read-only, a private writable output mount and bounded `tmpfs`.

ACXD-033 evaluates three native profiles against the same complete 16-axis contract. None is admissible in ACX-25 draft 1:

- `linux-native-v1` lacks a reviewed pinned unprivileged supervisor/delegation contract spanning Landlock/cgroup controls and the remaining process, resource and cleanup axes;
- `macos-app-sandbox-v1` requires a signed entitlement-bearing host/helper and still lacks the aggregate resource supervisor; the legacy `macos-seatbelt-v1` path remains fail-closed;
- `windows-appcontainer-job-v1` lacks a reviewed broker for AppContainer profile/DACL creation, pre-execution Job Object assignment, monitoring and cleanup.

Each profile emits a deterministic `LocalEnforcementReport` with every axis and rejects with `AECCTX_PROVIDER_PROFILE_UNAVAILABLE` before workspace creation or provider launch. The wheel/sdist contain no native broker or restricted decoder. This executable rejection is public `unsupported` evidence after ACX-25 acceptance; it is not successful sandbox execution and does not change the positive `oci-docker-v1` claims.

## Residual trust and operational risk

- A compromised Docker daemon or host kernel is outside the boundary; this profile is not a VM security claim.
- Image-digest pinning proves selected bytes, not publisher identity or authorization. Signing remains ACX-20.
- CPU allocation is bounded by Docker quota and wall timeout; the response's self-reported resource usage remains untrusted metadata.
- Decompression behavior is decoder-specific. A future decoder must prove its configured ratio/entity limits in its own corpus before a claim is public.
- Commercial entitlement, privacy, telemetry, retention and jurisdiction are provider-specific and must pass the review template below.
- Native Linux/macOS/Windows execution remains unsupported after ACX-25. ACX-26 admits only the optional `remote-https-spki-v1` protocol: an explicitly registered HTTPS origin and SPKI pin, per-call upload/billing/region/retention/telemetry policy, direct no-proxy transport, credential injection only after pin verification, bounded canonical bodies, terminal redirect/auth/identity failures and deterministic retry/replay. The remote service and decoder remain outside the trust boundary; provider-side isolation, deletion, availability, jurisdiction, billing and semantics are not claimed. Emulation is evidence only for the inspected Linux image architecture.
