"""Fixes for the upload scenario audit (audit/UPLOAD_SCENARIO_AUDIT.md).

Expected values come from the source tables: API Compendium 2021 Table 6-10 / 6-11 (liquids
unloading), section 8.2.2 and Exhibit 8.4 (CHP allocation), the ideal-gas relation for normal vs
standard m3. AR5 GWPs.
"""
import calendar
import csv
import io
import json
import time
import uuid

import pytest

from calculations.constants import get_active_gwp
from calculations.legacy_engine import compute_emissions

NG = 53.06 + 0.001 * 28 + 0.0001 * 265  # kg CO2e / MMBtu, Tables 4-5 / 4-6


def calc(app, payload):
    from routes.emissions import _lookup_api_factor

    with app.app_context():
        p = json.loads(json.dumps(payload))
        return compute_emissions(p, _lookup_api_factor(p.get("fuel")) or {}, gwp_dict=get_active_gwp(standard="AR5"))[0]


# ---------------------------------------------------------------- 1, 2 liquids unloading
@pytest.mark.parametrize("fuel,qty,unit,expected_ch4", [
    ("Liquids Unloading - Non-Plunger (Gulf Coast)", 12, "events", 12 * 0.255),
    ("Liquids Unloading - Plunger Lift (Rocky Mountain >100 events/yr)", 12, "events", 12 * 0.027),
    ("Liquids Unloading - Non-Plunger (10-50 events/yr)", 12, "events", 12 * 0.462),
    ("Liquids Unloading - Plunger Lift (≤100 events/yr)", 12, "events", 12 * 0.185),
    ("Liquids Unloading - Non-Plunger (Midcontinent)", 3, "events", 3 * 0.916),
])
def test_unloading_uses_the_selected_table_6_10_row(app, fuel, qty, unit, expected_ch4):
    em = calc(app, {"process_type": "unloading", "fuel": fuel, "amount": qty, "quantity": qty, "unit": unit,
                    "factor_source": "default", "year": 2023, "month": 7})
    assert em["ch4"] == pytest.approx(expected_ch4, rel=1e-6)


@pytest.mark.parametrize("fuel,per_well_year", [("Liquids Unloading - Non-Plunger", 2.792),
                                                ("Liquids Unloading - Plunger Lift (Tier 1 Default)", 1.774)])
def test_unloading_per_well_year_on_a_monthly_record(app, fuel, per_well_year):
    em = calc(app, {"process_type": "unloading", "fuel": fuel, "amount": 4, "quantity": 4, "unit": "wells",
                    "factor_source": "default", "year": 2023, "month": 7})
    assert em["ch4"] == pytest.approx(4 * per_well_year * 31 / 365, rel=1e-6)  # Table 6-11, July's share


# ---------------------------------------------------------------- 5, 7 gas volumes
GAS = {"c1": 87.5, "c2": 5.2, "c3": 2.1, "c4": 1.0, "c5": 0.5, "co2_mol": 1.8, "hhv": 1010, "combustion_efficiency": 99.5}


def t3(app, q, unit):
    return calc(app, dict(GAS, process_type="combustion", fuel="Natural Gas", amount=q, quantity=q, unit=unit,
                          factor_source="specific"))


def test_composition_method_needs_a_gas_volume(app):
    with pytest.raises(Exception, match="gas volume"):
        t3(app, 51, "MMBtu")


def test_composition_method_is_the_same_in_every_volume_unit(app):
    ref = t3(app, 50000, "scf")["co2"]
    for q, u in ((50, "Mscf"), (50000 / 35.3146667, "m3"), (50000 / 35.3146667, "Sm3"),
                 (50000 / 35.3146667 / (288.706 / 273.15), "Nm3")):
        assert t3(app, q, u)["co2"] == pytest.approx(ref, rel=1e-4), u


def test_normal_m3_is_converted_to_standard_m3(app):
    em = calc(app, {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1000, "quantity": 1000, "unit": "Nm3",
                    "factor_source": "default"})
    # 1 Nm3 (0 C) = 288.706 / 273.15 standard m3 (60 F); 1 m3 = 35.3146667 scf; 1,020 Btu/scf
    mmbtu = 1000 * 288.706 / 273.15 * 35.3146667 * 1020 / 1e6
    assert em["totalCo2e"] == pytest.approx(mmbtu * NG / 1000, rel=1e-4)


