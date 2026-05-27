"""Command line interface for STEP to IFC conversion."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .freecad_backend import ConversionError, convert_step_to_ifc
from .rotations import RotationStep, parse_rotation


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    input_step = Path(args.input_step)
    output_ifc = Path(args.output_ifc) if args.output_ifc else input_step.with_suffix(".ifc")

    try:
        _validate_paths(input_step, output_ifc)
        if _has_freecad_modules():
            convert_step_to_ifc(input_step, output_ifc, args.rotate)
            print(f"Wrote IFC file: {output_ifc}")
            return 0
        return _run_with_freecadcmd(
            input_step=input_step,
            output_ifc=output_ifc,
            rotations=args.rotate,
            freecad_cmd=args.freecad_cmd,
        )
    except (ConversionError, OSError, RuntimeError) as exc:
        print(f"step-to-ifc: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="step-to-ifc",
        description=(
            "Convert a STEP/STP model to IFC and optionally rotate it in "
            "90 degree steps around the X, Y and Z axes."
        ),
    )
    parser.add_argument("input_step", help="Path to the source .step or .stp file")
    parser.add_argument(
        "output_ifc",
        nargs="?",
        help="Path to the destination .ifc file (defaults to input name with .ifc)",
    )
    parser.add_argument(
        "-r",
        "--rotate",
        action="append",
        default=[],
        type=_rotation_arg,
        metavar="AXIS+/-",
        help=(
            "Rotate the model 90 degrees. Can be repeated. Accepted values: "
            "x+, x-, y+, y-, z+, z- (also accepts x:90 or y=-90)."
        ),
    )
    parser.add_argument(
        "--freecad-cmd",
        default=None,
        help=(
            "Path to FreeCADCmd. If omitted, STEP_TO_IFC_FREECAD_CMD, "
            "FREECADCMD and PATH are checked."
        ),
    )
    return parser


def _rotation_arg(value: str) -> RotationStep:
    try:
        return parse_rotation(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _validate_paths(input_step: Path, output_ifc: Path) -> None:
    if not input_step.exists():
        raise RuntimeError(f"Input file does not exist: {input_step}")
    if input_step.suffix.lower() not in {".step", ".stp"}:
        raise RuntimeError("Input file must have a .step or .stp extension")
    if output_ifc.suffix.lower() != ".ifc":
        raise RuntimeError("Output file must have a .ifc extension")


def _has_freecad_modules() -> bool:
    try:
        import FreeCAD  # noqa: F401  # type: ignore
    except ImportError:
        return False
    return True


def _run_with_freecadcmd(
    input_step: Path,
    output_ifc: Path,
    rotations: Sequence[RotationStep],
    freecad_cmd: str | None,
) -> int:
    command = _find_freecadcmd(freecad_cmd)
    runner = Path(__file__).with_name("_freecad_entry.py").resolve()
    src_root = Path(__file__).resolve().parents[1]

    args = [
        command,
        str(runner),
        "--input",
        str(input_step.resolve()),
        "--output",
        str(output_ifc.resolve()),
    ]
    for rotation in rotations:
        args.extend(["--rotate", rotation.cli_value()])

    env = os.environ.copy()
    env["PYTHONPATH"] = _prepend_pythonpath(src_root, env.get("PYTHONPATH"))
    completed = subprocess.run(args, env=env, check=False)
    return completed.returncode


def _find_freecadcmd(explicit_command: str | None) -> str:
    candidates = [
        explicit_command,
        os.environ.get("STEP_TO_IFC_FREECAD_CMD"),
        os.environ.get("FREECADCMD"),
        shutil.which("FreeCADCmd"),
        shutil.which("freecadcmd"),
        shutil.which("freecad"),
    ]
    for candidate in candidates:
        if candidate:
            return candidate

    raise RuntimeError(
        "Could not find FreeCADCmd. Install FreeCAD and ensure FreeCADCmd is "
        "on PATH, set STEP_TO_IFC_FREECAD_CMD, or pass --freecad-cmd."
    )


def _prepend_pythonpath(path: Path, existing: str | None) -> str:
    if not existing:
        return str(path)
    return f"{path}{os.pathsep}{existing}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
