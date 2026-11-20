"""Regression tests for the clean-room calculation audit of November 2026, batch C1 (combustion and engine).

Finding IDs refer to CALC_AUDIT_2026-11/REPORT.md. Expected values are worked by hand from the inputs and
the cited norm (API Compendium 2021 with its December 2025 corrections, 40 CFR 98 Subpart C), never read
from the engine.
"""
import copy

import pytest

from app import app
from calculations import compute_emissions
from calculations.combustion_methods import CombustionMethodCalculator
from calculations.dispatcher import CalculationDispatcher

GWP = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}
C_TO_CO2 = 44.01 / 12.011
LB_PER_T = 2204.62


@pytest.fixture
def ctx():
    with app.app_context():
        yield


def _calc(method, inputs):
    return CombustionMethodCalculator().calculate(method, inputs, gwp_dict=GWP)


def _v(res, gas):
    return res["results"][gas]["value"]


# the Scope 1 form's request for Tier 3 "Carbon content", liquid diesel (audit UI case C4)
C4 = {
    "facility_id": 1, "year": 2025, "month": 6, "process_type": "combustion", "quantity": 1000, "amount": 1000,
    "unit": "gal", "factor_source": "specific", "fuel_type": "Diesel (No. 2 Fuel Oil)", "fuel": "Diesel (No. 2 Fuel Oil)",
    "calc_inputs": {"combustion": {
        "combustion_method": "carbon_content", "fuel_state": "liquid", "fuel": "Diesel (No. 2 Fuel Oil)",
        "fuel_name": "Diesel (No. 2 Fuel Oil)", "fuel_type": "Diesel (No. 2 Fuel Oil)", "fuel_volume_unit": "gal",
        "unit": "gal", "density_unit": "lb/gal", "fuel_volume": 1000, "amount": 1000, "quantity": 1000,
        "fuel_density": 7.1, "carbon_wt_pct": 87, "oxidation_pct": 100}},
}
C4_CO2 = 1000 * 7.1 / LB_PER_T * 0.87 * C_TO_CO2  # Eq 4-12 / Exhibit 4.5: 10.266 t


# ---------------------------------------------------------------- F-GUI-01 (Critical)
def test_f_gui_01_carbon_content_liquid_books_no_trace_gas_unless_asked(ctx):
    from services.scope1_calc import resolve_factor

    p = copy.deepcopy(C4)
    em = compute_emissions(p, resolve_factor(copy.deepcopy(p)), gwp_dict=GWP)[0]
    assert em["co2"] == pytest.approx(C4_CO2, rel=1e-4)
    assert em["ch4"] == 0.0 and em["n2o"] == 0.0  # trace box unticked: was 414 t CH4 / 82.8 t N2O
    assert em["totalCo2e"] == pytest.approx(C4_CO2, rel=1e-4)


def test_f_gui_01_trace_gases_use_table_c1_hhv_per_gallon(ctx):
    from services.scope1_calc import resolve_factor

    p = copy.deepcopy(C4)
    p["calc_inputs"]["combustion"]["include_trace"] = True
    em = compute_emissions(p, resolve_factor(copy.deepcopy(p)), gwp_dict=GWP)[0]
    e = 1000 * 0.138  # Table C-1 distillate No. 2: 0.138 MMBtu/gal
    assert em["ch4"] == pytest.approx(e * 3.0e-3 / 1000, rel=1e-6)  # Table C-2 petroleum 3.0E-03 kg/MMBtu
    assert em["n2o"] == pytest.approx(e * 6.0e-4 / 1000, rel=1e-6)  # 6.0E-04 kg/MMBtu


def test_f_gui_01_generic_hhv_key_is_not_read_as_mmbtu_per_gallon():
    res = _calc("carbon_content", {"fuel_state": "liquid", "fuel": "diesel", "fuel_volume": 1000, "unit": "gal",
                                   "fuel_density": 7.1, "carbon_wt_pct": 87, "hhv": 138000})
    assert _v(res, "ch4") == 0.0 and _v(res, "n2o") == 0.0