# ---------------------------------------------------------------- 6 CHP
def test_chp_default_efficiencies_are_the_compendium_defaults():
    from calculations.indirect import CogenAllocationCalculator

    res = CogenAllocationCalculator().calculate(total_emissions=1000, heat_output=5000, power_output=1000,
                                                method="wri_efficiency", power_unit="mwh")
    p = 1000 * 3.412142
    assert res["metadata"]["allocated_heat_tonnes"] == pytest.approx((5000 / 0.80) / (5000 / 0.80 + p / 0.35) * 1000, rel=1e-6)


def test_chp_exhibit_8_4_with_the_plant_efficiencies():
    from calculations.indirect import CogenAllocationCalculator

    # Exhibit 8.4: 435,983 t, steam 3,614,000 MMBtu (80 %), power 1,100,600 MWh (33 %) -> share 0.284186
    res = CogenAllocationCalculator().calculate(total_emissions=435983, heat_output=3614000, power_output=1100600,
                                                method="wri_efficiency", power_unit="mwh", heat_efficiency=80,
                                                power_efficiency=33)
    assert res["metadata"]["allocated_heat_tonnes"] == pytest.approx(123900.2, rel=1e-4)


# ---------------------------------------------------------------- helpers for the HTTP checks
@pytest.fixture
def env(app, client):
    from extensions import db
    from models import Facility, User

    tag = uuid.uuid4().hex[:6]
    with app.app_context():
        u = User(email=f"fix_{tag}@test.com", fullName="Fix Admin", orgName="T", sector="Energy", role="admin",
                 location="Global Corporate Head Office")
        u.set_password("FixAdmin123!")
        r = User(email=f"rev_{tag}@test.com", fullName="Reviewer", orgName="T", sector="Energy", role="admin",
                 location="Global Corporate Head Office")
        r.set_password("FixAdmin123!")
        f = Facility(name=f"Fix Fac {tag}", region="FixRegion", code=f"FX-{tag}")
        db.session.add_all([u, r, f])
        db.session.commit()
        ids = {"uid": u.id, "rid": r.id, "fid": f.id, "fac": f.name, "tag": tag}
    with client.session_transaction() as s:
        s["user_id"] = ids["uid"]
    return ids


def upload(client, scope, text, **form):
    data = {"scope": str(scope), "global_factor_type": "auto", "file": (io.BytesIO(text.encode()), "f.csv"), **form}
    job = client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data").get_json()["job_id"]
    for _ in range(400):
        st = client.get(f"/api/emissions/upload/status/{job}").get_json()
        if st["status"] != "processing":
            return st, job
        time.sleep(0.05)


# ---------------------------------------------------------------- 3, 4 review queue
def test_pending_counts_cover_the_whole_queue(app, client, env):
    from extensions import db
    from models import Emission

    with app.app_context():
        for i in range(205):
            db.session.add(Emission(facility_id=env["fid"], year=2020, month=1, process_type="combustion",
                                    co2e_total=1.0, status="Pending", equipment_id=f"Q{i}"))
        db.session.commit()
    res = client.get("/api/emissions/pending").get_json()
    assert len(res["scope1"]) == 200 and res["pending_counts"]["1"] >= 205
    assert res["total_pending"] == sum(res["pending_counts"].values())
    assert res["pending_co2e"] >= 205


def test_batch_approve_reports_what_was_approved(app, client, env):
    from extensions import db
    from models import Emission

    with app.app_context():
        e = Emission(facility_id=env["fid"], year=2020, month=2, process_type="combustion", co2e_total=1.0,
                     status="Pending", created_by=env["uid"])
        db.session.add(e)
        db.session.commit()
        eid = e.id
    own = client.post("/api/emissions/approve/batch", json={"by_scope": {"1": [eid]}}).get_json()
    assert own["approved_count"] == 0  # the maker cannot approve (the UI now says so)
    with client.session_transaction() as s:
        s["user_id"] = env["rid"]
    assert client.post("/api/emissions/approve/batch", json={"by_scope": {"1": [eid]}}).get_json()["approved_count"] == 1


