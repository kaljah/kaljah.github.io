"""Verification test suite for systemic bug fixes across backend routes, services, and calculations.

Validates:
1. `routes/dashboard_ogmp.py`:
   - Bottom-up CH4 query scoped to requested facility_id (no un-scoped cross-facility leakage).
   - Both `facilityId` and `facility_id` query parameters supported.
2. `routes/data.py`:
   - `GET /api/data/production` with `facilityId=all` and `year=all` returns 200 without throwing 400.
   - `GET /api/data/ogmp-levels/logs` with `facility_id=all` returns 200 without throwing 400.
   - `GET /api/data/ogmp-surveys` and `GET /api/data/cbam-exports` support `facility_id`.
3. `routes/dashboard_bridge.py` and `routes/dashboard.py`:
   - All dashboard summary, mitigation, scope3, categorical, and intensity endpoints support snake_case `facility_id`.
4. `routes/equity_routes.py`:
   - Supports camelCase `facilityId` alongside `facility_id`.
5. `routes/emissions.py`:
   - Malformed non-numeric `facility_id` returns 422 instead of crashing with 500.
6. `calculations/vented_production_tank.py`:
   - VBE and Standing empirical equations execute without ZeroDivisionError or OverflowError under extreme boundary inputs.
7. `services/qaqc_dashboard.py`:
   - `completeness` calculation handles zero denominator without ZeroDivisionError.
"""
import pytest
from extensions import db
from models import Emission, LevelUpgradeLog, OgmpSurvey, ProductionData
from tests.audit_helpers import login, make_facility, make_user


@pytest.fixture
def auth_client(client, app):
    """Client authenticated with an admin user."""
    with app.app_context():
        u = make_user("admin", "Global")
    login(client, u)
    return client


def test_ogmp_metrics_facility_scoping_and_param_aliases(auth_client, app):
    """Verify that dashboard ogmp-metrics filters ch4_query by facility_id and supports both casings."""
    test_yr = 2088
    with app.app_context():
        f1 = make_facility(region="West", activity="Upstream")
        f2 = make_facility(region="East", activity="Upstream")

        e1 = Emission(facility_id=f1.id, year=test_yr, status="Verified", ch4_emissions=10.0, co2e_total=280.0, process_type="venting")
        e2 = Emission(facility_id=f2.id, year=test_yr, status="Verified", ch4_emissions=50.0, co2e_total=1400.0, process_type="venting")
        s1 = OgmpSurvey(facility_id=f1.id, year=test_yr, survey_date=f"{test_yr}-06-01", survey_type="Top-Down", estimated_annual_tch4=12.0)
        db.session.add_all([e1, e2, s1])
        db.session.commit()

        fid1 = f1.id
        fid2 = f2.id

    try:
        # Request with camelCase facilityId
        resp1 = auth_client.get(f"/api/dashboard/ogmp-metrics?facilityId={fid1}&year={test_yr}")
        assert resp1.status_code == 200, resp1.get_json()
        d1 = resp1.get_json()
        assert len(d1["facilities"]) == 1
        assert d1["facilities"][0]["facility_id"] == fid1

        # Request with snake_case facility_id
        resp2 = auth_client.get(f"/api/dashboard/ogmp-metrics?facility_id={fid1}&year={test_yr}")
        assert resp2.status_code == 200, resp2.get_json()
        d2 = resp2.get_json()
        assert len(d2["facilities"]) == 1
        assert d2["facilities"][0]["facility_id"] == fid1

        # Request with facilityId=all
        resp_all = auth_client.get(f"/api/dashboard/ogmp-metrics?facilityId=all&year={test_yr}")
        assert resp_all.status_code == 200
        d_all = resp_all.get_json()
        assert len(d_all["facilities"]) >= 2
    finally:
        with app.app_context():
            Emission.query.filter(Emission.year == test_yr).delete()
            OgmpSurvey.query.filter(OgmpSurvey.year == test_yr).delete()
            db.session.commit()


