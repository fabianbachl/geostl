"""The :class:`ElevationTile` hand-off object between data sources and meshing.

An ``ElevationTile`` holds heights already in meters on a regular *metric* grid,
so everything downstream (scaling, meshing) needs no further geo knowledge.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import numpy as np

if TYPE_CHECKING:
    from affine import Affine


@dataclass
class ElevationTile:
    """A cropped elevation raster on a regular metric grid.

    Attributes:
        heights: 2D float array of elevations in meters; row 0 is the north edge.
        transform: affine mapping from pixel indices to projected meters.
        crs: EPSG string of the projected grid, e.g. ``"EPSG:32633"``.
        nodata: sentinel value for missing pixels, if any.
    """

    heights: np.ndarray
    transform: "Affine"
    crs: str
    nodata: Optional[float] = None

    def pixel_size_m(self) -> tuple[float, float]:
        """Return ``(dx, dy)`` ground sample distance in meters."""
        return (abs(self.transform.a), abs(self.transform.e))

    def subset(self, row0: int, row1: int, col0: int, col1: int) -> "ElevationTile":
        """Return the sub-tile ``[row0:row1, col0:col1]`` with an adjusted transform.

        Row/column indices use Python-slice (half-open) semantics. Grid tiling
        passes ranges that share a boundary row/column across neighbors, so
        adjacent tiles have pixel-identical seams.
        """
        from affine import Affine

        sub = np.ascontiguousarray(self.heights[row0:row1, col0:col1])
        transform = self.transform * Affine.translation(col0, row0)
        return ElevationTile(
            heights=sub, transform=transform, crs=self.crs, nodata=self.nodata
        )