# ---------------------------------------------------------------- 10 facility import
def test_facility_import_sets_equity_share_and_operator(app, client, env):
    from models import Facility

    name = f"Eq Fac {env['tag']}"
    st, _ = upload(client, "facilities", "name,region,boundary_type,equity_share_pct,operator_status\n"
                                         f"{name},South,Equity Share,49,non-operated\n"
                                         f"Bad Eq {env['tag']},South,Equity Share,150,operated\n")
    assert st["skipped_count"] == 1 and "equity_share_pct" in st["skipped_preview"][0]["reason"]
    with app.app_context():
        f = Facility.query.filter_by(name=name).one()
        assert (f.equity_share_pct, f.operator_status, f.region) == (49.0, "non_operated", "South")


# ---------------------------------------------------------------- 13 Scope 3 factors as kg per unit
def test_scope3_factors_are_stored_per_activity_unit(app, client, env):
    from models import Scope3Emission

    fac = env["fac"]
    st, _ = upload(client, 3, "Facility,Year,Month,Category,Sub Category,Amount,Unit,Emission Factor,EF Unit\n"
                              f"{fac},2021,1,1,Steel,50,tonne,1.8,t CO2e / tonne\n"
                              f"{fac},2021,2,2,Capex,150000,USD,350,kg CO2e / $1000\n"
                              f"{fac},2021,3,6,Flights,45000,passenger-km,180,g CO2e / pkm\n")
    assert st["skipped_count"] == 0, st["skipped_preview"]
    st, _ = upload(client, "3_eeio", f"Facility,Year,Month,NAICS Code,Spend USD\n{fac},2021,4,331110,100000\n")
    with app.app_context():
        rows = {r.month: r for r in Scope3Emission.query.filter_by(facility_id=env["fid"], year=2021)}
    assert rows[1].emission_factor == pytest.approx(1800) and rows[1].co2e == pytest.approx(90)
    assert rows[2].emission_factor == pytest.approx(0.35) and rows[2].co2e == pytest.approx(52.5)
    assert rows[3].emission_factor == pytest.approx(0.18) and rows[3].co2e == pytest.approx(8.1)
    assert rows[4].emission_factor == pytest.approx(0.787)  # EPA v1.3.0 kg CO2e / USD


def test_manual_scope3_without_factor_is_refused(client, env):
    r = client.post("/api/scope3", json={"facility_id": env["fid"], "year": 2021, "month": 5, "category": "1",
                                         "sub_category": "x", "activity_data": 10, "unit": "t"})
    assert r.status_code == 422


def test_manual_scope3_edit_keeps_the_factor_unit(app, client, env):
    r = client.post("/api/scope3", json={"facility_id": env["fid"], "year": 2021, "month": 6, "category": "1",
                                         "sub_category": "Steel", "activity_data": 50, "unit": "tonne",
                                         "emission_factor": 1.8, "factor_unit": "t CO2e / tonne"})
    assert r.status_code in (200, 201), r.get_json()
    rid = r.get_json().get("id") or r.get_json().get("record", {}).get("id")
    up = client.put(f"/api/scope3/{rid}", json={"activity_data": 100})
    assert up.status_code == 200, up.get_json()
    from models import Scope3Emission
    with app.app_context():
        from extensions import db
        assert db.session.get(Scope3Emission, rid).co2e == pytest.approx(180)  # 100 t x 1.8 t/t


# ---------------------------------------------------------------- 18, 19 names and error file
def test_catalog_name_and_error_file(app, client, env):
    from models import Emission

    st, job = upload(client, 1, "Date,Facility,Process,Fuel,Quantity,Unit,Equipment ID,Notes\n"
                                f"2021-07,{env['fac']},COMBUSTION,natural gas,1000,mmbtu,CN-1,\n"
                                f"2021-07,{env['fac']},combustion,Nope,1,MMBtu,CN-2,\n")
    with app.app_context():
        rec = Emission.query.filter_by(equipment_id="CN-1", facility_id=env["fid"]).one()
        assert (rec.fuel_type, rec.unit) == ("Natural Gas", "MMBtu")
        assert rec.co2e_total == pytest.approx(1000 * NG / 1000)
    rows = list(csv.reader(io.StringIO(client.get(f"/api/emissions/upload/errors/{job}").data.decode())))
    assert rows[1][-1] == ""  # a blank cell stays blank (was "None")


# ---------------------------------------------------------------- 22 rate limit key
def test_rate_limit_counts_per_user(app):
    from extensions import rate_limit_key

    with app.test_request_context("/api/x", environ_base={"REMOTE_ADDR": "10.0.0.5"}):
        from flask import session
        assert rate_limit_key() == "10.0.0.5"
        session["user_id"] = 7
        assert rate_limit_key() == "user:7"
