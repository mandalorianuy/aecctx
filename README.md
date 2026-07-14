# AECCTX

AECCTX is an open, application-agnostic specification and local-first Python toolchain for compiling CAD, BIM, drawings, meshes, and related AEC files into deterministic context packages that humans, agents, and downstream applications can inspect without silently losing source evidence.

Version **0.1.0** is implemented, packaged and covered by a public conformance corpus.

AECCTX 0.2.0 is the released expansion line. It includes the bounded v0.2 shared schema, reviewed provider boundary, IFC 2D/georeferencing, DXF semantics/3D, experimental English OCR, mesh registration, experimental STEP/IGES and R2000 DWG, optional detached Ed25519 signing, the quality gate and the optional Codex inspector plugin. Claims remain exact and bounded by the aggregate v0.2 corpus.

## Why this exists

AEC formats split information across proprietary files, open schemas, vector drawings, raster documents, geometry, properties, and relationships. Feeding those files directly to an agent is expensive and unreliable; flattening them into a single Markdown file destroys precision and provenance.

AECCTX instead produces a package with:

- immutable source identity and parser provenance;
- extracted evidence with explicit confidence and diagnostics;
- neutral entities and relations without consumer-specific decisions;
- geometry and previews as sidecar artifacts;
- generated, token-budgeted Markdown navigation;
- a mandatory capability and loss report.

## Install

Python 3.12 or newer is required.

```bash
python -m pip install https://github.com/mandalorianuy/aecctx/releases/download/v0.2.0/aecctx-0.2.0-py3-none-any.whl
```

For optional adapters or MCP, install from the tagged source checkout:

```bash
git clone --branch v0.1.0 --depth 1 https://github.com/mandalorianuy/aecctx.git
cd aecctx
python -m pip install '.[all]'
```

The current post-v0.1 source checkout exposes signing as a separate optional dependency boundary:

```bash
python -m pip install '.[signing]'
```

Core validation and unsigned packages do not require the signing extra.

The bounded public delivery-gate profile can be exercised from the current source checkout. IDS evaluation remains optional:

```bash
python -m pip install -e '.[gate-ids]'
```

## Status and authority

- Format specification: [`docs/specs/aec-context-package-spec.md`](docs/specs/aec-context-package-spec.md)
- Plugin contract: [`docs/specs/aec-context-plugin-contract.md`](docs/specs/aec-context-plugin-contract.md)
- Post-v0.1 expansion specification: [`docs/specs/aecctx-capability-expansion-spec.md`](docs/specs/aecctx-capability-expansion-spec.md)
- v0.2 compatibility and migration: [`docs/compatibility-v0.2.md`](docs/compatibility-v0.2.md)
- Capability matrix: [`docs/capability-matrix.md`](docs/capability-matrix.md)
- Active implementation sequence: [`docs/implementation-plan.md`](docs/implementation-plan.md)
- Handoff for the implementation task: [`docs/HANDOFF.md`](docs/HANDOFF.md)

Only the first `pending-next` or `in_progress` task in the implementation plan is executable.
The same plan contains the v0.2 definition of ready/done, specification traceability, file-level deliverables, test matrices and milestone evidence protocol.

## CLI

```bash
aecctx ingest building.ifc --output building.aecctx --form zip --json
aecctx validate building.aecctx --json
aecctx info building.aecctx --json
aecctx query building.aecctx 'entity.original_class == "IfcWall"'
aecctx context building.aecctx --profile agent --token-budget 40000
aecctx diff revision-a.aecctx revision-b.aecctx

# Detached sidecar signing; package bytes are not modified.
aecctx sign building.aecctx --private-key signer.pem --kid project-key-1 \
  --output building.signatures.json
aecctx verify-signatures building.aecctx \
  --signature-bundle building.signatures.json \
  --key-registry registry.json --trust-policy policy.json --json

# Deterministic delivery-gate evaluation. Exit: pass=0, fail/review=1, error=2.
aecctx gate building.aecctx --policy delivery-policy.json --json
aecctx gate building.aecctx --policy delivery-policy.json \
  --baseline previous.aecctx \
  --output gate-result.json \
  --markdown gate-result.md \
  --ci-annotations gate-annotations.jsonl
```

`gate-result.json` is the canonical result. Markdown and provider-neutral JSONL annotations are generated projections only; neither grants engineering approval nor overrides package evidence. Output paths are create-only and inputs are treated as untrusted data. ACX-21 is public `partial` only for `aecctx-gate-v1-ids-1.0-simple-v1` on Python 3.12 Linux/macOS/Windows; unlisted IDS combinations and approval/certification semantics remain unsupported.

Unknown inputs use the honest opaque fallback. IFC, DXF, PDF, image and OBJ/STL/glTF content are selected by bounded content probes; `--adapter` can make the choice explicit.

The ACX-13 through ACX-18 v0.2 profiles are explicit:

