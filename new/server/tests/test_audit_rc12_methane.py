"""RC-12 methane / OGMP regressions (BUG-031, BUG-052, BUG-075)."""
import pytest

from extensions import db
from models import Emission, Facility
from services.ogmp import materiality_level, reconcile
from tests.audit_helpers import login, make_facility, make_user


@pytest.mark.parametrize("td,bu,exp_status,exp_v", [
    (453.62, 100.0, "Discrepancy Flagged", 353.62),
    (110.0, 100.0, "Reconciled", 10.0),
    (5.0, 0.0, "No Bottom-Up", None),
    (0.0, 5.0, "No Top-Down", None),
])
def test_bug052_status_derived_from_variance(td, bu, exp_status, exp_v):
    v, _flag, status = reconcile(td, bu, 20.0)
    assert status == exp_status and (v == pytest.approx(exp_v) if exp_v is not None else v is None)


def test_bug031_materiality_not_max():
    class R:
        def __init__(self, lvl, ch4):
            self.ogmp_level, self.ch4_emissions, self.co2e_total = lvl, ch4, ch4 * 28

    # 236.6 of 338.9 t at Level 2 (the audit's facility 13): facility is Level 2, not 4
    assert materiality_level([R(2, 236.6), R(4, 102.3)]) == 2
    assert materiality_level([R(4, 300), R(2, 38.9)]) == 4


def test_bug052_survey_override_needs_justification(client, app):
    with app.app_context():
        f = make_facility(region="West", activity="Upstream")
        db.session.add(Emission(facility_id=f.id, year=2024, month=1, process_type="venting", ch4_emissions=100.0,
                                co2e_total=2800, status="Verified"))
        db.session.commit()
        login(client, make_user("admin", "Global"))
        body = {"facility_id": f.id, "year": 2024, "survey_date": "2024-06-01", "measured_rate_kg_hr": 51.78}
        r = client.post("/api/data/ogmp-surveys", json=dict(body, reconciliation_status="Reconciled"))
        assert r.status_code == 400  # 51.78 kg/h x 8760 = 453.6 t vs 100 t -> flagged; override without reason
        assert client.post("/api/data/ogmp-surveys", json=body).status_code in (200, 201)
        rows = client.get(f"/api/data/ogmp-surveys?facilityId={f.id}").get_json()
        assert rows[0]["reconciliation_status"] == "Discrepancy Flagged"
        assert rows[0]["variance_pct"] == pytest.approx((51.78 * 8760 / 1000 - 100) / 100 * 100, rel=1e-3)


def test_bug075_satellite_export_annualised_8760(client, app):
    with app.app_context():
        f = make_facility(region="West", activity="Upstream")
        login(client, make_user("admin", "Global"))
        r = client.post("/api/satellite/sentinel5p/export-to-ogmp", json={
            "facility_id": f.id, "observation_date": "2024-06-01", "estimated_emission_rate_kg_hr": 100.0})
        assert r.status_code in (200, 201), r.get_data(as_text=True)
        from models import OgmpSurvey

        s = OgmpSurvey.query.filter_by(facility_id=f.id).first()
        assert s.estimated_annual_tch4 == pytest.approx(876.0) and s.measured_rate_kg_hr == pytest.approx(100.0)
