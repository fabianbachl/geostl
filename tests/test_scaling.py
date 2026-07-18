"""Tests for physical scaling (Phase 4)."""
import pytest

from geostl.scaling import resolve_scale


def test_bed_size_fits_longest_side():
    spec = resolve_scale(4000.0, 2000.0, bed_size_mm=200.0)
    assert spec.scale_xy_mm_per_m == pytest.approx(200.0 / 4000.0)  # longest = 4000 m
    assert spec.z_scale_mm_per_m == pytest.approx(200.0 / 4000.0)   # exaggeration 1.0


def test_z_exaggeration_multiplies_vertical_only():
    spec = resolve_scale(4000.0, 2000.0, bed_size_mm=200.0, z_exaggeration=2.0)
    assert spec.z_scale_mm_per_m == pytest.approx(2.0 * spec.scale_xy_mm_per_m)


def test_explicit_scale_xy_passthrough():
    spec = resolve_scale(4000.0, 2000.0, scale_xy=0.05)
    assert spec.scale_xy_mm_per_m == pytest.approx(0.05)


def test_base_thickness_passthrough():
    spec = resolve_scale(100.0, 100.0, scale_xy=1.0, base_thickness_mm=5.0)
    assert spec.base_thickness_mm == 5.0


def test_requires_exactly_one_of_bed_or_scale():
    with pytest.raises(ValueError):
        resolve_scale(1.0, 1.0)  # neither
    with pytest.raises(ValueError):
        resolve_scale(1.0, 1.0, bed_size_mm=10.0, scale_xy=0.1)  # both
