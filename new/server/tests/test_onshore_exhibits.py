"""API Compendium 2021 onshore upstream / midstream exhibits run through the engine — the same path as
POST /api/emissions (resolve_factor + compute_emissions). Inputs are the exhibits' stated inputs,
expected values their printed results (tonnes), read from scratch/2021-API-GHG-Compendium.pdf.

Tolerance is 2 % unless the printed answer is rounded to one or two significant figures.
The engine converts scf -> m3 -> mass with its gas densities (0.6785 / 1.861 kg/m3); the
exhibits use 379.3 scf/lbmol, which differs by about 0.4 %.
"""
import json

import pytest

from calculations.constants import get_active_gwp
from calculations.legacy_engine import compute_emissions
from services.scope1_calc import resolve_factor

CASES = []


def case(ex, title, payload, expect, tol=0.02):
    CASES.append(pytest.param(payload, expect, tol, id=f"{ex} {title}"))


def pl(process, source="default", **inputs):
    p = {"process_type": process, "factor_source": source, "calc_inputs": {process: dict(inputs)}}
    for k in ("amount", "unit"):
        if k in inputs:
            p[k] = inputs[k]
    if "amount" in inputs:
        p["quantity"] = inputs["amount"]
    return p


def act(process, key, amount, unit="", **kw):
    return pl(process, "default", activity_key=key, amount=amount, unit=unit or "count", **kw)


# ---- 6.2 exploration ----
case("6-2", "Oil well test vented, GOR x oil rate x hours",
     pl("well_testing", "specific", vent_method="gor", gor=700, oil_rate=4200, vent_hours=6, ch4_content=70, co2_content=10),
     {"ch4": 9.84, "co2": 3.87})
case("6-5a", "Coal seam drilling gas vented, 19.25e6 scf",
     pl("vented_gas", "specific", gas_volume=19.25e6, gas_volume_unit="scf", ch4_content=88.7, co2_content=10.9),
     {"ch4": 327, "co2": 110})
case("6-5b", "Coal seam well test gas flared, 3 x 6.76e6 scf, C2+ as ethane",
     pl("vented_gas", "specific", gas_volume=3 * 6.76e6, gas_volume_unit="scf", ch4_content=88.7, co2_content=10.9,
        c2plus_content=0.4, disposition="flared", combustion_efficiency=98),
     {"co2": 1050, "ch4": 6.9})
# ---- 6.3 production ----
case("6-7", "Gas well workovers without HF, Table 6-9",
     act("workovers", "wo_gas", 10, ch4_content=70, co2_content=9), {"ch4": 0.42, "co2": 0.15}, tol=0.03)
case("6-9", "Primary heavy oil casing gas, Table 6-12",
     act("casing_gas", "cg_primary_heavy", 100 * 365, "bbl", ch4_content=70, co2_content=9), {"ch4": 102.7, "co2": 36.3})
case("6-10", "Low-pressure casing gas migration, 3 wells",
     act("casing_gas", "cg_migration", 3, activity_days=365, ch4_content=70, co2_content=9), {"ch4": 2.00, "co2": 0.71})
case("6-14", "Kimray pump, production, Table 6-18",
     act("dehydrator", "dh_kimray_production", 25e6 * 365, "scf", ch4_content=82, co2_content=5), {"ch4": 180.7, "co2": 30.3})
case("6-15", "Desiccant dehydrator, Eq 6-16",
     pl("desiccant_dehydrator", "specific", vessel_height_ft=6.40, vessel_diameter_ft=1.60, vessel_pressure_psig=450,
        gas_fraction=45, refills=52, ch4_content=90, co2_content=5),
     {"ch4": 0.16, "co2": 0.025}, tol=0.03)
case("6-16", "AGR vent per unit, Table 6-19",
     act("agr", "agr_unit", 1, activity_days=365), {"ch4": 236.6})
case("6-17", "AGR sour / sweet material balance, Eq 6-18",
     pl("agr", "specific", vent_method="agr_balance", sour_gas_volume=150000, sweet_gas_volume=148500,
        gas_volume_unit="MMscf", sour_co2_content=3.0, sweet_co2_content=2.0),
     {"co2": 80506, "ch4": 2775})
