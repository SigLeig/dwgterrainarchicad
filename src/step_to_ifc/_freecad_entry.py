"""Entry point executed by FreeCADCmd."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:  # pragma: no cover - used by FreeCADCmd execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from step_to_ifc.freecad_backend import ConversionError, convert_step_to_ifc
from step_to_ifc.rotations import parse_rotation


def main() -> int:
    parser = argparse.ArgumentParser(prog="step-to-ifc-freecad")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--rotate", action="append", default=[])
    args = parser.parse_args()

    try:
        rotations = [parse_rotation(value) for value in args.rotate]
        convert_step_to_ifc(args.input, args.output, rotations)
        print(f"Wrote IFC file: {args.output}")
        return 0
    except (ConversionError, ValueError) as exc:
        print(f"step-to-ifc: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