def test_data_routes_all_parameter_handling(auth_client, app):
    """Verify data endpoints handle 'all' parameters and parameter aliases safely."""
    test_yr = 2087
    with app.app_context():
        f = make_facility(region="Central", activity="Upstream")
        fid = f.id

        prod = ProductionData(facility_id=fid, year=test_yr, month=1, gross_gas_mmsm3=1.0)
        survey = OgmpSurvey(facility_id=fid, year=test_yr, survey_date=f"{test_yr}-06-01", survey_type="Top-Down", estimated_annual_tch4=5.0)
        lvl_log = LevelUpgradeLog(facility_id=fid, source_type_code="COMP", old_level=3, new_level=4)
        db.session.add_all([prod, survey, lvl_log])
        db.session.commit()

    try:
        # 1. /api/data/production with facilityId=all and year=all
        r1 = auth_client.get("/api/data/production?facilityId=all&year=all")
        assert r1.status_code == 200, r1.get_json()
        assert isinstance(r1.get_json(), list)

        # 2. /api/data/production with snake_case facility_id
        r2 = auth_client.get(f"/api/data/production?facility_id={fid}&year={test_yr}")
        assert r2.status_code == 200
        assert len(r2.get_json()) >= 1

        # 3. /api/data/ogmp/level-logs with facility_id=all
        r3 = auth_client.get("/api/data/ogmp/level-logs?facility_id=all")
        assert r3.status_code == 200
        assert isinstance(r3.get_json(), list)

        # 4. /api/data/ogmp-surveys with facility_id
        r4 = auth_client.get(f"/api/data/ogmp-surveys?facility_id={fid}")
        assert r4.status_code == 200
        assert len(r4.get_json()) >= 1

        # 5. /api/data/cbam-exports with facility_id
        r5 = auth_client.get(f"/api/data/cbam-exports?facility_id={fid}")
        assert r5.status_code == 200
        assert isinstance(r5.get_json(), list)
    finally:
        with app.app_context():
            ProductionData.query.filter_by(facility_id=fid).delete()
            OgmpSurvey.query.filter_by(facility_id=fid).delete()
            LevelUpgradeLog.query.filter_by(facility_id=fid).delete()
            db.session.commit()


def test_dashboard_routes_snake_case_facility_id(auth_client, app):
    """Verify all dashboard sub-endpoints accept snake_case facility_id."""
    test_yr = 2086
    with app.app_context():
        f = make_facility(region="South", activity="Upstream")
        fid = f.id

        e = Emission(facility_id=fid, year=test_yr, status="Verified", ch4_emissions=1.0, co2e_total=28.0, process_type="venting")
        db.session.add(e)
        db.session.commit()

    try:
        endpoints = [
            f"/api/dashboard/summary?facility_id={fid}&year={test_yr}",
            f"/api/dashboard/batch-all?facility_id={fid}&year={test_yr}",
            f"/api/dashboard/mitigation?facility_id={fid}&year={test_yr}",
            f"/api/dashboard/scope3/summary?facility_id={fid}&year={test_yr}",
            f"/api/dashboard/categorical-breakdown?facility_id={fid}&year={test_yr}",
            f"/api/dashboard/intensity-stats?facility_id={fid}&year={test_yr}",
            f"/api/dashboard/yoy-bridge?facility_id={fid}&year={test_yr}",
        ]
        for ep in endpoints:
            res = auth_client.get(ep)
            assert res.status_code == 200, f"Failed on {ep}: {res.get_json()}"
    finally:
        with app.app_context():
            Emission.query.filter(Emission.facility_id == fid).delete()
            db.session.commit()


def test_equity_routes_camel_case_facility_id(auth_client, app):
    """Verify equity routes accept camelCase facilityId."""
    with app.app_context():
        f = make_facility(region="North", activity="Upstream")
        fid = f.id

    r1 = auth_client.get(f"/api/equity/shares?facilityId={fid}")
    assert r1.status_code == 200
    assert isinstance(r1.get_json(), list)

    r2 = auth_client.get(f"/api/equity/allocation?facilityId={fid}&year=2025")
    assert r2.status_code == 200
    assert isinstance(r2.get_json(), list)


