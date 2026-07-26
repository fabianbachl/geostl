"""Tests for the WCS source and its South Tyrol preset (mocked HTTP, no network)."""
import numpy as np
import pytest
import rasterio
import requests
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds

from geostl.positioning import BoundingBox
from geostl.sources.south_tyrol import SouthTyrolDGMSource
from geostl.sources.wcs import WCSSource

# A small box near Bolzano / Bozen, South Tyrol.
_BBOX = BoundingBox(south=46.46, west=11.30, north=46.50, east=11.36)


def _coverage_tiff(bbox, res_m=10.0, pad=200.0):
    """A synthetic EPSG:25832 DTM GeoTIFF covering ``bbox`` (as a WCS server would)."""
    left, bottom, right, top = transform_bounds("EPSG:4326", "EPSG:25832", *bbox.as_tuple())
    left, bottom, right, top = left - pad, bottom - pad, right + pad, top + pad
    width = int((right - left) / res_m)
    height = int((top - bottom) / res_m)
    yy, xx = np.mgrid[0:height, 0:width]
    data = (1000.0 + 0.1 * xx + 0.2 * yy).astype("float32")
    transform = from_origin(left, top, res_m, res_m)
    with MemoryFile() as mf:
        with mf.open(
            driver="GTiff", width=width, height=height, count=1, dtype="float32",
            crs="EPSG:25832", transform=transform, nodata=-9999.0,
        ) as ds:
            ds.write(data, 1)
        return mf.read()


class _Resp:
    def __init__(self, content, status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        pass


def test_params_subset_and_scaling():
    src = SouthTyrolDGMSource(resolution="0.5m")
    p = src._params(_BBOX, fetch_resolution_m=5.0)
    assert p["coverageId"] == "p_bz-Elevation__DigitalTerrainModel-0.5m"
    assert p["request"] == "GetCoverage" and p["version"] == "2.0.1"
    subset = p["subset"]
    assert any(s.startswith("E(") for s in subset)
    assert any(s.startswith("N(") for s in subset)
    # 0.5 m native, 5 m target -> scalefactor 0.1 (server-side downsample).
    assert p["scalefactor"] == "0.1"

    # Native (no cap) read requests no server-side scaling.
    assert "scalefactor" not in src._params(_BBOX, fetch_resolution_m=None)
    # A finer-than-native request never upsamples server-side.
    assert "scalefactor" not in src._params(_BBOX, fetch_resolution_m=0.25)


def test_fetch_reads_server_crop(monkeypatch):
    tiff = _coverage_tiff(_BBOX)

    def fake_get(url, **kwargs):
        assert "geoserver" in url
        return _Resp(tiff)

    monkeypatch.setattr(requests, "get", fake_get)
    tile = SouthTyrolDGMSource().fetch(_BBOX, fetch_resolution_m=10.0)

    assert tile.heights.ndim == 2
    assert tile.crs == "EPSG:32632"  # auto-UTM for ~11.3E
    assert np.isfinite(tile.heights).any()


def test_non_tiff_body_raises(monkeypatch):
    xml = b'<?xml version="1.0"?><ExceptionReport>bad coverage</ExceptionReport>'
    monkeypatch.setattr(requests, "get", lambda url, **kw: _Resp(xml))
    with pytest.raises(ValueError, match="did not return a GeoTIFF"):
        SouthTyrolDGMSource().fetch(_BBOX)


def test_invalid_resolution_rejected():
    with pytest.raises(ValueError):
        SouthTyrolDGMSource(resolution="9m")


def test_built_url_keeps_parentheses_literal():
    # The province's proxy 404s on percent-encoded "(" / "," — they must stay literal.
    url = SouthTyrolDGMSource(resolution="0.5m")._build_url(_BBOX, fetch_resolution_m=5.0)
    assert "subset=E(" in url and "subset=N(" in url
    assert "%28" not in url and "%2C" not in url and "%2F" not in url
    assert "scalefactor=0.1" in url


def test_generic_wcs_source_is_configurable():
    src = WCSSource("http://x/ows", "ws__cov", crs="EPSG:25832", axis_labels=("X", "Y"))
    p = src._params(_BBOX, fetch_resolution_m=None)
    assert p["coverageId"] == "ws__cov"
    assert any(s.startswith("X(") for s in p["subset"])
    assert any(s.startswith("Y(") for s in p["subset"])
