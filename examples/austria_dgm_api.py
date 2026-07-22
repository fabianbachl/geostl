"""Example: build an STL straight from the BEV Austria DGM API (no local file).

Fetches the 1 m ALS terrain model for the Pyhrn / Ennstal region directly from
BEV's INSPIRE ATOM download service — Cloud-Optimized GeoTIFF tiles read via
GDAL ``/vsicurl`` (overview-decimated, so no full download) — and writes a single
watertight STL. Requires network access; no local data file is needed.

Run from the repo root::

    python examples/austria_dgm_api.py
"""
from pathlib import Path

from geostl import GeoPoint, Region
from geostl.sources import AustriaDGMSource

# Same region as examples/austria_dgm.py, but fetched live from the API.
CORNER_A = GeoPoint(lat=47.691855, lon=14.039583)
CORNER_B = GeoPoint(lat=47.723852, lon=14.089708)
OUTPUT_PATH = Path("examples/pyhrn_ennstal_bev.stl")


def main() -> None:
    region = Region.from_corners(CORNER_A, CORNER_B)
    source = AustriaDGMSource()  # 1 m ALS DTM, latest series, from data.bev.gv.at

    # fetch_resolution_m caps the (remote) read; the printed pixel size is set at
    # export via resolution_mm.
    section = region.to_section(source).scale(
        bed_size_mm=200.0,
        z_exaggeration=1.0,
        base_thickness_mm=3.0,
    )

    h, w = section.tile.heights.shape
    print(f"Fetched {w}x{h} px in {section.tile.crs} from the BEV ATOM service")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    section.export_stl(OUTPUT_PATH, resolution_mm=0.5)
    print(f"Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
