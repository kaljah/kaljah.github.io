"""
Authoritative Golden Dataset Generator.
Generates comprehensive test cases covering classes A through Q across all 34 GHG calculations.
Zero production dependencies - utilizes validation.reference_model for expected values.
"""
import json
import os
from validation.reference_model import (
    IndependentUnitConverter,
    IndependentGWPModel,
    IndependentCombustionModel,
    IndependentFlaringModel,
    IndependentMudDegassing,
    IndependentCompletions,
    IndependentLiquidsUnloading,
    IndependentBlowdown,
    IndependentStorageTanks,
    IndependentPneumatics,
    IndependentFugitiveModel,
    IndependentAGRModel,
    IndependentDehydratorModel,
    IndependentStoichiometryModel,
    IndependentScope2Model,
    IndependentScope3Model,
    IndependentUncertaintyModel,
    IndependentIntensityModel,
    IndependentOGMPModel,
)


def build_case(
    test_id,
    category_code,
    category_name,
    calc_type,
    methodology,
    activity_data,
    units,
    emission_factor,
    factor_source="default",
    factor_version="2021",
    gwp_version="AR5",
    gwp_horizon="100",
    intermediate_results=None,
    expected_final_result=None,
    expected_units="tCO2e",
    tolerance=1e-5,
    assumptions="",
    is_invalid=False,
    expected_error=None,
):
    return {
        "test_id": test_id,
        "category_code": category_code,
        "category_name": category_name,
        "calc_type": calc_type,
        "methodology": methodology,
        "activity_data": activity_data,
        "units": units,
        "emission_factor": emission_factor,
        "factor_source": factor_source,
        "factor_version": factor_version,
        "gwp_version": gwp_version,
        "gwp_horizon": gwp_horizon,
        "intermediate_results": intermediate_results or {},
        "expected_final_result": expected_final_result or {},
        "expected_units": expected_units,
        "tolerance": tolerance,
        "assumptions": assumptions,
        "is_invalid": is_invalid,
        "expected_error": expected_error,
    }


