#!/usr/bin/env python3
"""Generate deterministic Apache-2.0 ACX-36 fixtures and hash-bound corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import ifcopenshell


ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = ROOT / "fixtures/v0.3/gate"
PROJECT_ROOT = FIXTURE_ROOT / "project"
OFFICIAL_ROOT = FIXTURE_ROOT / "official"
CORPUS = ROOT / "conformance/v0.3/gate-corpus.json"
PROFILE = "aecctx-gate-v1-ids-1.0-expanded-v1"
UPSTREAM_COMMIT = "1effec6f419798ce09617416d258a35bdc58320a"


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _project_ifc() -> bytes:
    model = ifcopenshell.open(ROOT / "fixtures/v0.2/gate/ids/project-wall.ifc")
    model.header.file_name.name = "expanded-profile.ifc"
    model.header.file_name.time_stamp = "2026-07-14T00:00:00Z"
    model.header.file_name.authorization = "Apache-2.0"
    assembly = model.create_entity(
        "IfcElementAssembly", GlobalId="0AAAAAAAAAAAAAAAAAAAAA", Name="Aggregate Assembly", PredefinedType="USERDEFINED"
    )
    aggregate_part = model.create_entity(
        "IfcBuildingElementProxy", GlobalId="1AAAAAAAAAAAAAAAAAAAAA", Name="Aggregate Part", PredefinedType="NOTDEFINED"
    )
    model.create_entity(
        "IfcRelAggregates", GlobalId="2AAAAAAAAAAAAAAAAAAAAA", RelatingObject=assembly, RelatedObjects=[aggregate_part]
    )
    group = model.create_entity("IfcGroup", GlobalId="3AAAAAAAAAAAAAAAAAAAAA", Name="Project Group")
    grouped_part = model.create_entity(
        "IfcBuildingElementProxy", GlobalId="4AAAAAAAAAAAAAAAAAAAAA", Name="Grouped Part", PredefinedType="NOTDEFINED"
    )
    model.create_entity(
        "IfcRelAssignsToGroup", GlobalId="5AAAAAAAAAAAAAAAAAAAAA", RelatedObjects=[grouped_part], RelatingGroup=group
    )
    contained_part = model.create_entity(
        "IfcBuildingElementProxy", GlobalId="6AAAAAAAAAAAAAAAAAAAAA", Name="Contained Part", PredefinedType="NOTDEFINED"
    )
    model.create_entity(
        "IfcRelContainedInSpatialStructure",
        GlobalId="7AAAAAAAAAAAAAAAAAAAAA",
        RelatedElements=[contained_part],
        RelatingStructure=model.by_type("IfcBuildingStorey")[0],
    )
    nesting_assembly = model.create_entity(
        "IfcElementAssembly", GlobalId="8AAAAAAAAAAAAAAAAAAAAA", Name="Nesting Assembly", PredefinedType="USERDEFINED"
    )
    nested_part = model.create_entity(
        "IfcBuildingElementProxy", GlobalId="9AAAAAAAAAAAAAAAAAAAAA", Name="Nested Part", PredefinedType="NOTDEFINED"
    )
    model.create_entity(
        "IfcRelNests", GlobalId="0BBBBBBBBBBBBBBBBBBBBB", RelatingObject=nesting_assembly, RelatedObjects=[nested_part]
    )
    model.create_entity("IfcSurfaceStyleRefraction", RefractionIndex=5.0)
    return (model.to_string().rstrip() + "\n").encode()


def _ids(title: str, applicability: str, requirements: str = "", *, min_occurs: str = "", max_occurs: str = "unbounded") -> bytes:
    minimum = f' minOccurs="{min_occurs}"' if min_occurs else ""
    maximum = f' maxOccurs="{max_occurs}"' if max_occurs else ""
    requirements_xml = f"<requirements>{requirements}</requirements>" if requirements else ""
    return f'''<?xml version="1.0" encoding="utf-8"?>
<ids xmlns="http://standards.buildingsmart.org/IDS" xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <info><title>{title}</title></info>
  <specifications><specification name="{title}" ifcVersion="IFC4">
    <applicability{minimum}{maximum}>{applicability}</applicability>{requirements_xml}
  </specification></specifications>
</ids>
'''.encode()


def _entity(name: str) -> str:
    return f"<entity><name><simpleValue>{name}</simpleValue></name></entity>"


def _partof(relation: str, parent: str) -> str:
    return f'<partOf relation="{relation}">{_entity(parent)}</partOf>'


def _restriction_attribute(name: str, base: str, children: str) -> str:
    return (
        f"<attribute><name><simpleValue>{name}</simpleValue></name><value>"
        f'<xs:restriction base="{base}">{children}</xs:restriction></value></attribute>'
    )


def _project_cases() -> list[tuple[str, bytes, str]]:
    cases: list[tuple[str, bytes, str]] = []
    relations = {
        "aggregates": ("IFCRELAGGREGATES", "IFCELEMENTASSEMBLY", "IFCSITE", "Aggregate Part"),
        "group": ("IFCRELASSIGNSTOGROUP", "IFCGROUP", "IFCSITE", "Grouped Part"),
        "containment": ("IFCRELCONTAINEDINSPATIALSTRUCTURE", "IFCBUILDINGSTOREY", "IFCSITE", "Contained Part"),
        "nests": ("IFCRELNESTS", "IFCELEMENTASSEMBLY", "IFCSITE", "Nested Part"),
    }
    for case_id, (relation, parent, wrong_parent, part_name) in relations.items():
        applicability = _restriction_attribute("Name", "xs:string", f'<xs:enumeration value="{part_name}" />')
        for expectation, selected_parent in (("pass", parent), ("fail", wrong_parent)):
            name = f"partof-{case_id}-{expectation}"
            cases.append((name, _ids(name, applicability, _partof(relation, selected_parent)), expectation))

    wall = _entity("IFCWALL")
    restriction_pairs = {
        "pattern": (
            _restriction_attribute("Name", "xs:string", '<xs:pattern value="Minimal .*" />'),
            _restriction_attribute("Name", "xs:string", '<xs:pattern value="Other .*" />'),
        ),
        "enumeration": (
            _restriction_attribute("Name", "xs:string", '<xs:enumeration value="Minimal Wall" /><xs:enumeration value="Other Wall" />'),
            _restriction_attribute("Name", "xs:string", '<xs:enumeration value="Other Wall" />'),
        ),
    }
    for case_id, pair in restriction_pairs.items():
        for expectation, requirement in zip(("pass", "fail"), pair, strict=True):
            name = f"restriction-{case_id}-{expectation}"
            cases.append((name, _ids(name, wall, requirement), expectation))

    surface = _entity("IFCSURFACESTYLEREFRACTION")
    numeric_pairs = {
        "inclusive": ('<xs:minInclusive value="0" /><xs:maxInclusive value="5" />', '<xs:minInclusive value="6" />'),
        "exclusive": ('<xs:minExclusive value="4" /><xs:maxExclusive value="6" />', '<xs:maxExclusive value="5" />'),
    }
    for case_id, pair in numeric_pairs.items():
        for expectation, children in zip(("pass", "fail"), pair, strict=True):
            name = f"restriction-{case_id}-{expectation}"
            requirement = _restriction_attribute("RefractionIndex", "xs:double", children)
            cases.append((name, _ids(name, surface, requirement), expectation))

    cardinalities = [
        ("cardinality-required-pass", _entity("IFCWALL"), "1", "unbounded", "pass"),
        ("cardinality-required-fail", _entity("IFCWINDOW"), "1", "unbounded", "fail"),
        ("cardinality-optional-present-pass", _entity("IFCWALL"), "0", "unbounded", "pass"),
        ("cardinality-optional-absent-pass", _entity("IFCWINDOW"), "0", "unbounded", "pass"),
        ("cardinality-prohibited-pass", _entity("IFCWINDOW"), "0", "0", "pass"),
        ("cardinality-prohibited-fail", _entity("IFCWALL"), "0", "0", "fail"),
    ]
    for name, applicability, minimum, maximum, expectation in cardinalities:
        cases.append((name, _ids(name, applicability, min_occurs=minimum, max_occurs=maximum), expectation))
    return cases


def _official_origin() -> dict[str, object]:
    files = []
    for path in sorted((OFFICIAL_ROOT / "cases").rglob("*")):
        if path.is_file():
            relative = path.relative_to(OFFICIAL_ROOT).as_posix()
            files.append(
                {
                    "path": f"fixtures/v0.3/gate/official/{relative}",
                    "sha256": _sha(path),
                    "upstream_path": f"Documentation/ImplementersDocumentation/TestCases/{relative.removeprefix('cases/')}",
                }
            )
    return {
        "commit": UPSTREAM_COMMIT,
        "license": "CC-BY-ND-4.0",
        "release": "v1.0.0",
        "repository": "https://github.com/buildingSMART/IDS",
        "files": files,
    }


def generate(project_root: Path, corpus_path: Path, origin_path: Path) -> None:
    if project_root.exists():
        shutil.rmtree(project_root)
    source = project_root / "expanded-profile.ifc"
    _write(source, _project_ifc())
    entries: list[dict[str, object]] = []
    for case_id, data, expected in _project_cases():
        path = project_root / "cases" / f"{case_id}.ids"
        _write(path, data)
        entries.append(
            {
                "case_id": f"project-{case_id}",
                "expected": expected,
                "ids": f"fixtures/v0.3/gate/project/cases/{case_id}.ids",
                "ids_sha256": _sha(path),
                "ifc": "fixtures/v0.3/gate/project/expanded-profile.ifc",
                "ifc_sha256": _sha(source),
                "license": "Apache-2.0",
                "origin": "AECCTX project-authored",
            }
        )
    origin = _official_origin()
    for item in origin["files"]:
        if item["path"].endswith(".ids"):
            ids_path = ROOT / item["path"]
            ifc_path = ids_path.with_suffix(".ifc")
            entries.append(
                {
                    "case_id": "official-" + ids_path.relative_to(OFFICIAL_ROOT / "cases").with_suffix("").as_posix().replace("/", "-"),
                    "expected": "pass" if ids_path.name.startswith("pass-") else "fail",
                    "ids": item["path"],
                    "ids_sha256": item["sha256"],
                    "ifc": ifc_path.relative_to(ROOT).as_posix(),
                    "ifc_sha256": _sha(ifc_path),
                    "license": "CC-BY-ND-4.0",
                    "origin": "buildingSMART IDS v1.0.0 unchanged",
                }
            )
    corpus = {
        "claim_id": "quality-gate.ids-expanded",
        "claim_status": "public",
        "corpus_version": "1",
        "entries": entries,
        "fixture_id": "v03-gate-acx36",
        "profile": PROFILE,
        "runtime": {"ifcopenshell": "0.8.5", "ifctester": "0.8.5"},
    }
    _write(corpus_path, _canonical(corpus))
    _write(origin_path, _canonical(origin))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    origin = OFFICIAL_ROOT / "ORIGIN.json"
    if not args.check:
        generate(PROJECT_ROOT, CORPUS, origin)
        print("aecctx v0.3 gate fixtures: generated")
        return 0
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        candidate_project = temp / "project"
        candidate_corpus = temp / "gate-corpus.json"
        candidate_origin = temp / "ORIGIN.json"
        generate(candidate_project, candidate_corpus, candidate_origin)
        for candidate in sorted(path for path in candidate_project.rglob("*") if path.is_file()):
            committed = PROJECT_ROOT / candidate.relative_to(candidate_project)
            if not committed.is_file() or committed.read_bytes() != candidate.read_bytes():
                raise SystemExit(f"project fixture drift: {candidate.relative_to(candidate_project).as_posix()}")
        if not CORPUS.is_file() or CORPUS.read_bytes() != candidate_corpus.read_bytes():
            raise SystemExit("gate corpus drift")
        if not origin.is_file() or origin.read_bytes() != candidate_origin.read_bytes():
            raise SystemExit("official provenance/hash drift")
    print("aecctx v0.3 gate fixtures: deterministic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
