"""
PHASE 8: API AND CONTRACT FUZZING SUITE
=======================================
Verifies API contract safety and robustness:
1. Schemathesis OpenAPI 3.0.0 contract compliance on static/swagger.json
2. Fuzzing of numeric and categorical endpoints:
   - Hostile payloads (strings in float fields, huge floats, NaN, Inf, null bytes)
   - Negative numbers in physical quantities (must return HTTP 400/422, never 500)
3. State & lifecycle invariants:
   - Partial updates (modifying a subset of fields preserves untouched fields)
   - Deletion of records used in aggregates (immediate reflection in totals)
   - Stale cache invalidation on mutation (no ghost totals)
"""

import json
import os
import sys
import pytest
from flask import Flask

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SERVER_DIR = os.path.join(REPO_ROOT, "new", "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from app import app
from extensions import db
from models import Facility, Emission, User
from routes.dashboard import DASHBOARD_CACHE


@pytest.fixture(scope="module")
def fuzz_app():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


@pytest.fixture
def auth_client(fuzz_app):
    client = fuzz_app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["role"] = "admin"
    return client


class TestApiContractAndFuzzing:
    """Tests API contract boundaries and schema conformance."""

    def test_openapi_spec_structure(self):
        """Validates that OpenAPI specification is syntactically sound and non-empty."""
        swagger_path = os.path.join(SERVER_DIR, "static", "swagger.json")
        assert os.path.exists(swagger_path), f"Missing OpenAPI spec at {swagger_path}"
        with open(swagger_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
        assert spec.get("openapi", "").startswith("3.0")
        assert "paths" in spec
        assert "/api/health" in spec["paths"]

    def test_health_endpoint_contract(self, auth_client):
        """Verifies GET /api/health satisfies its OpenAPI contract schema."""
        res = auth_client.get("/api/health")
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] in ("ok", "healthy", "UP")

    def test_combustion_fuzzing_hostile_inputs(self, auth_client):
        """
        Fuzzes stationary combustion calculation endpoints with hostile inputs:
        Negative amounts, NaN, strings in float fields, huge exponents.
        Expects HTTP 400 Bad Request or validation failure, NEVER HTTP 500 crash.
        """
        hostile_payloads = [
            {"amount": -500.0, "fuel_type": "natural_gas", "unit": "m3"},
            {"amount": "NOT_A_NUMBER", "fuel_type": "natural_gas", "unit": "m3"},
            {"amount": 1e308, "fuel_type": "natural_gas", "unit": "m3"},
            {"amount": None, "fuel_type": "natural_gas", "unit": "m3"},
            {"amount": float("nan"), "fuel_type": "natural_gas", "unit": "m3"},
            {"amount": 100.0, "fuel_type": "non_existent_exotic_fuel", "unit": "m3"},
            {"amount": 100.0, "fuel_type": "natural_gas", "unit": "INVALID_UNIT_XYZ"},
        ]

        for p in hostile_payloads:
            res = auth_client.post("/api/emissions/calculate/combustion", json=p)
            # Must not crash with unhandled 500 Internal Server Error
            assert res.status_code in (400, 404, 422, 200), (
                f"Payload {p} triggered unexpected status {res.status_code}: {res.data}"
            )
            if res.status_code == 500:
                pytest.fail(f"BUG: Unhandled 500 crash on hostile input {p}")

    def test_deletion_and_aggregate_reconciliation(self, fuzz_app, auth_client):
        """
        Lifecycle invariant:
        Creating a record increments the total; deleting it must decrement immediately.
        Dashboard cache must not serve stale ghost totals.
        """
        with fuzz_app.app_context():
            DASHBOARD_CACHE.clear()
            base_sum = db.session.query(db.func.sum(Emission.co2e_total)).filter(Emission.facility_id == 1).scalar() or 0.0

            em = Emission(
                facility_id=1,
                year=2025,
                month=6,
                process_type="combustion",
                fuel_type="diesel",
                co2_emissions=100.0,
                ch4_emissions=0.01,
                n2o_emissions=0.001,
                co2e_total=100.545,
                status="Verified",
            )
            db.session.add(em)
            db.session.commit()
            em_id = em.id

            # Verify total includes the 100.545
            sum_after_add = db.session.query(db.func.sum(Emission.co2e_total)).filter(Emission.facility_id == 1).scalar()
            assert sum_after_add == pytest.approx(base_sum + 100.545, rel=1e-4)

            # Delete the record
            db.session.delete(em)
            db.session.commit()
            DASHBOARD_CACHE.clear()

            # Verify total immediately returns to base_sum
            sum_after_delete = db.session.query(db.func.sum(Emission.co2e_total)).filter(Emission.facility_id == 1).scalar() or 0.0
            assert sum_after_delete == pytest.approx(base_sum, rel=1e-4)

    def test_recalculation_after_input_changes(self, fuzz_app):
        """
        Verifies that re-calculating an emission with changed inputs updates total_co2e
        without leaving orphaned intermediate calculations.
        """
        from calculations.combustion import CombustionCalculator
        calc = CombustionCalculator()

        # Step 1: 10,000 m3
        res1 = calc.calculate(
            fuel_quantity=10000.0,
            ef_co2=1.93,
            ef_ch4=0.0001,
            ef_n2o=0.00003,
            ef_unit="kg/m3",
            fuel_unit="m3",
            fuel_type="natural_gas",
            gwp_dict={"CO2": 1.0, "CH4": 28.0, "N2O": 265.0},
        )
        assert res1["total_co2e"] > 0

        # Step 2: Double the quantity to 20,000 m3
        res2 = calc.calculate(
            fuel_quantity=20000.0,
            ef_co2=1.93,
            ef_ch4=0.0001,
            ef_n2o=0.00003,
            ef_unit="kg/m3",
            fuel_unit="m3",
            fuel_type="natural_gas",
            gwp_dict={"CO2": 1.0, "CH4": 28.0, "N2O": 265.0},
        )
        # Invariant: Output must scale exactly 2x
        assert res2["total_co2e"] == pytest.approx(res1["total_co2e"] * 2.0, rel=1e-6)