# ---------------------------------------------------------------- F-CMB-02 (High)
def test_f_cmb_02_engine_heat_rate_follows_table_4_2_fuel():
    # Exhibit 4.1: 100 hp, 90 % load, 8,000 h at 6,186 Btu/hp-hr (gas IC engine) = 4,453.9 MMBtu
    res = _calc("equipment", {"equipment_type": "ic_4s_lean_ng", "engine_hp": 100, "load_pct": 90,
                              "operating_hours": 8000})
    e = 100 * 0.90 * 8000 * 6186 / 1e6
    assert res["intermediate"]["energy_mmbtu"] == pytest.approx(e, rel=1e-9)
    assert _v(res, "co2") == pytest.approx(e * 0.05306, rel=1e-9)
    diesel = _calc("equipment", {"equipment_type": "ic_diesel", "engine_hp": 100, "operating_hours": 1000})
    assert diesel["intermediate"]["energy_mmbtu"] == pytest.approx(100 * 1000 * 8089 / 1e6, rel=1e-9)
    gasoline = _calc("equipment", {"equipment_type": "ic_gasoline", "engine_hp": 100, "operating_hours": 1000})
    assert gasoline["intermediate"]["energy_mmbtu"] == pytest.approx(100 * 1000 * 7000 / 1e6, rel=1e-9)


# ---------------------------------------------------------------- F-CMB-03 (Medium), F-CMB-05 (Low)
def test_f_cmb_03_mass_input_with_trace_gases_needs_an_hhv_per_tonne():
    base = {"fuel_state": "solid", "fuel": "diesel", "fuel_mass": 100, "fuel_mass_unit": "t", "carbon_wt_pct": 86,
            "include_trace": True}
    with pytest.raises(ValueError, match="MMBtu/t"):
        _calc("carbon_content", base)
    res = _calc("carbon_content", dict(base, hhv_mmbtu_t=43.0))
    assert _v(res, "ch4") == pytest.approx(100 * 43.0 * 3.0e-6, rel=1e-9)
    coal = _calc("carbon_content", {"fuel_state": "solid", "fuel": "coal", "fuel_mass": 100, "fuel_mass_unit": "t",
                                    "carbon_wt_pct": 60, "include_trace": True})
    assert coal["intermediate"]["energy_mmbtu"] == pytest.approx(100 * 19.73 / 0.90718474, rel=1e-9)


def test_f_cmb_05_liquid_trace_energy_is_gallons_times_hhv():
    res = _calc("carbon_content", {"fuel_state": "liquid", "fuel": "gasoline", "fuel_volume": 42, "unit": "bbl",
                                   "fuel_density": 6.2, "carbon_wt_pct": 86, "include_trace": True})
    assert res["intermediate"]["energy_mmbtu"] == pytest.approx(42 * 42 * 0.125, rel=1e-9)


# ---------------------------------------------------------------- F-CMB-04 (Medium)
def test_f_cmb_04_gas_carbon_balance_needs_density_or_mw():
    base = {"fuel_state": "gas", "fuel_volume": 1000, "unit": "m3", "carbon_wt_pct": 70}
    with pytest.raises(ValueError, match="density"):
        _calc("carbon_content", base)
    res = _calc("carbon_content", dict(base, mw=17.4))
    assert _v(res, "co2") == pytest.approx(1000 * 17.4 / 23.685 / 1000 * 0.70 * C_TO_CO2, rel=1e-9)


