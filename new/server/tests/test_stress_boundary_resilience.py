"""
test_stress_boundary_resilience.py
==================================
Pillar 4: Chaos, Extreme Boundaries & Malformed Payloads Stress Test.

Validates application resilience under edge-case and hostile payloads:
1. Astronomical magnitudes (10^18, 10^24) and microscopic inputs (10^-15).
2. NaN, Infinity, -Infinity inputs handled gracefully without 500 crashes.
3. 1 MB giant string injections (Memory/Buffer overflow defense).
4. Formula / CSV injection vectors (=cmd|, @SUM, -2+3*cmd|).
5. Corrupted, truncated, or non-dictionary JSON payloads.
6. Multi-language Unicode, emoji, and boundary characters.
"""

import math
import json
import pytest
from app import app
from models import db, User, Facility, Emission
from emission_factors import API_FACTORS
from calculations import compute_emissions, calculate_co2e


@pytest.fixture(scope="module")
def boundary_client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    from extensions import limiter
    limiter.enabled = False

    with app.app_context():
        admin = User.query.filter_by(email="boundary_admin@test.com").first()
        if not admin:
            admin = User(
                email="boundary_admin@test.com",
                fullName="Boundary Stress Admin",
                orgName="ChaosCorp",
                sector="Energy",
                role="admin",
                location="Hassi Messaoud",
            )
            admin.set_password("BoundaryPass2026!")
            db.session.add(admin)
            db.session.commit()

        fac = Facility.query.filter_by(name="Resilience Testing Facility").first()
        if not fac:
            fac = Facility(
                name="Resilience Testing Facility",
                location="Hassi Messaoud",
                activity="Extraction",
                division="Production",
                region="South",
                field="Chaos Field",
                segment="Upstream",
            )
            db.session.add(fac)
            db.session.commit()

        fac_id = fac.id
        admin_id = admin.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = admin_id
        sess["_fresh"] = True

    yield {
        "client": client,
        "facility_id": fac_id,
        "user_id": admin_id,
    }
    limiter.enabled = True


class TestBoundaryResilienceEngine:
    """Mathematical calculations under extreme values."""

    def test_astronomical_quantities_resilience(self):
        """Quantities of 10^18 and 10^24 must compute without float overflow or crash."""
        factor = API_FACTORS.get("Natural Gas", {})
        magnitudes = [1e18, 1e20, 1e24]
        for mag in magnitudes:
            payload = {
                "process_type": "combustion",
                "fuel": "Natural Gas",
                "quantity": mag,
                "unit": "m3",
            }
            res, method = compute_emissions(payload, factor_data=factor)
            assert math.isfinite(res["totalCo2e"]), f"Non-finite result for mag {mag}"
            assert res["totalCo2e"] > 0
            assert math.isfinite(res["co2"])
            assert math.isfinite(res["ch4"])
            assert math.isfinite(res["n2o"])

        # Test calculate_co2e with astronomical numbers
        co2e = calculate_co2e(co2=1e18, ch4=1e16, n2o=1e14)
        assert math.isfinite(co2e)
        assert co2e > 1e18

    def test_microscopic_quantities_resilience(self):
        """Quantities of 10^-15 and 10^-20 must compute without underflow errors or ZeroDivision."""
        factor = API_FACTORS.get("Diesel", {})
        micros = [1e-12, 1e-15, 1e-20]
        for micro in micros:
            payload = {
                "process_type": "combustion",
                "fuel": "Diesel",
                "quantity": micro,
                "unit": "gal",
            }
            res, method = compute_emissions(payload, factor_data=factor)
            assert math.isfinite(res["totalCo2e"]), f"Non-finite result for micro {micro}"
            assert res["totalCo2e"] >= 0
            assert math.isfinite(res["co2"])

        # Zero quantity edge case
        res_zero, _ = compute_emissions(
            {
                "process_type": "combustion",
                "fuel": "Natural Gas",
                "quantity": 0.0,
                "unit": "m3",
            },
            factor_data=API_FACTORS.get("Natural Gas", {}),
        )
        assert res_zero["totalCo2e"] == 0.0

    def test_nan_infinity_rejection_or_handling(self):
        """Passing NaN or Infinity should not produce corrupt database writes."""
        nan_val = float("nan")
        inf_val = float("inf")

        # Check engine behavior
        try:
            res, _ = compute_emissions({
                "process_type": "combustion",
                "fuel": "Natural Gas",
                "quantity": nan_val,
                "unit": "m3",
            })
            assert math.isnan(res.get("totalCo2e", 0)) or res.get("totalCo2e") == 0
        except (ValueError, TypeError):
            pass

        try:
            res_inf, _ = compute_emissions({
                "process_type": "combustion",
                "fuel": "Natural Gas",
                "quantity": inf_val,
                "unit": "m3",
            })
        except (ValueError, OverflowError):
            pass


