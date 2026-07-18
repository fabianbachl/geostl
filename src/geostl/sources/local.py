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

    Reproduces the prototype notebook's ingestion path and stands in for
    :class:`~geostl.sources.austria.AustriaDGMSource` during early development
    (feed it ``assets/DGM_R25.tif``). Only the raster window covering the
    requested bbox is read, so multi-gigabyte DEMs are handled cheaply.
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

        from geostl.rectify import reproject_to_metric

        with rasterio.open(self.path) as ds:
            if ds.crs is None:
                raise ValueError(f"{self.path} has no CRS; cannot georeference it.")

            # Locate the bbox inside the source raster (in the source CRS) and read
            # ONLY that window with a small pad — the full DGM can be gigabytes.
            west, south, east, north = bbox.as_tuple()
            left, bottom, right, top = transform_bounds(
                "EPSG:4326", ds.crs, west, south, east, north
            )
            win = ds.window(left, bottom, right, top)

            pad = 2
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
            target_crs=target_crs,
            src_nodata=src_nodata,
        )
