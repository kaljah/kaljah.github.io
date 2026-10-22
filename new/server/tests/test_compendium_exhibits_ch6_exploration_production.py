"""API Compendium 2021 worked examples, chapter 6.2 and 6.3 (exploration, completions, associated gas, workovers,
unloading, casing gas). Printed values quoted from the exhibit; see compendium_exhibits_support for tolerances.
"PDF line" is the line in ``pdftotext -layout`` output of API-GHG-Compendium-110921.pdf.
"""
import pytest

from calculations.vented_associated_gas import AssociatedGasVentingCalculator
from calculations.vented_exploration import CoalSeamDrillingCalculator, WellTestingCalculator
from calculations.vented_mud import MudDegassingCalculator
from calculations.vented_production_wells import WorkoverWithoutFracturingCalculator

from compendium_exhibits_support import REL_MW, assert_printed, run_scope1, tonnes

GWP = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}


def test_exhibit_6_1_mud_degassing_water_based():
    """PDF line 10847. 85 drilling days, water-based mud, 70 mol % CH4, 9 mol % CO2: CH4 18.49, CO2 6.54 tonnes/yr.
    The exhibit uses the 0.2605 t CH4/day water-based factor of Table 6-2 (the offshore row)."""
    res = MudDegassingCalculator().calculate(tier="tier2_plus", drilling_days=85, mud_type="water_based",
                                             ch4_concentration=70, co2_concentration=9, location="offshore",
                                             gwp_dict=GWP)
    assert_printed(tonnes(res, "ch4"), "18.49", what="CH4")
    assert_printed(tonnes(res, "co2"), "6.54", rel=REL_MW, what="CO2")


def test_exhibit_6_2_oil_well_test_vented_six_hours():
    """PDF line 10991. GOR 700 scf/bbl, 4,200 bbl/day, 6 h vented (735,000 scf), 70 % CH4, 10 % CO2:
    CH4 9.84, CO2 3.87 tonnes/event."""
    res = WellTestingCalculator().calculate(tier="tier2", well_type="oil_well", gor=700, oil_production_rate=4200,
                                            test_duration_hours=6, ch4_content=70, co2_content=10, gwp_dict=GWP)
    assert_printed(tonnes(res, "ch4"), "9.84", gas="ch4", rel=0.0006, what="CH4")
    assert_printed(tonnes(res, "co2"), "3.87", gas="co2", rel=0.0002, what="CO2")


def test_exhibit_6_3_completion_with_hydraulic_fracturing(app):
    """PDF line 11191. 1.48e6 scf metered to a flare over 20 h, 7,390 scf N2, 4 h vented initial flowback, 70 % CH4,
    98 % flare: vented CH4 1.97, flared CO2 98.7, flared CH4 0.39 tonnes (CH4 total 2.36)."""
    em = run_scope1(app, {
        "process_type": "completions", "factor_source": "specific", "amount": 1, "unit": "events",
        "calc_inputs": {"completions": {"tier": "tier3", "calc_method": "metered", "comp_volume": 1480000,
                                        "volume_unit": "scf", "comp_injected_n2": 7390, "comp_injected_n2_unit": "scf",
                                        "comp_initial_flowback_hours": 4, "comp_duration": 20, "comp_ch4_content": 70,
                                        "comp_c2plus_content": 30, "comp_disposition": "flared", "comp_flare_eff": 98,
                                        "events": 1}}})
    # 2.36 is the sum of two values printed to 0.01 (1.97 and 0.39): +/-0.01 rounding plus the MW difference
    assert_printed(em["ch4"], "2.36", slack=4.0, what="CH4 (1.97 vented + 0.39 flared)")
    assert_printed(em["co2"], "98.7", rel=0.0002, what="CO2")


def _coal(**kw):
    return CoalSeamDrillingCalculator().calculate(gwp_dict=GWP, ch4_content=0.887, co2_content=0.109, **kw)


def test_exhibit_6_5_coal_seam_vented_drilling_gas():
    """PDF line 11505. Three wells (5 d x 1.5, 2 d x 1.5, 5 d x 1.75 MMscf/d = 19.25e6 scf), 88.7 % CH4, 10.9 % CO2:
    vented CH4 327, CO2 110 tonnes."""
    res = _coal(wells_data=[{"duration_days": 5, "gas_consumption_mmscf_day": 1.5},
                            {"duration_days": 2, "gas_consumption_mmscf_day": 1.5},
                            {"duration_days": 5, "gas_consumption_mmscf_day": 1.75}])
    assert_printed(tonnes(res, "ch4"), "327", gas="ch4", rel=0.0002, what="CH4")
    assert_printed(tonnes(res, "co2"), "110", rel=0.0002, what="CO2")


