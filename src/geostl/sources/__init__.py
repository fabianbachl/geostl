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
from geostl.sources.local import LocalGeoTiffSource
from geostl.sources.opentopography import OpenTopographySource

__all__ = [
    "ElevationSource",
    "LocalGeoTiffSource",
    "RemoteCOGSource",
    "OpenTopographySource",
    "AustriaDGMSource",
]
