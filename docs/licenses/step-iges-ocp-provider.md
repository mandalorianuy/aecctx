# ACX-17 OCP/OCCT provider distribution record

Date: 2026-07-12
Status: reviewed local provider profile

The provider `org.aecctx.step-iges.ocp@0.2.0` uses:

- `cadquery-ocp==7.9.3.1.1`: Apache-2.0 Python bindings;
- bundled Open CASCADE Technology 7.9.3: LGPL-2.1 with the OCCT exception;
- operator-built Ubuntu Noble Linux arm64 legacy image `aecctx-step-iges-ocp:0.2.0` with local image ID `sha256:875cbbbc5198ae44e8957e3a90c9a8afd0dc541f01029fb5186a296e3d2a0d47`;
- ACX-24 architecture-specific `linux/arm64` and `linux/amd64` targets whose IDs and resolved package locks are bound in `fixtures/v0.3/provider-multiarch/receipts/`.

The native runtime is not linked into or distributed with the Apache-2.0 AECCTX wheel/sdist. Core operation, validation, opaque ingest and replay mapping do not require it. The repository publishes a build recipe but no container image.

An operator who distributes the image must independently satisfy the OCP/OCCT notices, license-text, corresponding-source and relinking/replacement obligations for that distribution. The OCCT source for the selected release and official license terms are available from the Open CASCADE project. A rebuilt image has a different identity and is not covered by this runtime claim until reviewed.

Project STEP/IGES fixtures contain project-authored boxes, placements and metadata generated solely for conformance. They may be redistributed under the repository Apache-2.0 license.