def test_exhibit_6_5_coal_seam_flared_well_test_gas():
    """PDF line 11505. 6.76e6 scf per well x 3 wells flared at 98 % (the 'other' 0.4 % taken as ethane):
    CO2 1,050, CH4 6.9 tonnes. Known small difference: the calculator keeps the 0.4 % 'other' gas inert, the exhibit
    burns it as ethane (+0.8 % CO2: the exhibit's own arithmetic gives 1,052, the engine 1,044, both inside the
    three-figure 1,050 plus the molecular-weight tolerance)."""
    res = _coal(drilling_gas_vented_scf=0, well_testing_gas_flared_scf=6.76e6 * 3)
    assert_printed(tonnes(res, "co2"), "1,050", sig=3, rel=REL_MW, what="CO2")
    assert_printed(tonnes(res, "ch4"), "6.9", rel=0.0002, what="CH4")


@pytest.mark.parametrize("days,ch4,co2", [(15, "731", "287"), (365, "17,795", "6,991")])
def test_exhibits_6_5_and_6_6_associated_gas_venting(days, ch4, co2):
    """PDF lines 11631 (6-5, 15 days vented: CH4 731, CO2 287 t/yr) and 11674 (6-6, 365 days: 17,795 / 6,991).
    5,200 bbl/day, GOR 700 scf/bbl, 70 % CH4, 10 % CO2."""
    res = AssociatedGasVentingCalculator().calculate(
        tier="tier2", oil_production=5200, oil_unit="bbl/day", gor=700, gor_unit="scf/bbl", venting_duration=days,
        duration_unit="days", period_duration=365, ch4_content=70, co2_content=10, gwp_dict=GWP)
    assert_printed(tonnes(res, "ch4"), ch4, rel=REL_MW, what="CH4")
    assert_printed(tonnes(res, "co2"), co2, rel=REL_MW, what="CO2")


def test_exhibit_6_7_gas_well_workovers_without_fracturing():
    """PDF line 11813. 10 workovers, whole-gas factor 3,114 scf/workover, 70 % CH4, 9 % CO2:
    CH4 0.42, CO2 0.15 tonnes/yr."""
    res = WorkoverWithoutFracturingCalculator().calculate(workovers=10, well_type="gas_well", ch4_content=70,
                                                          co2_content=9, gwp_dict=GWP)
    assert_printed(tonnes(res, "ch4"), "0.42", rel=0.0002, what="CH4")
    assert_printed(tonnes(res, "co2"), "0.15", gas="co2", rel=0.0002, what="CO2")


def test_exhibit_6_8_liquids_unloading_equation_6_10():
    """PDF line 11964. 12 unloadings/yr, 10 in casing, 12,000 ft, 250 psig, 35,000 scf/h for 1 h, no plunger,
    80 % CH4, 3 % CO2: volume 1,332,000 scf/yr, CH4 20.39, CO2 2.10 tonnes/yr."""
    from calculations.vented_unloading import LiquidsUnloadingCalculator
    res = LiquidsUnloadingCalculator().calculate_tier3_equation_6_10(
        events=12, well_depth=12000, diameter=10.0, pressure=250.0, sfr=35000.0, hours_open=1.0,
        unloading_type="non_plunger", ch4_content=0.80, co2_content=0.03, gwp_dict=GWP)
    assert res["inputs"]["whole_gas_scf"] == pytest.approx(1_332_000.0, rel=1e-9)
    assert_printed(tonnes(res, "ch4"), "20.39", gas="ch4", rel=0.0002, what="CH4")
    assert_printed(tonnes(res, "co2"), "2.10", rel=0.0002, what="CO2")


def test_exhibit_6_9_primary_heavy_oil_casing_gas():
    """PDF line 12252. 100 bbl/day primary heavy oil, 365 days, whole-gas factor 210 scf/bbl (Table 6-12), 70 % CH4,
    9 % CO2: CH4 102.7, CO2 36.3 tonnes/yr."""
    from calculations.vented_production_wells import CasingGasVentCalculator
    res = CasingGasVentCalculator().calculate(method="throughput", oil_type="primary_heavy_oil", throughput_rate=100,
                                              operating_days=365, ch4_content=70, co2_content=9, gwp_dict=GWP)
    assert_printed(tonnes(res, "ch4"), "102.7", gas="ch4", rel=0.0002, what="CH4")
    assert_printed(tonnes(res, "co2"), "36.3", rel=0.0002, what="CO2")


