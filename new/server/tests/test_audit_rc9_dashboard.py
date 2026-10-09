"""RC-9 / RC-12 dashboard regressions on a controlled dataset.

Hand values: AR5 GWP-100 CH4 28 / N2O 265 (stored co2e); BOE = oil bbl + gas Mcf x 0.178.
"""
import pytest

from extensions import db
from models import (Emission, Facility, MitigationProject, OgmpSurvey, ProductionData, Scope2Emission,
                    Scope3Emission)
from tests.audit_helpers import login, make_facility, make_user, uniq


@pytest.fixture
def world(client, app):
    with app.app_context():
        from routes.dashboard import clear_dashboard_cache

        act = uniq("ACT")
        f1 = make_facility(region="West", activity=act, division="D1", segment="Upstream")
        f2 = make_facility(name=f1.name, region="West", activity=act, division="D1", segment="Upstream")  # same name
        rows = [
            # record-level activity NULL: must still count under the facility's activity (BUG-004)
            Emission(facility_id=f1.id, year=2031, month=1, process_type="combustion", co2e_total=100.0,
                     co2_emissions=100.0, ch4_emissions=0.0, n2o_emissions=0.0, status="Verified", activity=None),
            Emission(facility_id=f1.id, year=2031, month=2, process_type="routine_flaring", co2e_total=50.0,
                     co2_emissions=49.44, ch4_emissions=0.02, n2o_emissions=0.0, quantity=1.0, unit="MMscf",
                     status="Verified"),
            Emission(facility_id=f1.id, year=2031, month=3, process_type="fugitive_component", co2e_total=28.0,
                     ch4_emissions=1.0, status="Verified"),
            Emission(facility_id=f1.id, year=2031, month=4, process_type="combustion", co2e_total=7.0,
                     ch4_emissions=0.25, status="Pending"),
            Emission(facility_id=f2.id, year=2031, month=1, process_type="combustion", co2e_total=5.0, status="Verified"),
            # emissions in a year with no production (must not enter the all-years intensity)
            Emission(facility_id=f1.id, year=2032, month=1, process_type="combustion", co2e_total=1000.0,
                     status="Verified"),
            Scope2Emission(facility_id=f1.id, year=2031, month=1, source_type="electricity", co2e=10.0, status="Verified"),
            Scope3Emission(facility_id=f1.id, year=2031, month=1, category="Category 1", co2e=3.0, status="Pending"),
            ProductionData(facility_id=f1.id, year=2031, month=1, oil_amount=1000.0, oil_unit="bbl",
                           gas_amount=10000.0, gas_unit="mscf"),
            MitigationProject(facility_id=f1.id, name="done", project_type="x", quantity_tco2e=20.0, year=2031, status="Active"),
            MitigationProject(facility_id=f1.id, name="later", project_type="x", quantity_tco2e=500.0, year=2031, status="Planned"),
        ]
        db.session.add_all(rows)
        db.session.commit()
        clear_dashboard_cache()
        login(client, make_user("admin", "Global"))
        yield {"client": client, "f1": f1, "f2": f2, "act": act}


