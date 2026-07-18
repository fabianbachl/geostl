"""RemoteCOGSource — stream + crop a remote Cloud-Optimized GeoTIFF."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from geostl.sources.base import ElevationSource

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.geometry import BoundingBox


class RemoteCOGSource(ElevationSource):
    """Crop + reproject a remote COG via GDAL ``/vsicurl/`` (no full download).

    A rewrite of the lost ``crop_cog.py`` (its source was never committed; only
    the compiled ``.pyc`` survived). Contract preserved from that bytecode: crop
    to bbox, reproject, read one band into a 2D array.
    """

    def __init__(self, url: str):
        self.url = url

    def fetch(
        self,
        bbox: "BoundingBox",
        *,
        resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "ElevationTile":
        raise NotImplementedError  # Phase 7
