from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TerrainPoint:
    """A single terrain sample point in model coordinates."""

    x: float
    y: float
    z: float
    source: str = ""
    layer: str = ""

    def shifted(self, origin: tuple[float, float]) -> "TerrainPoint":
        ox, oy = origin
        return TerrainPoint(
            x=self.x - ox,
            y=self.y - oy,
            z=self.z,
            source=self.source,
            layer=self.layer,
        )


def deduplicate_points(
    points: Iterable[TerrainPoint], tolerance: float
) -> list[TerrainPoint]:
    """Remove near-identical points while keeping deterministic order."""

    if tolerance <= 0:
        seen: set[tuple[float, float, float]] = set()
        unique: list[TerrainPoint] = []
        for point in points:
            key = (point.x, point.y, point.z)
            if key not in seen:
                seen.add(key)
                unique.append(point)
        return unique

    scale = 1.0 / tolerance
    seen_keys: set[tuple[int, int, int]] = set()
    unique = []
    for point in points:
        key = (
            round(point.x * scale),
            round(point.y * scale),
            round(point.z * scale),
        )
        if key not in seen_keys:
            seen_keys.add(key)
            unique.append(point)
    return unique


def bounds(points: Iterable[TerrainPoint]) -> tuple[float, float, float, float, float, float]:
    materialized = list(points)
    if not materialized:
        raise ValueError("Cannot compute bounds for an empty point collection.")

    xs = [p.x for p in materialized]
    ys = [p.y for p in materialized]
    zs = [p.z for p in materialized]
    return min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)
