"""Fixes for the 10,000-row upload audit (audit/UPLOAD_10K_AUDIT.md).

Expected values are derived by hand: carbon balance on standard m3 (CO2 1.8613 kg/m3 = 44.01 / 23.645,
CH4 0.6785 kg/m3 at 60 F), 1 short ton = 907.18474 kg, CO2/C = 44.01 / 12.011, the natural-gas
boiler factor of Tables 4-5 / 4-6, AR5 GWPs, IPCC Approach 1 default uncertainties.
"""
import calendar
import io
import json
import time
import uuid

import pytest

from calculations.constants import get_active_gwp
from calculations.legacy_engine import compute_emissions

NG = 53.06 + 0.001 * 28 + 0.0001 * 265  # kg CO2e / MMBtu of boiler fuel
RHO_CO2, RHO_CH4 = 1.8613, 0.6785


def calc(app, payload):
    from routes.emissions import _lookup_api_factor

    with app.app_context():
        p = json.loads(json.dumps(payload))
        return compute_emissions(p, _lookup_api_factor(p.get("fuel")) or {}, gwp_dict=get_active_gwp(standard="AR5"))[0]


@pytest.fixture
def env(app, client):
    from extensions import db
    from models import Facility, User

    tag = uuid.uuid4().hex[:6]
    with app.app_context():
        u = User(email=f"k10_{tag}@test.com", fullName="Maker", orgName="T", sector="Energy", role="admin",
                 location="Global Corporate Head Office")
        u.set_password("FixAdmin123!")
        r = User(email=f"k10r_{tag}@test.com", fullName="Checker", orgName="T", sector="Energy", role="admin",
                 location="Global Corporate Head Office")
        r.set_password("FixAdmin123!")
        f = Facility(name=f"K10 Fac {tag}", region="K10Region", code=f"K10-{tag}", segment="Upstream")
        db.session.add_all([u, r, f])
        db.session.commit()
        ids = {"uid": u.id, "rid": r.id, "fid": f.id, "fac": f.name, "tag": tag}
    with client.session_transaction() as s:
        s["user_id"] = ids["uid"]
    return ids


def as_user(client, uid):
    with client.session_transaction() as s:
        s["user_id"] = uid


def upload(client, scope, text, **form):
    data = {"scope": str(scope), "global_factor_type": "auto", "file": (io.BytesIO(text.encode()), "f.csv"), **form}
    job = client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data").get_json()["job_id"]
    for _ in range(400):
        st = client.get(f"/api/emissions/upload/status/{job}").get_json()
        if st["status"] != "processing":
            return st
        time.sleep(0.05)


# ---------------------------------------------------------------- 1 Tier 3 flare efficiency
FLARE = {"c1": 85, "c2": 6, "c3": 3, "c4": 2, "c5": 1, "co2_mol": 2, "n2_mol": 1}
CARBON = 0.85 + 2 * 0.06 + 3 * 0.03 + 4 * 0.02 + 5 * 0.01  # mol C per mol gas = 1.19


def flare(app, **extra):
    return calc(app, dict(FLARE, process_type="flaring", fuel="Associated Gas (Flaring)", amount=10000,
                          quantity=10000, unit="m3", factor_source="specific", flare_type="elevated", **extra))


@pytest.mark.parametrize("eff", [90, 98, 99.5])
def test_flare_control_efficiency_is_used(app, eff):
    e = eff / 100
    em = flare(app, control_efficiency=eff)
    assert em["ch4"] == pytest.approx(10000 * 0.85 * (1 - e) * RHO_CH4 / 1000, rel=2e-3)
    assert em["co2"] == pytest.approx(10000 * (CARBON * e + 0.02) * RHO_CO2 / 1000, rel=2e-3)


def test_flare_separate_efficiencies_win_over_the_single_one(app):
    em = flare(app, control_efficiency=90, destruction_efficiency=99)
    assert em["ch4"] == pytest.approx(10000 * 0.85 * 0.01 * RHO_CH4 / 1000, rel=2e-3)
    assert em["co2"] == pytest.approx(10000 * (CARBON * 0.90 + 0.02) * RHO_CO2 / 1000, rel=2e-3)


# ---------------------------------------------------------------- 2 carbon balance mass units
@pytest.mark.parametrize("q,unit,tonnes", [(100, "short ton", 90.718474), (100, "Short-Ton", 90.718474),
                                           (2000, "lb", 0.90718474), (5, "long ton", 5.080234544)])
def test_carbon_balance_mass_units(app, q, unit, tonnes):
    em = calc(app, {"process_type": "stoichiometry", "fuel": "", "amount": q, "quantity": q, "unit": unit,
                    "factor_source": "specific", "carbon_content": 0.75})
    assert em["co2"] == pytest.approx(tonnes * 0.75 * 44.01 / 12.011, rel=1e-4)


def test_carbon_balance_unknown_mass_unit_is_refused(app):
    with pytest.raises(Exception, match="mass unit"):
        calc(app, {"process_type": "stoichiometry", "fuel": "", "amount": 10, "quantity": 10, "unit": "furlong",
                   "factor_source": "specific", "carbon_content": 0.75})


