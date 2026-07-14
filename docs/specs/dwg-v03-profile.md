# AECCTX v0.3 bounded DWG provider profile

Version: `0.3.0-draft.1`
Date: 2026-07-14
Status: normative for ACX-33 implementation; no public claim exists until every acceptance gate passes
Decision authority: ACXD-042

## 1. Functional boundary

ACX-33 adds the bounded claim `dwg.external-provider.v03` without changing the immutable `dwg.external-provider` v0.2 claim. The new profile accepts only project-authored DWG inputs with headers `AC1012` (R13), `AC1014` (R14), or `AC1015` (R2000), decoded by the exact reviewed GNU LibreDWG runtime. Each accepted version is an independent partial profile; passing one version never promotes another.

Direct LibreDWG JSON is observed decoder evidence. Converted DXF and any normalized geometry are converted or derived evidence and cite the source input and direct event. Markdown remains a projection. No record becomes consumer semantics, source-exact BREP, survey truth, or engineering validation.

## 2. Runtime, license, and selected releases

The sole provider is `org.aecctx.dwg.libredwg@0.3.0`, GNU LibreDWG 0.13.4 API/ABI 1, GPL-3.0-or-later, in the exact ACX-24 Linux arm64 and amd64 OCI images:

- arm64: `sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1`;
- amd64: `sha256:bcff6c67080688cb2d4f2cecef36ad5c687e1b895ef2adf23a3e3fb7a9248713`.

The Apache-2.0 wheel and sdist contain no LibreDWG binary, library, source, or GPL dependency. Images remain operator-built and are not acquired by core or CLI. Any image distribution retains the existing source, notice, build, and replacement obligations.

The official 0.13.4 program contract states that `dxf2dwg` is experimental and can create only R1.2 through R2000. Executable review of the exact image shows that `--as r13`, `--as r14`, and `--as r2000` create AC1012, AC1014, and AC1015 files. Although help text lists `r12`, the exact runtime rejects that option, so R12 is not claimed. R2004 writing is experimental, R2007 writing is not covered, and R2004 through R2018 remain unclaimed even if decoding may succeed.

The known upstream material-texture heap-overflow report lacks a linked fixing commit, CVE, or release-specific regression proof. Release 0.13.4 postdates closure, but the decoder remains untrusted native code and the full OCI boundary is mandatory. The upstream arm64 aggregate writer round-trip failures remain recorded; only the bounded read and conversion paths are provider capabilities.

## 3. Closed provider request

The only action is `extract`. No request can select an executable, option, output format, path, environment, plugin, callback, writer, or xref resolver. Exact configurations are:

| profile | DWG header | converted DXF target | unit/geometry ceiling |
|---|---|---|---|
| `acx33-r13-v1` | `AC1012` | `r13` / `AC1012` | explicit units when retained; simple converted geometry |
| `acx33-r14-v1` | `AC1014` | `r14` / `AC1014` | explicit units when retained; simple converted geometry |
| `acx33-r2000-v1` | `AC1015` | `r2000` / `AC1015` | explicit units when retained; simple converted geometry |

Every configuration also fixes `json_format="JSON"` and `resolve_external_references=false`. The worker invokes only `/opt/libredwg/bin/dwgread` twice, sequentially, for JSON and DXF. `dxf2dwg`, `dwgwrite`, `dwgrewrite`, shell commands, and caller-selected commands are unreachable.

## 4. Version, units, and geometry evidence

The six-byte source header and direct JSON `FILEHEADER.version` must equal the selected profile. Mismatch fails closed. The conversion event states requested and observed DXF versions, input and artifact hashes, converter identity, and `representation_fidelity="converted"`.

Units are `known` only when the direct decoder output retains an explicit finite `$INSUNITS` code in the selected mapping: `1=in`, `2=ft`, `4=mm`, `5=cm`, `6=m`, `7=km`. Zero, absent, malformed, unsupported, or conflicting values remain `unknown` or `conflicted`; no unit is inferred from coordinates, names, versions, extents, blocks, or geometry.

The maximum 3D support is `partial` for POINT, LINE, POLYLINE/vertex, 3DFACE, and MESH-style vertices/faces retained through the converted DXF and accepted by the existing bounded neutral DXF layer. Curves, transforms, elevations, and faces retain their coordinates and source/converted lineage. No tessellation, repair, extrusion, or inferred solid is source authority.

ACIS/SAT/SAB, REGION, 3DSOLID, BODY, SURFACE, proxy graphics, custom/vertical objects, proprietary class semantics, missing decoder objects, and conversion omissions emit structured loss and remain unsupported. Complete 3D, topology, exact BREP, render parity, and custom semantics are non-claims.