```bash
aecctx ingest model.ifc --output model-v02.aecctx --form zip --aecctx-version 0.2.0 --json
aecctx validate model-v02.aecctx --json
aecctx ingest model.dxf --output model-dxf-v02.aecctx --form zip --aecctx-version 0.2.0 --json
aecctx validate model-dxf-v02.aecctx --json
aecctx ingest scan.png --output scan-v02.aecctx --aecctx-version 0.2.0 \
  --inference-replay conformance/v0.2/inference-corpus.json \
  --inference-entry tesseract-ocr-aecctx-15 --json
aecctx ingest model.glb --output model-mesh-v02.aecctx --adapter geometry \
  --aecctx-version 0.2.0 --mesh-coordinate-profile registration.json --json

# Portable STEP/IGES replay; the CLI never launches the native provider.
aecctx ingest model.step --output model-step-v02.aecctx --adapter step-iges \
  --aecctx-version 0.2.0 --provider-replay conformance/v0.2/step-iges-corpus.json \
  --provider-entry ap214-assembly --json

# Portable R13/R14/R2000 DWG replay; the CLI never launches LibreDWG.
aecctx ingest drawing.dwg --output drawing-dwg-v02.aecctx --adapter dwg \
  --aecctx-version 0.2.0 --provider-replay conformance/v0.3/dwg-corpus.json \
  --provider-entry r2000-m-profile --json

# Closed xref bundle: pass one replay entry for each hash-bound DWG member.
aecctx ingest fixtures/v0.3/dwg/xref-bundle --output xref-dwg-v02.aecctx --adapter dwg \
  --aecctx-version 0.2.0 --provider-replay conformance/v0.3/dwg-corpus.json \
  --provider-entry r2000-mm-xref --provider-entry r2000-m-profile --json
```

Other adapters currently reject `--aecctx-version 0.2.0` until their governed expansion task publishes a profile. OCR, STEP/IGES and DWG remain experimental and partial under their normative profiles. STEP/IGES and DWG require a validated replay in CLI or validated `ProviderResult` in SDK. DWG is limited to exact `AC1012`, `AC1014` and `AC1015` profiles; JSON objects are observed decoder evidence while DXF/geometry are converted evidence. Xrefs require a closed hash-bound source bundle and explicit per-member replay. R12, R2004+, ambient traversal, encryption, ACIS/proxy/custom semantics, CRS and complete 3D remain unsupported or non-claims. Mesh registration never guesses units/CRS or rewrites source coordinates. Vision and hidden geometry are not inferred.

Signing accepts valid v0.1/v0.2 directory or ZIP packages and emits a detached JWS General JSON sidecar. Integrity, cryptographic validity, key lifecycle, trust and authorization remain separate fields. A valid signature proves key possession over the governed statement; it does not by itself prove organizational identity, engineering approval or construction readiness.

ACX-35 adds the exact optional `aecctx-x509-ed25519-crl-time-v1` profile: explicit Ed25519 X.509 paths, complete offline base CRLs, closed AECCTX trusted-time tokens and exact-target countersignatures. These layers remain separate from v1 and from one another. RFC 3161/CMS, OCSP, online or host discovery, production key custody, legal/qualified signatures and universal trust remain unsupported.

```bash
aecctx verify-advanced-trust PACKAGE --signature-bundle signatures.json \
  --policy advanced-trust-policy.json --json
```

## Python API

```python
from aecctx.validation import validate_package
from aecctx.query import query_package

result = validate_package("building.aecctx")
walls = query_package("building.aecctx", 'entity.original_class == "IfcWall"')
```

The optional MCP server is installed with `aecctx[mcp]` and launched with `aecctx-mcp`. It exposes only read-only wrappers over the same stable APIs.

## Non-goals for v0.1

- replacing IFC, Revit, AutoCAD, or authoring applications;
- claiming lossless support for every proprietary format;
- defining a universal construction ontology;
- allowing an LLM to approve or mutate source truth;
- embedding WoodFraming-specific families or rules in the public format.

## Development and release verification

```bash
./scripts/verify.sh
./scripts/verify_release.sh
```

`verify.sh` includes the baseline integration gate and expects the baseline package or sibling checkout available to maintainers. Public CI runs `scripts/verify_portable.sh` so external contributors need no private dependency.

Public CI runs on Linux, macOS and Windows. v0.1 compatibility remains governed by [`conformance/v0.1/corpus.json`](conformance/v0.1/corpus.json); v0.2 claims are aggregated by [`conformance/v0.2/corpus.json`](conformance/v0.2/corpus.json). See [`docs/compatibility-v0.2.md`](docs/compatibility-v0.2.md) and [`docs/releases/v0.2.0.md`](docs/releases/v0.2.0.md).

AECCTX is licensed under Apache-2.0. Optional adapters retain their separately documented permissive or LGPL dependency boundaries. See [`LICENSE`](LICENSE) and [`docs/licenses/`](docs/licenses/).
