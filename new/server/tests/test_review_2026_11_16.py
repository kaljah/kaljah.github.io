"""Regression tests for the code review of 2026-11-16 (uncommitted release/giz-demo changes): a Bearer token
that bypassed session revocation, gas compositions misread as percent, a user deletion that reassigned
authorship, a reconciliation that set its own review status, and unchecked annual report links."""
import pytest

from app import app
from audit_helpers import login, make_facility, make_user, uniq
from extensions import db
from models import OgmpAnnualReport, RecalculationRequest


@pytest.fixture
def ctx():
    with app.app_context():
        yield


# ---------------------------------------------------------------- C1: no Bearer token next to the session
def test_login_returns_no_bearer_token_and_a_bearer_header_does_not_authenticate(ctx):
    user = make_user("admin", "Global")
    with app.test_client() as c:
        body = login(c, user).get_json()
        assert "token" not in body and "access_token" not in body
    with app.test_client() as anonymous:
        r = anonymous.get("/api/auth/me", headers={"Authorization": "Bearer anything.at.all"})
        assert r.status_code == 401


# ---------------------------------------------------------------- H2: compositions are not re-read as percent
def test_pneumatic_composition_over_100_percent_is_refused_not_rescaled():
    from calculations.vented_production_pneumatic import PneumaticDeviceCalculator

    # 0.95 + 0.08 is 103 %: it used to be read as 0.95 % + 0.08 % (100x low)
    with pytest.raises(ValueError, match="cannot exceed 100"):
        PneumaticDeviceCalculator().calculate(count=1, hours=1000, bleed_rate=1, ch4_content=0.95, co2_content=0.08)


def test_agr_sour_and_sweet_contents_are_read_separately():
    from calculations.vented_production_tank import AcidGasRemovalCalculator

    def co2(sour, sweet):
        res = AcidGasRemovalCalculator().calculate(
            method="sour_sweet_balance", sour_gas_mmscf_yr=100.0, sweet_gas_mmscf_yr=60.0,
            sour_co2_content=sour, sweet_co2_content=sweet,
        )
        return res["results"]["co2"]["value"]

    # two streams: their contents may sum past 1 (0.70 + 0.40) without being percent
    assert co2(0.70, 0.40) == pytest.approx(co2("70%", "40%"))


def test_combustion_method_fraction_field_is_percent():
    from calculations.combustion_methods import _frac

    assert _frac(0.9, "efficiency") == pytest.approx(0.009)  # 0.9 is 0.9 %, never 90 %
    assert _frac(90, "efficiency") == pytest.approx(0.9)


def test_flare_hhv_without_unit_in_a_non_btu_range_is_refused():
    from calculations.combustion import FlaringCalculator

    with pytest.raises(ValueError, match="hhv_unit"):
        FlaringCalculator().calculate(gas_volume=1000.0, fuel_unit="m3", flare_type="elevated", uncertainties={},
                                      hhv=38.0, ch4_fraction=0.90)


# ---------------------------------------------------------------- H6: deletion never reassigns authorship
def test_user_with_a_required_reference_is_not_deleted(ctx):
    it_admin = make_user("it_admin", "Global")
    maker = make_user("user", "Global")
    db.session.add(RecalculationRequest(trigger_type="error_correction", justification="review test",
                                        requested_by=maker.id, target_scope="all"))
    db.session.commit()
    with app.test_client() as c:
        login(c, it_admin)
        r = c.delete(f"/api/auth/users/{maker.id}")
        assert r.status_code == 409, r.get_data(as_text=True)
    req = RecalculationRequest.query.filter_by(justification="review test").first()
    assert req.requested_by == maker.id  # not handed to the IT administrator


def test_user_without_required_references_is_still_deleted(ctx):
    it_admin = make_user("it_admin", "Global")
    plain = make_user("user", "Global")
    with app.test_client() as c:
        login(c, it_admin)
        assert c.delete(f"/api/auth/users/{plain.id}").status_code == 200


