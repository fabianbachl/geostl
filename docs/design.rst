======
Design
======

``geostl`` turns public elevation data (GeoTIFF / DEM) into 3D-printable terrain
models (STL). You give it a rectangle on the earth in WGS84 corner coordinates; it
fetches the height data covering that rectangle, rectifies it to a metric grid,
scales it to a print bed, and writes a watertight STL — either as a single section
or as a grid of seam-matched tiles that fit together when printed and assembled.

It deliberately targets rectangular WGS84 regions and watertight solids; slicing /
G-code are out of scope. This page describes the principles the library is built on; 
for the concrete API see :doc:`api`.


The pipeline
============

The pipeline is a straight flow from WGS84 corners to a printable STL file. 

    WGS84 corners  ->  Region
                          |
        to_section / to_grid   [fetch + rectify + scale, in one step]
        (bed_size_mm / scale_xy; fetch_resolution_m caps the read)
                          v
    scaled Section   (or a Grid of nx x ny seam-matched Sections)
                          |
                          v
    export_stl / to_mesh(resolution_mm)  ->  Mesher (top + walls + base)  ->  STL

A :class:`~geostl.geometry.GeoPoint` and :class:`~geostl.geometry.BoundingBox`
describe *where*; a :class:`~geostl.tiling.Region` becomes one
:class:`~geostl.tiling.Section` (:meth:`~geostl.tiling.Region.to_section`) or a
:class:`~geostl.tiling.Grid` of them (:meth:`~geostl.tiling.Region.to_grid`); an
:class:`~geostl.sources.base.ElevationSource` supplies the data as an
:class:`~geostl.elevation.ElevationTile`; and the :class:`~geostl.mesh.Mesher`
produces the printable solid.


Design principles
=================

A pluggable source abstraction
------------------------------

Different countries publish elevation data through different services, so data
access is hidden behind a single abstraction. An
:class:`~geostl.sources.base.ElevationSource` implements exactly one method::

    def fetch(self, bbox, *, fetch_resolution_m=None, target_crs=None) -> ElevationTile

Everything downstream — rectification, scaling, meshing, export — is
source-agnostic. **Supporting a new country or service means writing one adapter
and nothing else.** An adapter may do whatever it must internally (resolve which
tiles cover the bbox, download or stream them, mosaic, reproject); all of that
complexity stays behind ``fetch``.


One metric hand-off: the ElevationTile
--------------------------------------

:class:`~geostl.elevation.ElevationTile` is the single boundary between *fetching*
and *geometry*. It carries the heights (in metres) already on a **regular metric
grid**, plus the affine transform, CRS, and nodata value. Because the tile is
already metric and regular, everything after it is pure geometry with no
geospatial knowledge — the mesher never needs to know which country the data came
from, or in what projection it arrived.


Correct horizontal scale, by construction
------------------------------------------

A degree of longitude is not a fixed number of metres — it shrinks toward the
poles — so a heightfield laid out in raw lat/lon would be horizontally distorted.
``geostl`` therefore always reprojects into a **projected metric CRS** before
meshing. The default is the UTM zone of the bbox centroid
(:func:`~geostl.geometry.utm_epsg_for`), which callers can override (e.g. to a
national grid, or an equal-area CRS for very wide regions).

Reprojection is **output-driven**: the target grid is resolved first, and each
source is read through the window that covers *that output* (not the raw input
bbox). This one decision pays off three ways:

- Only the needed window is read, decimated to the output resolution — so
  Cloud-Optimized GeoTIFF overviews are used and multi-gigabyte or remote rasters
  are handled with small transfers.
- The read region provably covers the output rectangle even when the source and
  output grids are rotated relative to each other, which avoids NaN wedges at the
  corners of reprojected tiles.
- The same output grid can be shared across every tile of a grid (see below).


One shared ingestion path
-------------------------

