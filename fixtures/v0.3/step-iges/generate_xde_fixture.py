from __future__ import annotations

import re
from pathlib import Path

from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Controller
from OCP.TCollection import TCollection_ExtendedString, TCollection_HAsciiString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_ColorSurf, XCAFDoc_DocumentTool
from OCP.gp import gp_Trsf, gp_Vec


OUTPUT = Path("/output/ap214-xde.step")


def _normalize(path: Path) -> None:
    text = path.read_text(encoding="ascii")
    text = re.sub(r"(FILE_NAME\s*\(\s*)'[^']*'", r"\1'ap214-xde.step'", text, count=1)
    text = re.sub(r"(FILE_NAME\s*\(\s*'[^']*'\s*,\s*)'[^']*'", r"\1'2026-07-14T00:00:00'", text, count=1)
    path.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="ascii", newline="\n")


def main() -> None:
    document = TDocStd_Document(TCollection_ExtendedString("XCAF"))
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    color_tool = XCAFDoc_DocumentTool.ColorTool_s(document.Main())
    layer_tool = XCAFDoc_DocumentTool.LayerTool_s(document.Main())
    material_tool = XCAFDoc_DocumentTool.MaterialTool_s(document.Main())

    first = BRepPrimAPI_MakeBox(10.0, 20.0, 30.0).Shape()
    transform = gp_Trsf()
    transform.SetTranslation(gp_Vec(40.0, 5.0, 0.0))
    second = BRepPrimAPI_MakeBox(5.0, 10.0, 15.0).Shape().Moved(TopLoc_Location(transform))
    labels = [shape_tool.AddShape(first, False), shape_tool.AddShape(second, False)]
    for index, label in enumerate(labels, 1):
        TDataStd_Name.Set_s(label, TCollection_ExtendedString(f"Part {chr(64 + index)}"))
        color_tool.SetColor(label, Quantity_Color(0.2 * index, 0.3, 0.6, Quantity_TOC_RGB), XCAFDoc_ColorSurf)
        layer_tool.SetLayer(label, TCollection_ExtendedString(f"AECCTX-LAYER-{index}"))
        material_tool.SetMaterial(
            label,
            TCollection_HAsciiString("Steel" if index == 1 else "Aluminium"),
            TCollection_HAsciiString("Project-authored conformance material"),
            7850.0 if index == 1 else 2700.0,
            TCollection_HAsciiString("density"),
            TCollection_HAsciiString("kg/m3"),
        )

    STEPControl_Controller.Init_s()
    if not Interface_Static.SetCVal_s("write.step.schema", "AP214IS"):
        raise RuntimeError("AP214IS unavailable")
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    writer = STEPCAFControl_Writer()
    writer.SetNameMode(True)
    writer.SetColorMode(True)
    writer.SetLayerMode(True)
    writer.SetMaterialMode(True)
    writer.SetPropsMode(True)
    if not writer.Transfer(document, STEPControl_AsIs):
        raise RuntimeError("XDE transfer failed")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if writer.Write(str(OUTPUT)) != IFSelect_RetDone:
        raise RuntimeError("STEP write failed")
    _normalize(OUTPUT)


if __name__ == "__main__":
    main()
