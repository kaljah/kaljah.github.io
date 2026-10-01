"""Scope 1 Compendium exhibit audit, 2026-10-01 (audit/SCOPE1_100K_BULK_AUDIT_2026-10-01.md, section 8).

API Compendium 2021 worked examples run through the real import thread (the path the UI wizard and the
HTTP upload use), plus the defects they exposed (S1K-F21 .. F30). Expected values are the exhibits'
printed answers; tolerances cover their rounding and their 16 / 44 molecular weights.
"""
import csv
import io
import os
import tempfile

import pytest

from app import app as flask_app
from background_processor import _process_file_thread, upload_jobs, upload_jobs_lock
from extensions import db
from models import Emission, Facility, User

FACILITY = "S1K Exhibit 1001"


@pytest.fixture(scope="module")
def user_id():
    with flask_app.app_context():
        u = User.query.filter_by(email="s1k_exhibit_1001@ghg.com").first()
        if not u:
            u = User(email="s1k_exhibit_1001@ghg.com", fullName="S1K", orgName="Audit", sector="Oil & Gas",
                     role="admin", location="Global")
            u.set_password("S1kExhibit1001!")
            db.session.add(u)
            db.session.commit()
        if not Facility.query.filter_by(name=FACILITY).first():
            db.session.add(Facility(name=FACILITY, location="Illizi", country="Algeria", region="Illizi",
                                    division="Production", field="IA", segment="Upstream", activity="E&P"))
            db.session.commit()
        return u.id


def _run(user_id, row):
    """One CSV row through the import thread -> ({co2, ch4, n2o} tonnes or None, skip reason)."""
    ref = "S1KX-" + os.urandom(4).hex()
    row = {"date": "2024-12", "facility_name": FACILITY, "source_ref": ref, **row}
    buf = io.StringIO()
    w = csv.DictWriter(buf, list(row))
    w.writeheader()
    w.writerow(row)
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.write(fd, buf.getvalue().encode())
    os.close(fd)
    job = "job-s1kx-" + os.urandom(5).hex()
    with upload_jobs_lock:
        upload_jobs[job] = {"status": "processing", "progress": 0, "processed": 0, "total": 0, "errors": [],
                            "skipped": [], "error_csv_path": None, "anomalies": []}
    try:
        _process_file_thread(app=flask_app, job_id=job, file_path=path, original_filename="s1kx.csv",
                             user_id=user_id, global_factor_type="auto", provided_mapping=None, scope="1",
                             overwrite_duplicates=True)
    finally:
        if os.path.exists(path):
            os.remove(path)
    with upload_jobs_lock:
        reason = next((s["reason"] for s in upload_jobs[job]["skipped"]), None)
    with flask_app.app_context():
        e = Emission.query.filter_by(data_source_ref=ref).first()
        if e is None:
            return None, reason
        return {"co2": e.co2_emissions, "ch4": e.ch4_emissions, "n2o": e.n2o_emissions}, reason


def _ok(user_id, row):
    got, reason = _run(user_id, row)
    assert got is not None, reason
    return got


def _refused(user_id, row):
    got, reason = _run(user_id, row)
    assert got is None, f"accepted: {got}"
    return reason


# --- F21: AGR CO2 material balance (Eq 6-18) with the outlet-stream shrinkage --------------------
def test_f21_agr_balance_exhibit_6_17(user_id):
    got = _ok(user_id, dict(process_type="agr", factor_type="specific", quantity="150000", unit="MMscf",
                            agr_co2_in="3", agr_co2_out="2"))
    assert got["co2"] == pytest.approx(80506.0, rel=2e-3)      # was 78,925 t (inlet volume for both streams)
    assert got["ch4"] == pytest.approx(2775.0, rel=1e-3)


# --- F22: tank flash gas default CH4 content (27.4 % crude, 36.3 % condensate) ------------------
def test_f22_tank_gor_without_analysis_exhibit_6_19(user_id):
    got = _ok(user_id, dict(process_type="tank_flashing", factor_type="specific", quantity=str(451 * 365),
                            unit="bbl", tank_gor="47"))
    assert got["ch4"] == pytest.approx(40.6, rel=5e-3)         # was 126 t (85 % CH4)


