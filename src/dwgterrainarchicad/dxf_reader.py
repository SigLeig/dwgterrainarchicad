from __future__ import annotations

import fnmatch
import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import ezdxf

from .models import TerrainPoint, deduplicate_points


@dataclass(frozen=True)
class ReadOptions:
    layers: tuple[str, ...] = ()
    sample_distance: float = 0.0
    include_zero_elevation: bool = False
    min_z: float | None = None
    max_z: float | None = None
    dedupe_tolerance: float = 0.001


@dataclass
class ExtractionReport:
    source_path: Path
    points_before_dedupe: int = 0
    points_after_dedupe: int = 0
    skipped_zero_elevation: int = 0
    skipped_z_filter: int = 0
    scanned_entities: Counter[str] = field(default_factory=Counter)
    used_layers: Counter[str] = field(default_factory=Counter)


@dataclass
class ExtractionResult:
    points: list[TerrainPoint]
    report: ExtractionReport


def read_terrain_points(path: Path, options: ReadOptions) -> ExtractionResult:
    doc = ezdxf.readfile(path)
    modelspace = doc.modelspace()
    report = ExtractionReport(source_path=path)
    points: list[TerrainPoint] = []

    for entity in modelspace:
        dxftype = entity.dxftype()
        layer = getattr(entity.dxf, "layer", "")
        report.scanned_entities[dxftype] += 1

        if options.layers and not _matches_layer(layer, options.layers):
            continue

        extracted = _extract_entity_points(entity, options.sample_distance)
        for point in extracted:
            terrain_point = TerrainPoint(
                point[0],
                point[1],
                point[2],
                source=dxftype,
                layer=layer,
            )
            if not _is_allowed(terrain_point, options, report):
                continue
            points.append(terrain_point)
            report.used_layers[layer] += 1

    report.points_before_dedupe = len(points)
    unique_points = deduplicate_points(points, options.dedupe_tolerance)
    report.points_after_dedupe = len(unique_points)
    return ExtractionResult(points=unique_points, report=report)


def _matches_layer(layer: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(layer.lower(), pattern.lower()) for pattern in patterns)


def _is_allowed(
    point: TerrainPoint, options: ReadOptions, report: ExtractionReport
) -> bool:
    if not options.include_zero_elevation and math.isclose(point.z, 0.0, abs_tol=1e-9):
        report.skipped_zero_elevation += 1
        return False
    if options.min_z is not None and point.z < options.min_z:
        report.skipped_z_filter += 1
        return False
    if options.max_z is not None and point.z > options.max_z:
        report.skipped_z_filter += 1
        return False
    return True


def _extract_entity_points(entity, sample_distance: float) -> list[tuple[float, float, float]]:
    dxftype = entity.dxftype()
    if dxftype == "POINT":
        return [_vec_to_tuple(entity.dxf.location)]
    if dxftype == "LINE":
        return _sample_vertices(
            [_vec_to_tuple(entity.dxf.start), _vec_to_tuple(entity.dxf.end)],
            sample_distance,
        )
    if dxftype == "LWPOLYLINE":
        return _extract_lwpolyline(entity, sample_distance)
    if dxftype == "POLYLINE":
        return _extract_polyline(entity, sample_distance)
    if dxftype in {"ARC", "CIRCLE"}:
        return _extract_arc_or_circle(entity, sample_distance)
    if dxftype == "SPLINE":
        return _extract_spline(entity, sample_distance)
    if dxftype == "3DFACE":
        return _extract_3dface(entity)
    return []


def _extract_lwpolyline(entity, sample_distance: float) -> list[tuple[float, float, float]]:
    try:
        vertices = [_vec_to_tuple(vertex) for vertex in entity.vertices_in_wcs()]
    except AttributeError:
        elevation = float(getattr(entity.dxf, "elevation", 0.0))
        vertices = [(float(x), float(y), elevation) for x, y, *_ in entity.get_points()]
    return _sample_vertices(vertices, sample_distance, closed=bool(entity.closed))


def _extract_polyline(entity, sample_distance: float) -> list[tuple[float, float, float]]:
    vertices = [_vec_to_tuple(vertex.dxf.location) for vertex in entity.vertices]
    return _sample_vertices(vertices, sample_distance, closed=bool(entity.is_closed))


def _extract_arc_or_circle(entity, sample_distance: float) -> list[tuple[float, float, float]]:
    center = _vec_to_tuple(entity.dxf.center)
    radius = float(entity.dxf.radius)
    if radius <= 0:
        return []

    if entity.dxftype() == "CIRCLE":
        start_angle = 0.0
        end_angle = 360.0
    else:
        start_angle = float(entity.dxf.start_angle)
        end_angle = float(entity.dxf.end_angle)
        if end_angle <= start_angle:
            end_angle += 360.0

    arc_length = radius * math.radians(end_angle - start_angle)
    if sample_distance > 0:
        segments = max(2, math.ceil(arc_length / sample_distance))
    else:
        segments = max(12, math.ceil((end_angle - start_angle) / 10.0))

    points = []
    for index in range(segments + 1):
        fraction = index / segments
        angle = math.radians(start_angle + (end_angle - start_angle) * fraction)
        points.append(
            (
                center[0] + math.cos(angle) * radius,
                center[1] + math.sin(angle) * radius,
                center[2],
            )
        )
    return points


def _extract_spline(entity, sample_distance: float) -> list[tuple[float, float, float]]:
    try:
        distance = sample_distance if sample_distance > 0 else 1.0
        return [_vec_to_tuple(point) for point in entity.flattening(distance)]
    except Exception:
        return []


def _extract_3dface(entity) -> list[tuple[float, float, float]]:
    vertices: list[tuple[float, float, float]] = []
    for attr in ("vtx0", "vtx1", "vtx2", "vtx3"):
        if hasattr(entity.dxf, attr):
            vertex = _vec_to_tuple(getattr(entity.dxf, attr))
            if vertex not in vertices:
                vertices.append(vertex)
    return vertices


def _sample_vertices(
    vertices: Sequence[tuple[float, float, float]],
    sample_distance: float,
    closed: bool = False,
) -> list[tuple[float, float, float]]:
    if len(vertices) < 2 or sample_distance <= 0:
        return list(vertices)

    path_vertices = list(vertices)
    if closed and vertices[0] != vertices[-1]:
        path_vertices.append(vertices[0])

    sampled: list[tuple[float, float, float]] = []
    for start, end in zip(path_vertices, path_vertices[1:]):
        if not sampled:
            sampled.append(start)
        sampled.extend(_sample_segment(start, end, sample_distance))
    return sampled


def _sample_segment(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    sample_distance: float,
) -> Iterable[tuple[float, float, float]]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    length = math.hypot(dx, dy)
    if length == 0:
        return [end]

    steps = max(1, math.ceil(length / sample_distance))
    return [
        (
            start[0] + dx * index / steps,
            start[1] + dy * index / steps,
            start[2] + dz * index / steps,
        )
        for index in range(1, steps + 1)
    ]


def _vec_to_tuple(vector) -> tuple[float, float, float]:
    return (float(vector[0]), float(vector[1]), float(vector[2]))
