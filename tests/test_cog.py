"""Tests for RemoteCOGSource URL handling + delegation (no network)."""
import geostl.sources._raster as _raster
from geostl.geometry import BoundingBox
from geostl.sources import RemoteCOGSource

_BBOX = BoundingBox(south=1.0, west=2.0, north=3.0, east=4.0)


def test_single_url_is_vsicurl_prefixed(monkeypatch):
    captured = {}

    def fake(sources, bbox, **kwargs):
        captured["sources"] = list(sources)
        captured["kwargs"] = kwargs
        return "TILE"

    monkeypatch.setattr(_raster, "fetch_rasters", fake)
    out = RemoteCOGSource("https://x/y.tif").fetch(_BBOX, resolution_m=25)

    assert out == "TILE"
    assert captured["sources"] == ["/vsicurl/https://x/y.tif"]
    assert captured["kwargs"]["resolution_m"] == 25


def test_multiple_urls_and_idempotent_prefix(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        _raster, "fetch_rasters",
        lambda sources, bbox, **kw: captured.setdefault("sources", list(sources)),
    )
    RemoteCOGSource(["a.tif", "/vsicurl/b.tif"]).fetch(_BBOX)
    assert captured["sources"] == ["/vsicurl/a.tif", "/vsicurl/b.tif"]
