"""Scope 1 100,000-row bulk import audit, 2026-10-01 (audit/SCOPE1_100K_BULK_AUDIT_2026-10-01.md).

Each finding (S1K-F1 .. F20) is reproduced through the real import thread with a test row and, where
the outcome is a value, a reference row that states the same physical activity in a unit the
platform handled correctly before the fixes.
"""
import csv
import io
import os
import tempfile

import pytest

from app import app as flask_app
from background_processor import (
    MAX_IMPORT_ROWS, _build_mapping, _process_file_thread, get_job_status, upload_jobs, upload_jobs_lock,
)
from extensions import db
from models import Emission, Facility, User

FACILITY = "S1K Audit 1001"


@pytest.fixture(scope="module")
def user_id():
    with flask_app.app_context():
        u = User.query.filter_by(email="s1k_audit_1001@ghg.com").first()
        if not u:
            u = User(email="s1k_audit_1001@ghg.com", fullName="S1K", orgName="Audit", sector="Oil & Gas",
                     role="admin", location="Global")
            u.set_password("S1kAudit1001!")
            db.session.add(u)
            db.session.commit()
        if not Facility.query.filter_by(name=FACILITY).first():
            db.session.add(Facility(name=FACILITY, location="Illizi", country="Algeria", region="Illizi",
                                    division="Production", field="IA", segment="Upstream", activity="E&P"))
            db.session.commit()
        return u.id


def _upload(rows, user_id):
    header = ["date", "facility_name"] + sorted({k for r in rows for k in r}, key=lambda k: (k != "source_ref", k))
    buf = io.StringIO()
    w = csv.DictWriter(buf, header)
    w.writeheader()
    for r in rows:
        w.writerow({"date": "2024-03", "facility_name": FACILITY, **r})
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.write(fd, buf.getvalue().encode())
    os.close(fd)
    job = "job-s1k-" + os.urandom(5).hex()
    with upload_jobs_lock:
        upload_jobs[job] = {"status": "processing", "progress": 0, "processed": 0, "total": 0, "errors": [],
                            "skipped": [], "error_csv_path": None, "anomalies": []}
    try:
        _process_file_thread(app=flask_app, job_id=job, file_path=path, original_filename="s1k.csv",
                             user_id=user_id, global_factor_type="auto", provided_mapping=None, scope="1",
                             overwrite_duplicates=True)
    finally:
        if os.path.exists(path):
            os.remove(path)
    with upload_jobs_lock:
        skipped = {rows[s["row"] - 2]["source_ref"]: s["reason"] for s in upload_jobs[job]["skipped"]}
    with flask_app.app_context():
        recs = {e.data_source_ref: e for e in Emission.query.filter(
            Emission.data_source_ref.in_([r["source_ref"] for r in rows])).all()}
        out = {}
        for r in rows:
            e = recs.get(r["source_ref"])
            out[r["source_ref"]] = (None if e is None else {
                "co2": e.co2_emissions, "ch4": e.ch4_emissions, "n2o": e.n2o_emissions, "co2e": e.co2e_total,
                "qty": e.quantity, "unit": e.unit, "activity": e.activity, "region": e.region,
            }, skipped.get(r["source_ref"]))
    return out, get_job_status(job)


def _ref(tag):
    return f"S1K-{tag}-{os.urandom(3).hex()}"


def _pair(user_id, test, ref):
    a, b = _ref("t"), _ref("r")
    res, _ = _upload([dict(test, source_ref=a), dict(ref, source_ref=b)], user_id)
    return res[a], res[b]


def _one(user_id, test):
    a = _ref("t")
    res, _ = _upload([dict(test, source_ref=a)], user_id)
    return res[a]


def _close(x, y, tol=1e-6):
    return abs(x - y) <= tol * max(abs(x), abs(y), 1e-12)


# --- F1: Tier 3 combustion with site HHV + catalog factor and no gas analysis -------------------
def test_f1_tier3_hhv_without_composition_keeps_factor_co2(user_id):
    (t, err), (r, _) = _pair(
        user_id,
        dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="Mscf", factor_type="specific",
             hhv="1020", combustion_efficiency="99.5"),
        dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="Mscf", factor_type="default"))
    assert t is not None, err
    assert t["co2"] > 50 and _close(t["co2"], r["co2"])        # 1,020 MMBtu x 53.06 kg = 54.1 t


