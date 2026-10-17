"""
Test Untested Calculation Paths - Part 9
Forensic test suite covering Bugs 41 through 50:
- Bug 41: Vented production wells gas composition validation (Dalton's law, scale coordination, non-negative).
- Bug 42: WorkoverWithoutFracturingCalculator non-negative workovers and percentage parsing.
- Bug 43: CasingGasVentCalculator non-negative inputs and percentage actual_vent_fraction normalization.
- Bug 44: CO2EORVentingCalculator non-negative events, oil production, and retained CO2.
- Bug 45: ProductionNonRoutineVentingCalculator non-negative vent rate, duration, and events.
- Bug 46: Indirect energy/steam non-negative energy amount and emission factors.
- Bug 47: CogenAllocationCalculator non-negative emissions and 0.5% / 1% efficiency normalization.
- Bug 48: ActivityFactorCalculator non-negative operating days/hours and mixture consistency.
- Bug 49: LiquidsUnloadingCalculator Eq 6-10 and 6-11 non-negative SFR and hours.
- Bug 50: Downstream Refining, Petrochem, Coking, and H2 plant fraction normalization and physical bounds.
"""
import pytest
from calculations.vented_production_wells import (
    WorkoverWithoutFracturingCalculator,
    CasingGasVentCalculator,
    CO2EORVentingCalculator,
    ProductionNonRoutineVentingCalculator,
)
from calculations.indirect import (
    heat_to_mmbtu,
    IndirectSteamCalculator,
    CogenAllocationCalculator,
)
from calculations.activity_factors import ActivityFactorCalculator
from calculations.vented_unloading import LiquidsUnloadingCalculator
from calculations.vented_downstream import (
    SulfurRecoveryTailGasCalculator,
    PetrochemicalManufacturingCalculator,
    RefiningCokerCalculator,
    RefiningCokeCalciningCalculator,
    RefiningHydrogenPlantCalculator,
)


# ==============================================================================
# Bug 41 & 42: Vented Production Wells - Gas Composition & Workovers
# ==============================================================================
def test_workover_without_fracturing_gas_comp_and_negative_events():
    calc = WorkoverWithoutFracturingCalculator()

    # Negative workovers must raise ValueError
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(workovers=-2)

    # Negative gas content must raise ValueError
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(workovers=5, ch4_content="-5%")

    # Dalton's law / mixture constraint check
    with pytest.raises(ValueError, match="cannot exceed 100%"):
        calc.calculate(workovers=5, ch4_content="85%", co2_content="25%")

    # Percentage string parsing and scale coordination
    res = calc.calculate(workovers=5, ch4_content="85.5%", co2_content="1.5%")
    assert res["inputs"]["ch4_content"] == pytest.approx(0.855, rel=1e-4)
    assert res["inputs"]["co2_content"] == pytest.approx(0.015, rel=1e-4)
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > 0


# ==============================================================================
# Bug 43: Casing Gas Venting - Non-negative validation & Vent Fraction
# ==============================================================================
def test_casing_gas_vent_calculator_bounds_and_fraction():
    calc = CasingGasVentCalculator()

    # Negative well count
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(method="well_count", well_count=-3)

    # Negative throughput
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(method="throughput", throughput=-100)

    # Negative throughput rate
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(method="throughput", throughput_rate=-50)

    # Negative measured gas volume
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(method="direct_measurement", measured_gas_volume=-500)

    # Percentage string in actual_vent_fraction and mathematical scaling verification
    res_default = calc.calculate(
        method="throughput",
        throughput=1000,
        throughput_unit="bbl/yr",
        ch4_content="80%",
    )
    res_custom = calc.calculate(
        method="throughput",
        throughput=1000,
        throughput_unit="bbl/yr",
        actual_vent_fraction="65.5%",
        ch4_content="80%",
    )
    # Default primary heavy oil venting fraction is 63.2%
    expected_ratio = 0.655 / 0.632
    assert res_custom["results"]["ch4"]["value"] == pytest.approx(
        res_default["results"]["ch4"]["value"] * expected_ratio, rel=1e-4
    )
    assert res_custom["total_co2e"] > 0


