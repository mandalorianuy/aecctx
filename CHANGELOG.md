# Changelog

All notable changes are documented here. AECCTX follows Semantic Versioning for the reference implementation; the format compatibility policy for 0.x is in `docs/compatibility.md`.

## Unreleased

- Added the ACX-11 v0.2 shared schema substrate for observation/inference, coordinate qualification, representation fidelity and provider attestation.
- Added dual v0.1/v0.2 validation and writing, required-extension negotiation, cross-version diff metadata, publishable shared fixtures and a governed claim-to-test registry.
- Added the ACX-12 external-provider protocol, allowlisted registry, content-addressed replay corpus and digest-pinned `oci-docker-v1` enforcement profile with adversarial conformance.
- Added explicit rejection for unenforceable native/macOS provider profiles plus security, licensing and privacy review gates.
- Added ACX-13 opt-in IFC v0.2 source-native 2D and explicit projected-georeferencing profiles, reversible transform validation, deterministic cited SVG previews and degraded-state conformance fixtures.
- Format-specific v0.2 targets remain unchanged until their owning tasks complete conformance.

## 0.1.0 - 2026-07-11

- Published the stable v0.1 directory/ZIP package, schemas, value states, capability/loss reports and validation levels.
- Added deterministic reader/writer, source hashing, opaque fallback, query, semantic diff and budgeted context projections.
- Added optional IFC, DXF, vector/raster PDF, image and OBJ/STL/glTF adapters with public conformance fixtures.
- Added deterministic SVG/GLB derived artifacts, plugin isolation/resource policies and optional read-only MCP tools.
- Added multi-platform CI, clean-install verification, checksums, SPDX SBOM generation and release automation.

Unsupported in 0.1.0: authoring-format write-back, hidden-geometry inference, mandatory OCR/vision, direct DWG/RVT decoders, package authenticity/signing and consumer-specific mappings.