def test_exhibit_6_10_low_pressure_gas_well_casing_migration():
    """PDF line 12319. 3 low-pressure wells x 0.00213 t CH4/well-day x 365 d, adjusted from 81.6 to 70 mol % CH4,
    9 % CO2: CH4 2.00, CO2 0.71 tonnes/yr."""
    from calculations.vented_production_wells import CasingGasVentCalculator
    res = CasingGasVentCalculator().calculate(method="migration", well_count=3, operating_days=365, ch4_content=70,
                                              co2_content=9, gwp_dict=GWP)
    assert_printed(tonnes(res, "ch4"), "2.00", rel=0.0002, what="CH4")
    assert_printed(tonnes(res, "co2"), "0.71", gas="co2", rel=0.0002, what="CO2")


# ---------------------------------------------------------------- 6.3.6 - 6.3.8 pneumatics, dehydration, AGR ----------

def test_exhibit_6_11_continuous_low_bleed_controllers():
    """PDF line 12484. 80 low-bleed controllers, 8,760 h, 70 % CH4, 9 % CO2 (Table 6-14: 2.1 scf CH4/h at 81.6 %):
    CH4 24.2 tonnes/yr."""
    from calculations.vented_production_pneumatic import PneumaticDeviceCalculator
    res = PneumaticDeviceCalculator().calculate(count=80, hours=8760, controller_type="low_bleed",
                                                source_standard="api", ch4_content=0.70, co2_content=0.09)
    assert_printed(tonnes(res, "ch4"), "24.2", rel=0.0002, what="CH4")


def test_exhibit_6_11_co2_uses_the_whole_gas_factor():
    """PDF line 12484. The exhibit's text says CO2 uses the whole-gas factor (2.6 scf gas/h, Table 6-14) times the CO2
    mole fraction: 80 x 2.6 x 8,760 x 9 % -> 8.6 t. Its arithmetic multiplies 2.1 (the scf CH4/h figure) instead and
    prints 7.0, so the engine follows the text, not the printed number."""
    from calculations.vented_production_pneumatic import PneumaticDeviceCalculator
    res = PneumaticDeviceCalculator().calculate(count=80, hours=8760, controller_type="low_bleed",
                                                source_standard="api", ch4_content=0.70, co2_content=0.09)
    assert tonnes(res, "co2") == pytest.approx(80 * 2.6 * 8760 * 0.09 / 379.3 * 44.01 / 2204.62, rel=2e-3)


def test_exhibit_6_12_intermittent_controllers_monitoring_survey():
    """PDF line 12700. 76 normal all year + 4 normal 0.75 / malfunctioning 0.25 of the year, 70 % CH4, 9 % CO2:
    CH4 5.41, CO2 1.91 tonnes/yr."""
    from calculations.vented_production_pneumatic import PneumaticDeviceCalculator
    # the survey table: 76 controllers normal all year, 4 normal 0.75 / malfunctioning 0.25 of the year. The engine takes
    # one fraction per category, so the normal category is 76 + 4 x 0.75 = 79 controller-years.
    res = PneumaticDeviceCalculator().calculate(monitoring_program=True, normal_count=79, normal_fraction_year=1.0,
                                                malfunctioning_count=4, malfunctioning_fraction_year=0.25,
                                                hours=8760, ch4_content=0.70, co2_content=0.09)
    # the exhibit multiplies the Table 6-15 t/controller-yr factors 0.038 and 3.30 (2-3 figures); the engine derives
    # the same rates from the whole-gas 0.28 and 24.1 scf/h: 0.46 % apart (0.25 % of it the CH4 molecular weight)
    assert_printed(tonnes(res, "ch4"), "5.41", rel=6e-3, what="CH4")
    assert_printed(tonnes(res, "co2"), "1.91", rel=6e-3, what="CO2")


def _dehydrator(**kw):
    from calculations.vented_production_pneumatic import GasDehydrationCalculator
    return GasDehydrationCalculator().calculate(**kw)


