"""Tests for the mesher and STL export (Phase 3)."""
import numpy as np
import pytest

from geostl.mesh import Mesher

trimesh = pytest.importorskip("trimesh")


def _trimesh(m):
    return trimesh.Trimesh(
        vertices=np.asarray(m.vertices), faces=np.asarray(m.faces), process=False
    )


def test_flat_grid_counts_and_watertight():
    h = w = 3
    z = np.full((h, w), 10.0)
    m = Mesher().build(z, dx_mm=1.0, dy_mm=1.0, base_z_mm=0.0)

    assert m.vertices.shape == (2 * h * w, 3)   # top grid + mirrored base
    # top + base: 2 * 2*(h-1)*(w-1) = 16 ; walls: 2*2*(w-1) + 2*2*(h-1) = 16
    assert m.faces.shape == (32, 3)
    assert m.is_watertight()


def test_volume_bounds_and_outward_normals():
    h, w = 4, 5
    z = np.full((h, w), 8.0)
    m = Mesher().build(z, dx_mm=2.0, dy_mm=3.0, base_z_mm=0.0)
    tm = _trimesh(m)

    assert tm.is_watertight
    assert tm.is_winding_consistent
    # positive volume confirms normals point outward (not inverted)
    assert tm.volume == pytest.approx((w - 1) * 2.0 * (h - 1) * 3.0 * 8.0, rel=1e-6)
    lo, hi = tm.bounds
    assert (hi - lo) == pytest.approx([(w - 1) * 2.0, (h - 1) * 3.0, 8.0])


def test_varied_surface_is_watertight():
    z = np.array([[0, 1, 2], [1, 4, 2], [0, 2, 1]], dtype="float64") * 5 + 5
    m = Mesher().build(z, dx_mm=1.5, dy_mm=1.5, base_z_mm=0.0)
    tm = _trimesh(m)
    assert tm.is_watertight and tm.is_winding_consistent
    assert tm.volume > 0


def test_rejects_nonfinite_heights():
    z = np.array([[1.0, 2.0], [np.nan, 4.0]])
    with pytest.raises(ValueError):
        Mesher().build(z, 1.0, 1.0, 0.0)


def test_rejects_degenerate_grid():
    with pytest.raises(ValueError):
        Mesher().build(np.zeros((1, 5)), 1.0, 1.0, 0.0)


def test_export_stl_roundtrip(tmp_path):
    z = np.array([[0, 1, 2], [1, 3, 2], [0, 2, 1]], dtype="float64") * 5 + 5
    m = Mesher().build(z, 1.0, 1.0, 0.0)
    out = tmp_path / "m.stl"
    m.export_stl(out)

    assert out.exists() and out.stat().st_size > 0
    reloaded = trimesh.load(str(out))
    assert reloaded.is_watertight


def test_section_pipeline_to_stl(tmp_path, synthetic_source):
    """Region -> Section -> scale -> STL, end to end, with no files or network."""
    from geostl import GeoPoint, Region

    region = Region.from_corners(GeoPoint(47.69, 14.03), GeoPoint(47.73, 14.09))
    section = region.to_section(synthetic_source).scale(
        bed_size_mm=100.0, z_exaggeration=1.5, base_thickness_mm=2.0
    )
    out = tmp_path / "sec.stl"
    section.export_stl(out)

    tm = trimesh.load(str(out))
    assert tm.is_watertight
    lo, hi = tm.bounds
    # The longer horizontal side is scaled to the 100 mm bed.
    assert max(float((hi - lo)[0]), float((hi - lo)[1])) == pytest.approx(100.0, rel=1e-3)


def test_resolution_mm_downsamples_the_mesh(synthetic_source):
    """A coarser resolution_mm yields a lighter mesh at the requested pixel size."""
    from geostl import GeoPoint, Region

    region = Region.from_corners(GeoPoint(47.69, 14.03), GeoPoint(47.73, 14.09))
    section = region.to_section(synthetic_source).scale(bed_size_mm=100.0)

    full = section.to_mesh()                        # native (32x32)
    coarse = section.to_mesh(resolution_mm=10.0)    # native printed pixel ~3.2 mm

    assert coarse.faces.shape[0] < full.faces.shape[0]
    assert _trimesh(coarse).is_watertight
    # printed column spacing along a row ~ resolution_mm
    xs = np.unique(np.round(np.asarray(coarse.vertices)[:, 0], 3))
    assert float(np.median(np.diff(xs))) == pytest.approx(10.0, rel=0.2)


def test_resolution_mm_finer_than_source_warns(synthetic_source):
    from geostl import GeoPoint, Region

    region = Region.from_corners(GeoPoint(47.69, 14.03), GeoPoint(47.73, 14.09))
    section = region.to_section(synthetic_source).scale(bed_size_mm=100.0)
    with pytest.warns(RuntimeWarning):
        m = section.to_mesh(resolution_mm=0.5)  # finer than the native printed pixel
    assert _trimesh(m).is_watertight
