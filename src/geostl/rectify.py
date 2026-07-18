"""Rectify elevation data onto a regular metric grid (reproject to meters).

Horizontal degrees are not equal in meters, so the grid used for meshing must be
built in a projected metric CRS. The primary path warps via ``rasterio.warp``;
a dependency-light geodesic fallback (ported from the prototype) is available for
small areas when GDAL/rasterio reprojection is unavailable.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import numpy as np
    from affine import Affine

    from geostl.elevation import ElevationTile
    from geostl.geometry import BoundingBox


def reproject_to_metric(
    src_heights: "np.ndarray",
    src_transform: "Affine",
    src_crs: str,
    bbox: "BoundingBox",
    *,
    resolution_m: Optional[float] = None,
    target_crs: Optional[str] = None,
) -> "ElevationTile":
    """Warp a source raster into a projected metric CRS (default: auto-UTM).

    Yields a regular grid whose pixel spacing equals ``resolution_m`` so meshing
    can treat it as a plain lattice. Backed by ``rasterio.warp`` (imported lazily).
    """
    raise NotImplementedError  # Phase 2


def rectify_geodesic(tile: "ElevationTile", bbox: "BoundingBox") -> "ElevationTile":
    """No-GDAL fallback: approximate a local meter grid via geodesic distances.

    Ported from the prototype notebook (``geopy``). Approximate; distortion grows
    with bbox size. Use only when reprojection is unavailable.
    """
    raise NotImplementedError  # Phase 2 (optional)