def test_exhibit_6_13_glycol_dehydrator_electric_pump():
    """PDF line 13093. 25 MMscf/d, 82 % CH4, electric pump, no flash tank (0.0052859 t CH4/MMscf at 78.8 %):
    CH4 50.2 tonnes/yr, CO2 negligible (not appreciably soluble in glycol)."""
    res = _dehydrator(dehydrator_type="glycol", gas_throughput_mmscfd=25.0, operating_days=365.0,
                      has_gas_assisted_pump=False, ch4_content=0.82, co2_content=0.05)
    assert_printed(tonnes(res, "ch4"), "50.2", rel=0.0002, what="CH4")
    assert tonnes(res, "co2") == 0.0


def test_exhibit_6_14_kimray_pump_vent():
    """PDF line 13207. The same unit with a gas-operated (Kimray) pump: the pump adds 180.7 t CH4 and 30.3 t CO2 per
    year (0.01903 t CH4/MMscf at 78.8 %). The engine reports the dehydrator and the pump together, so the pump is the
    difference with and without it."""
    common = dict(dehydrator_type="glycol", gas_throughput_mmscfd=25.0, operating_days=365.0, ch4_content=0.82,
                  co2_content=0.05)
    without = _dehydrator(has_gas_assisted_pump=False, **common)
    with_pump = _dehydrator(has_gas_assisted_pump=True, **common)
    assert_printed(tonnes(with_pump, "ch4") - tonnes(without, "ch4"), "180.7", rel=0.0002, what="pump CH4")
    assert_printed(tonnes(with_pump, "co2"), "30.3", rel=REL_MW, what="pump CO2")


def test_exhibit_6_15_desiccant_dehydrator():
    """PDF line 13280. 6.40 ft x 1.60 ft vessel, 450 psig, 45 % packed, 52 refills (9,519 scf/yr), 90 % CH4, 5 % CO2:
    CH4 0.16, CO2 0.025 tonnes/yr."""
    res = _dehydrator(dehydrator_type="desiccant", vessel_height_ft=6.40, vessel_diameter_ft=1.60,
                      vessel_pressure_psig=450.0, gas_void_fraction=0.45, changeouts_per_year=52,
                      ch4_content=0.90, co2_content=0.05)
    assert_printed(tonnes(res, "ch4"), "0.16", gas="ch4", rel=0.0002, what="CH4")
    assert_printed(tonnes(res, "co2"), "0.025", rel=0.0002, what="CO2")


def test_exhibit_6_16_amine_unit_ch4_per_unit():
    """PDF line 13456. One AGR unit, 365 days x 0.6482 t CH4/day: 236.6 tonnes CH4/yr."""
    from calculations.vented_production_tank import AcidGasRemovalCalculator
    res = AcidGasRemovalCalculator().calculate(method="unit_count", unit_count=1, operating_days=365.0)
    assert_printed(tonnes(res, "ch4"), "236.6", rel=0.0002, what="CH4")


def test_exhibit_6_17_amine_unit_material_balance():
    """PDF line 13534. 150,000e6 scf in at 3.0 % CO2, 148,500e6 scf out at 2.0 %: CO2 80,506 tonnes/yr;
    CH4 150,000e6 scf x 0.0185 t/MMscf = 2,775 tonnes/yr."""
    from calculations.vented_production_tank import AcidGasRemovalCalculator
    res = AcidGasRemovalCalculator().calculate(sour_gas_mmscf_yr=150000.0, sweet_gas_mmscf_yr=148500.0,
                                               sour_co2_content=0.030, sweet_co2_content=0.020)
    assert_printed(tonnes(res, "co2"), "80,506", rel=0.0006, what="CO2")
    assert_printed(tonnes(res, "ch4"), "2,775", rel=0.0002, what="CH4")


# ---------------------------------------------------------------- 6.3.9 storage tank flashing ---------------------------

def _tank(**kw):
    from calculations.vented_production_tank import TankFlashingCalculator
    return TankFlashingCalculator().calculate(throughput=451.0 * 365.0, liquid_type="crude", ch4_content=0.274, **kw)


def test_exhibit_6_18a_flashing_vasquez_beggs():
    """PDF line 13846. 451 bbl/day, 48.8 API, separator 28.6 psig and 112 F, default 27.4 % CH4 in the vent gas
    (VBE: flash GOR 9.33 scf/bbl): CH4 8.04 tonnes/yr."""
    res = _tank(method="vbe", api_gravity=48.8, separator_pressure_psig=28.6, separator_temp_f=112.0)
    # the exhibit rounds SGx to 0.78 and Rs to 9.33 and 1.66 before multiplying
    assert_printed(tonnes(res, "ch4"), "8.04", rel=1e-2, what="CH4")


