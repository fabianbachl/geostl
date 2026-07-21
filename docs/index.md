# geostl

Turn public **elevation data (GeoTIFF/DEM)** into **3D-printable terrain STL**.

`geostl` lets you pick a rectangle on the earth in WGS84 coordinates, fetch the elevation
data covering it, rectify it to a metric grid, scale it to a print bed, and produce a
watertight STL — as a single section or a grid of seam-matched tiles that fit together.

```{note}
Working core, pre-1.0. The full pipeline — fetch → reproject → scale → watertight mesh →
STL, for single sections and seam-matched grids — is implemented and verified. Data sources
today: the Austria (BEV) API, local GeoTIFF, and remote COG; a global source
(OpenTopography), a CLI, and tile connectors are still to come. See {doc}`design` for the
design principles and roadmap.
```

## How it fits together

`Region` (WGS84) → `ElevationSource.fetch` → `ElevationTile` (metric grid) → rectify →
scale → `Mesher` → watertight STL. Supporting a new country/API means writing **one** new
`ElevationSource` adapter; nothing downstream changes.

```{toctree}
:maxdepth: 2
:caption: Contents

quickstart
design
api
```

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