# ---------------------------------------------------------------- F-CMB-06 (Medium)
def test_f_cmb_06_carbon_content_of_one_is_one_percent(ctx):
    res = _calc("carbon_content", {"fuel_state": "liquid", "fuel_volume": 1000, "unit": "gal", "fuel_density": 7.1,
                                   "carbon_wt_pct": 1})
    assert _v(res, "co2") == pytest.approx(1000 * 7.1 / LB_PER_T * 0.01 * C_TO_CO2, rel=1e-9)
    st = CalculationDispatcher().dispatch("stoichiometry", {"amount": 1, "unit": "t", "carbon_content": 1, "factor_source": "specific"}, {}, {},
                                          gwp_dict=GWP)
    assert st["results"]["co2"]["value"] == pytest.approx(1 * 0.01 * C_TO_CO2, rel=1e-6)  # was 3.664 t
    st85 = CalculationDispatcher().dispatch("stoichiometry", {"amount": 1, "unit": "t", "carbon_content": 85, "factor_source": "specific"}, {}, {},
                                            gwp_dict=GWP)
    assert st85["results"]["co2"]["value"] == pytest.approx(0.85 * C_TO_CO2, rel=1e-6)


# ---------------------------------------------------------------- F-CORE-02 (High)
def test_f_core_02_a_zero_gas_factor_is_not_filled_from_the_generic_key():
    from calculations.legacy_engine import _calculate_default_kg

    row = {"co2": 0.0, "ch4": 1.4, "n2o": 0.0, "factor": 1.4, "unit": "kg/bbl"}  # a CH4-only catalog row
    assert _calculate_default_kg(1000, "bbl", row, "ch4") == pytest.approx(1400.0)
    assert _calculate_default_kg(1000, "bbl", row, "co2") == 0.0  # was 1,400 kg
    assert _calculate_default_kg(1000, "bbl", row, "n2o") == 0.0  # was 1,400 kg (x 265)
    # a row with only a generic factor keeps using it
    assert _calculate_default_kg(10, "bbl", {"factor": 2.0, "unit": "kg/bbl"}, "co2") == pytest.approx(20.0)


def test_f_core_02_specific_venting_with_only_ch4_entered(ctx):
    p = {"process_type": "venting", "factor_source": "specific", "amount": 1000, "unit": "bbl",
         "specific_factors": {"ch4": 1.4, "ch4Unit": "kg/bbl"}, "year": 2024, "month": 1}
    em = compute_emissions(p, {"co2": 0.0, "ch4": 1.4, "n2o": 0.0, "factor": 1.4, "unit": "kg/bbl"}, gwp_dict=GWP)[0]
    assert em["ch4"] == pytest.approx(1.4, rel=1e-9)
    assert em["co2"] == 0.0 and em["n2o"] == 0.0
    assert em["totalCo2e"] == pytest.approx(1.4 * 28, rel=1e-9)  # 39.2 t (was 411.6 t)


# ---------------------------------------------------------------- F-CORE-03 (Medium)
def test_f_core_03_section_method_contents_are_percent(ctx):
    from calculations.activity_factors import ActivityFactorCalculator

    a = ActivityFactorCalculator()
    pct = a.calculate("wt_gas", 10, ch4_content=81.6, co2_content=0.5)
    small = a.calculate("wt_gas", 10, ch4_content=81.6, co2_content="0.5%")
    assert pct["results"]["co2"]["value"] == pytest.approx(small["results"]["co2"]["value"])  # 0.5 is 0.5 %


def test_f_core_03_vented_gas_shares_are_percent():
    from calculations.vented_gas import _frac

    assert _frac(0.5, "share") == pytest.approx(0.005)
    assert _frac(45, "share") == pytest.approx(0.45)
    assert _frac("45%", "share") == pytest.approx(0.45)


# ---------------------------------------------------------------- F-FAC-01 (Medium)
def test_f_fac_01_natural_gas_tier1_uses_table_c1_hhv(ctx):
    from services.scope1_calc import resolve_factor

    p = {"process_type": "combustion", "factor_source": "default", "fuel": "Natural Gas", "fuel_type": "Natural Gas",
         "amount": 1e6, "quantity": 1e6, "unit": "scf", "year": 2024, "month": 1}
    em = compute_emissions(dict(p), resolve_factor(dict(p)), gwp_dict=GWP)[0]
    assert em["co2"] == pytest.approx(1e6 * 1.026e-3 * 53.06 / 1000, rel=1e-9)  # 54.440 t (was 54.121 t)
    assert em["ch4"] == pytest.approx(1e6 * 1.026e-3 * 1.0e-3 / 1000, rel=1e-9)


