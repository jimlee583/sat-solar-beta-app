"""
Eclipse geometry for a circular orbit.

Assumptions
-----------
- Earth is a perfect sphere (no oblateness, no atmosphere).
- Sun is at infinite distance (parallel illumination).
- Shadow is cylindrical (umbra only; penumbra ignored).

Key geometry
------------
For a circular orbit of radius *r* and a beta angle *beta*:

    rho  = arcsin(R_earth / r)          — Earth angular radius as seen from the satellite
    beta*  = 90° - rho                   — critical beta angle above which no eclipse occurs

When |beta| < beta*:

    eclipse_half_angle = arccos( cos(rho) / cos(beta) )

    eclipse_fraction  = eclipse_half_angle / pi    (fraction of one orbit)

The eclipse_half_angle is measured in the orbit plane and represents half of
the arc the satellite spends in shadow.
"""

import math

from app.services.constants import R_EARTH_KM
from app.services.orbit import orbit_radius_km


def earth_angular_radius_deg(altitude_km: float) -> float:
    """
    Earth angular radius (rho) as seen from the satellite.

        rho = arcsin(R_earth / r)
    """
    r = orbit_radius_km(altitude_km)
    return math.degrees(math.asin(R_EARTH_KM / r))


def critical_beta_deg(altitude_km: float) -> float:
    """
    Critical beta angle above which the orbit is fully sunlit.

        beta* = 90° - rho
    """
    rho = earth_angular_radius_deg(altitude_km)
    return 90.0 - rho


def has_eclipse(altitude_km: float, beta_deg: float) -> bool:
    """Return True if the orbit experiences eclipse at this beta angle."""
    return abs(beta_deg) < critical_beta_deg(altitude_km)


def eclipse_half_angle_deg(altitude_km: float, beta_deg: float) -> float:
    """
    Half the eclipse arc in the orbit plane [degrees].

        phi_e = arccos( cos(rho) / cos(beta) )

    Returns 0 if the orbit is fully sunlit.
    """
    if not has_eclipse(altitude_km, beta_deg):
        return 0.0

    rho_rad = math.radians(earth_angular_radius_deg(altitude_km))
    beta_rad = math.radians(beta_deg)
    cos_phi = math.cos(rho_rad) / math.cos(beta_rad)
    # Clamp for numerical safety
    cos_phi = max(-1.0, min(1.0, cos_phi))
    return math.degrees(math.acos(cos_phi))


def eclipse_fraction(altitude_km: float, beta_deg: float) -> float:
    """Fraction of the orbit spent in eclipse (0–1)."""
    phi_e = eclipse_half_angle_deg(altitude_km, beta_deg)
    return phi_e / 180.0


def eclipse_duration_s(altitude_km: float, beta_deg: float, period_s: float) -> float:
    """Eclipse duration in seconds."""
    return eclipse_fraction(altitude_km, beta_deg) * period_s
