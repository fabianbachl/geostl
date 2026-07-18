"""WGS84 geometry primitives and metric-CRS selection helpers.

These are pure-Python and dependency-free so the rest of the package (and the
tests) can build on them without importing any geo stack.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GeoPoint:
    """A point in WGS84 geographic coordinates (decimal degrees)."""

    lat: float
    lon: float


@dataclass(frozen=True)
class BoundingBox:
    """An axis-aligned WGS84 rectangle.

    Invariant: ``south < north`` and ``west < east``. Use
    :meth:`from_corners` to build one from arbitrary opposite corners.
    """

    south: float
    west: float
    north: float
    east: float

    def __post_init__(self) -> None:
        if self.south >= self.north:
            raise ValueError(f"south ({self.south}) must be < north ({self.north})")
        if self.west >= self.east:
            raise ValueError(f"west ({self.west}) must be < east ({self.east})")

    @classmethod
    def from_corners(cls, a: GeoPoint, b: GeoPoint) -> "BoundingBox":
        """Build a normalized bbox from any two opposite corners."""
        return cls(
            south=min(a.lat, b.lat),
            west=min(a.lon, b.lon),
            north=max(a.lat, b.lat),
            east=max(a.lon, b.lon),
        )

    def centroid(self) -> GeoPoint:
        """The geometric center of the box."""
        return GeoPoint(
            lat=(self.south + self.north) / 2.0,
            lon=(self.west + self.east) / 2.0,
        )

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Return ``(west, south, east, north)`` — the order rasterio/GDAL expect."""
        return (self.west, self.south, self.east, self.north)


def utm_epsg_for(bbox: BoundingBox) -> int:
    """Return the EPSG code of the UTM zone covering the bbox centroid.

    Uses the standard 6°-wide zoning and picks the northern (``326xx``) or
    southern (``327xx``) band by hemisphere. This is the default choice for a
    locally metric, near-equal-scale horizontal grid.

    Example: a box around 14°E, 47°N (Austria) -> UTM 33N -> ``32633``.
    """
    c = bbox.centroid()
    zone = int(math.floor((c.lon + 180.0) / 6.0)) + 1
    zone = min(max(zone, 1), 60)
    return (32600 if c.lat >= 0 else 32700) + zone
