"""API Compendium 2021 worked examples, chapters 3 (units), 4 (combustion), 5 (flares / oxidizers) and 8 (indirect).

Each test runs the exhibit's own inputs through the software and compares with the number the exhibit prints
(see compendium_exhibits_support for how the tolerance is set). "PDF line" is the line of the exhibit in
``pdftotext -layout`` output of API-GHG-Compendium-110921.pdf.

Exhibits with no software counterpart: 3.3 / 3.4 (weight % <-> mole %), 3.5 (wet-gas heating value), 4.3 (LHV -> HHV
factor): the platform has no such calculation.
"""
import pytest

from calculations.combustion_methods import CombustionMethodCalculator
from calculations.constants import GWP_AR5
from calculations.indirect import CogenAllocationCalculator, IndirectSteamCalculator
from calculations.units import calculate_co2e, convert, normalize_gas_volume_to_standard

from compendium_exhibits_support import REL_ENGINE, assert_printed, run_scope1, tonnes


@pytest.fixture
def methods():
    return CombustionMethodCalculator()


# ---------------------------------------------------------------- chapter 3: units ----------------------------------

def test_exhibit_3_1_co2e_of_a_short_ton_inventory():
    """PDF line 4431. 8.8e6 short tons CO2 + 315,000 short tons CH4 (GWP 28) = 1.60e7 tonnes CO2e/yr."""
    co2_t = convert(8_800_000, "short_ton", "tonne")
    ch4_t = convert(315_000, "short_ton", "tonne")
    assert_printed(calculate_co2e(co2=co2_t, ch4=ch4_t, gwp_dict=GWP_AR5), "1.60e7", slack=1.0, what="CO2e")


@pytest.mark.parametrize("kwargs", [
    # 345 scfd/device at 14.696 psia, 60 F  ->  the exhibit's 350.3 at (101.3 kPa, 293 K) is the same gas
    dict(volume=350.3, operating_temp=293, temp_unit="K", operating_press=101.3, press_unit="kpa"),
    # 326.51 at 0 C and 760 mm Hg is the same 345 scfd
    dict(volume=326.51, operating_temp=0, temp_unit="C", operating_press=760, press_unit="mmhg"),
])
def test_exhibit_3_2_standard_condition_conversion(kwargs):
    """PDF line 4666 (Eq 3-5). The exhibit converts 345 scfd to other standard conditions; the engine converts a
    volume at those conditions back to its 60 F / 14.696 psia basis, so it must return 345 (exhibit rounding 0.1 %)."""
    got = normalize_gas_volume_to_standard(**kwargs)
    assert got == pytest.approx(345.0, rel=1e-3)


def test_exhibit_3_2_si_conversion():
    """PDF line 4723. 326.51 scfd -> 9.2456 m3/day (Table 3-4: 35.3147 ft3 per m3)."""
    # the exhibit divides 326.51 by 35.3147 and prints 9.2456; the quotient is 9.24573 (exhibit rounding, 1e-4)
    assert_printed(convert(326.51, "scf", "m3"), "9.2456", slack=3.0, what="m3/day")


# ---------------------------------------------------------- chapter 4: combustion --------------------------------------

def test_exhibit_4_1_engine_energy_input(methods):
    """PDF line 6462. 100 hp gas engine, 90 % load, 8,000 h at 6,186 Btu/hp-hr (HHV): 100 x 0.9 x 8000 x 6186
    = 4.454e9 Btu/yr (the exhibit's printed result is lost in the PDF text; the arithmetic is the exhibit's)."""
    res = methods.calculate("equipment", {"equipment_type": "ic_4s_lean_ng", "engine_hp": 100, "load_pct": 90,
                                          "operating_hours": 8000, "heat_rate_btu_hphr": 6186})
    assert res["intermediate"]["energy_mmbtu"] == pytest.approx(100 * 0.9 * 8000 * 6186 / 1e6, rel=1e-12)


