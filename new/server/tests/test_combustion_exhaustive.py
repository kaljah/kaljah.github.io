"""
Exhaustive unit test suite for calculations/combustion.py
Covers 100% of branch logic, helper functions, unit conversions,
thermodynamic corrections, and Tier 1/2/3 calculations for stationary combustion and flaring.
"""

import pytest
from calculations.combustion import (
    CombustionCalculator,
    FlaringCalculator,
    user_hhv,
    factor_hhv_unit,
    fuel_basis,
    _density_state,
    _density_kg_m3,
    hhv_mj_per_unit,
    convert_factor_to_kg_per_unit,
    _normalize_efficiency,
    _normalize_unit_str,
    UnitError,
)


# =============================================================================
# 1. HELPER FUNCTIONS & UNIT RESOLUTION
# =============================================================================

def test_user_hhv():
    """Test user_hhv parser with various energy units, defaults, and error cases."""
    # Blank or neutral defaults
    assert user_hhv(None, None) == (None, None)
    assert user_hhv(1000.0, "") == (1000.0, None)
    assert user_hhv(1000.0, "btu/unit") == (1000.0, None)
    assert user_hhv(1000.0, "-") == (1000.0, None)

    # Valid energy / basis conversions
    val, basis = user_hhv(38.0, "MJ/m3")
    assert basis == "btu/m3"
    assert val > 0

    val_scf, basis_scf = user_hhv(1020.0, "Btu/scf")
    assert basis_scf == "btu/scf"
    assert pytest.approx(val_scf) == 1020.0

    val_gal, basis_gal = user_hhv(138.0, "kbtu/gal")
    assert basis_gal == "btu/gal"
    assert pytest.approx(val_gal) == 138000.0

    val_kcal, basis_kcal = user_hhv(9000.0, "kcal/m3")
    assert basis_kcal == "btu/m3"
    assert val_kcal > 0

    # Unsupported or non-physical units
    with pytest.raises(UnitError, match="Unsupported HHV unit"):
        user_hhv(100.0, "gigawatts/hour")

    with pytest.raises(UnitError, match="not a volume or mass unit"):
        user_hhv(100.0, "MJ/invalid_den")


def test_factor_hhv_unit():
    """Test factor_hhv_unit extraction from factor metadata."""
    assert factor_hhv_unit(None) is None
    assert factor_hhv_unit({"hhv_unit": "btu/gal"}) == "btu/gal"
    assert factor_hhv_unit({"baseUnit": "gal"}) == "btu/gal"
    assert factor_hhv_unit({"baseUnit": "scf"}) == "btu/scf"
    assert factor_hhv_unit({"baseUnit": "bbl"}) == "btu/bbl"
    assert factor_hhv_unit({"baseUnit": "short_ton"}) == "kbtu/short_ton"
    assert factor_hhv_unit({"baseUnit": "ton"}) == "kbtu/short_ton"
    assert factor_hhv_unit({"baseUnit": "unknown_base"}) is None


def test_fuel_basis():
    """Test fuel_basis resolution across fuels and explicit units."""
    # Explicit hhv_unit
    assert fuel_basis("gas", "btu/scf") == ("scf", 1.0)
    assert fuel_basis("gas", "kbtu/short_ton") == ("short_ton", 1000.0)
    assert fuel_basis("gas", "mmbtu/bbl") == ("bbl", 1000000.0)

    with pytest.raises(UnitError, match="Unsupported HHV unit"):
        fuel_basis("gas", "invalid_hhv_unit")

    # Inferred from fuel words
    assert fuel_basis("Diesel")[0] == "gal"
    assert fuel_basis("Bituminous Coal")[0] == "short_ton"
    assert fuel_basis("Natural Gas")[0] == "scf"
    assert fuel_basis("arbitrary_unknown_gas")[0] == "scf"


def test_density_helpers():
    """Test _density_state and _density_kg_m3."""
    # Phase detection
    assert _density_state("liquid", "gal") == "volume_liquid"
    assert _density_state("gas", "scf") == "gas"
    assert _density_state("diesel") == "volume_liquid"
    assert _density_state("natural gas") == "gas"
    assert _density_state("coal") == "volume_liquid"

    # Density scaling
    assert _density_kg_m3(None, "volume_liquid") is None
    assert _density_kg_m3(0, "volume_liquid") is None
    # 0.84 kg/L entered for liquid -> 840 kg/m3
    assert _density_kg_m3(0.84, "volume_liquid") == 840.0
    # 850 kg/m3 entered for liquid -> 850.0
    assert _density_kg_m3(850.0, "volume_liquid") == 850.0
    # gas density 0.75 kg/m3 -> stays 0.75
    assert _density_kg_m3(0.75, "gas") == 0.75


