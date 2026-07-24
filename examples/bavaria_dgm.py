"""Example: build an STL from Bavaria's DGM1 open data (no local file).

Fetches the 1 m LiDAR terrain model around the Zugspitze (Germany's highest peak,
on the Austrian border) straight from the Bavarian surveying office's open-data
tile server — 1 km GeoTIFF tiles read via GDAL ``/vsicurl`` — and writes a single
watertight STL. Requires network access; no local data file is needed.

Run from the repo root::

    python examples/bavaria_dgm.py
"""
from pathlib import Path

from geostl import GeoPoint, Region
from geostl.sources import BavariaDGMSource

# A box around the Zugspitze massif (Wetterstein range).
CORNER_A = GeoPoint(lat=47.400, lon=10.960)
CORNER_B = GeoPoint(lat=47.430, lon=11.010)
OUTPUT_PATH = Path("examples/zugspitze_bayern.stl")


def main() -> None:
    region = Region.from_corners(CORNER_A, CORNER_B)
    source = BavariaDGMSource()  # 1 m DGM1 from geodaten.bayern.de (LDBV)

    # to_section fetches the covering tiles, rectifies, and scales in one step.
    # fetch_resolution_m caps the read at 2 m/px — plenty for a 200 mm print and
    # much lighter than the native 1 m over the whole massif.
    section = region.to_section(
        source,
        bed_size_mm=200.0,
        z_exaggeration=1.0,
        base_thickness_mm=3.0,
        fetch_resolution_m=2.0,
    )

    h, w = section.tile.heights.shape
    print(f"Fetched {w}x{h} px in {section.tile.crs} from the Bavaria DGM1 tiles")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    section.export_stl(OUTPUT_PATH, resolution_mm=0.5)
    print(f"Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