# ---------------------------------------------------------------- 3 steam boiler efficiency / loss
def test_steam_transmission_loss_is_a_percentage(app, client, env):
    from models import Scope2Emission

    fac = env["fac"]
    st = upload(client, 2, "Date,Facility,Source Type,Consumption,Unit,Boiler Eff,Trans Loss,Meter\n"
                           f"2019-01,{fac},steam,1000,MMBtu,80,0.9,K1\n"
                           f"2019-02,{fac},steam,1000,MMBtu,0.8,1,K2\n"
                           f"2019-03,{fac},steam,1000,MMBtu,85%,5%,K3\n"
                           f"2019-04,{fac},steam,1000,MMBtu,abc,5,K4\n"
                           f"2019-05,{fac},steam,1000,MMBtu,80,100,K5\n")
    assert st["skipped_count"] == 2, st["skipped_preview"]
    with app.app_context():
        rows = {r.month: r.co2e for r in Scope2Emission.query.filter_by(facility_id=env["fid"], year=2019)}
    assert rows[1] == pytest.approx(1000 / (0.80 * (1 - 0.009)) * NG / 1000, rel=1e-6)
    assert rows[2] == pytest.approx(1000 / (0.80 * (1 - 0.01)) * NG / 1000, rel=1e-6)
    assert rows[3] == pytest.approx(1000 / (0.85 * (1 - 0.05)) * NG / 1000, rel=1e-6)
    assert set(rows) == {1, 2, 3}


# ---------------------------------------------------------------- 5 one notification per batch
def test_batch_decision_sends_one_notification_per_maker(app, client, env):
    from extensions import db
    from models import Emission, Notification

    with app.app_context():
        recs = [Emission(facility_id=env["fid"], year=2018, month=m, process_type="combustion", co2e_total=1.0,
                         status="Pending", created_by=env["uid"], equipment_id=f"N{m}") for m in range(1, 6)]
        db.session.add_all(recs)
        db.session.commit()
        ids = [r.id for r in recs]
    as_user(client, env["rid"])
    res = client.post("/api/emissions/approve/batch", json={"by_scope": {"1": ids[:4]}}).get_json()
    assert res["approved_count"] == 4
    res = client.post("/api/emissions/approve/batch", json={"by_scope": {"1": ids[4:]}}).get_json()
    assert res["approved_count"] == 1
    with app.app_context():
        notes = Notification.query.filter_by(user_id=env["uid"]).order_by(Notification.id).all()
        assert len(notes) == 2
        batch, single = json.loads(notes[0].metadata_json), json.loads(notes[1].metadata_json)
    assert batch["record_count"] == 4 and sorted(batch["record_ids"]) == sorted(ids[:4])
    assert "4 of your Scope 1 records were approved" in notes[0].message
    assert single["record_id"] == ids[4]


# ---------------------------------------------------------------- 6 paged Scope 2 / 3 lists
def test_scope2_and_scope3_lists_page_on_the_server(app, client, env):
    from extensions import db
    from models import Scope2Emission, Scope3Emission

    with app.app_context():
        for m in range(1, 8):
            db.session.add(Scope2Emission(facility_id=env["fid"], year=2017, month=m, source_type="electricity",
                                          electricity_kwh=1, co2e=1, status="Verified"))
            db.session.add(Scope3Emission(facility_id=env["fid"], year=2017, month=m, category="Category 1",
                                          sub_category=f"P{m}", co2e=1, status="Verified"))
        db.session.commit()
    for ep in ("scope2", "scope3"):
        full = client.get(f"/api/{ep}?facilityId={env['fid']}").get_json()
        assert isinstance(full, list) and len(full) == 7  # old contract without paging
        p1 = client.get(f"/api/{ep}?facilityId={env['fid']}&limit=3&offset=0").get_json()
        p3 = client.get(f"/api/{ep}?facilityId={env['fid']}&limit=3&offset=6").get_json()
        assert p1["total"] == 7 and len(p1["data"]) == 3 and len(p3["data"]) == 1
        assert [r["id"] for r in p1["data"]] == [r["id"] for r in full[:3]]


# ---------------------------------------------------------------- 7 vented processes on the dashboard
@pytest.mark.parametrize("process,cat", [("well_testing", "vented"), ("workovers", "vented"), ("separation", "vented"),
                                         ("co2_eor", "vented"), ("thermal_oxidizer", "combustion"),
                                         ("tank_flashing", "vented"), ("chemical_production", "process")])
def test_source_category(process, cat):
    from services.dashboard_filters import source_category

    assert source_category(process) == cat


