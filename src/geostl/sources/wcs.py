"""WCSSource — fetch a bbox from an OGC Web Coverage Service (WCS 2.0.1).

A WCS server crops the coverage *server-side* and returns a GeoTIFF, so unlike a
tiled COG dataset there is nothing to discover or mosaic: one ``GetCoverage``
request yields exactly the requested rectangle. The returned GeoTIFF is handed to
the same shared ingestion path as every other source
(:mod:`geostl.sources._raster`) via an in-memory GDAL file, so cropping,
reprojection to the metric grid, and nodata handling stay in one place.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Sequence, Tuple

from geostl.sources.base import ElevationSource

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.positioning import BoundingBox

# GeoTIFF / BigTIFF magic numbers — used to tell a coverage from an XML
# ExceptionReport (a WCS server reports errors with HTTP 200 + an XML body).
_TIFF_MAGIC = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")


class WCSSource(ElevationSource):
    """Fetch elevation from an OGC Web Coverage Service (WCS 2.0.1 ``GetCoverage``).

    The request bbox is reprojected into the coverage's own CRS and sent as a
    server-side subset; the server returns a cropped GeoTIFF which is read through
    the shared ingestion path. When ``fetch_resolution_m`` and the coverage's
    ``native_res_m`` are both known, the read is coarsened server-side via the WCS
    *Scaling* extension (``scalefactor``), so only the pixels asked for are
    transferred — important for fine (sub-metre) coverages.

    Args:
        endpoint: the WCS service URL (the ``ows``/``wcs`` endpoint, no query).
        coverage_id: the coverage identifier. GeoServer joins a workspace and
            layer with a double underscore, e.g.
            ``"p_bz-Elevation__DigitalTerrainModel-0.5m"``.
        crs: the coverage's native CRS (an EPSG string); the subset is expressed
            in it and it is trusted as the source CRS when reprojecting.
        axis_labels: the coverage's subset axis labels, in ``(easting, northing)``
            order (GeoServer typically uses ``("E", "N")``).
        native_res_m: the coverage's native pixel size in metres. When given, a
            coarser ``fetch_resolution_m`` is turned into a ``scalefactor`` so the
            server downsamples before sending; without it, the crop is sent at
            full detail and any downsampling happens client-side.
        version: WCS version (``"2.0.1"``).
        fmt: requested output format (a GeoTIFF media type).
        timeout: per-request timeout in seconds (a full-detail crop can be large).
    """

    def __init__(
        self,
        endpoint: str,
        coverage_id: str,
        *,
        crs: str,
        axis_labels: Tuple[str, str] = ("E", "N"),
        native_res_m: Optional[float] = None,
        version: str = "2.0.1",
        fmt: str = "image/tiff",
        timeout: float = 120.0,
    ):
        self.endpoint = endpoint
        self.coverage_id = coverage_id
        self.crs = crs
        self.axis_labels = tuple(axis_labels)
        self.native_res_m = native_res_m
        self.version = version
        self.fmt = fmt
        self.timeout = timeout

    def _params(self, bbox: "BoundingBox", fetch_resolution_m: Optional[float]) -> dict:
        from rasterio.warp import transform_bounds

        # The subset must be given in the coverage's own CRS.
        left, bottom, right, top = transform_bounds(
            "EPSG:4326", self.crs, *bbox.as_tuple()
        )
        # Pad so the crop provably contains the (rotated) reprojected output grid.
        pad = max(50.0, 4.0 * (fetch_resolution_m or 1.0))
        left, bottom, right, top = left - pad, bottom - pad, right + pad, top + pad

        e_axis, n_axis = self.axis_labels
        params = {
            "service": "WCS",
            "version": self.version,
            "request": "GetCoverage",
            "coverageId": self.coverage_id,
            "format": self.fmt,
            # a list becomes repeated keys: subset=E(..)&subset=N(..)
            "subset": [f"{e_axis}({left},{right})", f"{n_axis}({bottom},{top})"],
        }
        if fetch_resolution_m and self.native_res_m:
            # scalefactor scales every axis uniformly; <1 downsamples. Only ask the
            # server to coarsen (never upsample beyond the native grid).
            factor = self.native_res_m / fetch_resolution_m
            if factor < 1.0:
                params["scalefactor"] = f"{factor:.6g}"
        return params

    def _build_url(self, bbox: "BoundingBox", fetch_resolution_m: Optional[float]) -> str:
        # Build the query string ourselves: this server's front proxy 404s on
        # percent-encoded parentheses/commas, and requests' requote_uri leaves the
        # KVP syntax characters "(),/" literal when they are already in the URL.
        pairs = []
        for key, value in self._params(bbox, fetch_resolution_m).items():
            values = value if isinstance(value, (list, tuple)) else [value]
            pairs.extend(f"{key}={item}" for item in values)
        return f"{self.endpoint}?{'&'.join(pairs)}"

    def fetch(
        self,
        bbox: "BoundingBox",
        *,
        fetch_resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "ElevationTile":
        import requests
        from rasterio.io import MemoryFile

        from geostl.sources._raster import fetch_rasters

        resp = requests.get(
            self._build_url(bbox, fetch_resolution_m), timeout=self.timeout
        )
        resp.raise_for_status()
        content = resp.content
        if not content.startswith(_TIFF_MAGIC):
            # A WCS server returns errors as an XML body with HTTP 200.
            snippet = content[:400].decode("utf-8", "replace").strip()
            raise ValueError(
                f"WCS GetCoverage did not return a GeoTIFF from {self.endpoint} "
                f"(coverage {self.coverage_id!r}). Server said:\n{snippet}"
            )

        # Read the server-cropped GeoTIFF through the one shared ingestion path,
        # from GDAL's in-memory filesystem (no temp file on disk).
        with MemoryFile(content) as memfile:
            return fetch_rasters(
                [memfile.name], bbox,
                fetch_resolution_m=fetch_resolution_m,
                target_crs=target_crs, src_crs=self.crs,
            )
