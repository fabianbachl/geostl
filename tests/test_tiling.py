"""Tests for grid tiling (Phase 5)."""
import numpy as np
import pytest

from geostl import GeoPoint, Grid, Region, Section

trimesh = pytest.importorskip("trimesh")


def _region() -> Region:
    return Region.from_corners(GeoPoint(47.69, 14.03), GeoPoint(47.73, 14.09))


def test_grid_shape_and_labels(synthetic_source):
    grid = _region().to_grid(synthetic_source, nx=2, ny=3)
    assert isinstance(grid, Grid)
    assert (grid.nx, grid.ny) == (2, 3)
    assert len(grid.sections) == 6
    assert {(s.row, s.col) for s in grid.sections} == {
        (r, c) for r in range(3) for c in range(2)
    }
    assert all(isinstance(s, Section) for s in grid.sections)


def test_seams_share_identical_edges(synthetic_source):
    grid = _region().to_grid(synthetic_source, nx=2, ny=2)
    by = {(s.row, s.col): s.tile.heights for s in grid.sections}
    # vertical seam: east column of (0,0) == west column of (0,1)
    assert np.array_equal(by[(0, 0)][:, -1], by[(0, 1)][:, 0])
    # horizontal seam: south row of (0,0) == north row of (1,0)
    assert np.array_equal(by[(0, 0)][-1, :], by[(1, 0)][0, :])


def test_scale_is_shared_across_tiles(synthetic_source):
    grid = _region().to_grid(synthetic_source, nx=2, ny=2).scale(
        bed_size_mm=100.0, z_exaggeration=1.5
    )
    assert len({s.dx_mm for s in grid.sections}) == 1
    assert len({s.z_scale_mm_per_m for s in grid.sections}) == 1
    refs = {s.z_ref_m for s in grid.sections}
    assert len(refs) == 1
    assert next(iter(refs)) == pytest.approx(float(grid.full_tile.heights.min()))


def test_shared_seam_z_matches_after_scaling(synthetic_source):
    """The printable guarantee: shared-seam top-surface heights are equal in mm."""
    grid = _region().to_grid(synthetic_source, nx=2, ny=2).scale(
        bed_size_mm=100.0, z_exaggeration=2.0
    )
    by = {(s.row, s.col): s for s in grid.sections}
    a, b = by[(0, 0)], by[(0, 1)]
    za = (a.tile.heights[:, -1] - a.z_ref_m) * a.z_scale_mm_per_m + a.base_thickness_mm
    zb = (b.tile.heights[:, 0] - b.z_ref_m) * b.z_scale_mm_per_m + b.base_thickness_mm
    assert np.allclose(za, zb)


def test_grid_export_writes_watertight_tiles(tmp_path, synthetic_source):
    grid = _region().to_grid(synthetic_source, nx=2, ny=2).scale(bed_size_mm=100.0)
    paths = grid.export_stl(tmp_path, prefix="t")
    assert {p.name for p in paths} == {
        "t_r0_c0.stl", "t_r0_c1.stl", "t_r1_c0.stl", "t_r1_c1.stl"
    }
    for p in paths:
        assert p.exists() and p.stat().st_size > 0
        assert trimesh.load(str(p)).is_watertight


def test_export_requires_scale(tmp_path, synthetic_source):
    grid = _region().to_grid(synthetic_source, nx=2, ny=2)
    with pytest.raises(RuntimeError):
        grid.export_stl(tmp_path)


def test_too_many_tiles_raises(synthetic_source):
    # A 32x32 source cannot split into 40 tiles on an axis without collapsing edges.
    with pytest.raises(ValueError):
        _region().to_grid(synthetic_source, nx=40, ny=1)