def test_exhibit_4_2_natural_gas_energy_input_and_co2(app):
    """PDF line 6506. 800e6 scf natural gas at 1,020 Btu/scf -> 8.16e11 Btu/yr (816,000 MMBtu). The exhibit prints
    only the energy; CO2 is that energy times the Table 4-3 / 4-5 natural-gas factor 0.05306 t/MMBtu (HHV)."""
    em = run_scope1(app, {"process_type": "combustion", "factor_source": "default", "fuel": "Natural Gas",
                          "fuel_type": "Natural Gas", "amount": 800e6, "quantity": 800e6, "unit": "scf",
                          "calc_inputs": {"combustion": {"amount": 800e6, "unit": "scf", "fuel": "Natural Gas"}}})
    assert em["co2"] == pytest.approx(8.16e11 / 1e6 * 0.05306, rel=1e-6)


def test_exhibit_4_5_liquid_fuel_carbon_balance(methods):
    """PDF line 6756. 4e6 gal No. 6 residual oil, 8.3 lb/gal, 92.3 wt % carbon -> 50,966 tonnes CO2/yr."""
    res = methods.calculate("carbon_content", {"fuel_volume": 4e6, "fuel_volume_unit": "gal", "fuel_density": 8.3,
                                               "density_unit": "lb/gal", "carbon_wt_pct": 92.3, "oxidation_pct": 100})
    # the exhibit converts C to CO2 with 44/12; the engine uses 44.01/12.011 (0.07 % lower)
    assert_printed(tonnes(res, "co2"), "50,966", rel=1e-3, what="CO2")


def test_exhibit_4_6_residual_oil_default_factors(app):
    """PDF line 7505. 4e6 gal No. 6 residual oil, default factors: CO2 44,984, CH4 1.80, N2O 0.36 tonnes/yr."""
    em = run_scope1(app, {"process_type": "combustion", "factor_source": "default",
                          "fuel": "Residual Fuel Oil (No. 6)", "fuel_type": "Residual Fuel Oil (No. 6)",
                          "amount": 4e6, "quantity": 4e6, "unit": "gal",
                          "calc_inputs": {"combustion": {"amount": 4e6, "unit": "gal",
                                                         "fuel": "Residual Fuel Oil (No. 6)"}}})
    # the exhibit takes the heat content from Table 3-8 (6.29 MMBtu/bbl = 0.1498 MMBtu/gal); the catalog holds the
    # Table 4-5 / EPA Part 98 value 0.150 MMBtu/gal with 75.10 kg/MMBtu (0.17 % higher). CH4 and N2O use Table 4-5 too.
    assert_printed(em["co2"], "44,984", rel=2e-3, what="CO2")
    assert_printed(em["ch4"], "1.80", slack=1.0, what="CH4")
    assert_printed(em["n2o"], "0.36", slack=1.0, what="N2O")


def test_exhibit_4_7_boiler_ch4_n2o(methods):
    """PDF line 7599. 800e6 scf gas at 1,032 Btu/scf in a low-NOx boiler: CH4 0.83, N2O 0.23 tonnes/yr."""
    res = methods.calculate("equipment", {"equipment_type": "boiler_ng_controlled", "fuel_volume": 800e6,
                                          "fuel_volume_unit": "scf", "hhv_btu_scf": 1032})
    assert_printed(tonnes(res, "ch4"), "0.83", what="CH4")
    assert_printed(tonnes(res, "n2o"), "0.23", what="N2O")


