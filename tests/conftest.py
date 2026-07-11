from __future__ import annotations

import shutil
from pathlib import Path

import pytest


@pytest.fixture
def minimal_package(tmp_path: Path) -> Path:
    source = Path(__file__).parents[1] / "fixtures" / "minimal-aecctx"
    target = tmp_path / "minimal-aecctx"
    shutil.copytree(source, target)
    return target

