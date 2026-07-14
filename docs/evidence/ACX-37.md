# ACX-37 Inspector Distribution and Host Portability Evidence

Date: 2026-07-14
Status: Accepted locally; exact-head CI and merge evidence are recorded at delivery closeout

## Governed result

ACXD-046 and `docs/specs/inspector-distribution-v03-profile.md` select only `aecctx-inspector-distribution-v1`: a deterministic local ZIP for `codex-local-plugin-contract-v1` on Python 3.12 Linux, macOS and Windows, AECCTX `>=0.2.0,<0.4.0`, and exact claimed MCP `1.28.1`.

Only `codex.aecctx-inspector-distribution` may be public `partial`. Marketplace publication, hosted/product-build or third-party host compatibility, universal model behavior, publisher trust, unique semantics, network action and provider shell execution remain non-claims.

## Functional evidence

- The archive has a single top-level plugin directory, sorted fixed-metadata entries, canonical embedded inventory and mandatory SHA-256. Repeated builds are byte-identical.
- Optional Ed25519 archive signatures bind a closed canonical statement and explicit caller key; absence remains `not_provided`, and mutation fails closed.
- Verified archive installation operates on the same checksum-bound bytes. Install is create-only, upgrade is strictly increasing and staged, staging failure preserves the installed tree, downgrade/equal replacement are rejected, and uninstall requires exact inventory.
- The only MCP command is local `aecctx-mcp` stdio. Validate, info, query, diff, context and gate results match their stable library owners for every claimed host profile.
- Prompt-like source/plugin content remains untrusted data. No plugin file exposes a shell, provider binary, restricted decoder, consumer mapping, trust-root selection, waiver creation or source mutation.
- The Apache-2.0 core wheel has no plugin dependency; the optional distribution remains in the sdist/repository surface only.

## Fixtures and conformance

- `fixtures/v0.3/plugin/host-matrix.json` fixes the three host profiles and runtime versions.
- `fixtures/v0.3/plugin/adversarial-cases.json` covers traversal, symlink, checksum, inventory, signature, downgrade, prompt injection and provider-shell denial.
- `fixtures/v0.3/plugin/lifecycle-cases.json` covers install, collision, upgrade, rollback, equal/downgrade refusal and exact/modified uninstall.
- `conformance/v0.3/plugin-corpus.json` binds the profile, claim, six operations, inventories, fixtures, scripts and tests by SHA-256.

## Validation evidence

Focused checks passed, and the portable gate passed its 311-test focused suite plus the complete 821-test suite with 13 intentional skips, deterministic fixture regeneration, wheel/sdist build and artifact scans. Exact-head GitHub Actions URLs are added after delivery. The required gate set is:

```text
python scripts/check_spec_contract.py
python scripts/check_codex_plugin.py
python scripts/check_codex_plugin_conformance.py
python scripts/build_inspector_distribution.py --check
python scripts/check_inspector_v03_conformance.py --require-public
python -m pytest tests/test_codex_plugin_v03.py tests/test_codex_plugin.py tests/test_codex_plugin_conformance.py tests/test_mcp_server.py tests/test_package_data.py tests/test_claim_registry.py tests/test_v03_claim_registry.py -q
./scripts/verify.sh
```

## Residual risk

- The claim verifies the local plugin contract and exact locked MCP runtime, not any Codex product release or marketplace lifecycle.
- Optional raw-key signatures prove only cryptographic validity for an explicitly supplied key; they do not prove publisher identity, authorization, revocation, trusted time or marketplace authenticity.
- Skills influence orchestration but cannot guarantee universal model behavior. Structured library/CLI/MCP results remain authority.
- Native, GPL and commercial decoders still require their separately reviewed external provider sandboxes.

WoodFraming was not modified and no consumer semantics were added.
