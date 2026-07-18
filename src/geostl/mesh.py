"""Heightfield -> watertight triangle mesh -> STL.

Connects the two halves the prototype left disjoint (a terrain array and a
numpy-stl mesh). Construction is vectorized; base/wall generation is kept
parameterized so tile connectors (pin holes) can be subtracted later.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


class TriangleMesh:
    """A backend-agnostic triangle mesh (vertices + faces) with STL export.

    Keeping this separate from numpy-stl / trimesh lets us export with one and
    validate/repair with the other without leaking either into the public API.
    """

    def __init__(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces

    def is_watertight(self) -> bool:
        """Best-effort manifold/watertight check (uses trimesh if installed)."""
        raise NotImplementedError  # Phase 3

    def export_stl(self, path, *, binary: bool = True) -> None:
        raise NotImplementedError  # Phase 3


class Mesher:
    """Builds a watertight solid from a scaled height lattice.

    Top surface: ``(H-1)(W-1)*2`` triangles. Plus vertical side walls dropped to
    the base plane, plus a bottom face -> a closed, printable solid.
    """

    def build(
        self,
        heights_mm: "np.ndarray",
        dx_mm: float,
        dy_mm: float,
        base_z_mm: float,
    ) -> TriangleMesh:
        raise NotImplementedError  # Phase 3