def test_exhibit_6_18b_flashing_standing():
    """PDF line 13994. Same facility, tank at 80 F: GOR 1.329 m3/m3, CH4 6.44 tonnes/yr."""
    res = _tank(method="standing", api_gravity=48.8, separator_pressure_psig=28.6, separator_temp_f=112.0,
                tank_temp_f=80.0)
    assert_printed(tonnes(res, "ch4"), "6.44", rel=REL_MW + 2e-3, what="CH4")


def test_exhibit_6_18c_flashing_eub_rule_of_thumb():
    """PDF line 14101. Vs = 0.0257 x 71.7 m3/day x 197.2 kPa = 363.4 m3/day, 27.4 % CH4, 4.5 % CO2:
    CH4 24.56, CO2 11.09 tonnes/yr."""
    res = _tank(method="eub", separator_pressure_psig=28.6, co2_content=0.045)
    assert_printed(tonnes(res, "ch4"), "24.56", gas="ch4", rel=0.0002 + 2e-3, what="CH4")
    assert_printed(tonnes(res, "co2"), "11.09", rel=0.0002 + 2e-3, what="CO2")


def test_exhibit_6_19_flashing_chart_approach(app):
    """PDF line 14170. Flash vapor-to-oil ratio read from the chart 47 scf/bbl, 451 bbl/day, 27.4 % CH4:
    CH4 40.6 tonnes/yr."""
    p = {"process_type": "tank_flashing", "factor_source": "specific", "amount": 451 * 365, "quantity": 451 * 365,
         "unit": "bbl", "calc_inputs": {"tank_flashing": {"amount": 451 * 365, "unit": "bbl", "tank_gor": 47,
                                                          "tank_ch4_content": 27.4}}}
    assert_printed(run_scope1(app, p)["ch4"], "40.6", gas="ch4", rel=0.0002, what="CH4")


def test_exhibit_6_20_flashing_large_tank_emission_factor(app):
    """PDF line 14309. 451 bbl/day x 365 x 0.193 kg CH4/bbl (Table 6-22, large uncontrolled; not adjusted for the
    separator gas CH4): CH4 31.8 tonnes/yr."""
    p = {"process_type": "tank_flashing", "factor_source": "default", "amount": 451 * 365, "quantity": 451 * 365,
         "unit": "bbl", "calc_inputs": {"tank_flashing": {"amount": 451 * 365, "unit": "bbl"}}}
    assert_printed(run_scope1(app, p)["ch4"], "31.8", rel=0.0002, what="CH4")


def test_exhibit_6_21_produced_water_tank():
    """PDF line 14749. 50 bbl/day produced water, salt unknown, 200 psig (250 psi row of Table 6-26, 0.0142 t/1000 bbl):
    CH4 0.26 tonnes/yr."""
    from calculations.vented_production_tank import TankFlashingCalculator
    res = TankFlashingCalculator().calculate(throughput=50.0 * 365.0, method="produced_water",
                                             liquid_type="produced_water", separator_pressure_psi=200.0,
                                             salt_content="average")
    assert_printed(tonnes(res, "ch4"), "0.26", rel=0.0002, what="CH4")


# ---------------------------------------------------------------- 6.10 crude transport, 6.11 refining --------------------

def test_exhibit_6_36_marine_ballasting_unknown_ullage():
    """PDF line 18046. 1e6 bbl/yr ballast water, typical operation (1.1 lb TOC/1000 gal), 15 wt % CH4 in the vapour:
    CH4 3.14 tonnes/yr."""
    from calculations.vented_ccus_transport import CrudeTransportLossesCalculator
    res = CrudeTransportLossesCalculator().calculate(activity="ballasting", ballast_water_bbl=1_000_000,
                                                     ballast_condition="typical", ch4_weight_pct=15, gwp_dict=GWP)
    # Table 6-48 prints the typical factor as 1.1 lb/1000 gal AND as 0.488 t/1e6 gal (129 mg/L); they differ by 2.2 %
    # ("round-off errors may result"). The exhibit multiplies the lb figure (3.143 t); the engine holds the tonne figure
    # (3.074 t). Both are the document's own numbers.
    assert_printed(tonnes(res, "ch4"), "3.14", rel=2.5e-2, what="CH4")
    assert tonnes(res, "ch4") == pytest.approx(1e6 * 42 / 1e6 * 0.488 * 0.15, rel=1e-3)


