from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from ..geometry import export_deterministic_glb
from ..ingest import CAPABILITIES, IngestResult, _timestamp, ingest_opaque
from ..package import PackageArtifact, PackageWriter, canonical_json, hash_file
from ..providers.protocol import ProviderResult
from ..step_iges import StepIgesInputError, validate_step_iges_events


PLUGIN_ID = "aecctx.adapter.step-iges.ocp-provider"
PLUGIN_VERSION = "0.2.0"


def _unknown(code: str) -> dict[str, str]:
    return {"reason_code": code, "state": "unknown"}


def _known(value: Any) -> dict[str, Any]:
    return {"state": "known", "value": value}


def _stable_id(prefix: str, digest: str, key: str) -> str:
    return f"{prefix}_{hashlib.sha256(f'{digest}\0{key}'.encode()).hexdigest()[:24]}"


def _provenance(instant: str, parents: list[str], runtime_digest: str, method: str) -> dict[str, Any]:
    return {
        "method": method,
        "parent_record_ids": sorted(parents),
        "producer_id": PLUGIN_ID,
        "producer_version": f"{PLUGIN_VERSION}+{runtime_digest}",
        "recorded_at": instant,
    }


def _product_label(raw: str) -> dict[str, Any]:
    match = re.match(r"#[0-9]+\s*=\s*PRODUCT\s*\(\s*'(?:[^']|'')*'\s*,\s*'((?:[^']|'')*)'", raw, re.DOTALL)
    return _known(match.group(1).replace("''", "'")) if match else _unknown("AECCTX_STEP_PRODUCT_NAME_UNAVAILABLE")


