from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import ifcopenshell


ROOT = Path(__file__).resolve().parent
FIXED_TIME = "2026-07-13T00:00:00Z"
AUTHOR = "AECCTX contributors"


def _header(model: ifcopenshell.file, name: str) -> None:
    model.header.file_description.description = ("ViewDefinition[DesignTransferView]",)
    model.header.file_name.name = name
    model.header.file_name.time_stamp = FIXED_TIME
    model.header.file_name.author = (AUTHOR,)
    model.header.file_name.organization = ("AECCTX",)
    model.header.file_name.preprocessor_version = "IfcOpenShell 0.8.5"
    model.header.file_name.originating_system = "AECCTX fixture generator"
    model.header.file_name.authorization = "Apache-2.0"


def _base(name: str) -> tuple[ifcopenshell.file, object, object, object, object]:
    model = ifcopenshell.file(schema="IFC4X3_ADD2")
    millimetre = model.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Prefix="MILLI", Name="METRE")
    metre = model.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE")
    units = model.create_entity("IfcUnitAssignment", Units=[millimetre])
    point_3d = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
    placement_3d = model.create_entity("IfcAxis2Placement3D", Location=point_3d)
    point_2d = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
    placement_2d = model.create_entity("IfcAxis2Placement2D", Location=point_2d)
    model_context = model.create_entity(
        "IfcGeometricRepresentationContext",
        ContextIdentifier="Model",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1.0e-5,
        WorldCoordinateSystem=placement_3d,
    )
    plan_context = model.create_entity(
        "IfcGeometricRepresentationContext",
        ContextIdentifier="Plan",
        ContextType="Plan",
        CoordinateSpaceDimension=2,
        Precision=1.0e-5,
        WorldCoordinateSystem=placement_2d,
    )
    model.create_entity(
        "IfcProject",
        GlobalId="3sm9$kPeP3C89AwjZkTn8$",
        Name=f"AECCTX {name}",
        RepresentationContexts=[model_context, plan_context],
        UnitsInContext=units,
    )
    projected = model.create_entity(
        "IfcProjectedCRS",
        Name="EPSG:32721",
        GeodeticDatum="WGS84",
        MapProjection="Transverse Mercator",
        MapZone="21S",
        MapUnit=metre,
    )
    subcontext = model.create_entity(
        "IfcGeometricRepresentationSubContext",
        ContextIdentifier="Annotation",
        ContextType="Plan",
        ParentContext=plan_context,
        TargetScale=0.01,
        TargetView="PLAN_VIEW",
    )
    _header(model, name)
    return model, model_context, projected, subcontext, placement_2d


def _product(model: ifcopenshell.file, name: str, representations: list[object] | None) -> None:
    shape = None if representations is None else model.create_entity("IfcProductDefinitionShape", Representations=representations)
    origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
    axis = model.create_entity("IfcAxis2Placement2D", Location=origin)
    local = model.create_entity("IfcLocalPlacement", RelativePlacement=axis)
    model.create_entity(
        "IfcAnnotation",
        GlobalId={
            "positive": "0sm9$kPeP3C89AwjZkTn8$",
            "empty": "1sm9$kPeP3C89AwjZkTn8$",
            "degraded": "2sm9$kPeP3C89AwjZkTn8$",
            "absent": "3sm9$kPeP3C89AwjZkTn8$",
        }[name],
        Name=f"AECCTX {name}",
        ObjectPlacement=local,
        Representation=shape,
        PredefinedType="NOTDEFINED",
    )


