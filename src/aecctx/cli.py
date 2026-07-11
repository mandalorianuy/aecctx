from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from . import __version__
from .validation import ValidationResult, validate_package


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "version":
        if arguments.as_json:
            print(json.dumps(_envelope(True, {"version": __version__}, []), sort_keys=True, separators=(",", ":")))
        else:
            print(__version__)
        return 0
    result = validate_package(arguments.package)
    return _emit_result(result, as_json=arguments.as_json, info=arguments.command == "info")