Reading a window, reprojecting it, and mosaicking several rasters is written once
and reused by every file/URL-based source.
:class:`~geostl.sources.local.LocalGeoTiffSource` (a local file),
:class:`~geostl.sources.cog.RemoteCOGSource` (one or many remote COGs via
``/vsicurl``), the national tile sources
(:class:`~geostl.sources.austria.AustriaDGMSource` and
:class:`~geostl.sources.germany.BavariaDGMSource`, which discover the covering
tiles and then delegate to ``RemoteCOGSource``), and even
:class:`~geostl.sources.wcs.WCSSource` (which hands the server-cropped GeoTIFF to
the same code through GDAL's in-memory filesystem) all funnel through the same
machinery. There is no second copy of the read / reproject / mosaic logic to drift
out of sync.


Seam-matched tiling
-------------------

For a grid, the **whole region is fetched once** and the resulting array is sliced
into ``nx x ny`` tiles that **share their boundary row/column** with each
neighbour. Because a shared edge is literally the same samples, adjacent printed
tiles butt together with identical heights. Fetching each tile independently would
resample separately and mismatch the seams, so the library deliberately does not
do that. The tiles also share **one scale and one vertical datum** (the
whole-region minimum), which keeps their surfaces continuous and their bases
coplanar when assembled.


Watertight, printable solids
----------------------------

A heightfield alone is not printable. :class:`~geostl.mesh.Mesher` closes it into a
solid: the top surface over the grid, four vertical side walls, and a base plane,
all wound so their normals point outward. Construction is fully vectorized (no
per-triangle Python loops), the base perimeter shares the wall vertices so the mesh
is manifold, and the result is written with ``numpy-stl``. ``trimesh`` (optional)
asserts watertightness in the tests.


Scaling to the print bed
------------------------

Scaling happens **as part of** the Region → Section conversion: a
:class:`~geostl.tiling.Section` is always a scaled model, never a bare rectified
grid. :meth:`~geostl.tiling.Region.to_section` / :meth:`~geostl.tiling.Region.to_grid`
take a target print-bed size (or an explicit millimetres-per-metre), a vertical
exaggeration factor, and a base thickness; :meth:`~geostl.tiling.Section.rescale` /
:meth:`~geostl.tiling.Grid.rescale` re-apply a different scale without re-fetching.
For a **grid**, ``bed_size_mm`` is the *print-bed* size: one shared scale is chosen
so the largest tile fits the bed, so every piece is printable while the assembled
pieces still align.


Resolution: read native, print in millimetres
----------------------------------------------

Fetching, scaling, and meshing stay separate concerns, so resolution has two meanings
within the pipeline:

- **Fetch** decides *how much source to read* — native (full) detail by default,
  or a coarser ``fetch_resolution_m`` (metres/pixel) for very large areas or highly
  detailed source material. It is reccommended to fetch more than the print resolution,
  so the mesher can downsample.
- **Mesh** decides the *printed* resolution: :meth:`~geostl.tiling.Section.export_stl`
  / ``to_mesh`` take a ``resolution_mm`` (one output pixel's size on the print). The
  mesher receives full-resolution data and downsamples to it; omit it for full
  detail, and if it is finer than the source supports a warning is issued and the
  available resolution is used.

For a grid this stays seam-safe: because ``scale`` fixed only resolution-independent
quantities, :meth:`~geostl.tiling.Grid.export_stl` downsamples the whole region
**once** and re-splits, so the tiles' shared edges stay pixel-identical.


Testable without the network
----------------------------

The default test suite performs no network or file I/O: a synthetic source yields
deterministic terrain as an :class:`~geostl.elevation.ElevationTile`, and the
API-discovery logic is exercised against mocked HTTP. Real endpoints are reserved
for opt-in smoke tests.


Portability and lazy dependencies
---------------------------------

Raster IO and warping use `rasterio <https://rasterio.readthedocs.io/>`_, which
ships pip-installable wheels with a bundled GDAL — important on Windows, where a
raw GDAL / ``osgeo`` install is painful. Heavy dependencies are imported lazily
inside the methods that need them, so importing ``geostl`` and its source registry
stays cheap, and optional features live behind extras (``validate`` for trimesh
checks, ``viz`` for previews, ``docs`` for Sphinx).


Data sources
============

Every source implements :meth:`~geostl.sources.base.ElevationSource.fetch`; adding
one is a self-contained adapter.

.. list-table::
   :header-rows: 1
   :widths: 26 16 58

   * - Source
     - Status
     - Notes
   * - :class:`~geostl.sources.austria.AustriaDGMSource`
     - Available
     - Austria's national 1 m ALS DTM/DSM (BEV), discovered from its INSPIRE ATOM
       service and read as EPSG:3035 COG tiles via ``/vsicurl`` — no local file
       needed (CC-BY-4.0).
   * - :class:`~geostl.sources.germany.BavariaDGMSource`
     - Available
     - Bavaria's national 1 m LiDAR DGM1 (LDBV), read as 1 km EPSG:25832 GeoTIFF
       tiles whose URLs are derived from the bbox; covers the Bavarian Alps —
       no local file needed.
   * - :class:`~geostl.sources.italy.SouthTyrolDGMSource`
     - Available
     - South Tyrol's LiDAR DTM (Province of Bolzano), fetched via its WCS and read
       through the shared path; 2.5 m province-wide (0.5 m where flown), covering
       the Dolomites and Ortler (CC0).
   * - :class:`~geostl.sources.wcs.WCSSource`
     - Available
     - Generic OGC Web Coverage Service (WCS 2.0.1) client: server-side crop to a
       GeoTIFF, read through the shared ingestion path.
   * - :class:`~geostl.sources.local.LocalGeoTiffSource`
     - Available
     - Any georeferenced GeoTIFF, any CRS; windowed reads handle multi-gigabyte
       files.
   * - :class:`~geostl.sources.cog.RemoteCOGSource`
     - Available
     - One or many remote Cloud-Optimized GeoTIFFs via ``/vsicurl``,
       overview-decimated; mosaicked when several are given.
   * - :class:`~geostl.sources.opentopography.OpenTopographySource`
     - *Upcoming*
     - Global SRTM / Copernicus DEMs via the OpenTopography API.


Upcoming
========

.. note::

   The following are planned and **not yet implemented**.

- **Global coverage — OpenTopographySource.** Fetch SRTM / Copernicus DEMs from the
  OpenTopography API so regions outside Austria work out of the box.
- **Previews.** ``matplotlib`` 2D heatmap and 3D solid previews behind the ``viz``
  extra.
- **Command-line interface.** A ``geostl`` command wrapping the section / grid
  workflow.
- **Tile connectors.** Optional *pin holes* carved into tile edges or bases so
  printed grid pieces can be pinned together or mounted to a backplate with threaded
  inserts. The wall/base meshing is kept parameterized so this can be added without 
  a redesign.
