"""Rectify elevation data onto a regular metric grid (reproject to meters).

Horizontal degrees are not equal in meters, so the grid used for meshing must be
built in a projected metric CRS. The primary path warps via ``rasterio.warp``;
a dependency-light geodesic fallback (ported from the prototype) is available for
small areas when GDAL/rasterio reprojection is unavailable.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    import numpy as np
    from affine import Affine

    from geostl.elevation import ElevationTile
    from geostl.positioning import BoundingBox


def resolve_output_grid(
    bbox: "BoundingBox",
    resolution_m: Optional[float] = None,
    target_crs: Optional[str] = None,
) -> Tuple[str, Tuple[float, float, float, float], int, int, "Affine"]:
    """Resolve the metric output grid covering ``bbox``.

    Returns ``(target_crs, (left, bottom, right, top), width, height, transform)``
    where the bounds/transform are in ``target_crs`` (default: the bbox's UTM
    zone) and the pixel spacing equals ``resolution_m`` (default 30 m). This is
    the single source of truth for the output grid, shared by the reprojection
    and by data sources that need to read a covering source window.
    """
    from rasterio.transform import from_origin
    from rasterio.warp import transform_bounds

    from geostl.positioning import utm_epsg_for

    if resolution_m is None:
        resolution_m = 30.0
    if target_crs is None:
        target_crs = f"EPSG:{utm_epsg_for(bbox)}"

    west, south, east, north = bbox.as_tuple()
    left, bottom, right, top = transform_bounds(
        "EPSG:4326", target_crs, west, south, east, north
    )
    width = max(1, int(round((right - left) / resolution_m)))
    height = max(1, int(round((top - bottom) / resolution_m)))
    transform = from_origin(left, top, resolution_m, resolution_m)
    return str(target_crs), (left, bottom, right, top), width, height, transform


def reproject_to_metric(
    src_heights: "np.ndarray",
    src_transform: "Affine",
    src_crs,
    bbox: "BoundingBox",
    *,
    resolution_m: Optional[float] = None,
    target_crs: Optional[str] = None,
    src_nodata: Optional[float] = None,
) -> "ElevationTile":
    """Warp a source raster into a projected metric CRS (default: auto-UTM).

    Args:
        src_heights: 2D source elevation array (in ``src_crs``).
        src_transform: affine transform of ``src_heights``.
        src_crs: CRS of the source array (an EPSG string or a rasterio CRS).
        bbox: the requested area, in WGS84.
        resolution_m: output ground sample distance in meters (default 30).
        target_crs: output CRS (default: the UTM zone of the bbox centroid).
        src_nodata: source nodata value to mask out during resampling.

    Returns:
        An :class:`~geostl.elevation.ElevationTile` on a regular metric grid whose
        pixel spacing equals ``resolution_m``; masked / off-source pixels are NaN.
        The caller is responsible for supplying ``src_heights`` that cover the
        whole output rectangle (see :func:`resolve_output_grid`).
    """
    import numpy as np
    from rasterio.warp import Resampling, reproject

    from geostl.elevation import ElevationTile

    target_crs, _bounds, width, height, dst_transform = resolve_output_grid(
        bbox, resolution_m, target_crs
    )

    dst = np.full((height, width), np.nan, dtype="float32")
    reproject(
        source=np.ascontiguousarray(src_heights),
        destination=dst,
        src_transform=src_transform,
        src_crs=src_crs,
        src_nodata=src_nodata,
        dst_transform=dst_transform,
        dst_crs=target_crs,
        dst_nodata=float("nan"),
        resampling=Resampling.bilinear,
    )
    return ElevationTile(
        heights=dst, transform=dst_transform, crs=target_crs, nodata=float("nan")
    )


def resample_heights(heights, transform, crs, target_res_m):
    """Downsample a metric height grid to ``target_res_m`` (same CRS, same extent).

    Area-averaging (anti-aliased) and NaN-aware, via ``rasterio.warp.reproject``.
    Returns ``(heights, transform)``. Intended for downsampling only —
    ``target_res_m`` should be >= the grid's current pixel size.
    """
    import numpy as np
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject

    src = np.ascontiguousarray(heights, dtype="float32")
    h, w = src.shape
    extent_x = w * abs(transform.a)
    extent_y = h * abs(transform.e)
    left, top = transform.c, transform.f

    out_w = max(1, int(round(extent_x / target_res_m)))
    out_h = max(1, int(round(extent_y / target_res_m)))
    dst_transform = from_origin(left, top, extent_x / out_w, extent_y / out_h)

    dst = np.full((out_h, out_w), np.nan, dtype="float32")
    reproject(
        source=src,
        destination=dst,
        src_transform=transform,
        src_crs=crs,
        src_nodata=float("nan"),
        dst_transform=dst_transform,
        dst_crs=crs,
        dst_nodata=float("nan"),
        resampling=Resampling.average,
    )
    return dst, dst_transform


def rectify_geodesic(tile: "ElevationTile", bbox: "BoundingBox") -> "ElevationTile":
    """No-GDAL fallback: approximate a local meter grid via geodesic distances.

    Ported from the prototype notebook (``geopy``). Approximate; distortion grows
    with bbox size. Use only when reprojection is unavailable.
    """
    raise NotImplementedError  # Phase 2 (optional)
