"""Tests for the shared raster ingestion (windowed read + reproject + mosaic)."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from geostl.positioning import BoundingBox
from geostl.sources._raster import fetch_rasters


def _write(path, *, west, north, width, height, res_deg=0.0002, fill=None):
    transform = from_origin(west, north, res_deg, res_deg)
    if fill is None:
        yy, xx = np.mgrid[0:height, 0:width]
        data = (xx + yy).astype("float32")
    else:
        data = np.full((height, width), float(fill), "float32")
    with rasterio.open(
        path, "w", driver="GTiff", width=width, height=height, count=1,
        dtype="float32", crs="EPSG:4326", transform=transform, nodata=-9999.0,
    ) as ds:
        ds.write(data, 1)


def test_single_source(tmp_path):
    p = tmp_path / "a.tif"
    _write(p, west=14.0, north=47.75, width=600, height=400)
    bbox = BoundingBox(south=47.69, west=14.03, north=47.73, east=14.09)
    tile = fetch_rasters([str(p)], bbox, fetch_resolution_m=50)
    assert tile.heights.ndim == 2
    assert tile.crs == "EPSG:32633"
    assert np.isfinite(tile.heights).all()


def test_two_tile_mosaic(tmp_path):
    left = tmp_path / "left.tif"
    right = tmp_path / "right.tif"
    # Two adjacent WGS84 tiles (abutting at lon 14.06), constant but different fills.
    _write(left, west=14.00, north=47.75, width=300, height=400, fill=100.0)
    _write(right, west=14.06, north=47.75, width=300, height=400, fill=200.0)
    bbox = BoundingBox(south=47.69, west=14.02, north=47.73, east=14.10)

    only_left = fetch_rasters([str(left)], bbox, fetch_resolution_m=50)
    both = fetch_rasters([str(left), str(right)], bbox, fetch_resolution_m=50)

    # The mosaic covers strictly more than one tile alone...
    assert np.isfinite(both.heights).mean() > np.isfinite(only_left.heights).mean()
    fin = both.heights[np.isfinite(both.heights)]
    # ...and its values come from the two source fills.
    assert (np.isclose(fin, 100.0) | np.isclose(fin, 200.0)).mean() > 0.99
    assert np.isclose(fin, 100.0).any() and np.isclose(fin, 200.0).any()


def test_no_overlap_raises(tmp_path):
    p = tmp_path / "a.tif"
    _write(p, west=14.0, north=47.75, width=100, height=100)
    bbox = BoundingBox(south=0.0, west=-150.0, north=0.1, east=-149.9)
    with pytest.raises(ValueError):
        fetch_rasters([str(p)], bbox, fetch_resolution_m=50)


def test_empty_sources_raises():
    bbox = BoundingBox(south=1.0, west=2.0, north=3.0, east=4.0)
    with pytest.raises(ValueError):
        fetch_rasters([], bbox, fetch_resolution_m=50)