def test_f1_composition_still_drives_carbon_balance(user_id):
    t, err = _one(user_id, dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="Mscf",
                                factor_type="specific", hhv="1020", combustion_efficiency="99.5", c1="95", c2="3"))
    assert t is not None, err
    assert t["co2"] > 50


# --- F2: Coke Oven Gas at Tier 3 ------------------------------------------------------------------
def test_f2_coke_oven_gas_tier3_uses_gas_basis(user_id):
    t, err = _one(user_id, dict(process_type="combustion", fuel="Coke Oven Gas", quantity="1000", unit="Mscf",
                                factor_type="specific", hhv="599", combustion_efficiency="99", c1="28", c2="3"))
    assert t is not None, err
    assert t["co2"] > 0


# --- F3: tank throughput units ----------------------------------------------------------------------
TANK = dict(process_type="tank_flashing", factor_type="specific", tank_gor="85", tank_ch4_content="65",
            tank_control_eff="0")


def test_f3_tank_kbbl_converted(user_id):
    (t, err), (r, _) = _pair(user_id, dict(TANK, quantity="5", unit="kbbl", tank_unit="kbbl"),
                             dict(TANK, quantity="5000", unit="bbl", tank_unit="bbl"))
    assert t is not None, err
    assert _close(t["co2e"], r["co2e"])


@pytest.mark.parametrize("u", ["tonne", "kg", "MMBtu", "scf"])
def test_f3_tank_non_liquid_volume_refused(user_id, u):
    t, err = _one(user_id, dict(TANK, quantity="5000", unit=u, tank_unit=u))
    assert t is None and err


# --- F4: pneumatic bleed units --------------------------------------------------------------------
PNEU = dict(process_type="pneumatic", quantity="25", unit="devices", pneu_count="25", pneu_hours="744",
            pneu_ch4_content="85", factor_type="specific")


@pytest.mark.parametrize("u", ["m³", "Sm3", "M3", "m3/hr"])
def test_f4_pneumatic_m3_spellings(user_id, u):
    (t, err), (r, _) = _pair(user_id, dict(PNEU, pneu_bleed_rate="0.169901", pneu_bleed_unit=u),
                             dict(PNEU, pneu_bleed_rate="6", pneu_bleed_unit="scf"))
    assert t is not None, err
    assert _close(t["co2e"], r["co2e"], 1e-4)     # 0.169901 m3/h = 6.000 scf/h


@pytest.mark.parametrize("u", ["lb/hr", "kg/hr", "furlongs"])
def test_f4_pneumatic_mass_or_unknown_rate_refused(user_id, u):
    t, err = _one(user_id, dict(PNEU, pneu_bleed_rate="6", pneu_bleed_unit=u))
    assert t is None and "bleed rate unit" in err.lower()


# --- F5 / F20: associated gas Tier 3 vent rate --------------------------------------------------------
AGV3 = dict(process_type="associated_gas_venting", venting_duration="100", ch4_content="75", co2_content="3",
            factor_type="specific")


def test_f5_vent_rate_mcf_per_day(user_id):
    (t, err), (r, _) = _pair(user_id, dict(AGV3, vent_rate="24", vent_rate_unit="Mcf/day"),
                             dict(AGV3, vent_rate="1000", vent_rate_unit="scfh"))
    assert t is not None, err
    assert _close(t["co2e"], r["co2e"])


def test_f5_unknown_vent_rate_unit_refused(user_id):
    t, err = _one(user_id, dict(AGV3, vent_rate="24", vent_rate_unit="lb/hr"))
    assert t is None and err


def test_f20_tier3_vent_duration_is_hours(user_id):
    # 1,000 scf/h x 100 h = 100,000 scf: CH4 = 1e5 x 0.75 x 16.04 / 379.3 lb = 3,171.6 lb = 1.4386 t
    t, err = _one(user_id, dict(AGV3, vent_rate="1000", vent_rate_unit="scfh"))
    assert t is not None, err
    assert _close(t["ch4"], 1e5 * 0.75 * 16.04 / 379.3 * 0.45359237 / 1000, 1e-3)


# --- F6: Mt -------------------------------------------------------------------------------------------
@pytest.mark.parametrize("u", ["Mt", "MT", "mt"])
def test_f6_mt_refused(user_id, u):
    t, err = _one(user_id, dict(process_type="combustion", fuel="Bituminous Coal", quantity="1", unit=u,
                                factor_type="default"))
    assert t is None and "ambiguous" in err


