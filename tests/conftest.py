"""Shared test fixtures. The default suite performs no network or file I/O."""
from __future__ import annotations

import numpy as np
import pytest

from geostl.elevation import ElevationTile
from geostl.sources.base import ElevationSource


def gaussian_hill(n: int = 32, height_m: float = 500.0) -> np.ndarray:
    """Deterministic synthetic terrain: a centered gaussian bump, in meters."""
    ax = np.linspace(-3.0, 3.0, n)
    xx, yy = np.meshgrid(ax, ax)
    return (height_m * np.exp(-(xx**2 + yy**2) / 2.0)).astype("float32")


class SyntheticSource(ElevationSource):
    """An :class:`ElevationSource` returning synthetic terrain — no I/O."""

    def __init__(self, n: int = 32, pixel_m: float = 25.0):
        self.n = n
        self.pixel_m = pixel_m

    def fetch(self, bbox, *, fetch_resolution_m=None, target_crs=None) -> ElevationTile:
        from affine import Affine  # ships transitively with rasterio

        heights = gaussian_hill(self.n)
        # Origin top-left; y decreases downward (row 0 = north).
        transform = Affine(self.pixel_m, 0.0, 0.0, 0.0, -self.pixel_m, 0.0)
        return ElevationTile(
            heights=heights, transform=transform, crs="EPSG:32633", nodata=None
        )


@pytest.fixture
def synthetic_source() -> SyntheticSource:
    return SyntheticSource()