def test_f22_condensate_gor_default_is_36_3_percent(user_id):
    got = _ok(user_id, dict(process_type="tank_flashing", factor_type="specific", quantity="10000", unit="bbl",
                            tank_gor="50", tank_liquid_type="condensate"))
    scf = 10000 * 50
    assert got["ch4"] == pytest.approx(scf * 0.363 / 379.3 * 16.04 / 2204.62, rel=5e-3)


# --- F23: Table 6-22 tank factor is not scaled by the separator gas CH4 content ------------------
def test_f23_tank_table_factor_unscaled_exhibit_6_20(user_id):
    got = _ok(user_id, dict(process_type="tank_flashing", factor_type="specific", quantity=str(451 * 365),
                            unit="bbl", tank_method="table_6_22", ch4_content="58"))
    assert got["ch4"] == pytest.approx(31.8, rel=5e-3)         # was 22.6 t (x 58 / 81.6)


# --- F24 / F25: Tier 3 liquid fuel carbon content (Eq 4-5) and density units --------------------
_RFO = dict(process_type="combustion", fuel="Residual Fuel Oil (No. 6)", factor_type="specific",
            quantity="4000000", unit="gal", hhv="150000", hhv_unit="Btu/gal", combustion_efficiency="100")


def test_f24_carbon_content_exhibit_4_5(user_id):
    got = _ok(user_id, dict(_RFO, carbon_content="92.3", density="8.3", density_unit="lb/gal"))
    assert got["co2"] == pytest.approx(50966.0, rel=2e-3)      # was 45,060 t: the catalog CO2 factor
    assert got["ch4"] == pytest.approx(1.80, rel=1e-2)         # CH4 / N2O stay on the fuel factors
    assert got["n2o"] == pytest.approx(0.36, rel=1e-2)


def test_f25_density_kg_m3_equals_lb_gal(user_id):
    a = _ok(user_id, dict(_RFO, carbon_content="92.3", density="8.3", density_unit="lb/gal"))
    b = _ok(user_id, dict(_RFO, carbon_content="92.3", density=str(8.3 * 119.826427)))   # form: kg/m3
    assert a["co2"] == pytest.approx(b["co2"], rel=1e-9)


def test_f24_carbon_content_on_mass_quantity(user_id):
    # the density is still needed for CH4 / N2O on the per-gallon heating value, not for the carbon balance
    got = _ok(user_id, dict(_RFO, quantity="1000", unit="t", carbon_content="85", density="990"))
    assert got["co2"] == pytest.approx(1000 * 0.85 * 44.01 / 12.011, rel=1e-6)


def test_f24_carbon_content_on_liquid_volume_needs_density(user_id):
    assert "density" in _refused(user_id, dict(_RFO, carbon_content="92.3"))


def test_f25_unknown_density_unit_refused(user_id):
    assert "density unit" in _refused(user_id, dict(_RFO, carbon_content="92.3", density="8.3",
                                                    density_unit="stone/pint"))


# --- F27: liquids unloading Eq 6-10 flow-line term per event; SFR rate units ----------------------
_UNLOAD = dict(process_type="unloading", factor_type="specific", quantity="12", unit="events",
               unloading_type="non_plunger", unload_depth="12000", unload_diam="10", unload_press="250",
               unload_freq="12", ch4_content="80", co2_content="3", unload_flare_eff="0")


def test_f27_unloading_exhibit_6_8(user_id):
    got = _ok(user_id, dict(_UNLOAD, sfr="35000", hours_open="1"))
    assert got["ch4"] == pytest.approx(20.39, rel=5e-3)


def test_f27_flowline_term_counted_per_event(user_id):
    base = _ok(user_id, dict(_UNLOAD, sfr="35000", hours_open="1"))
    longer = _ok(user_id, dict(_UNLOAD, sfr="35000", hours_open="3"))
    extra_scf = 12 * 35000 * (3 - 1)                             # was 35,000 x 2 (once per well-year)
    assert longer["ch4"] - base["ch4"] == pytest.approx(extra_scf * 0.80 / 379.3 * 16.04 / 2204.62, rel=5e-3)


