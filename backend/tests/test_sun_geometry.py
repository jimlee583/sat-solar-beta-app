"""Tests for Sun vector and eclipse mask generation."""

import numpy as np

from app.services.sun_geometry import eclipse_mask, sun_angles_vvlh, sun_vector_vvlh


def test_sun_vector_unit_length():
    """Sun vector should always be unit length."""
    angles = np.linspace(0, 360, 361)
    for beta in [0.0, 30.0, 60.0, -45.0]:
        sx, sy, sz = sun_vector_vvlh(angles, beta)
        norms = np.sqrt(sx**2 + sy**2 + sz**2)
        np.testing.assert_allclose(norms, 1.0, atol=1e-12)


def test_sun_vector_beta_zero_in_plane():
    """At beta=0 the Sun vector should lie in the X-Z plane (S_y = 0)."""
    angles = np.linspace(0, 360, 100)
    sx, sy, sz = sun_vector_vvlh(angles, 0.0)
    np.testing.assert_allclose(sy, 0.0, atol=1e-15)


def test_sun_vector_at_theta_zero():
    """At theta=0, beta=0: Sun should point in -Z (away from nadir → above satellite)."""
    sx, sy, sz = sun_vector_vvlh(np.array([0.0]), 0.0)
    np.testing.assert_allclose(sx[0], 0.0, atol=1e-15)
    np.testing.assert_allclose(sy[0], 0.0, atol=1e-15)
    np.testing.assert_allclose(sz[0], -1.0, atol=1e-15)


def test_eclipse_mask_no_eclipse_at_high_beta():
    """No eclipse samples when beta > critical."""
    angles = np.linspace(0, 360, 360)
    mask = eclipse_mask(angles, 500.0, 89.0)
    assert not mask.any()


def test_eclipse_mask_centered_at_180():
    """Eclipse should be centered around orbit angle = 180°."""
    angles = np.linspace(0, 360, 3600, endpoint=False)
    mask = eclipse_mask(angles, 500.0, 0.0)
    eclipsed_angles = angles[mask]
    if len(eclipsed_angles) > 0:
        center = eclipsed_angles.mean()
        assert abs(center - 180.0) < 1.0


def test_sun_angles_range():
    """Elevation should be in [-90, 90], azimuth in [-180, 180]."""
    angles = np.linspace(0, 360, 360)
    sx, sy, sz = sun_vector_vvlh(angles, 45.0)
    az, el = sun_angles_vvlh(sx, sy, sz)
    assert az.min() >= -180.0
    assert az.max() <= 180.0
    assert el.min() >= -90.0
    assert el.max() <= 90.0
