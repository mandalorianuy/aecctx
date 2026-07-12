from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

from ..dwg import DWGInputError, validate_dwg_events
from ..ingest import CAPABILITIES, IngestResult, _timestamp, ingest_opaque
from ..package import PackageArtifact, PackageWriter, canonical_json, hash_file
from ..providers.protocol import ProviderResult
from .dxf import _geometry


PLUGIN_ID = "aecctx.adapter.dwg.libredwg-provider"
PLUGIN_VERSION = "0.2.0"
CONVERTED_CLASSES = {"LINE", "POINT", "CIRCLE", "ARC", "LWPOLYLINE", "3DFACE", "INSERT", "TEXT", "MTEXT", "ATTRIB", "ATTDEF"}


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


def _records_artifact(path: str, records: list[dict[str, Any]]) -> PackageArtifact:
    payload = b"".join(canonical_json(item) for item in sorted(records, key=lambda value: value["record_id"]))
    return PackageArtifact(path, payload, "application/x-ndjson", path.split("/")[-1].removesuffix(".jsonl"), True)


def ingest_dwg(
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
            raise DWGInputError("AECCTX_DWG_VERSION_INVALID", "Provider result requires AECCTX v0.2")
        return ingest_opaque(source_path, output_path, created_at=created_at, embedding_policy=embedding_policy, package_form=package_form)
    if aecctx_version != "0.2.0":
        raise DWGInputError("AECCTX_DWG_VERSION_INVALID", "AECCTX version must be 0.1.0 or 0.2.0")
    if provider_result is None:
        raise DWGInputError("AECCTX_DWG_RUNTIME_UNAVAILABLE", "A validated DWG provider result is required")
    evidence = validate_dwg_events(provider_result)
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("source_path must be a regular file")
    if embedding_policy not in {"external", "embedded", "redacted"}:
        raise ValueError("embedding_policy must be external, embedded, or redacted")
    source_digest, source_bytes = hash_file(source)
    if source_digest != evidence.source_event["input_sha256"]:
        raise DWGInputError("AECCTX_DWG_INPUT_HASH_MISMATCH", "Provider evidence does not match source bytes")
    identity = source_digest[:24]
    source_id = f"src_{identity}"
    package_id = f"pkg_{identity}"
    instant = _timestamp(created_at)
    runtime_digest = str(provider_result.attestation.get("runtime_digest", "unknown"))
    storage_ref = f"sources/content/{source.name}" if embedding_policy == "embedded" else None

    source_record: dict[str, Any] = {
        "acquisition_origin": "local-file",
        "byte_size": source_bytes,
        "declared_format": _known("DWG R2000"),
        "declared_units": _unknown("AECCTX_DWG_UNITS_NOT_QUALIFIED"),
        "detected_format": _known("DWG AC1015"),
        "detected_producer": _known("LibreDWG 0.13.4 external provider"),
        "detected_units": _unknown("AECCTX_DWG_UNITS_NOT_QUALIFIED"),
        "display_name": source.name,
        "embedding_policy": embedding_policy,
        "evidence_class": "observed",
        "extractor": {"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
        "media_type": "image/vnd.dwg",
        "prior_source_revision": _unknown("AECCTX_PRIOR_REVISION_NOT_PROVIDED"),
        "provenance": _provenance(instant, [], runtime_digest, "external-provider-source-registration"),
        "record_id": source_id,
        "record_type": "source",
        "record_version": "0.2",
        "safety_diagnostics": ["AECCTX_INPUT_TREATED_AS_DATA", "AECCTX_EXTERNAL_REFERENCES_NOT_OPENED"],
        "sha256": source_digest,
        "source_id": source_id,
        "source_refs": [],
        "spatial_reference": _unknown("AECCTX_DWG_CRS_UNSUPPORTED"),
    }
    if storage_ref:
        source_record["storage_ref"] = storage_ref
    elif embedding_policy == "redacted":
        source_record["redaction_reason"] = "AECCTX_SOURCE_CONTENT_REDACTED_BY_POLICY"

    primitives: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    observed_by_handle: dict[str, str] = {}
    conflicts = set(evidence.source_json["aecctx_handle_conflicts"])
    for item in evidence.source_json["OBJECTS"]:
        locator = str(item["aecctx_locator"])
        handle = str(item["aecctx_handle"])
        original_class = str(item.get("object", item.get("entity")))
        primitive_id = _stable_id("prim_dwg", source_digest, locator)
        if handle not in conflicts:
            observed_by_handle[handle] = primitive_id
        primitive = {
            "decoder_record": dict(item),
            "evidence_class": "observed",
            "handle_state": {"reason_code": "AECCTX_DWG_HANDLE_CONFLICT", "state": "conflicted"} if handle in conflicts else _known(handle),
            "original_class": original_class,
            "provenance": _provenance(instant, [source_id], runtime_digest, "libredwg-json-source-object"),
            "record_id": primitive_id,
            "record_type": "primitive",
            "record_version": "0.2",
            "source_refs": [{"locator": locator, "source_id": source_id}],
        }
        primitives.append(primitive)
        if original_class in {"LAYER", "BLOCK_HEADER", "INSERT", "TEXT", "MTEXT", "ATTRIB", "ATTDEF"}:
            entity_id = _stable_id("entity_dwg", source_digest, locator)
            entities.append(
                {
                    "entity_id": entity_id,
                    "evidence_class": "observed",
                    "kind": f"aecctx:source-{original_class.lower().replace('_', '-')}",
                    "label": _known(item["name"]) if isinstance(item.get("name"), str) and item["name"] else _unknown("AECCTX_DWG_LABEL_UNAVAILABLE"),
                    "original_class": original_class,
                    "parent_evidence_ids": [primitive_id],
                    "provenance": _provenance(instant, [primitive_id], runtime_digest, "dwg-neutral-source-index"),
                    "record_id": entity_id,
                    "record_type": "entity",
                    "record_version": "0.2",
                    "source_local_identifiers": {"dwg_handle": handle},
                    "source_refs": [{"locator": locator, "source_id": source_id}],
                }
            )

    try:
        import ezdxf

        document = ezdxf.read(io.StringIO(evidence.converted_dxf.decode("utf-8", errors="strict")))
    except Exception as error:
        raise DWGInputError("AECCTX_DWG_CONVERTED_DXF_INVALID", f"Converted DXF parse failed: {type(error).__name__}") from error
    seen: set[str] = set()
    converted_unmatched = 0
    containers = [(f"layout:{layout.name}", layout) for layout in document.layouts]
    containers += [(f"block:{block.name}", block) for block in document.blocks if not block.block_record.is_any_layout]
    for container, collection in containers:
        expanded = list(collection)
        for entity in list(collection):
            if entity.dxftype() == "INSERT":
                expanded.extend(entity.attribs)
        for entity in expanded:
            original_class = entity.dxftype()
            handle = str(entity.dxf.get("handle", "")).upper()
            if original_class not in CONVERTED_CLASSES or not handle or handle in seen:
                continue
            seen.add(handle)
            parent = observed_by_handle.get(handle)
            parents = [parent] if parent else [source_id]
            if parent is None:
                converted_unmatched += 1
            locator = f"dwg-dxf:handle:{handle}"
            primitive_id = _stable_id("prim_dwg_dxf", source_digest, locator)
            primitives.append(
                {
                    "container": _known(container),
                    "evidence_class": "derived",
                    "geometry": _geometry(entity),
                    "original_class": original_class,
                    "parent_evidence_ids": parents,
                    "provenance": _provenance(instant, parents, runtime_digest, "libredwg-converted-dxf-ezdxf-normalization"),
                    "record_id": primitive_id,
                    "record_type": "primitive",
                    "record_version": "0.2",
                    "representation_fidelity": {"class": "converted", "derived": True, "source_representation_ids": parents},
                    "source_refs": [{"locator": locator, "source_id": source_id}],
                }
            )

    diagnostics: list[dict[str, Any]] = []
    diagnostic_codes = [str(item["code"]) for item in provider_result.diagnostics]
    if converted_unmatched:
        diagnostic_codes.append("AECCTX_DWG_DXF_HANDLE_UNMATCHED")
    for index, code in enumerate(sorted(set(diagnostic_codes))):
        diagnostics.append(
            {
                "code": code,
                "evidence_class": "observed",
                "message": "External DWG provider reported bounded conversion or identity loss.",
                "provenance": _provenance(instant, [source_id], runtime_digest, "external-provider-diagnostic"),
                "record_id": _stable_id("diag_dwg", source_digest, f"{index}:{code}"),
                "record_type": "diagnostic",
                "record_version": "0.2",
                "severity": "warning",
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
    artifacts = [_records_artifact(path, records) for path, records in record_sets.items()]
    artifacts.extend(
        [
            PackageArtifact("evidence/libredwg-source.json", canonical_json(evidence.source_json), "application/vnd.aecctx.libredwg+json", "observed-decoder-source", True),
            PackageArtifact("evidence/converted-r2000.dxf", evidence.converted_dxf, "application/dxf", "converted-dxf", True),
            PackageArtifact(
                "context/index.md",
                (f"# DWG AECCTX package\n\nPackage `{package_id}` preserves {len(evidence.source_json['OBJECTS'])} observed LibreDWG objects. Converted DXF geometry is derived evidence; structured records remain authoritative.\n").encode(),
                "text/markdown",
                "agent-context",
                False,
            ),
        ]
    )
    if storage_ref:
        artifacts.append(PackageArtifact(storage_ref, source, "image/vnd.dwg", "embedded-source", True))
    capabilities = {name: str(provider_result.capability_report[name]["support_level"]) for name in CAPABILITIES}
    loss_summary = sorted(
        {str(code) for report in provider_result.capability_report.values() for code in report.get("reason_codes", [])}
        | set(diagnostic_codes)
    )
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
