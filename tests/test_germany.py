"""Tests for BavariaDGMSource tile discovery (mocked HTTP, no network)."""
import re

import pytest
import requests

from geostl.positioning import BoundingBox
from geostl.sources.germany import BavariaDGMSource

# A small box in the Bavarian Alps near Garmisch-Partenkirchen.
_BBOX = BoundingBox(south=47.48, west=11.05, north=47.51, east=11.10)


def test_candidate_tiles_are_km_cells():
    names = BavariaDGMSource()._candidate_tiles(_BBOX)
    assert names, "expected at least one covering tile"
    assert all(re.fullmatch(r"\d+_\d+\.tif", n) for n in names)
    # UTM32 easting ~640-680 km, northing ~5260-5270 km for this area.
    for n in names:
        e_km, n_km = (int(x) for x in n[:-4].split("_"))
        assert 600 <= e_km <= 720
        assert 5200 <= n_km <= 5350


def test_tile_urls_keeps_only_existing(monkeypatch):
    # Pretend only tiles whose easting-km is even actually exist on the server.
    def fake_get(url, **kwargs):
        e_km = int(url.rsplit("/", 1)[1].split("_", 1)[0])
        status = 206 if e_km % 2 == 0 else 404

        class _R:
            status_code = status

            def close(self):
                pass

        return _R()

    monkeypatch.setattr(requests, "get", fake_get)
    urls = BavariaDGMSource()._tile_urls(_BBOX)
    assert urls, "some tiles should survive the existence probe"
    assert all(url.startswith("https://download1.bayernwolke.de/a/dgm/dgm1/") for url in urls)
    assert all(int(url.rsplit("/", 1)[1].split("_", 1)[0]) % 2 == 0 for url in urls)


def test_fetch_raises_when_no_tiles_exist(monkeypatch):
    def fake_get(url, **kwargs):
        class _R:
            status_code = 404

            def close(self):
                pass

        return _R()

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(ValueError):
        BavariaDGMSource().fetch(_BBOX)


def test_probe_failure_is_treated_as_missing(monkeypatch):
    def boom(url, **kwargs):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(requests, "get", boom)
    assert BavariaDGMSource()._tile_urls(_BBOX) == []