def test_emissions_malformed_facility_id_handled_gracefully(auth_client):
    """Verify malformed non-numeric facility_id returns 422 cleanly without 500 error."""
    resp = auth_client.get("/api/emissions?facility_id=not_an_int&year=2025")
    assert resp.status_code == 422


def test_tank_flashing_empirical_extreme_inputs():
    """Verify VBE and Standing empirical equations handle extreme inputs without ZeroDivision or Overflow."""
    from calculations.vented_production_tank import TankFlashingCalculator
    calc = TankFlashingCalculator()

    # VBE extreme inputs: extreme negative temperature, negative API gravity, extreme pressure
    res_vbe = calc.calculate(
        throughput=100.0,
        method="vbe",
        api_gravity=-50.0,  # Negative API bounded to >= 0
        separator_pressure_psig=50000.0,  # Huge pressure
        separator_temp_f=-500.0,  # Temperature below absolute zero bounded
        ch4_content=0.85,
    )
    assert res_vbe["results"]["ch4"]["value"] >= 0.0
    assert res_vbe["total_co2e"] >= 0.0

    # Standing extreme inputs: extreme temp, negative API, extreme pressure
    res_st = calc.calculate(
        throughput=100.0,
        method="standing",
        api_gravity=-131.5,  # API exactly hitting 131.5 denominator singularity bounded
        separator_pressure_psig=10000.0,
        separator_temp_f=-500.0,
        tank_temp_f=-500.0,
        ch4_content=0.85,
    )
    assert res_st["results"]["ch4"]["value"] >= 0.0
    assert res_st["total_co2e"] >= 0.0


def test_qaqc_dashboard_completeness_zero_denominator():
    """Verify qaqc completeness handles zero totals without ZeroDivisionError."""
    from services.qaqc_dashboard import completeness
    h_zero = {
        "total": 0,
        "s1": 0,
        "combustion": 0,
        "missing_facility": 0,
        "missing_fuel": 0,
        "missing_amount": 0,
        "missing_co2e": 0,
    }
    dims, score = completeness(h_zero)
    assert score == 100.0
    assert all(v == 100.0 for v in dims.values())


def test_dashboard_top_emitters_limit_non_integer(auth_client):
    """Verify /api/dashboard/equipment-emissions with non-integer limit returns 200 without crashing."""
    res = auth_client.get("/api/dashboard/equipment-emissions?limit=abc&year=2025")
    assert res.status_code == 200
    res_neg = auth_client.get("/api/dashboard/equipment-emissions?limit=-5&year=2025")
    assert res_neg.status_code == 200


def test_sbti_trajectory_invalid_facility_id(auth_client, app):
    """Verify /api/dashboard/sbti-trajectory returns 400 or 422 on invalid non-integer facility_id."""
    res = auth_client.get("/api/dashboard/sbti-trajectory?facility_id=not_an_int")
    assert res.status_code in (400, 422)
    assert "Invalid facility_id" in res.get_json().get("error", "") or "facility" in res.get_json().get("error", "").lower()


def test_notifications_malformed_facility_id_rbac(auth_client, client, app):
    """Verify broadcast notifications with malformed facility_id in metadata do not leak to IT users."""
    import json
    from models import Notification
    with app.app_context():
        it_user = make_user("it_admin", "Global")
        notif = Notification(
            title="LDAR Leak Test",
            message="Alert",
            user_id=None,
            metadata_json=json.dumps({"facility_id": "malformed_fid"})
        )
        db.session.add(notif)
        db.session.commit()
        nid = notif.id

    try:
        login(client, it_user)
        res = client.get("/api/notifications/")
        assert res.status_code == 200
        notifs = res.get_json()
        # IT user must NOT receive facility-scoped notification even if facility_id is malformed string
        assert not any(n["id"] == nid for n in notifs)
    finally:
        with app.app_context():
            Notification.query.filter_by(id=nid).delete()
            db.session.commit()


