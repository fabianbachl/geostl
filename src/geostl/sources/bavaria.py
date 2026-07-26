"""Southern-Germany elevation sources. Currently: Bavaria (Freistaat Bayern)."""
from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, List, Optional

from geostl.sources.base import ElevationSource

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.positioning import BoundingBox

# Bavaria publishes DGM1 as 1 km GeoTIFF tiles on an EPSG:25832 (UTM 32N) grid.
# A tile is named "<E_km>_<N_km>.tif" after its lower-left corner in kilometres,
# e.g. "720_5287.tif" covers E 720000..721000, N 5287000..5288000.
_BASE = "https://download1.bayernwolke.de/a/dgm/dgm1"
_CRS = "EPSG:25832"
_TILE_M = 1000


class BavariaDGMSource(ElevationSource):
    """Bavaria's national 1 m LiDAR terrain model (DGM1) as open GeoTIFF tiles.

    The Bavarian surveying office (LDBV) publishes DGM1 — a 1 m airborne-LiDAR
    digital terrain model of the whole Free State, including the Bavarian Alps and
    the Berchtesgaden and Allgäu ranges — as 1 km × 1 km GeoTIFF tiles on an
    EPSG:25832 grid, free to use (CC-BY-4.0 / Datenlizenz Deutschland). Tile URLs
    are deterministic from a tile's lower-left UTM32 kilometre coordinates, so
    :meth:`fetch` derives the covering tiles from the bbox, keeps the ones that
    actually exist (the grid is clipped to the state border), and delegates the
    reading to :class:`~geostl.sources.cog.RemoteCOGSource` — remote-raster
    handling then lives in exactly one place.

    Data source: Landesamt für Digitalisierung, Breitband und Vermessung (LDBV),
    https://geodaten.bayern.de/opengeodata/ (DGM1).
    """

    def __init__(self, *, base_url: str = _BASE, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _candidate_tiles(self, bbox: "BoundingBox") -> List[str]:
        """Names of every 1 km tile whose cell overlaps ``bbox`` (existence unchecked)."""
        from rasterio.warp import transform_bounds

        left, bottom, right, top = transform_bounds("EPSG:4326", _CRS, *bbox.as_tuple())
        e0, e1 = math.floor(left / _TILE_M), math.floor(right / _TILE_M)
        n0, n1 = math.floor(bottom / _TILE_M), math.floor(top / _TILE_M)
        return [
            f"{e}_{n}.tif"
            for e in range(e0, e1 + 1)
            for n in range(n0, n1 + 1)
        ]

    def _exists(self, url: str) -> bool:
        import requests

        try:
            # A one-byte ranged GET is a universally supported existence probe
            # (some CDNs disallow HEAD); tiles outside the state border 404.
            resp = requests.get(
                url, headers={"Range": "bytes=0-0"},
                timeout=self.timeout, stream=True,
            )
            resp.close()
            return resp.status_code in (200, 206)
        except requests.RequestException:
            return False

    def _tile_urls(self, bbox: "BoundingBox") -> List[str]:
        candidates = [f"{self.base_url}/{name}" for name in self._candidate_tiles(bbox)]
        if not candidates:
            return []
        workers = min(16, len(candidates))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            keep = list(pool.map(self._exists, candidates))
        return [url for url, ok in zip(candidates, keep) if ok]

    def fetch(
        self,
        bbox: "BoundingBox",
        *,
        fetch_resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "ElevationTile":
        from geostl.sources.cog import RemoteCOGSource

        urls = self._tile_urls(bbox)
        if not urls:
            raise ValueError(
                "no Bavaria DGM1 tiles cover this bbox (outside Bavaria, or the "
                "tile server is unreachable)"
            )
        return RemoteCOGSource(urls, src_crs=_CRS).fetch(
            bbox, fetch_resolution_m=fetch_resolution_m, target_crs=target_crs
        )
