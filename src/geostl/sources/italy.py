"""Northern-Italy elevation sources. Currently: South Tyrol (Alto Adige / Südtirol)."""
from __future__ import annotations

from geostl.sources.wcs import WCSSource

# GeoServer WCS endpoint of the Autonomous Province of Bolzano / South Tyrol.
_ENDPOINT = "https://geoservices9.civis.bz.it/geoserver/ows"

# Coverage ids (GeoServer joins workspace + layer with a double underscore).
_COVERAGES = {
    "0.5m": "p_bz-Elevation__DigitalTerrainModel-0.5m",
    "2.5m": "p_bz-Elevation__DigitalTerrainModel-2.5m",
}


class SouthTyrolDGMSource(WCSSource):
    """South Tyrol's LiDAR digital terrain model (Province of Bolzano) via WCS.

    An airborne-LiDAR terrain model of the autonomous province — the Dolomites,
    Ortler and Vinschgau, adjoining Austrian Tyrol — on an EPSG:25832 grid,
    released under CC0. It is served as an OGC Web Coverage Service, so
    :meth:`fetch` asks the server for the requested rectangle and reads the
    returned GeoTIFF through the shared ingestion path (see
    :class:`~geostl.sources.wcs.WCSSource`); there are no tiles to discover.

    Two products are published. The **2.5 m** model (the default) covers the whole
    province and is the safe choice. The **0.5 m** model is much finer but is only
    published for parts of the province (valley floors and flown corridors); over
    high-alpine terrain it returns nodata, so it is opt-in. At a print-bed scale
    2.5 m ground sampling is already far finer than the printed pixel size.

    Because the 0.5 m grid is sub-metre, fetching a large area of it at full detail
    transfers a lot of data — pass ``fetch_resolution_m`` to have the server
    downsample the crop before sending it.

    Args:
        resolution: which published model to use — ``"2.5m"`` (default, full
            coverage) or ``"0.5m"`` (finer, but partial coverage).

    Data source: Autonomous Province of Bolzano – South Tyrol, https://data.civis.bz.it
    (Modello digitale del terreno / Digitales Geländemodell, CC0).
    """

    def __init__(self, *, resolution: str = "2.5m", timeout: float = 120.0):
        if resolution not in _COVERAGES:
            raise ValueError(
                f"resolution must be one of {sorted(_COVERAGES)}, got {resolution!r}"
            )
        self.resolution = resolution
        super().__init__(
            _ENDPOINT,
            _COVERAGES[resolution],
            crs="EPSG:25832",
            axis_labels=("E", "N"),
            native_res_m=float(resolution.rstrip("m")),
            timeout=timeout,
        )
