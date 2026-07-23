"""Optional matplotlib previews (install with the ``viz`` extra).

matplotlib is imported lazily inside each function so the core package has no
hard dependency on it.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geostl.elevation import ElevationTile
    from geostl.tiling import Section, Grid, Region


def preview_region(region: "Region"):
    """2D ``pcolormesh`` preview of a region.
    Plot shows original dimensions and fetched resolution.
    """
    raise NotImplementedError  # Phase 8

def preview_grid(grid: "Grid"):
    """2D ``pcolormesh`` preview of a grid of sections.
    Plot shows model dimensions.
    """
    raise NotImplementedError  # Phase 8

def preview_section(section: "Section"):
    """2D ``pcolormesh`` preview of a section.
    Plot shows model dimensions.
    """
    raise NotImplementedError  # Phase 8


def preview_mesh(section: "Section"):
    """3D surface preview of a section."""
    raise NotImplementedError  # Phase 8
