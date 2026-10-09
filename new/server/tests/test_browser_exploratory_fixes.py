"""Regression tests for the exploratory browser test findings (audit/BROWSER_EXPLORATORY_TEST.md).

Expected values are re-derived from the API Compendium 2021 tables / exhibits named in each test
(379.3 scf/lbmol at 60 F, 1 MMBtu = 1.055056 GJ), never from the code under test.
"""
import io
import json
import uuid

import pytest

from calculations.constants import get_active_gwp
from calculations.legacy_engine import compute_emissions
from services.scope1_calc import resolve_factor

SCF_PER_M3 = 35.3146667
J_PER_MMBTU = 1.055056e9
MV_SM3_PER_KMOL = 23.685  # Sm3 / kgmole, Compendium section 5.1.2


def calc(app, payload):
    with app.app_context():
        p = json.loads(json.dumps(payload))
        em, _ = compute_emissions(p, resolve_factor(p) or {}, gwp_dict=get_active_gwp(standard="AR5"))
        return em


def tier1(process, fuel, amount, unit, **extra):
    return {"process_type": process, "factor_source": "default", "fuel": fuel, "fuel_type": fuel,
            "amount": amount, "quantity": amount, "unit": unit,
            "calc_inputs": {process: {"fuel": fuel, "amount": amount, "unit": unit, **extra}}}


def activity(process, key, amount, unit="count", **extra):
    return {"process_type": process, "factor_source": "default", "activity_key": key, "amount": amount,
            "quantity": amount, "unit": unit, "calc_inputs": {process: {"activity_key": key, "amount": amount,
                                                                         "unit": unit, **extra}}}


# ---- F3: mud degassing, Table 6-2 onshore (tonnes CH4 / drilling day) ----
@pytest.mark.parametrize("fuel,ef", [("Drilling - Mud Degassing (Water Based)", 0.0458),
                                     ("Drilling - Mud Degassing (Oil Based)", 0.0103),
                                     ("Drilling - Mud Degassing (Synthetic)", 0.0103)])
def test_f3_mud_degassing_table_6_2(app, fuel, ef):
    em = calc(app, tier1("drilling", fuel, 100, "days"))
    assert em["ch4"] == pytest.approx(100 * ef, rel=1e-6)


# ---- F2: engine CH4 / N2O, Table 4-7 (tonne / 10^12 J, HHV) ----
@pytest.mark.parametrize("fuel,ch4_t_per_tj,n2o_t_per_tj", [
    ("Natural Gas - 4-Stroke Rich Burn Engine", 0.10, None),
    ("Natural Gas - 4-Stroke Lean Burn Engine", 0.537, None),
    ("Natural Gas - 2-Stroke Lean Burn Engine", 0.623, None),
    ("Natural Gas - Turbine", 0.0037, 0.0013),
])
def test_f2_engine_factors_table_4_7(app, fuel, ch4_t_per_tj, n2o_t_per_tj):
    em = calc(app, tier1("combustion", fuel, 1000, "m3"))
    tj = 1000 * SCF_PER_M3 * 1020 / 1e6 * J_PER_MMBTU / 1e12   # 1,020 Btu/scf (Table 3-8)
    assert em["ch4"] == pytest.approx(tj * ch4_t_per_tj, rel=1e-3)
    if n2o_t_per_tj:
        assert em["n2o"] == pytest.approx(tj * n2o_t_per_tj, rel=1e-3)


# ---- F1: fuels the form offered and the server rejected (Table 4-5 / 40 CFR 98 Table C-1) ----
@pytest.mark.parametrize("fuel,mmbtu_per_gal,kg_co2_per_mmbtu", [
    ("Propylene", 0.091, 67.77), ("Butane", 0.103, 64.77), ("Isobutane", 0.099, 64.94),
    ("Naphtha", 0.125, 68.02),
    ("Lubricants", 0.144, 74.27), ("Waste Oil", 0.138, 74.00),
])
def test_f1_liquid_fuels_table_4_5(app, fuel, mmbtu_per_gal, kg_co2_per_mmbtu):
    em = calc(app, tier1("combustion", fuel, 1000, "gal"))
    assert em["co2"] == pytest.approx(1000 * mmbtu_per_gal * kg_co2_per_mmbtu / 1000, rel=1e-3)


