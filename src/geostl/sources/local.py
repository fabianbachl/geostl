"""LocalGeoTiffSource — read elevation from a local GeoTIFF (offline / dev / tests)."""
from __future__ import annotations

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
    multi-gigabyte DEMs are handled cheaply.

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
        fetch_resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "ElevationTile":
        from geostl.sources._raster import fetch_rasters

        return fetch_rasters(
            [str(self.path)], bbox, fetch_resolution_m=fetch_resolution_m,
            target_crs=target_crs,
        )
