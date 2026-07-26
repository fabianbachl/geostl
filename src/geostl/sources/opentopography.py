"""OpenTopographySource — global DEMs via the OpenTopography REST API.

The global fallback: when no national high-resolution source covers a region,
OpenTopography serves worldwide DEMs (Copernicus, SRTM, ...) as a server-side
crop to a GeoTIFF, which is read through the shared ingestion path. A free API
key is required (register at https://portal.opentopography.org/).
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

from geostl.sources.base import ElevationSource

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.positioning import BoundingBox

_ENDPOINT = "https://portal.opentopography.org/API/globaldem"

# Global DEMs offered by the API, with their nominal ground sampling. COP30
# (Copernicus GLO-30) is the default — global, void-filled, ~30 m.
_DEMS = {
    "COP30": 30.0, "COP90": 90.0,
    "SRTMGL1": 30.0, "SRTMGL3": 90.0,
    "NASADEM": 30.0, "AW3D30": 30.0, "SRTM15Plus": 500.0,
}


class OpenTopographySource(ElevationSource):
    """Fetch global DEM data (Copernicus, SRTM, ...) from OpenTopography.

    A single ``GetCoverage``-style request returns the bbox cropped from a global
    DEM as an EPSG:4326 GeoTIFF, which is read through the shared ingestion path
    (see :func:`geostl.sources._raster.geotiff_from_bytes`). This is the global
    fallback for regions without a national high-resolution source; the datasets
    are ~30 m (``COP30``/``SRTMGL1``) or coarser, so it does not replace the
    national 1–2 m sources where those exist.

    A free API key is required. Pass it as ``api_key`` or set the
    ``OPENTOPOGRAPHY_API_KEY`` environment variable.

    Args:
        api_key: OpenTopography API key. Falls back to ``$OPENTOPOGRAPHY_API_KEY``.
        dem: dataset code — one of ``COP30`` (default), ``COP90``, ``SRTMGL1``,
            ``SRTMGL3``, ``NASADEM``, ``AW3D30``, ``SRTM15Plus``.
        timeout: per-request timeout in seconds.

    Data source: OpenTopography (https://opentopography.org); cite the specific
    dataset's DOI as required by its terms.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        dem: str = "COP30",
        *,
        endpoint: str = _ENDPOINT,
        timeout: float = 120.0,
    ):
        if dem not in _DEMS:
            raise ValueError(f"dem must be one of {sorted(_DEMS)}, got {dem!r}")
        self.api_key = api_key or os.environ.get("OPENTOPOGRAPHY_API_KEY")
        self.dem = dem
        self.endpoint = endpoint
        self.timeout = timeout

    def fetch(
        self,
        bbox: "BoundingBox",
        *,
        fetch_resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "ElevationTile":
        import requests

        from geostl.sources._raster import TIFF_MAGIC, geotiff_from_bytes

        if not self.api_key:
            raise ValueError(
                "OpenTopography requires an API key: pass api_key= or set "
                "OPENTOPOGRAPHY_API_KEY (register at https://portal.opentopography.org/)."
            )
        params = {
            "demtype": self.dem,
            "south": bbox.south, "north": bbox.north,
            "west": bbox.west, "east": bbox.east,
            "outputFormat": "GTiff",
            "API_Key": self.api_key,
        }
        resp = requests.get(self.endpoint, params=params, timeout=self.timeout)
        content = resp.content
        if not content.startswith(TIFF_MAGIC):
            # Errors come back as an XML/text body (401 no key, 400 bad bbox, ...).
            snippet = content[:400].decode("utf-8", "replace").strip()
            raise ValueError(
                f"OpenTopography did not return a GeoTIFF (dem {self.dem!r}, "
                f"HTTP {resp.status_code}). Server said:\n{snippet}"
            )
        # The global DEMs are delivered in EPSG:4326.
        return geotiff_from_bytes(
            content, bbox, src_crs="EPSG:4326",
            fetch_resolution_m=fetch_resolution_m, target_crs=target_crs,
        )
