"""Region + Grid: from a WGS84 rectangle to one or many mesh-ready Sections."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

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

        Fetching per-tile would resample independently and mismatch seams, so the
        split happens on the single fetched array with shared edge pixels — that
        is what makes the printed tiles butt together.
        """
        raise NotImplementedError  # Phase 5


@dataclass
class Section:
    """A single rectified region, ready to scale and mesh."""

    tile: "ElevationTile"
    row: int = 0
    col: int = 0
    # Physical scaling; None until .scale() resolves it.
    dx_mm: Optional[float] = None
    dy_mm: Optional[float] = None
    z_scale_mm_per_m: Optional[float] = None
    base_thickness_mm: Optional[float] = None

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

        The lowest finite elevation maps to ``base_thickness_mm`` above a base
        plane at z=0; NaN holes are filled at that lowest level so the solid stays
        closed.
        """
        import numpy as np

        from geostl.mesh import Mesher

        if self.dx_mm is None or self.z_scale_mm_per_m is None:
            raise RuntimeError("call .scale(...) before meshing this Section")

        h = np.asarray(self.tile.heights, dtype="float64")
        finite = np.isfinite(h)
        if not finite.any():
            raise ValueError("tile has no finite elevation data to mesh")
        min_h = float(h[finite].min())
        h = np.where(finite, h, min_h)

        z_top = (h - min_h) * self.z_scale_mm_per_m + self.base_thickness_mm
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

    def scale(self, **kwargs) -> "Grid":
        """Apply one shared scale to every tile (computed from the whole region)."""
        raise NotImplementedError  # Phase 5

    def export_stl(self, directory, *, prefix: str = "tile") -> None:
        """Write one STL per tile: ``<directory>/<prefix>_r<row>_c<col>.stl``."""
        raise NotImplementedError  # Phase 5
