from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from .adapters.dxf import ingest_dxf
from .adapters.geometry import ingest_geometry
from .adapters.ifc import ingest_ifc
from .adapters.image import ingest_image
from .adapters.pdf import ingest_pdf
from .ingest import ingest_opaque
from .package import PackageReader
from .validation import validate_package


INGESTERS: dict[str, Callable[..., Any]] = {
    "dxf": ingest_dxf,
    "geometry": ingest_geometry,
    "ifc": ingest_ifc,
    "image": ingest_image,
    "opaque": ingest_opaque,
    "pdf": ingest_pdf,
}


def run_corpus(corpus_path: str | Path) -> dict[str, Any]:
    path = Path(corpus_path).resolve()
    root = path.parents[2]
    corpus = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    with tempfile.TemporaryDirectory(prefix="aecctx-conformance-") as temporary:
        temporary_root = Path(temporary)
        for index, configured in enumerate(corpus["entries"]):
            source = root / configured["source"]
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            first = temporary_root / f"{index:02d}-a.aecctx"
            second = temporary_root / f"{index:02d}-b.aecctx"
            ingester = INGESTERS[configured["adapter"]]
            ingester(source, first, created_at=corpus["created_at"], package_form="zip")
            ingester(source, second, created_at=corpus["created_at"], package_form="zip")
            validation = validate_package(first)
            manifest = PackageReader(first).manifest
            entries.append(
                {
                    "adapter": configured["adapter"],
                    "claims_match": manifest["capabilities"] == configured["capabilities"] and source_hash == configured["sha256"],
                    "deterministic": first.read_bytes() == second.read_bytes(),
                    "id": configured["id"],
                    "logical_digest": manifest["logical_digest"],
                    "valid": validation.valid,
                }
            )
    return {
        "entries": entries,
        "ok": all(entry["valid"] and entry["deterministic"] and entry["claims_match"] for entry in entries),
        "version": corpus["version"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus")
    arguments = parser.parse_args()
    report = run_corpus(arguments.corpus)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