def ingest_step_iges(
    source_path: str | Path,
    output_path: str | Path,
    *,
    created_at: str | None = None,
    embedding_policy: str = "external",
    package_form: str = "directory",
    aecctx_version: str = "0.1.0",
    provider_result: ProviderResult | None = None,
) -> IngestResult:
    if aecctx_version == "0.1.0":
        if provider_result is not None:
            raise StepIgesInputError("AECCTX_STEP_IGES_VERSION_INVALID", "Provider result requires AECCTX v0.2")
        return ingest_opaque(source_path, output_path, created_at=created_at, embedding_policy=embedding_policy, package_form=package_form)
    if aecctx_version != "0.2.0":
        raise StepIgesInputError("AECCTX_STEP_IGES_VERSION_INVALID", "AECCTX version must be 0.1.0 or 0.2.0")
    if provider_result is None:
        raise StepIgesInputError("AECCTX_STEP_IGES_RUNTIME_UNAVAILABLE", "A validated STEP/IGES provider result is required")
    evidence = validate_step_iges_events(provider_result)
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("source_path must be a regular file")
    if embedding_policy not in {"external", "embedded", "redacted"}:
        raise ValueError("embedding_policy must be external, embedded, or redacted")
    source_digest, source_bytes = hash_file(source)
    identity = source_digest[:24]
    source_id = f"src_{identity}"
    package_id = f"pkg_{identity}"
    instant = _timestamp(created_at)
    runtime_digest = str(provider_result.attestation.get("runtime_digest", "unknown"))
    format_name = str(evidence.source["format"])
    media_type = "model/step" if format_name == "step" else "model/iges"
    storage_ref = f"sources/content/{source.name}" if embedding_policy == "embedded" else None

    source_record: dict[str, Any] = {
        "acquisition_origin": "local-file",
        "byte_size": source_bytes,
        "declared_format": _known(format_name.upper()),
        "declared_units": _unknown("AECCTX_STEP_IGES_UNIT_NOT_MAPPED"),
        "detected_format": _known(format_name.upper()),
        "detected_producer": _known("OCP/OCCT 7.9.3 external provider"),
        "detected_units": _unknown("AECCTX_STEP_IGES_UNIT_NOT_MAPPED"),
        "display_name": source.name,
        "embedding_policy": embedding_policy,
        "evidence_class": "observed",
        "extractor": {"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
        "media_type": media_type,
        "prior_source_revision": _unknown("AECCTX_PRIOR_REVISION_NOT_PROVIDED"),
        "provenance": _provenance(instant, [], runtime_digest, "external-provider-source-registration"),
        "record_id": source_id,
        "record_type": "source",
        "record_version": "0.2",
        "safety_diagnostics": ["AECCTX_INPUT_TREATED_AS_DATA", "AECCTX_EXTERNAL_REFERENCES_NOT_OPENED"],
        "sha256": source_digest,
        "source_id": source_id,
        "source_refs": [],
        "spatial_reference": _unknown("AECCTX_STEP_IGES_CRS_UNSUPPORTED"),
    }
    if storage_ref:
        source_record["storage_ref"] = storage_ref
    elif embedding_policy == "redacted":
        source_record["redaction_reason"] = "AECCTX_SOURCE_CONTENT_REDACTED_BY_POLICY"

    source_items = evidence.source.get("entities", evidence.source.get("directory", []))
    primitives: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    primitive_by_source_id: dict[int, str] = {}
    for item in source_items:
        source_number = int(item.get("id", item.get("sequence")))
        locator = f"step:#{source_number}" if format_name == "step" else f"iges:D{source_number}"
        original_class = str(item.get("original_class", f"IGES_{item.get('entity_type')}_FORM_{item.get('form')}"))
        primitive_id = _stable_id("prim_step_iges", source_digest, locator)
        primitive_by_source_id[source_number] = primitive_id
        primitive = {
            **dict(item),
            "evidence_class": "observed",
            "original_class": original_class,
            "provenance": _provenance(instant, [source_id], runtime_digest, "external-provider-source-entity"),
            "record_id": primitive_id,
            "record_type": "primitive",
            "record_version": "0.2",
            "source_refs": [{"locator": locator, "source_id": source_id}],
        }
        primitives.append(primitive)
        if original_class == "PRODUCT":
            entity_id = _stable_id("entity_step_product", source_digest, locator)
            entities.append(
                {
                    "entity_id": entity_id,
                    "evidence_class": "observed",
                    "kind": "aecctx:source-product",
                    "label": _product_label(str(item.get("raw", ""))),
                    "original_class": original_class,
                    "parent_evidence_ids": [primitive_id],
                    "provenance": _provenance(instant, [primitive_id], runtime_digest, "step-product-neutral-index"),
                    "record_id": entity_id,
                    "record_type": "entity",
                    "record_version": "0.2",
                    "source_local_identifiers": {"step_id": source_number},
                    "source_refs": [{"locator": locator, "source_id": source_id}],
                }
            )
        if original_class == "NEXT_ASSEMBLY_USAGE_OCCURRENCE":
            relation_id = _stable_id("relation_step_assembly", source_digest, locator)
            relations.append(
                {
                    "endpoints": [{"role": "referenced-source-entity", "source_entity_id": value} for value in item.get("references", [])],
                    "evidence_class": "observed",
                    "original_class": original_class,
                    "parent_evidence_ids": [primitive_id],
                    "provenance": _provenance(instant, [primitive_id], runtime_digest, "step-assembly-neutral-index"),
                    "record_id": relation_id,
                    "record_type": "relation",
                    "record_version": "0.2",
                    "relation_id": relation_id,
                    "relation_type": "aecctx:source-assembly-usage",
                    "source_refs": [{"locator": locator, "source_id": source_id}],
                }
            )

    import trimesh

    mesh = trimesh.Trimesh(vertices=evidence.mesh["vertices"], faces=evidence.mesh["triangles"], process=False)
    glb = export_deterministic_glb([mesh])
    brep_path = "geometry/root-1.brep"
    glb_path = "geometry/scene.glb"
    derived_id = _stable_id("prim_step_iges_brep", source_digest, "shape:1")
    source_representation_ids = sorted(primitive_by_source_id.values())
    primitives.append(
        {
            "artifact_ref": brep_path,
            "bounds": evidence.shape["bounds"],
            "evidence_class": "derived",
            "mesh_artifact_ref": glb_path,
            "original_class": "OCCT_TRANSLATED_BREP",
            "provenance": _provenance(instant, source_representation_ids, runtime_digest, "occt-translator-derived-brep"),
            "record_id": derived_id,
            "record_type": "primitive",
            "record_version": "0.2",
            "representation_fidelity": {"class": "brep", "derived": True, "source_representation_ids": source_representation_ids},
            "source_refs": [{"locator": "shape:1", "source_id": source_id}],
            "topology": evidence.shape["topology"],
            "translator_processing": evidence.shape["translator_processing"],
        }
    )
    capabilities = {name: str(provider_result.capability_report[name]["support_level"]) for name in CAPABILITIES}
    loss_summary = sorted({str(code) for report in provider_result.capability_report.values() for code in report.get("reason_codes", [])})
    diagnostics = []
    for index, diagnostic in enumerate(provider_result.diagnostics):
        diagnostics.append(
            {
                "code": diagnostic["code"],
                "evidence_class": "observed",
                "message": "External provider reported STEP/IGES extraction diagnostics.",
                "provenance": _provenance(instant, [source_id], runtime_digest, "external-provider-diagnostic"),
                "record_id": _stable_id("diag_step_iges", source_digest, f"{index}:{diagnostic['code']}"),
                "record_type": "diagnostic",
                "record_version": "0.2",
                "severity": diagnostic.get("severity", "info"),
                "source_refs": [{"locator": "provider-result", "source_id": source_id}],
            }
        )
    record_sets = {
        "sources/sources.jsonl": [source_record],
        "evidence/primitives.jsonl": primitives,
        "evidence/assertions.jsonl": [],
        "model/entities.jsonl": entities,
        "model/relations.jsonl": relations,
        "diagnostics/diagnostics.jsonl": diagnostics,
    }
    artifacts = [
        PackageArtifact(path, b"".join(canonical_json(item) for item in sorted(items, key=lambda value: value["record_id"])), "application/x-ndjson", path.split("/")[-1].removesuffix(".jsonl"), True)
        for path, items in record_sets.items()
    ]
    artifacts.extend(
        [
            PackageArtifact(brep_path, evidence.brep, "model/vnd.opencascade.brep", "translator-derived-brep", False),
            PackageArtifact(glb_path, glb, "model/gltf-binary", "tessellated-3d-geometry", False),
            PackageArtifact(
                "context/index.md",
                (f"# STEP/IGES AECCTX package\n\nPackage `{package_id}` preserves {len(source_items)} observed source entities. BREP and GLB are translator-derived evidence; structured records remain authoritative.\n").encode(),
                "text/markdown",
                "agent-context",
                False,
            ),
        ]
    )
    if storage_ref:
        artifacts.append(PackageArtifact(storage_ref, source, media_type, "embedded-source", True))
    manifest = PackageWriter(output, package_form=package_form).write(
        package_id=package_id,
        created_at=instant,
        source_ids=[source_id],
        capabilities=capabilities,
        loss_summary=loss_summary,
        embedding_policy=embedding_policy,
        producer={"name": PLUGIN_ID, "version": PLUGIN_VERSION},
        artifacts=artifacts,
        aecctx_version="0.2.0",
    )
    return IngestResult(package_id, source_id, manifest["logical_digest"], output)
