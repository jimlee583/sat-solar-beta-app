"""
Solar array geometry and dual-axis tracking for a two-wing array system.

Version 2 Geometry
------------------
Two solar array wings are mounted symmetrically on the spacecraft body,
which is aligned with the VVLH frame:

    +X = velocity direction
    +Y = cross-track (completes right-handed triad)
    +Z = nadir

±Y mounting (default, mounting="y"):
    Forward wing: mounted on the +Y side, zero-angle normal n0 = [0, +1, 0]
    Aft    wing:  mounted on the -Y side, zero-angle normal n0 = [0, -1, 0]

    Gimbal sequence:  n = Rz(outer) @ Rx(inner) @ n0
    Right wing (N0_RIGHT = [0,+1,0]):  inner = arcsin(sz),  outer = atan2(-sx, sy)
    Left  wing (N0_LEFT  = [0,-1,0]):  inner = arcsin(-sz), outer = atan2(sx, -sy)

±X mounting (mounting="x"):
    Forward wing: mounted on the +X side, zero-angle normal n0 = [+1, 0, 0]
    Aft    wing:  mounted on the -X side, zero-angle normal n0 = [-1, 0, 0]

    Gimbal sequence:  n = Rz(outer) @ Ry(inner) @ n0
    Forward wing (N0_FORWARD = [+1,0,0]):  inner = arcsin(-sz), outer = atan2(sy, sx)
    Aft     wing (N0_AFT     = [-1,0,0]):  inner = arcsin(sz),  outer = atan2(-sy, -sx)

    Analytical normal for forward wing:
        n = [cos(outer)*cos(inner),  sin(outer)*cos(inner),  -sin(inner)]

When |cos(inner)| ≈ 0 (sun along ±Z), outer is indeterminate (gimbal lock);
we default outer = 0.
"""

import numpy as np


def rotation_matrix_x(angle_rad: float) -> np.ndarray:
    """3x3 rotation matrix about the X axis (right-hand rule)."""
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [1.0, 0.0, 0.0],
        [0.0, c, -s],
        [0.0, s, c],
    ])


def rotation_matrix_y(angle_rad: float) -> np.ndarray:
    """3x3 rotation matrix about the Y axis (right-hand rule)."""
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [ c,  0.0, s],
        [0.0, 1.0, 0.0],
        [-s,  0.0, c],
    ])


def rotation_matrix_z(angle_rad: float) -> np.ndarray:
    """3x3 rotation matrix about the Z axis (right-hand rule)."""
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    return np.array([
        [c, -s, 0.0],
        [s, c, 0.0],
        [0.0, 0.0, 1.0],
    ])


def compute_wing_normal(
    outer_rad: float,
    inner_rad: float,
    n0: np.ndarray,
    mounting: str = "y",
) -> np.ndarray:
    """
    Compute the wing panel normal after applying outer (Z) and inner rotations.

    ±Y mounting (mounting="y"):  n = Rz(outer) @ Rx(inner) @ n0
    ±X mounting (mounting="x"):  n = Rz(outer) @ Ry(inner) @ n0

    Returns a 3-vector (unit length within numerical tolerance).
    """
    Rz = rotation_matrix_z(outer_rad)
    Ri = rotation_matrix_x(inner_rad) if mounting == "y" else rotation_matrix_y(inner_rad)
    return Rz @ Ri @ n0


# Base (zero-angle) panel normals — ±Y mounting
N0_RIGHT = np.array([0.0, 1.0, 0.0])
N0_LEFT = np.array([0.0, -1.0, 0.0])

# Base (zero-angle) panel normals — ±X mounting
N0_FORWARD = np.array([1.0, 0.0, 0.0])
N0_AFT = np.array([-1.0, 0.0, 0.0])

# Threshold below which cos(inner) is treated as zero (gimbal lock)
_COS_INNER_EPS = 1e-10


