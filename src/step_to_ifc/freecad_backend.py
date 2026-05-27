"""FreeCAD-backed STEP to IFC conversion."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .rotations import RotationStep


class ConversionError(RuntimeError):
    """Raised when FreeCAD cannot complete a conversion."""


def convert_step_to_ifc(
    input_step: Path | str,
    output_ifc: Path | str,
    rotations: Iterable[RotationStep] = (),
) -> None:
    """Import a STEP file, rotate its objects and export them to IFC.

    This function must run inside a FreeCAD Python runtime. The public CLI
    launches FreeCADCmd automatically when it is called from normal Python.
    """

    try:
        import FreeCAD  # type: ignore
        import Import  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without FreeCAD
        raise ConversionError(
            "FreeCAD Python modules are not available. Run through the "
            "step-to-ifc CLI with FreeCADCmd installed, or use FreeCAD's Python."
        ) from exc

    input_path = Path(input_step).expanduser().resolve()
    output_path = Path(output_ifc).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise ConversionError(f"Input STEP file does not exist: {input_path}")
    if input_path.suffix.lower() not in {".step", ".stp"}:
        raise ConversionError("Input file must have a .step or .stp extension")
    if output_path.suffix.lower() != ".ifc":
        raise ConversionError("Output file must have a .ifc extension")

    doc = FreeCAD.newDocument("StepToIfcConversion")
    try:
        Import.insert(str(input_path), doc.Name)
        doc.recompute()

        exportable_objects = _exportable_objects(doc)
        if not exportable_objects:
            raise ConversionError(f"No exportable geometry found in {input_path}")

        rotation_steps = tuple(rotations)
        if rotation_steps:
            _apply_rotations(FreeCAD, exportable_objects, rotation_steps)
            doc.recompute()

        _export_ifc(exportable_objects, str(output_path))
    finally:
        FreeCAD.closeDocument(doc.Name)


def _exportable_objects(doc: object) -> list[object]:
    objects = []
    for obj in getattr(doc, "Objects", []):
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        is_null = getattr(shape, "isNull", None)
        if callable(is_null) and is_null():
            continue
        objects.append(obj)
    return objects


def _apply_rotations(
    freecad_module: object,
    objects: Iterable[object],
    rotations: Iterable[RotationStep],
) -> None:
    axis_vectors = {
        "x": freecad_module.Vector(1, 0, 0),
        "y": freecad_module.Vector(0, 1, 0),
        "z": freecad_module.Vector(0, 0, 1),
    }

    for rotation_step in rotations:
        rotation = freecad_module.Rotation(
            axis_vectors[rotation_step.axis], rotation_step.degrees
        )
        placement = freecad_module.Placement(freecad_module.Vector(0, 0, 0), rotation)
        for obj in objects:
            obj.Placement = placement.multiply(obj.Placement)


def _export_ifc(objects: list[object], output_path: str) -> None:
    errors: list[str] = []

    try:
        import importIFC  # type: ignore

        importIFC.export(objects, output_path)
        return
    except Exception as exc:  # pragma: no cover - depends on FreeCAD install
        errors.append(f"importIFC.export failed: {exc}")

    try:
        import Import  # type: ignore

        Import.export(objects, output_path)
        return
    except Exception as exc:  # pragma: no cover - depends on FreeCAD install
        errors.append(f"Import.export failed: {exc}")

    details = "; ".join(errors)
    raise ConversionError(
        "Could not export IFC. Make sure FreeCAD has IFC/BIM support installed. "
        f"Details: {details}"
    )
