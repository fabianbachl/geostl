"""Phase 1: LocalGeoTiffSource + reproject_to_metric, via a synthetic GeoTIFF.

No real asset or network is needed — each test writes a tiny WGS84 DEM to a temp
file, so the suite runs anywhere.
"""
from __future__ import annotations

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from geostl import GeoPoint, Region, Section
from geostl.elevation import ElevationTile
from geostl.sources import LocalGeoTiffSource

# Synthetic source raster covers lon [14.00, 14.12], lat [47.67, 47.75].
_SRC_MAX = 1100.0
_SRC_MIN = 300.0


def _write_synthetic_dem(path) -> None:
    """Write a small WGS84 DEM (a gaussian hill) covering the Austria test bbox."""
    west, north = 14.00, 47.75
    xres = yres = 0.0002  # ~15-22 m per pixel
    width, height = 600, 400
    transform = from_origin(west, north, xres, yres)
    yy, xx = np.mgrid[0:height, 0:width]
    cx, cy = width / 2, height / 2
    heights = (
        (_SRC_MAX - _SRC_MIN)
        * np.exp(-(((xx - cx) / 120) ** 2 + ((yy - cy) / 90) ** 2))
        + _SRC_MIN
    ).astype("float32")
    with rasterio.open(
        path, "w", driver="GTiff", width=width, height=height, count=1,
        dtype="float32", crs="EPSG:4326", transform=transform, nodata=0.0,
    ) as ds:
        ds.write(heights, 1)


def _region() -> Region:
    return Region.from_corners(GeoPoint(47.69, 14.03), GeoPoint(47.73, 14.09))


def test_fetch_returns_metric_tile(tmp_path):
    dem = tmp_path / "dem.tif"
    _write_synthetic_dem(dem)

    tile = LocalGeoTiffSource(dem).fetch(_region().bbox, fetch_resolution_m=50)

    assert isinstance(tile, ElevationTile)
    assert tile.heights.ndim == 2
    assert tile.crs == "EPSG:32633"  # auto-UTM 33N for ~14E, 47.7N
    assert tile.pixel_size_m() == pytest.approx((50.0, 50.0))

    h, w = tile.heights.shape
    assert 70 < h < 110  # bbox ~4.4 km tall at 50 m
    assert 70 < w < 110  # bbox ~4.5 km wide at 50 m

    finite = tile.heights[np.isfinite(tile.heights)]
    assert finite.size > 0
    assert finite.max() <= _SRC_MAX + 1.0
    assert finite.min() >= _SRC_MIN - 1.0


def test_target_crs_override(tmp_path):
    dem = tmp_path / "dem.tif"
    _write_synthetic_dem(dem)

    tile = LocalGeoTiffSource(dem).fetch(
        _region().bbox, fetch_resolution_m=50, target_crs="EPSG:31287"
    )
    assert tile.crs == "EPSG:31287"


def test_region_to_section_wraps_tile(tmp_path):
    dem = tmp_path / "dem.tif"
    _write_synthetic_dem(dem)

    section = _region().to_section(
        LocalGeoTiffSource(dem), bed_size_mm=200.0, fetch_resolution_m=50
    )
    assert isinstance(section, Section)
    assert section.scale_xy_mm_per_m is not None  # born scaled
    assert section.tile.crs == "EPSG:32633"
    assert section.tile.heights.ndim == 2


def test_bbox_outside_raster_raises(tmp_path):
    dem = tmp_path / "dem.tif"
    _write_synthetic_dem(dem)

    # Somewhere in the Pacific — no overlap with the Austrian source raster.
    off = Region.from_corners(GeoPoint(0.0, -150.0), GeoPoint(0.1, -149.9))
    with pytest.raises(ValueError):
        LocalGeoTiffSource(dem).fetch(off.bbox, fetch_resolution_m=50)


def test_rotated_source_crs_fully_covers_output(tmp_path):
    """A source in a rotated CRS (EPSG:31287, Austria Lambert) must still fully
    cover the UTM output grid — no NaN wedges at the corners (regression)."""
    from rasterio.transform import from_origin
    from rasterio.warp import transform_bounds

    from geostl.positioning import BoundingBox

    path = tmp_path / "lambert.tif"
    res, n = 50.0, 500
    x0, ytop = 450000.0, 350000.0  # inside the Austrian Lambert domain
    transform = from_origin(x0, ytop, res, res)
    data = np.linspace(500.0, 2000.0, n * n, dtype="float32").reshape(n, n)
    with rasterio.open(
        path, "w", driver="GTiff", width=n, height=n, count=1,
        dtype="float32", crs="EPSG:31287", transform=transform, nodata=0.0,
    ) as ds:
        ds.write(data, 1)

    # WGS84 extent of the raster, shrunk 20% so the query is safely inside the data.
    west, south, east, north = transform_bounds(
        "EPSG:31287", "EPSG:4326", x0, ytop - n * res, x0 + n * res, ytop
    )
    mx, my = (east - west) * 0.2, (north - south) * 0.2
    bbox = BoundingBox(south=south + my, west=west + mx, north=north - my, east=east - mx)

    tile = LocalGeoTiffSource(path).fetch(bbox, fetch_resolution_m=100)
    assert np.isfinite(tile.heights).all()


def test_native_read_is_finer_than_capped(tmp_path):
    """Without fetch_resolution_m the source is read at native detail — finer and
    more pixels than a coarse cap."""
    dem = tmp_path / "dem.tif"
    _write_synthetic_dem(dem)
    src = LocalGeoTiffSource(dem)

    native = src.fetch(_region().bbox)                          # native (max) detail
    capped = src.fetch(_region().bbox, fetch_resolution_m=100)  # coarse read

    assert native.heights.size > capped.heights.size
    assert max(native.pixel_size_m()) < max(capped.pixel_size_m())
