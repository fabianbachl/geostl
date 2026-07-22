"""Example: build a 3D-printable STL from the Austrian DGM.

Selects the same region the prototype ``scratchpad.ipynb`` used — a section of
the Pyhrn / Ennstal area of the Austrian Alps — and turns it into a single
watertight STL.

Requires the elevation raster at ``assets/DGM_R25.tif`` (git-ignored): a 25 m
Austrian *Digitales Geländemodell* tile in EPSG:31287. 
Found at:
https://doi.org/10.48677/6a853c17-8960-44a4-81fb-18e0549a1c80

Run from the repo root::
    python examples/austria_dgm.py
"""
from pathlib import Path

from geostl import GeoPoint, Region
from geostl.sources import LocalGeoTiffSource

# Same bounding box as scratchpad.ipynb, whose corners were given as (lon, lat):
#   ((14.039583, 47.691855), (14.089708, 47.723852))
CORNER_A = GeoPoint(lat=47.691855, lon=14.039583)
CORNER_B = GeoPoint(lat=47.723852, lon=14.089708)

DGM_PATH = Path("assets/DGM_R25.tif")
OUTPUT_PATH = Path("examples/pyhrn_ennstal.stl")


def main() -> None:
    if not DGM_PATH.exists():
        raise SystemExit(
            f"Elevation raster not found at {DGM_PATH}. Place a 25 m Austrian DGM "
            "GeoTIFF there (see the README) and rerun."
        )

    region = Region.from_corners(CORNER_A, CORNER_B)
    source = LocalGeoTiffSource(DGM_PATH)

    # Fetch + rectify to a metric grid, then scale for the print bed.
    section = region.to_section(source, fetch_resolution_m=3).scale(
        bed_size_mm=200.0,      # longest horizontal side -> 200 mm
        z_exaggeration=1.0,     # play up the relief
        base_thickness_mm=3.0,  # solid base below the lowest point
    )

    h, w = section.tile.heights.shape
    print(f"Fetched {w}x{h} px in {section.tile.crs} at {section.tile.pixel_size_m()} m/px")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    section.export_stl(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
