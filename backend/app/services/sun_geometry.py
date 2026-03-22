"""
Sun-vector and Sun-angle generation in the VVLH frame over one orbit.

VVLH Frame Convention (Version 1)
----------------------------------
    +X  =  velocity direction (in the local horizontal plane)
    +Z  =  nadir (toward Earth center)
    +Y  =  completes the right-handed triad  (Y = Z x X)

The VVLH axes map to the orbital basis vectors as:
    VVLH +X  =  e_v   (velocity)
    VVLH +Y  = -e_n   (negative orbit normal,  since Y = Z x X = (-e_r) x e_v)
    VVLH +Z  = -e_r   (nadir = negative radial outward)

Orbit angle convention
----------------------
Theta is measured from the subsolar point — the location in the orbit closest
to the Sun projection into the orbit plane.  Theta = 0 means the Sun is
directly "above" the satellite (anti-nadir / zenith direction).

Sun unit vector in VVLH
-----------------------
Decomposing the Sun direction (at infinity) into the rotating orbital basis
and then re-expressing in VVLH:

    S_x = -sin(theta) * cos(beta)
    S_y = -sin(beta)
    S_z = -cos(theta) * cos(beta)

Sanity checks:
  - theta=0, beta=0  →  S = (0, 0, -1)  → Sun at zenith (anti-nadir) ✓
  - theta=180°        →  S_z = +cos(beta) → Sun below (toward Earth)  ✓  (eclipse zone)
  - beta=0            →  S_y = 0, Sun stays in the X-Z plane          ✓

Azimuth and elevation
---------------------
    azimuth   = atan2(S_y, S_x)   [deg]
    elevation = arcsin(S_z)        [deg]

Elevation > 0 means the Sun is toward nadir.

Eclipse masking
---------------
The satellite is in eclipse when theta falls within the eclipse arc centered
at theta = 180° (anti-Sun side).
"""

import numpy as np

from app.services.eclipse import eclipse_half_angle_deg, has_eclipse


def sun_vector_vvlh(
    orbit_angle_deg: np.ndarray,
    beta_deg: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute the Sun unit-vector components in the VVLH frame over one orbit.

    Parameters
    ----------
    orbit_angle_deg : ndarray
        Orbit angle array [degrees], 0 = subsolar point.
    beta_deg : float
        Beta angle [degrees].

    Returns
    -------
    sx, sy, sz : ndarray
        Sun unit-vector components in VVLH (+X vel, +Y cross, +Z nadir).
    """
    theta = np.radians(orbit_angle_deg)
    beta = np.radians(beta_deg)

    sx = -np.sin(theta) * np.cos(beta)
    sy = -np.sin(beta) * np.ones_like(theta)
    sz = -np.cos(theta) * np.cos(beta)

    return sx, sy, sz


def sun_angles_vvlh(
    sx: np.ndarray,
    sy: np.ndarray,
    sz: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Convert VVLH Sun vector to azimuth and elevation.

    azimuth   = atan2(S_y, S_x)   [deg]
    elevation = arcsin(S_z)        [deg]

    Elevation is positive when the Sun is toward nadir (+Z).
    """
    az = np.degrees(np.arctan2(sy, sx))
    el = np.degrees(np.arcsin(np.clip(sz, -1.0, 1.0)))
    return az, el


def eclipse_mask(
    orbit_angle_deg: np.ndarray,
    altitude_km: float,
    beta_deg: float,
) -> np.ndarray:
    """
    Boolean array: True where the satellite is in Earth's shadow.

    Eclipse is centered at orbit angle = 180° (anti-Sun point).
    """
    if not has_eclipse(altitude_km, beta_deg):
        return np.zeros_like(orbit_angle_deg, dtype=bool)

    half_angle = eclipse_half_angle_deg(altitude_km, beta_deg)

    # Wrap orbit angle to [0, 360)
    angle = np.mod(orbit_angle_deg, 360.0)

    # Eclipse region: 180 - half_angle  to  180 + half_angle
    return np.abs(angle - 180.0) <= half_angle
