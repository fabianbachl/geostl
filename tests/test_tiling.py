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
    assert len({s.scale_xy_mm_per_m for s in grid.sections}) == 1
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


def test_bed_size_is_per_tile(synthetic_source):
    """bed_size_mm sizes the print bed: every tile fits it, largest fills it."""
    bed = 100.0
    grid = _region().to_grid(synthetic_source, nx=2, ny=2).scale(bed_size_mm=bed)
    sizes = []
    for s in grid.sections:
        h, w = s.tile.heights.shape
        dx_m, dy_m = s.tile.pixel_size_m()
        sizes.append(max((w - 1) * dx_m, (h - 1) * dy_m) * s.scale_xy_mm_per_m)
    assert max(sizes) == pytest.approx(bed)         # largest tile fills the bed
    assert all(size <= bed + 1e-6 for size in sizes)  # every tile fits the bed


def test_grid_resolution_mm_downsample_keeps_seams(synthetic_source):
    """resolution_mm downsamples the whole region once and re-splits, so the tiles'
    shared seams stay pixel-identical."""
    grid = _region().to_grid(synthetic_source, nx=2, ny=2).scale(bed_size_mm=100.0)
    coarse = grid._sections_for(resolution_mm=12.0)  # coarser than the native printed px
    by = {(s.row, s.col): s.tile.heights for s in coarse}

    assert np.array_equal(by[(0, 0)][:, -1], by[(0, 1)][:, 0])  # vertical seam
    assert np.array_equal(by[(0, 0)][-1, :], by[(1, 0)][0, :])  # horizontal seam
    # and it actually downsampled relative to the native tiles
    assert by[(0, 0)].size < grid.sections[0].tile.heights.size
