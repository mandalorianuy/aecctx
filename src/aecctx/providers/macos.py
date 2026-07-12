from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import ProviderExecutionError, ProviderRegistration


@dataclass(frozen=True, slots=True)
class MacOSSeatbeltProfile:
    sandbox_executable: Path = Path("/usr/bin/sandbox-exec")
    profile_id: str = "macos-seatbelt-v1"

    def preflight(self, registration: ProviderRegistration) -> None:
        raise ProviderExecutionError(
            "AECCTX_PROVIDER_PROFILE_UNAVAILABLE",
            "macos-seatbelt-v1 cannot prove restricted host reads and the required memory axis",
        )
