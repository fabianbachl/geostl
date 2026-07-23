"""Example: tile a LARGER Austrian DGM region into printable STL pieces.

Selects a region several times larger than ``examples/austria_dgm.py`` (still
centered on the Pyhrn / Ennstal area) and splits it into an ``nx x ny`` grid of
seam-matched tiles. The whole region is fetched once and sliced with shared edge
pixels, so the tiles butt together when printed and assembled.

Requires the elevation raster at ``assets/DGM_R25.tif`` (git-ignored): a 25 m
Austrian *Digitales Geländemodell* tile in EPSG:31287. Found at:
https://doi.org/10.48677/6a853c17-8960-44a4-81fb-18e0549a1c80

Run from the repo root::

    python examples/austria_dgm_grid.py
"""
from pathlib import Path

import numpy as np

from geostl import GeoPoint, Region
from geostl.sources import LocalGeoTiffSource

# ~0.30 deg lon x 0.20 deg lat (~22 km square) — about 6x wider than the
# single-section example in each direction.
CORNER_A = GeoPoint(lat=47.60, lon=13.95)
CORNER_B = GeoPoint(lat=47.80, lon=14.25)

NX, NY = 3, 3
DGM_PATH = Path("assets/DGM_R25.tif")
OUTPUT_DIR = Path("examples/grid_out")


def main() -> None:
    if not DGM_PATH.exists():
        raise SystemExit(
            f"Elevation raster not found at {DGM_PATH}. Place a 25 m Austrian DGM "
            "GeoTIFF there (see the README) and rerun."
        )

    region = Region.from_corners(CORNER_A, CORNER_B)
    source = LocalGeoTiffSource(DGM_PATH)

    # One native read for the whole region, split into NX*NY seam-matched tiles.
    # (For a fine/remote source over a big area, pass fetch_resolution_m to cap
    # the read; the 25 m local DGM is cheap to read whole.)
    grid = region.to_grid(
        source, nx=NX, ny=NY,
        bed_size_mm=240.0,      # each tile fits a 240 mm print bed
        z_exaggeration=1.0,     # true vertical scale
        base_thickness_mm=3.0,
    )

    fh, fw = grid.full_tile.heights.shape
    print(f"Full region {fw}x{fh} px in {grid.full_tile.crs}; split into {NX}x{NY} tiles")
    for s in grid.sections:
        h, w = s.tile.heights.shape
        nan = 100.0 * float(np.mean(~np.isfinite(s.tile.heights)))
        print(f"  tile r{s.row} c{s.col}: {w}x{h} px, nodata={nan:.1f}%")

    # resolution_mm sets the printed pixel size; the region is downsampled once and
    # re-split so the tiles' seams stay identical.
    paths = grid.export_stl(OUTPUT_DIR, prefix="dgm", resolution_mm=1.0)
    total_mb = sum(p.stat().st_size for p in paths) / 1e6
    print(f"Wrote {len(paths)} STL tiles to {OUTPUT_DIR}/ ({total_mb:.1f} MB total)")


if __name__ == "__main__":
    main()