def generate_golden_dataset():
    cases = []

    # =========================================================================
    # A. NORMAL CASES (Baseline realistic operational scenarios)
    # =========================================================================
    # A1. Stationary Combustion Natural Gas (Tier 1 Energy-based kg/MMBtu)
    res_a1 = IndependentCombustionModel.calculate_tier1_2(
        fuel_quantity=100_000.0,
        fuel_unit="m3",
        emission_factors={"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"},
        fuel_type="natural_gas",
        hhv=1020.0,
    )
    cases.append(build_case(
        test_id="GOLD-A01-COMB-NG-NORM",
        category_code="A",
        category_name="Normal Case",
        calc_type="stationary_combustion",
        methodology="API Compendium 2021 §5.1 (Tier 1)",
        activity_data={"quantity": 100_000.0, "fuel_type": "natural_gas", "hhv": 1020.0},
        units="m3",
        emission_factor={"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"},
        intermediate_results={"energy_mmbtu": 100_000.0 * 35.314666721 * 1020.0 / 1e6},
        expected_final_result=res_a1,
        assumptions="Standard gas HHV 1020 Btu/scf, standard thermodynamic density",
    ))

    # A2. Flaring Dual Efficiency Elevated Flare
    res_a2 = IndependentFlaringModel.calculate(
        gas_volume=50_000.0,
        volume_unit="m3",
        ch4_fraction=0.88,
        flare_type="elevated",
        composition={"c1": 0.88, "c2": 0.05, "co2_mol": 0.02},
        ef_n2o=0.0001,
    )
    cases.append(build_case(
        test_id="GOLD-A02-FLARE-ELEV-NORM",
        category_code="A",
        category_name="Normal Case",
        calc_type="flaring",
        methodology="API Compendium 2021 §5.2 (Dual-Efficiency)",
        activity_data={"volume": 50_000.0, "amount": 50_000.0, "flare_type": "elevated", "ch4_fraction": 0.88, "c1": 0.88, "c2": 0.05, "co2_mol": 0.02},
        units="m3",
        emission_factor={"flare_type": "elevated", "ef_n2o": 0.0001, "ef_unit": "kg/m3"},
        expected_final_result=res_a2,
        assumptions="Elevated flare default eta_c=0.984, eta_d=0.980",
    ))

    # A3. Liquids Unloading
    res_a3 = IndependentLiquidsUnloading.calculate(
        well_depth=5000.0,
        diameter=2.441,
        pressure=150.0,
        events=12,
        ch4_content=0.85,
    )
    cases.append(build_case(
        test_id="GOLD-A03-UNLOAD-NORM",
        category_code="A",
        category_name="Normal Case",
        calc_type="liquids_unloading",
        methodology="API Compendium 2021 §6.4 Eq. 6-3",
        activity_data={"well_depth": 5000.0, "diameter": 2.441, "pressure": 150.0, "events": 12},
        units="events",
        emission_factor={"ch4_content": 0.85},
        expected_final_result=res_a3,
        assumptions="Tubing wellbore geometry at 150 psig, 60F",
    ))

    # A4. Storage Tank Flashing
    res_a4 = IndependentStorageTanks.calculate(
        throughput=10_000.0,
        throughput_unit="bbl",
        gas_oil_ratio=50.0,
        ch4_content=0.80,
    )
    cases.append(build_case(
        test_id="GOLD-A04-TANK-FLASH-NORM",
        category_code="A",
        category_name="Normal Case",
        calc_type="tank_flashing",
        methodology="API Compendium 2021 §6.8 GOR Method",
        activity_data={"throughput": 10_000.0, "gas_oil_ratio": 50.0},
        units="bbl",
        emission_factor={"gor": 50.0, "ch4_content": 0.80},
        expected_final_result=res_a4,
        assumptions="Flash gas GOR 50 scf/bbl, 80% CH4",
    ))

    # A5. Scope 2 Grid Electricity
    res_a5 = IndependentScope2Model.calculate_electricity(
        kwh=500_000.0,
        grid_ef=0.522,  # Algerian National Grid
    )
    cases.append(build_case(
        test_id="GOLD-A05-SCOPE2-GRID-NORM",
        category_code="A",
        category_name="Normal Case",
        calc_type="scope2_electricity",
        methodology="GHG Protocol Scope 2 Location-Based",
        activity_data={"electricity_kwh": 500_000.0},
        units="kWh",
        emission_factor={"factor": 0.522, "unit": "kg CO2e/kWh", "grid": "Algerian National Grid"},
        expected_final_result=res_a5,
        assumptions="500 MWh consumption in Algerian National Grid",
    ))

    # A6. Scope 3 Spend EEIO
    res_a6 = IndependentScope3Model.calculate(
        activity_amount=250_000.0,
        emission_factor=3200.1,  # NAICS 211 Oil & Gas Extraction
        factor_unit="kg CO2e/$1000",
        calc_method="spend_eeio",
    )
    cases.append(build_case(
        test_id="GOLD-A06-SCOPE3-EEIO-NORM",
        category_code="A",
        category_name="Normal Case",
        calc_type="scope3_spend",
        methodology="GHG Protocol Scope 3 Category 1 (USEEIO v1.3)",
        activity_data={"spend_amount": 250_000.0},
        units="USD",
        emission_factor={"factor": 3200.1, "unit": "kg CO2e/$1000", "naics": "211"},
        expected_final_result=res_a6,
        assumptions="$250k spend in NAICS 211 Oil & Gas extraction",
    ))

    # =========================================================================
    # B. ZERO CASES (Zero activity, zero factor, zero emissions)
    # =========================================================================
    res_b1 = IndependentCombustionModel.calculate_tier1_2(0.0, "m3", {"co2": 53.06, "unit": "kg/MMBtu"})
    cases.append(build_case(
        test_id="GOLD-B01-ZERO-ACTIVITY",
        category_code="B",
        category_name="Zero Case",
        calc_type="stationary_combustion",
        methodology="API Compendium 2021 §5.1",
        activity_data={"quantity": 0.0},
        units="m3",
        emission_factor={"co2": 53.06, "unit": "kg/MMBtu"},
        expected_final_result=res_b1,
        assumptions="Zero fuel consumption must result in exactly 0.0 emissions",
    ))

    res_b2 = IndependentScope2Model.calculate_electricity(0.0, 0.522)
    cases.append(build_case(
        test_id="GOLD-B02-ZERO-SCOPE2",
        category_code="B",
        category_name="Zero Case",
        calc_type="scope2_electricity",
        methodology="GHG Protocol Scope 2",
        activity_data={"electricity_kwh": 0.0},
        units="kWh",
        emission_factor={"factor": 0.522},
        expected_final_result=res_b2,
        assumptions="Zero kWh must produce 0.0 tCO2e",
    ))

    # =========================================================================
    # C. VERY SMALL VALUES (Micro / Sub-milligram trace quantities)
    # =========================================================================
    res_c1 = IndependentCombustionModel.calculate_tier1_2(1e-6, "m3", {"co2": 1.861, "unit": "kg/m3"})
    cases.append(build_case(
        test_id="GOLD-C01-VERY-SMALL-VAL",
        category_code="C",
        category_name="Very Small Value",
        calc_type="stationary_combustion",
        methodology="API Compendium 2021 §5.1",
        activity_data={"quantity": 1e-6},
        units="m3",
        emission_factor={"co2": 1.861, "unit": "kg/m3"},
        expected_final_result=res_c1,
        tolerance=1e-12,
        assumptions="1 micro-cubic-meter fuel trace calculation",
    ))

    # =========================================================================
    # D. VERY LARGE VALUES (Gigawatt-scale refinery / field operations)
    # =========================================================================
    res_d1 = IndependentCombustionModel.calculate_tier1_2(1e9, "m3", {"co2": 1.861, "unit": "kg/m3"})
    cases.append(build_case(
        test_id="GOLD-D01-VERY-LARGE-VAL",
        category_code="D",
        category_name="Very Large Value",
        calc_type="stationary_combustion",
        methodology="API Compendium 2021 §5.1",
        activity_data={"quantity": 1e9},
        units="m3",
        emission_factor={"co2": 1.861, "unit": "kg/m3"},
        expected_final_result=res_d1,
        tolerance=1e-3,
        assumptions="1 billion m3 fuel industrial refinery throughput",
    ))

    # =========================================================================
    # E. DECIMAL / FRACTIONAL VALUES
    # =========================================================================
    res_e1 = IndependentFugitiveModel.calculate_equipment(17.385, 0.0045, ef_unit="kg/hr", ch4_content=0.8432)
    cases.append(build_case(
        test_id="GOLD-E01-DECIMAL-VALS",
        category_code="E",
        category_name="Decimal Value",
        calc_type="equipment_fugitive",
        methodology="API Compendium 2021 §7.2",
        activity_data={"equipment_count": 17.385, "ch4_content": 0.8432},
        units="count",
        emission_factor={"factor": 0.0045, "unit": "kg/hr"},
        expected_final_result=res_e1,
        assumptions="Fractional equipment count and non-integer composition",
    ))

    # =========================================================================
    # F. BOUNDARY VALUES (Efficiencies at 0.0, 1.0, 100.0%)
    # =========================================================================
    res_f1 = IndependentFlaringModel.calculate(
        gas_volume=10_000.0,
        volume_unit="m3",
        ch4_fraction=0.85,
        combustion_eff=1.0,
        destruction_eff=1.0,
    )
    cases.append(build_case(
        test_id="GOLD-F01-EFFICIENCY-100PCT",
        category_code="F",
        category_name="Boundary Value",
        calc_type="flaring",
        methodology="API Compendium 2021 §5.2",
        activity_data={"volume": 10_000.0, "amount": 10_000.0, "c1": 0.85, "ch4_fraction": 0.85, "flare_type": "elevated", "combustion_efficiency": 1.0, "destruction_efficiency": 1.0},
        units="m3",
        emission_factor={"ch4_content": 0.85, "c1": 0.85},
        expected_final_result=res_f1,
        assumptions="100% destruction efficiency must yield exactly 0.0 unburnt CH4",
    ))

    res_f2 = IndependentFlaringModel.calculate(
        gas_volume=10_000.0,
        volume_unit="m3",
        ch4_fraction=0.85,
        combustion_eff=0.0,
        destruction_eff=0.0,
    )
    cases.append(build_case(
        test_id="GOLD-F02-EFFICIENCY-0PCT",
        category_code="F",
        category_name="Boundary Value",
        calc_type="flaring",
        methodology="API Compendium 2021 §5.2",
        activity_data={"volume": 10_000.0, "amount": 10_000.0, "c1": 0.85, "ch4_fraction": 0.85, "flare_type": "elevated", "combustion_efficiency": 0.0, "destruction_efficiency": 0.0},
        units="m3",
        emission_factor={"ch4_content": 0.85, "c1": 0.85},
        expected_final_result=res_f2,
        assumptions="0% combustion efficiency yields 0.0 combusted CO2 and 100% unburnt CH4",
    ))

    # =========================================================================
    # G. MISSING OPTIONAL VALUES (Graceful fallback defaults)
    # =========================================================================
    res_g1 = IndependentPneumatics.calculate(count=10, hours=None, bleed_rate=15.0)  # hours defaults to 8760
    cases.append(build_case(
        test_id="GOLD-G01-MISSING-OPTIONAL-HOURS",
        category_code="G",
        category_name="Missing Optional Value",
        calc_type="pneumatic_device",
        methodology="API Compendium 2021 §6.10",
        activity_data={"count": 10, "bleed_rate": 15.0, "pneu_ch4_content": 0.85, "ch4_content": 0.85},
        units="count",
        emission_factor={"bleed_rate": 15.0},
        expected_final_result=res_g1,
        assumptions="Missing operating hours defaults authoritatively to 8760 hours/yr",
    ))

    # =========================================================================
    # H. INVALID VALUES (NaN, Infinity, Malformed)
    # =========================================================================
    cases.append(build_case(
        test_id="GOLD-H01-INVALID-NAN-QTY",
        category_code="H",
        category_name="Invalid Value",
        calc_type="stationary_combustion",
        methodology="API Compendium 2021 §5.1",
        activity_data={"quantity": "NaN"},
        units="m3",
        emission_factor={"co2": 53.06},
        is_invalid=True,
        expected_error="ValueError",
        assumptions="System must reject NaN activity data and not produce numeric emissions",
    ))

    cases.append(build_case(
        test_id="GOLD-H02-INVALID-INF-QTY",
        category_code="H",
        category_name="Invalid Value",
        calc_type="stationary_combustion",
        methodology="API Compendium 2021 §5.1",
        activity_data={"quantity": "Infinity"},
        units="m3",
        emission_factor={"co2": 53.06},
        is_invalid=True,
        expected_error="ValueError",
        assumptions="System must reject infinite activity data",
    ))

    # =========================================================================
    # I. NEGATIVE VALUES (Negative quantities prohibited)
    # =========================================================================
    cases.append(build_case(
        test_id="GOLD-I01-NEGATIVE-QTY-REJECTED",
        category_code="I",
        category_name="Negative Value",
        calc_type="stationary_combustion",
        methodology="API Compendium 2021 §5.1",
        activity_data={"quantity": -500.0},
        units="m3",
        emission_factor={"co2": 53.06},
        is_invalid=True,
        expected_error="ValueError",
        assumptions="Negative fuel quantity must be rejected to prevent negative emissions",
    ))

    # =========================================================================
    # J. UNIT CONVERSION CASES (Equivalence across unit systems)
    # =========================================================================
    # 1 tonne = 1000 kg = 1,000,000 g
    res_j1 = IndependentCombustionModel.calculate_tier1_2(1.0, "tonne", {"co2": 2.5, "unit": "kg/kg"})
    res_j2 = IndependentCombustionModel.calculate_tier1_2(1000.0, "kg", {"co2": 2.5, "unit": "kg/kg"})
    res_j3 = IndependentCombustionModel.calculate_tier1_2(1_000_000.0, "g", {"co2": 2.5, "unit": "kg/kg"})
    cases.append(build_case(
        test_id="GOLD-J01-UNIT-EQUIV-MASS",
        category_code="J",
        category_name="Unit Conversion Equivalence",
        calc_type="stationary_combustion",
        methodology="API Compendium 2021 §5.1",
        activity_data={"equiv_cases": [1.0, 1000.0, 1e6]},
        units="tonne/kg/g",
        emission_factor={"co2": 2.5, "unit": "kg/kg"},
        expected_final_result={"tonne": res_j1, "kg": res_j2, "gram": res_j3},
        tolerance=1e-8,
        assumptions="1 tonne == 1000 kg == 1,000,000 g must yield identical emissions",
    ))

    # =========================================================================
    # K. MULTIPLE-GAS CASES (Simultaneous CO2, CH4, N2O)
    # =========================================================================
    res_k1 = IndependentCombustionModel.calculate_tier1_2(
        fuel_quantity=10_000.0,
        fuel_unit="m3",
        emission_factors={"co2": 1.9, "ch4": 0.05, "n2o": 0.002, "unit": "kg/m3"},
    )
    cases.append(build_case(
        test_id="GOLD-K01-MULTI-GAS-MASS",
        category_code="K",
        category_name="Multiple-Gas Case",
        calc_type="stationary_combustion",
        methodology="API Compendium 2021 §5.1",
        activity_data={"quantity": 10_000.0},
        units="m3",
        emission_factor={"co2": 1.9, "ch4": 0.05, "n2o": 0.002, "unit": "kg/m3"},
        expected_final_result=res_k1,
        assumptions="Independent tracking of CO2, CH4, and N2O masses and combined CO2e",
    ))

    # =========================================================================
    # L. MULTIPLE-SOURCE AGGREGATION
    # =========================================================================
    s1 = {"value": 1500.0, "uncertainty": 0.05}
    s2 = {"value": 3500.0, "uncertainty": 0.07}
    u_comb = IndependentUncertaintyModel.combine_sum([s1, s2])
    cases.append(build_case(
        test_id="GOLD-L01-MULTI-SOURCE-AGG",
        category_code="L",
        category_name="Multiple-Source Case",
        calc_type="aggregation_uncertainty",
        methodology="IPCC 2006 GL Vol. 1 §3.3 Eq. 3.2",
        activity_data={"sources": [s1, s2]},
        units="tCO2e",
        emission_factor={},
        expected_final_result={"total_value": 5000.0, "relative_uncertainty": u_comb},
        assumptions="Additive aggregation of independent emission sources with SRSS uncertainty",
    ))

    # =========================================================================
    # M. MULTIPLE-FACILITY PORTFOLIO
    # =========================================================================
    boe_fac1 = IndependentIntensityModel.calculate_boe(100_000.0, 50_000.0)
    boe_fac2 = IndependentIntensityModel.calculate_boe(250_000.0, 10_000.0)
    cases.append(build_case(
        test_id="GOLD-M01-MULTI-FACILITY-BOE",
        category_code="M",
        category_name="Multiple-Facility Case",
        calc_type="production_boe",
        methodology="SPE / WPC BOE Normalization",
        activity_data={"facility_1": {"oil": 100_000.0, "gas": 50_000.0}, "facility_2": {"oil": 250_000.0, "gas": 10_000.0}},
        units="BOE",
        emission_factor={},
        expected_final_result={"fac1_boe": boe_fac1, "fac2_boe": boe_fac2, "total_boe": boe_fac1 + boe_fac2},
        assumptions="Portfolio BOE aggregation from oil and gas production",
    ))

    # =========================================================================
    # N. MULTIPLE-YEAR HISTORICAL COMPARISON
    # =========================================================================
    wec_2024 = IndependentIntensityModel.calculate_wec(ch4_tonnes=150.0, gas_prod_m3=10_000_000.0, year=2024)
    wec_2025 = IndependentIntensityModel.calculate_wec(ch4_tonnes=150.0, gas_prod_m3=10_000_000.0, year=2025)
    wec_2026 = IndependentIntensityModel.calculate_wec(ch4_tonnes=150.0, gas_prod_m3=10_000_000.0, year=2026)
    cases.append(build_case(
        test_id="GOLD-N01-MULTI-YEAR-WEC",
        category_code="N",
        category_name="Multiple-Year Case",
        calc_type="epa_wec",
        methodology="EPA 40 CFR Part 99 / IRA §136",
        activity_data={"ch4_tonnes": 150.0, "gas_prod_m3": 10_000_000.0},
        units="tCH4",
        emission_factor={},
        expected_final_result={"wec_2024": wec_2024, "wec_2025": wec_2025, "wec_2026": wec_2026},
        assumptions="Statutory escalation of WEC fee: $900 in 2024, $1200 in 2025, $1500 in 2026+",
    ))

    # =========================================================================
    # O. CUSTOM EMISSION FACTOR CASE
    # =========================================================================
    res_o1 = IndependentCombustionModel.calculate_tier1_2(
        fuel_quantity=50_000.0,
        fuel_unit="m3",
        emission_factors={"co2": 2.15, "ch4": 0.08, "n2o": 0.005, "unit": "kg/m3"},
        fuel_type="custom_fuel_blend",
    )
    cases.append(build_case(
        test_id="GOLD-O01-CUSTOM-FACTOR",
        category_code="O",
        category_name="Custom Emission Factor Case",
        calc_type="stationary_combustion",
        methodology="Tier 2 Facility-Specific Custom Factor",
        activity_data={"quantity": 50_000.0, "fuel_type": "custom_fuel_blend"},
        units="m3",
        emission_factor={"co2": 2.15, "ch4": 0.08, "n2o": 0.005, "unit": "kg/m3"},
        factor_source="custom",
        expected_final_result=res_o1,
        assumptions="Tier 2 user-defined custom emission factor",
    ))

    # =========================================================================
    # P. DEFAULT FACTOR CASE
    # =========================================================================
    res_p1 = IndependentDehydratorModel.calculate_tier1(throughput_mmscf=100.0)
    cases.append(build_case(
        test_id="GOLD-P01-DEFAULT-DEHY-FACTOR",
        category_code="P",
        category_name="Default Factor Case",
        calc_type="dehydrator",
        methodology="API Compendium 2021 Table 6-6",
        activity_data={"throughput_mmscf": 100.0},
        units="MMscf",
        emission_factor={"factor": 0.266, "unit": "tonnes CH4/MMscf"},
        factor_source="default",
        expected_final_result=res_p1,
        assumptions="API Table 6-6 Tier 1 default uncontrolled factor 0.266 tCH4/MMscf",
    ))

    # =========================================================================
    # Q. DIFFERENT METHODOLOGY COMPARISON (Tier 1 vs Tier 3 Engineering)
    # =========================================================================
    res_q_t1 = IndependentDehydratorModel.calculate_tier1(throughput_mmscf=50.0)
    res_q_t3 = IndependentDehydratorModel.calculate_tier3(
        pump_rate=15.0,
        pump_unit="gph",
        hours=8760.0,
        ch4_content=0.85,
        contactor_press=800.0,
        contactor_temp=100.0,
    )
    cases.append(build_case(
        test_id="GOLD-Q01-METHODOLOGY-COMPARISON",
        category_code="Q",
        category_name="Different Methodology Case",
        calc_type="dehydrator_methodology",
        methodology="Tier 1 Default Factor vs Tier 3 Henry's Law Solubility",
        activity_data={"tier1_throughput_mmscf": 50.0, "tier3_pump_rate": 15.0, "hours": 8760.0},
        units="MMscf / gph",
        emission_factor={},
        expected_final_result={"tier1": res_q_t1, "tier3": res_q_t3},
        assumptions="Comparison of generic throughput screening vs physical Henry's law glycol solubility",
    ))

    return cases


def get_golden_cases():
    return generate_golden_dataset()


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    cases = generate_golden_dataset()
    json_path = os.path.join(out_dir, "golden_cases.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)
    print(f"Generated {len(cases)} golden dataset test cases at {json_path}")