# ==============================================================================
# Bug 44: CO2 EOR Venting - Non-negative events & production
# ==============================================================================
def test_co2_eor_venting_calculator_bounds():
    calc = CO2EORVentingCalculator()

    # Negative events
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="pump_blowdown", events=-1, physical_volume_m3=10, co2_density_kg_m3=650, co2_weight_fraction=0.98)

    # Negative oil production
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="dissolved_retention", oil_production_bbl=-5000, co2_retained_tonnes_per_bbl=0.05)

    # Negative retained CO2
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="dissolved_retention", oil_production_bbl=5000, co2_retained_tonnes_per_bbl=-0.1)

    # Valid run
    res = calc.calculate(activity="dissolved_retention", oil_production_bbl=10000, co2_retained_tonnes_per_bbl=0.05)
    assert res["results"]["co2"]["value"] > 0
    assert res["total_co2e"] > 0


# ==============================================================================
# Bug 45: Production Non-Routine Venting - Non-negative validation
# ==============================================================================
def test_production_non_routine_venting_bounds():
    calc = ProductionNonRoutineVentingCalculator()

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(vent_rate_scfm=-10.0, duration_minutes=30.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(vent_rate_scfm=50.0, duration_minutes=-15.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(vent_rate_scfm=50.0, duration_minutes=60.0, events=-2)

    res = calc.calculate(vent_rate_scfm=100.0, duration_minutes=60.0, events=2, ch4_content="88%")
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > 0


# ==============================================================================
# Bug 46: Indirect Steam & Heat - Non-negative bounds
# ==============================================================================
def test_indirect_heat_and_steam_bounds():
    # Negative heat amount
    with pytest.raises(ValueError, match="cannot be negative"):
        heat_to_mmbtu(-50.0, "mmbtu")

    calc = IndirectSteamCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(heat_energy=100.0, ef_co2=-1.5, boiler_efficiency=0.8, transmission_loss=0.0, uncertainties=None)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(heat_energy=100.0, ef_co2=0.05, boiler_efficiency=0.8, transmission_loss=0.0, uncertainties=None, ef_ch4=-0.01)

    res = calc.calculate(heat_energy=500.0, heat_unit="mmbtu", ef_co2=0.07, boiler_efficiency=0.85, transmission_loss=0.05, ef_ch4=0.001, ef_n2o=0.0001, uncertainties=None)
    assert res["results"]["co2"]["value"] > 0
    assert res["total_co2e"] > 0


# ==============================================================================
# Bug 47: Cogen Allocation - Efficiency normalization and bounds
# ==============================================================================
def test_cogen_allocation_calculator_bounds_and_efficiencies():
    calc = CogenAllocationCalculator()

    # Negative total emissions
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(total_emissions=-100.0, heat_output=200.0, power_output=50.0)

    # 0.5% and 1% efficiency strings must not be corrupted to 50% or 100%
    res = calc.calculate(
        total_emissions=1000.0,
        heat_output=500.0,
        power_output=100.0,
        heat_efficiency="0.5%",
        power_efficiency="1%",
        method="wri_efficiency",
    )
    # heat_share = 500 / 0.005 = 100,000; power_share = 100 / 0.01 = 10,000
    # denominator = 110,000 -> allocated_heat = 1000 * 100/110 = 909.0909 tonnes
    assert res["total_co2e"] == pytest.approx(909.0909, rel=1e-4)
    assert res["metadata"]["allocated_heat_tonnes"] == pytest.approx(909.0909, rel=1e-4)
    assert res["metadata"]["allocated_power_tonnes"] == pytest.approx(90.9091, rel=1e-4)
    assert res["metadata"]["allocated_heat_tonnes"] + res["metadata"]["allocated_power_tonnes"] == pytest.approx(1000.0, rel=1e-4)


# ==============================================================================
# Bug 48: Activity Factor Calculator - Operating time & mixture bounds
# ==============================================================================
def test_activity_factor_calculator_bounds():
    calc = ActivityFactorCalculator()

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(key="cg_migration", amount=5, days=-10)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(key="prod_pc_high_bleed_api", amount=5, hours=-5)

    with pytest.raises(ValueError, match="cannot exceed 100%"):
        calc.calculate(key="prod_pc_high_bleed_api", amount=5, ch4_content="80%", co2_content="30%")

    res = calc.calculate(
        key="prod_pc_high_bleed_api",
        amount=2,
        hours=100,
        ch4_content="90%",
    )
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > 0


# ==============================================================================
# Bug 49: Liquids Unloading - Eq 6-10 and 6-11 non-negative rate / hours
# ==============================================================================
def test_liquids_unloading_equations_non_negative_bounds():
    calc = LiquidsUnloadingCalculator()

    # Eq 6-10: negative sfr
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate_tier3_equation_6_10(
            events=5,
            well_depth=5000,
            diameter=2.5,
            pressure=100,
            sfr=-10.0,
            hours_open=2.0,
            ch4_content=0.85,
        )

    # Eq 6-10: negative hours_open
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate_tier3_equation_6_10(
            events=5,
            well_depth=5000,
            diameter=2.5,
            pressure=100,
            sfr=50.0,
            hours_open=-1.0,
            ch4_content=0.85,
        )

    # Eq 6-11: negative sfr_p
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate_tier3_equation_6_11(
            p_shut=200,
            p_line=50,
            p_sep=30,
            sfr_p=-100.0,
            t_p=1.5,
            ch4_content=0.85,
        )

    # Eq 6-11: negative t_p
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate_tier3_equation_6_11(
            p_shut=200,
            p_line=50,
            p_sep=30,
            sfr_p=500.0,
            t_p=-0.5,
            ch4_content=0.85,
        )


# ==============================================================================
# Bug 50: Downstream Refining, Petrochem, Coking, and H2 Plants
# ==============================================================================
def test_downstream_calculators_bounds_and_fraction_parsing():
    # 1. SulfurRecoveryTailGasCalculator
    sru = SulfurRecoveryTailGasCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        sru.calculate(sour_gas_scf_yr=-1000)

    with pytest.raises(ValueError, match="cannot be negative"):
        sru.calculate(refinery_throughput_bbl_yr=-500)

    # Percentage string in carbon_mole_fraction
    res_sru = sru.calculate(sour_gas_scf_yr=1_000_000, carbon_mole_fraction="22.5%")
    assert res_sru["results"]["co2"]["value"] > 0
    assert res_sru["total_co2e"] > 0

    # 2. PetrochemicalManufacturingCalculator
    petro = PetrochemicalManufacturingCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        petro.calculate(process_type="methanol", production_tonnes=-100)

    with pytest.raises(ValueError, match="cannot be negative"):
        petro.calculate(
            feedstocks=[(-50, "85%")],
            primary_product_tonnes=30,
            primary_product_c_frac="90%",
        )

    res_petro = petro.calculate(
        feedstocks=[(100, "85%"), (20, "50%")],
        primary_product_tonnes=80,
        primary_product_c_frac="90%",
        secondary_products=[(10, "40%")],
    )
    assert res_petro["results"]["co2"]["value"] > 0
    assert res_petro["total_co2e"] > 0

    # 3. RefiningCokerCalculator
    coker = RefiningCokerCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        coker.calculate(coker_type="delayed", steam_mass_tonnes_cycle=-5.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        coker.calculate(coker_type="delayed", steam_mass_tonnes_cycle=10.0, num_cycles_per_yr=-1)

    res_coker = coker.calculate(coker_type="delayed", steam_mass_tonnes_cycle=10.0, num_cycles_per_yr=50)
    assert res_coker["results"]["ch4"]["value"] > 0
    assert res_coker["total_co2e"] > 0

    # 4. RefiningCokeCalciningCalculator
    calcining = RefiningCokeCalciningCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        calcining.calculate(green_coke_mass_tonnes_yr=-100, green_coke_carbon_fraction="90%", calcined_coke_carbon_fraction="95%")

    res_calc = calcining.calculate(
        green_coke_mass_tonnes_yr=1000,
        green_coke_carbon_fraction="90%",
        calcined_coke_mass_tonnes_yr=800,
        calcined_coke_carbon_fraction="95%",
    )
    assert res_calc["results"]["co2"]["value"] > 0
    assert res_calc["total_co2e"] > 0

    # 5. RefiningHydrogenPlantCalculator
    h2_calc = RefiningHydrogenPlantCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        h2_calc.calculate(method="feedstock_balance", feedstock_rate_tonnes_yr=-100, feedstock_carbon_fraction="80%")

    with pytest.raises(ValueError, match="cannot be negative"):
        h2_calc.calculate(method="h2_stoichiometry", h2_production_scf_yr=-50000, co2_to_h2_molar_ratio=0.25)

    res_h2 = h2_calc.calculate(method="feedstock_balance", feedstock_rate_tonnes_yr=1000, feedstock_carbon_fraction="85%")
    assert res_h2["results"]["co2"]["value"] > 0
    assert res_h2["total_co2e"] > 0
