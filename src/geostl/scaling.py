"""Physical scaling: real-world meters -> print-bed millimeters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ScaleSpec:
    """Resolved physical scaling shared across a Section or a whole Grid."""

    scale_xy_mm_per_m: float  # horizontal mm per real meter
    z_scale_mm_per_m: float   # vertical mm per real meter (includes exaggeration)
    base_thickness_mm: float


def resolve_scale(
    extent_x_m: float,
    extent_y_m: float,
    *,
    bed_size_mm: Optional[float] = None,
    scale_xy: Optional[float] = None,
    z_exaggeration: float = 1.0,
    base_thickness_mm: float = 3.0,
) -> ScaleSpec:
    """Compute a :class:`ScaleSpec` from either a target bed size or an explicit mm/m.

    Exactly one of ``bed_size_mm`` or ``scale_xy`` must be provided. When
    ``bed_size_mm`` is given, the model's longer horizontal side is scaled to
    exactly that many millimeters. ``z_exaggeration`` multiplies the vertical
    scale relative to the horizontal one. For a grid, call this once against the
    whole region so every tile shares the scale.

    Args:
        extent_x_m: real-world width of the model footprint, in meters.
        extent_y_m: real-world height of the model footprint, in meters.
        bed_size_mm: target size (mm) of the longer horizontal side.
        scale_xy: explicit horizontal scale in mm per real meter.
        z_exaggeration: vertical exaggeration factor (1.0 = true scale).
        base_thickness_mm: solid base below the lowest point, in mm.
    """
    if (bed_size_mm is None) == (scale_xy is None):
        raise ValueError("provide exactly one of bed_size_mm or scale_xy")

    if bed_size_mm is not None:
        if bed_size_mm <= 0:
            raise ValueError("bed_size_mm must be positive")
        longest = max(extent_x_m, extent_y_m)
        if longest <= 0:
            raise ValueError("model extent must be positive")
        scale_xy = bed_size_mm / longest
    elif scale_xy <= 0:
        raise ValueError("scale_xy must be positive")

    if z_exaggeration <= 0:
        raise ValueError("z_exaggeration must be positive")
    if base_thickness_mm < 0:
        raise ValueError("base_thickness_mm must be >= 0")

    return ScaleSpec(
        scale_xy_mm_per_m=float(scale_xy),
        z_scale_mm_per_m=float(scale_xy * z_exaggeration),
        base_thickness_mm=float(base_thickness_mm),
    )
