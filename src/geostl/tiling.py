"""Region + Grid: from a WGS84 rectangle to one or many mesh-ready Sections."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from geostl.geometry import BoundingBox, GeoPoint

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.mesh import TriangleMesh
    from geostl.sources.base import ElevationSource


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
        resolution_m: float = 25.0,
        target_crs: Optional[str] = None,
    ) -> "Section":
        """Fetch + rectify this whole region as a single :class:`Section`."""
        tile = source.fetch(self.bbox, resolution_m=resolution_m, target_crs=target_crs)
        return Section(tile=tile)

    def to_grid(
        self,
        source: "ElevationSource",
        *,
        nx: int,
        ny: int,
        resolution_m: float = 25.0,
        target_crs: Optional[str] = None,
    ) -> "Grid":
        """Fetch the whole region in ONE warp, then split into ``nx*ny`` tiles.

        The region is fetched once and the resulting array is sliced so that
        adjacent tiles **share their boundary row/column** (a 1-pixel overlap).
        Because the shared edge is literally the same samples, the printed tiles
        butt together with identical seam heights. Call :meth:`Grid.scale` to
        give every tile one shared scale and z-reference.
        """
        if nx < 1 or ny < 1:
            raise ValueError("nx and ny must both be >= 1")

        tile = source.fetch(self.bbox, resolution_m=resolution_m, target_crs=target_crs)
        h, w = tile.heights.shape

        # nx+1 / ny+1 cut indices; neighbouring tiles reuse the cut as a shared edge.
        col_edges = np.linspace(0, w - 1, nx + 1).round().astype(int)
        row_edges = np.linspace(0, h - 1, ny + 1).round().astype(int)
        if np.unique(col_edges).size != nx + 1 or np.unique(row_edges).size != ny + 1:
            raise ValueError(
                f"region ({w}x{h} px) is too small to split into {nx}x{ny} tiles; "
                "use a finer resolution_m or fewer tiles"
            )

        sections: List[Section] = []
        for r in range(ny):
            for c in range(nx):
                sub = tile.subset(
                    int(row_edges[r]), int(row_edges[r + 1]) + 1,
                    int(col_edges[c]), int(col_edges[c + 1]) + 1,
                )
                sections.append(Section(tile=sub, row=r, col=c))
        return Grid(sections=sections, nx=nx, ny=ny, full_tile=tile)


@dataclass
class Section:
    """A single rectified region, ready to scale and mesh."""

    tile: "ElevationTile"
    row: int = 0
    col: int = 0
    # Physical scaling; None until .scale() (or Grid.scale) resolves it.
    dx_mm: Optional[float] = None
    dy_mm: Optional[float] = None
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
        """Resolve physical dimensions (mm). Returns ``self`` for chaining."""
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
        self.dx_mm = dx_m * spec.scale_xy_mm_per_m
        self.dy_mm = dy_m * spec.scale_xy_mm_per_m
        self.z_scale_mm_per_m = spec.z_scale_mm_per_m
        self.base_thickness_mm = spec.base_thickness_mm
        return self

    def to_mesh(self) -> "TriangleMesh":
        """Build the watertight mesh (top surface + walls + base).

        Heights are measured from ``z_ref_m`` (defaults to this tile's lowest
        finite value); that reference maps to ``base_thickness_mm`` above a base
        plane at z=0. NaN holes are filled at the lowest level so the solid stays
        closed. Using a shared ``z_ref_m`` across grid tiles keeps their surfaces
        continuous at the seams.
        """
        from geostl.mesh import Mesher

        if self.dx_mm is None or self.z_scale_mm_per_m is None:
            raise RuntimeError("call .scale(...) before meshing this Section")

        h = np.asarray(self.tile.heights, dtype="float64")
        finite = np.isfinite(h)
        if not finite.any():
            raise ValueError("tile has no finite elevation data to mesh")
        min_h = float(h[finite].min())
        h = np.where(finite, h, min_h)

        ref = self.z_ref_m if self.z_ref_m is not None else min_h
        z_top = (h - ref) * self.z_scale_mm_per_m + self.base_thickness_mm
        return Mesher().build(z_top, self.dx_mm, self.dy_mm, base_z_mm=0.0)

    def export_stl(self, path) -> None:
        """Build the mesh and write it to ``path`` as an STL."""
        self.to_mesh().export_stl(path)


@dataclass
class Grid:
    """An ``nx*ny`` set of seam-matched Sections sharing a single scale."""

    sections: List[Section] = field(default_factory=list)
    nx: int = 0
    ny: int = 0
    full_tile: Optional["ElevationTile"] = None

    def scale(
        self,
        *,
        bed_size_mm: Optional[float] = None,
        scale_xy: Optional[float] = None,
        z_exaggeration: float = 1.0,
        base_thickness_mm: float = 3.0,
    ) -> "Grid":
        """Apply one shared scale + z-reference to every tile.

        ``bed_size_mm`` is the **print-bed size**: the scale is chosen so the
        largest tile's longer side maps to ``bed_size_mm``, so every tile fits the
        bed. That single scale — with a shared base thickness and z-reference (the
        whole-region minimum) — is applied to all tiles, which is what makes the
        printed pieces align at their seams. Pass ``scale_xy`` instead for an
        explicit mm-per-meter.
        """
        from geostl.scaling import resolve_scale

        if self.full_tile is None:
            raise RuntimeError("Grid has no full_tile; build it via Region.to_grid")
        if not self.sections:
            raise RuntimeError("Grid has no sections to scale")

        dx_m, dy_m = self.full_tile.pixel_size_m()
        # Size by the largest tile so every tile fits the print bed.
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
        z_ref = float(self.full_tile.heights[finite].min())

        for s in self.sections:
            s.dx_mm = dx_m * spec.scale_xy_mm_per_m
            s.dy_mm = dy_m * spec.scale_xy_mm_per_m
            s.z_scale_mm_per_m = spec.z_scale_mm_per_m
            s.base_thickness_mm = spec.base_thickness_mm
            s.z_ref_m = z_ref
        return self

    def export_stl(self, directory, *, prefix: str = "tile") -> List[Path]:
        """Write one STL per tile: ``<directory>/<prefix>_r<row>_c<col>.stl``.

        Returns the list of written paths.
        """
        if not self.sections or self.sections[0].dx_mm is None:
            raise RuntimeError("call .scale(...) on the Grid before exporting")

        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        paths: List[Path] = []
        for s in self.sections:
            p = directory / f"{prefix}_r{s.row}_c{s.col}.stl"
            s.export_stl(p)
            paths.append(p)
        return paths