# --- F7: unknown temperature / pressure units -----------------------------------------------------------
COMP = dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="m3", factor_type="specific",
            hhv="1020", combustion_efficiency="99.5", c1="90", c2="5")


def test_f7_unknown_pressure_unit_refused(user_id):
    t, err = _one(user_id, dict(COMP, operating_temperature="15", temp_unit="C", operating_pressure="10",
                                press_unit="kg/cm2"))
    assert t is None and "pressure unit" in err


def test_f7_unknown_temperature_unit_refused(user_id):
    t, err = _one(user_id, dict(COMP, operating_temperature="60", temp_unit="deg", operating_pressure="0",
                                press_unit="psig"))
    assert t is None and "temperature unit" in err


def test_f7_mmhg_is_absolute(user_id):
    (t, err), (r, _) = _pair(user_id,
                             dict(COMP, operating_temperature="15.5556", temp_unit="C", operating_pressure="760",
                                  press_unit="mmHg"),
                             dict(COMP, operating_temperature="15.5556", temp_unit="C", operating_pressure="14.696",
                                  press_unit="psia"))
    assert t is not None, err
    assert _close(t["co2e"], r["co2e"], 1e-4)


# --- F8 / F9: contradicting units -----------------------------------------------------------------------------
def test_f8_quantity_cell_unit_must_match(user_id):
    t, err = _one(user_id, dict(process_type="combustion", fuel="Natural Gas", quantity="928 m3", unit="scf",
                                factor_type="default"))
    assert t is None and "carries the unit" in err
    t, err = _one(user_id, dict(process_type="combustion", fuel="Natural Gas", quantity="928 scf", unit="scf",
                                factor_type="default"))
    assert t is not None, err


def test_f9_unit_and_tank_unit_disagree(user_id):
    t, err = _one(user_id, dict(TANK, quantity="1000", unit="bbl", tank_unit="m3"))
    assert t is None and "Contradicting units" in err


# --- F10: unloading factor basis --------------------------------------------------------------------------
@pytest.mark.parametrize("fuel,unit", [("Liquids Unloading - Non-Plunger (≤10 events/yr)", "wells"),
                                       ("Liquids Unloading - Plunger Lift (Tier 1 Default)", "events"),
                                       ("Liquids Unloading - Plunger Lift (Tier 1 Default)", "devices")])
def test_f10_unloading_unit_must_match_factor(user_id, fuel, unit):
    t, err = _one(user_id, dict(process_type="unloading", fuel=fuel, quantity="10", unit=unit, factor_type="default"))
    assert t is None and err


def test_f10_unloading_matching_units_accepted(user_id):
    t, err = _one(user_id, dict(process_type="unloading", fuel="Liquids Unloading - Non-Plunger (≤10 events/yr)",
                                quantity="10", unit="events", factor_type="default"))
    assert t is not None and _close(t["ch4"], 4.12), err


# --- F11: hhv_unit -----------------------------------------------------------------------------------------
def test_f11_hhv_unit_mj_per_m3(user_id):
    (t, err), (r, _) = _pair(user_id, dict(COMP, quantity="1000", unit="Mscf", hhv="37.99", hhv_unit="MJ/m3"),
                             dict(COMP, quantity="1000", unit="Mscf", hhv="1020"))
    assert t is not None, err
    assert _close(t["n2o"], r["n2o"], 1e-3)      # 37.99 MJ/m3 = 1,020 Btu/scf


def test_f11_unknown_hhv_unit_refused(user_id):
    t, err = _one(user_id, dict(COMP, quantity="1000", unit="Mscf", hhv="37.99", hhv_unit="MJ/furlong"))
    assert t is None and err


# --- F12: metadata columns ---------------------------------------------------------------------------------
def test_f12_mapping_keeps_metadata_exact():
    m = _build_mapping(["date", "facility_name", "activity_key", "operating_hours", "blowdown_pressure",
                        "blowdown_events", "comp_gor"], scope="1")
    assert "activity" not in m and "pneu_hours" not in m and "unload_press" not in m
    assert "unload_freq" not in m and "gor" not in m


def test_f12_activity_key_not_stored_as_activity(user_id):
    t, err = _one(user_id, dict(process_type="well_testing", activity_key="wt_gas", quantity="3", unit="count",
                                factor_type="default"))
    assert t is not None, err
    assert t["activity"] == "E&P"


