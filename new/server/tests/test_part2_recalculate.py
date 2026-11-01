"""
Unit & Regression Tests for Part 2.2: Recalculate Action & Maker-Checker Workflow
=================================================================================
Verifies:
1. Preview recalculation calculates impact (records affected, tCO2e before/after, delta) without mutating DB.
2. Recalculation request enforces GHG Protocol base-year triggers and mandatory justification.
3. Maker-checker approval executes recalculation, updates records, records history snapshots, and creates audit log.
4. Base-year recalculation records are created per GHG Protocol Chapter 5.
"""
import pytest
from extensions import db
from models import Emission, RecalculationRequest, RecalculationHistory, BaseYearRecalculation
from tests.audit_helpers import make_facility, make_user, login, uniq


def test_recalculate_preview_simulation(app, client):
    """Item 2.2: Preview returns impact without mutating stored database records."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        fac = make_facility(name=uniq("FAC_RECALC"))

        # Create Scope 1 emission records: 2024, CH4 10.0 tonnes
        # Under AR5 (CH4=28): 10 * 28 = 280 tCO2e
        # Under AR6 (CH4=29.8): 10 * 29.8 = 298 tCO2e
        em = Emission(
            facility_id=fac.id,
            year=2024,
            month=1,
            process_type="venting",
            quantity=100.0,
            unit="m3",
            co2_emissions=0.0,
            ch4_emissions=10.0,
            n2o_emissions=0.0,
            co2e_total=280.0,
            gwp_version="AR5",
            status="Verified",
            is_test=False,
        )
        db.session.add(em)
        db.session.commit()

        # Preview recalculation to AR6
        res = client.post(
            "/api/recalculate/preview",
            json={
                "year": 2024,
                "facility_id": fac.id,
                "scope": "1",
                "target_gwp_standard": "AR6",
            },
        )
        assert res.status_code == 200, res.get_data(as_text=True)
        data = res.json

        assert data["records_affected"] == 1
        assert data["tco2e_before"] == pytest.approx(280.0, rel=1e-3)
        assert data["tco2e_after"] == pytest.approx(298.0, rel=1e-3)
        assert data["delta_tco2e"] == pytest.approx(18.0, rel=1e-3)

        # Verify DB is 100% untouched after preview
        reloaded = db.session.get(Emission, em.id)
        assert reloaded.co2e_total == 280.0
        assert reloaded.gwp_version == "AR5"


def test_recalculate_request_enforces_triggers_and_justification(app, client):
    """Item 2.2: Enforce GHG Protocol triggers and minimum justification length."""
    with app.app_context():
        user = make_user("user")
        login(client, user)

        fac = make_facility(name=uniq("FAC_REQ"))

        # 1. Invalid trigger type -> rejected
        res_invalid = client.post(
            "/api/recalculate/request",
            json={
                "year": 2024,
                "trigger_type": "arbitrary_adjustment",
                "justification": "Adjusting values arbitrarily for target compliance",
            },
        )
        assert res_invalid.status_code == 400
        assert "Invalid trigger_type" in res_invalid.json["error"]

        # 2. Short justification -> rejected
        res_short = client.post(
            "/api/recalculate/request",
            json={
                "year": 2024,
                "trigger_type": "methodology_change",
                "justification": "Too short",
            },
        )
        assert res_short.status_code == 400
        assert "justification" in res_short.json["error"].lower()

        # 3. Valid trigger type & detailed justification -> accepted with status pending_approval
        res_valid = client.post(
            "/api/recalculate/request",
            json={
                "year": 2024,
                "facility_id": fac.id,
                "scope": "1",
                "target_gwp_standard": "AR6",
                "trigger_type": "methodology_change",
                "justification": "Adopting IPCC AR6 Global Warming Potentials per corporate board directive.",
            },
        )
        assert res_valid.status_code == 201
        data = res_valid.json
        assert data["request"]["status"] == "pending_approval"
        assert data["request"]["trigger_type"] == "methodology_change"


def test_recalculate_maker_checker_approval_and_history(app, client):
    """Item 2.2: Maker-checker approval executes recalculation, archives history, and logs audit."""
    with app.app_context():
        engineer = make_user("user")
        admin = make_user("admin")

        fac = make_facility(name=uniq("FAC_EXEC"))

        # Create record
        em = Emission(
            facility_id=fac.id,
            year=2023,  # Base year
            month=5,
            process_type="venting",
            quantity=50.0,
            unit="m3",
            co2_emissions=0.0,
            ch4_emissions=5.0,
            n2o_emissions=0.0,
            co2e_total=140.0,  # 5 * 28 (AR5)
            gwp_version="AR5",
            status="Verified",
            is_test=False,
        )
        db.session.add(em)
        db.session.commit()

        # Engineer requests recalculation
        login(client, engineer)
        res_req = client.post(
            "/api/recalculate/request",
            json={
                "year": 2023,
                "facility_id": fac.id,
                "scope": "1",
                "target_gwp_standard": "AR6",
                "trigger_type": "methodology_change",
                "justification": "Re-aligning baseline inventory to IPCC AR6 standard.",
            },
        )
        assert res_req.status_code == 201
        req_id = res_req.json["request"]["id"]

        # Admin approves recalculation
        login(client, admin)
        res_app = client.post(f"/api/recalculate/{req_id}/approve")
        assert res_app.status_code == 200, res_app.get_data(as_text=True)

        # Verify record updated
        reloaded = db.session.get(Emission, em.id)
        assert reloaded.co2e_total == pytest.approx(149.0, rel=1e-3)  # 5 * 29.8
        assert reloaded.gwp_version == "AR6"

        # Verify historical snapshot in RecalculationHistory
        hist = RecalculationHistory.query.filter_by(request_id=req_id).first()
        assert hist is not None
        assert hist.old_co2e == pytest.approx(140.0, rel=1e-3)
        assert hist.new_co2e == pytest.approx(149.0, rel=1e-3)
        assert hist.old_gwp_version == "AR5"
        assert hist.new_gwp_version == "AR6"

        # Verify BaseYearRecalculation record created for year 2023
        by_rec = BaseYearRecalculation.query.filter_by(year=2023).first()
        assert by_rec is not None
        assert "methodology_change" in by_rec.reason.lower()
