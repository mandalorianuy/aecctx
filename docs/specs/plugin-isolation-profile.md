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
