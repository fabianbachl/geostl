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

    Reproduces the prototype notebook's ingestion path and stands in for
    :class:`~geostl.sources.austria.AustriaDGMSource` during early development
    (feed it ``assets/DGM_R25.tif``).
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
        raise NotImplementedError  # Phase 1
