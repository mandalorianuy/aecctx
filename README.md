# AECCTX

AECCTX is an open, application-agnostic specification and local-first Python toolchain for compiling CAD, BIM, drawings, meshes, and related AEC files into deterministic context packages that humans, agents, and downstream applications can inspect without silently losing source evidence.

Version **0.1.0** is implemented, packaged and covered by a public conformance corpus.

The post-v0.1 implementation line is active. ACX-11 implements the bounded v0.2 shared schema/compatibility substrate, ACX-12 the reviewed external-provider foundation, ACX-13 bounded IFC 2D/georeferencing, ACX-14 DXF source-semantics/bounded-3D, ACX-15 an experimental opt-in English OCR profile, and ACX-16 explicit mesh coordinate qualification/manual registration. Claims remain exact and bounded by their corpora.

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
python -m pip install https://github.com/mandalorianuy/aecctx/releases/download/v0.1.0/aecctx-0.1.0-py3-none-any.whl
```

For optional adapters or MCP, install from the tagged source checkout:

```bash
git clone --branch v0.1.0 --depth 1 https://github.com/mandalorianuy/aecctx.git
cd aecctx
python -m pip install '.[all]'
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
```

Unknown inputs use the honest opaque fallback. IFC, DXF, PDF, image and OBJ/STL/glTF content are selected by bounded content probes; `--adapter` can make the choice explicit.

The ACX-13 through ACX-16 v0.2 profiles are explicit:

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
```

Other adapters currently reject `--aecctx-version 0.2.0` until their governed expansion task publishes a profile. OCR remains experimental and partial under [`docs/specs/inference-v02-profile.md`](docs/specs/inference-v02-profile.md). Mesh registration is partial under [`docs/specs/mesh-coordinate-v02-profile.md`](docs/specs/mesh-coordinate-v02-profile.md): it never guesses units/CRS or rewrites source coordinates. Vision and hidden geometry are not inferred.

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

Public CI runs on Linux, macOS and Windows. The governed fixture claims live in [`conformance/v0.1/corpus.json`](conformance/v0.1/corpus.json); compatibility and current release limitations are documented in [`docs/compatibility.md`](docs/compatibility.md) and [`docs/releases/v0.1.0.md`](docs/releases/v0.1.0.md).

AECCTX is licensed under Apache-2.0. Optional adapters retain their separately documented permissive or LGPL dependency boundaries. See [`LICENSE`](LICENSE) and [`docs/licenses/`](docs/licenses/).
