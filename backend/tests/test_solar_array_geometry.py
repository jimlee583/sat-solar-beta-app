"""Tests for the solar array geometry and dual-axis tracking module."""

import numpy as np
import pytest

from app.services.solar_array_geometry import (
    N0_AFT,
    N0_FORWARD,
    N0_LEFT,
    N0_RIGHT,
    compute_wing_arrays,
    compute_wing_normal,
    rotation_matrix_x,
    rotation_matrix_y,
    rotation_matrix_z,
    solve_dual_axis_tracking,
)


# ---- Rotation matrix tests ----


class TestRotationMatrices:
    def test_rx_identity_at_zero(self):
        R = rotation_matrix_x(0.0)
        np.testing.assert_allclose(R, np.eye(3), atol=1e-15)

    def test_rz_identity_at_zero(self):
        R = rotation_matrix_z(0.0)
        np.testing.assert_allclose(R, np.eye(3), atol=1e-15)

    def test_rx_90_deg(self):
        R = rotation_matrix_x(np.pi / 2)
        # Rx(90°) maps [0,1,0] -> [0,0,1] and [0,0,1] -> [0,-1,0]
        v = R @ np.array([0.0, 1.0, 0.0])
        np.testing.assert_allclose(v, [0.0, 0.0, 1.0], atol=1e-15)
        v2 = R @ np.array([0.0, 0.0, 1.0])
        np.testing.assert_allclose(v2, [0.0, -1.0, 0.0], atol=1e-15)

    def test_rz_90_deg(self):
        R = rotation_matrix_z(np.pi / 2)
        # Rz(90°) maps [1,0,0] -> [0,1,0] and [0,1,0] -> [-1,0,0]
        v = R @ np.array([1.0, 0.0, 0.0])
        np.testing.assert_allclose(v, [0.0, 1.0, 0.0], atol=1e-15)
        v2 = R @ np.array([0.0, 1.0, 0.0])
        np.testing.assert_allclose(v2, [-1.0, 0.0, 0.0], atol=1e-15)

    def test_rotation_is_orthogonal(self):
        for angle in [0.0, 0.5, 1.0, np.pi / 4, np.pi / 2, np.pi]:
            Rx = rotation_matrix_x(angle)
            Rz = rotation_matrix_z(angle)
            np.testing.assert_allclose(Rx @ Rx.T, np.eye(3), atol=1e-14)
            np.testing.assert_allclose(Rz @ Rz.T, np.eye(3), atol=1e-14)
            assert abs(np.linalg.det(Rx) - 1.0) < 1e-14
            assert abs(np.linalg.det(Rz) - 1.0) < 1e-14


# ---- Wing normal tests ----


class TestWingNormal:
    def test_right_wing_zero_angles(self):
        n = compute_wing_normal(0.0, 0.0, N0_RIGHT)
        np.testing.assert_allclose(n, [0.0, 1.0, 0.0], atol=1e-15)

    def test_left_wing_zero_angles(self):
        n = compute_wing_normal(0.0, 0.0, N0_LEFT)
        np.testing.assert_allclose(n, [0.0, -1.0, 0.0], atol=1e-15)

    def test_wing_normal_is_unit_length(self):
        rng = np.random.default_rng(42)
        for _ in range(100):
            outer = rng.uniform(-np.pi, np.pi)
            inner = rng.uniform(-np.pi / 2, np.pi / 2)
            for n0 in [N0_RIGHT, N0_LEFT]:
                n = compute_wing_normal(outer, inner, n0)
                assert abs(np.linalg.norm(n) - 1.0) < 1e-14

    def test_right_wing_analytical_formula(self):
        outer, inner = np.radians(30.0), np.radians(45.0)
        n = compute_wing_normal(outer, inner, N0_RIGHT)
        expected = np.array([
            -np.sin(outer) * np.cos(inner),
            np.cos(outer) * np.cos(inner),
            np.sin(inner),
        ])
        np.testing.assert_allclose(n, expected, atol=1e-14)

    def test_left_wing_analytical_formula(self):
        outer, inner = np.radians(30.0), np.radians(45.0)
        n = compute_wing_normal(outer, inner, N0_LEFT)
        expected = np.array([
            np.sin(outer) * np.cos(inner),
            -np.cos(outer) * np.cos(inner),
            -np.sin(inner),
        ])
        np.testing.assert_allclose(n, expected, atol=1e-14)