def batch(c, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    return c.get(f"/api/dashboard/batch-all?{q}").get_json()


def rows_for(b, year=2031):
    """batch-all returns the summary for every year (the client picks the selected one)."""
    return [r for r in b["summary"] if int(r["year"]) == year]


def test_bug004_040_061_facility_filters_and_source_split(world):
    b = batch(world["client"], year=2031, activity=world["act"])
    s = rows_for(b)
    s1 = sum(r["scope1_total"] for r in s)
    assert s1 == pytest.approx(100 + 50 + 28 + 5)  # record with NULL activity counted
    buckets = {k: sum(r[k] for r in s) for k in ("combustion", "flaring", "venting", "fugitive", "process", "other")}
    assert sum(buckets.values()) == pytest.approx(s1)  # parts == whole (BUG-040)
    assert buckets["fugitive"] == pytest.approx(28) and buckets["flaring"] == pytest.approx(50)
    assert buckets["combustion"] == pytest.approx(105)


def test_bug054_include_pending_everywhere(world):
    b = batch(world["client"], year=2031, activity=world["act"], includePending="true")
    assert sum(r["scope1_total"] for r in rows_for(b)) == pytest.approx(190)
    assert b["scope3_summary"]["total"] == pytest.approx(3)
    ps = batch(world["client"], year=2031, activity=world["act"])["pending_stats"]
    assert ps["count"] == 2 and ps["totalCo2e"] == pytest.approx(10.0)


def test_bug005_072_gwp20_uses_active_standard(world):
    from calculations.constants import get_active_gwp

    g20, g100 = get_active_gwp(horizon="20"), get_active_gwp(horizon="100")
    b = batch(world["client"], year=2031, activity=world["act"], gwp_horizon=20)
    ch4 = 0.02 + 1.0
    assert sum(r["scope1_total"] for r in rows_for(b)) == pytest.approx(183 + ch4 * (g20["CH4"] - g100["CH4"]))
    assert b["pending_stats"]["totalCo2e"] == pytest.approx(7 + 0.25 * (g20["CH4"] - g100["CH4"]) + 3, abs=0.01)


def test_bug064_categorical_groups_by_facility_id(world):
    rows = batch(world["client"], year=2031, activity=world["act"])["categorical_breakdown"]
    ids = {r["facility_id"] for r in rows}
    assert {world["f1"].id, world["f2"].id} <= ids


def test_bug094_planned_mitigation_not_netted(world):
    b = batch(world["client"], year=2031, activity=world["act"])
    assert sum(m["quantity_tco2e"] for m in b["mitigation"]) == pytest.approx(20)
    assert sum(m["quantity_tco2e"] for m in b["mitigation_planned"]) == pytest.approx(500)


def test_bug041_no_goal_badge_in_all_years_or_filtered_view(world):
    assert batch(world["client"])["goal"] is None
    assert batch(world["client"], year=2031, activity=world["act"])["goal"] is None


def test_bug017_all_years_intensity_pairs_emissions_with_production(world):
    rows = world["client"].get(f"/api/dashboard/intensity-stats?year=all&facilityId={world['f1'].id}").get_json()
    r = rows[0]
    boe = 1000 + 10000 * 0.178
    assert r["total_boe"] == pytest.approx(boe)
    assert r["intensity_years"] == [2031]
    assert r["co2_intensity"] == pytest.approx((178 + 10) * 1000 / boe)  # 2032's 1000 t excluded
    assert r["unmatched_co2e"] == pytest.approx(1000)


def test_bug088_ch4_without_gas_has_no_loss_rate(world):
    f = make_facility(region="West", segment="Upstream")
    db.session.add(Emission(facility_id=f.id, year=2031, month=1, process_type="venting", ch4_emissions=5.0,
                            co2e_total=140.0, status="Verified"))
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    r = world["client"].get(f"/api/dashboard/intensity-stats?year=2031&facilityId={f.id}").get_json()[0]
    assert r["methane_loss_rate_pct"] is None and r["ogmp_target_status"] == "Missing Production Data"


def test_bug033_035_036_026_flaring_units_and_streams(world):
    c = world["client"]
    f = world["f1"]
    fs = c.get(f"/api/dashboard/flaring-summary?year=2031&facilityId={f.id}").get_json()
    assert fs["routine_flaring"]["volume_m3"] == pytest.approx(28316.85, rel=1e-5)  # 1 MMscf
    assert fs["unclassified_flaring"]["volume_m3"] == 0
    # gas produced 10,000 Mcf = 283,168.47 m3 -> intensity 10 %
    assert fs["flaring_intensity_pct"] == pytest.approx(28316.846592 / 283168.46592 * 100, rel=1e-4)
    allyears = c.get(f"/api/dashboard/flaring-summary?year=all&facilityId={f.id}").get_json()
    assert allyears["year"] == "all" and allyears["flaring_intensity_pct"] is None
    filtered = c.get("/api/dashboard/flaring-summary?year=2031&activity=nonexistent").get_json()
    assert filtered["total_flaring"]["volume_m3"] == 0


def test_bug079_all_years_reconciliation_per_year(world):
    f = make_facility(region="West", segment="Upstream")
    for y in (2031, 2032):
        db.session.add(Emission(facility_id=f.id, year=y, month=1, process_type="venting", ch4_emissions=100.0,
                                co2e_total=2800.0, status="Verified"))
        import datetime

        db.session.add(OgmpSurvey(facility_id=f.id, year=y, estimated_annual_tch4=100.0,
                                  survey_date=datetime.date(y, 6, 1), survey_type="aerial"))
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    m = world["client"].get(f"/api/dashboard/ogmp-metrics?year=all&facilityId={f.id}").get_json()
    row = m["facilities"][0] if isinstance(m, dict) else m[0]
    assert row["reconciliation_variance_pct"] == pytest.approx(0.0)
    assert row["reconciliation_status"] == "Reconciled"


def test_bug086_segment_category(world):
    from services.intensity import segment_category

    assert segment_category("Upstream") == "upstream"
    assert segment_category("Downstream / Processing") == "downstream"
    assert segment_category("GNL Plant") == "midstream"
    assert segment_category("Oil & Gas") is None and segment_category(None) is None


def test_flaring_record_without_gas_volume_is_not_reported_compliant(world):
    """A flaring record in tonnes has no flared volume; 0 % intensity must not read as COMPLIANT."""
    f = make_facility(region="West", segment="Upstream")
    db.session.add_all([
        Emission(facility_id=f.id, year=2031, month=1, process_type="flaring", co2e_total=6372.8, quantity=2000.0,
                 unit="tonnes", status="Verified"),
        ProductionData(facility_id=f.id, year=2031, month=1, gas_amount=10000.0, gas_unit="mscf"),
    ])
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    fs = world["client"].get(f"/api/dashboard/flaring-summary?year=2031&facilityId={f.id}").get_json()
    assert fs["records_with_unknown_volume_unit"] == 1
    assert fs["is_compliant"] is None and fs["compliance_status"].startswith("Cannot assess")
    assert fs["yoy_change_pct"] is None
