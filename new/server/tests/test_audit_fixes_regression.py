"""
Comprehensive Regression Test Suite for Calculation Logic, Equations & Pipeline Audit Fixes
Verifies all 7 verified bugs uncovered during the full mathematical and physical audit.
"""
import pytest
from calculations.constants import get_active_gwp
from calculations.vented_downstream import FireSuppressionCalculator
from calculations.vented_unloading import LiquidsUnloadingCalculator
from calculations.vented_gas import VentedGasCalculator
from calculations.vented_ccus_transport import CrudeTransportLossesCalculator
from services.intensity import SCF_PER_BOE


def test_fix1_scf_per_boe_defined_and_valid():
    """Verify SCF_PER_BOE is exported, imported in intensity.py, and mathematically valid."""
    assert SCF_PER_BOE is not None
    assert isinstance(SCF_PER_BOE, (int, float))
    # 1020 Btu/scf / 1000 / 5.8 MMBtu/BOE = 0.17586 BOE/Mscf -> 1000 / 0.17586 = ~5686 scf/BOE
    assert 5600.0 < SCF_PER_BOE < 5850.0


def test_fix2_scope1_calc_fgas_persistence():
    """Verify F-gas emissions are correctly stored in record.gas_composition."""
    from services.scope1_calc import apply_result
    from models import Emission
    from calculations.vented_downstream import FireSuppressionCalculator

    calc = FireSuppressionCalculator()
    api_res = calc.calculate(
        agent_type="HFC-227ea",
        charge_capacity_kg=1000.0,
        annual_release_rate=0.05,
    )
    em_result = {
        "co2": api_res["results"]["co2"]["value"],
        "ch4": api_res["results"]["ch4"]["value"],
        "n2o": api_res["results"]["n2o"]["value"],
        "totalCo2e": api_res["total_co2e"],
        "_full_api_res": api_res,
    }

    record = Emission()
    record.gas_composition = {}
    payload = {
        "process_type": "fire_suppression",
        "agent_type": "HFC-227ea",
        "charge_capacity_kg": 1000.0,
    }
    apply_result(record, payload, em_result, "api_equation_6_56", None, "AR5")

    assert record.gas_composition is not None
    assert isinstance(record.gas_composition, dict)
    # Must contain f-gas metrics
    assert "f_gas_t" in record.gas_composition or "f_gas_kg" in record.gas_composition or "f_gas" in record.gas_composition
    # 1000 kg * 0.05 = 50 kg = 0.05 tonnes
    if "f_gas_t" in record.gas_composition:
        assert pytest.approx(record.gas_composition["f_gas_t"], rel=1e-3) == 0.05
    if "f_gas_kg" in record.gas_composition:
        assert pytest.approx(record.gas_composition["f_gas_kg"], rel=1e-3) == 50.0


def test_fix3_fire_suppression_dynamic_gwp_override():
    """Verify clean agent dynamic GWP resolution works for both hyphenated and underscore keys."""
    calc = FireSuppressionCalculator()
    
    # 1. Custom GWP with hyphenated key (e.g. AR6 or custom horizon)
    custom_gwps = {"HFC-227ea": 3350.0}
    res_hyphen = calc.calculate(agent_type="HFC-227ea", direct_discharge_kg=1000.0, gwp_dict=custom_gwps)
    assert res_hyphen["inputs"]["gwp"] == 3350.0
    assert pytest.approx(res_hyphen["total_co2e"], rel=1e-3) == 3350.0

    # 2. Custom GWP with underscore key
    custom_gwps_under = {"hfc_227ea": 3400.0}
    res_under = calc.calculate(agent_type="hfc_227ea", direct_discharge_kg=1000.0, gwp_dict=custom_gwps_under)
    assert res_under["inputs"]["gwp"] == 3400.0
    assert pytest.approx(res_under["total_co2e"], rel=1e-3) == 3400.0

    # 3. Default AR5 fallback when not overridden
    res_default = calc.calculate(agent_type="HFC-227ea", direct_discharge_kg=1000.0)
    assert res_default["inputs"]["gwp"] == 3220.0
    assert pytest.approx(res_default["total_co2e"], rel=1e-3) == 3220.0


