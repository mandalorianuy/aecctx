from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as metadata_version
from pathlib import Path
from typing import Any

from ..records import RecordStore
from .evaluator import finding_fingerprint
from .models import GateCheckPolicy, GateCheckResult, GateFinding, GateLimits
from .policy import canonical_gate_json


IDS_NAMESPACE = "http://standards.buildingsmart.org/IDS"
ALLOWED_SCHEMAS = frozenset({"IFC2X3", "IFC4"})
ALLOWED_FACETS = frozenset({"entity", "attribute", "classification", "property", "material"})
EXPECTED_DEPENDENCIES = {"ifctester": "0.8.5", "ifcopenshell": "0.8.5"}
_ACTIVE_XML_MARKERS = (b"<!DOCTYPE", b"<!ENTITY", b"XI:INCLUDE", b"XINCLUDE")


class IdsEvaluationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class WorkerExecution:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool


@dataclass(frozen=True, slots=True)
class UnsupportedIdsObservation:
    code: str
    subject_id: str
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class PreparedIdsInput:
    ids_bytes: bytes
    ids_digest: str
    source_bytes: bytes
    source_id: str
    source_digest: str
    source_schema: str
    unsupported: tuple[UnsupportedIdsObservation, ...]
    specification_count: int
    facet_count: int


def _configuration(check: GateCheckPolicy) -> dict[str, Any]:
    def thaw(value: Any) -> Any:
        if isinstance(value, tuple):
            if not value:
                return {}
            if all(
                isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str)
                for item in value
            ):
                return {item[0]: thaw(item[1]) for item in value}
            return [thaw(item) for item in value]
        return value

    return {key: thaw(value) for key, value in check.configuration}


def _read_regular(path: str | Path, *, limit: int, label: str) -> bytes:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise IdsEvaluationError("AECCTX_GATE_IDS_INPUT_INVALID", f"{label} must be a regular non-symlink file")
    try:
        size = candidate.stat().st_size
    except OSError as error:
        raise IdsEvaluationError("AECCTX_GATE_IDS_INPUT_INVALID", f"{label} cannot be inspected") from error
    if size > limit:
        raise IdsEvaluationError("AECCTX_GATE_IDS_LIMIT_EXCEEDED", f"{label} exceeds its byte limit")
    try:
        data = candidate.read_bytes()
    except OSError as error:
        raise IdsEvaluationError("AECCTX_GATE_IDS_INPUT_INVALID", f"{label} cannot be read") from error
    if len(data) != size or len(data) > limit:
        raise IdsEvaluationError("AECCTX_GATE_IDS_INPUT_INVALID", f"{label} changed during evaluation")
    return data


def _split_tag(tag: str) -> tuple[str, str]:
    if tag.startswith("{") and "}" in tag:
        namespace, local = tag[1:].split("}", 1)
        return namespace, local
    return "", tag


def _xml_depth(root: ET.Element) -> int:
    highest = 1
    stack = [(root, 1)]
    while stack:
        element, depth = stack.pop()
        highest = max(highest, depth)
        stack.extend((child, depth + 1) for child in element)
    return highest


