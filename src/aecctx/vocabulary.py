from __future__ import annotations

import json
from importlib.resources import files


def _registry() -> dict[str, object]:
    resource = files("aecctx.schemas.v0_1").joinpath("neutral-vocabulary.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def resolve_neutral_term(term: str) -> str | None:
    if not term.startswith("aecctx:"):
        return None
    local_name = term.removeprefix("aecctx:")
    registry = _registry()
    known = set(registry["kinds"]) | set(registry["relation_types"])
    if local_name not in known:
        return None
    return f"{registry['namespace']}{local_name}"