def solve_dual_axis_tracking(
    sun_vec_body: np.ndarray,
    n0: np.ndarray,
    mounting: str = "y",
) -> tuple[float, float]:
    """
    Solve for ideal (outer, inner) gimbal angles [radians] so that the wing
    normal aligns with the sun unit vector.

    Parameters
    ----------
    sun_vec_body : (3,) array
        Sun unit vector in body/VVLH coordinates.
    n0 : (3,) array
        Zero-angle panel normal (N0_RIGHT, N0_LEFT, N0_FORWARD, or N0_AFT).
    mounting : str
        "y" → Rz(outer) @ Rx(inner) @ n0  (±Y cross-track wings)
        "x" → Rz(outer) @ Ry(inner) @ n0  (±X velocity-axis wings)

    Returns
    -------
    outer_rad, inner_rad : float
        Gimbal angles in radians.

    Notes
    -----
    ±Y mounting:
        Right (n0[1] > 0):  inner = arcsin(sz),   outer = atan2(-sx, sy)
        Left  (n0[1] < 0):  inner = arcsin(-sz),  outer = atan2(sx, -sy)

    ±X mounting:
        Forward (n0[0] > 0):  inner = arcsin(-sz), outer = atan2(sy, sx)
        Aft     (n0[0] < 0):  inner = arcsin(sz),  outer = atan2(-sy, -sx)

    When |cos(inner)| < epsilon, outer is set to 0 (gimbal lock).
    """
    sx, sy, sz = float(sun_vec_body[0]), float(sun_vec_body[1]), float(sun_vec_body[2])

    if mounting == "x":
        if n0[0] > 0:  # forward wing
            inner_rad = np.arcsin(np.clip(-sz, -1.0, 1.0))
            cos_inner = np.cos(inner_rad)
            if abs(cos_inner) < _COS_INNER_EPS:
                outer_rad = 0.0
            else:
                outer_rad = float(np.arctan2(sy, sx))
        else:  # aft wing
            inner_rad = np.arcsin(np.clip(sz, -1.0, 1.0))
            cos_inner = np.cos(inner_rad)
            if abs(cos_inner) < _COS_INNER_EPS:
                outer_rad = 0.0
            else:
                outer_rad = float(np.arctan2(-sy, -sx))
    else:  # mounting == "y"
        if n0[1] > 0:  # right wing
            inner_rad = np.arcsin(np.clip(sz, -1.0, 1.0))
            cos_inner = np.cos(inner_rad)
            if abs(cos_inner) < _COS_INNER_EPS:
                outer_rad = 0.0
            else:
                outer_rad = float(np.arctan2(-sx, sy))
        else:  # left wing
            inner_rad = np.arcsin(np.clip(-sz, -1.0, 1.0))
            cos_inner = np.cos(inner_rad)
            if abs(cos_inner) < _COS_INNER_EPS:
                outer_rad = 0.0
            else:
                outer_rad = float(np.arctan2(sx, -sy))

    return outer_rad, float(inner_rad)


def compute_wing_arrays(
    sun_x: np.ndarray,
    sun_y: np.ndarray,
    sun_z: np.ndarray,
    n0: np.ndarray,
    mounting: str = "y",
) -> dict[str, np.ndarray]:
    """
    For sampled sun vectors over one orbit, compute tracking angles,
    wing normals, incidence angles, and cosine efficiency for one wing.

    Parameters
    ----------
    sun_x, sun_y, sun_z : (N,) arrays
        Sun unit vector components in body/VVLH.
    n0 : (3,) array
        Zero-angle panel normal for this wing.
    mounting : str
        "y" for ±Y cross-track wings, "x" for ±X velocity-axis wings.

    Returns
    -------
    dict with keys:
        outer_angle_deg, inner_angle_deg,
        normal_x, normal_y, normal_z,
        incidence_deg, cosine_efficiency
    """
    n = len(sun_x)
    outer_deg = np.empty(n)
    inner_deg = np.empty(n)
    normal_x = np.empty(n)
    normal_y = np.empty(n)
    normal_z = np.empty(n)
    incidence = np.empty(n)
    cos_eff = np.empty(n)

    for i in range(n):
        s = np.array([sun_x[i], sun_y[i], sun_z[i]])
        s_norm = np.linalg.norm(s)

        if s_norm < 1e-15:
            outer_deg[i] = 0.0
            inner_deg[i] = 0.0
            normal_x[i], normal_y[i], normal_z[i] = n0
            incidence[i] = 90.0
            cos_eff[i] = 0.0
            continue

        s_hat = s / s_norm

        o_rad, i_rad = solve_dual_axis_tracking(s_hat, n0, mounting=mounting)
        outer_deg[i] = np.degrees(o_rad)
        inner_deg[i] = np.degrees(i_rad)

        n_vec = compute_wing_normal(o_rad, i_rad, n0, mounting=mounting)
        n_len = np.linalg.norm(n_vec)
        if n_len > 0:
            n_vec = n_vec / n_len

        normal_x[i] = n_vec[0]
        normal_y[i] = n_vec[1]
        normal_z[i] = n_vec[2]

        dot = float(np.dot(n_vec, s_hat))
        dot_clipped = np.clip(dot, -1.0, 1.0)
        incidence[i] = np.degrees(np.arccos(dot_clipped))
        cos_eff[i] = max(0.0, dot_clipped)

    return {
        "outer_angle_deg": outer_deg,
        "inner_angle_deg": inner_deg,
        "normal_x": normal_x,
        "normal_y": normal_y,
        "normal_z": normal_z,
        "incidence_deg": incidence,
        "cosine_efficiency": cos_eff,
    }
