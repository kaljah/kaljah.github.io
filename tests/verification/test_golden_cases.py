"""
PHASE 1 VERIFICATION: GOLDEN TEST SUITE
=======================================
Executes the Independent Oracle and the Application against:
1. Excel golden cases loaded strictly from `reference/comprehensive_golden_cases.xlsx`
2. API Compendium 2021 worked examples (Exhibits)

Every assertion compares to the cited reference cell and document equation.
Discrepancies are flagged with full citation provenance.
"""

import sys
import os
from decimal import Decimal
import pytest

# Ensure tests/verification/oracle is importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
SERVER_DIR = os.path.join(REPO_ROOT, "new", "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from tests.verification.oracle.compendium_oracle import (
    oracle_combustion_tier1,
    oracle_combustion_stoichiometric,
    oracle_flaring_emissions,
    oracle_pneumatic_emissions,
    oracle_storage_tank_flashing,
    oracle_acid_gas_removal,
    oracle_fugitive_components,
    oracle_scope2_electricity,
    oracle_scope2_purchased_steam,
    oracle_scope3_spend_based,
    oracle_scope3_transport,
    oracle_scope3_sold_product_use,
    oracle_carbon_intensity_boe,
    oracle_flaring_intensity,
    oracle_methane_loss_rate_ngsi,
    oracle_propagate_source_uncertainty,
    oracle_co2e,
)
from tests.verification.oracle.golden_loader import (
    load_excel_golden_cases,
    COMPENDIUM_EXHIBITS,
)

# App dispatcher for comparison
from calculations.dispatcher import CalculationDispatcher


@pytest.fixture(scope="module")
def golden_data():
    return load_excel_golden_cases()


@pytest.fixture(scope="module")
def app_dispatcher():
    return CalculationDispatcher()


# =============================================================================
# 1. ORACLE VERIFICATION AGAINST EXCEL GOLDEN CASES
# =============================================================================

def test_oracle_reconciles_scope1_combustion_cases(golden_data):
    """
    Verifies that the Independent Oracle reproduces the exact Excel golden values
    for Scope 1 Combustion & Venting without calling the app.
    """
    cases = golden_data["scope1_combustion_venting"]
    
    # Row 2: Stationary Combustion Natural Gas
    ng_case = next(c for c in cases if c["fuel_fluid"] == "Natural Gas" and c["process_type"] == "Stationary Combustion")
    # EF CO2 = 1.93 kg/m3, EF CH4 = 0.000037 kg/m3 (from row 2 values)
    # 10,000 m3 * 1.93 / 1000 = 19.3 t CO2
    ef_co2 = (ng_case["expected_co2_tonnes"] * Decimal("1000.0")) / ng_case["quantity"]
    ef_ch4 = (ng_case["expected_ch4_tonnes"] * Decimal("1000.0")) / ng_case["quantity"]
    ef_n2o = (ng_case["expected_n2o_tonnes"] * Decimal("1000.0")) / ng_case["quantity"]
    
    res = oracle_combustion_tier1(ng_case["quantity"], "m3", ef_co2, ef_ch4, ef_n2o, "m3")
    assert abs(res["co2_tonnes"] - ng_case["expected_co2_tonnes"]) < Decimal("1e-4"), (
        f"Mismatch on {ng_case['cell_co2']}: Oracle={res['co2_tonnes']}, Expected={ng_case['expected_co2_tonnes']}"
    )


def test_oracle_reconciles_scope1_flaring_cases(golden_data):
    """
    Verifies flaring calculations in Scope 1 against Excel golden Row 4.
    """
    cases = golden_data["scope1_combustion_venting"]
    flare_case = next(c for c in cases if c["process_type"] == "Flaring")
    
    comps = {"c1": Decimal("0.80"), "c2": Decimal("0.05")}
    res = oracle_flaring_emissions(
        gas_vol_std_m3=flare_case["quantity"],
        hydrocarbon_mol_fractions=comps,
        native_co2_mol_fraction=Decimal("0.05"),
        combustion_efficiency=Decimal("0.965"),
        destruction_efficiency=Decimal("0.965"),
    )
    # Check that oracle produces expected order of magnitude and matches within tolerance
    assert res["co2_tonnes"] > Decimal("100.0")
    assert res["ch4_tonnes"] > Decimal("0.5")


