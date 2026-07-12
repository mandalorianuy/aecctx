"""Generate the project-authored ACX-18 R2000 DXF source fixture."""

from __future__ import annotations

from pathlib import Path

import ezdxf


ROOT = Path(__file__).parent
ezdxf.options.write_fixed_meta_data_for_testing = True


def build_profile() -> ezdxf.document.Drawing:
    doc = ezdxf.new("R2000", units=ezdxf.units.M)
    doc.header["$TDCREATE"] = 2461234.5
    doc.header["$TDUPDATE"] = 2461234.5
    doc.layers.add("AECCTX_DETAIL", color=3)
    doc.appids.add("AECCTX_EVIDENCE")
    model = doc.modelspace()

    line = model.add_line((0, 0, 0), (4, 0, 0), dxfattribs={"layer": "AECCTX_DETAIL"})
    line.set_xdata("AECCTX_EVIDENCE", [(1000, "../../never-opened/external.dwg")])
    model.add_circle((2, 2, 0), 1.0)
    model.add_arc((5, 2, 0), 1.5, 15, 225)
    model.add_lwpolyline([(0, 4), (2, 5), (4, 4)], dxfattribs={"layer": "AECCTX_DETAIL"})
    model.add_point((3, 3, 1))
    model.add_3dface([(0, 0, 0), (1, 0, 1), (1, 1, 1), (0, 1, 0)])
    model.add_text("AECCTX R2000", dxfattribs={"insert": (0, 6), "height": 0.4})
    model.add_mtext("Observed source text", dxfattribs={"insert": (0, 7), "char_height": 0.35})

    block = doc.blocks.new("AECCTX_COMPONENT", base_point=(0, 0, 0))
    block.add_line((0, 0), (1, 0))
    block.add_circle((0.5, 0.5), 0.25)
    block.add_attdef("ROLE", (0, 0.8), "neutral")
    first = model.add_blockref("AECCTX_COMPONENT", (8, 1))
    first.add_attrib("ROLE", "first", (8, 1.8))
    second = model.add_blockref("AECCTX_COMPONENT", (10, 1), dxfattribs={"rotation": 30})
    second.add_attrib("ROLE", "second", (10, 1.8))

    paper = doc.layouts.new("AECCTX_SHEET")
    paper.add_text("Paper evidence", dxfattribs={"insert": (1, 1), "height": 0.25})
    doc.blocks.new("AECCTX_XREF", dxfattribs={"flags": 4, "xref_path": "../../never-opened/reference.dwg"})
    return doc


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    build_profile().saveas(ROOT / "r2000-profile.dxf", fmt="asc")


if __name__ == "__main__":
    main()
