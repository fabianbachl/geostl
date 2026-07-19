"""Shared raster ingestion used by all file/URL-based sources.

Opens one or more rasterio-readable sources (local paths or ``/vsicurl/`` URLs),
reads only the window covering the requested output — decimated to roughly the
output resolution so Cloud-Optimized GeoTIFF overviews are used and remote reads
stay small — reprojects each onto the shared metric output grid, and mosaics them.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, Sequence

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.geometry import BoundingBox


def _read_window(ds, crs, out_crs, out_bounds, out_width, out_height, pad=3):
    """Read the window of ``ds`` covering ``out_bounds`` (given in ``out_crs``),
    decimated to about the output pixel count.

    ``crs`` is the source CRS to trust (an override for datasets with a broken
    embedded CRS). Returns ``(array, transform, crs, nodata)`` or ``None`` if
    there is no overlap.
    """
    from affine import Affine
    from rasterio.warp import transform_bounds
    from rasterio.windows import Window

    left, bottom, right, top = transform_bounds(out_crs, crs, *out_bounds)
    win = ds.window(left, bottom, right, top)
    col0 = max(0, int(math.floor(win.col_off)) - pad)
    row0 = max(0, int(math.floor(win.row_off)) - pad)
    col1 = min(ds.width, int(math.ceil(win.col_off + win.width)) + pad)
    row1 = min(ds.height, int(math.ceil(win.row_off + win.height)) + pad)
    if col1 <= col0 or row1 <= row0:
        return None

    win_w, win_h = col1 - col0, row1 - row0
    # Never read finer than the output needs; this lets COG overviews do the work.
    factor = max(1.0, win_w / (out_width + 2 * pad), win_h / (out_height + 2 * pad))
    read_w = max(1, int(round(win_w / factor)))
    read_h = max(1, int(round(win_h / factor)))

    window = Window(col0, row0, win_w, win_h)
    arr = ds.read(1, window=window, out_shape=(read_h, read_w)).astype("float32")
    transform = ds.window_transform(window) * Affine.scale(win_w / read_w, win_h / read_h)
    return arr, transform, crs, ds.nodata


def fetch_rasters(
    sources: Sequence[str],
    bbox: "BoundingBox",
    *,
    resolution_m: Optional[float] = None,
    target_crs: Optional[str] = None,
    src_crs: Optional[str] = None,
) -> "ElevationTile":
    """Read, reproject, and mosaic ``sources`` onto one metric output grid.

    ``sources`` are rasterio identifiers — local paths or ``/vsicurl/<url>`` for
    remote COGs. Each is opened, its covering window read (decimated to the output
    resolution), reprojected to the target metric grid, and merged (the first
    source with data wins per pixel). ``src_crs`` overrides the datasets' embedded
    CRS (needed when a COG advertises a broken/engineering CRS). Raises
    ``ValueError`` if nothing overlaps.
    """
    import numpy as np
    import rasterio

    from geostl.elevation import ElevationTile
    from geostl.rectify import reproject_to_metric, resolve_output_grid

    if not sources:
        raise ValueError("no raster sources given")

    out_crs, out_bounds, width, height, dst_transform = resolve_output_grid(
        bbox, resolution_m, target_crs
    )
    acc = np.full((height, width), np.nan, dtype="float32")
    covered = 0
    for src in sources:
        with rasterio.open(src) as ds:
            eff_crs = src_crs or ds.crs
            if eff_crs is None:
                raise ValueError(f"{src} has no CRS; pass src_crs to override it.")
            got = _read_window(ds, eff_crs, out_crs, out_bounds, width, height)
            if got is None:
                continue
            arr, src_transform, arr_crs, src_nodata = got
            piece = reproject_to_metric(
                arr, src_transform, arr_crs, bbox,
                resolution_m=resolution_m, target_crs=out_crs, src_nodata=src_nodata,
            )
        fill = np.isnan(acc) & np.isfinite(piece.heights)
        acc[fill] = piece.heights[fill]
        covered += 1

    if covered == 0:
        raise ValueError("requested bbox does not overlap any of the raster sources")
    return ElevationTile(
        heights=acc, transform=dst_transform, crs=out_crs, nodata=float("nan")
    )
