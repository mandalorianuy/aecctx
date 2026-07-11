from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path


def test_bundled_manifest_schema_is_available_offline() -> None:
    schema_path = files("aecctx.schemas.v0_1").joinpath("manifest.schema.json")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["$id"] == "https://aecctx.dev/schemas/v0.1/manifest.schema.json"


def test_bundled_schemas_match_normative_repository_copies() -> None:
    root = files("aecctx.schemas.v0_1")
    repository = Path(__file__).parents[1] / "schemas" / "v0.1"

    for name in ("manifest.schema.json", "record.schema.json"):
        bundled = json.loads(root.joinpath(name).read_text(encoding="utf-8"))
        normative = json.loads((repository / name).read_text(encoding="utf-8"))
        assert bundled == normative
