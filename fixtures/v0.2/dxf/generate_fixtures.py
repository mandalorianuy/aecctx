"""Generate the project-authored ACX-14 DXF conformance fixtures."""

from __future__ import annotations

from pathlib import Path

import ezdxf


ROOT = Path(__file__).parent


def build_profile() -> ezdxf.document.Drawing:
    doc = ezdxf.new("R2018", setup=True, units=ezdxf.units.M)
    doc.header["$TDCREATE"] = 2461229.5
    doc.header["$TDUPDATE"] = 2461229.5
    doc.appids.add("AECCTX_TEST")
    model = doc.modelspace()

    material = doc.materials.new("AECCTX_TEST_MATERIAL")
    material.dxf.description = "Project-authored neutral test material"

    line = model.add_line((0, 0, 1), (2, 0, 3), dxfattribs={"layer": "0"})
    line.set_xdata("AECCTX_TEST", [(1000, "source-semantic-tag"), (1070, 14)])
    line.dxf.material_handle = material.dxf.handle
    extension = line.new_extension_dict()
    xrecord = extension.add_xrecord("AECCTX_METADATA")
    xrecord.reset([(1, "extension-record"), (40, 2.5), (310, b"\x00\x01\x02")])
    nested = extension.add_dictionary("AECCTX_NESTED")
    nested_value = doc.objects.add_dictionary_var(owner=nested.dxf.handle, value="nested-value")
    nested.add("VALUE", nested_value)

    point = model.add_point((1, 2, 4))
    face = model.add_3dface([(0, 0, 0), (2, 0, 0), (2, 2, 1), (0, 2, 1)])

    polyline = model.add_polyline3d([(0, 0, 0), (0, 1, 2), (0, 2, 4)])
    polyline.dxf.layer = "0"
    polyface = model.add_polyface()
    polyface.append_face([(0, 0, 0), (1, 0, 0), (1, 1, 1), (0, 1, 1)])
    polymesh = model.add_polymesh((2, 2))
    polymesh.set_mesh_vertex((0, 0), (3, 0, 0))
    polymesh.set_mesh_vertex((0, 1), (3, 1, 0))
    polymesh.set_mesh_vertex((1, 0), (4, 0, 1))
    polymesh.set_mesh_vertex((1, 1), (4, 1, 1))

    mesh = model.add_mesh()
    with mesh.edit_data() as data:
        data.vertices = [(5, 0, 0), (6, 0, 0), (6, 1, 1), (5, 1, 1)]
        data.faces = [(0, 1, 2, 3)]

    circle = model.add_circle((2, 3, 1), 0.5, dxfattribs={"extrusion": (0, 1, 1)})
    circle.dxf.layer = "0"

    leaf = doc.blocks.new("AECCTX_LEAF", base_point=(0, 0, 0))
    leaf.add_3dface([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)])
    leaf.add_attdef("ROLE", (0, 0, 0), "neutral-component")
    parent = doc.blocks.new("AECCTX_PARENT", base_point=(0, 0, 0))
    parent.add_blockref("AECCTX_LEAF", (1, 2, 3), dxfattribs={"xscale": 2, "yscale": 2, "zscale": 2, "rotation": 30})
    insert = model.add_blockref("AECCTX_PARENT", (10, 20, 30), dxfattribs={"rotation": 15})
    insert.add_attrib("ROLE", "source-attribute", (10, 20, 30))

    group = doc.groups.new("AECCTX_GROUP", description="source-native group", selectable=True)
    group.set_data([line, point, face])

    doc.blocks.new("AECCTX_XREF", dxfattribs={"flags": 4, "xref_path": "never-opened.dxf"})
    solid = model.add_3dsolid()
    solid.sab = b"AECCTX project-authored opaque ACIS payload"
    return doc


def build_cycle() -> ezdxf.document.Drawing:
    doc = ezdxf.new("R2000", units=ezdxf.units.M)
    doc.header["$TDCREATE"] = 2461229.5
    doc.header["$TDUPDATE"] = 2461229.5
    first = doc.blocks.new("CYCLE_A")
    second = doc.blocks.new("CYCLE_B")
    first.add_blockref("CYCLE_B", (0, 0, 0))
    second.add_blockref("CYCLE_A", (0, 0, 0))
    doc.modelspace().add_blockref("CYCLE_A", (0, 0, 0))
    return doc


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    profile = build_profile()
    profile.saveas(ROOT / "r2018-semantics-3d-ascii.dxf", fmt="asc")
    profile.saveas(ROOT / "r2018-semantics-3d-binary.dxf", fmt="bin")
    build_cycle().saveas(ROOT / "r2000-cyclic-inserts.dxf", fmt="asc")
    (ROOT / "malformed-tags.dxf").write_bytes(b"0\nSECTION\n2\nENTITIES\n0\nLINE\n10\nnot-a-number\n0\nEOF\n")


if __name__ == "__main__":
    main()
