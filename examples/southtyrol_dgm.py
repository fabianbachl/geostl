"""Example: build an STL from South Tyrol's LiDAR DTM (no local file).

Fetches the terrain model of the Schlern / Sciliar massif and the Seiser Alm
(Alpe di Siusi) in the Dolomites straight from the Autonomous Province of
Bolzano's Web Coverage Service — the server crops the coverage and returns a
GeoTIFF — and writes a single watertight STL. Requires network access; no local
data file is needed.

Run from the repo root::

    python examples/southtyrol_dgm.py
"""
from pathlib import Path

from geostl import GeoPoint, Region
from geostl.sources import SouthTyrolDGMSource

# A box over the Schlern / Sciliar and the Seiser Alm.
CORNER_A = GeoPoint(lat=46.505, lon=11.555)
CORNER_B = GeoPoint(lat=46.555, lon=11.625)
OUTPUT_PATH = Path("examples/schlern_suedtirol.stl")


def main() -> None:
    region = Region.from_corners(CORNER_A, CORNER_B)
    # 2.5 m LiDAR DTM (full province coverage) from data.civis.bz.it, via WCS.
    source = SouthTyrolDGMSource()

    section = region.to_section(
        source,
        bed_size_mm=200.0,
        z_exaggeration=1.0,
        base_thickness_mm=3.0,
    )

    h, w = section.tile.heights.shape
    print(f"Fetched {w}x{h} px in {section.tile.crs} from the South Tyrol WCS")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    section.export_stl(OUTPUT_PATH, resolution_mm=0.5)
    print(f"Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
