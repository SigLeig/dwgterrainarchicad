from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from .converter import ConversionError, ensure_dxf
from .dxf_reader import ReadOptions, read_terrain_points
from .exporters import choose_origin, export_archicad_files


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        parser.error(f"Input file does not exist: {input_path}")

    output_dir = Path(args.output_dir).expanduser()
    try:
        origin_mode = _parse_origin(args.origin)
        bbox = _parse_bbox(args.bbox)
    except ValueError as exc:
        parser.error(str(exc))

    with tempfile.TemporaryDirectory(prefix="dwgterrainarchicad-") as temp_dir:
        try:
            dxf_path = ensure_dxf(input_path, Path(temp_dir), args.converter)
            result = read_terrain_points(
                dxf_path,
                ReadOptions(
                    layers=_parse_layers(args.layers),
                    bbox=bbox,
                    sample_distance=args.sample_distance,
                    include_zero_elevation=args.include_zero_elevation,
                    min_z=args.min_z,
                    max_z=args.max_z,
                    dedupe_tolerance=args.dedupe_tolerance,
                ),
            )
        except (ConversionError, OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        if not result.points:
            print(
                "error: no terrain points were found. Try --include-zero-elevation, "
                "--layers with the correct contour layer, or convert the DWG to DXF "
                "and inspect whether contour lines contain Z/elevation values.",
                file=sys.stderr,
            )
            return 2

        origin = choose_origin(result.points, origin_mode)
        outputs = export_archicad_files(
            result.points,
            output_dir,
            input_path.stem,
            origin,
            result.report,
        )

    print(f"Exported {len(result.points)} terrain points")
    print(f"Origin offset: X={origin[0]:.3f}, Y={origin[1]:.3f}")
    for label, path in outputs.items():
        print(f"{label}: {path}")
    if result.report.skipped_bbox:
        print(f"Skipped points outside bbox: {result.report.skipped_bbox}")
    if result.report.skipped_zero_elevation:
        print(
            "Skipped zero-elevation points: "
            f"{result.report.skipped_zero_elevation} "
            "(use --include-zero-elevation to keep them)"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dwg-terrain-archicad",
        description=(
            "Extract 3D terrain points from DWG/DXF contour data and write files "
            "that can be imported as an Archicad mesh from surveyor data."
        ),
    )
    parser.add_argument("input", help="Input .dwg or .dxf file")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="terrain-output",
        help="Directory for exported Archicad files (default: terrain-output)",
    )
    parser.add_argument(
        "--converter",
        help=(
            "Optional DWG-to-DXF converter command. Use {input} and {output} "
            "placeholders for custom tools, or pass the ODA File Converter path."
        ),
    )
    parser.add_argument(
        "--layers",
        help=(
            "Comma-separated layer filters, with wildcards allowed "
            "(example: KOTE*,TERRAIN*)"
        ),
    )
    parser.add_argument(
        "--bbox",
        help=(
            "Only export points inside this coordinate box: minX,minY,maxX,maxY. "
            "Use original DWG/DXF coordinates, usually UTM meters."
        ),
    )
    parser.add_argument(
        "--sample-distance",
        type=float,
        default=0.0,
        help=(
            "Optional maximum spacing between sampled points along contour lines. "
            "Use drawing units, usually meters for UTM files."
        ),
    )
    parser.add_argument(
        "--include-zero-elevation",
        action="store_true",
        help="Keep points where Z/elevation is 0. Default skips them.",
    )
    parser.add_argument("--min-z", type=float, help="Ignore points below this elevation")
    parser.add_argument("--max-z", type=float, help="Ignore points above this elevation")
    parser.add_argument(
        "--dedupe-tolerance",
        type=float,
        default=0.001,
        help="Point deduplication tolerance in drawing units (default: 0.001)",
    )
    parser.add_argument(
        "--origin",
        default="auto",
        help=(
            "Coordinate origin handling: auto, min, none, or explicit X,Y. "
            "auto shifts large UTM coordinates close to Archicad's project origin."
        ),
    )
    return parser


def _parse_layers(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _parse_bbox(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None

    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("--bbox must be minX,minY,maxX,maxY")

    try:
        min_x, min_y, max_x, max_y = (float(part) for part in parts)
    except ValueError as exc:
        raise ValueError("--bbox values must be numbers") from exc

    if min_x >= max_x or min_y >= max_y:
        raise ValueError("--bbox must have min values before max values")
    return (min_x, min_y, max_x, max_y)


def _parse_origin(value: str) -> str | tuple[float, float]:
    normalized = value.strip().lower()
    if normalized in {"auto", "min", "none"}:
        return normalized

    if "," not in value:
        raise ValueError("--origin must be auto, min, none, or X,Y")
    x_value, y_value = value.split(",", 1)
    try:
        return (float(x_value), float(y_value))
    except ValueError as exc:
        raise ValueError("--origin X,Y must contain numeric values") from exc


if __name__ == "__main__":
    raise SystemExit(main())