def test_f27_sfr_mcf_per_day(user_id):
    a = _ok(user_id, dict(_UNLOAD, sfr="35000", hours_open="3"))
    b = _ok(user_id, dict(_UNLOAD, sfr=str(35000 * 24 / 1000), sfr_unit="Mcf/day", hours_open="3"))
    assert a["ch4"] == pytest.approx(b["ch4"], rel=1e-6)        # Mcf/day was read as scf/day


# --- F28: no silent 85 % / 70 % CH4 for an unanalysed gas -------------------------------------
def test_f28_completion_volume_needs_ch4(user_id):
    reason = _refused(user_id, dict(process_type="completions", factor_type="specific", comp_method="metered_volume",
                                    quantity="1480000", unit="scf", comp_duration="20"))
    assert "CH4" in reason


def test_f28_associated_gas_needs_ch4(user_id):
    reason = _refused(user_id, dict(process_type="associated_gas_venting", factor_type="custom",
                                    oil_production="5200", oil_unit="bbl/day", quantity="5200", unit="bbl/day",
                                    gor="700", gor_unit="scf/bbl", venting_duration="15", period_duration="15"))
    assert "CH4" in reason


# --- F29: flare defaults (98 % conversion, 2 % / 0.5 % residual CH4) and flare_voc N2O ----------
def test_f29_flare_voc_n2o_exhibit_5_2(user_id):
    got = _ok(user_id, dict(process_type="flaring", factor_type="specific", combustion_method="flare_voc",
                            voc_mass="2.21", voc_mass_unit="short_ton", wt_ch4="2.73", wt_c2h6="0.85",
                            wt_c3h8="1.35", wt_c4h10="0.99", wt_c5h12="0.83", wt_c6plus="2.16", wt_co2="90.43",
                            combustion_efficiency="98"))
    assert got["co2"] == pytest.approx(515.7, rel=5e-3)
    assert got["n2o"] == pytest.approx(7.76e-4, rel=1e-2)       # was 0


def test_f29_flaring_default_efficiencies():
    from calculations.combustion import FlaringCalculator

    for ftype, eta_d in (("elevated", 0.98), ("enclosed", 0.995), ("pit", 0.98)):
        res = FlaringCalculator().calculate(gas_volume=1000.0, ch4_fraction=1.0, uncertainties={}, fuel_unit="m3",
                                            flare_type=ftype, c1=1.0)
        co2 = res["results"]["co2"]["value"]
        ch4 = res["results"]["ch4"]["value"]
        from calculations.units import CONVERSIONS
        assert co2 == pytest.approx(1000 * 0.98 * CONVERSIONS["density_co2"] / 1000, rel=1e-6), ftype
        assert ch4 == pytest.approx(1000 * (1 - eta_d) * CONVERSIONS["density_ch4"] / 1000, rel=1e-6), ftype


# --- Exhibits that were already right stay right ---------------------------------------------
@pytest.mark.parametrize("row,expect", [
    (dict(process_type="dehydrator", factor_type="default", activity_key="dh_kimray_production",
          quantity=str(25 * 365), unit="MMscf", ch4_content="82", co2_content="5"), {"ch4": 180.7, "co2": 30.3}),
    (dict(process_type="co2_eor", factor_type="specific", vent_method="co2_mass", physical_volume_m3="36.4",
          co2_density="650", co2_wt_pct="98.5", events="1"), {"co2": 23.3}),
    (dict(process_type="loading", factor_type="default", activity_key="load_splash_dedicated", quantity="50000",
          unit="bbl", toc_ch4_wt="12"), {"ch4": 0.554}),
    (dict(process_type="fugitive", factor_type="specific", fugitive_method="correlation", component_type="flange",
          corr_zero_count="95", corr_screened_count="4", fugitive_ppm="7950", corr_pegged_10k_count="1",
          operating_hours="8760"), {"ch4": 0.47}),
], ids=["6-14", "6-22", "6-35", "7-5"])
def test_exhibits_unchanged(user_id, row, expect):
    got = _ok(user_id, row)
    for gas, v in expect.items():
        assert got[gas] == pytest.approx(v, rel=1.5e-2), gas