# ---------------------------------------------------------------- F-FAC-02 (Medium)
def test_f_fac_02_mobile_tier1_uses_table_4_16_by_vehicle(ctx):
    from services.scope1_calc import resolve_factor

    p = {"process_type": "mobile", "factor_source": "default", "fuel": "Motor Gasoline", "fuel_type": "Motor Gasoline",
         "amount": 1000, "quantity": 1000, "unit": "gal", "year": 2024, "month": 1, "vehicle_type": "ldgv_tier1"}
    em = compute_emissions(dict(p), resolve_factor(dict(p)), gwp_dict=GWP)[0]
    assert em["co2"] == pytest.approx(1000 * 0.125 * 70.22 / 1000, rel=1e-6)  # Table C-1 basis unchanged
    assert em["ch4"] == pytest.approx(8.7e-4, rel=1e-9)   # Table 4-16 LDGV Tier 1, t / 1,000 gal
    assert em["n2o"] == pytest.approx(1.8e-3, rel=1e-9)   # was 7.5e-5 t (stationary Table C-2)
    with pytest.raises(ValueError, match="Table 4-16"):
        compute_emissions({k: v for k, v in p.items() if k != "vehicle_type"}, resolve_factor(dict(p)), gwp_dict=GWP)


def test_f_fac_02_vehicle_distance_any_table_4_16_vehicle():
    res = _calc("vehicle_distance", {"distance": 1e6, "vehicle_type": "hd_diesel_advanced", "fuel_economy_mpg": 8.8})
    gal = 1e6 / 8.8  # Exhibit 4.12: 113,636 gal
    assert _v(res, "ch4") == pytest.approx(gal / 1000 * 4.2e-4, rel=1e-9)
    assert _v(res, "n2o") == pytest.approx(gal / 1000 * 5.7e-4, rel=1e-9)
    with pytest.raises(ValueError, match="Table 4-16"):
        _calc("vehicle_distance", {"distance": 1e6, "vehicle_fuel": "diesel", "fuel_economy_mpg": 8.8})


# ---------------------------------------------------------------- F-FAC-06 (Low)
def test_f_fac_06_engine_factors_from_the_lb_column_of_table_4_11():
    from emission_factors import API_FACTORS as CAT

    lb = 0.45359237
    assert CAT["Natural Gas - 4-Stroke Rich Burn Engine"]["ch4"] == pytest.approx(0.23 * lb, rel=1e-4)
    assert CAT["Natural Gas - Turbine"]["n2o"] == pytest.approx(0.003 * lb, rel=1e-4)


# ---------------------------------------------------------------- F-CORE-07 (Medium)
def test_f_core_07_gas_boe_on_table_3_4_basis():
    from calculations.units import GAS_BOE_PER_MSCF, SCF_PER_BOE

    assert SCF_PER_BOE == pytest.approx(5647.52)
    assert GAS_BOE_PER_MSCF == pytest.approx(1000 / 5647.52)


# ---------------------------------------------------------------- F-CMB-07 (Low)
def test_f_cmb_07_energy_basis_flare_n2o_factor_needs_hhv(ctx):
    base = {"process_type": "flaring", "factor_source": "specific", "amount": 1e6, "unit": "scf", "ch4_content": 90,
            "ef_n2o": 0.0001, "ef_unit": "kg/MMBtu", "year": 2024, "month": 1}
    with pytest.raises(ValueError, match="heating value"):
        compute_emissions(dict(base), {}, gwp_dict=GWP)
    em = compute_emissions(dict(base, hhv=1000), {}, gwp_dict=GWP)[0]
    assert em["n2o"] == pytest.approx(1e6 * 1000 / 1e6 * 0.0001 / 1000, rel=1e-6)
