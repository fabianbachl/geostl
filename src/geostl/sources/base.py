"""The :class:`ElevationSource` abstract base class — the extensibility point."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.geometry import BoundingBox


class ElevationSource(ABC):
    """Fetch elevation data for a WGS84 bbox and return a metric ElevationTile.

    Subclasses implement one method and hide every country/API specific behind
    it: which tiles/endpoints cover the bbox, downloading/streaming, auth,
    mosaicking, and cropping + reprojecting to a metric grid.
    """

    @abstractmethod
    def fetch(
        self,
        bbox: "BoundingBox",
        *,
        fetch_resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "ElevationTile":
        """Return heights covering ``bbox``, warped to ``target_crs`` (default:
        auto-UTM). The source is read at native resolution unless
        ``fetch_resolution_m`` requests a coarser read (metres/pixel)."""
        raise NotImplementedError
