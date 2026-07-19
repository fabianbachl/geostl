# Quickstart

## Install (development)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\Activate.ps1
# POSIX:    source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.11+ (developed on 3.14).

## Build a section from the Austria DGM API

No data files needed — the tiles are discovered from BEV's ATOM service and read via GDAL
`/vsicurl` (network required):

```python
from geostl import Region, GeoPoint
from geostl.sources import AustriaDGMSource

region = Region.from_corners(GeoPoint(47.691855, 14.039583),
                             GeoPoint(47.723852, 14.089708))
source = AustriaDGMSource()  # 1 m ALS terrain model from data.bev.gv.at

section = region.to_section(source, resolution_m=25)
section.scale(bed_size_mm=200, z_exaggeration=1.0, base_thickness_mm=3)
section.export_stl("terrain.stl")
```

## Choose a different source

The pipeline is source-agnostic — swap the source and nothing else changes:

```python
from geostl.sources import LocalGeoTiffSource, RemoteCOGSource

source = LocalGeoTiffSource("assets/DGM_R25.tif")        # any local GeoTIFF
source = RemoteCOGSource("https://example.com/dem.tif")  # any remote COG
```

## Build a tiled grid

```python
grid = region.to_grid(source, nx=3, ny=3, resolution_m=25)
grid.scale(bed_size_mm=200, z_exaggeration=1.0, base_thickness_mm=3)
grid.export_stl("out/", prefix="tile")   # out/tile_r0_c0.stl ...
```

The whole region is fetched once and split into tiles with shared edge pixels, so the printed
pieces butt together seamlessly.

## Build the documentation

```bash
pip install -e ".[docs]"
python -m sphinx -b html docs docs/_build/html
```
