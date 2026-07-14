from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from aecctx.adapters.ifc import ingest_ifc
from aecctx.gate import GateError, canonical_gate_json, evaluate_gate, load_gate_policy


SHA256 = "0" * 64
FIXED_TIME = "2026-07-14T00:00:00Z"
SIMPLE_PROFILE = "aecctx-gate-v1-ids-1.0-simple-v1"
EXPANDED_PROFILE = "aecctx-gate-v1-ids-1.0-expanded-v1"
ROOT = Path(__file__).parents[1]
OFFICIAL = ROOT / "fixtures" / "v0.3" / "gate" / "official" / "cases"


def _policy_bytes(ids_profile: str | None) -> bytes:
    configuration = {"ids_sha256": SHA256, "source_id": "source:ifc"}
    if ids_profile is not None:
        configuration["ids_profile"] = ids_profile
    return canonical_gate_json(
        {
            "profile": "https://aecctx.dev/gate/v1",
            "policy_id": "ids-expanded",
            "policy_version": "1.0.0",
            "evaluation_time": FIXED_TIME,
            "checks": [
                {
                    "check_id": "ids",
                    "kind": "ids.specification",
                    "severity": "error",
                    "failure_mode": "fail",
                    "configuration": configuration,
                }
            ],
            "waivers": [],
        }
    )


def test_ids_profile_selector_is_backward_compatible_and_closed() -> None:
    absent = load_gate_policy(_policy_bytes(None))
    simple = load_gate_policy(_policy_bytes(SIMPLE_PROFILE))
    expanded = load_gate_policy(_policy_bytes(EXPANDED_PROFILE))

    assert dict(absent.checks[0].configuration) == {
        "ids_sha256": SHA256,
        "source_id": "source:ifc",
    }
    assert dict(simple.checks[0].configuration)["ids_profile"] == SIMPLE_PROFILE
    assert dict(expanded.checks[0].configuration)["ids_profile"] == EXPANDED_PROFILE

    try:
        load_gate_policy(_policy_bytes("aecctx-gate-v1-ids-unknown"))
    except GateError as error:
        assert error.code == "AECCTX_GATE_SCHEMA_INVALID"
    else:
        raise AssertionError("unknown IDS profiles must fail closed")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate(tmp_path: Path, source: Path) -> tuple[Path, str]:
    package = tmp_path / "candidate"
    result = ingest_ifc(source, package, created_at=FIXED_TIME)
    return package, result.source_id


def _expanded_policy(ids_path: Path, source_id: str, *, failure_mode: str = "fail"):
    configuration = {
        "ids_profile": EXPANDED_PROFILE,
        "ids_sha256": _digest(ids_path),
        "source_id": source_id,
    }
    payload = {
        "profile": "https://aecctx.dev/gate/v1",
        "policy_id": "ids-expanded",
        "policy_version": "1.0.0",
        "evaluation_time": FIXED_TIME,
        "checks": [
            {
                "check_id": "ids",
                "kind": "ids.specification",
                "severity": "error",
                "failure_mode": failure_mode,
                "configuration": configuration,
            }
        ],
        "waivers": [],
    }
    return load_gate_policy(canonical_gate_json(payload))


@pytest.mark.parametrize(
    "ids_path",
    sorted(OFFICIAL.rglob("*.ids")),
    ids=lambda path: path.relative_to(OFFICIAL).as_posix(),
)
def test_selected_official_expanded_case_matches_filename_expectation(
    tmp_path: Path, ids_path: Path
) -> None:
    source = ids_path.with_suffix(".ifc")
    package, source_id = _candidate(tmp_path, source)

    result = evaluate_gate(
        package,
        _expanded_policy(ids_path, source_id),
        ids_document=ids_path,
        ifc_source=source,
    )

    expected = "pass" if ids_path.name.startswith("pass-") else "fail"
    assert result.outcome == expected
    assert result.ids_digest == _digest(ids_path)


