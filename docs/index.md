# geostl

Turn public **elevation data (GeoTIFF/DEM)** into **3D-printable terrain STL**.

`geostl` lets you pick a rectangle on the earth in WGS84 coordinates, fetch the elevation
data covering it, rectify it to a metric grid, scale it to a print bed, and produce a
watertight STL — as a single section or a grid of seam-matched tiles that fit together.

```{note}
Pre-alpha. The public API surface and the pluggable data-source abstraction are in place;
the implementation is proceeding phase by phase. See the project's `DESIGN.md` for the
full architecture and roadmap.
```

## How it fits together

`Region` (WGS84) → `ElevationSource.fetch` → `ElevationTile` (metric grid) → rectify →
scale → `Mesher` → watertight STL. Supporting a new country/API means writing **one** new
`ElevationSource` adapter; nothing downstream changes.

```{toctree}
:maxdepth: 2
:caption: Contents

quickstart
api
```

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
