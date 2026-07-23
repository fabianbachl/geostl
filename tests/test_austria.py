"""Tests for AustriaDGMSource ATOM discovery (mocked HTTP, no network)."""
import pytest
import requests

from geostl.positioning import BoundingBox
from geostl.sources.austria import (
    AustriaDGMSource,
    _intersects,
    _parse_service_feed,
    _tif_hrefs,
)

TILE = "CRS3035RES50000mN2700000E4600000"
_POLY = "47.3 13.9 47.8 13.9 47.8 14.7 47.3 14.7 47.3 13.9"  # lat lon pairs


def _entry(model, stichtag, feed):
    return (
        f"<entry><title>ALS {model} {TILE} Höhenraster 1m Stichtag {stichtag}</title>"
        f'<link type="application/atom+xml" rel="alternate" href="{feed}"/>'
        f"<georss:polygon>{_POLY}</georss:polygon></entry>"
    )


SERVICE_XML = (
    '<feed xmlns="http://www.w3.org/2005/Atom" '
    'xmlns:georss="http://www.georss.org/georss">'
    + _entry("DTM", "15.09.2019", "http://feed/dtm-2019")
    + _entry("DTM", "15.09.2025", "http://feed/dtm-2025")
    + _entry("DSM", "15.09.2025", "http://feed/dsm-2025")
    + "</feed>"
).encode()


def _ds_feed(tif):
    return (
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        f'<entry><link rel="alternate" type="image/tiff" href="{tif}"/></entry>'
        "</feed>"
    ).encode()


_FEEDS = {
    "http://feed/dtm-2019": _ds_feed("http://data/dtm2019.tif"),
    "http://feed/dtm-2025": _ds_feed("http://data/dtm2025.tif"),
    "http://feed/dsm-2025": _ds_feed("http://data/dsm2025.tif"),
}


class _Resp:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


@pytest.fixture
def mock_http(monkeypatch):
    def fake_get(url, **kwargs):
        if "describe/service" in url:
            return _Resp(SERVICE_XML)
        return _Resp(_FEEDS[url])

    monkeypatch.setattr(requests, "get", fake_get)


_BBOX = BoundingBox(south=47.69, west=14.03, north=47.73, east=14.09)


def test_parse_service_feed():
    entries = _parse_service_feed(SERVICE_XML)
    assert len(entries) == 3
    e = entries[0]
    assert (e["model"], e["tile"], e["date"]) == ("DTM", TILE, "20190915")
    assert e["bbox"] == (13.9, 47.3, 14.7, 47.8)
    assert e["dataset_feed"] == "http://feed/dtm-2019"


def test_tif_hrefs():
    assert _tif_hrefs(_ds_feed("http://data/x.tif")) == ["http://data/x.tif"]


def test_intersects():
    assert _intersects((13.9, 47.3, 14.7, 47.8), (14.0, 47.6, 14.1, 47.7))
    assert not _intersects((13.9, 47.3, 14.7, 47.8), (15.0, 47.6, 15.1, 47.7))


def test_default_picks_latest_dtm(mock_http):
    assert AustriaDGMSource()._tile_urls(_BBOX) == ["http://data/dtm2025.tif"]


def test_pinned_stichtag(mock_http):
    src = AustriaDGMSource(stichtag="20190915")
    assert src._tile_urls(_BBOX) == ["http://data/dtm2019.tif"]


def test_dsm_model(mock_http):
    assert AustriaDGMSource(model="DSM")._tile_urls(_BBOX) == ["http://data/dsm2025.tif"]


def test_fetch_raises_when_no_tile_covers(mock_http):
    far = BoundingBox(south=40.0, west=10.0, north=40.1, east=10.1)
    with pytest.raises(ValueError):
        AustriaDGMSource().fetch(far)


def test_invalid_model_rejected():
    with pytest.raises(ValueError):
        AustriaDGMSource(model="XYZ")