def test_empty_json_payloads_return_400_not_500(auth_client, app):
    """Verify routes that parse JSON bodies do not crash with 500 when empty body is sent."""
    # 1. Custom factors import with empty body
    r1 = auth_client.post("/api/custom-factors/import", data="", content_type="application/json")
    assert r1.status_code == 400
    assert "No factors provided" in r1.get_json().get("error", "")

    # 2. Emissions import with empty body
    r2 = auth_client.post("/api/emissions/import", data="", content_type="application/json")
    assert r2.status_code == 400
    assert "No records provided" in r2.get_json().get("error", "")

    # 3. Auth profile update with empty body
    r3 = auth_client.put("/api/auth/profile", data="", content_type="application/json")
    assert r3.status_code == 200


def test_ldar_all_status_filters(auth_client, app):
    """Verify LDAR list endpoints do not return empty lists when status=all or leak_status=all is queried."""
    from models import ComponentInventory, FugitiveSurvey
    with app.app_context():
        fac = make_facility(region="LDAR_Test", activity="Upstream")
        fid = fac.id
        comp = ComponentInventory(
            facility_id=fid,
            equipment_type="Valves",
            component_type="Gate Valve",
            service_type="Gas",
            quantity=5,
            operating_hours=8760,
            status="Active"
        )
        surv = FugitiveSurvey(
            facility_id=fid,
            survey_method="Method 21",
            survey_date="2025-05-01",
            leak_status="Non-leaking",
            leaking_hours=8760
        )
        db.session.add_all([comp, surv])
        db.session.commit()
        cid = comp.id
        sid = surv.id

    try:
        # Check components with status=all
        r_c = auth_client.get(f"/api/ldar/components?facility_id={fid}&status=all")
        assert r_c.status_code == 200
        assert any(c["id"] == cid for c in r_c.get_json()["components"])

        # Check surveys with leak_status=all
        r_s = auth_client.get(f"/api/ldar/surveys?facility_id={fid}&leak_status=all")
        assert r_s.status_code == 200
        assert any(s["id"] == sid for s in r_s.get_json()["surveys"])
    finally:
        with app.app_context():
            FugitiveSurvey.query.filter_by(id=sid).delete()
            ComponentInventory.query.filter_by(id=cid).delete()
            db.session.commit()


def test_vented_gas_temperature_absolute_zero_guard():
    """Verify VentedGasCalculator raises ValueError when temperature is at or below absolute zero and supports sub-zero F."""
    from calculations.vented_gas import VentedGasCalculator
    calc = VentedGasCalculator()
    # 1. At or below absolute zero raises ValueError
    with pytest.raises(ValueError, match="above absolute zero"):
        calc.calculate("actual", {
            "actual_volume": 1000.0,
            "actual_unit": "ft3",
            "gas_pressure_atm": 1.0,
            "gas_temp_f": -460.0,
            "ch4_content": 0.85,
            "co2_content": 0.05
        })

    # 2. Valid sub-zero winter temperature (-20 F) calculates without error
    res = calc.calculate("actual", {
        "actual_volume": 1000.0,
        "actual_unit": "ft3",
        "gas_pressure_atm": 1.0,
        "gas_temp_f": -20.0,
        "ch4_content": 0.85,
        "co2_content": 0.05
    })
    assert res["results"]["ch4"]["value"] > 0


def test_gwp_recalculation_steam_float_tolerance(app):
    """Verify steam emission factor matching uses float tolerance in GWP recalculation."""
    from models import Scope2Emission
    from services.gwp_recalculation import recalculate_all_emissions_gwp
    with app.app_context():
        fac = make_facility(region="SteamTest", activity="Downstream")
        fid = fac.id
        s2 = Scope2Emission(
            facility_id=fid,
            year=2090,
            source_type="purchased_steam",
            co2e=100.0,
            emission_factor=53.060000000001,
            co2e_location_based=100.0,
            co2e_market_based=100.0,
            status="Verified"
        )
        db.session.add(s2)
        db.session.commit()
        s2_id = s2.id

    try:
        with app.app_context():
            recalculate_all_emissions_gwp("AR5", previous="AR4")
            updated = db.session.get(Scope2Emission, s2_id)
            assert updated.co2e != 100.0  # Successfully recalculated with AR5 GWP!
    finally:
        with app.app_context():
            Scope2Emission.query.filter_by(id=s2_id).delete()
            db.session.commit()


