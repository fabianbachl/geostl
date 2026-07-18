"""AustriaDGMSource — the primary source: Austrian Digitales Geländemodell (DGM)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from geostl.sources.base import ElevationSource

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.geometry import BoundingBox


class AustriaDGMSource(ElevationSource):
    """Austrian national DGM open data.

    The acquisition path — endpoint / tiling scheme / native CRS (e.g.
    MGI/Austria Lambert ``EPSG:31287`` or ETRS89/UTM33N ``EPSG:25833``) — is the
    first research task of Phase 6. Until it is settled, use
    :class:`~geostl.sources.local.LocalGeoTiffSource` with a downloaded DGM tile.
    """

    def fetch(
        self,
        bbox: "BoundingBox",
        *,
        resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "ElevationTile":
        raise NotImplementedError  # Phase 6