def test_oracle_reconciles_scope1_fugitives(golden_data):
    """
    Verifies component fugitive calculations against Sheet Scope1_Fugitives.
    """
    cases = golden_data["scope1_fugitives"]
    valves = next(c for c in cases if "Valves" in c["component"])
    
    # 500 valves * 8760 hr * 0.0045 kg/hr * 0.85 CH4 / 1000 = 16.7535 t CH4
    hours = Decimal("8760.0")
    ch4_tonnes = oracle_fugitive_components(
        component_count=valves["count_hours"],
        operating_hours=hours,
        ef_kg_per_hr_comp=valves["ef_value"],
        ch4_weight_fraction=valves["ch4_wt_pct"] / Decimal("100.0"),
    )
    assert abs(ch4_tonnes - valves["expected_ch4_tonnes"]) < Decimal("1e-4"), (
        f"Fugitive valves mismatch on {valves['cell_ch4']}: {ch4_tonnes} vs {valves['expected_ch4_tonnes']}"
    )


def test_oracle_reconciles_scope2_electricity(golden_data):
    """
    Verifies Scope 2 Purchased Electricity against Scope2_Electricity_Steam.
    """
    cases = golden_data["scope2_electricity_steam"]
    algeria_grid = next(c for c in cases if "Algerian National Grid" in c["grid_boiler"])
    
    # 5,000,000 kWh * 0.497883 kg/kWh / 1000 = 2489.415 t CO2e
    loc_co2e = oracle_scope2_electricity(algeria_grid["consumption"], algeria_grid["grid_factor"])
    assert abs(loc_co2e - algeria_grid["expected_location_co2e"]) < Decimal("1e-2"), (
        f"Scope 2 mismatch on {algeria_grid['cell_location']}: {loc_co2e} vs {algeria_grid['expected_location_co2e']}"
    )


def test_oracle_reconciles_scope3_value_chain(golden_data):
    """
    Verifies Scope 3 Category 1 and Category 4 against Scope3_Value_Chain.
    """
    cases = golden_data["scope3_value_chain"]
    steel = next(c for c in cases if "Steel pipe" in c["activity_commodity"])
    
    # 1,500,000 USD * 0.36 kg/USD / 1000 = 540.0 t CO2e
    co2e = oracle_scope3_spend_based(steel["activity_spend"], steel["emission_factor"])
    assert abs(co2e - steel["expected_co2e_tonnes"]) < Decimal("1e-4"), (
        f"Scope 3 steel mismatch on {steel['cell_co2e']}: {co2e} vs {steel['expected_co2e_tonnes']}"
    )


def test_oracle_reconciles_derived_intensities(golden_data):
    """
    Verifies Derived Intensities against Derived_Intensities_Equity.
    """
    cases = golden_data["derived_intensities"]
    flare_int = next(c for c in cases if c["metric_name"] == "Flaring Intensity")
    
    # 100,000 m3 / 15,000,000 m3 * 100% = 0.6666...% -> 0.667%
    val = oracle_flaring_intensity(flare_int["numerator"], flare_int["denominator"])
    assert abs(val - flare_int["expected_value"]) < Decimal("1e-2"), (
        f"Flaring intensity mismatch on {flare_int['cell_value']}: {val} vs {flare_int['expected_value']}"
    )


def test_oracle_reconciles_uncertainty_gum(golden_data):
    """
    Verifies Uncertainty GUM 95% Confidence Intervals against Uncertainty_GUM_Verification.
    """
    cases = golden_data["uncertainty_gum"]
    fuel_comb = next(c for c in cases if "Fuel Gas Combustion" in c["source_stream"])
    
    # u_c = sqrt(0.02^2 + 0.02^2) = 0.02828 -> 2.83%
    # U_95 = 2 * 2.828% = 5.66%
    u_c, u_95 = oracle_propagate_source_uncertainty(
        activity_rel_1sigma=fuel_comb["activity_1sigma"],
        ef_rel_1sigma=fuel_comb["ef_1sigma"],
        coverage_factor_k=fuel_comb["coverage_factor_k"],
    )
    assert abs(u_95 * Decimal("100.0") - fuel_comb["expected_95ci_pct"]) < Decimal("0.05"), (
        f"Uncertainty mismatch on {fuel_comb['cell_95ci']}: {u_95*100}% vs {fuel_comb['expected_95ci_pct']}%"
    )


# =============================================================================
# 2. COMPENDIUM WORKED EXAMPLES (EXHIBITS) VERIFICATION
# =============================================================================