def test_f1_liquid_factor_rejects_gas_volume(app):
    # a per-gallon heating value cannot be applied to a gas volume
    with pytest.raises(Exception, match="gas volume"):
        calc(app, tier1("combustion", "Propylene", 1000, "scf"))


def test_f1_solids_and_gases(app):
    em = calc(app, tier1("combustion", "Tires", 10, "ton"))          # 28.00 MMBtu / short ton
    assert em["co2"] == pytest.approx(10 * 28.0 * 85.97 / 1000, rel=1e-3)
    # acetylene, Table 3-8: 0.0686 lb/ft3, 92.3 wt % C -> carbon balance at 100 % oxidation
    em = calc(app, tier1("combustion", "Acetylene", 1000, "scf"))
    assert em["co2"] == pytest.approx(1000 * 0.0686 * 0.923 * 44.01 / 12.011 / 2204.62, rel=2e-3)
    em = calc(app, tier1("mobile", "Compressed Natural Gas (CNG)", 1000, "scf"))
    assert em["co2"] == pytest.approx(1000 * 1020 / 1e6 * 53.06 / 1000, rel=1e-3)


@pytest.mark.parametrize("fuel,carbons", [("Propane (Flaring)", 3), ("Butane (Flaring)", 4),
                                          ("Ethylene (Flaring)", 2), ("Propylene (Flaring)", 3)])
def test_f1_pure_gas_flares_equation_5_3(app, fuel, carbons):
    em = calc(app, tier1("flaring", fuel, 1000, "m3"))
    assert em["co2"] == pytest.approx(1000 / MV_SM3_PER_KMOL * carbons * 44.01 * 0.965 / 1000, rel=1e-3)
    assert not em["ch4"]


def test_f1_flaring_variants_use_flaring_factors(app):
    em = calc(app, tier1("routine_flaring", "Natural Gas (Flaring - Elevated)", 1000, "m3"))
    # Equation 5-2 on the Table 5-1 processing-plant gas (CH4 91.9, NMHC 6.84 as C2, CO2 0.58 mol %), 98 %
    assert em["co2"] == pytest.approx(((0.919 + 0.0684 * 2) * 0.965 + 0.0058) * 44.01 / MV_SM3_PER_KMOL, rel=1e-3)


# ---- F4: separators / produced water are not tank flashing ----
def test_f4_separation_catalog_name_is_not_tank_flashing(app):
    with pytest.raises(Exception, match="No emission factor found"):
        calc(app, tier1("separation", "Separator Venting - Gas Well", 100, "m3"))


def test_f4_produced_water_exhibit_6_21(app):
    # Exhibit 6-21: 50 bbl/d, 250 psi, salt unknown -> 0.0142 t CH4 / 1,000 bbl
    em = calc(app, activity("separation", "pw_250psi_avg", 50 * 365, "bbl"))
    assert em["ch4"] == pytest.approx(50 * 365 * 0.0142 / 1000, rel=1e-6)
    em = calc(app, activity("separation", "sep_dump_valve_crude", 1000, "bbl"))   # Table 6-25
    assert em["ch4"] == pytest.approx(1000 * 2.70e-3 / 1000, rel=1e-6)


# ---- F5: pneumatic controllers / pumps by segment (Tables 6-14, 6-15, 6-16, 6-34, 6-42) ----
@pytest.mark.parametrize("key,t_per_year", [
    ("prod_pc_high_bleed_api", 2.25), ("prod_pc_high_bleed_ghgrp", 5.11), ("prod_pc_low_bleed_api", 0.36),
    ("prod_pc_low_bleed_ghgrp", 0.191), ("prod_pc_int_avg_api", 1.27), ("prod_pc_int_ghgrp", 1.85),
    ("cip_piston_ghgrp", 2.86), ("cip_diaphragm_api", 2.54), ("cip_avg_gri", 1.73),
    ("proc_pc_continuous", 8.304), ("ts_pc_continuous", 3.5), ("ts_pc_intermittent", 0.4),
])
def test_f5_pneumatic_tables(app, key, t_per_year):
    em = calc(app, activity("pneumatic", key, 1))
    # the tables print the converted factor to 2-3 significant figures
    assert em["ch4"] == pytest.approx(t_per_year, rel=0.012)