def _preflight_xml(data: bytes, limits: GateLimits) -> tuple[tuple[UnsupportedIdsObservation, ...], int, int]:
    upper = data.upper()
    if any(marker in upper for marker in _ACTIVE_XML_MARKERS):
        raise IdsEvaluationError("AECCTX_GATE_IDS_XML_ACTIVE_CONTENT", "active XML constructs are forbidden")
    try:
        root = ET.fromstring(data)
    except (ET.ParseError, RecursionError) as error:
        raise IdsEvaluationError("AECCTX_GATE_IDS_XML_INVALID", "IDS XML is malformed") from error
    namespace, local = _split_tag(root.tag)
    if namespace != IDS_NAMESPACE or local != "ids":
        raise IdsEvaluationError("AECCTX_GATE_IDS_NAMESPACE_UNSUPPORTED", "IDS namespace is unsupported")
    if _xml_depth(root) > 32:
        raise IdsEvaluationError("AECCTX_GATE_IDS_LIMIT_EXCEEDED", "IDS XML nesting exceeds its limit")

    specifications: list[ET.Element] = []
    facets: list[tuple[str, ET.Element]] = []
    unsupported: dict[tuple[str, str], UnsupportedIdsObservation] = {}
    for element in root.iter():
        element_namespace, element_local = _split_tag(element.tag)
        if element_namespace == IDS_NAMESPACE and element_local == "specification":
            specifications.append(element)
            versions = set(str(element.attrib.get("ifcVersion", "")).split())
            if not versions or not versions <= ALLOWED_SCHEMAS:
                unsupported[("version", str(len(specifications) - 1))] = UnsupportedIdsObservation(
                    "AECCTX_GATE_IDS_FACET_UNSUPPORTED",
                    f"ids-specification:{len(specifications) - 1:04d}",
                    f"ids-specification:{len(specifications) - 1:04d}",
                )
        if element_namespace == IDS_NAMESPACE and element_local in ALLOWED_FACETS:
            facets.append((element_local, element))
        elif element_namespace == IDS_NAMESPACE and element_local in {"partOf", "uri"}:
            index = len(facets)
            unsupported[("facet", f"{element_local}:{index}")] = UnsupportedIdsObservation(
                "AECCTX_GATE_IDS_FACET_UNSUPPORTED",
                f"ids-facet:{element_local}:{index:04d}",
                f"ids-facet:{element_local}:{index:04d}",
            )
        if element_namespace == "http://www.w3.org/2001/XMLSchema" and element_local != "schema":
            index = len(unsupported)
            unsupported[("restriction", f"{element_local}:{index}")] = UnsupportedIdsObservation(
                "AECCTX_GATE_IDS_RESTRICTION_UNSUPPORTED",
                f"ids-restriction:{element_local}:{index:04d}",
                f"ids-restriction:{element_local}:{index:04d}",
            )
    if not specifications:
        raise IdsEvaluationError("AECCTX_GATE_IDS_XML_INVALID", "IDS contains no specifications")
    if len(specifications) > limits.max_ids_specifications or len(facets) > limits.max_ids_facets:
        raise IdsEvaluationError("AECCTX_GATE_IDS_LIMIT_EXCEEDED", "IDS structural count exceeds its limit")
    return tuple(unsupported[key] for key in sorted(unsupported)), len(specifications), len(facets)


def _source_record(store: RecordStore, source_id: str) -> dict[str, Any]:
    candidates = [
        dict(record.raw)
        for record in store.records.values()
        if record.record_type == "source" and record.raw.get("source_id") == source_id
    ]
    if len(candidates) != 1:
        raise IdsEvaluationError("AECCTX_GATE_IDS_SOURCE_ID_MISMATCH", "IDS source ID is not uniquely registered")
    return candidates[0]


def _source_schema(record: dict[str, Any]) -> str:
    detected = record.get("detected_format")
    if not isinstance(detected, dict) or detected.get("state") != "known" or not isinstance(detected.get("value"), str):
        raise IdsEvaluationError("AECCTX_GATE_IDS_SOURCE_SCHEMA_MISMATCH", "registered IFC schema is not known")
    schema = str(detected["value"]).upper()
    if schema not in ALLOWED_SCHEMAS:
        raise IdsEvaluationError("AECCTX_GATE_IDS_SOURCE_SCHEMA_MISMATCH", "registered IFC schema is unsupported")
    return schema


def dependency_versions() -> tuple[tuple[str, str], ...]:
    observed: list[tuple[str, str]] = []
    for name, expected in sorted(EXPECTED_DEPENDENCIES.items()):
        try:
            actual = metadata_version(name)
        except PackageNotFoundError as error:
            raise IdsEvaluationError("AECCTX_GATE_IDS_DEPENDENCY_UNAVAILABLE", f"optional dependency {name} is unavailable") from error
        if actual != expected:
            raise IdsEvaluationError(
                "AECCTX_GATE_IDS_DEPENDENCY_VERSION_MISMATCH",
                f"optional dependency {name} must be exactly {expected}",
            )
        observed.append((name, actual))
    return tuple(observed)


def prepare_ids_input(
    store: RecordStore,
    check: GateCheckPolicy,
    ids_path: str | Path,
    ifc_source_path: str | Path,
    limits: GateLimits,
) -> PreparedIdsInput:
    if check.kind != "ids.specification":
        raise TypeError("check must be an ids.specification GateCheckPolicy")
    configuration = _configuration(check)
    ids_bytes = _read_regular(ids_path, limit=limits.max_ids_bytes, label="IDS input")
    source_bytes = _read_regular(ifc_source_path, limit=limits.max_ifc_bytes, label="IFC source")
    ids_digest = hashlib.sha256(ids_bytes).hexdigest()
    source_digest = hashlib.sha256(source_bytes).hexdigest()
    if ids_digest != configuration["ids_sha256"]:
        raise IdsEvaluationError("AECCTX_GATE_IDS_DIGEST_MISMATCH", "IDS digest does not match policy")
    source_id = str(configuration["source_id"])
    source_record = _source_record(store, source_id)
    if source_record.get("sha256") != source_digest:
        raise IdsEvaluationError("AECCTX_GATE_IDS_SOURCE_HASH_MISMATCH", "IFC source digest does not match package evidence")
    schema = _source_schema(source_record)
    unsupported, specification_count, facet_count = _preflight_xml(ids_bytes, limits)
    return PreparedIdsInput(
        ids_bytes=ids_bytes,
        ids_digest=ids_digest,
        source_bytes=source_bytes,
        source_id=source_id,
        source_digest=source_digest,
        source_schema=schema,
        unsupported=unsupported,
        specification_count=specification_count,
        facet_count=facet_count,
    )