case("6-22", "CO2 EOR injection pump blowdown, Eq 6-20",
     pl("co2_eor", "specific", physical_volume_m3=36.4, co2_density=650, co2_wt_pct=98.5), {"co2": 23}, tol=0.02)
# ---- 6.4 gathering & boosting ----
case("6-23", "G&B pneumatic controllers, type unknown, Table 6-29",
     act("pneumatic", "gb_pc_avg", 80, ch4_content=70, co2_content=9), {"ch4": 85.7, "co2": 30.3})
case("6-24", "G&B reciprocating rod packing, GHGRP factor",
     act("compressor_venting", "gb_rp_ghgrp", 4, activity_hours=8470, ch4_content=70, co2_content=9),
     {"ch4": 0.62, "co2": 0.22})
case("6-26a", "Vessel blowdowns", act("non_routine_venting", "gb_bd_vessel", 5, ch4_content=70, co2_content=8),
     {"ch4": 0.007, "co2": 0.002}, tol=0.06)
case("6-26b", "Compressor blowdowns", act("non_routine_venting", "gb_bd_compressor", 1, ch4_content=70, co2_content=8),
     {"ch4": 0.064, "co2": 0.020}, tol=0.03)
case("6-26c", "Gathering pipeline blowdowns", act("non_routine_venting", "gb_bd_pipeline", 5, ch4_content=70, co2_content=8),
     {"ch4": 0.026, "co2": 0.008}, tol=0.06)
case("6-27a", "PRV releases", act("non_routine_venting", "gb_prv", 6), {"ch4": 0.0039})
case("6-27b", "Pipeline dig-ins", act("non_routine_venting", "gb_digins", 6), {"ch4": 0.077})
case("6-27c", "Compressor starts", act("non_routine_venting", "gb_compressor_starts", 1), {"ch4": 0.16})
case("6-27d", "Oil pump station maintenance", act("non_routine_venting", "gb_oil_pump_station", 1), {"ch4": 0.00071})
# ---- 6.5 processing ----
case("6-28a", "Glycol dehydrator vent, processing, Table 6-35",
     act("dehydrator", "dh_glycol_processing", 25e6 * 365, "scf", ch4_content=90), {"ch4": 22.06})
case("6-28b", "Kimray pump, processing, Table 6-36",
     act("dehydrator", "dh_kimray_processing", 25e6 * 365, "scf", ch4_content=90, co2_content=5), {"ch4": 32.26, "co2": 4.93})
case("6-29", "Natural gas blanketed tank, actual -> standard volume",
     pl("tank", "specific", vent_method="actual", actual_volume=32000, actual_unit="bbl", gas_temp_f=75,
        ch4_content=82, co2_content=1),
     {"ch4": 2.74, "co2": 0.09}, tol=0.03)
case("6-30", "Processing non-routine, per 10^6 m3", act("non_routine_venting", "proc_non_routine_m3", 20e6 * 365, "m3"),
     {"ch4": 908})
# ---- 6.6 transmission & storage ----
case("6-31a", "Rod packing, operating", act("compressor_venting", "ts_rp_operating", 5, activity_hours=7970, ch4_content=90),
     {"ch4": 180.5})
case("6-31b", "Rod packing, standby pressurised", act("compressor_venting", "ts_rp_standby", 5, activity_hours=630, ch4_content=90),
     {"ch4": 20.9})
case("6-32a", "Centrifugal wet seals", act("compressor_venting", "ts_cent_wet_avg", 3, activity_hours=8760, ch4_content=95),
     {"ch4": 491.1})
case("6-32b", "Centrifugal dry seals", act("compressor_venting", "ts_cent_dry_avg", 2, activity_hours=8760, ch4_content=95),
     {"ch4": 102.2})