# ---- Dual-axis tracking tests ----


class TestDualAxisTracking:
    @pytest.mark.parametrize("n0", [N0_RIGHT, N0_LEFT])
    def test_tracking_recovers_sun_vector(self, n0):
        """For random sun vectors, tracking should align the normal with the sun."""
        rng = np.random.default_rng(123)
        for _ in range(50):
            s = rng.standard_normal(3)
            s = s / np.linalg.norm(s)
            outer, inner = solve_dual_axis_tracking(s, n0)
            n = compute_wing_normal(outer, inner, n0)
            np.testing.assert_allclose(n, s, atol=1e-10)

    def test_right_wing_sun_along_y(self):
        """Sun along +Y should give zero angles for the right wing."""
        s = np.array([0.0, 1.0, 0.0])
        outer, inner = solve_dual_axis_tracking(s, N0_RIGHT)
        n = compute_wing_normal(outer, inner, N0_RIGHT)
        np.testing.assert_allclose(n, s, atol=1e-15)
        assert abs(outer) < 1e-10
        assert abs(inner) < 1e-10

    def test_left_wing_sun_along_neg_y(self):
        """Sun along -Y should give zero angles for the left wing."""
        s = np.array([0.0, -1.0, 0.0])
        outer, inner = solve_dual_axis_tracking(s, N0_LEFT)
        n = compute_wing_normal(outer, inner, N0_LEFT)
        np.testing.assert_allclose(n, s, atol=1e-15)
        assert abs(outer) < 1e-10
        assert abs(inner) < 1e-10

    @pytest.mark.parametrize("n0", [N0_RIGHT, N0_LEFT])
    def test_gimbal_lock_sun_along_z(self, n0):
        """Sun along ±Z is a gimbal-lock case; normal should still align."""
        for s in [np.array([0, 0, 1.0]), np.array([0, 0, -1.0])]:
            outer, inner = solve_dual_axis_tracking(s, n0)
            n = compute_wing_normal(outer, inner, n0)
            np.testing.assert_allclose(n, s, atol=1e-10)


# ---- Batch wing arrays test ----


class TestComputeWingArrays:
    def test_cosine_efficiency_in_range(self):
        angles = np.linspace(0, 360, 72, endpoint=False)
        theta = np.radians(angles)
        sx = -np.sin(theta)
        sy = np.zeros_like(theta)
        sz = -np.cos(theta)
        for n0 in [N0_RIGHT, N0_LEFT]:
            result = compute_wing_arrays(sx, sy, sz, n0)
            assert np.all(result["cosine_efficiency"] >= 0.0)
            assert np.all(result["cosine_efficiency"] <= 1.0 + 1e-12)

    def test_normals_are_unit_vectors(self):
        angles = np.linspace(0, 360, 36, endpoint=False)
        theta = np.radians(angles)
        beta = np.radians(30.0)
        sx = -np.sin(theta) * np.cos(beta)
        sy = -np.sin(beta) * np.ones_like(theta)
        sz = -np.cos(theta) * np.cos(beta)
        for n0 in [N0_RIGHT, N0_LEFT]:
            result = compute_wing_arrays(sx, sy, sz, n0)
            norms = np.sqrt(
                result["normal_x"] ** 2
                + result["normal_y"] ** 2
                + result["normal_z"] ** 2
            )
            np.testing.assert_allclose(norms, 1.0, atol=1e-12)

    def test_ideal_tracking_gives_near_unity_cosine(self):
        """With ideal tracking and no eclipse, cosine efficiency should be ~1."""
        angles = np.linspace(0, 360, 72, endpoint=False)
        theta = np.radians(angles)
        sx = -np.sin(theta)
        sy = np.zeros_like(theta)
        sz = -np.cos(theta)
        for n0 in [N0_RIGHT, N0_LEFT]:
            result = compute_wing_arrays(sx, sy, sz, n0)
            np.testing.assert_allclose(
                result["cosine_efficiency"], 1.0, atol=1e-10
            )
            np.testing.assert_allclose(
                result["incidence_deg"], 0.0, atol=1e-8
            )


