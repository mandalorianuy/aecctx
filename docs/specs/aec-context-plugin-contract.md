# AECCTX Extractor Plugin Contract

Version: `0.1.0`
Date: 2026-07-11
Status: Stable v0.1 normative contract

## 1. Purpose

Plugins convert untrusted source bytes into AECCTX evidence and optional neutral records. The core orchestrates plugins but does not require every decoder to share its language, license, process, or distribution.

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, and MAY are normative.

## 2. Lifecycle

A plugin implements:

1. `describe`: return identity, version, license, execution mode and declared capabilities.
2. `probe`: inspect a bounded prefix/metadata set and return format candidates without mutation.
3. `extract`: stream source data into evidence/artifact events.
4. `finalize`: return capability, loss, sanitization, timing and resource reports.
5. Optional `render`: create derived previews with explicit source record references.

An implementation MAY expose this lifecycle in-process for compatible permissive libraries. Native, GPL, commercial, network-backed, or higher-risk plugins SHOULD run in isolated processes.

## 3. Descriptor

Every plugin descriptor MUST contain:

- stable `plugin_id` and semantic `plugin_version`;
- implementation/runtime version;
- license identifier and distribution posture;
- supported media types/extensions as hints, never sole detection proof;
- input and output capabilities;
- local/network execution mode;
- deterministic mode declaration;
- resource-limit support;
- parser/geometry engine versions where applicable.

## 4. Event envelope

Extraction emits ordered events with:

- `event_version`;
- `event_type`;
- `source_id`;
- plugin-local sequence number;
- stable source locator;
- payload or artifact reference;
- extraction confidence and method;
- diagnostics and parent references.

Allowed v0.1 event types are `container`, `primitive`, `assertion`, `entity`, `relation`, `artifact`, `diagnostic`, and `unsupported`.

Plugins MUST emit source evidence before a normalized record references it. They MUST NOT emit consumer decisions or accepted engineering claims.

## 5. Capability and loss report

Finalization MUST report `full`, `partial`, `opaque`, or `unsupported` for:

- identity;
- hierarchy/containers;
- properties;
- relationships;
- text/annotations;
- 2D geometry;
- 3D geometry;
- materials/styles;
- georeferencing;
- validation.

Every non-`full` result MUST include stable reason codes, affected locators or counts when knowable, and recommended fallbacks. Warnings alone cannot replace the structured report.

## 6. Determinism

Given identical bytes, configuration, plugin/runtime versions, platform-normalized settings, and no declared external provider, a deterministic plugin MUST emit semantically identical records and artifact hashes. Ordering differences are normalized by the core.

Network or inference-backed plugins MUST declare non-deterministic inputs and record provider, model/service version, request policy, timestamps, and response hashes.

## 7. Safety

Plugins MUST treat inputs as data and MUST NOT execute embedded macros, scripts, links, commands, extensions, or callbacks. The core supplies limits for bytes, records, nesting, decompression ratio, wall time, CPU time and memory. A plugin that cannot honor a required limit MUST be isolated or rejected.

Paths emitted by plugins are logical POSIX package paths. Absolute paths, `..`, device paths and symlink escapes are invalid.

## 8. Failure behavior

Fatal plugin failure does not erase registered source identity or prior emitted diagnostics. The core records the session as failed and MUST NOT present partial records as complete. Recoverable unsupported content is emitted as `unsupported` evidence and reflected in the loss report.

## 9. Compatibility

The core negotiates contract major/minor versions. A major mismatch is rejected. Unknown optional fields are retained or ignored according to their schema extension policy; unknown required event types are rejected.
