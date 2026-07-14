from __future__ import annotations

import json
import argparse
from pathlib import Path

from aecctx.crs import build_runtime_registry_document


HERE = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    registry = build_runtime_registry_document(author={"id": "aecctx-conformance", "type": "project"})
    expected = json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    target = HERE / "crs-registry.json"
    if arguments.check:
        if not target.is_file() or target.read_text(encoding="utf-8") != expected:
            raise SystemExit("AECCTX_CRS_FIXTURE_DRIFT")
    else:
        target.write_text(expected, encoding="utf-8")


if __name__ == "__main__":
    main()