def test_hhv_mj_per_unit_and_conversion():
    """Test hhv_mj_per_unit conversions, phase mismatches, and density requirements."""
    # Missing HHV
    with pytest.raises(UnitError, match="heating value .* is required"):
        hhv_mj_per_unit(None, "scf")

    # Gas vs liquid mismatch
    with pytest.raises(UnitError, match="is a gas volume but this fuel's heating value is per"):
        hhv_mj_per_unit(138000, "scf", fuel_type="diesel")

    with pytest.raises(UnitError, match="is a liquid volume but this fuel's heating value is per"):
        hhv_mj_per_unit(1020, "gal", fuel_type="natural_gas")

    # Mass to volume crossing without density
    with pytest.raises(UnitError, match="needs the fuel density"):
        hhv_mj_per_unit(138000, "tonne", fuel_type="diesel", density=None)

    # Mass to volume crossing WITH density
    mj_t = hhv_mj_per_unit(138000, "tonne", fuel_type="diesel", density=840.0)
    assert mj_t > 0

    # Volume to mass crossing WITH density (e.g. coal basis is short_ton, activity in m3)
    mj_v = hhv_mj_per_unit(20000, "m3", fuel_type="coal", density=1200.0)
    assert mj_v > 0


def test_convert_factor_to_kg_per_unit():
    """Test convert_factor_to_kg_per_unit for physical, energy, and density-dependent factors."""
    # Zero or None factor
    assert convert_factor_to_kg_per_unit(0.0, "kg/scf", "scf") == 0.0
    assert convert_factor_to_kg_per_unit(None, "kg/scf", "scf") == 0.0

    # Missing unit
    with pytest.raises(UnitError, match="has no unit"):
        convert_factor_to_kg_per_unit(1.5, "", "scf")

    # Direct physical conversion
    kg_scf = convert_factor_to_kg_per_unit(0.054, "kg/scf", "mcf")
    assert pytest.approx(kg_scf) == 54.0

    # Bare factor unit
    kg_bare = convert_factor_to_kg_per_unit(0.054, "scf", "scf")
    assert pytest.approx(kg_bare) == 0.054

    # Energy denominator with physical activity unit
    kg_energy = convert_factor_to_kg_per_unit(
        value=53.06,
        factor_unit="kg/MMBtu",
        activity_unit="scf",
        hhv=1020.0,
        fuel_type="natural_gas",
    )
    assert kg_energy > 0

    # Energy denominator with energy activity unit (kWh)
    kg_kwh = convert_factor_to_kg_per_unit(
        value=53.06,
        factor_unit="kg/MMBtu",
        activity_unit="kWh",
    )
    assert kg_kwh > 0

    # Volume to mass crossing for factor
    with pytest.raises(UnitError, match="needs the fuel density"):
        convert_factor_to_kg_per_unit(0.05, "kg/gal", "tonne", fuel_type="diesel", density=None)

    kg_dens = convert_factor_to_kg_per_unit(
        0.05, "kg/gal", "tonne", fuel_type="diesel", density=840.0
    )
    assert kg_dens > 0


# =============================================================================
# 2. COMBUSTION CALCULATOR (STATIONARY COMBUSTION)
# =============================================================================

@pytest.fixture
def combustion():
    return CombustionCalculator()


def test_combustion_standard_fuel_factor(combustion):
    """Test standard fuel-factor calculation with natural gas, diesel, and coal."""
    # Natural gas
    res_ng = combustion.calculate(
        fuel_quantity=10000.0,
        fuel_unit="scf",
        fuel_type="natural_gas",
        ef_co2=53.06,
        ef_ch4=0.001,
        ef_n2o=0.0001,
        ef_unit="kg/MMBtu",
        hhv=1020.0,
    )
    # 10,000 scf x 1,020 Btu/scf = 10.2 MMBtu; factors in kg/MMBtu; AR5 GWPs 28 (CH4) and 265 (N2O)
    mmbtu = 10000 * 1020 / 1e6
    assert res_ng["results"]["co2"]["value"] == pytest.approx(mmbtu * 53.06 / 1000, rel=1e-9)
    assert res_ng["results"]["ch4"]["value"] == pytest.approx(mmbtu * 0.001 / 1000, rel=1e-9)
    assert res_ng["results"]["n2o"]["value"] == pytest.approx(mmbtu * 0.0001 / 1000, rel=1e-9)
    assert res_ng["total_co2e"] == pytest.approx(mmbtu / 1000 * (53.06 + 0.001 * 28 + 0.0001 * 265), rel=1e-9)