def test_f12_unloading_basin_not_stored_as_region(user_id):
    t, err = _one(user_id, dict(process_type="unloading", quantity="12", unit="events", factor_type="custom",
                                unloading_type="plunger", region="Gulf Coast", ch4_content="87"))
    assert t is not None, err
    assert t["region"] == "Illizi"


# --- F15: oversized file refused before processing -------------------------------------------------------------
def test_f15_oversized_csv_refused_up_front(user_id):
    lines = ["date,facility_name,process_type,fuel,quantity,unit,factor_type,source_ref"]
    lines += [f"2024-03,{FACILITY},combustion,Natural Gas,1,MMBtu,default,BIG-{i}" for i in range(MAX_IMPORT_ROWS + 20)]
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.write(fd, "\n".join(lines).encode())
    os.close(fd)
    job = "job-s1k-big-" + os.urandom(4).hex()
    with upload_jobs_lock:
        upload_jobs[job] = {"status": "processing", "progress": 0, "processed": 0, "total": 0, "errors": [],
                            "skipped": [], "error_csv_path": None, "anomalies": []}
    try:
        _process_file_thread(app=flask_app, job_id=job, file_path=path, original_filename="big.csv", user_id=user_id,
                             global_factor_type="auto", provided_mapping=None, scope="1", overwrite_duplicates=False)
    finally:
        if os.path.exists(path):
            os.remove(path)
    st = get_job_status(job)
    assert st["status"] == "error" and st["processed"] == 0
    assert "No rows were saved" in st["errors"][0]


# --- F16: unit vocabularies --------------------------------------------------------------------------------
@pytest.mark.parametrize("ou", ["bbl/d", "bpd", "gal/day"])
def test_f16_agv_oil_rate_spellings(user_id, ou):
    (t, err), (r, _) = _pair(
        user_id,
        dict(process_type="associated_gas_venting", quantity="100", unit=ou, oil_production="100", oil_unit=ou,
             gor="500", gor_unit="scf/bbl", venting_duration="20", ch4_content="75", co2_content="3", factor_type="custom"),
        dict(process_type="associated_gas_venting", quantity="100", unit="bbl/day", oil_production="100",
             oil_unit="bbl/day", gor="500", gor_unit="scf/bbl", venting_duration="20", ch4_content="75",
             co2_content="3", factor_type="custom"))
    assert t is not None, err
    if ou != "gal/day":
        assert _close(t["co2e"], r["co2e"])
    else:
        assert _close(t["co2e"] * 42, r["co2e"])


def test_f16_agv_unknown_gor_unit_refused(user_id):
    t, err = _one(user_id, dict(process_type="associated_gas_venting", quantity="100", unit="bbl/day",
                                oil_production="100", oil_unit="bbl/day", gor="500", gor_unit="furlongs",
                                venting_duration="20", ch4_content="75", factor_type="custom"))
    assert t is None and "GOR unit" in err


def test_f16_nm3_vented_gas_and_barrels_activity(user_id):
    (t, err), (r, _) = _pair(
        user_id,
        dict(process_type="vented_gas", vent_method="volume", quantity="1000", unit="Nm3", ch4_content="80",
             co2_content="2", factor_type="specific"),
        dict(process_type="vented_gas", vent_method="volume", quantity="1056.9468", unit="Sm3", ch4_content="80",
             co2_content="2", factor_type="specific"))
    assert t is not None, err
    assert _close(t["co2e"], r["co2e"], 1e-4)
    (t, err), (r, _) = _pair(
        user_id, dict(process_type="separation", activity_key="sep_dump_valve_crude", quantity="1000", unit="barrels",
                      factor_type="default"),
        dict(process_type="separation", activity_key="sep_dump_valve_crude", quantity="1000", unit="bbl",
             factor_type="default"))
    assert t is not None, err
    assert _close(t["co2e"], r["co2e"])


@pytest.mark.parametrize("u,mult", [("g/hr", 1000.0), ("kg/day", 24.0)])
def test_f16_leak_rate_units(user_id, u, mult):
    base = dict(process_type="fugitive", fugitive_method="measurement", operating_hours="744", ch4_content="81.6",
                factor_type="specific")
    (t, err), (r, _) = _pair(user_id, dict(base, measured_rate=str(2.5 * mult), rate_unit=u),
                             dict(base, measured_rate="2.5", rate_unit="kg/hr"))
    assert t is not None, err
    assert _close(t["co2e"], r["co2e"])


