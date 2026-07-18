# Quickstart

## Install (development)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\Activate.ps1
# POSIX:    source .venv/bin/activate
pip install -e ".[dev,docs]"
```

Requires Python 3.11+ (developed on 3.14).

## Build a single section

```python
from geostl import Region, GeoPoint
from geostl.sources import LocalGeoTiffSource

region = Region.from_corners(GeoPoint(47.691855, 14.039583),
                             GeoPoint(47.723852, 14.089708))
src = LocalGeoTiffSource("assets/DGM_R25.tif")

section = region.to_section(src, resolution_m=25)
section.scale(bed_size_mm=200, z_exaggeration=1.8, base_thickness_mm=3)
section.export_stl("terrain.stl")
```

## Build a tiled grid

```python
grid = region.to_grid(src, nx=3, ny=3, resolution_m=25)
grid.scale(bed_size_mm=200, z_exaggeration=1.8, base_thickness_mm=3)
grid.export_stl("out/", prefix="tile")   # out/tile_r0_c0.stl ...
```

The whole region is fetched in a single warp and split into tiles with shared edge pixels,
so the printed pieces butt together seamlessly.

## Build the documentation

```bash
python -m sphinx -b html docs docs/_build/html
```