def test_exhibit_4_8_gasoline_engine_ch4_n2o(methods):
    """PDF line 8195. 100 hp gasoline engine, 90 % load, 8,000 h (7,000 Btu/hp-hr): CH4 0.62, N2O 0.00303 tonnes/yr."""
    res = methods.calculate("equipment", {"equipment_type": "ic_gasoline", "engine_hp": 100, "load_pct": 90,
                                          "operating_hours": 8000})
    assert res["intermediate"]["energy_mmbtu"] == pytest.approx(5040.0)
    assert_printed(tonnes(res, "ch4"), "0.62", what="CH4")
    assert_printed(tonnes(res, "n2o"), "0.00303", slack=1.5, what="N2O (exhibit 6.01e-7, engine 6.0e-7 t/MMBtu)")


def test_exhibit_4_12_heavy_diesel_fleet_ch4_n2o_and_fuel(methods):
    """PDF line 8697. 1e6 miles at 8.8 mi/gal = 113,636 gal; CH4 0.048, N2O 0.064 tonnes (Table 4-16 factors).
    The exhibit's CO2 1,297 t uses 0.0822 t/MMBtu, which is not the Table 4-3 diesel figure (0.0684 HHV) the same
    document prints, so it is checked here with the exhibit's own factor and heating value."""
    res = methods.calculate("vehicle_distance", {"distance": 1e6, "distance_unit": "mile",
                                                 "vehicle_type": "hd_diesel_advanced", "fuel_economy_mpg": 8.8,
                                                 "hhv_mmbtu_gal": 5.83 / 42.0, "co2_ef_t_mmbtu": 0.0822})
    assert res["intermediate"]["fuel_gal"] == pytest.approx(113_636, abs=0.5)
    assert_printed(tonnes(res, "co2"), "1,297", slack=2.0, what="CO2 with the exhibit's 0.0822 t/MMBtu")
    assert_printed(tonnes(res, "ch4"), "0.048", what="CH4")
    # the exhibit prints 0.064 for 113,636 gal x 5.7e-4 t/1000 gal = 0.0648 (it truncates)
    assert_printed(tonnes(res, "n2o"), "0.064", slack=2.0, what="N2O")


def _marine_fleet(app):
    return run_scope1(app, {"process_type": "mobile", "factor_source": "default", "fuel": "Marine Diesel Oil",
                            "fuel_type": "Marine Diesel Oil", "amount": 275498, "quantity": 275498, "unit": "m3",
                            "calc_inputs": {"mobile": {"amount": 275498, "unit": "m3", "fuel": "Marine Diesel Oil"}}})


def test_exhibit_4_13_marine_diesel_fleet_co2(app):
    """PDF line 8801. 275,498 m3 diesel (17 tankers, 90 % at sea): CO2 742,580 tonnes/yr (exhibit uses 69.4 t/1e12 J
    x 1.07e16 J, three digits)."""
    assert_printed(_marine_fleet(app)["co2"], "742,580", rel=0.0006, what="CO2")


def test_exhibit_4_13_marine_diesel_fleet_ch4_n2o(app):
    """PDF line 8840. CH4 68.9 tonnes/yr (275,498 m3 x 2.5e-4); N2O 275,498 m3 x 7.2e-5 = 19.8 tonnes/yr (the
    exhibit's printed N2O is lost in the PDF text, its arithmetic is as stated)."""
    em = _marine_fleet(app)
    assert_printed(em["ch4"], "68.9", what="CH4")
    assert_printed(em["n2o"], "19.8", what="N2O")


# ---------------------------------------------------------- chapter 5: flares and oxidizers ---------------------------

