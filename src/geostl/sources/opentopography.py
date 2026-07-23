"""OpenTopographySource — global DEMs via the OpenTopography REST API."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from geostl.sources.base import ElevationSource

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.positioning import BoundingBox


class OpenTopographySource(ElevationSource):
    """Fetch global DEM data (SRTM, Copernicus, ...) from OpenTopography.

    Requires a free API key. ``dem`` selects the dataset (e.g. ``"COP30"``).
    HTTP is done with ``requests`` (imported lazily in ``fetch``).
    """

    def __init__(self, api_key: str, dem: str = "COP30"):
        self.api_key = api_key
        self.dem = dem

    def fetch(
        self,
        bbox: "BoundingBox",
        *,
        fetch_resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "ElevationTile":
        raise NotImplementedError  # upcoming
