from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from . import __version__
from .context import render_context
from .diff import diff_packages
from .ingest import ingest_opaque
from .query import QuerySyntaxError, query_package
from .validation import ValidationResult, validate_package


class IngestVersionError(ValueError):
    code = "AECCTX_INGEST_VERSION_UNSUPPORTED"


def _envelope(ok: bool, data: Any, diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    return {"data": data, "diagnostics": diagnostics, "ok": ok}


def _emit_result(result: ValidationResult, *, as_json: bool, info: bool = False) -> int:
    diagnostics = [item.to_dict() for item in result.diagnostics]
    if info and result.manifest is not None:
        data = {
            key: result.manifest[key]
            for key in ("aecctx_version", "package_id", "logical_digest", "package_form", "source_ids", "capabilities", "loss_summary")
        }
    else:
        data = {"package_id": result.package_id, "valid": result.valid}
    if as_json:
        print(json.dumps(_envelope(result.valid, data, diagnostics), sort_keys=True, separators=(",", ":")))
    elif result.valid:
        print(f"AECCTX package valid: {result.package_id}")
    else:
        for diagnostic in result.diagnostics:
            location = f" [{diagnostic.path}]" if diagnostic.path else ""
            print(f"{diagnostic.code}{location}: {diagnostic.message}", file=sys.stderr)
    return 0 if result.valid else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aecctx")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "info"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("package")
        command_parser.add_argument("--json", action="store_true", dest="as_json")
    version = subparsers.add_parser("version")
    version.add_argument("--json", action="store_true", dest="as_json")
    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("source")
    ingest.add_argument("--output", required=True)
    ingest.add_argument("--form", choices=("directory", "zip"), default="directory")
    ingest.add_argument("--embedding-policy", choices=("external", "embedded", "redacted"), default="external")
    ingest.add_argument("--adapter", choices=("auto", "opaque", "ifc", "dxf", "pdf", "image", "geometry"), default="auto")
    ingest.add_argument("--aecctx-version", choices=("0.1.0", "0.2.0"), default="0.1.0")
    ingest.add_argument("--created-at")
    ingest.add_argument("--json", action="store_true", dest="as_json")
    query = subparsers.add_parser("query")
    query.add_argument("package")
    query.add_argument("expression")
    query.add_argument("--json", action="store_true", dest="as_json")
    diff = subparsers.add_parser("diff")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.add_argument("--json", action="store_true", dest="as_json")
    context = subparsers.add_parser("context")
    context.add_argument("package")
    context.add_argument("--profile", choices=("agent", "audit", "compact"), default="agent")
    context.add_argument("--token-budget", type=int, default=40_000)
    context.add_argument("--chunk-token-budget", type=int, default=4_000)
    context.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "version":
        if arguments.as_json:
            print(json.dumps(_envelope(True, {"version": __version__}, []), sort_keys=True, separators=(",", ":")))
        else:
            print(__version__)
        return 0
    if arguments.command == "ingest":
        try:
            adapter = arguments.adapter
            if adapter == "auto":
                from .adapters.ifc import IFCPlugin
                from .adapters.dxf import DXFPlugin
                from .adapters.image import ImagePlugin
                from .adapters.pdf import PDFPlugin
                from .adapters.geometry import GeometryPlugin

                with open(arguments.source, "rb") as source_handle:
                    prefix = source_handle.read(64 * 1024)
                if IFCPlugin().probe(prefix)["confidence"] == 1.0:
                    adapter = "ifc"
                elif DXFPlugin().probe(prefix)["confidence"] == 1.0:
                    adapter = "dxf"
                elif PDFPlugin().probe(prefix)["confidence"] == 1.0:
                    adapter = "pdf"
                elif GeometryPlugin().probe(prefix)["confidence"] == 1.0:
                    adapter = "geometry"
                elif ImagePlugin().probe(prefix)["confidence"] == 1.0:
                    adapter = "image"
                else:
                    adapter = "opaque"
            if arguments.aecctx_version == "0.2.0" and adapter != "ifc":
                raise IngestVersionError(f"Adapter {adapter} has no governed AECCTX v0.2 profile")
            if adapter == "ifc":
                from .adapters.ifc import ingest_ifc

                result = ingest_ifc(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                    aecctx_version=arguments.aecctx_version,
                )
            elif adapter == "dxf":
                from .adapters.dxf import ingest_dxf

                result = ingest_dxf(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                )
            elif adapter == "pdf":
                from .adapters.pdf import ingest_pdf

                result = ingest_pdf(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                )
            elif adapter == "image":
                from .adapters.image import ingest_image

                result = ingest_image(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                )
            elif adapter == "geometry":
                from .adapters.geometry import ingest_geometry

                result = ingest_geometry(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                )
            else:
                result = ingest_opaque(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                )
        except (OSError, ValueError) as error:
            diagnostic = {"code": getattr(error, "code", "AECCTX_INGEST_FAILED"), "message": str(error), "severity": "error"}
            if arguments.as_json:
                print(json.dumps(_envelope(False, None, [diagnostic]), sort_keys=True, separators=(",", ":")))
            else:
                print(f"AECCTX_INGEST_FAILED: {error}", file=sys.stderr)
            return 2
        data = {
            "logical_digest": result.logical_digest,
            "output": str(result.output),
            "package_id": result.package_id,
            "source_id": result.source_id,
            "support": "partial" if adapter in {"ifc", "dxf", "pdf", "image", "geometry"} else "opaque",
            "adapter": adapter,
            "aecctx_version": arguments.aecctx_version,
        }
        if arguments.as_json:
            print(json.dumps(_envelope(True, data, []), sort_keys=True, separators=(",", ":")))
        else:
            print(f"AECCTX opaque package created: {result.output}")
        return 0
    if arguments.command == "query":
        try:
            result = query_package(arguments.package, arguments.expression)
        except (QuerySyntaxError, ValueError) as error:
            diagnostic = {"code": getattr(error, "code", "AECCTX_QUERY_FAILED"), "message": str(error), "severity": "error"}
            if arguments.as_json:
                print(json.dumps(_envelope(False, None, [diagnostic]), sort_keys=True, separators=(",", ":")))
            else:
                print(f"{diagnostic['code']}: {error}", file=sys.stderr)
            return 2
        data = result.to_dict()
        if arguments.as_json:
            print(json.dumps(_envelope(True, data, []), sort_keys=True, separators=(",", ":")))
        else:
            for record_id in result.record_ids:
                print(record_id)
        return 0
    if arguments.command == "diff":
        result = diff_packages(arguments.before, arguments.after)
        data = result.to_dict()
        if arguments.as_json:
            print(json.dumps(_envelope(True, data, []), sort_keys=True, separators=(",", ":")))
        else:
            print(json.dumps(data, indent=2, sort_keys=True))
        return 1 if result.semantic_change else 0
    if arguments.command == "context":
        try:
            projection = render_context(
                arguments.package,
                profile=arguments.profile,
                token_budget=arguments.token_budget,
                chunk_token_budget=arguments.chunk_token_budget,
            )
        except ValueError as error:
            diagnostic = {"code": "AECCTX_CONTEXT_FAILED", "message": str(error), "severity": "error"}
            if arguments.as_json:
                print(json.dumps(_envelope(False, None, [diagnostic]), sort_keys=True, separators=(",", ":")))
            else:
                print(f"AECCTX_CONTEXT_FAILED: {error}", file=sys.stderr)
            return 2
        if arguments.as_json:
            print(json.dumps(_envelope(True, projection.to_dict(), []), sort_keys=True, separators=(",", ":")))
        else:
            sys.stdout.buffer.write(projection.files["context/index.md"])
        return 0
    result = validate_package(arguments.package)
    return _emit_result(result, as_json=arguments.as_json, info=arguments.command == "info")
