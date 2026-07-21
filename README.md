# geostl

Turn public **elevation data (GeoTIFF/DEM)** into **3D-printable terrain models (STL)**.

Pick a rectangle on the earth in WGS84 coordinates; `geostl` fetches the height data covering
it, rectifies it to a metric grid, scales it to your print bed, and writes a watertight STL —
either as a single section or as a grid of seam-matched tiles that fit together.

> **Status: working core, pre-1.0.** The full pipeline is implemented and verified end to end —
> fetch → reproject (auto-UTM) → scale → watertight mesh → STL, for both single sections and
> seam-matched grids. Data sources today: the **Austria (BEV) API**, **local GeoTIFF**, and
> **remote COG**. Still to come: a global source (OpenTopography), a CLI, and tile connectors.
> See the [design docs](docs/design.rst) for the architecture and roadmap.

## Install (development)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\Activate.ps1
# POSIX:    source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.11+ (developed on 3.14). Optional extras: `validate` (trimesh watertight
checks), `docs` (Sphinx); `viz` and `fallback` back planned preview / geodesic features.

## Quickstart

Straight from the Austrian DGM API — no data files, just network:

```python
from geostl import Region, GeoPoint
from geostl.sources import AustriaDGMSource

region = Region.from_corners(GeoPoint(47.691855, 14.039583),
                             GeoPoint(47.723852, 14.089708))
source = AustriaDGMSource()  # 1 m ALS terrain model from data.bev.gv.at

# Single section -> one watertight STL
section = region.to_section(source)            # native detail (fetch_resolution_m=… caps big reads)
section.scale(bed_size_mm=200, z_exaggeration=1.0, base_thickness_mm=3)
section.export_stl("terrain.stl", resolution_mm=0.4)   # 0.4 mm printed pixels

# ...or split a region into a 3x3 grid of seam-matched, tileable pieces
grid = region.to_grid(source, nx=3, ny=3)
grid.scale(bed_size_mm=200, z_exaggeration=1.0, base_thickness_mm=3)
grid.export_stl("out/", prefix="tile", resolution_mm=0.4)   # out/tile_r0_c0.stl ...
```

Have a local DEM instead? Swap the source — everything downstream is identical:

```python
from geostl.sources import LocalGeoTiffSource
source = LocalGeoTiffSource("assets/DGM_R25.tif")
```

## Data sources

Every source implements one method, `fetch(bbox) -> ElevationTile`; the rest of the pipeline is
source-agnostic, so adding a country/service means writing just one adapter.

| Source | Status | Notes |
|---|---|---|
| `AustriaDGMSource` | ✅ | BEV 1 m ALS DTM/DSM via the INSPIRE ATOM service; no local file (CC-BY-4.0). |
| `LocalGeoTiffSource` | ✅ | Any georeferenced GeoTIFF, any CRS; windowed reads handle multi-GB files. |
| `RemoteCOGSource` | ✅ | One or many remote Cloud-Optimized GeoTIFFs via `/vsicurl` (overview-decimated). |
| `OpenTopographySource` | ⬜ | Global SRTM / Copernicus DEMs — planned. |

## Examples

- [`examples/austria_dgm_api.py`](examples/austria_dgm_api.py) — a watertight STL **straight
  from the BEV Austria DGM API** (no local file; needs network).
- [`examples/austria_dgm.py`](examples/austria_dgm.py) — same region from a local
  `assets/DGM_R25.tif` GeoTIFF.
- [`examples/austria_dgm_grid.py`](examples/austria_dgm_grid.py) — tile a larger region into a
  3×3 grid of seam-matched STL pieces.

## Architecture (one line)

`Region` (WGS84) → `ElevationSource.fetch` → `ElevationTile` (metric grid) → rectify → scale →
`Mesher` → watertight STL. Supporting a new country/API means writing **one** new
`ElevationSource` adapter; nothing downstream changes. Full detail in the [design docs](docs/design.rst).

## Tests & docs

```bash
pytest                                            # runs offline (HTTP mocked for the API logic)
python -m sphinx -b html docs docs/_build/html    # build the API docs (needs the `docs` extra)
```

## License

MIT — see [LICENSE](LICENSE).
