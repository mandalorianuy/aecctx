# AECCTX v0.2 DWG Evidence Profile

Version: `0.2.0-draft.1`
Date: 2026-07-12
Status: ACX-18 normative design pending implementation evidence
Decision authority: ACXD-007, ACXD-014, ACXD-019, ACXD-024 and ACXD-029

## 1. Scope and claims

ACX-18 defines one bounded target claim, `dwg.external-provider`, selected only with `aecctx_version="0.2.0"`. The initial implementation profile is limited to self-contained DWG R2000 files whose six-byte header is `AC1015`.

The claim begins as `target`. It may become `experimental partial` only after the exact provider image, fixture corpus, replay, package mapping, security/license review and live OCI gates pass. The default and explicit v0.1 behavior remain opaque and byte-identical to normal opaque ingest.

No generic DWG support is claimed. R1.2-R14, R2004-R2018, future versions, encrypted/protected drawings, password bypass, proxy/custom object semantics, ACIS modeler bodies, external-reference traversal and embedded executable content remain unsupported or opaque.

## 2. Provider and license boundary

The selected provider is `org.aecctx.dwg.libredwg@0.2.0`, using GNU LibreDWG 0.13.4 API/ABI 1. LibreDWG is GPL-3.0-or-later and never enters the Apache-2.0 core wheel, source distribution, optional in-process extras or host import path. It executes only in the reviewed ACX-12 `oci-docker-v1` profile.

The provider image is built explicitly by an operator from the official LibreDWG 0.13.4 release archive:

- source: `https://github.com/LibreDWG/libredwg/releases/download/0.13.4/libredwg-0.13.4.tar.xz`;
- SHA-256: `7e153ea4dac4cbf3dc9c50b9ef7a5604e09cdd4c5520bcf8017877bbe1422cd5`;
- build mode: `./configure --enable-release`;
- provider runtime tool: `dwgread` only;
- project-fixture generation tool: `dxf2dwg`, invoked only by the explicit repository generator and never from a provider request.

The immutable locally inspected image ID is a mandatory implementation output. Core ingest never builds, pulls, installs or discovers the image. The repository does not distribute the image by default. Any later image distribution must ship complete GPL notices, corresponding source/build instructions and relinking/replacement rights appropriate to that distribution.

There is no entitlement, account, credential, telemetry, retention or service dependency. A decoder/version/base-image/build-option/image-ID change creates a new provider profile and requires new review and conformance.

The security review must explicitly record the February 2026 upstream heap-buffer-overflow report involving material texture parsing, verify whether the selected 0.13.4 release contains the relevant fix, and retain the full OCI resource boundary regardless. Absence of a published CVE or a successful fixture run is not proof that the native decoder is memory-safe.

The official 0.13.4 arm64 release build has a known verification limitation: its aggregate `make check` fails `programs/alive.test` on JSON-to-DWG writer round trips, while `programs/dxf.test` passes the read/DWG-to-DXF and DXF-to-DWG paths used by this profile. The reviewed image build MUST run the exact upstream `dxf.test`, then the AECCTX provider read/conversion/adversarial corpus. It MUST record the aggregate upstream failure and MUST NOT present the selected test cut as full upstream conformance. A future LibreDWG release requires a new decision and complete re-evaluation.

## 3. Rejected providers

ODA Drawings SDK and Autodesk RealDWG are not selected. Both require commercial licensing/entitlement and an approved redistribution and CI model that this repository does not possess. Autodesk Platform Services conversion is also not selected because it would require network credentials, upload consent, retention/jurisdiction governance and external-input provenance.

These alternatives remain future governed profiles; their availability cannot promote the LibreDWG claim.

## 4. Trust and execution boundary

DWG bytes, LibreDWG JSON/DXF, stderr, object graphs, strings, handles and geometry are untrusted data. The provider uses the complete ACX-12 Linux-container controls:

- no network, non-root user, read-only root filesystem, dropped capabilities and `no-new-privileges`;
- one process, bounded CPU, memory, wall time, PIDs, open files, input/output bytes, records, recursion and temporary storage;
- read-only content-addressed source/request/provider mounts and one bounded writable output mount;
- fixed locale, timezone and environment;
- schema, sequence, path, symlink, size, hash, attestation and host-path validation before mapping;
- complete process-tree termination and workspace cleanup.