def test_methane_split_counts_well_testing_as_venting(app, client, env):
    from extensions import db
    from models import Emission, ProductionData

    with app.app_context():
        db.session.add_all([
            Emission(facility_id=env["fid"], year=2016, month=1, process_type="well_testing", ch4_emissions=2.0,
                     co2e_total=56.0, status="Verified"),
            Emission(facility_id=env["fid"], year=2016, month=1, process_type="combustion", ch4_emissions=0.5,
                     co2e_total=100.0, status="Verified"),
            ProductionData(facility_id=env["fid"], year=2016, month=1, oil_amount=1000, oil_unit="bbl",
                           gas_amount=1000, gas_unit="Mscf"),
        ])
        db.session.commit()
    rows = client.get(f"/api/dashboard/intensity-stats?year=2016&facilityId={env['fid']}").get_json()
    row = next(r for r in rows if r["facility_id"] == env["fid"])
    assert row["ch4_venting"] == pytest.approx(2.0) and row["ch4_combustion"] == pytest.approx(0.5)
    summary = client.get(f"/api/dashboard/summary?facilityId={env['fid']}&year=2016").get_json()
    assert sum(r["venting"] for r in summary) == pytest.approx(56.0)
    assert sum(r["other"] for r in summary) == pytest.approx(0.0)


# ---------------------------------------------------------------- 8, 12 uncertainty page
def test_uncertainty_tiers_are_the_calculation_tiers(app, client, env):
    from extensions import db
    from models import Emission

    with app.app_context():
        for src, t, proc in (("default", 50.0, "combustion"), ("custom", 30.0, "combustion"),
                             ("specific", 20.0, "tank_flashing")):
            db.session.add(Emission(facility_id=env["fid"], year=2015, month=1, process_type=proc, factor_source=src,
                                    co2_emissions=t, co2e_total=t, uncertainty=0.02, status="Verified"))
        db.session.commit()
    res = client.get(f"/api/dashboard/uncertainty?year=2015&facility_id={env['fid']}").get_json()
    assert res["tier_breakdown"] == {"Tier 1": 50.0, "Tier 2": 30.0, "Tier 3": 20.0}
    assert res["uncertainty_bands"] == {"low": 100.0, "medium": 0.0, "high": 0.0}  # 2 % x 2 = 4 % at 95 %
    cats = {c["category"] for c in res["categories"]}
    assert "tank_flashing" not in cats and "Storage Tank - Flashing/Events" in cats


# ---------------------------------------------------------------- 9 bulk Scope 3 uncertainty
def test_bulk_scope3_records_get_the_form_default_uncertainty(app, client, env):
    from models import Scope3Emission

    fac = env["fac"]
    upload(client, 3, "Facility,Year,Month,Category,Sub Category,Amount,Unit,Emission Factor,EF Unit\n"
                      f"{fac},2014,1,1,Steel,50,tonne,1.8,t CO2e / tonne\n"
                      f"{fac},2014,2,1,Cement,10,tonne,0.9,t CO2e / tonne\n")
    upload(client, "3_eeio", f"Facility,Year,Month,NAICS Code,Spend USD\n{fac},2014,3,331110,100000\n")
    upload(client, 3, "Facility,Year,Month,Category,Sub Category,Amount,Unit,Emission Factor,EF Unit,Uncertainty\n"
                      f"{fac},2014,4,1,Glass,5,tonne,1,t CO2e / tonne,12\n")
    with app.app_context():
        rows = {r.month: r.uncertainty for r in Scope3Emission.query.filter_by(facility_id=env["fid"], year=2014)}
    # the form's defaults are +/-20 % (factor) and +/-10 % (activity) at 95 %; stored as the combined
    # 1-sigma fraction: sqrt(0.20^2 + 0.10^2) / 2 (same convention as Scope 2: 2.7 % 1-sigma, 5.4 % at 95 %)
    for m in (1, 2, 3):
        assert rows[m] == pytest.approx((0.20 ** 2 + 0.10 ** 2) ** 0.5 / 2, rel=0.02)
    assert rows[4] == pytest.approx(0.12)


# ---------------------------------------------------------------- 10 dashboard uncertainty follows the filters
def test_dashboard_uncertainty_follows_the_facility_filter(app, client, env):
    from extensions import db
    from models import Emission

    with app.app_context():
        db.session.add(Emission(facility_id=env["fid"], year=2013, month=1, process_type="combustion",
                                co2_emissions=7.0, co2e_total=7.0, status="Verified"))
        db.session.commit()
    res = client.get(f"/api/dashboard/batch-all?year=2013&facilityId={env['fid']}").get_json()
    assert res["uncertainty"]["total_inventory_emissions"] == pytest.approx(7.0)
    seg = client.get("/api/dashboard/batch-all?year=2013&segment=NoSuchSegment").get_json()
    assert seg["uncertainty"]["total_inventory_emissions"] == 0


# ---------------------------------------------------------------- 11 per-year factors in a leap year
@pytest.mark.parametrize("year", [2023, 2024])
def test_per_device_year_factor_uses_the_days_of_the_year(app, year):
    em = calc(app, {"process_type": "pneumatic", "fuel": "Pneumatic Controller - High Bleed (>6 scfh)", "amount": 10,
                    "quantity": 10, "unit": "devices", "factor_source": "default", "year": year, "month": 2})
    days = calendar.monthrange(year, 2)[1]
    # 5.11 t CH4 per device-year (catalog, Table 6-14 row)
    assert em["ch4"] == pytest.approx(10 * 5.11 * days / (366 if calendar.isleap(year) else 365), rel=1e-6)
