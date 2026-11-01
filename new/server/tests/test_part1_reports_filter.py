"""Regression tests for Part 1.10: Reports filter.

Requirements:
- "Verified records only" shows ONLY Verified rows (no Pending rows).
- "Verified and pending records" shows both Verified and Pending rows.
- Total records count strictly matches active status filters.
"""
import pytest
from tests.audit_helpers import make_facility, make_user, login, uniq
from models import Emission, Scope2Emission, Scope3Emission
from extensions import db


def test_reports_filter_verified_only_excludes_pending(client, app):
    with app.app_context():
        admin = make_user("admin")
        fac = make_facility(name=uniq("FAC_REP"))
        login(client, admin)

        # Create 1 Verified and 1 Pending Scope 1 record
        e_ver = Emission(
            record_id=uniq("REC_VER"),
            facility_id=fac.id,
            year=2026,
            month=6,
            quantity=100.0,
            co2e_total=200.0,
            status="Verified",
            is_test=False,
        )
        e_pend = Emission(
            record_id=uniq("REC_PEND"),
            facility_id=fac.id,
            year=2026,
            month=6,
            quantity=100.0,
            co2e_total=200.0,
            status="Pending",
            is_test=False,
        )
        # Create 1 Verified and 1 Pending Scope 2 record
        s2_ver = Scope2Emission(
            facility_id=fac.id,
            year=2026,
            month=6,
            electricity_kwh=1000.0,
            co2e=150.0,
            status="Verified",
        )
        s2_pend = Scope2Emission(
            facility_id=fac.id,
            year=2026,
            month=6,
            electricity_kwh=1000.0,
            co2e=150.0,
            status="Pending",
        )
        db.session.add_all([e_ver, e_pend, s2_ver, s2_pend])
        db.session.commit()

        # 1. Query with status=Verified
        res_ver = client.get(f"/api/emissions?facility_id={fac.id}&year=2026&month=6&status=Verified")
        assert res_ver.status_code == 200
        data_ver = res_ver.get_json()
        assert data_ver["total"] == 2  # 1 Scope 1 + 1 Scope 2
        statuses_ver = [r["status"] for r in data_ver["emissions"]]
        assert all(s == "Verified" for s in statuses_ver)
        assert len(statuses_ver) == 2

        # 2. Query with status=Verified,Pending
        res_both = client.get(f"/api/emissions?facility_id={fac.id}&year=2026&month=6&status=Verified,Pending")
        assert res_both.status_code == 200
        data_both = res_both.get_json()
        assert data_both["total"] == 4  # 2 Scope 1 + 2 Scope 2
        statuses_both = set(r["status"] for r in data_both["emissions"])
        assert statuses_both == {"Verified", "Pending"}

        # 3. Query with status=all
        res_all = client.get(f"/api/emissions?facility_id={fac.id}&year=2026&month=6&status=all")
        assert res_all.status_code == 200
        data_all = res_all.get_json()
        assert data_all["total"] == 4
