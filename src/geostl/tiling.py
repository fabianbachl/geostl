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
        raise NotImplementedError  # Phase 1-3

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
        raise NotImplementedError  # Phase 4

    def to_mesh(self) -> "TriangleMesh":
        """Build the watertight mesh (top surface + walls + base)."""
        raise NotImplementedError  # Phase 3

    def export_stl(self, path) -> None:
        raise NotImplementedError  # Phase 3


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