def test_fix4_fire_suppression_physical_mass_format():
    """Verify format_result carries physical chemical mass in results['f_gas']['value'], not CO2e mass."""
    calc = FireSuppressionCalculator()
    # 2000 kg = 2.0 metric tonnes of HFC-227ea (GWP = 3220)
    res = calc.calculate(agent_type="HFC-227ea", direct_discharge_kg=2000.0)
    
    f_gas_dict = res["results"]["f_gas"]
    assert isinstance(f_gas_dict, dict)
    # Physical mass must be 2.0 tonnes, NOT 2.0 * 3220 = 6440 tonnes!
    assert pytest.approx(f_gas_dict["value"], rel=1e-4) == 2.0
    assert pytest.approx(f_gas_dict["co2e"], rel=1e-4) == 6440.0
    assert pytest.approx(res["total_co2e"], rel=1e-4) == 6440.0


def test_fix5_liquids_unloading_eq6_10_scales_with_events():
    """Verify Eq. 6-10 supports both API Compendium annual hours and hours_per_event scaling."""
    calc = LiquidsUnloadingCalculator()
    
    # 1. API Compendium 2021 verbatim Equation 6-10 (hours_open is cumulative annual hours per well-year):
    # Wellbore: 12 * (0.37e-3 * 4.5^2 * 8500 * 800) = 611,888 scf
    # Flowline: 1000 * (3 - 1.0) * 1.0 = 2,000 scf -> Total: 613,888 scf
    res_compendium = calc.calculate_tier3_equation_6_10(
        events=12, well_depth=8500, diameter=4.5, pressure=800, sfr=1000, hours_open=3.0, unloading_type="non_plunger",
        ch4_content=0.87
    )
    vr_comp = res_compendium["inputs"]["vr_per_well_scf"]
    assert pytest.approx(vr_comp, rel=1e-4) == 613388.0

    # 2. Per-event mode (hours_per_event=True, Subpart W per-event flowline venting):
    # Flowline: 12 * 1000 * (3 - 1.0) * 1.0 = 24,000 scf -> Total: 611,388 + 24,000 = 635,388 scf
    res_per_event = calc.calculate_tier3_equation_6_10(
        events=12, well_depth=8500, diameter=4.5, pressure=800, sfr=1000, hours_open=3.0, unloading_type="non_plunger",
        ch4_content=0.87, hours_per_event=True
    )
    vr_per_ev = res_per_event["inputs"]["vr_per_well_scf"]
    assert pytest.approx(vr_per_ev, rel=1e-4) == 635388.0


def test_fix6_agr_balance_flared_methane_destruction_and_n2o_volume():
    """Verify AGR contactor mass balance when flared applies methane destruction and flares acid gas volume."""
    calc = VentedGasCalculator()
    
    # Sour gas: 100 MMscf, sweet gas: 95 MMscf, sour CO2: 8%, sweet CO2: 1%
    # Table 6-19 throughput factor: 0.0185 t CH4 / MMscf -> 1.85 t CH4 co-absorbed
    # Flared disposition: 98% DE -> 1.85 * 0.02 = 0.037 t CH4 uncombusted slip
    res_flared = calc.calculate("agr_balance", {
        "unit": "mmscf",
        "sour_gas_volume": 100,
        "sweet_gas_volume": 95,
        "sour_co2_content": 0.08,
        "sweet_co2_content": 0.01,
        "disposition": "flared",
        "destruction_efficiency": 0.98,
    })
    
    ch4_val = res_flared["results"]["ch4"]["value"]
    # Methane must reflect 98% destruction (0.037 t), not 100% emission (1.85 t)
    assert pytest.approx(ch4_val, rel=1e-3) == 0.037
    
    # N2O must be computed on acid gas volume (~167,000 scf), NOT sour throughput (100,000,000 scf)
    n2o_val = res_flared["results"]["n2o"]["value"]
    assert n2o_val < 0.001  # If on 100 MMscf it would be ~0.01 t


