# AECCTX DXF v0.3 Profile

Version: `dxf-v03-profile-1`
Status: normative for ACX-28
Decision: ACXD-036

## 1. Runtime and release boundary

The only reviewed runtime is optional `ezdxf==1.4.4` under its MIT license. The public profile covers project-authored ASCII and binary evidence for `AC1009`, `AC1015`, `AC1018`, `AC1021` and `AC1032`; an individual release is claimable only when its exact corpus case passes. Parser acceptance is not a release claim.

The default `ingest_dxf()` profile remains AECCTX v0.1. ACX-28 behavior requires `aecctx_version="0.2.0"`; passing a source bundle enables only the additional bounded xref profile.

## 2. Source evidence and neutral semantics

Raw tags, handles, owners, layouts, layers, blocks, extension dictionaries, XDATA and existing ACX-14 semantics remain authoritative. ACX-28 adds namespaced `dxf_v03` evidence for:

- `ELLIPSE`: center, major axis, extrusion, ratio and parameter bounds;
- `SPLINE`: degree, flags, knots, weights, control points and fit points;
- `HELIX`: spline evidence plus axis, start point, radius, turn height/count, handedness and constraint;
- `RAY` and `XLINE`: start and unit vector;
- `MLINE`: style name, scale, justification, extrusion and vertices.
- `MESH`: source vertices, faces and edges for the newly covered R2007 release profile.

Every value is copied from source/API state. Missing, malformed, non-finite or over-limit state is explicit. Neutral entities retain `aecctx:linear-element` or `aecctx:opaque-object`; layer names, block names and geometry MUST NOT create wall, beam, panel, stud, joist or rafter classifications.

## 3. Derived curve geometry

ELLIPSE, SPLINE and HELIX may produce a deterministic ordered sampled path using fixed `max_chord_error=0.001 drawing-unit`, `minimum_segments=8` and `maximum_vertices=4096`. RAY/XLINE remain unbounded source definitions; MLINE remains source semantics; MESH topology is source evidence and its GLB remains derived under ACXD-026. Sampled vertices are derived, cite the source primitive and state their tolerance and truncation state. They are not exact analytic geometry, B-Rep, survey evidence or consumer classifications.

## 4. Content-addressed source bundle

An optional bundle is a directory containing `source-bundle.json` plus declared members. The manifest conforms to `schemas/v0.2/source-bundle.schema.json` and contains version `0.2`, one root logical path and a closed entry list. Each entry binds logical path, role (`root` or `xref`), media type, byte count and lowercase SHA-256.

Before parsing any DXF member, AECCTX MUST validate the entire manifest and all member metadata, paths, regular-file status, containment, sizes and hashes. Defaults and hard ceilings are 32 files, depth 8, 512 MiB per file and 1 GiB aggregate. Callers may lower but not raise these ceilings.

Only xref paths declared by root or traversed bundle documents are eligible. A path is normalized as a POSIX logical path relative to the bundle root; ambient host-relative resolution is prohibited. Absolute paths, drive paths, URI/network paths, traversal, undeclared files, cycles, depth overflow, size overflow, digest mismatch and symlinks fail closed before opening the affected xref. Traversal order is deterministic by normalized logical path.

Each member emits a distinct source record. Xref primitives cite that source record, and the root block record preserves both the source-declared path and resolved bundle logical path. Source bytes are embedded only under the caller's normal embedding policy.

## 5. Explicit non-claims

ACIS/SAT/SAB interpretation, exact surfaces/B-Rep, proxy/custom semantics, encrypted/protected content, ambient filesystem xrefs, network xrefs, DWG xrefs, external images/underlays, write-back, engineering approval and construction-domain classification remain unsupported or opaque. Raw preservation or parser acceptance alone does not promote a public claim.

## 6. Conformance and security

Public claims are `dxf.source-semantics.v03` and `dxf.geometry.v03`, each `partial`. They require the committed corpus hashes, deterministic regeneration, positive/degraded/negative/adversarial tests, source separation, capability/loss diagnostics, v0.1/v0.2 regression tests, clean wheel/sdist scans and repository gates. Inputs are untrusted data; embedded commands, links, macros and source-provided paths are never executed or followed.
