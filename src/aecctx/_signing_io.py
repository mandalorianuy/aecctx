from __future__ import annotations

import base64
import binascii
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from .signing import SigningError


_BASE64URL = re.compile(r"[A-Za-z0-9_-]+")


class _DuplicateJSONName(ValueError):
    pass


def _object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONName(key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(value)


def _normalize_nfc(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise _DuplicateJSONName(normalized_key)
            normalized[normalized_key] = _normalize_nfc(item)
        return normalized
    return value


def load_strict_json(data: bytes, *, label: str, max_bytes: int) -> Any:
    if len(data) > max_bytes:
        raise SigningError("AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED", f"{label} exceeds its byte limit")
    try:
        text = data.decode("utf-8")
        value = json.loads(text, object_pairs_hook=_object_from_pairs, parse_constant=_reject_constant)
        return _normalize_nfc(value)
    except _DuplicateJSONName as error:
        raise SigningError("AECCTX_SIGNING_JSON_DUPLICATE_KEY", f"{label} contains duplicate JSON names") from error
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise SigningError("AECCTX_SIGNING_JSON_INVALID", f"{label} is not valid strict JSON") from error


def canonical_json_nfc(value: Any, *, terminal_lf: bool) -> bytes:
    try:
        normalized = _normalize_nfc(value)
        text = json.dumps(normalized, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    except _DuplicateJSONName as error:
        raise SigningError("AECCTX_SIGNING_JSON_DUPLICATE_KEY", "value contains duplicate normalized JSON names") from error
    except (TypeError, ValueError) as error:
        raise SigningError("AECCTX_SIGNING_JSON_INVALID", "value cannot be represented as canonical JSON") from error
    return (text + ("\n" if terminal_lf else "")).encode("utf-8")


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def base64url_decode(value: str, *, expected_bytes: int | None = None) -> bytes:
    if not value or "=" in value or _BASE64URL.fullmatch(value) is None:
        raise SigningError("AECCTX_SIGNING_BASE64URL_INVALID", "base64url value is not canonical")
    try:
        decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (binascii.Error, ValueError) as error:
        raise SigningError("AECCTX_SIGNING_BASE64URL_INVALID", "base64url value is invalid") from error
    if base64url_encode(decoded) != value or (expected_bytes is not None and len(decoded) != expected_bytes):
        raise SigningError("AECCTX_SIGNING_BASE64URL_INVALID", "base64url value has invalid length or encoding")
    return decoded


def read_bounded_regular_file(path: str | Path, *, max_bytes: int, label: str) -> bytes:
    candidate = Path(path)
    try:
        if candidate.is_symlink() or not candidate.is_file():
            raise SigningError("AECCTX_SIGNING_FILE_UNSAFE", f"{label} must be a regular non-symlink file")
        if candidate.stat().st_size > max_bytes:
            raise SigningError("AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED", f"{label} exceeds its byte limit")
        with candidate.open("rb") as handle:
            data = handle.read(max_bytes + 1)
    except SigningError:
        raise
    except OSError as error:
        raise SigningError("AECCTX_SIGNING_FILE_UNSAFE", f"{label} cannot be read safely") from error
    if len(data) > max_bytes:
        raise SigningError("AECCTX_SIGNING_INPUT_LIMIT_EXCEEDED", f"{label} exceeds its byte limit")
    return data
