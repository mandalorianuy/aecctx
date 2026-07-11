from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str
    severity: str = "error"
    path: str | None = None
    record_id: str | None = None
    suggested_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


class AECCTXError(Exception):
    """Base class for typed AECCTX failures."""

    code = "AECCTX_ERROR"


class PackageValidationError(AECCTXError):
    code = "AECCTX_PACKAGE_INVALID"

