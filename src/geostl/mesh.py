"""Heightfield -> watertight triangle mesh -> STL.

Connects the two halves the prototype left disjoint (a terrain array and a
numpy-stl mesh). Construction is fully vectorized; base/wall generation is kept
parameterized so tile connectors (pin holes) can be subtracted later.

The solid is built as a top surface over an ``H x W`` height lattice, a mirrored
flat base, and four vertical walls joining their perimeters. The base mirrors the
full grid so its perimeter vertices coincide exactly with the wall bottoms — that
shared subdivision is what keeps the solid watertight. All triangles are wound so
their normals point outward.
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
        self.vertices = vertices  # (N, 3) float
        self.faces = faces        # (F, 3) int, outward-wound

    def is_watertight(self) -> bool:
        """Return whether the mesh is a closed manifold (uses trimesh)."""
        import numpy as np

        try:
            import trimesh
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError(
                "is_watertight() needs the 'validate' extra (pip install geostl[validate])"
            ) from exc

        tm = trimesh.Trimesh(
            vertices=np.asarray(self.vertices, dtype="float64"),
            faces=np.asarray(self.faces),
            process=False,
        )
        return bool(tm.is_watertight)

    def export_stl(self, path, *, binary: bool = True) -> None:
        """Write the mesh to ``path`` as an STL file (binary by default)."""
        import numpy as np
        from stl import Mode
        from stl import mesh as stl_mesh

        v = np.asarray(self.vertices, dtype="float32")
        f = np.asarray(self.faces, dtype=np.int64)
        data = np.zeros(len(f), dtype=stl_mesh.Mesh.dtype)
        data["vectors"] = v[f]
        m = stl_mesh.Mesh(data, remove_empty_areas=False)
        # save() recomputes facet normals from the (outward) winding by default.
        m.save(str(path), mode=Mode.BINARY if binary else Mode.ASCII)


class Mesher:
    """Builds a watertight solid from a scaled height lattice."""

    def build(
        self,
        heights_mm: "np.ndarray",
        dx_mm: float,
        dy_mm: float,
        base_z_mm: float,
    ) -> TriangleMesh:
        """Build a closed, outward-wound solid.

        Args:
            heights_mm: 2D top-surface heights in mm (row 0 = north); must be finite.
            dx_mm: column spacing in mm.
            dy_mm: row spacing in mm.
            base_z_mm: z of the flat base plane; must sit below every top height.
        """
        import numpy as np

        z = np.asarray(heights_mm, dtype="float64")
        if z.ndim != 2:
            raise ValueError("heights_mm must be a 2D array")
        h, w = z.shape
        if h < 2 or w < 2:
            raise ValueError("need at least a 2x2 grid to build a mesh")
        if not np.all(np.isfinite(z)):
            raise ValueError("heights_mm contains non-finite values; fill them first")

        # --- vertices: top grid then a mirrored base grid --------------------
        rr, cc = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        x = cc * float(dx_mm)
        y = (h - 1 - rr) * float(dy_mm)  # row 0 (north) -> largest y
        top = np.stack([x, y, z], axis=-1).reshape(-1, 3)
        base = np.stack(
            [x, y, np.full_like(z, float(base_z_mm))], axis=-1
        ).reshape(-1, 3)
        vertices = np.concatenate([top, base], axis=0)

        off = h * w  # base vertex index = off + (r * w + c)

        # --- grid-cell corner indices (row-major, top grid) ------------------
        r = np.arange(h - 1)[:, None]
        c = np.arange(w - 1)[None, :]
        v00 = (r * w + c).ravel()
        v01 = (r * w + c + 1).ravel()
        v10 = ((r + 1) * w + c).ravel()
        v11 = ((r + 1) * w + c + 1).ravel()

        def tri(*cols):
            return np.stack(cols, axis=1)

        # Top surface (normals +z) and mirrored base (normals -z, reversed).
        top1 = tri(v00, v10, v11)
        top2 = tri(v00, v11, v01)
        base1 = tri(v00 + off, v11 + off, v10 + off)
        base2 = tri(v00 + off, v01 + off, v11 + off)

        # --- walls (outward normals) -----------------------------------------
        cw = np.arange(w - 1)
        rw = np.arange(h - 1)
        south_row = (h - 1) * w  # row H-1 sits at y = 0 (south)
        e = w - 1                # last column (east)

        north1 = tri(cw, cw + 1, off + cw + 1)          # +y
        north2 = tri(cw, off + cw + 1, off + cw)
        south1 = tri(south_row + cw, off + south_row + cw + 1, south_row + cw + 1)  # -y
        south2 = tri(south_row + cw, off + south_row + cw, off + south_row + cw + 1)
        west1 = tri(rw * w, off + (rw + 1) * w, (rw + 1) * w)  # -x
        west2 = tri(rw * w, off + rw * w, off + (rw + 1) * w)
        east1 = tri(rw * w + e, (rw + 1) * w + e, off + (rw + 1) * w + e)  # +x
        east2 = tri(rw * w + e, off + (rw + 1) * w + e, off + rw * w + e)

        faces = np.concatenate(
            [top1, top2, base1, base2, north1, north2,
             south1, south2, west1, west2, east1, east2],
            axis=0,
        )
        return TriangleMesh(vertices=vertices, faces=faces)