@pytest.mark.parametrize(
    ("replacements", "expected_code"),
    [
        ((("IFCRELASSIGNSTOGROUP", "IFCRELDEFINESBYPROPERTIES"),), "AECCTX_GATE_IDS_FACET_UNSUPPORTED"),
        (
            (
                ("<partOf relation=\"IFCRELASSIGNSTOGROUP\">", "<uri>"),
                ("</partOf>", "</uri>"),
            ),
            "AECCTX_GATE_IDS_FACET_UNSUPPORTED",
        ),
        ((("<xs:pattern value=\".*\" />", "<xs:minLength value=\"1\" />"),), "AECCTX_GATE_IDS_RESTRICTION_UNSUPPORTED"),
    ],
)
def test_unlisted_expanded_constructs_fail_as_policy_findings(
    tmp_path: Path, replacements: tuple[tuple[str, str], ...], expected_code: str
) -> None:
    source_ids = OFFICIAL / "partof" / "pass-a_grouped_element_passes_a_group_relationship.ids"
    source_ifc = source_ids.with_suffix(".ifc")
    ids_path = tmp_path / "unsupported.ids"
    text = source_ids.read_text(encoding="utf-8")
    for old, new in replacements:
        text = text.replace(old, new, 1)
    ids_path.write_text(text, encoding="utf-8")
    package, source_id = _candidate(tmp_path, source_ifc)

    result = evaluate_gate(
        package,
        _expanded_policy(ids_path, source_id),
        ids_document=ids_path,
        ifc_source=source_ifc,
    )

    assert result.outcome == "fail"
    assert expected_code in {finding.code for finding in result.findings}


@pytest.mark.parametrize("facet", ["geometry", "quantity"])
def test_geometry_and_quantity_facets_remain_unsupported(tmp_path: Path, facet: str) -> None:
    source = OFFICIAL / "ids" / "pass-required_specifications_need_at_least_one_applicable_entity_1_2.ifc"
    ids_path = tmp_path / f"{facet}.ids"
    ids_path.write_text(
        f'''<?xml version="1.0" encoding="utf-8"?>
<ids xmlns="http://standards.buildingsmart.org/IDS">
  <info><title>unsupported {facet}</title></info>
  <specifications>
    <specification name="unsupported {facet}" ifcVersion="IFC2X3 IFC4">
      <applicability maxOccurs="unbounded"><entity><name><simpleValue>IFCWALL</simpleValue></name></entity></applicability>
      <requirements><{facet}/></requirements>
    </specification>
  </specifications>
</ids>
''',
        encoding="utf-8",
    )
    package, source_id = _candidate(tmp_path, source)
    result = evaluate_gate(
        package,
        _expanded_policy(ids_path, source_id),
        ids_document=ids_path,
        ifc_source=source,
    )
    assert result.outcome == "fail"
    assert {finding.code for finding in result.findings} == {"AECCTX_GATE_IDS_FACET_UNSUPPORTED"}


def test_unlisted_specification_cardinality_fails_before_worker(tmp_path: Path) -> None:
    source_ids = OFFICIAL / "ids" / "pass-required_specifications_need_at_least_one_applicable_entity_1_2.ids"
    source_ifc = source_ids.with_suffix(".ifc")
    ids_path = tmp_path / "cardinality.ids"
    ids_path.write_text(
        source_ids.read_text(encoding="utf-8").replace(
            '<applicability maxOccurs="unbounded">',
            '<applicability minOccurs="2" maxOccurs="unbounded">',
            1,
        ),
        encoding="utf-8",
    )
    package, source_id = _candidate(tmp_path, source_ifc)
    result = evaluate_gate(
        package,
        _expanded_policy(ids_path, source_id),
        ids_document=ids_path,
        ifc_source=source_ifc,
    )
    assert result.outcome == "fail"
    assert {finding.code for finding in result.findings} == {"AECCTX_GATE_IDS_CARDINALITY_UNSUPPORTED"}
