from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any, Iterable


VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[2]


def _requirement_name(requirement: str) -> str:
    match = re.match(r"[A-Za-z0-9_.-]+", requirement)
    if match is None:
        raise ValueError(f"invalid requirement: {requirement}")
    return match.group(0).lower()


def build_release_metadata(artifacts: Iterable[str | Path], *, output_directory: str | Path) -> dict[str, str]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    artifact_paths = sorted((Path(path) for path in artifacts), key=lambda path: path.name)
    checksums_path = output / "SHA256SUMS"
    checksum_lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in artifact_paths]
    checksums_path.write_text("".join(checksum_lines), encoding="utf-8")

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked_versions = {package["name"].lower(): package["version"] for package in lock["package"] if "version" in package}
    requirements = list(project.get("dependencies", []))
    for extra_requirements in project.get("optional-dependencies", {}).values():
        requirements.extend(extra_requirements)
    dependency_names = sorted({_requirement_name(requirement) for requirement in requirements if _requirement_name(requirement) != "aecctx"})
    packages = [
        {
            "SPDXID": "SPDXRef-Package-aecctx",
            "downloadLocation": "https://github.com/mandalorianuy/aecctx",
            "filesAnalyzed": False,
            "licenseConcluded": "Apache-2.0",
            "licenseDeclared": "Apache-2.0",
            "name": "aecctx",
            "supplier": "Organization: AECCTX contributors",
            "versionInfo": VERSION,
        }
    ]
    relationships = []
    for name in dependency_names:
        spdx_id = "SPDXRef-Package-" + re.sub(r"[^A-Za-z0-9.-]", "-", name)
        packages.append(
            {
                "SPDXID": spdx_id,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "name": name,
                "versionInfo": locked_versions.get(name, "NOASSERTION"),
            }
        )
        relationships.append({"relatedSpdxElement": spdx_id, "relationshipType": "DEPENDS_ON", "spdxElementId": "SPDXRef-Package-aecctx"})
    sbom = {
        "SPDXID": "SPDXRef-DOCUMENT",
        "creationInfo": {"created": "2026-07-11T00:00:00Z", "creators": ["Tool: aecctx-release/0.1.0"]},
        "dataLicense": "CC0-1.0",
        "documentNamespace": "https://aecctx.dev/spdx/aecctx-0.1.0",
        "name": "aecctx-0.1.0",
        "packages": packages,
        "relationships": relationships,
        "spdxVersion": "SPDX-2.3",
    }
    sbom_path = output / "aecctx-0.1.0.spdx.json"
    sbom_path.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"checksums": str(checksums_path), "sbom": str(sbom_path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+")
    parser.add_argument("--output-directory", required=True)
    arguments = parser.parse_args()
    print(json.dumps(build_release_metadata(arguments.artifacts, output_directory=arguments.output_directory), sort_keys=True))


if __name__ == "__main__":
    main()

