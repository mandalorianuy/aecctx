from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ProviderDescriptor, ProviderExecutionError, ProviderLimits
from .protocol import _validate_schema, build_provider_request, validate_provider_response


def validate_provider_replay_corpus(corpus_path: str | Path) -> dict[str, Any]:
    """Validate committed provider exchanges without launching a provider runtime."""

    path = Path(corpus_path).resolve()
    try:
        corpus = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProviderExecutionError("AECCTX_PROVIDER_CORPUS_INVALID", f"Provider corpus is unreadable: {error}") from error
    if not isinstance(corpus, dict) or corpus.get("version") != "0.2.0" or not isinstance(corpus.get("entries"), list):
        raise ProviderExecutionError("AECCTX_PROVIDER_CORPUS_INVALID", "Provider corpus must declare version 0.2.0 and entries")

    repository_root = path.parents[2]
    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for configured in corpus["entries"]:
        if not isinstance(configured, dict) or not isinstance(configured.get("id"), str) or not configured["id"]:
            raise ProviderExecutionError("AECCTX_PROVIDER_CORPUS_INVALID", "Provider corpus entry requires a non-empty id")
        entry_id = configured["id"]
        if entry_id in seen_ids:
            raise ProviderExecutionError("AECCTX_PROVIDER_CORPUS_INVALID", f"Duplicate provider corpus entry: {entry_id}")
        seen_ids.add(entry_id)

        descriptor_raw = _read_json(repository_root, configured, "descriptor")
        _validate_schema(descriptor_raw, "provider-descriptor.schema.json")
        descriptor = ProviderDescriptor.from_dict(descriptor_raw)
        limits_raw = configured.get("limits", {})
        if not isinstance(limits_raw, dict):
            raise ProviderExecutionError("AECCTX_PROVIDER_CORPUS_INVALID", f"{entry_id}: limits must be an object")
        try:
            limits = ProviderLimits(**limits_raw)
        except TypeError as error:
            raise ProviderExecutionError("AECCTX_PROVIDER_CORPUS_INVALID", f"{entry_id}: invalid limits: {error}") from error
        input_path = _repo_path(repository_root, configured, "input")
        input_bytes = input_path.read_bytes()
        request = _read_json(repository_root, configured, "request")
        expected_request = build_provider_request(
            descriptor.provider_id,
            configured.get("action", "extract"),
            input_bytes,
            limits=limits,
            configuration=configured.get("configuration", {}),
        )
        if request != expected_request:
            raise ProviderExecutionError("AECCTX_PROVIDER_CORPUS_MISMATCH", f"{entry_id}: committed request is not reproducible")
        response = _read_json(repository_root, configured, "response")
        output_root = _repo_path(repository_root, configured, "output_root")
        result = validate_provider_response(response, request, descriptor, output_root, limits=limits)
        results.append(
            {
                "artifacts": len(result.artifacts),
                "id": entry_id,
                "provider_id": descriptor.provider_id,
                "valid": True,
            }
        )
    return {"entries": results, "ok": all(entry["valid"] for entry in results), "version": corpus["version"]}


def _repo_path(repository_root: Path, configured: dict[str, Any], field: str) -> Path:
    value = configured.get(field)
    if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
        raise ProviderExecutionError("AECCTX_PROVIDER_CORPUS_INVALID", f"Provider corpus field {field} must be a safe relative path")
    path = (repository_root / value).resolve()
    if repository_root != path and repository_root not in path.parents:
        raise ProviderExecutionError("AECCTX_PROVIDER_CORPUS_INVALID", f"Provider corpus field {field} escapes repository")
    return path


def _read_json(repository_root: Path, configured: dict[str, Any], field: str) -> dict[str, Any]:
    path = _repo_path(repository_root, configured, field)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProviderExecutionError("AECCTX_PROVIDER_CORPUS_INVALID", f"Provider corpus field {field} is unreadable: {error}") from error
    if not isinstance(value, dict):
        raise ProviderExecutionError("AECCTX_PROVIDER_CORPUS_INVALID", f"Provider corpus field {field} must contain an object")
    return value
