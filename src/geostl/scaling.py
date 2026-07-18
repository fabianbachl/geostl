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

    Exactly one of ``bed_size_mm`` or ``scale_xy`` must be provided. For a grid,
    call this once against the whole region so every tile shares the scale.
    """
    raise NotImplementedError  # Phase 4
