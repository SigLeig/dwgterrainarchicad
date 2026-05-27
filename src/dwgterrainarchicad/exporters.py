from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Literal

from .dxf_reader import ExtractionReport
from .models import TerrainPoint, bounds

OriginMode = Literal["auto", "min", "none"]


def choose_origin(
    points: list[TerrainPoint],
    mode: OriginMode | tuple[float, float],
) -> tuple[float, float]:
    if isinstance(mode, tuple):
        return mode
    if mode == "none":
        return (0.0, 0.0)

    min_x, min_y, _, max_x, max_y, _ = bounds(points)
    if mode == "min":
        return (min_x, min_y)

    largest_abs_coordinate = max(abs(min_x), abs(min_y), abs(max_x), abs(max_y))
    if largest_abs_coordinate > 100_000:
        return (min_x, min_y)
    return (0.0, 0.0)


def export_archicad_files(
    points: list[TerrainPoint],
    output_dir: Path,
    basename: str,
    origin: tuple[float, float],
    report: ExtractionReport,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    shifted_points = [point.shifted(origin) for point in points]

    outputs = {
        "archicad_txt": output_dir / f"{basename}_archicad_surveyor.txt",
        "csv": output_dir / f"{basename}_points.csv",
        "metadata": output_dir / f"{basename}_metadata.json",
    }

    _write_archicad_txt(shifted_points, outputs["archicad_txt"])
    _write_csv(shifted_points, outputs["csv"])
    _write_metadata(points, shifted_points, origin, report, outputs["metadata"])
    return outputs


def _write_archicad_txt(points: list[TerrainPoint], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        for point in points:
            file.write(f"{point.x:.3f}\t{point.y:.3f}\t{point.z:.3f}\n")


def _write_csv(points: list[TerrainPoint], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["x", "y", "z", "source", "layer"])
        for point in points:
            writer.writerow(
                [
                    f"{point.x:.3f}",
                    f"{point.y:.3f}",
                    f"{point.z:.3f}",
                    point.source,
                    point.layer,
                ]
            )


def _write_metadata(
    original_points: list[TerrainPoint],
    shifted_points: list[TerrainPoint],
    origin: tuple[float, float],
    report: ExtractionReport,
    path: Path,
) -> None:
    metadata = {
        "source": str(report.source_path),
        "origin": {"x": origin[0], "y": origin[1]},
        "point_count": len(shifted_points),
        "original_bounds": _bounds_dict(original_points),
        "export_bounds": _bounds_dict(shifted_points),
        "points_before_dedupe": report.points_before_dedupe,
        "points_after_dedupe": report.points_after_dedupe,
        "skipped_bbox": report.skipped_bbox,
        "skipped_zero_elevation": report.skipped_zero_elevation,
        "skipped_z_filter": report.skipped_z_filter,
        "scanned_entities": dict(report.scanned_entities),
        "used_layers": dict(report.used_layers),
        "archicad_import": {
            "file": path.with_name(path.name.replace("_metadata.json", "_archicad_surveyor.txt")).name,
            "format": "tab separated X Y Z without header",
        },
    }
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _bounds_dict(points: list[TerrainPoint]) -> dict[str, float]:
    min_x, min_y, min_z, max_x, max_y, max_z = bounds(points)
    return {
        "min_x": min_x,
        "min_y": min_y,
        "min_z": min_z,
        "max_x": max_x,
        "max_y": max_y,
        "max_z": max_z,
    }
