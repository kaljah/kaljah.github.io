"""Regression tests for Part 1.9: Junk and test data.

Requirements:
- Required-field validation: reject empty or "None", "null", "undefined" names across facilities, sources, mitigation, custom factors.
- is_test flag excludes test data from production dashboards, reports, and ledger.
- Dry-run report generated without modifying or auto-deleting records.
"""
import os
import json
import pytest
from tests.audit_helpers import make_facility, make_user, login, uniq
from models import Facility, EmissionSource, CustomFactor, MitigationProject, Emission


def test_required_name_validation_rejects_none_and_empty(client, app):
    with app.app_context():
        admin = make_user("admin")
        fac = make_facility(name=uniq("FAC_VALID"))
        login(client, admin)

        # 1. Facility name cannot be empty or 'None'
        res = client.post("/api/facilities", json={"name": "None", "region": "North"})
        assert res.status_code in (400, 422)

        res_empty = client.post("/api/facilities", json={"name": "   ", "region": "North"})
        assert res_empty.status_code in (400, 422)

        # 2. Emission source name cannot be 'None' or empty
        res_src = client.post("/api/sources", json={"facility_id": fac.id, "name": "None", "type": "combustion"})
        assert res_src.status_code == 400

        res_src_empty = client.post("/api/sources", json={"facility_id": fac.id, "name": "  ", "type": "combustion"})
        assert res_src_empty.status_code == 400

        # 3. Custom factor name cannot be 'None' or empty
        res_fac = client.post("/api/custom-factors", json={"name": "None", "unit": "kg/scf", "co2_factor": 1.5})
        assert res_fac.status_code == 400

        res_fac_empty = client.post("/api/custom-factors", json={"name": "", "unit": "kg/scf", "co2_factor": 1.5})
        assert res_fac_empty.status_code == 400

        # 4. Mitigation project name cannot be 'None' or empty
        res_mit = client.post("/api/mitigation", json={"facility_id": fac.id, "name": "None", "year": 2026, "quantity_tco2e": 500})
        assert res_mit.status_code == 400

        res_mit_empty = client.post("/api/mitigation", json={"facility_id": fac.id, "name": "  ", "year": 2026, "quantity_tco2e": 500})
        assert res_mit_empty.status_code == 400


def test_is_test_flag_excludes_test_data_from_emissions_ledger(client, app):
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        # Create a production facility and a test facility
        prod_fac = make_facility(name=uniq("FAC_PROD"))
        test_fac = make_facility(name=uniq("FAC_TEST"), is_test=True)

        # Create emissions under both facilities
        e_prod = Emission(
            record_id=uniq("REC_PROD"),
            facility_id=prod_fac.id,
            year=2026,
            month=5,
            quantity=100.0,
            unit="m3",
            co2e_total=250.0,
            status="Verified",
            is_test=False,
        )
        e_test = Emission(
            record_id=uniq("REC_TEST"),
            facility_id=test_fac.id,
            year=2026,
            month=5,
            quantity=100.0,
            unit="m3",
            co2e_total=250.0,
            status="Verified",
            is_test=True,
        )
        from extensions import db
        db.session.add_all([e_prod, e_test])
        db.session.commit()

        # Query production ledger (include_test=False by default)
        res = client.get("/api/emissions?year=2026&month=5")
        assert res.status_code == 200
        data = res.get_json()
        ids = [rec["id"] for rec in data.get("emissions", [])]

        assert f"s1_{e_prod.id}" in ids
        assert f"s1_{e_test.id}" not in ids


def test_junk_data_dryrun_report_exists():
    report_path = "new/server/reports/junk_test_data_dryrun.json"
    assert os.path.exists(report_path)
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "facilities" in data
    assert "emission_sources" in data
    assert "custom_factors" in data
    assert "users" in data
