"""Parsing and validation for 90 degree model rotations."""

from __future__ import annotations

from dataclasses import dataclass


_AXES = {"x", "y", "z"}


@dataclass(frozen=True)
class RotationStep:
    """A single 90 degree rotation around a principal axis."""

    axis: str
    degrees: int

    def __post_init__(self) -> None:
        axis = self.axis.lower()
        if axis not in _AXES:
            raise ValueError(f"Unknown rotation axis {self.axis!r}; expected x, y or z")
        if self.degrees not in (-90, 90):
            raise ValueError("Only +/-90 degree rotations are supported")
        object.__setattr__(self, "axis", axis)

    def cli_value(self) -> str:
        sign = "+" if self.degrees > 0 else "-"
        return f"{self.axis}{sign}"


def parse_rotation(value: str) -> RotationStep:
    """Parse CLI rotation values such as x+, -y, z:90 or x=-90."""

    original = value
    normalized = value.strip().lower().replace(" ", "")
    if not normalized:
        raise ValueError("Rotation cannot be empty")

    for separator in (":", "="):
        if separator in normalized:
            axis, degrees = normalized.split(separator, 1)
            return _rotation_from_axis_and_degrees(axis, degrees, original)

    if len(normalized) == 1 and normalized in _AXES:
        return RotationStep(normalized, 90)

    if len(normalized) == 2:
        first, second = normalized
        if first in _AXES and second in {"+", "-"}:
            return RotationStep(first, 90 if second == "+" else -90)
        if first in {"+", "-"} and second in _AXES:
            return RotationStep(second, 90 if first == "+" else -90)

    for axis in _AXES:
        if normalized.startswith(axis):
            degrees = normalized[len(axis) :]
            return _rotation_from_axis_and_degrees(axis, degrees, original)

    raise ValueError(
        f"Invalid rotation {original!r}; use x+, x-, y+, y-, z+ or z-"
    )


def _rotation_from_axis_and_degrees(
    axis: str, degrees: str, original: str
) -> RotationStep:
    axis = axis.strip().lower()
    if axis not in _AXES:
        raise ValueError(
            f"Invalid rotation axis in {original!r}; expected x, y or z"
        )

    try:
        parsed_degrees = int(degrees)
    except ValueError as exc:
        raise ValueError(
            f"Invalid rotation degrees in {original!r}; expected 90 or -90"
        ) from exc

    return RotationStep(axis, parsed_degrees)