def test_exhibit_5_1_flare_known_volume(app):
    """PDF line 9985. 20e6 scf flared, 80 % CH4 etc., 98 % combustion: CH4 6.1, CO2 1,095 tonnes/yr."""
    em = run_scope1(app, {"process_type": "flaring", "factor_source": "specific", "fuel": "Natural Gas",
                          "fuel_type": "Natural Gas", "amount": 20e6, "quantity": 20e6, "unit": "scf",
                          "calc_inputs": {"flaring": {"amount": 20e6, "unit": "scf", "fuel": "Natural Gas",
                                                      "hhv": 1020, "c1": 80, "c2": 4.2, "c3": 1.3, "c4": 0.4,
                                                      "co2_content": 12, "n2_content": 2.1,
                                                      "combustion_efficiency": 98, "destruction_efficiency": 98}}})
    assert_printed(em["ch4"], "6.1", what="CH4")
    # exhibit: 98 % of carbon to CO2 with 44/12 and 379.3 scf/lbmole; engine 44.01/12.011 and 23.685 m3/kmol
    assert_printed(em["co2"], "1,095", gas="co2", rel=0.0002, what="CO2")
    # The exhibit's own N2O (6.46e-4), CO2 (37.23) and CH4 (0.024) lines use the Table 5-5 "Flaring - gas production"
    # factors on the 3 MMscf/d PRODUCED, a different method; the platform has no production-based flare factor.


def test_exhibit_5_2_flare_back_calculated_from_voc(methods):
    """PDF line 10071. 2.21 short tons VOC emitted, weight % analysis, 98 % efficiency:
    CO2 515.7, CH4 1.03, N2O 7.76e-4 tonnes/yr."""
    res = methods.calculate("flare_voc", {
        "voc_mass": 2.21, "voc_mass_unit": "short_ton", "combustion_efficiency": 98,
        "wt_ch4": 2.73, "wt_c2h6": 0.85, "wt_c3h8": 1.35, "wt_c4h10": 0.99, "wt_c5h12": 0.83, "wt_c6plus": 2.16,
        "wt_co2": 90.43})
    # CO2: the exhibit rounds the mixture carbon to 80.08 wt % (engine 80.15: C6+ taken as hexane) and uses 44/12
    assert_printed(tonnes(res, "co2"), "515.7", rel=2e-3, what="CO2")
    assert_printed(tonnes(res, "ch4"), "1.03", slack=1.0, what="CH4")
    assert_printed(tonnes(res, "n2o"), "7.76e-4", slack=2.0, what="N2O")


def test_exhibit_5_3_thermal_oxidizer(methods):
    """PDF line 10292. 4,122,487 bbl crude loaded, 1.23 lb VOC/1000 gal, 99 % destruction:
    CO2 338.9, CH4 0.085 tonnes/yr."""
    res = methods.calculate("thermal_oxidizer", {
        "liquid_loaded": 4_122_487, "liquid_unit": "bbl", "loading_loss_lb_kgal": 1.23, "voc_fraction_of_toc": 85,
        "toc_carbon_wt_pct": 82.15, "toc_ch4_wt_pct": 7.5, "destruction_efficiency": 99})
    # 44/12 in the exhibit, 44.01/12.011 in the engine: 0.07 %
    assert_printed(tonnes(res, "co2"), "338.9", rel=1e-3, what="CO2")
    assert_printed(tonnes(res, "ch4"), "0.085", slack=1.0, what="CH4")


# ---------------------------------------------------------- chapter 8: indirect ---------------------------------------

def test_exhibit_8_3_purchased_steam():
    """PDF line 30292. 15e6 lb of 600 psig / 700 F steam (1,350 - 180 Btu/lb), 92 % boiler, 10 % loss:
    CO2 1,263, CH4 0.0235, N2O 0.0064 tonnes/yr."""
    res = IndirectSteamCalculator().calculate(
        heat_energy=15e6, heat_unit="lb", steam_enthalpy_btu_lb=1350 - 180, ef_co2=59.0, ef_ch4=1.10e-3, ef_n2o=3.0e-4,
        boiler_efficiency=0.92, transmission_loss=0.10, uncertainties={})
    assert res["inputs"]["energy_btu"] == pytest.approx(1.755e10)
    assert_printed(tonnes(res, "co2"), "1,263", slack=1.0, what="CO2")
    assert_printed(tonnes(res, "ch4"), "0.0235", slack=1.0, what="CH4")
    assert_printed(tonnes(res, "n2o"), "0.0064", slack=1.0, what="N2O")


