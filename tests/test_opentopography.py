"""Tests for OpenTopographySource (mocked HTTP, no network)."""
import numpy as np
import pytest
import requests
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from geostl.positioning import BoundingBox
from geostl.sources.opentopography import OpenTopographySource

# A small box near Bolzano — the global fallback works anywhere.
_BBOX = BoundingBox(south=46.46, west=11.30, north=46.50, east=11.36)


def _dem_tiff(bbox, res_deg=0.0003, pad=0.002):
    """A synthetic EPSG:4326 DEM GeoTIFF covering ``bbox`` (as OpenTopography returns)."""
    west, south, east, north = bbox.west - pad, bbox.south - pad, bbox.east + pad, bbox.north + pad
    width = int((east - west) / res_deg)
    height = int((north - south) / res_deg)
    yy, xx = np.mgrid[0:height, 0:width]
    data = (500.0 + xx + yy).astype("float32")
    transform = from_origin(west, north, res_deg, res_deg)
    with MemoryFile() as mf:
        with mf.open(
            driver="GTiff", width=width, height=height, count=1, dtype="float32",
            crs="EPSG:4326", transform=transform, nodata=-32768.0,
        ) as ds:
            ds.write(data, 1)
        return mf.read()


class _Resp:
    def __init__(self, content, status=200):
        self.content = content
        self.status_code = status


def test_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENTOPOGRAPHY_API_KEY", raising=False)
    with pytest.raises(ValueError, match="requires an API key"):
        OpenTopographySource().fetch(_BBOX)


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("OPENTOPOGRAPHY_API_KEY", "envkey")
    assert OpenTopographySource().api_key == "envkey"


def test_invalid_dem_rejected():
    with pytest.raises(ValueError):
        OpenTopographySource(api_key="k", dem="NOPE")


def test_fetch_reads_dem(monkeypatch):
    tiff = _dem_tiff(_BBOX)
    captured = {}

    def fake_get(url, params=None, **kwargs):
        captured["params"] = params
        return _Resp(tiff)

    monkeypatch.setattr(requests, "get", fake_get)
    tile = OpenTopographySource(api_key="k", dem="COP30").fetch(_BBOX, fetch_resolution_m=30.0)

    assert captured["params"]["demtype"] == "COP30"
    assert captured["params"]["API_Key"] == "k"
    assert (captured["params"]["south"], captured["params"]["north"]) == (_BBOX.south, _BBOX.north)
    assert tile.crs == "EPSG:32632"  # reprojected to auto-UTM
    assert np.isfinite(tile.heights).any()


def test_error_body_raises(monkeypatch):
    err = b'<?xml version="1.0"?><error>Error: API Key required for access.</error>'
    monkeypatch.setattr(requests, "get", lambda url, params=None, **kw: _Resp(err, status=401))
    with pytest.raises(ValueError, match="did not return a GeoTIFF"):
        OpenTopographySource(api_key="bad").fetch(_BBOX)
