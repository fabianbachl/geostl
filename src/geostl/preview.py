"""Optional matplotlib previews (install with the ``viz`` extra).

matplotlib is imported lazily inside each function so the core package has no
hard dependency on it.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.tiling import Section


def preview_heatmap(tile: "ElevationTile"):
    """2D ``pcolormesh`` preview of an elevation tile (ported from the notebook)."""
    raise NotImplementedError  # Phase 8


def preview_mesh(section: "Section"):
    """3D surface preview of a section."""
    raise NotImplementedError  # Phase 8