case("6-33a", "Transmission station blowdowns", act("non_routine_venting", "ts_station_bd", 2), {"ch4": 108})
case("6-33b", "Transmission pipeline venting", act("non_routine_venting", "ts_pipeline_venting", 50), {"ch4": 31})
# ---- 6.7 distribution ----
case("6-34a", "M&R station blowdowns", act("non_routine_venting", "dist_mr", 3), {"ch4": 0.0087})
case("6-34b", "Odorizer and sampling vents", act("non_routine_venting", "dist_odorizer", 3), {"ch4": 0.068})
case("6-34c", "Distribution pipeline blowdowns", act("non_routine_venting", "dist_pipeline_bd", 20), {"ch4": 0.64})
case("6-34d", "Distribution dig-ins", act("non_routine_venting", "dist_digins", 20), {"ch4": 0.61})
case("6-34e", "Distribution PRVs", act("non_routine_venting", "dist_prv", 20), {"ch4": 0.02}, tol=0.05)
# ---- 6.10 loading ----
case("6-35", "Rail splash loading, dedicated, 12 wt % CH4",
     act("loading", "load_splash_dedicated", 50000, "bbl", toc_ch4_wt=12), {"ch4": 0.554})
# ---- 7.3 fugitives, correlation approach ----
case("7-5", "Correlation approach, 100 flanges",
     pl("fugitive", "specific", fugitive_method="correlation", correlation_type="flange", corr_zero_count=95,
        corr_screened_count=4, screening_ppm=7950, corr_pegged_10k_count=1, operating_hours=8760),
     {"ch4": 0.47})
# ---- Section 4 combustion ----
case("4.5", "Residual fuel by carbon content",
     pl("combustion", "specific", combustion_method="carbon_content", fuel_volume=4e6, fuel_volume_unit="gal",
        fuel_density=8.3, density_unit="lb/gal", carbon_wt_pct=92.3),
     {"co2": 50966})
case("4.7", "Low-NOx gas boiler, equipment basis",
     pl("combustion", "specific", combustion_method="equipment", equipment_type="boiler_ng_controlled",
        fuel_volume=800e6, fuel_volume_unit="scf", hhv_btu_scf=1032),
     {"ch4": 0.83, "n2o": 0.23})
case("4.8", "100 hp gasoline engine, equipment basis",
     pl("combustion", "specific", combustion_method="equipment", equipment_type="ic_gasoline", engine_hp=100,
        load_pct=90, operating_hours=8000),
     {"ch4": 0.62, "n2o": 0.00303})
case("4.12", "Heavy-duty diesel trucks by distance",
     pl("mobile", "specific", combustion_method="vehicle_distance", distance=1_000_000, distance_unit="mile",
        vehicle_type="hd_diesel_advanced", fuel_economy_mpg=8.8, hhv_mmbtu_gal=5.83 / 42, co2_ef_t_mmbtu=0.0822),
     {"co2": 1297, "ch4": 0.048, "n2o": 0.064})
# ---- Section 5 waste gas ----
case("5.2", "Flare from known VOC emission",
     pl("flaring", "specific", combustion_method="flare_voc", voc_mass=2.21, voc_mass_unit="short_ton",
        wt_ch4=2.73, wt_c2h6=0.85, wt_c3h8=1.35, wt_c4h10=0.99, wt_c5h12=0.83, wt_c6plus=2.16, wt_co2=90.43,
        combustion_efficiency=98),
     {"co2": 515.7, "ch4": 1.03})
case("5.3", "Thermal oxidizer on crude loading",
     pl("thermal_oxidizer", "specific", liquid_loaded=4_122_487, liquid_unit="bbl", loading_loss_lb_kgal=1.23,
        voc_fraction_of_toc=85, toc_carbon_wt_pct=82.15, toc_ch4_wt_pct=7.5, destruction_efficiency=99),
     {"co2": 338.9, "ch4": 0.085})


@pytest.mark.parametrize("payload,expect,tol", CASES)
def test_onshore_exhibit(app, payload, expect, tol):
    with app.app_context():
        p = json.loads(json.dumps(payload))
        em, _ = compute_emissions(p, resolve_factor(p) or {}, gwp_dict=get_active_gwp(standard="AR5"))
        for gas, exp in expect.items():
            assert float(em.get(gas) or 0) == pytest.approx(exp, rel=tol), gas


