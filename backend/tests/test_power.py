"""Tests for the solar power generation module."""

import numpy as np

from app.services.constants import SOLAR_CONSTANT_W_M2
from app.services.power import compute_power_summary, compute_wing_power


class TestComputeWingPower:
    def test_eclipse_forces_power_to_zero(self):
        cos_eff = np.array([1.0, 1.0, 1.0, 1.0])
        in_eclipse = np.array([False, True, True, False])
        power = compute_wing_power(cos_eff, in_eclipse, 5.0, 0.30, 0.85)
        assert power[0] > 0
        assert power[1] == 0.0
        assert power[2] == 0.0
        assert power[3] > 0

    def test_power_is_non_negative(self):
        cos_eff = np.array([0.0, 0.5, 1.0, 0.0])
        in_eclipse = np.array([False, False, False, True])
        power = compute_wing_power(cos_eff, in_eclipse, 5.0, 0.30, 0.85)
        assert np.all(power >= 0.0)

    def test_known_power_value(self):
        """P = 1361 * 5.0 * 0.30 * 0.85 * 1.0 = 1735.275 W for full illumination."""
        cos_eff = np.array([1.0])
        in_eclipse = np.array([False])
        power = compute_wing_power(cos_eff, in_eclipse, 5.0, 0.30, 0.85)
        expected = SOLAR_CONSTANT_W_M2 * 5.0 * 0.30 * 0.85
        np.testing.assert_allclose(power[0], expected, rtol=1e-10)

    def test_cosine_scales_power(self):
        cos_eff = np.array([1.0, 0.5, 0.0])
        in_eclipse = np.array([False, False, False])
        power = compute_wing_power(cos_eff, in_eclipse, 5.0, 0.30, 0.85)
        np.testing.assert_allclose(power[1], power[0] * 0.5, rtol=1e-10)
        assert power[2] == 0.0


class TestComputePowerSummary:
    def test_total_equals_sum_of_wings(self):
        left = np.array([100.0, 200.0, 0.0, 150.0])
        right = np.array([100.0, 200.0, 0.0, 150.0])
        summary = compute_power_summary(
            left, right, 3000.0,
            np.array([0.0, 0.0, 90.0, 0.0]),
            np.array([0.0, 0.0, 90.0, 0.0]),
        )
        expected_avg = float(np.mean(left + right))
        assert abs(summary["average_total_power_w"] - expected_avg) < 1e-10
        assert abs(
            summary["average_total_power_w"]
            - summary["average_left_power_w"]
            - summary["average_right_power_w"]
        ) < 1e-10

    def test_peak_and_min(self):
        left = np.array([0.0, 100.0, 200.0])
        right = np.array([0.0, 150.0, 300.0])
        summary = compute_power_summary(
            left, right, 3000.0,
            np.array([90.0, 10.0, 0.0]),
            np.array([90.0, 5.0, 0.0]),
        )
        assert summary["peak_total_power_w"] == 500.0
        assert summary["min_total_power_w"] == 0.0

    def test_percent_of_bus_power(self):
        left = np.array([1500.0, 1500.0])
        right = np.array([1500.0, 1500.0])
        summary = compute_power_summary(
            left, right, 3000.0,
            np.array([0.0, 0.0]),
            np.array([0.0, 0.0]),
        )
        assert abs(summary["percent_of_required_bus_power_avg"] - 100.0) < 1e-10

    def test_incidence_extremes(self):
        left = np.array([100.0, 200.0])
        right = np.array([100.0, 200.0])
        left_inc = np.array([5.0, 45.0])
        right_inc = np.array([10.0, 30.0])
        summary = compute_power_summary(left, right, 3000.0, left_inc, right_inc)
        assert summary["max_left_incidence_deg"] == 45.0
        assert summary["min_left_incidence_deg"] == 5.0
        assert summary["max_right_incidence_deg"] == 30.0
        assert summary["min_right_incidence_deg"] == 10.0
