# AECCTX v0.1 Plugin Isolation Profile

Version: `0.1.0`
Date: 2026-07-11
Status: Normative reference implementation profile

## Registration and protocol

- Only allowlisted plugin IDs resolve to installed module/class targets; callers cannot submit import paths.
- The parent and worker exchange one bounded JSON request/response over stdin/stdout.
- Actions are limited to `describe`, `probe`, `extract`, `finalize`, and optional `render`.
- Worker output is captured to files before parsing so a plugin cannot force unbounded parent stdout buffering.

## Process policy

- Every run receives a private temporary working directory, HOME and TMPDIR; deterministic locale/hash settings; no shell; and a new process session.
- The Python worker replaces socket creation/connection with a deterministic denial before loading plugins. Adapters must also declare `network_mode=disabled`.
- Wall timeout terminates the complete process group.
- POSIX workers apply CPU, address-space, open-file and output-file limits. Input bytes, output bytes and emitted records are checked independently by the protocol.
- Platforms that cannot enforce a required resource axis must reject the plugin or use a reviewed operating-system sandbox provider.

## External plugin boundary

The built-in runner accepts only reviewed Python adapters. Native, GPL, commercial or network-backed decoders are not admitted merely by supplying a command. They require a separately reviewed sandbox/provider contract that enforces equivalent limits and declares licensing, network, determinism and loss behavior.

## v0.2 external provider profile

ACXD-024 defines a content-addressed JSON file protocol and allowlisted provider registry. The caller supplies a provider ID, action, input bytes and bounded configuration; it never supplies a command, import path, callback, environment override or output path.

The initial executable profile is `oci-docker-v1`. It MUST use an allowlisted digest-pinned image already present locally; disable network; use a read-only root filesystem, non-root user, dropped capabilities and `no-new-privileges`; bound memory, CPU, PIDs, open files and output; mount content-addressed input and provider code read-only; mount only the bounded output writable; terminate the container on timeout; and validate all returned paths/hashes/events before use. The runner MUST NOT pull or build images implicitly.

`macos-seatbelt-v1` is not an admissible restricted-decoder profile: current macOS enforcement cannot both run the Python reference provider without broad host reads and prove the required memory axis. It MUST reject rather than fall back.

The profile is unavailable when any required enforcement axis cannot be proven. Other hosts MUST reject the run or use a separately reviewed profile; ordinary subprocess isolation is not equivalent.