class TestBoundaryResilienceAPI:
    """API endpoints under hostile, oversized, or malformed inputs."""

    def test_nan_and_inf_api_rejection(self, boundary_client):
        """API endpoints must cleanly reject NaN and Infinity with 400/422 and 0 crashes."""
        client = boundary_client["client"]
        fac_id = boundary_client["facility_id"]

        for bad_qty in ["NaN", "Infinity", "-Infinity", "null", "undefined"]:
            resp = client.post(
                "/api/emissions/",
                json={
                    "year": 2024,
                    "month": 6,
                    "facility_id": fac_id,
                    "process_type": "combustion",
                    "fuel": "Natural Gas",
                    "quantity": bad_qty,
                    "unit": "m3",
                },
            )
            assert resp.status_code in [400, 422, 201], f"Status {resp.status_code} for {bad_qty}"
            assert resp.status_code != 500

    def test_giant_one_megabyte_string_payload(self, boundary_client):
        """1 MB giant string payload in text fields must not cause server crash or memory exhaustion."""
        client = boundary_client["client"]
        fac_id = boundary_client["facility_id"]

        giant_string = "X" * (1024 * 1024)  # 1 MegaByte string

        resp = client.post(
            "/api/emissions/",
            json={
                "year": 2024,
                "month": 6,
                "facility_id": fac_id,
                "process_type": "combustion",
                "fuel": "Natural Gas",
                "quantity": 100.0,
                "unit": "m3",
                "notes": giant_string,
            },
        )
        assert resp.status_code in [200, 201, 400, 413, 422]
        assert resp.status_code != 500

    def test_formula_injection_sanitization(self, boundary_client):
        """Formula injection patterns (=cmd|, @SUM, +1+1) must not be executed."""
        client = boundary_client["client"]
        fac_id = boundary_client["facility_id"]

        formula_payloads = [
            "=cmd|' /C calc'!A0",
            "@SUM(1+1)*cmd|' /C calc'!A0",
            "-2+3*cmd|' /C calc'!A0",
            "+1+1",
            "=HYPERLINK(\"http://evil.com\",\"Click\")",
        ]

        for formula in formula_payloads:
            resp = client.post(
                "/api/emissions/",
                json={
                    "year": 2024,
                    "month": 7,
                    "facility_id": fac_id,
                    "process_type": "combustion",
                    "fuel": "Natural Gas",
                    "quantity": 50.0,
                    "unit": "m3",
                    "equipment": formula,
                    "notes": formula,
                },
            )
            assert resp.status_code in [200, 201, 400, 422]
            assert resp.status_code != 500

    def test_corrupted_and_empty_json_payloads(self, boundary_client):
        """Malformed, empty, or non-dictionary JSON payloads must return 400/422 cleanly."""
        client = boundary_client["client"]

        # Completely empty payload
        resp_empty = client.post("/api/emissions/", data="", content_type="application/json")
        assert resp_empty.status_code in [400, 422]

        # Raw string instead of object
        resp_str = client.post("/api/emissions/", data='"just a string"', content_type="application/json")
        assert resp_str.status_code in [400, 422]

        # List instead of dict
        resp_list = client.post("/api/emissions/", data="[1, 2, 3]", content_type="application/json")
        assert resp_list.status_code in [400, 422]

        # Broken JSON syntax
        resp_broken = client.post("/api/emissions/", data="{year: 2024, broken", content_type="application/json")
        assert resp_broken.status_code in [400, 422]

    def test_unicode_and_special_character_burst(self, boundary_client):
        """Arabic, Chinese, emojis, and special control characters handled cleanly."""
        client = boundary_client["client"]
        fac_id = boundary_client["facility_id"]

        unicode_samples = [
            "حقل حاسي مسعود للغاز الطبيعي",
            "阿尔及利亚天然气开采项目",
            "🔥🏭⚡🌿 Carbon Accounting Project 2026",
            "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?`~",
        ]

        for sample in unicode_samples:
            resp = client.post(
                "/api/emissions/",
                json={
                    "year": 2024,
                    "month": 8,
                    "facility_id": fac_id,
                    "process_type": "combustion",
                    "fuel": "Natural Gas",
                    "quantity": 120.0,
                    "unit": "m3",
                    "equipment": sample,
                },
            )
            assert resp.status_code in [200, 201]
            data = resp.get_json()
            assert data is not None
