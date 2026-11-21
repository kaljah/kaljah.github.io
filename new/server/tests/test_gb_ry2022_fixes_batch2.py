"""GB HBNS / El Merk RY 2022 validation, fix batch 2 (calculation engine and catalog).

Findings and decisions: docs/validation-gb-ry2022-fix-plan.md. Expected values are worked by hand from the report's
inputs and the cited tables (API Compendium 2021, EPA 40 CFR 98 Tables C-1 / C-2), never read from the engine.
"""
import pytest

from app import app
from calculations import compute_emissions
from calculations.constants import GWP_AR4

L_PER_GAL = 3.785411784
SCF_PER_M3 = 1 / 0.028316846592
NM3_TO_SM3 = ((60.0 - 32.0) * 5.0 / 9.0 + 273.15) / 273.15
LB = 0.45359237  # kg
# HBNS fuel gas, report Table 6 (mol %), the remainder to 100 % as N2
HB_FUEL_GAS = {"c1": 68.4, "c2": 17.2, "c3": 10.1, "c4": 2.3, "c5": 0.5, "c6": 0.2, "c7": 0.1, "c8": 0.1,
               "co2_mol": 0.6, "n2_mol": 0.5, "composition_basis": "percent", "hhv": 1362.97, "hhv_unit": "Btu/scf"}


@pytest.fixture
def ctx():
    with app.app_context():
        yield


def _catalog(name):
    from emission_factors import API_FACTORS
    return dict(API_FACTORS[name])


# ---------------------------------------------------------------- GB-002
def test_gb002_diesel_engine_catalog_row_takes_table_4_11_ch4(ctx):
    """399.9 m3 of diesel in a stationary engine: 105,642 gal x 0.138 MMBtu/gal x 0.36 lb TOC/MMBtu x 9 % CH4."""
    p = {"process_type": "combustion", "factor_source": "default", "fuel": "Diesel - IC Engine", "amount": 399.9,
         "unit": "m3"}
    em, _ = compute_emissions(dict(p), _catalog("Diesel - IC Engine"), gwp_dict=GWP_AR4)
    mmbtu = 399.9 * 1000 / L_PER_GAL * 0.138
    assert float(em["ch4"]) == pytest.approx(mmbtu * 0.36 * 0.09 * LB / 1000, rel=1e-3)
    assert float(em["co2"]) == pytest.approx(mmbtu * 73.96 / 1000, rel=1e-3)


# ---------------------------------------------------------------- GB-007 / GB-008
def test_gb007_aviation_gasoline_mobile_with_litres(ctx):
    """562,880 L of aviation gasoline (Table C-1 69.25 kg/MMBtu at 0.120 MMBtu/gal; Table 4-16 aviation gasoline
    0.0083 / 0.00087 t per 1,000 gal): 1,235.7 t CO2, 1.234 t CH4, 0.129 t N2O."""
    gal = 562_880 / L_PER_GAL
    p = {"process_type": "mobile", "factor_source": "default", "fuel": "Aviation Gasoline", "amount": 562_880,
         "unit": "liters", "vehicle_type": "aviation_gasoline"}
    em, _ = compute_emissions(dict(p), _catalog("Aviation Gasoline"), gwp_dict=GWP_AR4)
    assert float(em["co2"]) == pytest.approx(gal * 0.120 * 69.25 / 1000, rel=1e-3)
    assert float(em["ch4"]) == pytest.approx(gal / 1000 * 0.0083, rel=1e-3)
    assert float(em["n2o"]) == pytest.approx(gal / 1000 * 0.00087, rel=1e-3)


@pytest.mark.parametrize("unit", ["l", "L", "liter", "liters", "litre", "litres"])
def test_gb008_litre_spellings(unit):
    from calculations import combustion_methods, mobile_factors
    assert mobile_factors.fuel_gallons(L_PER_GAL, unit) == pytest.approx(1.0)
    assert combustion_methods.LIQ_TO_GAL[unit.lower()] == pytest.approx(1 / L_PER_GAL)


# ---------------------------------------------------------------- GB-020 / D11
def test_gb020_table_4_16_applies_to_a_site_factor_with_a_vehicle_type(ctx):
    """1,000 gal under a custom CO2 factor (8.31 kg/gal): CH4 / N2O from Table 4-16 aviation gasoline,
    0.0083 / 0.00087 t per 1,000 gal (Compendium 4.6.1 at any tier)."""
    p = {"process_type": "mobile", "factor_source": "custom", "fuel": "Aviation Gasoline", "amount": 1000,
         "unit": "gal", "vehicle_type": "aviation_gasoline"}
    em, _ = compute_emissions(dict(p), {"type": "custom", "co2": 8.31, "ch4": 0, "n2o": 0, "unit": "kg/gal",
                                         "hhv": 120000}, gwp_dict=GWP_AR4)
    assert float(em["co2"]) == pytest.approx(8.31, rel=1e-3)
    assert float(em["ch4"]) == pytest.approx(0.0083, rel=1e-3)
    assert float(em["n2o"]) == pytest.approx(0.00087, rel=1e-3)


