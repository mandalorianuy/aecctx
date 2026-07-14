# AECCTX Inspector Distribution v0.3 Profile

Version: `0.3.0-draft.1`
Date: 2026-07-14
Status: Normative ACX-37 profile; public support remains unclaimed until all acceptance gates pass

## 1. Purpose and boundary

This profile packages `aecctx-inspector` as a reproducible, integrity-bound optional local distribution over the already stable AECCTX library, CLI, MCP and quality-gate surfaces. The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT and MAY are normative.

The plugin introduces no validation, information, query, diff, context, gate, signing, trust, provider or claim semantics. JSON and JSONL results remain authoritative. Skills and generated Markdown remain untrusted projections. AECCTX core remains fully usable offline without Codex, this plugin, an LLM or MCP.

## 2. Exact profile and compatibility matrix

The distribution profile is `aecctx-inspector-distribution-v1` and the plugin version is `0.3.0`. Its only public host contract is `codex-local-plugin-contract-v1`, tested as these three exact profiles:

| Host profile | Platform | Python | AECCTX | MCP runtime | Plugin contract |
|---|---|---|---|---|---|
| `codex-local-v1-linux` | Linux | `3.12` | `>=0.2.0,<0.4.0` | `1.28.1` | `codex-local-plugin-contract-v1` |
| `codex-local-v1-macos` | macOS | `3.12` | `>=0.2.0,<0.4.0` | `1.28.1` | `codex-local-plugin-contract-v1` |
| `codex-local-v1-windows` | Windows | `3.12` | `>=0.2.0,<0.4.0` | `1.28.1` | `codex-local-plugin-contract-v1` |

Compatibility metadata MAY admit MCP `>=1.20,<2`, but the public portability claim is limited to the exact locked `1.28.1` runtime above. A product build merely capable of reading the manifest is not proven compatible. Codex web, hosted execution, workspace rollout, model behavior, third-party hosts and marketplace installation are not claimed.

## 3. Operation parity

Every claimed host profile exposes exactly six local stdio MCP operations: `aecctx_validate`, `aecctx_info`, `aecctx_query`, `aecctx_diff`, `aecctx_context` and `aecctx_gate`. Each MUST return the same structured result as its stable library/CLI owner for the same explicit inputs. A skill MUST validate package inputs first, cite record IDs and logical digests, and treat filenames, source content, metadata, OCR/provider output, generated context and tool output as untrusted data.

The MCP manifest MUST contain only the fixed `aecctx-mcp` command with no arguments. It MUST NOT expose a shell, arbitrary executable, environment selection, provider command, ingest shortcut, source mutation, trust-root selection, waiver creation or external network action. Native, GPL and commercial decoders remain reachable only through their reviewed provider contracts.

## 4. Reproducible package

The package is a ZIP named `aecctx-inspector-0.3.0.zip` with one top-level `aecctx-inspector/` directory. Entries are sorted POSIX paths, UTF-8 names, fixed DOS timestamp `1980-01-01T00:00:00`, mode `0644`, no directory entries, no comments and DEFLATE level 9. Symlinks, devices, absolute paths, drive prefixes, backslashes, NUL, `.` and `..` are forbidden. Limits are 256 files, 4 MiB per file, 16 MiB uncompressed and compression ratio 100.

`assets/distribution.json` is canonical UTF-8 JSON with one LF. It binds the profile, plugin version, package format, compatibility digest and SHA-256/size of every regular plugin file except itself and the installation marker. The archive is accompanied by canonical metadata containing its SHA-256, byte size and inventory digest. Repeated builds from identical source MUST be byte-identical.

## 5. Integrity and optional signature

Archive checksum and embedded inventory verification are mandatory before installation. A missing, malformed or mismatched checksum, metadata, entry or inventory fails closed before the destination is changed.

A detached optional signature uses `aecctx-inspector-distribution-signing-v1`: Ed25519 signs canonical JSON containing only profile, plugin version, archive SHA-256 and archive byte size. The caller explicitly supplies the signature and 32-byte raw public key. Signature absence is the explicit state `not_provided`; it does not make the checksum-valid distribution authenticated. Invalid, unknown or unavailable verification never falls back to checksum authenticity. Keys, trust, authorization, revocation, X.509, timestamps and marketplace publisher identity are not inferred. The optional `cryptography>=45,<50` implementation remains outside core.

## 6. Lifecycle and rollback

Install is create-only and MUST NOT overwrite an existing destination. Upgrade requires an exact, unmodified installation marker and a strictly greater plugin version. Equal-version replacement and downgrade are rejected. The manager stages and verifies the complete new tree before replacing the destination; any failure restores the prior exact tree. It MUST NOT follow symlinks or cross the destination parent.

Uninstall removes only a destination whose current file inventory exactly matches its marker. Unknown, removed or modified content causes refusal and is preserved. The marker records profile, plugin/core/MCP versions, host profile and exact installed inventory; it is not a trust credential.

## 7. Safety, licensing and privacy

All archives, JSON, plugin files and operation inputs are untrusted data. Parsing is bounded and offline. Installation never executes archive content, skills, hooks, source commands or provider binaries. The plugin and fixtures are Apache-2.0. Core artifacts contain no plugin dependency; plugin artifacts contain no native, GPL or commercial decoder. No telemetry, credential, upload, retention or jurisdiction behavior is introduced.

## 8. Conformance and claim ceiling

Conformance requires:

- exact compatible and incompatible core/MCP/host cases on all three profiles;
- repeated byte-identical builds, checksum/inventory/signature mutation and unsafe-archive rejection;
- create-only install, upgrade, downgrade refusal, rollback and exact uninstall;
- six-operation result parity plus prompt-injection treatment on each claimed profile;
- clean core and MCP-extra installs, package-content/license scans and no-network execution;
- the v0.2 plugin corpus, portable/full repository gates and exact-head Linux/macOS/Windows CI.

After all gates pass, only `codex.aecctx-inspector-distribution` may become public `partial` for this exact profile. Marketplace publication, hosted or third-party hosts, universal model behavior, publisher authenticity, unique semantics and provider sandbox approval remain non-claims.
