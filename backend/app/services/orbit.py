"""
Circular-orbit mechanics.

Assumptions
-----------
- Earth is spherical with radius R_EARTH_KM.
- Orbit is perfectly circular at the given altitude.
"""

import math

from app.services.constants import MU_EARTH_KM3_S2, R_EARTH_KM


def orbit_radius_km(altitude_km: float) -> float:
    """Orbit radius = R_earth + altitude."""
    return R_EARTH_KM + altitude_km


def orbital_period_s(altitude_km: float) -> float:
    """
    Keplerian period for a circular orbit.

        T = 2 * pi * sqrt(r^3 / mu)

    Parameters
    ----------
    altitude_km : float
        Altitude above Earth's surface [km].

    Returns
    -------
    float
        Orbital period [seconds].
    """
    r = orbit_radius_km(altitude_km)
    return 2.0 * math.pi * math.sqrt(r**3 / MU_EARTH_KM3_S2)