# ---- ±X (velocity-axis) mounting tests ----


class TestRotationMatrixY:
    def test_ry_identity_at_zero(self):
        R = rotation_matrix_y(0.0)
        np.testing.assert_allclose(R, np.eye(3), atol=1e-15)

    def test_ry_90_deg(self):
        R = rotation_matrix_y(np.pi / 2)
        # Ry(90°) maps [1,0,0] -> [0,0,-1] and [0,0,1] -> [1,0,0]
        v = R @ np.array([1.0, 0.0, 0.0])
        np.testing.assert_allclose(v, [0.0, 0.0, -1.0], atol=1e-15)
        v2 = R @ np.array([0.0, 0.0, 1.0])
        np.testing.assert_allclose(v2, [1.0, 0.0, 0.0], atol=1e-15)

    def test_ry_is_orthogonal(self):
        for angle in [0.0, 0.5, 1.0, np.pi / 4, np.pi / 2, np.pi]:
            Ry = rotation_matrix_y(angle)
            np.testing.assert_allclose(Ry @ Ry.T, np.eye(3), atol=1e-14)
            assert abs(np.linalg.det(Ry) - 1.0) < 1e-14


class TestXMountedTracking:
    @pytest.mark.parametrize("n0", [N0_FORWARD, N0_AFT])
    def test_x_mounted_ideal_tracking_zero_incidence(self, n0):
        """For random sun vectors, ±X tracking should align the normal with the sun."""
        rng = np.random.default_rng(42)
        for _ in range(50):
            s = rng.standard_normal(3)
            s = s / np.linalg.norm(s)
            outer, inner = solve_dual_axis_tracking(s, n0, mounting="x")
            n = compute_wing_normal(outer, inner, n0, mounting="x")
            np.testing.assert_allclose(n, s, atol=1e-10)

    def test_forward_wing_sun_along_x(self):
        """Sun along +X should give zero angles for the forward wing."""
        s = np.array([1.0, 0.0, 0.0])
        outer, inner = solve_dual_axis_tracking(s, N0_FORWARD, mounting="x")
        n = compute_wing_normal(outer, inner, N0_FORWARD, mounting="x")
        np.testing.assert_allclose(n, s, atol=1e-15)
        assert abs(outer) < 1e-10
        assert abs(inner) < 1e-10

    def test_aft_wing_sun_along_neg_x(self):
        """Sun along -X should give zero angles for the aft wing."""
        s = np.array([-1.0, 0.0, 0.0])
        outer, inner = solve_dual_axis_tracking(s, N0_AFT, mounting="x")
        n = compute_wing_normal(outer, inner, N0_AFT, mounting="x")
        np.testing.assert_allclose(n, s, atol=1e-15)
        assert abs(outer) < 1e-10
        assert abs(inner) < 1e-10

    def test_x_mounted_inner_small_at_high_beta(self):
        """At beta=80°, theta=0°, forward wing inner should be small (<15°)."""
        # Sun at beta=80°, theta=0°: sy≈−sin(80°)≈−0.985, sz≈−cos(0°)*cos(80°)≈−0.174
        beta = np.radians(80.0)
        sx = 0.0
        sy = -np.sin(beta)
        sz = -np.cos(beta)
        s = np.array([sx, sy, sz])
        outer, inner = solve_dual_axis_tracking(s, N0_FORWARD, mounting="x")
        assert abs(np.degrees(inner)) < 15.0
        # outer should be near atan2(sy, sx) = atan2(-0.985, 0) = -90°
        assert abs(np.degrees(outer) - (-90.0)) < 5.0

    def test_x_mounted_wing_arrays_unity_cosine(self):
        """With ideal ±X tracking and no eclipse, cosine efficiency should be ~1."""
        angles = np.linspace(0, 360, 72, endpoint=False)
        theta = np.radians(angles)
        sx = -np.sin(theta)
        sy = np.zeros_like(theta)
        sz = -np.cos(theta)
        for n0 in [N0_FORWARD, N0_AFT]:
            result = compute_wing_arrays(sx, sy, sz, n0, mounting="x")
            np.testing.assert_allclose(result["cosine_efficiency"], 1.0, atol=1e-10)
            np.testing.assert_allclose(result["incidence_deg"], 0.0, atol=1e-8)
