#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import sys
import tempfile
from pathlib import Path

import ezdxf
from ezdxf import xref


HERE = Path(__file__).resolve().parent
FIXED = "2026-07-14T00:00:00Z"
ezdxf.options.write_fixed_meta_data_for_testing = True


def _write(doc: object, path: Path, *, binary: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.filename = str(path)
    if binary:
        stream = io.BytesIO()
        doc.write(stream, fmt="bin")
        payload = stream.getvalue()
    else:
        stream = io.StringIO(newline="\n")
        doc.write(stream, fmt="asc")
        payload = doc.encode(stream.getvalue())
    path.write_bytes(payload)


def _curves(version: str) -> object:
    doc = ezdxf.new(version, setup=True)
    doc.header["$TDCREATE"] = 2461234.5
    doc.header["$TDUPDATE"] = 2461234.5
    msp = doc.modelspace()
    msp.add_line((0, 0, 0), (3, 2, 1), dxfattribs={"layer": "NEUTRAL_EVIDENCE"})
    if version != "R12":
        # Keep generated fixture coordinates byte-stable across libm
        # implementations.  Axis-aligned directions avoid platform-specific
        # normalization rounding while still exercising both entity types.
        msp.add_ray((1, 1, 0), (2, 1, 0))
        msp.add_xline((2, 1, 0), (2, 2, 0))
        msp.add_ellipse((2, 2, 1), major_axis=(3, 0, 0), ratio=0.5, start_param=0, end_param=math.pi * 1.5)
        msp.add_spline([(0, 0, 0), (1, 2, 1), (3, 3, 0), (5, 1, 2)], degree=3)
        msp.add_mline([(0, 0), (2, 0), (4, 0)])
    if version == "R2007":
        helix = msp.add_helix(radius=1.5, pitch=0.75, turns=2.5)
        helix.transform(ezdxf.math.Matrix44.translate(8, 0, 0))
        helix.control_points = [
            tuple(round(float(component), 12) for component in point)
            for point in helix.control_points
        ]
        mesh = msp.add_mesh()
        with mesh.edit_data() as data:
            data.vertices = [(0, 0, 0), (2, 0, 0), (2, 2, 1), (0, 2, 0)]
            data.faces = [(0, 1, 2, 3)]
    return doc


def _bundle(root: Path) -> None:
    child = ezdxf.new("R2007")
    child.modelspace().add_ellipse((1, 1, 0), major_axis=(2, 0, 0), ratio=0.4)
    nested = ezdxf.new("R2004")
    nested.modelspace().add_spline([(0, 0), (1, 1), (2, 0)])
    xref.define(child, "NESTED", "refs/nested/nested.dxf")
    child.modelspace().add_blockref("NESTED", (5, 0))
    host = ezdxf.new("R2018")
    xref.define(host, "CHILD", "refs/child.dxf")
    host.modelspace().add_blockref("CHILD", (10, 20, 0))
    _write(host, root / "root.dxf")
    _write(child, root / "refs/child.dxf")
    _write(nested, root / "refs/nested/nested.dxf")
    entries = []
    for logical, role in (("root.dxf", "root"), ("refs/child.dxf", "xref"), ("refs/nested/nested.dxf", "xref")):
        data = (root / logical).read_bytes()
        entries.append({"bytes": len(data), "media_type": "application/dxf", "path": logical, "role": role, "sha256": hashlib.sha256(data).hexdigest()})
    (root / "source-bundle.json").write_text(json.dumps({"entries": entries, "root": "root.dxf", "version": "0.2"}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generate(root: Path) -> None:
    _write(_curves("R12"), root / "r12-curves-ascii.dxf")
    _write(_curves("R2004"), root / "r2004-curves-binary.dxf", binary=True)
    _write(_curves("R2007"), root / "r2007-curves-ascii.dxf")
    _bundle(root / "xref-bundle")


def main() -> int:
    if os.environ.get("PYTHONHASHSEED") != "0":
        environment = dict(os.environ)
        environment["PYTHONHASHSEED"] = "0"
        os.execve(sys.executable, [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], environment)
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        generate(HERE)
        return 0
    with tempfile.TemporaryDirectory() as temporary:
        generated = Path(temporary)
        generate(generated)
        expected = {
            path.relative_to(HERE): path.read_bytes()
            for path in HERE.rglob("*")
            if path.is_file() and path.name != "generate_fixtures.py" and "__pycache__" not in path.parts
        }
        actual = {path.relative_to(generated): path.read_bytes() for path in generated.rglob("*") if path.is_file()}
        if expected == actual:
            return 0
        for relative in sorted(set(expected) | set(actual), key=str):
            committed = expected.get(relative)
            regenerated = actual.get(relative)
            if committed == regenerated:
                continue
            committed_hash = hashlib.sha256(committed).hexdigest() if committed is not None else "missing"
            regenerated_hash = hashlib.sha256(regenerated).hexdigest() if regenerated is not None else "missing"
            print(f"fixture drift: {relative} committed={committed_hash} regenerated={regenerated_hash}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
