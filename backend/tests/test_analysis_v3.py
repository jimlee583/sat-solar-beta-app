"""Smoke and integration tests for the V3 analysis endpoint."""

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestAnalyzeV3Endpoint:
    def test_v3_default_request(self):
        resp = client.post("/api/analyze/v3", json={})
        assert resp.status_code == 200
        data = resp.json()

        # V1 fields present
        assert "orbit_radius_km" in data
        assert "orbital_period_s" in data
        assert len(data["orbit_angle_deg"]) == 360

        # V3 ideal fields present (V2-named duplicates removed)
        assert len(data["right_ideal_outer_angle_deg"]) == 360
        assert len(data["left_ideal_power_w"]) == 360
        assert len(data["ideal_total_power_w"]) == 360

        # V3 achieved fields present
        assert len(data["right_achieved_outer_angle_deg"]) == 360
        assert len(data["left_achieved_outer_angle_deg"]) == 360
        assert len(data["right_achieved_power_w"]) == 360
        assert len(data["achieved_total_power_w"]) == 360

        # V3 summary metrics
        assert data["average_ideal_total_power_w"] > 0
        assert data["average_achieved_total_power_w"] > 0
        assert 0 < data["achieved_vs_ideal_energy_ratio"] <= 1.0 + 1e-9

        # V2-named duplicate array fields must no longer be present
        assert "right_outer_angle_deg" not in data
        assert "total_power_w" not in data

    def test_v3_with_defaults_achieved_equals_ideal(self):
        """With wide angle limits and no keep-out zones, achieved should match ideal."""
        resp = client.post("/api/analyze/v3", json={
            "outer_rate_limit_deg_per_s": 1000.0,
            "inner_rate_limit_deg_per_s": 1000.0,
        })
        assert resp.status_code == 200
        data = resp.json()

        np.testing.assert_allclose(
            data["right_achieved_outer_angle_deg"],
            data["right_ideal_outer_angle_deg"],
            atol=1e-6,
        )
        np.testing.assert_allclose(
            data["left_achieved_inner_angle_deg"],
            data["left_ideal_inner_angle_deg"],
            atol=1e-6,
        )
        assert abs(data["achieved_vs_ideal_energy_ratio"] - 1.0) < 1e-4

    def test_v3_eclipse_zeroes_achieved_power(self):
        resp = client.post("/api/analyze/v3", json={"beta_deg": 0})
        assert resp.status_code == 200
        data = resp.json()
        eclipse_indices = [i for i, e in enumerate(data["in_eclipse"]) if e]
        assert len(eclipse_indices) > 0
        for i in eclipse_indices:
            assert data["right_achieved_power_w"][i] == 0.0
            assert data["left_achieved_power_w"][i] == 0.0
            assert data["achieved_total_power_w"][i] == 0.0

    def test_v3_achieved_total_equals_wing_sum(self):
        resp = client.post("/api/analyze/v3", json={})
        data = resp.json()
        for i in range(len(data["achieved_total_power_w"])):
            expected = data["left_achieved_power_w"][i] + data["right_achieved_power_w"][i]
            assert abs(data["achieved_total_power_w"][i] - expected) < 1e-6

    def test_v3_achieved_respects_angle_limits(self):
        resp = client.post("/api/analyze/v3", json={
            "right_outer_min_deg": -45.0,
            "right_outer_max_deg": 45.0,
            "right_inner_min_deg": -30.0,
            "right_inner_max_deg": 30.0,
            "left_outer_min_deg": -45.0,
            "left_outer_max_deg": 45.0,
            "left_inner_min_deg": -30.0,
            "left_inner_max_deg": 30.0,
        })
        assert resp.status_code == 200
        data = resp.json()

        for val in data["right_achieved_outer_angle_deg"]:
            assert -45.0 - 1e-9 <= val <= 45.0 + 1e-9
        for val in data["right_achieved_inner_angle_deg"]:
            assert -30.0 - 1e-9 <= val <= 30.0 + 1e-9
        for val in data["left_achieved_outer_angle_deg"]:
            assert -45.0 - 1e-9 <= val <= 45.0 + 1e-9
        for val in data["left_achieved_inner_angle_deg"]:
            assert -30.0 - 1e-9 <= val <= 30.0 + 1e-9

    def test_v3_rate_limit_constrains_step_size(self):
        rate = 0.5  # deg/s
        resp = client.post("/api/analyze/v3", json={
            "num_samples_per_orbit": 72,
            "outer_rate_limit_deg_per_s": rate,
            "inner_rate_limit_deg_per_s": rate,
        })
        assert resp.status_code == 200
        data = resp.json()

        T_s = data["orbital_period_s"]
        dt_s = T_s / 72
        max_delta = rate * dt_s

        for key in ["right_achieved_outer_angle_deg", "right_achieved_inner_angle_deg",
                     "left_achieved_outer_angle_deg", "left_achieved_inner_angle_deg"]:
            arr = data[key]
            for i in range(1, len(arr)):
                delta = abs(arr[i] - arr[i - 1])
                assert delta <= max_delta + 1e-9, (
                    f"{key}[{i}]: delta={delta:.6f} > max_delta={max_delta:.6f}"
                )

    def test_v3_with_keepout_zone(self):
        zones = [{
            "wing": "right",
            "outer_min_deg": -5.0,
            "outer_max_deg": 5.0,
            "inner_min_deg": -5.0,
            "inner_max_deg": 5.0,
            "label": "thruster-plume",
        }]
        resp = client.post("/api/analyze/v3", json={
            "keepout_zones": zones,
            "outer_rate_limit_deg_per_s": 100.0,
            "inner_rate_limit_deg_per_s": 100.0,
        })
        assert resp.status_code == 200
        data = resp.json()

        # With high rate limits the achieved angle should never be in the zone
        for i in range(len(data["right_achieved_outer_angle_deg"])):
            o = data["right_achieved_outer_angle_deg"][i]
            inn = data["right_achieved_inner_angle_deg"][i]
            inside = -5.0 <= o <= 5.0 and -5.0 <= inn <= 5.0
            assert not inside, (
                f"Achieved angles ({o:.4f}, {inn:.4f}) inside keep-out zone at sample {i}"
            )

    def test_v3_ideal_tracking_loss_zero_for_no_eclipse_orbit(self):
        """With beta above critical and no constraints, ideal tracking loss should be ~0%.

        This verifies the sunlit-only loss metric does not conflate eclipse
        unavailability with pointing quality.
        """
        # beta=75° is well above critical_beta (~66.7°) for 500 km — fully sunlit orbit.
        resp = client.post("/api/analyze/v3", json={
            "beta_deg": 75.0,
            "outer_rate_limit_deg_per_s": 1000.0,
            "inner_rate_limit_deg_per_s": 1000.0,
        })
        assert resp.status_code == 200
        data = resp.json()

        assert data["eclipse_fraction"] == 0.0, "Expected no eclipse at beta=75°"
        # Ideal tracker with no constraints should lose nothing during sunlit passes
        assert data["ideal_tracking_loss_percent"] == pytest.approx(0.0, abs=0.1), (
            f"ideal_tracking_loss_percent={data['ideal_tracking_loss_percent']:.4f}% "
            "— should be ~0% for a perfect tracker with no eclipse"
        )

    def test_v3_rate_limit_keepout_achieved_stays_outside(self):
        """T1: Rate-limited achieved angles must not enter a keep-out zone.

        Uses a tight rate limit (0.1 deg/s) and a wide keep-out zone that the
        ideal angles cross.  Before the C1/C2 fix, the achieved angle could
        be rate-limited into the zone; after the fix in_keepout reflects the
        achieved position and the achieved angle itself must be outside.
        """
        # Keep-out zone centred on the subsolar direction (outer~0, inner~0),
        # which the ideal angles pass through at beta=0.
        zones = [{
            "wing": "right",
            "outer_min_deg": -15.0,
            "outer_max_deg": 15.0,
            "inner_min_deg": -15.0,
            "inner_max_deg": 15.0,
            "label": "centre-zone",
        }]
        resp = client.post("/api/analyze/v3", json={
            "beta_deg": 0.0,
            "num_samples_per_orbit": 360,
            "keepout_zones": zones,
            # Tight rate limit — gives plenty of opportunity for rate-limited re-entry
            "outer_rate_limit_deg_per_s": 0.1,
            "inner_rate_limit_deg_per_s": 0.1,
        })
        assert resp.status_code == 200
        data = resp.json()

        for i in range(len(data["right_achieved_outer_angle_deg"])):
            o = data["right_achieved_outer_angle_deg"][i]
            inn = data["right_achieved_inner_angle_deg"][i]
            inside = -15.0 <= o <= 15.0 and -15.0 <= inn <= 15.0
            # The in_keepout flag must agree with whether achieved is actually inside
            assert data["right_in_keepout"][i] == inside, (
                f"in_keepout flag mismatch at sample {i}: "
                f"flag={data['right_in_keepout'][i]}, inside={inside}, "
                f"angles=({o:.4f}, {inn:.4f})"
            )

    def test_v1_and_v2_still_work(self):
        resp1 = client.post("/api/analyze/v1", json={})
        assert resp1.status_code == 200
        resp2 = client.post("/api/analyze/v2", json={})
        assert resp2.status_code == 200
