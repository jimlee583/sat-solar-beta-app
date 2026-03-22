"""Tests for Version 3 articulation constraint logic."""

import math

import numpy as np
import pytest

from app.models import KeepOutZone
from app.services.constraints import (
    AxisLimits,
    apply_angle_limits,
    apply_rate_limit,
    find_keepout_violation,
    is_in_keepout_zone,
    resolve_keepout_violation,
)


# ---------------------------------------------------------------------------
# Angle-limit clipping
# ---------------------------------------------------------------------------


class TestApplyAngleLimits:
    def test_within_range_no_clip(self):
        val, clipped = apply_angle_limits(45.0, -90.0, 90.0)
        assert val == 45.0
        assert clipped is False

    def test_clip_below_min(self):
        val, clipped = apply_angle_limits(-100.0, -90.0, 90.0)
        assert val == -90.0
        assert clipped is True

    def test_clip_above_max(self):
        val, clipped = apply_angle_limits(200.0, -180.0, 180.0)
        assert val == 180.0
        assert clipped is True

    def test_at_boundary_no_clip(self):
        val, clipped = apply_angle_limits(-90.0, -90.0, 90.0)
        assert val == -90.0
        assert clipped is False

        val, clipped = apply_angle_limits(90.0, -90.0, 90.0)
        assert val == 90.0
        assert clipped is False


# ---------------------------------------------------------------------------
# Rate-limit enforcement
# ---------------------------------------------------------------------------


class TestApplyRateLimit:
    def test_small_step_no_limit(self):
        val, limited = apply_rate_limit(10.0, 10.5, 1.0, 1.0)
        assert val == 10.5
        assert limited is False

    def test_large_step_is_limited(self):
        val, limited = apply_rate_limit(0.0, 10.0, 1.0, 2.0)
        assert val == pytest.approx(2.0)
        assert limited is True

    def test_negative_step_is_limited(self):
        val, limited = apply_rate_limit(0.0, -10.0, 1.0, 3.0)
        assert val == pytest.approx(-3.0)
        assert limited is True

    def test_exact_max_delta_not_limited(self):
        val, limited = apply_rate_limit(0.0, 5.0, 1.0, 5.0)
        assert val == pytest.approx(5.0)
        assert limited is False

    def test_step_to_step_delta_respects_rate(self):
        rate = 2.0
        dt = 0.5
        max_delta = rate * dt
        prev = 10.0
        cmd = 20.0
        val, limited = apply_rate_limit(prev, cmd, rate, dt)
        assert abs(val - prev) <= max_delta + 1e-12
        assert limited is True


# ---------------------------------------------------------------------------
# Keep-out zone detection
# ---------------------------------------------------------------------------


class TestKeepOutZoneDetection:
    def _zone(self) -> KeepOutZone:
        return KeepOutZone(
            wing="right",
            outer_min_deg=-10.0, outer_max_deg=10.0,
            inner_min_deg=-5.0, inner_max_deg=5.0,
            label="test-zone",
        )

    def test_inside_zone(self):
        assert is_in_keepout_zone(0.0, 0.0, self._zone()) is True

    def test_outside_zone(self):
        assert is_in_keepout_zone(20.0, 0.0, self._zone()) is False

    def test_on_boundary_is_inside(self):
        assert is_in_keepout_zone(10.0, 5.0, self._zone()) is True

    def test_find_violation_correct_wing(self):
        zones = [self._zone()]
        violated, label = find_keepout_violation("right", 0.0, 0.0, zones)
        assert violated is True
        assert label == "test-zone"

    def test_find_violation_wrong_wing(self):
        zones = [self._zone()]
        violated, label = find_keepout_violation("left", 0.0, 0.0, zones)
        assert violated is False
        assert label == ""


# ---------------------------------------------------------------------------
# Keep-out resolution
# ---------------------------------------------------------------------------


class TestResolveKeepoutViolation:
    def _limits(self) -> AxisLimits:
        return AxisLimits(outer_min=-180.0, outer_max=180.0,
                          inner_min=-90.0, inner_max=90.0)

    def _zone(self) -> KeepOutZone:
        return KeepOutZone(
            wing="right",
            outer_min_deg=-20.0, outer_max_deg=20.0,
            inner_min_deg=-15.0, inner_max_deg=15.0,
        )

    def test_no_violation_returns_ideal(self):
        o, i, adj, lbl = resolve_keepout_violation(
            "right", 50.0, 50.0, [self._zone()], self._limits(),
        )
        assert o == 50.0
        assert i == 50.0
        assert adj is False

    def test_violation_projects_to_boundary(self):
        o, i, adj, lbl = resolve_keepout_violation(
            "right", 0.0, 0.0, [self._zone()], self._limits(),
        )
        assert adj is True
        violated, _ = find_keepout_violation("right", o, i, [self._zone()])
        assert violated is False

    def test_resolved_point_respects_angle_limits(self):
        tight_limits = AxisLimits(outer_min=-25.0, outer_max=25.0,
                                  inner_min=-20.0, inner_max=20.0)
        o, i, adj, _ = resolve_keepout_violation(
            "right", 5.0, 5.0, [self._zone()], tight_limits,
        )
        assert adj is True
        assert tight_limits.outer_min <= o <= tight_limits.outer_max
        assert tight_limits.inner_min <= i <= tight_limits.inner_max