@pytest.mark.parametrize("payload,msg", [
    (act("workovers", "no_such_row", 1), "Unknown activity factor"),
    (act("workovers", "cg_primary_heavy", 10, "bbl"), "does not apply"),
    (act("workovers", "wo_gas", -1), "negative"),
    (act("casing_gas", "cg_primary_heavy", 10, "kg"), "unit"),
    (pl("workovers", "default", amount=3, unit="count"), "Select an activity factor"),
    (pl("vented_gas", "specific", gas_volume=1e6, gas_volume_unit="scf", ch4_content=90, co2_content=20), "exceeds 100"),
    (pl("combustion", "specific", combustion_method="equipment", equipment_type="warp_drive", energy_mmbtu=1), "Unknown equipment"),
    (pl("fugitive", "specific", fugitive_method="correlation", correlation_type="teapot", screening_ppm=10,
        corr_screened_count=1), "Unknown correlation component"),
])
def test_invalid_inputs_rejected(app, payload, msg):
    with app.app_context():
        p = json.loads(json.dumps(payload))
        with pytest.raises(Exception, match=msg):
            compute_emissions(p, resolve_factor(p) or {}, gwp_dict=get_active_gwp(standard="AR5"))


def test_activity_factor_endpoint_requires_login(client):
    assert client.get("/api/activity-factors").status_code == 401
    assert client.get("/api/equipment-combustion-factors").status_code == 401


@pytest.fixture
def plain_user(app):
    from extensions import db
    from models import User

    with app.app_context():
        u = User.query.filter_by(email="onshore_exhibits_user@test.com").first()
        if not u:
            u = User(email="onshore_exhibits_user@test.com", fullName="Onshore User", orgName="TestCorp",
                     sector="Energy", role="user", location="Global Corporate Head Office")
            u.set_password("OnshorePass123!")
            db.session.add(u)
            db.session.commit()
        return u.id


def test_activity_factor_endpoint_filters_by_process(client, plain_user):
    with client.session_transaction() as sess:
        sess["user_id"] = plain_user
    rows = client.get("/api/activity-factors?process=pneumatic_devices").get_json()["factors"]
    assert rows and all("pneumatic" in r["processes"] for r in rows)
    assert {"gb_pc_avg"} <= {r["key"] for r in rows}
    eq = client.get("/api/equipment-combustion-factors").get_json()["factors"]
    assert "boiler_ng_controlled" in {r["key"] for r in eq}


# ---- full POST /api/emissions path, payloads shaped like the Scope 1 form sends them ----
@pytest.fixture
def api_ctx(app, client):
    from tests.audit_helpers import login, make_facility, make_user

    with app.app_context():
        f = make_facility(region="West")
        login(client, make_user("admin", "Global"))
        yield f


def _post(client, f, process, source, **inputs):
    body = {"facility_id": f.id, "year": 2025, "month": 3, "process_type": process, "factor_source": source,
            "calc_inputs": {process: inputs}}
    if "amount" in inputs:  # the form sends the activity amount at top level and in calc_inputs
        body.update(amount=inputs["amount"], quantity=inputs["amount"], unit=inputs.get("unit"))
    return client.post("/api/emissions/", json=body)


def test_post_activity_factor_record(client, api_ctx):
    r = _post(client, api_ctx, "workovers", "default", activity_key="wo_gas", amount=10, unit="count",
              ch4_content=70, co2_content=9)
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["emissions"]["ch4"] == pytest.approx(0.42, rel=0.03)


def test_post_engineered_record_without_amount(client, api_ctx):
    # Exhibit 6-15: the desiccant method sends vessel inputs only, no activity amount
    r = _post(client, api_ctx, "desiccant_dehydrator", "specific", vent_method="desiccant", vessel_height_ft=6.4,
              vessel_diameter_ft=1.6, vessel_pressure_psig=450, gas_fraction=45, refills=52, ch4_content=90,
              co2_content=5)
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["emissions"]["ch4"] == pytest.approx(0.16, rel=0.03)


def test_post_combustion_method_record(client, api_ctx):
    # Exhibit 5.3 through the thermal oxidizer process
    r = _post(client, api_ctx, "thermal_oxidizer", "specific", combustion_method="thermal_oxidizer",
              liquid_loaded=4_122_487, liquid_unit="bbl", loading_loss_lb_kgal=1.23, voc_fraction_of_toc=85,
              toc_carbon_wt_pct=82.15, toc_ch4_wt_pct=7.5, destruction_efficiency=99)
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["emissions"]["co2"] == pytest.approx(338.9, rel=0.02)


def test_post_activity_process_without_method_is_rejected(client, api_ctx):
    r = _post(client, api_ctx, "workovers", "default", amount=3, unit="count")
    assert r.status_code in (400, 422)
