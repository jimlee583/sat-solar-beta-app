"""Tests for eclipse geometry."""

import math

from app.services.eclipse import (
    critical_beta_deg,
    eclipse_fraction,
    eclipse_half_angle_deg,
    has_eclipse,
)


def test_critical_beta_positive():
    beta_crit = critical_beta_deg(500.0)
    assert 0.0 < beta_crit < 90.0


def test_no_eclipse_above_critical_beta():
    beta_crit = critical_beta_deg(500.0)
    assert not has_eclipse(500.0, beta_crit + 1.0)
    assert not has_eclipse(500.0, -(beta_crit + 1.0))


def test_eclipse_exists_at_beta_zero():
    assert has_eclipse(500.0, 0.0)


def test_eclipse_fraction_bounds():
    ef = eclipse_fraction(500.0, 0.0)
    assert 0.0 < ef < 1.0


def test_eclipse_fraction_zero_when_full_sun():
    beta_crit = critical_beta_deg(500.0)
    ef = eclipse_fraction(500.0, beta_crit + 5.0)
    assert ef == 0.0


def test_eclipse_fraction_symmetric():
    """Eclipse fraction should be the same for ±beta."""
    ef_pos = eclipse_fraction(500.0, 30.0)
    ef_neg = eclipse_fraction(500.0, -30.0)
    assert abs(ef_pos - ef_neg) < 1e-10


def test_eclipse_fraction_decreases_with_beta():
    """Use beta values below the critical angle (~22° at 500 km)."""
    ef_0 = eclipse_fraction(500.0, 0.0)
    ef_10 = eclipse_fraction(500.0, 10.0)
    ef_20 = eclipse_fraction(500.0, 20.0)
    assert ef_0 > ef_10 > ef_20 > 0.0


def test_eclipse_half_angle_beta_zero():
    """At beta=0 the half-angle equals rho = arcsin(R_earth / r)."""
    from app.services.constants import R_EARTH_KM
    from app.services.orbit import orbit_radius_km

    alt = 500.0
    r = orbit_radius_km(alt)
    rho = math.degrees(math.asin(R_EARTH_KM / r))
    # arccos(cos(rho)/cos(0)) = arccos(cos(rho)) = rho
    assert abs(eclipse_half_angle_deg(alt, 0.0) - rho) < 0.01