def _execute_worker(
    command: list[str],
    request_bytes: bytes,
    *,
    timeout_seconds: float,
    output_limit: int,
) -> WorkerExecution:
    environment = {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "PYTHONHASHSEED": "0",
    }
    for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR"):
        if key in os.environ:
            environment[key] = os.environ[key]
    creationflags = 0
    kwargs: dict[str, Any] = {"start_new_session": os.name != "nt"}
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs = {"creationflags": creationflags}
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=stdout_file,
            stderr=stderr_file,
            env=environment,
            **kwargs,
        )
        timed_out = False
        try:
            process.communicate(request_bytes, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                if os.name != "nt":
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    if os.name != "nt":
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                except OSError:
                    pass
                process.wait()
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read(output_limit + 1)
        stderr = stderr_file.read(4_097)
    return WorkerExecution(process.returncode, stdout, stderr, timed_out)


def _invoke_worker(request: dict[str, Any], limits: GateLimits) -> dict[str, Any]:
    command = [sys.executable, "-I", "-m", "aecctx.gate._ids_worker"]
    execution = _execute_worker(
        command,
        canonical_gate_json(request),
        timeout_seconds=limits.ids_timeout_seconds,
        output_limit=limits.max_result_bytes,
    )
    if execution.timed_out:
        raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_TIMEOUT", "IDS worker exceeded its timeout")
    if execution.returncode != 0:
        raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_CRASH", "IDS worker failed")
    if len(execution.stdout) > limits.max_result_bytes:
        raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_LIMIT", "IDS worker output exceeds its limit")
    try:
        response = json.loads(execution.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker output is not valid JSON") from error
    if not isinstance(response, dict) or set(response) != {"version", "ifc_schema", "specifications"}:
        raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker response envelope is invalid")
    if response["version"] != "1" or not isinstance(response["specifications"], list):
        raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker protocol version is invalid")
    return response


def _finding(
    check: GateCheckPolicy,
    *,
    code: str,
    subject_id: str,
    observed_state: str,
    evidence_refs: tuple[str, ...],
    message: str,
) -> GateFinding:
    check_id = f"aecctx.policy.{check.check_id}"
    return GateFinding(
        code=code,
        check_id=check_id,
        severity=check.severity,
        disposition=check.failure_mode,
        subject_id=subject_id,
        observed_state=observed_state,
        evidence_refs=evidence_refs,
        fingerprint=finding_fingerprint(
            check_id=check_id,
            code=code,
            subject_id=subject_id,
            observed_state=observed_state,
            evidence_refs=evidence_refs,
        ),
        message=message,
    )


def evaluate_prepared_ids_check(
    check: GateCheckPolicy,
    prepared: PreparedIdsInput,
    limits: GateLimits,
) -> GateCheckResult:
    base_refs = (
        f"ids:{prepared.ids_digest}",
        f"source:{prepared.source_id}:{prepared.source_digest}",
    )
    if prepared.unsupported:
        findings = tuple(
            _finding(
                check,
                code=item.code,
                subject_id=item.subject_id,
                observed_state="unsupported",
                evidence_refs=(*base_refs, item.evidence_ref),
                message="IDS contains a profile element outside the bounded evaluator",
            )
            for item in prepared.unsupported
        )
        return GateCheckResult(
            check_id=f"aecctx.policy.{check.check_id}",
            kind=check.kind,
            status=check.failure_mode,
            severity=check.severity,
            evidence_refs=base_refs,
            findings=findings,
            message="IDS contains unsupported bounded-profile content",
        )

    dependency_versions()
    with tempfile.TemporaryDirectory(prefix="aecctx-ids-") as temporary:
        root = Path(temporary)
        ids_snapshot = root / f"{prepared.ids_digest}.ids"
        source_snapshot = root / f"{prepared.source_digest}.ifc"
        ids_snapshot.write_bytes(prepared.ids_bytes)
        source_snapshot.write_bytes(prepared.source_bytes)
        request = {
            "version": "1",
            "ids_path": str(ids_snapshot),
            "ids_digest": prepared.ids_digest,
            "ifc_path": str(source_snapshot),
            "ifc_digest": prepared.source_digest,
            "ifc_schema": prepared.source_schema,
            "limits": {
                "max_specifications": limits.max_ids_specifications,
                "max_facets": limits.max_ids_facets,
                "max_entities": limits.max_ids_entities,
                "max_findings": limits.max_findings,
            },
        }
        response = _invoke_worker(request, limits)

    if response.get("ifc_schema") != prepared.source_schema:
        raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker returned the wrong IFC schema")
    specifications = response["specifications"]
    if len(specifications) != prepared.specification_count:
        raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker returned the wrong specification count")
    findings: list[GateFinding] = []
    evidence: list[str] = list(base_refs)
    entity_count = 0
    for index, specification in enumerate(specifications):
        if not isinstance(specification, dict) or set(specification) != {
            "id", "status", "applicable_entities", "failed_entities", "requirements"
        }:
            raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker specification is invalid")
        specification_id = f"ids-specification:{index:04d}"
        if specification["id"] != specification_id or not isinstance(specification["status"], bool):
            raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker specification identity is invalid")
        evidence.append(specification_id)
        entity_refs = specification["failed_entities"]
        applicable_refs = specification["applicable_entities"]
        requirements = specification["requirements"]
        if not all(isinstance(value, list) for value in (entity_refs, applicable_refs, requirements)):
            raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker entity lists are invalid")
        if any(not isinstance(item, str) or not item for item in (*entity_refs, *applicable_refs)):
            raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker entity reference is invalid")
        entity_count += len(entity_refs) + len(applicable_refs)
        if specification["status"] is False:
            refs = tuple((*base_refs, specification_id, *sorted(set(entity_refs))))
            findings.append(
                _finding(
                    check,
                    code="AECCTX_GATE_IDS_SPECIFICATION_FAILED",
                    subject_id=specification_id,
                    observed_state="failed",
                    evidence_refs=refs,
                    message="IDS specification did not conform",
                )
            )
        for requirement_index, requirement in enumerate(requirements):
            if not isinstance(requirement, dict) or set(requirement) != {"id", "kind", "status", "failed_entities"}:
                raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker requirement is invalid")
            requirement_id = f"{specification_id}:requirement:{requirement_index:04d}"
            if requirement["id"] != requirement_id or requirement["kind"] not in ALLOWED_FACETS or not isinstance(requirement["status"], bool):
                raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker requirement identity is invalid")
            failed_entities = requirement["failed_entities"]
            if not isinstance(failed_entities, list) or any(not isinstance(item, str) or not item for item in failed_entities):
                raise IdsEvaluationError("AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID", "IDS worker requirement entities are invalid")
            entity_count += len(failed_entities)
            evidence.append(requirement_id)
            if requirement["status"] is False:
                findings.append(
                    _finding(
                        check,
                        code="AECCTX_GATE_IDS_REQUIREMENT_FAILED",
                        subject_id=requirement_id,
                        observed_state="failed",
                        evidence_refs=tuple((*base_refs, requirement_id, *sorted(set(failed_entities)))),
                        message="IDS requirement did not conform",
                    )
                )
    if entity_count > limits.max_ids_entities or len(findings) > limits.max_findings:
        raise IdsEvaluationError("AECCTX_GATE_IDS_LIMIT_EXCEEDED", "IDS result exceeds its bounded counts")
    status = check.failure_mode if findings else "pass"
    return GateCheckResult(
        check_id=f"aecctx.policy.{check.check_id}",
        kind=check.kind,
        status=status,
        severity=check.severity,
        evidence_refs=tuple(evidence),
        findings=tuple(findings),
        message="IDS requirements satisfy policy" if not findings else "IDS requirements require policy action",
    )


def evaluate_ids_check(
    candidate_store: RecordStore,
    check: GateCheckPolicy,
    ids_path: str | Path,
    ifc_source_path: str | Path,
    limits: GateLimits,
) -> GateCheckResult:
    prepared = prepare_ids_input(candidate_store, check, ids_path, ifc_source_path, limits)
    return evaluate_prepared_ids_check(check, prepared, limits)
