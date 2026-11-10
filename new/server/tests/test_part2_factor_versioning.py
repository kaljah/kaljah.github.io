"""
Unit & Regression Tests for Part 2.1: Emission Factor and GWP Set Versioning
===========================================================================
Verifies:
1. Version every emission factor and GWP set (id, valid_from, source, approved_by/at).
2. Editing a factor with references creates a new version; never overwrites.
3. Factor history endpoint returns complete version lineage.
4. GWP standards endpoint returns versioned AR4, AR5, AR6 metadata.
5. Dry-run backfill report exists and verified 0 unapproved database writes.
"""
import os
import json
import pytest
from extensions import db
from models import CustomFactor, Emission
from tests.audit_helpers import make_facility, make_user, login, uniq


def test_custom_factor_versioning_on_update(app, client):
    """Item 2.1: Editing a custom factor with references creates a new version instead of overwriting."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        fac = make_facility(name=uniq("FAC_VER"))

        # 1. Create Initial Custom Factor (v1.0)
        res_create = client.post(
            "/api/custom-factors",
            json={
                "name": uniq("LightFuelGas"),
                "co2_factor": 1.50,
                "ch4_factor": 0.05,
                "n2o_factor": 0.01,
                "unit": "m3",
                "source": "Demo Operator Co. Lab Assay 2024",
                "valid_from": "2024-01-01",
                "version": "1.0",
                "facility_id": fac.id,
            },
        )
        assert res_create.status_code == 201, res_create.get_data(as_text=True)
        factor_id = res_create.json["id"]

        # 2. Attach an emission record to this factor so it has references
        em = Emission(
            facility_id=fac.id,
            year=2024,
            month=6,
            process_type="combustion",
            quantity=1000.0,
            unit="m3",
            custom_factor_id=factor_id,
            factor_version="1.0",
            co2e_total=1500.0,
            status="Verified",
            is_test=False,
        )
        db.session.add(em)
        db.session.commit()

        # 3. Update the custom factor (new test lab assay results)
        res_update = client.put(
            f"/api/custom-factors/{factor_id}",
            json={
                "co2_factor": 1.45,  # Changed value
                "source": "Demo Operator Co. Lab Assay 2025 Rev B",
                "valid_from": "2025-01-01",
            },
        )
        # Should create a new version (201 Created)
        assert res_update.status_code == 201, res_update.get_data(as_text=True)
        update_data = res_update.json
        assert update_data.get("is_new_version") is True
        new_factor_id = update_data["id"]
        assert new_factor_id != factor_id
        assert update_data["version"] in ("1.1", "2.0")

        # 4. Verify old factor is preserved and archived
        old_factor = db.session.get(CustomFactor, factor_id)
        assert old_factor.is_archived is True
        assert old_factor.co2_factor == 1.50  # Values untouched!

        # 5. Verify new factor has parent link and new values
        new_factor = db.session.get(CustomFactor, new_factor_id)
        assert new_factor.parent_factor_id == factor_id
        assert new_factor.co2_factor == 1.45
        assert new_factor.is_archived is False


def test_custom_factor_version_history_lineage(app, client):
    """Item 2.1: Factor history endpoint returns full version lineage."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        fac = make_facility(name=uniq("FAC_HIST"))

        f1 = CustomFactor(
            name=uniq("CrudeOilFactor"),
            version="1.0",
            co2_factor=3.10,
            ch4_factor=0.01,
            n2o_factor=0.001,
            unit="bbl",
            source="API Table 4-1",
            valid_from="2023-01-01",
            created_by=admin.id,
            facility_id=fac.id,
        )
        db.session.add(f1)
        db.session.commit()

        f2 = CustomFactor(
            name=f1.name,
            version="1.1",
            parent_factor_id=f1.id,
            co2_factor=3.05,
            ch4_factor=0.01,
            n2o_factor=0.001,
            unit="bbl",
            source="API Table 4-1 Updated",
            valid_from="2024-01-01",
            created_by=admin.id,
            facility_id=fac.id,
        )
        db.session.add(f2)
        db.session.commit()

        res = client.get(f"/api/custom-factors/{f2.id}/history")
        assert res.status_code == 200
        data = res.json
        assert data["current_id"] == f2.id
        assert len(data["versions"]) >= 2
        versions = [v["version"] for v in data["versions"]]
        assert "1.0" in versions
        assert "1.1" in versions


def test_gwp_standards_endpoint_metadata(app, client):
    """Item 2.1: Versioned GWP standards endpoint returns AR4, AR5, AR6 with metadata."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        res = client.get("/api/custom-factors/gwp-standards")
        assert res.status_code == 200
        standards = res.json

        std_ids = {s["id"] for s in standards}
        assert {"AR4", "AR5", "AR6"}.issubset(std_ids)

        for s in standards:
            assert "name" in s
            assert "valid_from" in s
            assert "source" in s
            assert "approved_by" in s
            assert "factors_100yr" in s
            assert "factors_20yr" in s
            assert s["factors_100yr"]["co2"] == 1.0


def test_dryrun_factor_versioning_backfill_report_exists():
    """Item 2.1: Dry-run factor backfill report exists and verifies zero unapproved mutations."""
    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports", "factor_versioning_backfill_dryrun.json"))
    assert os.path.exists(report_path), f"Dry-run report missing at {report_path}"

    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("records_written") == 0
    assert data.get("records_mutated") == 0
    assert "scope1" in data
    assert "scope2" in data
    assert "scope3" in data