def test_well_testing_disposition_partitioning_with_recovery():
    """Verify WellTestingCalculator accurately partitions emissions when vented, flared, and recovered fractions coexist."""
    from calculations.vented_exploration import WellTestingCalculator
    calc = WellTestingCalculator()

    # Tier 3 with 50% vented, 30% flared, 20% recovered
    res = calc.calculate(
        measured_gas_volume=100_000.0,
        volume_unit="scf",
        tier="tier3",
        ch4_content=0.80,
        co2_content=0.05,
        frac_vented=0.50,
        frac_flared=0.30,
        frac_recovered=0.20,
    )
    details = res["metadata"]["split_details"]
    # Gross CH4 in 100k scf at 80% CH4:
    # 100000 / 379.3 * 0.8 * 16.04 / 2204.6226 = 1.536 tonnes
    # Vented portion must be exactly 50% of gross:
    gross_ch4 = (100_000.0 / 379.3) * 0.80 * 16.04 / 2204.6226218487757
    assert abs(details["vented_ch4"] - (gross_ch4 * 0.50)) < 1e-4
    # Flared unburnt CH4 must be exactly 30% of gross * (1 - 0.98):
    assert abs(details["flared_unburnt_ch4"] - (gross_ch4 * 0.30 * 0.02)) < 1e-4

    # 100% recovered should yield zero emissions
    res_rec = calc.calculate(
        measured_gas_volume=50_000.0,
        tier="tier3",
        frac_vented=0.0,
        frac_flared=0.0,
        frac_recovered=1.0,
    )
    assert res_rec["results"]["ch4"]["value"] == 0.0
    assert res_rec["results"]["co2"]["value"] == 0.0
    assert res_rec["total_co2e"] == 0.0


def test_tank_flashing_vbe_negative_log_singularity():
    """Verify VBE equation avoids negative specific gravity and negative emissions under low pressure / high temp."""
    from calculations.vented_production_tank import TankFlashingCalculator
    calc = TankFlashingCalculator()

    # At 0 psig, log10((0 + 14.7)/114.7) is negative. High API and high temp could make sg_x negative without clamping.
    res = calc.calculate(
        throughput=500.0,
        method="vbe",
        api_gravity=70.0,
        separator_pressure_psig=0.0,
        separator_temp_f=450.0,
        gas_specific_gravity=0.85,
        ch4_content=0.80,
        co2_content=0.05,
    )
    assert res["results"]["ch4"]["value"] >= 0.0
    assert res["results"]["co2"]["value"] >= 0.0
    assert res["total_co2e"] >= 0.0


def test_tank_flashing_working_loss_gas_volume_and_co2():
    """Verify working_loss method computes total_gas_scf and gross_co2_tonnes when CH4 and CO2 are present."""
    from calculations.vented_production_tank import TankFlashingCalculator
    calc = TankFlashingCalculator()

    res = calc.calculate(
        throughput=1000.0,
        method="working_loss",
        ef_ch4=1.5,  # 1.5 kg CH4 / bbl -> 1.5 tonnes CH4
        ch4_content=0.75,
        co2_content=0.10,
    )
    assert res["results"]["ch4"]["value"] > 0.0
    # Gas volume should be calculated and positive
    assert res["inputs"]["total_gas_scf"] > 0.0
    # Native CO2 in the breathing vapor should be accounted for
    assert res["results"]["co2"]["value"] > 0.0


def test_ccus_crude_transport_negative_volume_guard():
    """Verify CrudeTransportLossesCalculator rejects negative volumes and negative weight fractions."""
    from calculations.vented_ccus_transport import CrudeTransportLossesCalculator
    calc = CrudeTransportLossesCalculator()

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="loading", volume_loaded_bbl=-50.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="ballasting", ballast_water_bbl=-100.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="loading", volume_loaded_bbl=50.0, ch4_weight_pct=-10.0)