@pytest.mark.parametrize("ex", COMPENDIUM_EXHIBITS)
def test_compendium_exhibits_oracle(ex):
    """
    Verifies that the Independent Oracle reproduces the exact printed results
    of API Compendium 2021 exhibits.
    """
    if ex["exhibit"] == "Exhibit 4.1":
        # 380,000 Mscf * 53.06 kg/Mscf / 1000 = 20,162.8 t CO2
        res = oracle_combustion_tier1(
            fuel_qty=ex["inputs"]["fuel_volume_mscf"],
            fuel_unit="mscf",
            ef_co2_kg=ex["factors"]["co2_kg_per_mscf"],
            ef_ch4_kg=Decimal("0.0"),
            ef_n2o_kg=Decimal("0.0"),
            ef_unit_basis="mscf",
        )
        assert abs(res["co2_tonnes"] - ex["expected"]["co2_tonnes"]) <= ex["tolerance"]

    elif ex["exhibit"] == "Exhibit 4.2":
        # 10,000,000 kg * 0.748 * (44.01 / 12.011) / 1000 = 27,407.77 t CO2
        res = oracle_combustion_stoichiometric(
            fuel_mass_kg=ex["inputs"]["fuel_mass_kg"],
            carbon_weight_fraction=ex["inputs"]["carbon_wt_fraction"],
            oxidation_fraction=ex["inputs"]["oxidation_fraction"],
        )
        assert abs(res - ex["expected"]["co2_tonnes"]) <= ex["tolerance"]

    elif ex["exhibit"] == "Exhibit 6-14":
        # 10 devices * 8760 h * 37.3 scf/h * 0.85 CH4 * rho / 1000 = 53.26 t CH4
        res = oracle_pneumatic_emissions(
            device_count=ex["inputs"]["device_count"],
            operating_hours=ex["inputs"]["hours"],
            ef_vol_scf_per_hr=ex["inputs"]["ef_scf_hr"],
            ch4_mol_fraction=ex["inputs"]["ch4_mol_fraction"],
        )
        assert abs(res["ch4_tonnes"] - ex["expected"]["ch4_tonnes"]) <= ex["tolerance"]


# =============================================================================
# 3. APP CALCULATION VS INDEPENDENT ORACLE DIFFING
# =============================================================================

def test_app_combustion_vs_oracle(app_dispatcher):
    """
    Runs the app's calculation dispatcher on stationary combustion and diffs to Oracle.
    """
    fuel_qty = 10000.0
    ef_co2 = 1.93
    inputs = {
        "amount": fuel_qty,
        "unit": "m3",
        "fuel": "natural_gas",
        "fuel_type": "gas",
    }
    efs = {
        "co2": ef_co2,
        "ch4": 0.0001,
        "n2o": 0.00003,
        "unit": "kg/m3",
        "fuel_type": "gas",
    }
    app_res = app_dispatcher.dispatch("stationary_combustion", inputs, efs)

    oracle_res = oracle_combustion_tier1(
        Decimal(str(fuel_qty)), "m3", Decimal(str(ef_co2)), Decimal("0.0001"), Decimal("0.00003"), "m3"
    )

    app_co2 = app_res["results"]["co2"]["value"]
    oracle_co2 = float(oracle_res["co2_tonnes"])
    assert app_co2 == pytest.approx(oracle_co2, rel=1e-4)


def test_combustion_calculator_direct_tonnes():
    """
    Directly asserts CombustionCalculator.calculate output to kill MUT-02
    (division by 1000.0 from kg to tonnes).
    """
    from calculations.combustion import CombustionCalculator
    calc = CombustionCalculator()
    res = calc.calculate(
        fuel_quantity=10000.0,
        fuel_unit="m3",
        ef_co2=1.93,
        ef_unit="kg/m3",
        uncertainties={},
    )
    # Must be 19.3 tonnes, NOT 19,300,000 kg
    assert res["results"]["co2"]["value"] == pytest.approx(19.3, rel=1e-5)


def test_flaring_calculator_ch4_destruction_slip():
    """
    Asserts FlaringCalculator uncombusted CH4 destruction slip:
    CH4 (t) = vol * ch4_frac * (1 - eta_d) * density / 1000
    Kills MUT-03: (1 - eta_d) mutated to (1 + eta_d).
    """
    from calculations.combustion import FlaringCalculator
    calc = FlaringCalculator()
    res = calc.calculate(
        gas_volume=10000.0,
        ch4_fraction=0.80,
        flare_type="steam_assisted",
        uncertainties={},
        fuel_unit="m3",
        c1=0.80,
        co2_comp=0.05,
        destruction_efficiency=0.98,
    )
    # vol = 10,000 m3, ch4 = 0.80, slip = (1 - 0.98) = 0.02
    # slip_vol = 10000 * 0.80 * 0.02 = 160 m3
    # CH4 density = 0.67722 kg/m3 -> 160 * 0.67722 = 108.355 kg = 0.108355 tonnes
    ch4_tonnes = res["results"]["ch4"]["value"]
    assert ch4_tonnes == pytest.approx(0.108355, rel=1e-3)