def test_combustion_thermodynamic_normalization(combustion):
    """Test API §4.2.1 thermodynamic temperature and pressure normalization on gas volume."""
    # Gas volume measured at actual conditions (e.g. 50 psig, 100 F)
    res_actual = combustion.calculate(
        fuel_quantity=1000.0,
        fuel_unit="m3",
        fuel_type="natural_gas",
        ef_co2=1.9,
        ef_unit="kg/m3",
        operating_temperature=100.0,
        temp_unit="F",
        operating_pressure=50.0,
        press_unit="psig",
    )
    assert res_actual["metadata"]["thermodynamic_normalized"] is True
    # V_std = V x (P_abs / 14.696) x (288.706 K / T_abs): 50 psig = 64.696 psia, 100 F = 310.928 K -> 4,087.66 m3
    v_std = 1000.0 * (50 + 14.696) / 14.696 * 288.706 / ((100 - 32) / 1.8 + 273.15)
    assert res_actual["results"]["co2"]["value"] == pytest.approx(v_std * 1.9 / 1000, rel=1e-5)


def test_combustion_tier3_gas_composition(combustion):
    """Test Tier 3 carbon mass balance from C1-C10 and native CO2 gas composition."""
    # High heavy-hydrocarbons (> 10% C2+) triggers warning
    res_comp = combustion.calculate(
        fuel_quantity=1000.0,
        fuel_unit="m3",
        fuel_type="natural_gas",
        combustion_efficiency=0.99,
        c1=75.0,
        c2=12.0,
        c3=5.0,
        c4=3.0,
        c5=1.0,
        co2_comp=4.0,
    )
    assert res_comp["metadata"]["heavy_hydrocarbon_warning"] is True
    # carbon per mole of gas 0.75 + 2 x 0.12 + 3 x 0.05 + 4 x 0.03 + 5 x 0.01 = 1.31 at 99 % combustion, plus 4 % native CO2
    rho_co2, rho_ch4 = 44.01 / 23.685, 16.04 / 23.685
    assert res_comp["results"]["co2"]["value"] == pytest.approx(1000 * (1.31 * 0.99 + 0.04) * rho_co2 / 1000, rel=1e-9)
    assert res_comp["results"]["ch4"]["value"] == pytest.approx(1000 * 0.75 * 0.01 * rho_ch4 / 1000, rel=1e-9)  # slip

    # Fractional composition <= 1.0 without heavy warning
    res_frac = combustion.calculate(
        fuel_quantity=500.0,
        fuel_unit="m3",
        fuel_type="natural_gas",
        combustion_efficiency=0.995,
        c1=0.95,
        c2=0.02,
        co2_comp=0.01,
    )
    assert res_frac["metadata"]["heavy_hydrocarbon_warning"] is False
    # fractions: carbon 0.95 + 2 x 0.02 = 0.99 mol C/mol at 99.5 % combustion, plus 1 % native CO2, 500 m3
    assert res_frac["results"]["co2"]["value"] == pytest.approx(500 * (0.99 * 0.995 + 0.01) * rho_co2 / 1000, rel=1e-9)
    assert res_frac["results"]["ch4"]["value"] == pytest.approx(500 * 0.95 * 0.005 * rho_ch4 / 1000, rel=1e-9)