# ---------------------------------------------------------------- GB-015 / GB-018
def test_gb015_turbine_factors_agree_between_catalog_and_equipment_method():
    """Table 4-11 (AP-42 3.1-2a) 0.0086 / 0.003 lb per 10^6 Btu on both paths."""
    from calculations.combustion_methods import EQUIPMENT_FACTORS
    eq = EQUIPMENT_FACTORS["turbine_ng_uncontrolled"]
    cat = _catalog("Natural Gas - Turbine")
    assert eq["ch4"] * 1000 == pytest.approx(0.0086 * LB, rel=1e-9)
    assert eq["n2o"] * 1000 == pytest.approx(0.003 * LB, rel=1e-9)
    assert cat["ch4"] == pytest.approx(eq["ch4"] * 1000, rel=1e-3)
    assert cat["n2o"] == pytest.approx(eq["n2o"] * 1000, rel=1e-3)


def test_gb018_diesel_engine_equipment_factor_is_ap42_toc_times_9_pct():
    from calculations.combustion_methods import EQUIPMENT_FACTORS, TOC_CH4_WT
    assert EQUIPMENT_FACTORS["ic_diesel"]["ch4"] * TOC_CH4_WT * 1000 == pytest.approx(0.36 * 0.09 * LB, rel=1e-9)


# ---------------------------------------------------------------- GB-017
def test_gb017_entered_equipment_factors_next_to_a_composition(ctx):
    """1,000,000 Nm3 of HBNS fuel gas (HHV 1,362.97 Btu/scf) in a heater with Table 4-9 low-NOx factors entered:
    N2O = energy x 2.8e-4 kg/MMBtu, CH4 = energy x 1.0e-3 kg/MMBtu."""
    p = {"process_type": "combustion", "factor_source": "specific", "amount": 1_000_000, "unit": "Nm3",
         **HB_FUEL_GAS, "ch4_factor": 1.0e-3, "n2o_factor": 2.8e-4, "ch4_factor_unit": "kg/MMBtu",
         "n2o_factor_unit": "kg/MMBtu"}
    em, _ = compute_emissions(dict(p), {}, gwp_dict=GWP_AR4)
    mmbtu = 1_000_000 * NM3_TO_SM3 * SCF_PER_M3 * 1362.97 / 1e6
    assert float(em["n2o"]) == pytest.approx(mmbtu * 2.8e-4 / 1000, rel=2e-3)
    assert float(em["ch4"]) == pytest.approx(mmbtu * 1.0e-3 / 1000, rel=2e-3)


# ---------------------------------------------------------------- GB-009
def test_gb009_provenance_names_the_gwp_report_used():
    from calculations.constants import GWP_AR5, GWP_AR6
    from calculations.legacy_engine import _standard_of
    assert _standard_of(GWP_AR4) == "AR4"
    assert _standard_of(GWP_AR5) == "AR5"
    assert _standard_of(GWP_AR6) == "AR6"
    assert _standard_of({"CH4": 30.0, "N2O": 200.0}) is None


# ---------------------------------------------------------------- GB-026
@pytest.mark.parametrize("salt", ["20%", "20 %", 20, 20.0, "20"])
def test_gb026_salt_content_spellings_read_as_the_20_pct_row(salt):
    from calculations.vented_production_tank import TankFlashingCalculator as T
    assert T._produced_water_factor(50, salt) == T._produced_water_factor(50, "20%")


# ---------------------------------------------------------------- GB-006 / D12
def test_gb006_gas_processing_plant_table_7_34(ctx):
    """194,132.66 MMscf processed x 4.507e-2 t CH4/MMscf x 68.4 / 86.8 = 6,894.8 t CH4."""
    p = {"process_type": "fugitive_facility", "facility_type": "gas_processing", "factor_source": "default",
         "amount": 194_132.66, "unit": "MMscf", "ch4_content": 68.4}
    em, _ = compute_emissions(dict(p), {}, gwp_dict=GWP_AR4)
    assert float(em["ch4"]) == pytest.approx(194_132.66 * 4.507e-2 * 68.4 / 86.8, rel=1e-4)


def test_gb006_gas_processing_per_plant_covers_the_month(ctx):
    """One plant for March 2022: 22,984.25 kg CH4/plant-year x 31 / 365 days."""
    p = {"process_type": "fugitive_facility", "facility_type": "gas_processing", "factor_source": "default",
         "amount": 1, "unit": "plant", "year": 2022, "month": 3}
    em, _ = compute_emissions(dict(p), {}, gwp_dict=GWP_AR4)
    assert float(em["ch4"]) == pytest.approx(22.98425 * 31 / 365, rel=1e-4)


# ---------------------------------------------------------------- GB-038
def test_gb038_sm3_at_15c():
    from calculations.units import gas_volume_m3
    t60 = (60.0 - 32.0) * 5.0 / 9.0 + 273.15
    assert gas_volume_m3(1000, "sm3_15c") == pytest.approx(1000 * t60 / 288.15, rel=1e-12)