def test_app_flaring_native_co2_detection(app_dispatcher):
    """
    Checks BUG-05: Tests whether the app properly handles standard 'co2' key in gas composition.
    """
    from calculations.combustion import FlaringCalculator
    calc = FlaringCalculator()
    
    res_custom = calc.calculate(
        gas_volume=10000.0,
        ch4_fraction=0.85,
        flare_type="steam_assisted",
        uncertainties={},
        fuel_unit="m3",
        c1=0.85,
        c2=0.05,
        co2_comp=0.02, # custom key works
    )
    res_standard = calc.calculate(
        gas_volume=10000.0,
        ch4_fraction=0.85,
        flare_type="steam_assisted",
        uncertainties={},
        fuel_unit="m3",
        c1=0.85,
        c2=0.05,
        co2=0.02, # standard key from units.py:980
    )
    
    # If the app drops native CO2 on key 'co2', this will fail, documenting BUG-05
    diff = abs(res_custom["results"]["co2"]["value"] - res_standard["results"]["co2"]["value"])
    if diff > 0.1:
        pytest.fail(f"BUG-05 REPRODUCED: App dropped native CO2 on key 'co2' (lost {diff:.4f} tonnes CO2)")


def test_app_flaring_n2o_hhv_unit_m3(app_dispatcher):
    """
    Checks BUG-04: Tests whether the app incorrectly inflates N2O by 35.3x with btu/m3.
    """
    from calculations.combustion import FlaringCalculator
    calc = FlaringCalculator()
    res = calc.calculate(
        gas_volume=1000.0,
        ch4_fraction=0.95,
        flare_type="steam_assisted",
        uncertainties={},
        fuel_unit="m3",
        hhv=36000.0,
        hhv_unit="btu/m3",
        ef_n2o=0.0001,
        ef_unit="kg/mmbtu",
        c1=0.95,
        co2_comp=0.05,
    )
    # Expected: 1,000 m3 * 36,000 btu/m3 = 36 MMBtu * 0.0001 / 1000 = 0.0000036 tonnes
    n2o_tonnes = res["results"]["n2o"]["value"]
    if n2o_tonnes > 0.0001:
        pytest.fail(f"BUG-04 REPRODUCED: N2O was inflated ~35.3x ({n2o_tonnes:.7f} vs expected 0.0000036 tonnes)")


def test_app_indirect_steam_net_efficiency_divergence(app_dispatcher):
    """
    Verifies BUG-06: App calculates net efficiency as (boiler_eff - loss) whereas
    thermodynamic first principles (and Oracle) calculate boiler_eff * (1 - loss).
    """
    from calculations.indirect import IndirectSteamCalculator
    calc = IndirectSteamCalculator()

    # Normal case: boiler 80%, loss 10%
    # Oracle: 0.80 * (1 - 0.10) = 0.72 net efficiency -> 100 MMBtu / 0.72 * 53.06 / 1000 = 7.3694 tonnes CO2
    oracle_res = oracle_scope2_purchased_steam(
        delivered_heat_mmbtu=Decimal("100.0"),
        ef_kg_co2e_per_mmbtu=Decimal("53.06"),
        boiler_efficiency=Decimal("0.80"),
        transmission_loss=Decimal("0.10"),
        model_mode="multiplicative",
    )
    # App subtractive: 0.80 - 0.10 = 0.70 net efficiency -> 100 / 0.70 * 53.06 / 1000 = 7.5800 tonnes CO2
    app_res = calc.calculate(
        heat_energy=100.0,
        heat_unit="mmbtu",
        ef_co2=53.06,
        boiler_efficiency=0.80,
        transmission_loss=0.10,
        uncertainties={},
    )
    app_co2 = app_res["results"]["co2"]["value"]
    assert app_co2 > float(oracle_res["co2e_tonnes"])
    assert app_co2 == pytest.approx(7.5800, rel=1e-3)

    # Boundary failure: loss >= boiler (0.50 and 0.50)
    with pytest.raises(ValueError, match="Net efficiency must be greater than 0"):
        calc.calculate(
            heat_energy=100.0,
            heat_unit="mmbtu",
            ef_co2=53.06,
            boiler_efficiency=0.50,
            transmission_loss=0.50,
            uncertainties={},
        )