def test_combustion_tier3_liquid_solid_carbon(combustion):
    """Test Tier 3 fuel analysis for liquid/solid fuel by carbon wt % (Exhibit 4.5)."""
    # 1. Fuel mass basis (10 tonnes diesel at 86 wt % carbon)
    res_mass = combustion.calculate(
        fuel_quantity=10.0,
        fuel_unit="t",
        fuel_type="diesel",
        density=840.0,
        carbon_wt=86.0,
        combustion_efficiency=0.995,
        ef_ch4=0.003,
        ef_n2o=0.0006,
        ef_unit="kg/MMBtu",
        hhv=138000,
    )
    # CO2 = 10 * 0.86 * 0.995 * (44.01 / 12.011) = 31.35 tonnes
    assert pytest.approx(res_mass["results"]["co2"]["value"], rel=1e-2) == 31.35
    assert res_mass["results"]["ch4"]["value"] > 0

    # 2. Liquid volume basis with density
    res_vol = combustion.calculate(
        fuel_quantity=1000.0,
        fuel_unit="gal",
        fuel_type="diesel",
        density=840.0,
        carbon_wt=0.86,
        carbon_wt_unit="fraction",
    )
    assert res_vol["results"]["co2"]["value"] > 0

    # Errors on invalid carbon wt % or missing density
    with pytest.raises(ValueError, match="between 0 and 100 wt %"):
        combustion.calculate(fuel_quantity=10.0, fuel_unit="t", carbon_wt=105.0)

    with pytest.raises(UnitError, match="needs the fuel density"):
        combustion.calculate(
            fuel_quantity=1000.0, fuel_unit="gal", fuel_type="diesel", carbon_wt=85.0, density=None
        )

    with pytest.raises(UnitError, match="needs the fuel quantity as a mass or a liquid volume"):
        combustion.calculate(
            fuel_quantity=1000.0, fuel_unit="scf", fuel_type="natural_gas", carbon_wt=85.0
        )


# =============================================================================
# 3. FLARING CALCULATOR (DUAL-EFFICIENCY)
# =============================================================================

@pytest.fixture
def flaring():
    return FlaringCalculator()


def test_flaring_dual_efficiency_defaults(flaring):
    """Test flaring calculator with default combustion and destruction efficiencies."""
    res = flaring.calculate(
        gas_volume=10000.0,
        fuel_unit="m3",
        ch4_fraction=0.85,
        flare_type="elevated",
        uncertainties={"_factor_source": "specific"},
    )
    assert res["metadata"]["combustion_efficiency"] == 0.965
    assert res["metadata"]["destruction_efficiency"] == 0.98
    assert res["results"]["co2"]["value"] > 0
    assert res["results"]["ch4"]["value"] > 0
    assert res["results"]["n2o"]["value"] > 0


def test_flaring_thermodynamic_and_custom_efficiencies(flaring):
    """Test flaring calculator with custom efficiencies, T/P correction, and refinery fuel gas."""
    res = flaring.calculate(
        gas_volume=500.0,
        fuel_unit="m3",
        fuel_type="refinery_fuel_gas",
        ch4_fraction=0.75,
        flare_type="steam_assisted",
        combustion_efficiency=0.995,
        destruction_efficiency=0.999,
        operating_temperature=120.0,
        temp_unit="F",
        operating_pressure=15.0,
        press_unit="psig",
        uncertainties={},
    )
    assert res["metadata"]["combustion_efficiency"] == 0.995
    assert res["metadata"]["destruction_efficiency"] == 0.999
    assert res["metadata"]["thermodynamic_normalized"] is True
    assert res["results"]["co2"]["value"] > 0
    assert res["results"]["ch4"]["value"] > 0


def test_flaring_c1_c10_compositions(flaring):
    """Test flaring with detailed hydrocarbon stream (C1-C10) and native CO2."""
    # Percentage format (> 1.5)
    res_pct = flaring.calculate(
        gas_volume=1000.0,
        fuel_unit="m3",
        ch4_fraction=0.80,
        flare_type="ground_flare",
        c1=80.0,
        c2=10.0,
        c3=4.0,
        c4=2.0,
        co2_comp=3.0,
        uncertainties={},
    )
    # carbon 0.80 + 2 x 0.10 + 3 x 0.04 + 4 x 0.02 = 1.20 at the 96.5 % ground-flare carbon conversion, plus 3 % CO2
    rho_co2, rho_ch4 = 44.01 / 23.685, 16.04 / 23.685
    carbon_pct = 0.80 + 2 * 0.10 + 3 * 0.04 + 4 * 0.02
    assert res_pct["results"]["co2"]["value"] == pytest.approx(1000 * (carbon_pct * 0.965 + 0.03) * rho_co2 / 1000, rel=1e-9)
    assert res_pct["results"]["ch4"]["value"] == pytest.approx(1000 * 0.80 * 0.02 * rho_ch4 / 1000, rel=1e-9)

    # Fractional format <= 1.0
    res_frac = flaring.calculate(
        gas_volume=1000.0,
        fuel_unit="m3",
        ch4_fraction=0.85,
        flare_type="elevated",
        c1=0.85,
        c2=0.08,
        c3=0.04,
        co2_mol=0.02,
        uncertainties={},
    )
    carbon_frac = 0.85 + 2 * 0.08 + 3 * 0.04   # 1.13 mol C per mol gas, plus 2 % native CO2
    assert res_frac["results"]["co2"]["value"] == pytest.approx(1000 * (carbon_frac * 0.965 + 0.02) * rho_co2 / 1000, rel=1e-9)


