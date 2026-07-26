"""Example: build an STL anywhere on Earth via the OpenTopography global fallback.

Fetches a ~30 m global DEM (Copernicus GLO-30 by default) for any WGS84 rectangle
straight from the OpenTopography REST API and writes a watertight STL. This is the
worldwide fallback for regions without a national high-resolution source.

Needs a free OpenTopography API key — register at https://portal.opentopography.org/
and set it in the environment before running::

    export OPENTOPOGRAPHY_API_KEY=your_key_here      # (Windows: setx / $env:)
    python examples/opentopography_global.py
"""
from pathlib import Path

from geostl import GeoPoint, Region
from geostl.sources import OpenTopographySource

# Mont Blanc / Monte Bianco — outside every national source implemented so far.
CORNER_A = GeoPoint(lat=45.79, lon=6.84)
CORNER_B = GeoPoint(lat=45.87, lon=6.95)
OUTPUT_PATH = Path("examples/mont_blanc_global.stl")


def main() -> None:
    region = Region.from_corners(CORNER_A, CORNER_B)
    # API key read from $OPENTOPOGRAPHY_API_KEY; COP30 = Copernicus GLO-30 (~30 m).
    source = OpenTopographySource(dem="COP30")

    section = region.to_section(
        source,
        bed_size_mm=200.0,
        z_exaggeration=1.5,  # gentle exaggeration reads well at 30 m
        base_thickness_mm=3.0,
    )

    h, w = section.tile.heights.shape
    print(f"Fetched {w}x{h} px in {section.tile.crs} from OpenTopography ({source.dem})")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    section.export_stl(OUTPUT_PATH, resolution_mm=0.5)
    print(f"Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