def test_pneumatic_pump_and_dehydration_bounds():
    """Verify bounds in PneumaticPumpCalculator, GasDehydrationCalculator, and PneumaticDeviceCalculator."""
    from calculations.vented_production_pneumatic import (
        PneumaticPumpCalculator,
        GasDehydrationCalculator,
        PneumaticDeviceCalculator,
    )
    pump_calc = PneumaticPumpCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        pump_calc.calculate(method="engineering", volume_liquid_pumped_ft3=-10.0, pump_outlet_pressure_psig=50.0)

    with pytest.raises(ValueError, match="above absolute zero"):
        pump_calc.calculate(
            method="engineering",
            volume_liquid_pumped_ft3=100.0,
            pump_outlet_pressure_psig=50.0,
            gas_temperature_f=-460.0,
        )

    dehy_calc = GasDehydrationCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        dehy_calc.calculate(operating_days=-5.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        dehy_calc.calculate(gas_throughput_mmscfd=-2.0)

    pneu_calc = PneumaticDeviceCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        pneu_calc.calculate(monitoring_program=True, normal_count=-3)


def test_lng_distribution_negative_guards():
    """Verify negative input guards in LNGVentingCalculator, DistributionPneumaticsCalculator, and DistributionNonRoutineCalculator."""
    from calculations.vented_lng_distribution import (
        LNGVentingCalculator,
        DistributionPneumaticsCalculator,
        DistributionNonRoutineCalculator,
    )
    lng_calc = LNGVentingCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        lng_calc.calculate(activity="loading_transfer", transfer_volume_m3=-100.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        lng_calc.calculate(activity="direct_bog_vent", vented_gas_scf=-500.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        lng_calc.calculate(activity="loading_transfer", transfer_volume_m3=100.0, ch4_content=-0.2)

    dist_pneu = DistributionPneumaticsCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        dist_pneu.calculate(ch4_content=-0.5)

    dist_nr = DistributionNonRoutineCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        dist_nr.calculate(co2_content=-0.1)


def test_production_wells_non_routine_and_eor_guards():
    """Verify negative input guards in CO2EORVentingCalculator and ProductionNonRoutineVentingCalculator."""
    from calculations.vented_production_wells import (
        CO2EORVentingCalculator,
        ProductionNonRoutineVentingCalculator,
    )
    eor_calc = CO2EORVentingCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        eor_calc.calculate(activity="pump_blowdown", physical_volume_m3=-5.0, co2_density_kg_m3=650.0, co2_weight_fraction=0.98)

    with pytest.raises(ValueError, match="cannot be negative"):
        eor_calc.calculate(activity="pump_blowdown", physical_volume_m3=5.0, co2_density_kg_m3=-650.0, co2_weight_fraction=0.98)

    with pytest.raises(ValueError, match="cannot be negative"):
        eor_calc.calculate(activity="pump_blowdown", physical_volume_m3=5.0, co2_density_kg_m3=650.0, co2_weight_fraction=-0.98)

    nr_calc = ProductionNonRoutineVentingCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        nr_calc.calculate(source_type="prv", equipment_count=-5)


def test_fugitive_onshore_flow_and_leaker_normalization():
    """Verify mole fraction normalization, sum consistency, and non-negative guards in onshore fugitives."""
    from calculations.fugitive_onshore import convert_fugitive_flow_to_kg_hr, OnshoreScreeningMeasurementCalculator

    # 1. Percentage vs fraction normalization in convert_fugitive_flow_to_kg_hr
    res_frac = convert_fugitive_flow_to_kg_hr(100.0, "m3/hr", ch4_mol=0.85, co2_mol=0.02)
    res_pct = convert_fugitive_flow_to_kg_hr(100.0, "m3/hr", ch4_mol=85.0, co2_mol=2.0)
    assert pytest.approx(res_pct["ch4_kg_hr"], rel=1e-5) == res_frac["ch4_kg_hr"]
    assert pytest.approx(res_pct["co2_kg_hr"], rel=1e-5) == res_frac["co2_kg_hr"]

    # 2. Non-negative checks and invalid bounds
    with pytest.raises(ValueError, match="cannot be negative"):
        convert_fugitive_flow_to_kg_hr(-10.0, "m3/hr", ch4_mol=0.85)

    with pytest.raises(ValueError, match="cannot be negative"):
        convert_fugitive_flow_to_kg_hr(10.0, "m3/hr", ch4_mol=-0.5)

    with pytest.raises(ValueError, match="cannot exceed 100"):
        convert_fugitive_flow_to_kg_hr(10.0, "m3/hr", ch4_mol=0.85, co2_mol=0.25)

    # 3. Leaker survey normalization
    calc = OnshoreScreeningMeasurementCalculator()
    res_l_frac = calc.calculate_ogi_survey("valve", "gas", leakers_detected=5, ch4_mol=0.80, co2_mol=0.03)
    res_l_pct = calc.calculate_ogi_survey("valve", "gas", leakers_detected=5, ch4_mol=80.0, co2_mol=3.0)
    assert pytest.approx(res_l_pct["intermediate"]["total_ch4_tonnes"], rel=1e-5) == res_l_frac["intermediate"]["total_ch4_tonnes"]
    assert pytest.approx(res_l_pct["total_co2e"], rel=1e-5) == res_l_frac["total_co2e"]

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate_ogi_survey("valve", "gas", leakers_detected=5, ch4_mol=-0.1)

    with pytest.raises(ValueError, match="cannot exceed 100"):
        calc.calculate_ogi_survey("valve", "gas", leakers_detected=5, ch4_mol=0.9, co2_mol=0.2)


def test_completion_flowback_split_disposition_auto_activation():
    """Verify CompletionFlowbackCalculator honors explicit disposition fractions even if disposition='split' is omitted."""
    from calculations.vented_completion import CompletionFlowbackCalculator
    calc = CompletionFlowbackCalculator()

    # Pass explicit split fractions without disposition="split"
    res_auto = calc.calculate(
        tier="tier3",
        flowback_volume=1_000_000.0,
        volume_unit="scf",
        ch4_content=0.85,
        co2_content=0.02,
        frac_vented=0.2,
        frac_flared=0.8,
    )
    # Pass explicit split fractions with disposition="split"
    res_explicit = calc.calculate(
        tier="tier3",
        flowback_volume=1_000_000.0,
        volume_unit="scf",
        ch4_content=0.85,
        co2_content=0.02,
        disposition="split",
        frac_vented=0.2,
        frac_flared=0.8,
    )
    assert pytest.approx(res_auto["results"]["ch4"]["value"], rel=1e-5) == res_explicit["results"]["ch4"]["value"]
    assert pytest.approx(res_auto["total_co2e"], rel=1e-5) == res_explicit["total_co2e"]

    # Invalid sum of fractions
    with pytest.raises(ValueError, match="must sum to 100%"):
        calc.calculate(
            tier="tier3",
            flowback_volume=1_000_000.0,
            volume_unit="scf",
            ch4_content=0.85,
            frac_vented=0.5,
            frac_flared=0.7,
        )


def test_midstream_agr_and_dehydrator_bounds():
    """Verify input guards on throughput, CO2 concentrations, and CH4 content in midstream calculators."""
    from calculations.midstream import AGRCalculator, DehydratorCalculator

    agr = AGRCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        agr.calculate(throughput=10.0, co2_in=-0.05, co2_out=0.01)

    with pytest.raises(ValueError, match="cannot be negative"):
        agr.calculate(throughput=-10.0, co2_in=0.05, co2_out=0.01)

    with pytest.raises(ValueError, match="below 100"):
        agr.calculate(throughput=10.0, co2_in=0.50, co2_out=1.0)

    dehy = DehydratorCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        dehy.calculate(throughput=-5.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        dehy.calculate(throughput=5.0, ch4_content=-0.2)


def test_vented_unloading_volume_based_control_efficiency_normalization():
    """Verify LiquidsUnloadingCalculator.calculate_volume_based handles string and numeric control efficiencies cleanly."""
    from calculations.vented_unloading import LiquidsUnloadingCalculator
    calc = LiquidsUnloadingCalculator()

    res_str = calc.calculate_volume_based(
        well_depth=5000.0,
        diameter=2.0,
        pressure=100.0,
        ch4_content=85.0,
        events=5,
        control_efficiency="95%",
    )
    res_num = calc.calculate_volume_based(
        well_depth=5000.0,
        diameter=2.0,
        pressure=100.0,
        ch4_content=85.0,
        events=5,
        control_efficiency=0.95,
    )
    assert pytest.approx(res_str["total_co2e"], rel=1e-5) == res_num["total_co2e"]
    assert pytest.approx(res_str["results"]["ch4"]["value"], rel=1e-5) == res_num["results"]["ch4"]["value"]


def test_component_fugitive_negative_counts():
    """Verify ComponentFugitiveCalculator rejects negative component counts."""
    from calculations.fugitive import ComponentFugitiveCalculator
    calc = ComponentFugitiveCalculator()

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(component_counts={"valve": -5}, ch4_content=0.85, uncertainties={})

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(component_counts={"valve": {"count": -2, "ef": 0.0045}}, ch4_content=0.85, uncertainties={})


def test_associated_gas_venting_control_efficiency():
    """Verify control_efficiency reduces emissions appropriately in AssociatedGasVentingCalculator across Tiers."""
    from calculations.vented_associated_gas import AssociatedGasVentingCalculator
    calc = AssociatedGasVentingCalculator()

    # Tier 1 control reduction
    res_t1_uncontrolled = calc.calculate(tier="Tier 1", oil_production=1000.0, control_efficiency=0.0)
    res_t1_controlled = calc.calculate(tier="Tier 1", oil_production=1000.0, control_efficiency=0.90)
    assert pytest.approx(res_t1_controlled["results"]["ch4"]["value"], rel=1e-5) == res_t1_uncontrolled["results"]["ch4"]["value"] * 0.10
    assert pytest.approx(res_t1_controlled["total_co2e"], rel=1e-5) == res_t1_uncontrolled["total_co2e"] * 0.10

    # Tier 2 control reduction
    res_t2_uncontrolled = calc.calculate(tier="Tier 2", oil_production=1000.0, gor=500.0, ch4_content=0.80, control_efficiency=0.0)
    res_t2_controlled = calc.calculate(tier="Tier 2", oil_production=1000.0, gor=500.0, ch4_content=0.80, control_efficiency=0.90)
    assert pytest.approx(res_t2_controlled["results"]["ch4"]["value"], rel=1e-5) == res_t2_uncontrolled["results"]["ch4"]["value"] * 0.10
    assert pytest.approx(res_t2_controlled["total_co2e"], rel=1e-5) == res_t2_uncontrolled["total_co2e"] * 0.10

    # Tier 3 control reduction
    res_t3_uncontrolled = calc.calculate(tier="Tier 3", vent_volume=10000.0, ch4_content=0.80, control_efficiency=0.0)
    res_t3_controlled = calc.calculate(tier="Tier 3", vent_volume=10000.0, ch4_content=0.80, control_efficiency=0.90)
    assert pytest.approx(res_t3_controlled["results"]["ch4"]["value"], rel=1e-5) == res_t3_uncontrolled["results"]["ch4"]["value"] * 0.10

    with pytest.raises(ValueError, match="Control efficiency"):
        calc.calculate(tier="Tier 1", oil_production=1000.0, control_efficiency=-0.2)


def test_nitric_acid_calculator_negative_ef_and_abatement_bounds():
    """Verify NitricAcidCalculator rejects negative emission factor and enforces bounds on abatement efficiency."""
    from calculations.stoichiometry import NitricAcidCalculator
    calc = NitricAcidCalculator()

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(production_amount=100.0, ef_n2o=-5.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(production_amount=100.0, abatement_efficiency=-0.1)

    with pytest.raises(ValueError, match="cannot exceed 100"):
        calc.calculate(production_amount=100.0, abatement_efficiency=150.0)

    # Percentage normalization (e.g. 90% abatement)
    res_pct = calc.calculate(production_amount=100.0, abatement_efficiency=90.0)
    res_frac = calc.calculate(production_amount=100.0, abatement_efficiency=0.90)
    assert pytest.approx(res_pct["results"]["n2o"]["value"], rel=1e-5) == res_frac["results"]["n2o"]["value"]
    assert pytest.approx(res_pct["total_co2e"], rel=1e-5) == res_frac["total_co2e"]