def test_exhibit_6_37_marine_transit_losses():
    """PDF line 18115. 500,000 bbl per trip, 10-day trips, 25 trips/yr, 0.57 t TOC/(week x 1e6 gal), 15 wt % CH4:
    CH4 64.1 tonnes/yr."""
    from calculations.vented_ccus_transport import CrudeTransportLossesCalculator
    res = CrudeTransportLossesCalculator().calculate(activity="transit", volume_transported_bbl=500_000,
                                                     trip_duration_days=10, trips_per_year=25, ch4_weight_pct=15,
                                                     gwp_dict=GWP)
    assert_printed(tonnes(res, "ch4"), "64.1", rel=0.0002, what="CH4")


def _fccu(**kw):
    from calculations.vented_downstream import RefiningCatalystRegenCalculator
    return RefiningCatalystRegenCalculator().calculate(supplemental_fuel_mmbtu_hr=100.0, gwp_dict=GWP, **kw)


def test_exhibit_6_38_fccu_coke_burn_and_co_boiler():
    """PDF line 18386. Coke burn 119,750 t/yr at 0.93 carbon (Eq 6-34) plus 100 MMBtu/h of supplemental gas (8,760 h):
    CO2 408,348 (regenerator) and 46,516 (boiler), CH4 12.04 + 0.88, N2O 2.40 + 0.86 tonnes/yr."""
    res = _fccu(approach="coke_burn", coke_burn_rate_tonnes_yr=119750.0, carbon_content_fraction=0.93)
    inputs = res["inputs"]
    assert_printed(inputs["coke_burn_co2"], "408,348", rel=0.0002, what="coke burn CO2")
    assert_printed(inputs["supplemental_co2"], "46,516", rel=0.0002, what="boiler CO2")
    # Eq 6-38 scales the CO2 by EF_CH4/EF_CO2 of petroleum coke: the engine's ratio is 0.34 % below the exhibit's
    assert_printed(inputs["coke_burn_ch4"], "12.04", rel=4e-3, what="coke burn CH4")
    assert_printed(inputs["coke_burn_n2o"], "2.40", rel=0.0002, what="coke burn N2O")
    # the summary table prints a total of 454,149, but its own parts add up to 408,348 + 46,516 = 454,864 (exhibit
    # arithmetic slip); the sum of the printed parts is what is checked
    assert tonnes(res, "co2") == pytest.approx(408_348 + 46_516, rel=1e-4)


def test_exhibit_6_38_fccu_flue_gas_k_factor_approach():
    """PDF line 18386, step 2 and summary. Blower air 2,150 dscm/min, 11 % CO2 + 9 % CO, 8,760 h (0.2982 kg-min/hr-dscm-%
    constant): coke-burn CO2 411,862 tonnes/yr; summary CH4 12.14. The summary prints N2O 2.45, but the same CO2-ratio the exhibit
    uses for the other two approaches (2.40 / 408,348 and 2.47 / 419,859) gives 2.42 for 411,862, which is what the
    engine returns; 2.45 is an exhibit slip and is not asserted."""
    res = _fccu(approach="k1_k2_k3", flue_gas_rate_dscm_min=2150.0, co2_pct=11.0, co_pct=9.0, operating_hours=8760.0)
    assert_printed(res["inputs"]["coke_burn_co2"], "411,862", rel=0.0002, what="coke burn CO2")
    assert_printed(res["inputs"]["coke_burn_ch4"], "12.14", rel=4e-3, what="coke burn CH4")
    assert_printed(res["inputs"]["coke_burn_n2o"], "2.42", rel=0.0002, what="coke burn N2O (ratio of the other two rows)")


def test_exhibit_6_38_fccu_air_blower_rate_approach():
    """PDF line 18386, step 3 and summary. Air 2,150 m3/min x (11 % CO2 + 9 % CO) x 44/23.685, 525,600 min:
    coke-burn CO2 419,859 tonnes/yr; summary CH4 12.38, N2O 2.47."""
    res = _fccu(approach="air_blower", air_rate_m3_min=2150.0, co2_pct=11.0, co_pct=9.0, operating_hours=8760.0)
    assert_printed(res["inputs"]["coke_burn_co2"], "419,859", rel=0.0002, what="coke burn CO2")
    assert_printed(res["inputs"]["coke_burn_ch4"], "12.38", rel=4e-3, what="coke burn CH4")
    assert_printed(res["inputs"]["coke_burn_n2o"], "2.47", rel=0.0002, what="coke burn N2O")