def test_loading_uses_table_6_47(app):
    em = calc(app, activity("loading", "load_submerged_dedicated", 1e6, "gal"))
    assert em["ch4"] == pytest.approx(0.91 * 0.15, rel=1e-6)   # 15 wt % CH4 default in TOC


# ---- endpoint checks ----
@pytest.fixture
def admin(app):
    from extensions import db
    from models import Facility, User

    with app.app_context():
        u = User.query.filter_by(email="explore_admin@test.com").first()
        if not u:
            u = User(email="explore_admin@test.com", fullName="Explore Admin", orgName="TestCorp",
                     sector="Energy", role="admin", location="Global Corporate Head Office")
            u.set_password("ExploreAdmin123!")
            db.session.add(u)
        f = Facility.query.filter_by(name="Explore Facility").first()
        if not f:
            f = Facility(name="Explore Facility", region="Explore", activity="EP", division="Production",
                         field="EX", segment="Upstream", code=f"EXP-{uuid.uuid4().hex[:6]}")
            db.session.add(f)
        db.session.commit()
        return u.id, f.id


def login(client, uid):
    with client.session_transaction() as sess:
        sess["user_id"] = uid


def s1(fid, **kw):
    base = {"facility_id": fid, "year": 2026, "month": 3, "process_type": "combustion", "factor_source": "default",
            "fuel": "Natural Gas", "fuel_type": "Natural Gas", "amount": 1000, "quantity": 1000, "unit": "m3"}
    base.update(kw)
    return base


def test_17_deleted_id_is_not_reused(client, admin):
    uid, fid = admin
    login(client, uid)
    r1 = client.post("/api/emissions", json=s1(fid))
    assert r1.status_code == 201, r1.get_json()
    first = r1.get_json()["id"]
    assert client.delete(f"/api/emissions/{first}").status_code in (200, 204)
    r2 = client.post("/api/emissions", json=s1(fid))
    assert r2.get_json()["id"] > first


def test_13_library_factor_record_named(client, admin, app):
    from extensions import db
    from models import CustomFactor, Emission

    uid, fid = admin
    with app.app_context():
        cf = CustomFactor(name="Explore Lib Factor", unit="scf", co2_factor=2.0, ch4_factor=0.01, n2o_factor=0.0001)
        db.session.add(cf)
        db.session.commit()
        cf_id = cf.id
    login(client, uid)
    r = client.post("/api/emissions", json=s1(fid, factor_source="custom", factor_mode="library",
                                              fuel=str(cf_id), fuel_type=str(cf_id), custom_factor_id=cf_id))
    assert r.status_code == 201, r.get_json()
    with app.app_context():
        rec = db.session.get(Emission, r.get_json()["id"])
        assert rec.fuel_type == "Explore Lib Factor"
        assert rec.co2_emissions == pytest.approx(1000 * SCF_PER_M3 * 2.0 / 1000, rel=1e-4)


def test_18_scope2_create_is_audited_and_listed(client, admin, app):
    from models import ActivityLog

    uid, fid = admin
    login(client, uid)
    r = client.post("/api/scope2", json={"year": 2026, "month": 3, "facility_id": fid, "source_type": "electricity",
                                          "grid_region": "Algerian National Grid", "electricity_kwh": 1000})
    assert r.status_code == 201, r.get_json()
    sid = r.get_json()["id"]
    with app.app_context():
        assert ActivityLog.query.filter_by(entity="Scope2Emission", record_id=str(sid), action="CREATE").count() == 1
    row = next(x for x in client.get("/api/scope2").get_json() if x["id"] == sid)
    assert row["uncertainty"] is not None and row["status"] == "Verified"


def test_19_audit_timestamps_carry_utc_offset(client, admin):
    uid, fid = admin
    login(client, uid)
    client.post("/api/emissions", json=s1(fid))
    logs = client.get("/api/audit/?limit=5").get_json()
    items = logs.get("logs") or logs.get("data") or logs
    assert items and items[0]["timestamp"].endswith("+00:00")


