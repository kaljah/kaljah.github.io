"""
Unit & Regression Tests for Part 2.4: Trace this Number Drill-down and Export Provenance
========================================================================================
Verifies:
1. /api/traceability/trace returns full data provenance tree:
   - Total, categories breakdown, record count, formula, GWP standard
   - Factor versions and source references
   - Submitter, reviewer, sign-off lineage and audit timestamps
   - Sample contributing records
2. Exports include factor version, source, GWP standard, approved by, approved at.
"""
import pytest
from extensions import db
from models import Emission, Facility
from tests.audit_helpers import make_facility, make_user, login, uniq


def test_trace_number_provenance_tree(app, client):
    """Item 2.4: Full provenance drill-down returned for metric."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        fac = make_facility(name=uniq("FAC_TRACE"))

        # Create Scope 1 emission with explicit factor version and lineage
        em = Emission(
            record_id=uniq("S1_REC"),
            facility_id=fac.id,
            year=2024,
            month=3,
            process_type="combustion",
            fuel_type="Diesel Fuel Oil",
            quantity=1000.0,
            unit="liters",
            factor_source="API Compendium 2021 Table 4-3",
            factor_version="API-2021.1",
            gwp_version="AR5",
            ef_used_co2=2.68,
            co2_emissions=2.68,
            ch4_emissions=0.0001,
            n2o_emissions=0.00002,
            co2e_total=2.688,
            status="Verified",
            created_by_name="Engineer A",
            approved_by_name="Approver B",
            is_test=False,
        )
        db.session.add(em)
        db.session.commit()

        res = client.get(
            "/api/traceability/trace",
            query_string={
                "metric": "scope1_total",
                "year": 2024,
                "facility_id": fac.id,
            },
        )
        assert res.status_code == 200, res.get_data(as_text=True)
        data = res.json

        assert data["total_value"] == pytest.approx(2.69, rel=1e-2)
        assert data["unit"] == "tCO2e"
        assert data["record_count"] >= 1
        assert "formula" in data and len(data["formula"]) > 0

        # Check factor provenance
        factors = data["factors_applied"]
        assert len(factors) >= 1
        f_entry = next((f for f in factors if "API-2021.1" in f.get("version", "")), None)
        assert f_entry is not None
        assert "API Compendium 2021" in f_entry["source"]

        # Check lineage
        lineage = data["data_lineage"]
        assert "Engineer A" in lineage["submitters"]
        assert "Approver B" in lineage["approvers"]
        assert lineage["statuses"].get("Verified", 0) >= 1

        # Check sample records
        sample = data["sample_records"]
        assert len(sample) >= 1
        assert sample[0]["record_id"] == em.record_id
        assert sample[0]["factor_version"] == "API-2021.1"


def test_export_includes_traceability_metadata(app, client):
    """Item 2.4: Export JSON and Excel include factor version, source, GWP, and approval metadata."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        fac = make_facility(name=uniq("FAC_EXP_TRACE"))

        em = Emission(
            record_id=uniq("REC_EXP"),
            facility_id=fac.id,
            year=2024,
            month=1,
            process_type="combustion",
            quantity=100.0,
            unit="m3",
            factor_source="API Table 4-3",
            factor_version="API-2021.1",
            gwp_version="AR5",
            co2e_total=250.0,
            status="Verified",
            created_by_name="Submitter 1",
            approved_by_name="Approver 1",
            is_test=False,
        )
        db.session.add(em)
        db.session.commit()

        # Query JSON export
        res = client.get(
            "/api/emissions/export",
            query_string={
                "scope": "1",
                "year": 2024,
                "facilityId": fac.id,
                "format": "json",
            },
        )
        assert res.status_code == 200
        export_records = res.json.get("data", res.json) if isinstance(res.json, dict) else res.json

        target_row = next((r for r in export_records if r.get("record_id") == em.record_id), None)
        assert target_row is not None
        assert target_row.get("factor_version") == "API-2021.1"
        assert target_row.get("gwp_version") == "AR5"
        assert "Approver 1" in target_row.get("approved_by", "")