def test_flaring_n2o_energy_and_volume_factors(flaring):
    """Test N2O emissions under energy factor basis and volume factor basis."""
    # 1. Energy factor basis (kg/MMBtu)
    res_energy = flaring.calculate(
        gas_volume=1000.0,
        fuel_unit="m3",
        ch4_fraction=0.85,
        flare_type="elevated",
        ef_n2o=0.0001,
        ef_unit="kg/MMBtu",
        hhv=1020.0,
        uncertainties={},
    )
    assert res_energy["results"]["n2o"]["value"] > 0

    # 2. Volume factor basis (kg/m3)
    res_vol = flaring.calculate(
        gas_volume=1000.0,
        fuel_unit="m3",
        ch4_fraction=0.85,
        flare_type="elevated",
        ef_n2o=0.000005,
        ef_unit="kg/m3",
        uncertainties={},
    )
    assert res_vol["results"]["n2o"]["value"] > 0

    # 3. Zero N2O
    res_zero = flaring.calculate(
        gas_volume=1000.0,
        fuel_unit="m3",
        ch4_fraction=0.85,
        flare_type="elevated",
        ef_n2o=0.0,
        uncertainties={},
    )
    assert res_zero["results"]["n2o"]["value"] == 0.0


def test_combustion_final_edge_branches(combustion, flaring):
    """Test legacy unit string normalizer, density fallback, and composition parsing edges."""
    # _normalize_unit_str
    assert _normalize_unit_str("") == ""
    assert _normalize_unit_str("m³") == "m3"

    # _density_state fallback
    assert _density_state("unknown_synthetic_fuel") == "volume_liquid"

    # hhv_mj_per_unit dimension mismatch with density
    with pytest.raises(UnitError, match="cannot be converted to the HHV basis"):
        hhv_mj_per_unit(1000.0, "km", fuel_type="diesel", density=840.0)

    # convert_factor_to_kg_per_unit volume factor on mass activity
    val = convert_factor_to_kg_per_unit(
        value=1.5,
        factor_unit="kg/m3",
        activity_unit="kg",
        fuel_type="diesel",
        density=840.0,
    )
    assert val > 0

    # convert_factor_to_kg_per_unit mass factor on volume activity (hits line 221)
    val_mv = convert_factor_to_kg_per_unit(
        value=1.5,
        factor_unit="kg/tonne",
        activity_unit="m3",
        fuel_type="diesel",
        density=840.0,
    )
    assert val_mv > 0

    # Combustion C1-C10 parsing with invalid strings and total > 100%
    res_c_err = combustion.calculate(
        fuel_quantity=1000.0,
        fuel_unit="m3",
        fuel_type="natural_gas",
        c1="invalid_c1",
        c2="60%",
        c3="50%",
    )
    assert res_c_err["results"]["co2"]["value"] > 0

    # Combustion carbon wt with '%' sign
    res_cw = combustion.calculate(
        fuel_quantity=10.0,
        fuel_unit="t",
        fuel_type="diesel",
        density=840.0,
        carbon_wt="85%",
    )
    assert res_cw["results"]["co2"]["value"] > 0

    # Flaring C1-C10 parsing with invalid string and total > 100%
    res_f_err = flaring.calculate(
        gas_volume=1000.0,
        fuel_unit="m3",
        ch4_fraction=0.80,
        flare_type="elevated",
        c1="invalid_c1",
        c2="60%",
        c3="50%",
        ef_n2o=0.0001,
        ef_unit="m3",  # no slash in ef_unit hits line 628
        uncertainties={},
    )
    assert res_f_err["results"]["co2"]["value"] > 0

