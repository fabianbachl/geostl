"""AustriaDGMSource — BEV ALS Digitales Geländemodell (DGM), the primary source."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Dict, List, Optional

from geostl.sources.base import ElevationSource

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.positioning import BoundingBox

_ATOM = "http://www.w3.org/2005/Atom"
_GEORSS = "http://www.georss.org/georss"

# INSPIRE ATOM download service for BEV ALS elevation (DTM + DSM, all series).
_SERVICE_FEED = (
    "https://data.bev.gv.at/geonetwork/srv/atom/describe/service"
    "?uuid=208cff7a-c8aa-42fe-bf4f-2b8156e37528"
)

# Entry titles look like:
#   "ALS DTM CRS3035RES50000mN2700000E4600000 Höhenraster 1m Stichtag 15.09.2025"
_TITLE_RE = re.compile(
    r"ALS\s+(?P<model>DTM|DSM)\s+(?P<tile>CRS3035RES\d+mN\d+E\d+)\b"
    r".*?Stichtag\s+(?P<d>\d{2})\.(?P<m>\d{2})\.(?P<y>\d{4})"
)


class AustriaDGMSource(ElevationSource):
    """Austria's national ALS elevation model (BEV) via its INSPIRE ATOM service.

    The data is a 1 m Airborne-Laser-Scanning terrain (``DTM``) or surface
    (``DSM``) model, published as ~50 km Cloud-Optimized GeoTIFF tiles on an
    EPSG:3035 grid under CC-BY-4.0. :meth:`fetch` discovers the tile(s) covering
    the requested bbox from the ATOM feed and then delegates the actual reading to
    :class:`~geostl.sources.cog.RemoteCOGSource`, so remote-COG handling lives in
    exactly one place. Only overview-decimated windows are transferred.

    Tiles are re-flown over time and carry several *Stichtag* (release) series; by
    default the most recent series available for each covering tile is used. Pass
    ``stichtag`` (``"YYYYMMDD"``) to pin a release, or ``model="DSM"`` for the
    surface model.

    Data source: Bundesamt für Eich- und Vermessungswesen (BEV),
    https://data.bev.gv.at (DOI 10.48677/ec12896e-1ecd-47ad-8d48-44d236e383cc).
    """

    def __init__(
        self,
        *,
        model: str = "DTM",
        stichtag: Optional[str] = None,
        service_feed: str = _SERVICE_FEED,
        timeout: float = 60.0,
    ):
        if model not in ("DTM", "DSM"):
            raise ValueError("model must be 'DTM' or 'DSM'")
        self.model = model
        self.stichtag = stichtag
        self.service_feed = service_feed
        self.timeout = timeout
        self._index: Optional[List[Dict]] = None  # cached parsed service feed

    def _load_index(self) -> List[Dict]:
        if self._index is None:
            import requests

            resp = requests.get(self.service_feed, timeout=self.timeout)
            resp.raise_for_status()
            self._index = _parse_service_feed(resp.content)
        return self._index

    def _tile_urls(self, bbox: "BoundingBox") -> List[str]:
        import requests

        query = bbox.as_tuple()  # (w, s, e, n)
        matches = [
            e for e in self._load_index()
            if e["model"] == self.model and _intersects(e["bbox"], query)
        ]
        if self.stichtag is not None:
            matches = [e for e in matches if e["date"] == self.stichtag]

        # Keep, per tile, the chosen (or most recent) Stichtag.
        best: Dict[str, Dict] = {}
        for e in matches:
            cur = best.get(e["tile"])
            if cur is None or e["date"] > cur["date"]:
                best[e["tile"]] = e

        urls: List[str] = []
        for e in best.values():
            resp = requests.get(e["dataset_feed"], timeout=self.timeout)
            resp.raise_for_status()
            urls.extend(_tif_hrefs(resp.content))
        return urls

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
                f"no BEV ALS {self.model} tiles cover this bbox (outside Austria, "
                "or the requested stichtag is unavailable there)"
            )
        # BEV COGs advertise a broken engineering CRS; force EPSG:3035 (per the feed).
        return RemoteCOGSource(urls, src_crs="EPSG:3035").fetch(
            bbox, fetch_resolution_m=fetch_resolution_m, target_crs=target_crs
        )


def _parse_service_feed(xml_bytes: bytes) -> List[Dict]:
    """Parse the ATOM service feed into per-tile entries.

    Each returned dict has ``model``, ``tile``, ``date`` (YYYYMMDD), ``bbox``
    (w, s, e, n in WGS84) and ``dataset_feed`` (URL of the tile's dataset feed).
    """
    root = ET.fromstring(xml_bytes)
    entries: List[Dict] = []
    for e in root.findall(f"{{{_ATOM}}}entry"):
        title = e.findtext(f"{{{_ATOM}}}title") or ""
        poly = e.findtext(f"{{{_GEORSS}}}polygon") or ""
        m = _TITLE_RE.search(title)
        if not (m and poly):
            continue
        dataset_feed = None
        for link in e.findall(f"{{{_ATOM}}}link"):
            if (link.get("type") or "").startswith("application/atom+xml"):
                dataset_feed = link.get("href")
        if not dataset_feed:
            continue
        nums = [float(x) for x in poly.split()]
        lats, lons = nums[0::2], nums[1::2]
        entries.append(
            {
                "model": m["model"],
                "tile": m["tile"],
                "date": f"{m['y']}{m['m']}{m['d']}",
                "bbox": (min(lons), min(lats), max(lons), max(lats)),
                "dataset_feed": dataset_feed,
            }
        )
    return entries


def _tif_hrefs(xml_bytes: bytes) -> List[str]:
    """Return the GeoTIFF download URLs listed in a tile's dataset feed."""
    root = ET.fromstring(xml_bytes)
    urls: List[str] = []
    for e in root.findall(f"{{{_ATOM}}}entry"):
        for link in e.findall(f"{{{_ATOM}}}link"):
            if (link.get("type") or "") == "image/tiff":
                href = link.get("href")
                if href:
                    urls.append(href)
    return urls


def _intersects(a, b) -> bool:  # both (w, s, e, n)
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])