def test_exhibit_8_1_purchased_electricity_supplier_factor():
    """PDF line 29705. 500,000 kWh from a natural gas combined-cycle plant at 0.40 t CO2/MWh: CO2 200 tonnes/yr.
    The platform has no generation-technology factor table, only grid regions and a supplier CO2e factor, so the
    exhibit's CH4 (0.0034 t) and N2O (0.0143 t) lines are not reproducible; the CO2 line is, as a 0.40 kg/kWh factor."""
    from routes.scope2 import resolve_electricity_factor
    factor, region = resolve_electricity_factor(None, 0.40)
    assert region is None
    assert_printed(500_000 * factor / 1000.0, "200", what="CO2e")


def test_exhibit_8_2_purchased_electricity_state_grid_factors():
    """PDF line 30036. 500,000 kWh in Colorado (eGRID RMPA: 0.564 t CO2, 5.31e-5 t CH4, 7.71e-6 t N2O per MWh):
    CO2 282.0, CH4 0.0266, N2O 0.0039 tonnes/yr."""
    from types import SimpleNamespace

    from services.scope2_gases import gas_split
    split = gas_split(SimpleNamespace(source_type="electricity", grid_region="US-RMPA (WECC Rockies)",
                                      electricity_kwh=500_000, co2e=0))
    assert_printed(split["co2"], "282.0", what="CO2")
    assert_printed(split["ch4"], "0.0266", what="CH4")
    assert_printed(split["n2o"], "0.0039", what="N2O")


# ---------------------------------------------------------- chapter 8: cogeneration allocation -------------------------

TOTAL_COGEN_CO2E = 435_983   # Exhibit 8.4 step 1: 431,783 t CO2 + 31.7 t CH4 x 21 + 11.4 t N2O x 310


def test_exhibit_8_4_cogeneration_wri_efficiency_method():
    """PDF line 30528. 3,614,000 MMBtu steam and 1,100,600 MWh electricity from 435,983 t CO2e of combustion, reference
    efficiencies 80 % (steam) and 33 % (electricity): steam 123,900.2, electricity 312,082.8 tonnes CO2e (step 4
    prints 312,092.8 once and 312,082.8 later; 435,983 - 123,900.2 = 312,082.8)."""
    res = CogenAllocationCalculator().calculate(
        total_emissions=TOTAL_COGEN_CO2E, heat_output=3_614_000, heat_unit="mmbtu", power_output=1_100_600,
        power_unit="mwh", method="wri_efficiency", heat_efficiency=0.80, power_efficiency=0.33)
    meta = res["metadata"]
    # the exhibit converts MWh to Btu with 2.931e-4 kWh/Btu (3,412 Btu/kWh), the engine with 3,412.14
    assert_printed(meta["allocated_heat_tonnes"], "123,900.2", rel=0.0002, what="steam")
    assert_printed(meta["allocated_power_tonnes"], "312,082.8", rel=0.0002, what="electricity")


def test_exhibit_8_6_cogeneration_energy_content_method():
    """PDF line 30892. The same facility by energy content: steam 3.614e12 Btu and electricity 3.755e12 Btu share
    the 435,983 t CO2e: electricity 222,163 tonnes CO2e and steam 213,820 (the exhibit prints 213,980 in step 5 but uses 213,820 in the next
    line; 435,983 - 222,163 = 213,820)."""
    res = CogenAllocationCalculator().calculate(
        total_emissions=TOTAL_COGEN_CO2E, heat_output=3_614_000, heat_unit="mmbtu", power_output=1_100_600,
        power_unit="mwh", method="energy_content")
    meta = res["metadata"]
    assert_printed(meta["allocated_power_tonnes"], "222,163", rel=0.0002, what="electricity")
    assert_printed(meta["allocated_heat_tonnes"], "213,820", rel=0.0002, what="steam")