def test_f16_drilling_hours(user_id):
    (t, err), (r, _) = _pair(
        user_id,
        dict(process_type="drilling", fuel="Drilling - Mud Degassing (Water Based)", quantity="720", unit="hours",
             factor_type="default"),
        dict(process_type="drilling", fuel="Drilling - Mud Degassing (Water Based)", quantity="30", unit="days",
             factor_type="default"))
    assert t is not None, err
    assert _close(t["co2e"], r["co2e"])


@pytest.mark.parametrize("fuel", ["Natural Gas", "Compressed Natural Gas (CNG)"])
@pytest.mark.parametrize("u,ref_u", [("MMcf", "MMscf"), ("kscf", "Mscf")])
def test_f16_composition_method_mmcf(user_id, fuel, u, ref_u):
    (t, err), (r, _) = _pair(user_id, dict(COMP, fuel=fuel, quantity="1", unit=u),
                             dict(COMP, fuel=fuel, quantity="1", unit=ref_u))
    assert t is not None, err
    assert _close(t["co2e"], r["co2e"]) and _close(t["ch4"], r["ch4"])


# --- F17: thousands separators in method columns ---------------------------------------------------------------
def test_f17_thousands_separator_in_method_column(user_id):
    (t, err), (r, _) = _pair(
        user_id,
        dict(process_type="associated_gas_venting", quantity="12,345.6", unit="scf", vent_volume="12,345.6",
             vent_volume_unit="scf", ch4_content="75", co2_content="3", factor_type="specific"),
        dict(process_type="associated_gas_venting", quantity="12345.6", unit="scf", vent_volume="12345.6",
             vent_volume_unit="scf", ch4_content="75", co2_content="3", factor_type="specific"))
    assert t is not None, err
    assert _close(t["co2e"], r["co2e"])


# --- F18: Tier 2 catalog factor + site HHV -----------------------------------------------------------------------
def test_f18_tier2_catalog_with_site_hhv(user_id):
    (t, err), (r, _) = _pair(user_id,
                             dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="Mscf",
                                  factor_type="custom", hhv="1035"),
                             dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="Mscf",
                                  factor_type="default"))
    assert t is not None, err
    assert _close(t["co2"], r["co2"] * 1035 / 1020)


def test_f18_tier2_unknown_name_without_site_props_refused(user_id):
    t, err = _one(user_id, dict(process_type="combustion", fuel="Natural Gas", quantity="1000", unit="Mscf",
                                factor_type="custom"))
    assert t is None and "not found" in err


# --- F19: engineered records keep their activity -----------------------------------------------------------------
def test_f19_engineered_records_have_quantity(user_id):
    t, err = _one(user_id, dict(process_type="completions", comp_method="rate_duration", comp_rate="50",
                                comp_rate_unit="Mcf/day", comp_duration="72", ch4_content="84", co2_content="2",
                                factor_type="specific"))
    assert t is not None, err
    assert t["qty"] and t["unit"] == "scf" and _close(t["qty"], 150000.0, 1e-6)
    t, err = _one(user_id, dict(AGV3, vent_rate="1000", vent_rate_unit="scfh"))
    assert t is not None and t["qty"] and t["unit"] == "scf", err


def test_f9_form_representation_is_not_a_contradiction():
    """The form sends the converted top-level amount (bbl) and the method amount in its own unit (m3):
    the same activity twice, accepted; one number in two units is refused."""
    from calculations import compute_emissions

    m3 = 794.936475
    bbl = m3 * 6.28981077
    base = dict(process_type="tank_flashing", source_type="tank_flashing", factor_source="specific", year=2024,
                month=3)
    tank = dict(tank_gor=85, tank_ch4_content=65, tank_control_eff=0)
    with flask_app.app_context():
        two_reps, _ = compute_emissions(dict(base, amount=bbl, unit="bbl",
                                             calc_inputs={"tank_flashing": dict(tank, amount=m3, tank_unit="m3")}), {})
        ref, _ = compute_emissions(dict(base, amount=5000, unit="bbl",
                                        calc_inputs={"tank_flashing": dict(tank, amount=5000, tank_unit="bbl")}), {})
        assert _close(two_reps["totalCo2e"], ref["totalCo2e"])
        with pytest.raises(ValueError, match="Contradicting units"):
            compute_emissions(dict(base, amount=1000, unit="bbl", tank_unit="m3", **tank), {})