def test_fix7_crude_transport_flared_n2o_heating_value_dimension():
    """Verify crude transport marine loading vapor combustion N2O includes TOC heating value (~44 MMBtu/t)."""
    calc = CrudeTransportLossesCalculator()
    
    res = calc.calculate(
        mode="loading",
        volume_loaded_bbl=100000,
        vessel_type="tanker",
        control_efficiency=0.98,
        control_type="flare",
    )
    
    n2o_val = res["results"]["n2o"]["value"]
    # 9.24 t TOC captured * 0.98 = 9.055 t TOC -> ~399 MMBtu -> ~3.99e-5 t N2O
    # Before the fix without MMBtu conversion, it was 9.055 * 0.85 * 1e-7 = 7.7e-7 t (understated by 50x)
    assert n2o_val > 1.0e-5
    assert pytest.approx(n2o_val, rel=0.1) == 3.99e-5


def test_fix8_liquids_unloading_plunger_lift_z_floor():
    """Verify plunger lift wells with 0.5 <= HR < 1.0 correctly engage flowline venting (Z=1)."""
    calc = LiquidsUnloadingCalculator()
    res = calc.calculate_tier3_equation_6_10(
        events=1,
        well_depth=5000,
        diameter=2.5,
        pressure=200.0,
        sfr=20000.0,
        hours_open=0.75,
        unloading_type="plunger",
        ch4_content=0.85,
    )
    wellbore_scf = 1 * 0.37e-3 * (2.5 ** 2) * 5000 * 200.0  # 2,312.5 scf
    flowline_scf = 20000.0 * (0.75 - 0.5) * 1.0            # 5,000 scf (X=0.5, Z=1.0)
    assert res["inputs"]["whole_gas_scf"] == pytest.approx(wellbore_scf + flowline_scf, rel=1e-4)


def test_fix9_activity_factors_gas_fraction_scaling():
    """Verify ActivityFactorCalculator handles both decimal fraction and percentage without 100x attenuation."""
    from calculations.activity_factors import ActivityFactorCalculator
    calc = ActivityFactorCalculator()
    # wt_gas row has basis 0.816
    res_pct = calc.calculate("wt_gas", 2, ch4_content=81.6, co2_content=2.0)
    res_frac = calc.calculate("wt_gas", 2, ch4_content=0.816, co2_content=0.02)
    assert res_pct["results"]["ch4"]["value"] == pytest.approx(res_frac["results"]["ch4"]["value"])
    assert res_pct["results"]["co2"]["value"] == pytest.approx(res_frac["results"]["co2"]["value"])
    assert res_frac["intermediate"]["ch4_scale"] == pytest.approx(1.0)


def test_fix10_scope2_steam_ton_canonical_metric_tonnes():
    """Verify background_processor stores steam_ton as metric tonnes without short-ton inflation."""
    from background_processor import _process_row_scope2
    from models import Facility, Scope2Emission
    from extensions import db
    from app import app

    with app.app_context():
        fac = Facility.query.first()
        if not fac:
            fac = Facility(name="Steam Test Facility", code="ST-001", country="Algeria")
            db.session.add(fac)
            db.session.flush()

        row = {
            "date": "2025-06",
            "facility_name": fac.name,
            "source_type": "steam",
            "consumption": "100",
            "unit": "tonne",
            "boiler_eff": "80",
            "steam_enthalpy_btu_lb": "1170",
        }
        obj, errors = _process_row_scope2(
            row=row,
            user_id=1,
            fac_name_map={fac.name.lower(): fac},
            fac_id_map={str(fac.id): fac},
            GRID_FACTORS={},
            job_id="steam-audit-fix",
            row_idx=1,
        )
        assert errors == []
        assert obj is not None
        # steam_ton must store 100.0 (metric tonnes), NOT 110.231 (short tons)
        assert obj.steam_ton == pytest.approx(100.0)
