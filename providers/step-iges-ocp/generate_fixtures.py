from __future__ import annotations

import re
from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.IFSelect import IFSelect_RetDone
from OCP.IGESControl import IGESControl_Writer
from OCP.Interface import Interface_Static
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopoDS import TopoDS_Compound
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf, gp_Vec


OUTPUT = Path("/output")
FIXED_TIME = "2026-07-12T00:00:00"


def assembly_shape() -> TopoDS_Compound:
    box = BRepPrimAPI_MakeBox(10.0, 20.0, 30.0).Shape()
    transform = gp_Trsf()
    transform.SetTranslation(gp_Vec(40.0, 0.0, 0.0))
    placed = box.Moved(TopLoc_Location(transform))
    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    builder.Add(compound, box)
    builder.Add(compound, placed)
    return compound


def normalize_step(path: Path) -> None:
    text = path.read_text(encoding="ascii")
    text = re.sub(
        r"(FILE_NAME\s*\(\s*'[^']*'\s*,\s*)'[^']*'",
        rf"\1'{FIXED_TIME}'",
        text,
        count=1,
    )
    text = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    path.write_text(text, encoding="ascii", newline="\n")


def write_step(filename: str, schema: str, shape: object) -> None:
    writer = STEPControl_Writer()
    if not Interface_Static.SetCVal_s("write.step.schema", schema):
        raise RuntimeError(f"STEP schema mode unavailable: {schema}")
    Interface_Static.SetIVal_s("write.step.assembly", 1)
    writer.Model(True)
    if writer.Transfer(shape, STEPControl_AsIs) != IFSelect_RetDone:
        raise RuntimeError(f"STEP transfer failed: {filename}")
    path = OUTPUT / filename
    if writer.Write(str(path)) != IFSelect_RetDone:
        raise RuntimeError(f"STEP write failed: {filename}")
    normalize_step(path)


def write_iges(filename: str, shape: object) -> None:
    writer = IGESControl_Writer("MM", 1)
    if not writer.AddShape(shape):
        raise RuntimeError(f"IGES transfer failed: {filename}")
    if not writer.Write(str(OUTPUT / filename)):
        raise RuntimeError(f"IGES write failed: {filename}")
    path = OUTPUT / filename
    text = path.read_text(encoding="ascii")
    text = re.sub(r"15H[0-9]{8}\.[0-9]{6}", "15H20260712.000000", text)
    path.write_text(text, encoding="ascii", newline="\n")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    box = BRepPrimAPI_MakeBox(10.0, 20.0, 30.0).Shape()
    write_step("ap203-part.step", "AP203", box)
    write_step("ap214-assembly.step", "AP214IS", assembly_shape())
    write_step("ap242-part.step", "AP242DIS", box)
    write_iges("iges53-part.igs", box)


if __name__ == "__main__":
    main()