## 5. Content-addressed xrefs

Optional xrefs reuse the ACX-28 `source-bundle.json` schema and validation ceilings. A DWG bundle contains one root and declared `xref` members with media type `image/vnd.dwg`; all members are regular, hash-bound, size-bound, and validated before decoder invocation. Absolute, drive, URI, traversal, symlink, undeclared, duplicate, cyclic, depth-exceeding, digest-mismatched, or oversized members fail closed.

The provider never opens an xref path from DWG bytes. Each admitted bundle member is decoded as an independent provider request by the caller and mapped as a distinct source. Resolution matches a retained inert source path only to a normalized declared logical path. Traversal order is deterministic. Missing or ambiguous matches remain unresolved. Xref provenance cites both the declaring source and the separately decoded target source; source identities are never merged.

Limits remain 32 files, 512 MiB per member, 1 GiB aggregate, and maximum xref depth 8. Network and ambient filesystem resolution are prohibited.

## 6. Failure and loss contract

Stable negative outcomes include:

- `AECCTX_DWG_VERSION_UNCLAIMED`, `AECCTX_DWG_HEADER_TRUNCATED`, and `AECCTX_DWG_JSON_VERSION_INVALID`;
- `AECCTX_DWG_ENCRYPTED_UNSUPPORTED` and `AECCTX_DWG_PROTECTED_UNSUPPORTED`;
- `AECCTX_DWG_ACIS_UNSUPPORTED`, `AECCTX_DWG_PROXY_OBJECT_UNSUPPORTED`, and `AECCTX_DWG_CUSTOM_OBJECT_UNSUPPORTED`;
- `AECCTX_DWG_CONVERSION_LOSS` and `AECCTX_DWG_DXF_HANDLE_UNMATCHED`;
- `AECCTX_DWG_HANDLE_CONFLICT` with occurrence-qualified observed locators;
- inherited content-addressed bundle failures with DWG-specific outward codes;
- inherited OCI digest, platform, resource, timeout, attestation, artifact, and cleanup failures;
- `AECCTX_DWG_REQUEST_OUTSIDE_PROFILE` or `AECCTX_DWG_CONFIGURATION_INVALID` for every writer or caller-command attempt.

Encrypted/password-protected content is never bypassed. A zero decoder exit or syntactically valid artifact cannot imply semantic completeness.

## 7. Fixtures and conformance

Publishable positives are authored as deterministic DXF source data with `ezdxf==1.4.4`, then mechanically encoded by the exact reviewed `dxf2dwg` binary under network-disabled, non-root execution. The repository binds generator bytes, source DXF hashes, output DWG hashes, runtime image IDs, command profile, and observed replay outputs.

The corpus includes R13, R14, and R2000; explicit metre/millimetre/unknown units; simple 3D faces/lines/points; a closed root/child xref bundle; duplicate handles; conversion loss; encrypted/protected envelope mutations; ACIS/proxy/custom direct-output adversarial cases; corrupt/wrong-version inputs; writer/configuration denial; deterministic replay; and byte-equivalent live arm64/amd64 outputs.

Positive claim gates are:

1. public and packaged event schema equality;
2. generator reproducibility and fixture hash equality;
3. direct/converted/derived lineage and explicit value-state tests;
4. replay corpus validation and hostile decoder-output rejection;
5. exact live arm64/amd64 artifact and event equality;
6. writer denial, no-network, bundle confinement, license, and package scans;
7. focused suites, portable verification, and `./scripts/verify.sh`.

## 8. Public ceiling and residuals

`dwg.external-provider.v03` may become public `partial` only for the three exact version/runtime/platform profiles above. It does not claim generic DWG, R12, R2004+, encryption, ACIS, proprietary/custom semantics, complete xrefs, complete 3D, CRS/georeferencing, authoring, repair, image authenticity, native macOS/Windows, other architectures, or other providers.

ODA/RealDWG or commercial/network providers require a separate entitlement, redistribution, CI, security, privacy, retention, jurisdiction, lifecycle, and conformance decision. WoodFraming and all consumer mappings remain outside AECCTX.

## 9. Primary references

- GNU LibreDWG 0.13.4 manual: `https://www.gnu.org/software/libredwg/manual/LibreDWG.html`;
- LibreDWG program limits: `https://www.gnu.org/software/libredwg/manual/html_node/Programs.html`;
- LibreDWG encoding limits: `https://www.gnu.org/software/libredwg/manual/html_node/Encoding.html`;
- official release: `https://github.com/LibreDWG/libredwg/releases/tag/0.13.4`;
- upstream material-texture report: `https://github.com/LibreDWG/libredwg/issues/1037`.