# ---------------------------------------------------------------- H7: OGMP reconciliation and report links
def test_reconciliation_awaits_review_whatever_status_is_sent(ctx):
    fac = make_facility(name=uniq("OGMP"))
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        r = c.post("/api/ogmp/reconcile", json={"facility_id": fac.id, "year": 2024, "status": "Verified"})
        assert r.status_code == 200, r.get_data(as_text=True)
        assert r.get_json()["annual_report"]["status"] == "Pending"


def test_measurement_cannot_link_another_facilitys_annual_report(ctx):
    mine, other = make_facility(name=uniq("OGMP")), make_facility(name=uniq("OGMP"))
    foreign = OgmpAnnualReport(facility_id=other.id, year=2024, tenant_id="default")
    db.session.add(foreign)
    db.session.commit()
    body = {"facility_id": mine.id, "year": 2024, "campaign_date": "2024-05-01", "survey_type": "Aerial",
            "measured_rate_kg_hr": 1.0}
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        r = c.post("/api/ogmp/site-measurements", json={**body, "annual_report_id": foreign.id})
        assert r.status_code == 404
        r = c.post("/api/ogmp/site-measurements", json={**body, "annual_report_id": "x"})
        assert r.status_code == 400
        assert c.post("/api/ogmp/site-measurements", json=body).status_code == 201


def test_target_with_a_malformed_entity_id_is_a_400(ctx):
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        r = c.post("/api/ogmp/targets", json={"reporting_entity_id": "abc"})
        assert r.status_code == 400


# ---------------------------------------------------------------- follow-up review: replacing plan milestones
def test_default_plan_also_replaces_milestones_stored_with_another_tenant_spelling(ctx):
    from models import OgmpImplementationPlan

    fac = make_facility(name=uniq("OGMP"))
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        assert c.post("/api/ogmp/implementation-plans", json={"facility_id": fac.id, "generate_default": True}).status_code == 201
        # rows imported with another spelling of the default tenant ("Default " is the same tenant)
        OgmpImplementationPlan.query.filter_by(facility_id=fac.id).update({"tenant_id": "Default "})
        db.session.commit()
        r = c.post("/api/ogmp/implementation-plans", json={"facility_id": fac.id, "generate_default": True})
        assert r.status_code == 409 and r.get_json()["existing_count"] == 11
        r = c.post("/api/ogmp/implementation-plans", json={"facility_id": fac.id, "generate_default": True, "confirm": True})
        assert r.status_code == 201
    assert OgmpImplementationPlan.query.filter_by(facility_id=fac.id).count() == 11  # replaced, not duplicated


# ---------------------------------------------------------------- follow-up review: tenant lookups fail closed
def _tenant_lookup_fails(*_a, **_k):
    raise RuntimeError("tenant lookup failed")


def test_scope_filter_refuses_to_run_unfiltered_when_the_tenant_cannot_be_resolved(ctx, monkeypatch):
    import utils
    from models import Facility
    from services.dashboard_filters import apply_scope

    monkeypatch.setattr(utils, "get_current_tenant_id", _tenant_lookup_fails)
    with pytest.raises(RuntimeError, match="tenant lookup failed"):
        apply_scope(Facility.query, Facility, allowed_fids=None, include_test=True)


def test_dashboard_cache_key_never_falls_back_to_the_default_tenant(ctx, monkeypatch):
    import utils
    from routes.dashboard import make_cache_key

    monkeypatch.setattr(utils, "get_current_tenant_id", _tenant_lookup_fails)
    with pytest.raises(RuntimeError, match="tenant lookup failed"):
        make_cache_key("_query_summary")(year=2024)


def test_survey_discrepancy_check_does_not_hide_a_failure(ctx):
    from routes.dashboard_ogmp import _survey_has_discrepancy

    fac = make_facility(name=uniq("OGMP"))
    with pytest.raises(ValueError):  # it used to answer "no discrepancy"
        _survey_has_discrepancy(fac, True, "not-a-year", 20.0)


def test_tenant_is_never_guessed_from_the_organisation_name(ctx):
    from utils import get_current_tenant_id

    user = make_user("admin", "Global")
    user.orgName = "Al-Amal Petroleum Corp"
    assert get_current_tenant_id(user) == "default"
