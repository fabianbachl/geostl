# geostl

Turn public **elevation data (GeoTIFF/DEM)** into **3D-printable terrain models (STL)**.

Pick a rectangle on the earth in WGS84 coordinates; `geostl` fetches the height data covering
it, rectifies it to a metric grid, scales it to your print bed, and writes a watertight STL —
either as a single section or as a grid of seam-matched tiles that fit together.

> See the [design docs](docs/design.rst) for the architecture and roadmap.

## Install (development)

```bash
pip install -e ".[dev]"
```

Requires Python 3.11+ (tested and developed on 3.14). 

## Quickstart
Straight from the Austrian DGM API — no data files, just network:

```python
from geostl import Region, GeoPoint
from geostl.sources import AustriaDGMSource

region = Region.from_corners(GeoPoint(47.691855, 14.039583),
                             GeoPoint(47.723852, 14.089708))
source = AustriaDGMSource()  # 1 m ALS terrain model from data.bev.gv.at

# Single section -> one watertight STL
section = region.to_section(source, bed_size_mm=200, z_exaggeration=1.0,
                            base_thickness_mm=3, fetch_resolution_m=3)  # coarse read for speed
section.export_stl("terrain.stl", resolution_mm=0.4)   # 0.4 mm printed pixels

# ...or split a region into a 3x3 grid of seam-matched, tileable pieces
grid = region.to_grid(source, nx=3, ny=3, bed_size_mm=200, z_exaggeration=1.0,
                      base_thickness_mm=3)
grid.export_stl("out/", prefix="tile", resolution_mm=0.4)   # out/tile_r0_c0.stl ...

# ...both cases will produce tiles with their longest side beeing 200mm in length
```

## Data sources

Different sources can be used, everything downstream is identical:

```python
from geostl.sources import LocalGeoTiffSource
source = LocalGeoTiffSource("assets/DGM_R25.tif")
```

Every source implements one method, `fetch(bbox) -> ElevationTile`; the rest of the pipeline is
source-agnostic, so adding a country/service means writing just one adapter.

All implemented sources rely on GeoTIFF/COG data, but this is not a limitation. As long as the `ElevationSource`
outputs a correctly scaled `ElevationTile` object, the downstream can handle it.

### Currently implemented
| Source | Description |
|---|---|
| `AustriaDGMSource` | BEV 1 m ALS DTM/DSM via the INSPIRE ATOM service; no local file (CC-BY-4.0). |
| `LocalGeoTiffSource` | Any georeferenced GeoTIFF, any CRS; windowed reads handle multi-GB files. |
| `RemoteCOGSource` | One or many remote Cloud-Optimized GeoTIFFs via `/vsicurl` (overview-decimated). |

As long as the Source implements the `ElevationSource(ABC)` class, it can be used with the rest of the library

## Examples

- [`examples/austria_dgm_api.py`](examples/austria_dgm_api.py) — a watertight STL **straight
  from the BEV Austria DGM API** (no local file; needs network).
- [`examples/austria_dgm.py`](examples/austria_dgm.py) — same region from a local
  `assets/DGM_R25.tif` GeoTIFF.
- [`examples/austria_dgm_grid.py`](examples/austria_dgm_grid.py) — tile a larger region into a
  3×3 grid of seam-matched STL pieces. Again, based on the local DGM_R25 GeoTIFF file by the BMEV. 

## Tests & docs

```bash
pytest                                            # runs offline (HTTP mocked for the API logic)
python -m sphinx -b html docs docs/_build/html    # build the API docs (needs sphinx)
```

## Contribution

I am glad about any contributions to this project, I am a passionate mountaineer based in Austria, so getting the Austrian
high-resolution data up and running was my highest priority. Implementing a wider array of sources will greatly
elevate the usefulness of this library.

## License

MIT — see [LICENSE](LICENSE).
