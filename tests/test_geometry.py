"""Tests for the pure-Python WGS84 geometry helpers."""
import pytest

from geostl.geometry import BoundingBox, GeoPoint, utm_epsg_for


def test_from_corners_normalizes_order():
    a = GeoPoint(lat=47.72, lon=14.09)
    b = GeoPoint(lat=47.69, lon=14.04)
    bbox = BoundingBox.from_corners(a, b)
    assert (bbox.south, bbox.north) == (47.69, 47.72)
    assert (bbox.west, bbox.east) == (14.04, 14.09)


def test_centroid():
    bbox = BoundingBox(south=47.0, west=14.0, north=48.0, east=16.0)
    c = bbox.centroid()
    assert c.lat == pytest.approx(47.5)
    assert c.lon == pytest.approx(15.0)


def test_as_tuple_is_west_south_east_north():
    bbox = BoundingBox(south=1.0, west=2.0, north=3.0, east=4.0)
    assert bbox.as_tuple() == (2.0, 1.0, 4.0, 3.0)


def test_invalid_bbox_raises():
    with pytest.raises(ValueError):
        BoundingBox(south=48.0, west=14.0, north=47.0, east=16.0)


@pytest.mark.parametrize(
    "lon,lat,expected",
    [
        (14.06, 47.7, 32633),   # Austria      -> UTM 33N
        (-122.3, 47.6, 32610),  # Seattle      -> UTM 10N
        (151.2, -33.9, 32756),  # Sydney       -> UTM 56S
    ],
)
def test_utm_epsg_selection(lon, lat, expected):
    bbox = BoundingBox(
        south=lat - 0.05, west=lon - 0.05, north=lat + 0.05, east=lon + 0.05
    )
    assert utm_epsg_for(bbox) == expected
