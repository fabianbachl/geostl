"""LocalGeoTiffSource — read elevation from a local GeoTIFF (offline / dev / tests)."""
from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from geostl.sources.base import ElevationSource

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.geometry import BoundingBox


class LocalGeoTiffSource(ElevationSource):
    """Read, crop, and reproject a local GeoTIFF via rasterio.

    Works with any georeferenced GeoTIFF — not just one file or one region. The
    source is read in whatever CRS it declares and warped onto a metric output
    grid, and only the raster window covering the requested output is read, so
    multi-gigabyte DEMs are handled cheaply. It reproduces the prototype
    notebook's ingestion path and stands in for
    :class:`~geostl.sources.austria.AustriaDGMSource` during early development
    (feed it ``assets/DGM_R25.tif``).

    Any region the file covers works, and the output CRS defaults to the UTM zone
    of the requested bbox centroid (see :func:`~geostl.geometry.utm_epsg_for`), so
    callers need not reason about zones: a western-Austria box resolves to UTM 32N
    while a central or eastern one uses 33N, each with correct elevations. A DEM
    from another country in its own national CRS works the same way; only the file
    path changes.

    **Limitations**

    * Regions outside the file's coverage come back as ``NaN`` (filled flat when
      meshed); a bbox that does not overlap the raster at all raises
      :class:`ValueError`.
    * A single region that spans a UTM-zone boundary is still projected into one
      zone (the centroid's), so horizontal-scale distortion grows toward the far
      edge. For a very wide east–west region, pass an explicit equal-area or
      equidistant ``target_crs`` to :meth:`fetch`.
    * A bbox crossing the antimeridian cannot be expressed, because of the
      ``west < east`` invariant of :class:`~geostl.geometry.BoundingBox`.
    """

    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)

    def fetch(
        self,
        bbox: "BoundingBox",
        *,
        resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "ElevationTile":
        import rasterio
        from rasterio.warp import transform_bounds
        from rasterio.windows import Window

        from geostl.rectify import reproject_to_metric, resolve_output_grid

        with rasterio.open(self.path) as ds:
            if ds.crs is None:
                raise ValueError(f"{self.path} has no CRS; cannot georeference it.")

            # Resolve the output grid, then read the source window that covers it:
            # the output rectangle (in target CRS) mapped back into the source CRS.
            # Using the *output* extent — not the WGS84 bbox — is what prevents the
            # rotated projection from leaving NaN wedges at the output corners.
            out_crs, out_bounds, _w, _h, _t = resolve_output_grid(
                bbox, resolution_m, target_crs
            )
            sleft, sbottom, sright, stop = transform_bounds(out_crs, ds.crs, *out_bounds)
            win = ds.window(sleft, sbottom, sright, stop)

            pad = 3  # a few pixels of context for edge resampling
            col0 = max(0, int(math.floor(win.col_off)) - pad)
            row0 = max(0, int(math.floor(win.row_off)) - pad)
            col1 = min(ds.width, int(math.ceil(win.col_off + win.width)) + pad)
            row1 = min(ds.height, int(math.ceil(win.row_off + win.height)) + pad)
            if col1 <= col0 or row1 <= row0:
                raise ValueError(
                    f"Requested bbox does not overlap {self.path} "
                    f"(raster bounds {tuple(ds.bounds)} in {ds.crs})."
                )

            window = Window(col0, row0, col1 - col0, row1 - row0)
            src = ds.read(1, window=window).astype("float32")
            src_transform = ds.window_transform(window)
            src_crs = ds.crs
            src_nodata = ds.nodata

        return reproject_to_metric(
            src,
            src_transform,
            src_crs,
            bbox,
            resolution_m=resolution_m,
            target_crs=out_crs,
            src_nodata=src_nodata,
        )
