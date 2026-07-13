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

`macos-seatbelt-v1` is rejected with `AECCTX_PROVIDER_PROFILE_UNAVAILABLE`. The attempted profile could not both execute the Python runtime without broad host reads and prove a hard memory limit. A native subprocess with partial limits is not an acceptable fallback.

Native Linux/macOS and Windows profiles are governed by ACXB-001 and remain unsupported. The current public claim is therefore `partial` across the expansion target and `full` only for the exact `oci-docker-v1` Linux-container/reference-provider combination.

## Residual trust and operational risk

- A compromised Docker daemon or host kernel is outside the boundary; this profile is not a VM security claim.
- Image-digest pinning proves selected bytes, not publisher identity or authorization. Signing remains ACX-20.
- CPU allocation is bounded by Docker quota and wall timeout; the response's self-reported resource usage remains untrusted metadata.
- Decompression behavior is decoder-specific. A future decoder must prove its configured ratio/entity limits in its own corpus before a claim is public.
- Commercial entitlement, privacy, telemetry, retention and jurisdiction are provider-specific and must pass the review template below.
- Native macOS/Windows execution, unreviewed architectures and remote runtimes remain unsupported after ACX-24; emulation is evidence only for the inspected Linux image architecture.
