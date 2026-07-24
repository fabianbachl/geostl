"""Elevation data-source adapters.

Every adapter implements :meth:`ElevationSource.fetch` and hides all
country/API specifics (endpoints, tiling, auth, mosaicking) behind it::

    from geostl.sources import LocalGeoTiffSource, AustriaDGMSource

Heavy dependencies (rasterio, requests) are imported lazily inside each
adapter's ``fetch`` so importing this package stays cheap.
"""
from geostl.sources.austria import AustriaDGMSource
from geostl.sources.base import ElevationSource
from geostl.sources.cog import RemoteCOGSource
from geostl.sources.germany import BavariaDGMSource
from geostl.sources.local import LocalGeoTiffSource
from geostl.sources.opentopography import OpenTopographySource
from geostl.sources.south_tyrol import SouthTyrolDGMSource
from geostl.sources.wcs import WCSSource

__all__ = [
    "ElevationSource",
    "LocalGeoTiffSource",
    "RemoteCOGSource",
    "WCSSource",
    "OpenTopographySource",
    "AustriaDGMSource",
    "BavariaDGMSource",
    "SouthTyrolDGMSource",
]