def positive() -> ifcopenshell.file:
    model, model_context, projected, subcontext, _ = _base("ifc4x3-curves-annotations-scaled.ifc")
    model.create_entity(
        "IfcMapConversionScaled",
        SourceCRS=model_context,
        TargetCRS=projected,
        Eastings=500000.0,
        Northings=6100000.0,
        OrthogonalHeight=12.5,
        XAxisAbscissa=1.0,
        XAxisOrdinate=0.0,
        Scale=0.001,
        FactorX=2.0,
        FactorY=3.0,
        FactorZ=4.0,
    )
    location = model.create_entity("IfcCartesianPoint", Coordinates=(100.0, 200.0))
    direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0))
    position = model.create_entity("IfcAxis2Placement2D", Location=location, RefDirection=direction)
    circle = model.create_entity("IfcCircle", Position=position, Radius=50.0)
    ellipse = model.create_entity("IfcEllipse", Position=position, SemiAxis1=80.0, SemiAxis2=40.0)
    trimmed = model.create_entity(
        "IfcTrimmedCurve",
        BasisCurve=circle,
        Trim1=[model.create_entity("IfcParameterValue", 0.0)],
        Trim2=[model.create_entity("IfcParameterValue", 1.570796326795)],
        SenseAgreement=True,
        MasterRepresentation="PARAMETER",
    )
    segment_a = model.create_entity(
        "IfcCompositeCurveSegment", Transition="CONTINUOUS", SameSense=True, ParentCurve=trimmed
    )
    segment_b = model.create_entity(
        "IfcCompositeCurveSegment", Transition="DISCONTINUOUS", SameSense=False, ParentCurve=ellipse
    )
    composite = model.create_entity("IfcCompositeCurve", Segments=[segment_a, segment_b], SelfIntersect=False)
    points = model.create_entity(
        "IfcCartesianPointList2D",
        CoordList=[(0.0, 0.0), (100.0, 0.0), (150.0, 50.0), (100.0, 100.0)],
    )
    line = model.create_entity("IfcLineIndex", (1, 2))
    arc = model.create_entity("IfcArcIndex", (2, 3, 4))
    indexed = model.create_entity("IfcIndexedPolyCurve", Points=points, Segments=[line, arc], SelfIntersect=False)
    text = model.create_entity("IfcTextLiteral", Literal="AECCTX plan note", Placement=position, Path="RIGHT")
    fill = model.create_entity("IfcAnnotationFillArea", OuterBoundary=circle, InnerBoundaries=[ellipse])

    font = model.create_entity("IfcPreDefinedTextFont", Name="sans-serif")
    text_style = model.create_entity(
        "IfcTextStyle", Name="AECCTX text", TextFontStyle=font, ModelOrDraughting=False
    )
    curve_style = model.create_entity("IfcCurveStyle", Name="AECCTX curve", ModelOrDraughting=False)
    hatching = model.create_entity(
        "IfcFillAreaStyleHatching",
        HatchLineAppearance=curve_style,
        StartOfNextHatchLine=model.create_entity("IfcPositiveLengthMeasure", 10.0),
        HatchLineAngle=0.785398163397,
    )
    fill_style = model.create_entity(
        "IfcFillAreaStyle", Name="AECCTX fill", FillStyles=[hatching], ModelOrDraughting=False
    )
    model.create_entity("IfcStyledItem", Item=text, Styles=[text_style], Name="text direct")
    model.create_entity("IfcStyledItem", Item=circle, Styles=[curve_style], Name="curve direct")
    model.create_entity("IfcStyledItem", Item=fill, Styles=[fill_style], Name="fill direct")
    representation = model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=subcontext,
        RepresentationIdentifier="Annotation",
        RepresentationType="Annotation2D",
        Items=[circle, ellipse, trimmed, composite, indexed, text, fill],
    )
    _product(model, "positive", [representation])
    return model


def degraded() -> ifcopenshell.file:
    model, model_context, projected, subcontext, _ = _base("ifc4x3-degraded.ifc")
    model.create_entity(
        "IfcMapConversionScaled",
        SourceCRS=model_context,
        TargetCRS=projected,
        Eastings=500000.0,
        Northings=6100000.0,
        OrthogonalHeight=12.5,
        XAxisAbscissa=1.0,
        XAxisOrdinate=0.0,
        Scale=0.001,
        FactorX=1.0,
        FactorY=1.0,
        FactorZ=0.0,
    )
    location = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
    position = model.create_entity("IfcAxis2Placement2D", Location=location)
    invalid_circle = model.create_entity("IfcCircle", Position=position, Radius=-1.0)
    overlong = model.create_entity("IfcTextLiteral", Literal="x" * 1025, Placement=position, Path="RIGHT")
    vector = model.create_entity(
        "IfcVector",
        Orientation=model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0)),
        Magnitude=1.0,
    )
    unsupported_line = model.create_entity("IfcLine", Pnt=location, Dir=vector)
    failed = model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=subcontext,
        RepresentationIdentifier="Annotation",
        RepresentationType="Annotation2D",
        Items=[invalid_circle, overlong, unsupported_line],
    )
    empty = model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=subcontext,
        RepresentationIdentifier="FootPrint",
        RepresentationType="Curve2D",
        Items=[],
    )
    _product(model, "degraded", [failed])
    _product(model, "empty", [empty])
    _product(model, "absent", None)
    return model


def conflicted() -> ifcopenshell.file:
    model, model_context, projected, _, _ = _base("ifc4x3-conflicted-georef.ifc")
    for eastings in (500000.0, 600000.0):
        model.create_entity(
            "IfcMapConversionScaled",
            SourceCRS=model_context,
            TargetCRS=projected,
            Eastings=eastings,
            Northings=6100000.0,
            OrthogonalHeight=12.5,
            XAxisAbscissa=1.0,
            XAxisOrdinate=0.0,
            Scale=0.001,
            FactorX=1.0,
            FactorY=1.0,
            FactorZ=1.0,
        )
    _product(model, "absent", None)
    return model


BUILDERS = {
    "ifc4x3-curves-annotations-scaled.ifc": positive,
    "ifc4x3-degraded.ifc": degraded,
    "ifc4x3-conflicted-georef.ifc": conflicted,
}


def _bytes(builder: object) -> bytes:
    model = builder()
    return (model.to_string().rstrip() + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        mismatches = [name for name, builder in BUILDERS.items() if not (ROOT / name).is_file() or (ROOT / name).read_bytes() != _bytes(builder)]
        if mismatches:
            raise SystemExit(f"IFC v0.3 fixtures are stale: {', '.join(mismatches)}")
        print("AECCTX IFC v0.3 fixtures: deterministic")
        return 0
    for name, builder in BUILDERS.items():
        target = ROOT / name
        with tempfile.NamedTemporaryFile(dir=ROOT, delete=False) as handle:
            handle.write(_bytes(builder))
            temporary = Path(handle.name)
        temporary.replace(target)
    print("AECCTX IFC v0.3 fixtures: generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
