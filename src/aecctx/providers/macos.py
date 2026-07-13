from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import ProviderRegistration
from .local import LocalProviderProfile


@dataclass(frozen=True, slots=True)
class MacOSSeatbeltProfile:
    sandbox_executable: Path = Path("/usr/bin/sandbox-exec")
    profile_id: str = "macos-seatbelt-v1"

    def preflight(self, registration: ProviderRegistration) -> None:
        LocalProviderProfile(platform="macos").preflight(registration)