The provider accepts no caller command, shell, callback, environment, plugin, resource path or LibreDWG option. Its worker invokes only the fixed `dwgread` binary; the image's writer utilities are not reachable through provider actions or configuration. It never executes VBA, macros, links, xrefs, embedded OLE content or source-provided commands. stderr becomes only stable diagnostic codes, never raw package evidence.

## 5. Request, output and conversion provenance

The only action is `extract`. Configuration is exact canonical JSON:

```json
{
  "dwg_version": "AC1015",
  "json_format": "JSON",
  "dxf_version": "r2000",
  "profile": "acx18-r2000-v1",
  "resolve_external_references": false
}
```

The provider verifies the `AC1015` header before invoking LibreDWG. It runs:

1. `dwgread --format JSON --file <bounded-output> <content-addressed-input>`;
2. `dwgread --format DXF --file <bounded-output> <content-addressed-input>`.

The provider response contains:

- observed DWG header/version and validated LibreDWG JSON source-object events;
- a content-addressed canonicalized JSON artifact;
- a content-addressed converted DXF artifact;
- conversion/runtime/settings/input/output hashes;
- ordered diagnostics, resource usage, capability/loss report and attestation.

The JSON route is direct decoder evidence. The DXF artifact is converted evidence and MUST NOT be described as native DWG geometry. Mapping or GLB derived through the existing DXF adapter cites both the observed DWG object and converted DXF evidence and retains conversion loss.

## 6. Source identity and bounded structure

Stable locators are:

- DWG object/entity: `dwg:handle:<uppercase-hex-handle>`;
- header variable: `dwg-header:<NAME>`;
- class: `dwg-class:<number>`;
- converted DXF entity: `dwg-dxf:handle:<uppercase-hex-handle>` when preserved, otherwise a converted locator with explicit unresolved identity;
- artifact: `dwg-artifact:<role>:sha256:<digest>`.

Duplicate or malformed handles, broken owner references, unsafe nesting and non-finite geometry reject or degrade before package construction.

For the R2000 corpus, the provider preserves when present:

- exact file header, source hash and LibreDWG version/error state;
- object/entity handle, original class/type, owner/reactor/extension-dictionary references exposed by JSON;
- layer, linetype, block-header, block/insert and layout records exposed by JSON;
- xref/path strings only as inert data, never opened;
- text and simple properties without consumer interpretation;
- header units and coordinate variables only when explicit;
- LINE, POINT, CIRCLE, ARC, LWPOLYLINE, POLYLINE_2D, 3DFACE, INSERT, TEXT, MTEXT, ATTRIB and ATTDEF source classes as raw observed objects.

Neutral normalization is limited to exact records exercised by the corpus. A name or geometry never becomes a wall, beam, panel, discipline or consumer family.

## 7. Geometry and fidelity

LibreDWG JSON objects remain observed decoder evidence. The converted R2000 DXF is a derived conversion artifact with:

- converter/provider/runtime/configuration digest;
- input DWG hash and output DXF hash;
- requested and observed version;
- warning/error codes;
- source-handle preservation status;
- explicit `representation_fidelity.class = "converted"`.

Existing bounded DXF parsing may normalize the enumerated simple geometry only after the converted artifact independently validates. Any GLB/SVG is subordinate derived evidence. ACIS solids/surfaces, proxy graphics, custom objects, unsupported classes and objects skipped by LibreDWG remain opaque/unsupported and cannot yield a full 3D or validation claim.

The provider never rewrites DWG, repairs CRCs, explodes inserts, resolves xrefs or heals geometry.

## 8. Capability and diagnostics

The maximum initial support is:

- identity: `full` only for the exact source bytes and R2000 header;
- hierarchy, properties, relationships, text, 2D geometry and materials/styles: `partial`;
- 3D geometry: `partial` only for enumerated simple entities preserved through conversion;
- georeferencing and validation: `unsupported`.

Stable diagnostics include:

- `AECCTX_DWG_VERSION_UNCLAIMED`;
- `AECCTX_DWG_HEADER_INVALID`;
- `AECCTX_DWG_ENCRYPTED_UNSUPPORTED`;
- `AECCTX_DWG_EXTERNAL_REFERENCE_UNRESOLVED`;
- `AECCTX_DWG_PROXY_OBJECT_UNSUPPORTED`;
- `AECCTX_DWG_ACIS_UNSUPPORTED`;
- `AECCTX_DWG_HANDLE_INVALID`;
- `AECCTX_DWG_REFERENCE_INVALID`;
- `AECCTX_DWG_DECODE_FAILED`;
- `AECCTX_DWG_DECODE_PARTIAL`;
- `AECCTX_DWG_JSON_INVALID`;
- `AECCTX_DWG_DXF_CONVERSION_FAILED`;
- `AECCTX_DWG_CONVERSION_LOSS`;
- `AECCTX_DWG_RUNTIME_UNAVAILABLE`;
- inherited ACX-12 registration, digest, sandbox, timeout, resource, protocol, attestation and cleanup failures.

LibreDWG non-critical warnings, unknown/unhandled classes and conversion omissions must become structured loss. A zero process exit cannot imply complete semantics.

## 9. Fixtures and conformance

Project-authored fixtures are generated from project-authored DXF/JSON commands through the exact provider image and are publishable under Apache-2.0 as source data. The corpus includes:

- positive R2000 drawing with model/paper layouts, layers, blocks/inserts, attributes, text and enumerated 2D/3D simple entities;
- xref string retained but unresolved;
- proxy/custom and ACIS-like unsupported evidence where it can be generated without proprietary samples;
- malformed/truncated header, wrong/future version, corrupt object graph and oversized input;
- missing/rejected provider, image-ID mismatch, timeout, memory/output/record limit and hostile response;
- deterministic live/replay parity and repeated ZIP package bytes;
- default/explicit v0.1 opaque identity;
- clean wheel/sdist scan proving no LibreDWG binary/library or GPL dependency;
- repository scan proving no WoodFraming, `WFDomain`, `WFImport` or consumer ontology.

If a negative binary cannot be legally/project-authored, the test mutates only project-authored fixture bytes and records that provenance.

## 10. CLI and SDK

`ingest_dwg()` defaults to v0.1 opaque behavior. The v0.2 SDK requires a validated `ProviderResult`. The CLI adds adapter `dwg` and paired `--provider-replay/--provider-entry` for portable replay. The CLI never launches, builds, pulls or installs LibreDWG.

Live execution remains an explicit SDK operation using a caller-constructed reviewed `ProviderRunner`. Provider absence or rejection may fall back only through a separate explicit opaque ingest call; it cannot advertise the DWG claim.

## 11. Residuals

The following remain explicit residuals requiring a new or amended governed profile, decision and corpus:

- DWG versions other than R2000/AC1015;
- unsupported or unstable LibreDWG classes, especially advanced R2010+ content;
- source-exact interpretation of proxy/custom objects and proprietary verticals;
- ACIS/SAT bodies and exact B-Rep;
- xref resolution, multifile drawing sets and external resources;
- encryption/password handling or bypass;
- native paper/model viewport rendering parity;
- authoritative georeferencing, survey CRS and engineering validation;
- ODA, RealDWG or network-backed provider profiles;
- live execution outside the exact reviewed Linux-container image;
- provider image publisher authenticity;
- authoring write-back or source repair.

A residual is functional work only when a later plan defines provider authority, exact output behavior, fixtures, tests and acceptance; merely restating the gap does not count as progress.

## 12. Primary references

- GNU LibreDWG 0.13.4 manual: `https://www.gnu.org/software/libredwg/manual/LibreDWG.html`;
- LibreDWG JSON contract: `https://www.gnu.org/software/libredwg/manual/html_node/JSON.html`;
- LibreDWG programs and conversion behavior: `https://www.gnu.org/software/libredwg/manual/html_node/Programs.html`;
- official 0.13.4 release: `https://github.com/LibreDWG/libredwg/releases/tag/0.13.4`;
- Autodesk RealDWG overview: `https://aps.autodesk.com/developer/overview/realdwg-api`;
- ODA Drawings SDK overview: `https://www.opendesign.com/products/drawings`.
