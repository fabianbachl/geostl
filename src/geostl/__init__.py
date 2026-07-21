"""geostl — turn public elevation data (GeoTIFF/DEM) into 3D-printable terrain STL.

Typical use::

    from geostl import Region, GeoPoint
    from geostl.sources import LocalGeoTiffSource

    region = Region.from_corners(GeoPoint(47.69, 14.04), GeoPoint(47.72, 14.09))
    section = region.to_section(LocalGeoTiffSource("assets/DGM_R25.tif"))
    section.scale(bed_size_mm=200, z_exaggeration=1.5, base_thickness_mm=3)
    section.export_stl("terrain.stl", resolution_mm=0.4)

Data-source adapters live in :mod:`geostl.sources` and are imported from there so
that heavy geo dependencies are only pulled in when actually used.
"""
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from geostl.elevation import ElevationTile
from geostl.geometry import BoundingBox, GeoPoint
from geostl.tiling import Grid, Region, Section

try:
    __version__ = _version("geostl")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0"

__all__ = [
    "GeoPoint",
    "BoundingBox",
    "ElevationTile",
    "Region",
    "Section",
    "Grid",
    "__version__",
]
