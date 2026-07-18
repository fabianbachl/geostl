# geostl

Turn public **elevation data (GeoTIFF/DEM)** into **3D-printable terrain models (STL)**.

Pick a rectangle on the earth in WGS84 coordinates; `geostl` fetches the height data covering
it, rectifies it to a metric grid, scales it to your print bed, and writes a watertight STL —
either as a single section or as a grid of seam-matched tiles that fit together.

> **Status: pre-alpha scaffold.** The package structure, public API surface, and the
> data-source abstraction are in place; most method bodies are stubs that raise
> `NotImplementedError`. See [DESIGN.md](DESIGN.md) for the architecture and the phased
> implementation roadmap.

## Install (development)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\Activate.ps1
# POSIX:    source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.11+ (developed on 3.14). Optional extras: `viz` (matplotlib previews),
`fallback` (geopy geodesic rectification), `validate` (trimesh watertight checks).

## Quickstart (target API)

```python
from geostl import Region, GeoPoint
from geostl.sources import LocalGeoTiffSource

region = Region.from_corners(GeoPoint(47.691855, 14.039583),
                             GeoPoint(47.723852, 14.089708))
src = LocalGeoTiffSource("assets/DGM_R25.tif")

# Single section
section = region.to_section(src, resolution_m=25)
section.scale(bed_size_mm=200, z_exaggeration=1.8, base_thickness_mm=3)
section.export_stl("terrain.stl")

# 3x3 tiled grid (seams matched, one shared scale)
grid = region.to_grid(src, nx=3, ny=3, resolution_m=25)
grid.scale(bed_size_mm=200, z_exaggeration=1.8, base_thickness_mm=3)
grid.export_stl("out/", prefix="tile")
```

## Architecture (one line)

`Region` (WGS84) → `ElevationSource.fetch` → `ElevationTile` (metric grid) → rectify → scale →
`Mesher` → watertight STL. Supporting a new country/API means writing **one** new
`ElevationSource` adapter; nothing downstream changes. Full detail in [DESIGN.md](DESIGN.md).

## License

MIT — see [LICENSE](LICENSE).
