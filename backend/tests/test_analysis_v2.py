"""Smoke test for the V2 analysis endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestAnalyzeV2Endpoint:
    def test_v2_default_request(self):
        resp = client.post("/api/analyze/v2", json={})
        assert resp.status_code == 200
        data = resp.json()

        # V1 fields present
        assert "orbit_radius_km" in data
        assert "orbital_period_s" in data
        assert "eclipse_fraction" in data
        assert len(data["orbit_angle_deg"]) == 360

        # V2 wing fields present
        assert len(data["right_outer_angle_deg"]) == 360
        assert len(data["left_outer_angle_deg"]) == 360
        assert len(data["right_power_w"]) == 360
        assert len(data["left_power_w"]) == 360
        assert len(data["total_power_w"]) == 360

        # V2 summary fields
        assert data["average_total_power_w"] > 0
        assert data["peak_total_power_w"] > 0
        assert data["percent_of_required_bus_power_avg"] > 0

    def test_v2_custom_request(self):
        resp = client.post("/api/analyze/v2", json={
            "altitude_km": 400,
            "beta_deg": 30,
            "num_samples_per_orbit": 72,
            "solar_array_area_m2_per_wing": 10.0,
            "solar_cell_efficiency": 0.28,
            "degradation_factor": 0.90,
            "required_bus_power_w": 5000.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["orbit_angle_deg"]) == 72
        assert data["average_total_power_w"] > 0

    def test_v1_endpoint_still_works(self):
        """V1 backward compatibility."""
        resp = client.post("/api/analyze/v1", json={"altitude_km": 500})
        assert resp.status_code == 200
        data = resp.json()
        assert "orbit_radius_km" in data
        assert "right_power_w" not in data  # V2 fields absent from V1

    def test_v2_eclipse_zeroes_power(self):
        """At beta=0 there should be eclipse samples with zero power."""
        resp = client.post("/api/analyze/v2", json={"beta_deg": 0})
        assert resp.status_code == 200
        data = resp.json()
        eclipse_indices = [i for i, e in enumerate(data["in_eclipse"]) if e]
        assert len(eclipse_indices) > 0
        for i in eclipse_indices:
            assert data["right_power_w"][i] == 0.0
            assert data["left_power_w"][i] == 0.0
            assert data["total_power_w"][i] == 0.0

    def test_v2_total_equals_wing_sum(self):
        resp = client.post("/api/analyze/v2", json={})
        data = resp.json()
        for i in range(len(data["total_power_w"])):
            expected = data["left_power_w"][i] + data["right_power_w"][i]
            assert abs(data["total_power_w"][i] - expected) < 1e-6
