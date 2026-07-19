"""RemoteCOGSource — stream + crop one or more remote Cloud-Optimized GeoTIFFs."""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Sequence, Union

from geostl.sources.base import ElevationSource

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.geometry import BoundingBox


class RemoteCOGSource(ElevationSource):
    """Crop + reproject one or more remote COGs via GDAL ``/vsicurl/``.

    Accepts a single URL or a list; when several are given they are mosaicked
    (the first with data wins per pixel), which is how tiled national datasets are
    assembled. Only the window covering the request is read, decimated to the
    output resolution, so a COG's overviews keep transfers small — no full
    download. The actual reading/reprojection/mosaicking is the shared machinery
    in :mod:`geostl.sources._raster`, so tiled sources such as
    :class:`~geostl.sources.austria.AustriaDGMSource` can reuse it.

    Pass ``src_crs`` (e.g. ``"EPSG:3035"``) to override a broken/engineering CRS
    embedded in the COGs. A rewrite of the lost ``crop_cog.py`` (its source was
    never committed; only the compiled ``.pyc`` survived), with the same
    crop-reproject-one-band intent.
    """

    def __init__(self, url: Union[str, Sequence[str]], *, src_crs: Optional[str] = None):
        self.urls: List[str] = [url] if isinstance(url, str) else list(url)
        self.src_crs = src_crs

    def fetch(
        self,
        bbox: "BoundingBox",
        *,
        resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "ElevationTile":
        from geostl.sources._raster import fetch_rasters

        sources = [
            u if u.startswith("/vsicurl/") else f"/vsicurl/{u}" for u in self.urls
        ]
        return fetch_rasters(
            sources, bbox, resolution_m=resolution_m, target_crs=target_crs,
            src_crs=self.src_crs,
        )
