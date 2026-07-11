from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .package import PackageArtifact, PackageWriter, canonical_json, hash_file


CAPABILITIES = (
    "identity",
    "hierarchy",
    "properties",
    "relationships",
    "text",
    "2d_geometry",
    "3d_geometry",
    "materials_styles",
    "georeferencing",
    "validation",
)


@dataclass(frozen=True, slots=True)
class IngestResult:
    package_id: str
    source_id: str
    logical_digest: str
    output: Path


def _timestamp(value: str | None) -> str:
    if value is not None:
        return value
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _unknown(reason_code: str) -> dict[str, str]:
    return {"reason_code": reason_code, "state": "unknown"}


def ingest_opaque(
    source_path: str | Path,
    output_path: str | Path,
    *,
    created_at: str | None = None,
    embedding_policy: str = "external",
    package_form: str = "directory",
) -> IngestResult:
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("source_path must be a regular file")
    if output.exists():
        raise FileExistsError(output)
    if embedding_policy not in {"external", "embedded", "redacted"}:
        raise ValueError("embedding_policy must be external, embedded, or redacted")
    if package_form not in {"directory", "zip"}:
        raise ValueError("package_form must be directory or zip")

    source_digest, source_bytes = hash_file(source)
    instant = _timestamp(created_at)
    identity = source_digest[:24]
    source_id = f"src_{identity}"
    package_id = f"pkg_{identity}"
    media_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    provenance = {
        "method": "opaque-registration",
        "parent_record_ids": [],
        "producer_id": "aecctx.core.opaque",
        "producer_version": "0.1.0.dev0",
        "recorded_at": instant,
    }
    storage_ref = f"sources/content/{source.name}" if embedding_policy == "embedded" else None
    source_record: dict[str, Any] = {
        "acquisition_origin": "local-file",
        "byte_size": source_bytes,
        "declared_format": _unknown("AECCTX_SOURCE_FORMAT_NOT_DECLARED"),
        "declared_units": _unknown("AECCTX_SOURCE_UNITS_NOT_DECLARED"),
        "detected_format": _unknown("AECCTX_NO_FORMAT_ADAPTER"),
        "detected_producer": _unknown("AECCTX_NO_FORMAT_ADAPTER"),
        "detected_units": _unknown("AECCTX_NO_FORMAT_ADAPTER"),
        "display_name": source.name,
        "embedding_policy": embedding_policy,
        "extractor": {"plugin_id": "aecctx.core.opaque", "plugin_version": "0.1.0.dev0"},
        "media_type": media_type,
        "prior_source_revision": _unknown("AECCTX_PRIOR_REVISION_NOT_PROVIDED"),
        "provenance": provenance,
        "record_id": source_id,
        "record_type": "source",
        "record_version": "0.1",
        "safety_diagnostics": ["AECCTX_ACTIVE_CONTENT_NOT_EXECUTED"],
        "sha256": source_digest,
        "source_id": source_id,
        "source_refs": [],
        "spatial_reference": _unknown("AECCTX_NO_FORMAT_ADAPTER"),
    }
    if storage_ref is not None:
        source_record["storage_ref"] = storage_ref
    elif embedding_policy == "redacted":
        source_record["redaction_reason"] = "AECCTX_SOURCE_CONTENT_REDACTED_BY_POLICY"

    primitive_id = f"prim_opaque_{identity}"
    primitive = {
        "container": _unknown("AECCTX_NO_FORMAT_ADAPTER"),
        "extraction_confidence": {"band": "full", "method": "exact-byte-registration"},
        "original_class": "opaque-file",
        "provenance": {**provenance, "parent_record_ids": [source_id]},
        "record_id": primitive_id,
        "record_type": "primitive",
        "record_version": "0.1",
        "source_refs": [{"locator": "byte-range:0-*", "source_id": source_id}],
        "value": {"reason_code": "AECCTX_NO_FORMAT_ADAPTER", "state": "unsupported"},
    }
    capabilities = {name: ("full" if name in {"identity", "validation"} else "opaque") for name in CAPABILITIES}
    loss_summary = [f"AECCTX_OPAQUE_{name.upper()}" for name in CAPABILITIES if capabilities[name] != "full"]
    diagnostics = []
    for index, capability in enumerate(name for name in CAPABILITIES if capabilities[name] != "full"):
        diagnostics.append(
            {
                "affected_count": 1,
                "capability": capability,
                "code": f"AECCTX_OPAQUE_{capability.upper()}",
                "fallback": "Install and select a conforming format adapter; retain this opaque evidence record.",
                "message": f"No adapter interpreted the source capability: {capability}",
                "provenance": {**provenance, "parent_record_ids": [source_id, primitive_id]},
                "record_id": f"diag_opaque_{index:02d}_{identity}",
                "record_type": "diagnostic",
                "record_version": "0.1",
                "severity": "info",
                "source_refs": [{"locator": "byte-range:0-*", "source_id": source_id}],
                "support_level": "opaque",
            }
        )

    artifacts: dict[str, tuple[bytes | Path, str, str, bool]] = {
        "context/index.md": (
            (
                f"# AECCTX opaque package\n\nPackage `{package_id}` registers source `{source_id}` exactly by SHA-256. "
                "No source semantics or geometry were inferred. Authoritative evidence is in `sources/` and `evidence/`.\n"
            ).encode("utf-8"),
            "text/markdown",
            "agent-context",
            False,
        ),
        "diagnostics/diagnostics.jsonl": (b"".join(canonical_json(item) for item in diagnostics), "application/x-ndjson", "diagnostics", True),
        "evidence/assertions.jsonl": (b"", "application/x-ndjson", "assertions", True),
        "evidence/primitives.jsonl": (canonical_json(primitive), "application/x-ndjson", "primitives", True),
        "model/entities.jsonl": (b"", "application/x-ndjson", "entities", True),
        "model/relations.jsonl": (b"", "application/x-ndjson", "relations", True),
        "sources/sources.jsonl": (canonical_json(source_record), "application/x-ndjson", "sources", True),
    }
    if storage_ref is not None:
        artifacts[storage_ref] = (source, media_type, "embedded-source", True)

    artifact_inputs = [
        PackageArtifact(
            path=logical_path,
            content=value,
            media_type=artifact_media_type,
            role=role,
            authoritative=authoritative,
        )
        for logical_path, (value, artifact_media_type, role, authoritative) in artifacts.items()
    ]
    manifest = PackageWriter(output, package_form=package_form).write(
        package_id=package_id,
        created_at=instant,
        source_ids=[source_id],
        capabilities=capabilities,
        loss_summary=loss_summary,
        embedding_policy=embedding_policy,
        producer={"name": "aecctx", "version": "0.1.0.dev0"},
        artifacts=artifact_inputs,
    )
    return IngestResult(package_id, source_id, manifest["logical_digest"], output)
