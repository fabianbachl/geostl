"""Region + Grid: from a WGS84 rectangle to one or many mesh-ready Sections.

Three stages, each owning one concern:

* **fetch** (``Region.to_section`` / ``to_grid``) — how much source to read
  (``fetch_resolution_m``; native by default),
* **scale** (``Section.scale`` / ``Grid.scale``) — physical size only, in mm per
  real metre (resolution-independent),
* **mesh** (``export_stl`` / ``to_mesh``) — the printed model resolution
  (``resolution_mm``; full detail by default).
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from geostl.geometry import BoundingBox, GeoPoint

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.mesh import TriangleMesh
    from geostl.sources.base import ElevationSource


def _split_tile(tile: "ElevationTile", nx: int, ny: int) -> List["Section"]:
    """Split a tile into ``nx*ny`` Sections that share boundary rows/columns.

    Neighbouring tiles reuse the cut row/column as a 1-pixel overlap, so their
    seams are pixel-identical and the printed pieces butt together.
    """
    if nx < 1 or ny < 1:
        raise ValueError("nx and ny must both be >= 1")

    h, w = tile.heights.shape
    col_edges = np.linspace(0, w - 1, nx + 1).round().astype(int)
    row_edges = np.linspace(0, h - 1, ny + 1).round().astype(int)
    if np.unique(col_edges).size != nx + 1 or np.unique(row_edges).size != ny + 1:
        raise ValueError(
            f"region ({w}x{h} px) is too small to split into {nx}x{ny} tiles; "
            "use fewer tiles or a finer fetch (smaller fetch_resolution_m)"
        )

    sections: List[Section] = []
    for r in range(ny):
        for c in range(nx):
            sub = tile.subset(
                int(row_edges[r]), int(row_edges[r + 1]) + 1,
                int(col_edges[c]), int(col_edges[c + 1]) + 1,
            )
            sections.append(Section(tile=sub, row=r, col=c))
    return sections


class Region:
    """A geographic rectangle (WGS84) the user wants to model."""

    def __init__(self, bbox: BoundingBox):
        self.bbox = bbox

    @classmethod
    def from_corners(cls, a: GeoPoint, b: GeoPoint) -> "Region":
        return cls(BoundingBox.from_corners(a, b))

    def to_section(
        self,
        source: "ElevationSource",
        *,
        fetch_resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "Section":
        """Fetch + rectify this whole region as a single :class:`Section`.

        The source is read at native resolution by default; ``fetch_resolution_m``
        reads a coarser overview (metres/pixel) for large areas. The printed model
        resolution is chosen later, at :meth:`Section.export_stl` / ``to_mesh``.
        """
        tile = source.fetch(
            self.bbox, fetch_resolution_m=fetch_resolution_m, target_crs=target_crs
        )
        return Section(tile=tile)

    def to_grid(
        self,
        source: "ElevationSource",
        *,
        nx: int,
        ny: int,
        fetch_resolution_m: Optional[float] = None,
        target_crs: Optional[str] = None,
    ) -> "Grid":
        """Fetch the whole region in ONE read, then split into ``nx*ny`` tiles.

        The region is fetched once (native resolution unless ``fetch_resolution_m``
        is given) and sliced so adjacent tiles share their boundary row/column, so
        the printed tiles butt together. Call :meth:`Grid.scale` for the shared
        scale, then :meth:`Grid.export_stl` (with an optional ``resolution_mm``).
        """
        tile = source.fetch(
            self.bbox, fetch_resolution_m=fetch_resolution_m, target_crs=target_crs
        )
        sections = _split_tile(tile, nx, ny)
        return Grid(sections=sections, nx=nx, ny=ny, full_tile=tile)


@dataclass
class Section:
    """A single rectified region, ready to scale and mesh."""

    tile: "ElevationTile"
    row: int = 0
    col: int = 0
    # Physical scale (resolution-independent); None until .scale() resolves it.
    scale_xy_mm_per_m: Optional[float] = None
    z_scale_mm_per_m: Optional[float] = None
    base_thickness_mm: Optional[float] = None
    # Elevation (m) that maps to the base level. None -> this tile's own minimum;
    # Grid.scale sets it to the whole-region minimum so tiles align in z.
    z_ref_m: Optional[float] = None

    def scale(
        self,
        *,
        bed_size_mm: Optional[float] = None,
        scale_xy: Optional[float] = None,
        z_exaggeration: float = 1.0,
        base_thickness_mm: float = 3.0,
    ) -> "Section":
        """Resolve the physical scale (mm per real metre, z, base). Chainable.

        Resolution-independent: it fixes how real-world metres map to millimetres,
        not how dense the mesh is (that is chosen at meshing via ``resolution_mm``).
        """
        from geostl.scaling import resolve_scale

        dx_m, dy_m = self.tile.pixel_size_m()
        h, w = self.tile.heights.shape
        spec = resolve_scale(
            (w - 1) * dx_m,
            (h - 1) * dy_m,
            bed_size_mm=bed_size_mm,
            scale_xy=scale_xy,
            z_exaggeration=z_exaggeration,
            base_thickness_mm=base_thickness_mm,
        )
        self.scale_xy_mm_per_m = spec.scale_xy_mm_per_m
        self.z_scale_mm_per_m = spec.z_scale_mm_per_m
        self.base_thickness_mm = spec.base_thickness_mm
        return self

    def to_mesh(self, resolution_mm: Optional[float] = None) -> "TriangleMesh":
        """Build the watertight mesh (top surface + walls + base).

        Receives the tile's full-resolution data and, when ``resolution_mm`` is
        given, downsamples it to that printed pixel size (metres/pixel =
        ``resolution_mm / scale``). If ``resolution_mm`` is finer than the source
        supports, a warning is issued and the native resolution is used. Heights
        are measured from ``z_ref_m`` (default: this tile's lowest finite value),
        which maps to ``base_thickness_mm`` above a base plane at z=0.
        """
        from geostl.mesh import Mesher
        from geostl.rectify import resample_heights

        if self.scale_xy_mm_per_m is None or self.z_scale_mm_per_m is None:
            raise RuntimeError("call .scale(...) before meshing this Section")

        heights = self.tile.heights
        transform, crs = self.tile.transform, self.tile.crs
        dx_m, dy_m = self.tile.pixel_size_m()

        if resolution_mm is not None:
            target_res_m = resolution_mm / self.scale_xy_mm_per_m
            native_res_m = max(dx_m, dy_m)
            if target_res_m > native_res_m * 1.001:
                heights, transform = resample_heights(heights, transform, crs, target_res_m)
                dx_m, dy_m = abs(transform.a), abs(transform.e)
            elif target_res_m < native_res_m * 0.999:
                warnings.warn(
                    f"resolution_mm={resolution_mm} is finer than the source supports "
                    f"(~{native_res_m * self.scale_xy_mm_per_m:.3g} mm); using native.",
                    RuntimeWarning,
                    stacklevel=2,
                )

        h = np.asarray(heights, dtype="float64")
        finite = np.isfinite(h)
        if not finite.any():
            raise ValueError("tile has no finite elevation data to mesh")
        min_h = float(h[finite].min())
        h = np.where(finite, h, min_h)

        ref = self.z_ref_m if self.z_ref_m is not None else min_h
        dx_mm = dx_m * self.scale_xy_mm_per_m
        dy_mm = dy_m * self.scale_xy_mm_per_m
        z_top = (h - ref) * self.z_scale_mm_per_m + self.base_thickness_mm
        return Mesher().build(z_top, dx_mm, dy_mm, base_z_mm=0.0)

    def export_stl(self, path, resolution_mm: Optional[float] = None) -> None:
        """Build the mesh (optionally downsampled to ``resolution_mm``) and write STL."""
        self.to_mesh(resolution_mm).export_stl(path)


@dataclass
class Grid:
    """An ``nx*ny`` set of seam-matched Sections sharing a single scale."""

    sections: List[Section] = field(default_factory=list)
    nx: int = 0
    ny: int = 0
    full_tile: Optional["ElevationTile"] = None
    # Shared physical scale (resolution-independent); None until .scale().
    scale_xy_mm_per_m: Optional[float] = None
    z_scale_mm_per_m: Optional[float] = None
    base_thickness_mm: Optional[float] = None
    z_ref_m: Optional[float] = None

    def scale(
        self,
        *,
        bed_size_mm: Optional[float] = None,
        scale_xy: Optional[float] = None,
        z_exaggeration: float = 1.0,
        base_thickness_mm: float = 3.0,
    ) -> "Grid":
        """Resolve one shared physical scale + z-reference for every tile.

        ``bed_size_mm`` is the **print-bed size**: the scale is chosen so the
        largest tile's longer side maps to ``bed_size_mm``, so every tile fits the
        bed. The scale is resolution-independent; the printed model resolution is
        chosen at :meth:`export_stl` via ``resolution_mm``.
        """
        from geostl.scaling import resolve_scale

        if self.full_tile is None:
            raise RuntimeError("Grid has no full_tile; build it via Region.to_grid")
        if not self.sections:
            raise RuntimeError("Grid has no sections to scale")

        dx_m, dy_m = self.full_tile.pixel_size_m()
        # Size by the largest tile so every tile fits the print bed (ground extents
        # are resolution-independent).
        fit_x = max((s.tile.heights.shape[1] - 1) * dx_m for s in self.sections)
        fit_y = max((s.tile.heights.shape[0] - 1) * dy_m for s in self.sections)
        spec = resolve_scale(
            fit_x,
            fit_y,
            bed_size_mm=bed_size_mm,
            scale_xy=scale_xy,
            z_exaggeration=z_exaggeration,
            base_thickness_mm=base_thickness_mm,
        )
        finite = np.isfinite(self.full_tile.heights)
        if not finite.any():
            raise ValueError("region has no finite elevation data")

        self.scale_xy_mm_per_m = spec.scale_xy_mm_per_m
        self.z_scale_mm_per_m = spec.z_scale_mm_per_m
        self.base_thickness_mm = spec.base_thickness_mm
        self.z_ref_m = float(self.full_tile.heights[finite].min())
        for s in self.sections:
            self._apply_scale(s)
        return self

    def _apply_scale(self, section: "Section") -> None:
        section.scale_xy_mm_per_m = self.scale_xy_mm_per_m
        section.z_scale_mm_per_m = self.z_scale_mm_per_m
        section.base_thickness_mm = self.base_thickness_mm
        section.z_ref_m = self.z_ref_m

    def _sections_for(self, resolution_mm: Optional[float]) -> List["Section"]:
        """Sections to mesh: the native tiles, or — for a coarser ``resolution_mm``
        — the whole region downsampled once and re-split so seams stay identical."""
        if resolution_mm is None:
            return self.sections

        from geostl.elevation import ElevationTile
        from geostl.rectify import resample_heights

        target_res_m = resolution_mm / self.scale_xy_mm_per_m
        fdx, fdy = self.full_tile.pixel_size_m()
        native_res_m = max(fdx, fdy)
        if target_res_m <= native_res_m * 1.001:
            if target_res_m < native_res_m * 0.999:
                warnings.warn(
                    f"resolution_mm={resolution_mm} is finer than the source supports "
                    f"(~{native_res_m * self.scale_xy_mm_per_m:.3g} mm); using native.",
                    RuntimeWarning,
                    stacklevel=3,
                )
            return self.sections

        heights, transform = resample_heights(
            self.full_tile.heights, self.full_tile.transform,
            self.full_tile.crs, target_res_m,
        )
        coarse = ElevationTile(
            heights=heights, transform=transform,
            crs=self.full_tile.crs, nodata=float("nan"),
        )
        sections = _split_tile(coarse, self.nx, self.ny)
        for s in sections:
            self._apply_scale(s)
        return sections

    def export_stl(
        self, directory, *, prefix: str = "tile", resolution_mm: Optional[float] = None
    ) -> List[Path]:
        """Write one STL per tile: ``<directory>/<prefix>_r<row>_c<col>.stl``.

        With ``resolution_mm``, the whole region is downsampled once and re-split so
        the tiles' seams stay pixel-identical. Returns the list of written paths.
        """
        if self.scale_xy_mm_per_m is None:
            raise RuntimeError("call .scale(...) on the Grid before exporting")

        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        paths: List[Path] = []
        for s in self._sections_for(resolution_mm):
            p = directory / f"{prefix}_r{s.row}_c{s.col}.stl"
            s.export_stl(p)  # sections are already at the target resolution
            paths.append(p)
        return paths
