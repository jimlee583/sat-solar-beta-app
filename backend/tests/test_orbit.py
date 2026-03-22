"""Tests for circular orbit calculations."""

import math

from app.services.constants import MU_EARTH_KM3_S2, R_EARTH_KM
from app.services.orbit import orbit_radius_km, orbital_period_s


def test_orbit_radius():
    assert orbit_radius_km(0.0) == R_EARTH_KM
    assert orbit_radius_km(500.0) == R_EARTH_KM + 500.0


def test_orbital_period_iss():
    """ISS at ~408 km should have a period near 92.6 minutes."""
    T = orbital_period_s(408.0)
    T_min = T / 60.0
    assert 92.0 < T_min < 93.5


def test_orbital_period_formula():
    """Verify against the direct Kepler formula."""
    alt = 600.0
    r = R_EARTH_KM + alt
    expected = 2.0 * math.pi * math.sqrt(r**3 / MU_EARTH_KM3_S2)
    assert abs(orbital_period_s(alt) - expected) < 1e-6


def test_orbital_period_increases_with_altitude():
    assert orbital_period_s(800.0) > orbital_period_s(400.0)