def test_drafts_are_not_in_the_review_queue(client, admin):
    uid, fid = admin
    login(client, uid)
    r = client.post("/api/emissions", json=s1(fid, status="Draft", amount=777, quantity=777))
    assert r.status_code == 201
    pending = client.get("/api/emissions/pending").get_json()
    rows = pending.get("records") or pending.get("data") or pending.get("scope1") or []
    assert all(x.get("id") != r.get_json()["id"] for x in rows if str(x.get("scope")) == "1")


def test_11_excel_export_scope2_steam_row(client, admin):
    import openpyxl

    uid, fid = admin
    login(client, uid)
    r = client.post("/api/scope2", json={"year": 2026, "month": 4, "facility_id": fid, "source_type": "indirect_steam",
                                          "amount": 1000, "unit": "mmbtu",
                                          "calc_inputs": {"indirect_steam": {"boiler_eff": 0.8, "trans_loss": 0.1}}})
    assert r.status_code == 201, r.get_json()
    x = client.get("/api/emissions/export?year=2026&scope=2&format=excel")
    assert x.status_code == 200, x.data[:200]
    ws = openpyxl.load_workbook(io.BytesIO(x.data), data_only=True)["Emissions Inventory"]
    rows = [row for row in ws.iter_rows(values_only=True) if row and row[0] == f"S2-{r.get_json()['id']}"]
    assert rows and rows[0][9] == "Purchased steam / heat" and rows[0][10] == 1000 and rows[0][11] == "MMBtu"


_CH4_1E6_M3 = 1e6 * 16.04 / 23.685 / 1000.0  # t CH4 in 1e6 m3 (API Compendium molar volume)


def test_10_ogmp_export_loss_rate_and_reconciliation(client, admin, app):
    import openpyxl
    from extensions import db
    from models import Emission, Facility, ProductionData

    uid, _ = admin
    with app.app_context():
        f = Facility(name="OGMP Explore", region="OGMPX", activity="EP", division="Production", field="OX",
                     segment="Upstream", code=f"OGX-{uuid.uuid4().hex[:6]}")
        db.session.add(f)
        db.session.flush()
        # gross gas 1,000 MMSm3 (the Methane Intensity basis) next to a small raw gas figure
        db.session.add(ProductionData(facility_id=f.id, year=2031, month=1, gas_amount=1000, gas_unit="mscf",
                                      gross_gas_mmsm3=1000.0))
        db.session.add(Emission(facility_id=f.id, year=2031, month=1, process_type="venting", status="Verified",
                                ch4_emissions=_CH4_1E6_M3, co2e_total=_CH4_1E6_M3 * 28, record_id=str(uuid.uuid4())))
        db.session.commit()
        fname = f.name
    login(client, uid)
    x = client.get("/api/reports/ogmp-export?year=2031")
    assert x.status_code == 200, x.data[:300]
    wb = openpyxl.load_workbook(io.BytesIO(x.data), data_only=True)
    summary = [r for r in wb.worksheets[0].iter_rows(values_only=True) if r and r[0] == fname][0]
    # 1e6 m3 of CH4 (677.22 t at 0.67722 kg/m3) over 1e9 m3 gross gas = 0.1 %
    assert summary[8] == pytest.approx(1e9) and summary[11] == pytest.approx(0.1, rel=1e-3)
    rec = [r for r in wb["4. Reconciliation Matrix"].iter_rows(values_only=True) if r and r[0] == fname][0]
    assert rec[7] == "NOT ASSESSED"


def test_d5_qa_summary_counts_stored_scan_outliers(client, admin):
    uid, _ = admin
    login(client, uid)
    d = client.get("/api/qaqc/dashboard").get_json()
    s = d["diagnostics"]["anomalies_summary"]
    listed = [r for r in d.get("flagged_records", []) if "rejected" not in str(r.get("status") or "").lower()]
    assert s["pending"] + s["verified"] >= len([r for r in listed if r.get("source") == "stored_scan"])
