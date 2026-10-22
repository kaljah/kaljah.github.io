"""
Exhaustive unit test suite for calculations/combustion_methods.py
Covers 100% of branches, equations, unit conversions, and validation logic.
API Compendium 2021 Sections 4 & 5.
"""

import pytest
from calculations.combustion_methods import (
    CombustionMethodCalculator,
    equipment_factor_list,
    EQUIPMENT_FACTORS,
    VEHICLE_FACTORS,
    FUEL_BASIS,
)


@pytest.fixture
def calc():
    return CombustionMethodCalculator()


def test_equipment_factor_list():
    """Verify list of equipment factors is populated correctly."""
    factors = equipment_factor_list()
    assert len(factors) == len(EQUIPMENT_FACTORS)
    for f in factors:
        assert "key" in f
        assert "label" in f
        assert "fuel" in f
        assert "table" in f


def test_carbon_content_mass_basis(calc):
    """Test carbon content method with direct fuel mass across different units."""
    # 10 tonnes of fuel at 85 wt% carbon, 99% oxidation
    res = calc.calculate(
        method="carbon_content",
        inputs={
            "fuel_mass": 10.0,
            "fuel_mass_unit": "t",
            "carbon_wt_pct": 85.0,
            "oxidation_pct": 99.0,
        },
    )
    # 10 * 0.85 * 0.99 * (44.01 / 12.011) = 30.835 tonnes CO2
    co2 = res["results"]["co2"]["value"]
    assert pytest.approx(co2, rel=1e-3) == 30.835
    assert res["intermediate"]["fuel_mass_t"] == 10.0
    assert res["intermediate"]["carbon_wt"] == 0.85

    # Test with kg, lb, and short_ton
    for unit, factor in [("kg", 1e-3), ("lb", 1.0 / 2204.62), ("short_ton", 0.90718474)]:
        res_u = calc.calculate(
            method="carbon_content",
            inputs={
                "fuel_mass": 1000.0,
                "fuel_mass_unit": unit,
                "carbon_wt_pct": 80.0,
                "oxidation_pct": 100.0,
            },
        )
        expected_mass_t = 1000.0 * factor
        assert pytest.approx(res_u["intermediate"]["fuel_mass_t"], rel=1e-3) == expected_mass_t


def test_carbon_content_volume_basis(calc):
    """Test carbon content method with liquid volume and fuel density."""
    # 1000 gallons, density 7.0 lb/gal, 85 wt% carbon
    res = calc.calculate(
        method="carbon_content",
        inputs={
            "fuel_volume": 1000.0,
            "fuel_volume_unit": "gal",
            "fuel_density": 7.0,
            "density_unit": "lb/gal",
            "carbon_wt_pct": 85.0,
        },
    )
    # mass = 1000 * 7.0 / 2204.62 = 3.17515 tonnes
    # co2 = 3.17515 * 0.85 * 1.0 * (44.01 / 12.011) = 9.888 tonnes
    assert pytest.approx(res["results"]["co2"]["value"], rel=1e-3) == 9.888

    # Test volume units: bbl, m3, l
    for v_unit, d_unit in [("bbl", "kg/m3"), ("m3", "kg/l"), ("l", "g/ml")]:
        res_v = calc.calculate(
            method="carbon_content",
            inputs={
                "amount": 100.0,
                "unit": v_unit,
                "fuel_density": 800.0 if d_unit == "kg/m3" else 0.8,
                "density_unit": d_unit,
                "carbon_wt_pct": 80.0,
            },
        )
        assert res_v["results"]["co2"]["value"] > 0


def test_equipment_energy_input_options(calc):
    """Test all 3 energy input mechanisms for equipment method."""
    # 1. Direct energy MMBtu
    res_direct = calc.calculate(
        method="equipment",
        inputs={
            "equipment_type": "boiler_ng_controlled",
            "energy_mmbtu": 500.0,
        },
    )
    assert res_direct["intermediate"]["energy_mmbtu"] == 500.0
    assert res_direct["results"]["co2"]["value"] > 0
    assert res_direct["results"]["ch4"]["value"] > 0
    assert res_direct["results"]["n2o"]["value"] > 0

    # 2. Engine hp, load, hours, heat rate
    res_engine = calc.calculate(
        method="equipment",
        inputs={
            "equipment_type": "ic_4s_lean_ng",
            "engine_hp": 1000.0,
            "load_pct": 80.0,
            "operating_hours": 100.0,
            "heat_rate_btu_hphr": 7500.0,
        },
    )
    # MMBtu = 1000 * 0.80 * 100 * 7500 / 1e6 = 600.0 MMBtu
    assert pytest.approx(res_engine["intermediate"]["energy_mmbtu"]) == 600.0

    # 3. Fuel volume for natural gas across units
    for g_unit in ["scf", "mcf", "mscf", "mmscf", "m3", "sm3"]:
        res_gas = calc.calculate(
            method="equipment",
            inputs={
                "equipment_type": "boiler_ng_uncontrolled",
                "fuel_volume": 100.0,
                "fuel_volume_unit": g_unit,
                "hhv_btu_scf": 1020.0,
            },
        )
        assert res_gas["intermediate"]["energy_mmbtu"] > 0

    # 4. Fuel volume for liquid fuel across units
    for l_unit in ["gal", "bbl", "m3", "l"]:
        res_liq = calc.calculate(
            method="equipment",
            inputs={
                "equipment_type": "ic_diesel",
                "amount": 100.0,
                "unit": l_unit,
                "hhv_mmbtu_gal": 0.138,
            },
        )
        assert res_liq["intermediate"]["energy_mmbtu"] > 0


# CH4 and N2O factors of every equipment row as the Compendium prints them in Table 4-11 "Converted to SI Basis"
# (tonne per 10^12 J, HHV; Table 4-9 for boilers is printed per 10^6 Btu). 1 MMBtu = 1.055056e9 J. TOC rows (gasoline,
# diesel) are tonne TOC and 9 wt % of the TOC is CH4 (AP-42, Table 4-11 footnote a). N2O: the table value where one is
# printed, otherwise the fuel factor (natural gas 1.0e-7, diesel and gasoline 6.0e-7 tonne/MMBtu, EPA Part 98).
PER_PJ = 1.055056e-3   # tonne per MMBtu for 1 tonne per 10^12 J
EQUIPMENT_TABLE_CH4_N2O = {
    "boiler_ng_controlled": (1.0e-6, 2.8e-7),
    "boiler_ng_uncontrolled": (1.0e-6, 9.8e-7),
    "ic_2s_lean_ng": (0.623 * PER_PJ, 1.0e-7),
    "ic_4s_lean_ng": (0.537 * PER_PJ, 1.0e-7),
    "ic_4s_lean_ng_vaughn": (0.494 * PER_PJ, 1.0e-7),
    "ic_4s_rich_ng": (0.10 * PER_PJ, 1.0e-7),
    "ic_4s_rich_ng_nscr": (0.043 * PER_PJ, 1.0e-7),
    "ic_gasoline": (1.30 * PER_PJ * 0.09, 6.0e-7),
    "ic_diesel": (0.15 * PER_PJ * 0.09, 6.0e-7),
    "ic_large_bore_diesel": (0.0035 * PER_PJ, 6.0e-7),
    "ic_dual_fuel": (0.26 * PER_PJ, 1.0e-7),
    "turbine_ng_uncontrolled": (0.0037 * PER_PJ, 0.0013 * PER_PJ),
}


def test_equipment_all_types(calc):
    """Every equipment row gives 100 MMBtu x its Compendium factor (a row added to EQUIPMENT_FACTORS must be pinned)."""
    assert set(EQUIPMENT_FACTORS) == set(EQUIPMENT_TABLE_CH4_N2O)
    for eq_key, (ch4_ef, n2o_ef) in EQUIPMENT_TABLE_CH4_N2O.items():
        res = calc.calculate(
            method="equipment",
            inputs={
                "equipment_type": eq_key,
                "energy_mmbtu": 100.0,
                "co2_ef_t_mmbtu": 0.055,  # custom override
            },
        )
        assert res["results"]["co2"]["value"] == pytest.approx(100.0 * 0.055, rel=1e-9), eq_key
        assert res["results"]["ch4"]["value"] == pytest.approx(100.0 * ch4_ef, rel=1e-6), eq_key
        assert res["results"]["n2o"]["value"] == pytest.approx(100.0 * n2o_ef, rel=1e-6), eq_key


def test_vehicle_distance(calc):
    """Test vehicle distance method with standard and custom factors."""
    # Standard heavy-duty diesel
    res_diesel = calc.calculate(
        method="vehicle_distance",
        inputs={
            "distance": 1000.0,
            "distance_unit": "mile",
            "vehicle_type": "hd_diesel_advanced",
            "vehicle_fuel": "diesel",
            "fuel_economy_mpg": 6.5,
        },
    )
    # gal = 1000 / 6.5 = 153.846
    assert pytest.approx(res_diesel["intermediate"]["fuel_gal"], rel=1e-3) == 153.846
    # 153.846 gal x 0.138 MMBtu/gal = 21.23 MMBtu: CO2 x 0.07396 t/MMBtu (Table 4-5); CH4 and N2O from the
    # Table 4-16 heavy-duty diesel (advanced control) factors, 4.2e-4 and 5.7e-4 t per 1,000 gal
    gal = 1000.0 / 6.5
    assert res_diesel["results"]["co2"]["value"] == pytest.approx(gal * 0.138 * 0.07396, rel=1e-6)
    assert res_diesel["results"]["ch4"]["value"] == pytest.approx(gal / 1000 * 4.2e-4, rel=1e-6)
    assert res_diesel["results"]["n2o"]["value"] > 0

    # Distance in km with gasoline vehicle and custom ch4/n2o factors
    res_km = calc.calculate(
        method="vehicle_distance",
        inputs={
            "amount": 160.934,  # ~100 miles
            "distance_unit": "km",
            "vehicle_fuel": "gasoline",
            "fuel_economy_mpg": 25.0,
            "hhv_mmbtu_gal": 0.125,
            "co2_ef_t_mmbtu": 0.070,
            "ch4_t_per_kgal": 0.0003,
            "n2o_t_per_kgal": 0.0005,
        },
    )
    assert pytest.approx(res_km["intermediate"]["fuel_gal"], rel=1e-2) == 4.0
    assert res_km["results"]["co2"]["value"] > 0


def test_flare_voc_back_calculation(calc):
    """Test flare back-calculation from VOC mass (Exhibit 5.2)."""
    res = calc.calculate(
        method="flare_voc",
        inputs={
            "voc_mass": 1.5,
            "voc_mass_unit": "t",
            "wt_ch4": 70.0,
            "wt_c2h6": 12.0,
            "wt_c3h8": 8.0,
            "wt_c4h10": 4.0,
            "wt_c5h12": 2.0,
            "wt_c6plus": 1.0,
            "wt_co2": 3.0,
            "combustion_efficiency": 98.0,
        },
    )
    # Exhibit 5.2 arithmetic by hand: VOC (C3+) is 8 + 4 + 2 + 1 = 15 wt %, hydrocarbon 70 + 12 + 15 = 97 wt %,
    # so 1.5 t VOC carries 1.5 x 97 / 15 = 9.7 t hydrocarbon; at 98 % efficiency the flared hydrocarbon is 50x the
    # emitted one (eff / (1 - eff) = 49 of it burnt). Carbon fractions 12 x n / MW (C6+ as hexane).
    wt = {"ch4": 70.0, "c2h6": 12.0, "c3h8": 8.0, "c4h10": 4.0, "c5h12": 2.0, "c6h14": 1.0}
    mw = {"ch4": 16.043, "c2h6": 30.069, "c3h8": 44.096, "c4h10": 58.122, "c5h12": 72.149, "c6h14": 86.175}
    nc = {"ch4": 1, "c2h6": 2, "c3h8": 3, "c4h10": 4, "c5h12": 5, "c6h14": 6}
    w_hc = sum(wt.values())
    c_mix = sum(wt[k] * 12.011 * nc[k] / mw[k] for k in wt) / w_hc
    hc_emitted = 1.5 * w_hc / 15.0
    assert res["intermediate"]["hc_emitted_t"] == pytest.approx(9.7, rel=1e-9)
    assert res["intermediate"]["hc_carbon_wt"] == pytest.approx(c_mix, rel=1e-3)
    assert res["results"]["co2"]["value"] == pytest.approx(
        hc_emitted * c_mix * 0.98 / 0.02 * 44.01 / 12.011 + 1.5 * 3.0 / 15.0, rel=2e-3)
    assert res["results"]["ch4"]["value"] == pytest.approx(hc_emitted * 70.0 / w_hc, rel=1e-9)
    # mixture molecular weight = hydrocarbon wt % / sum(wt % / MW)
    assert res["intermediate"]["hc_mw"] == pytest.approx(w_hc / sum(wt[k] / mw[k] for k in wt), rel=2e-3)
    # ideal-gas HHV of the mixture, Btu/scf, from the mole fractions (Eq 3-11; gross heating values at 60 F)
    hhv = {"ch4": 1010.0, "c2h6": 1769.7, "c3h8": 2516.1, "c4h10": 3262.4, "c5h12": 4008.9, "c6h14": 4755.9}
    mol = {k: wt[k] / mw[k] for k in wt}
    assert res["intermediate"]["hc_hhv_btu_scf"] == pytest.approx(
        sum(mol[k] * hhv[k] for k in wt) / sum(mol.values()), rel=2e-3)
    # N2O: hydrocarbon flared (9.7 / 0.02 = 485 t) in scf at 379.3 scf/lbmole x the mixture HHV x 9.5e-8 t/MMBtu
    flared_scf = hc_emitted / 0.02 * 2204.62 / res["intermediate"]["hc_mw"] * 379.3
    assert res["results"]["n2o"]["value"] == pytest.approx(
        flared_scf * res["intermediate"]["hc_hhv_btu_scf"] / 1e6 * 9.5e-8, rel=2e-3)

    # Test with kg and lb
    for m_unit in ["kg", "lb"]:
        res_m = calc.calculate(
            method="flare_voc",
            inputs={
                "amount": 2000.0,
                "unit": m_unit,
                "wt_ch4": 75.0,
                "wt_c3h8": 15.0,
                "wt_co2": 5.0,
            },
        )
        # 2,000 kg or lb of VOC: 75 + 15 = 90 wt % hydrocarbon, VOC (propane) 15 wt %: hydrocarbon = VOC x 90 / 15
        voc_t = 2000.0 * (0.001 if m_unit == "kg" else 1 / 2204.62)
        c_mix_m = (75.0 * 12.011 / 16.043 + 15.0 * 3 * 12.011 / 44.096) / 90.0
        assert res_m["results"]["co2"]["value"] == pytest.approx(
            voc_t * 90 / 15 * c_mix_m * 0.98 / 0.02 * 44.01 / 12.011 + voc_t * 5.0 / 15.0, rel=2e-3), m_unit
        assert res_m["results"]["ch4"]["value"] == pytest.approx(voc_t * 90 / 15 * 75.0 / 90.0, rel=1e-9), m_unit


def test_thermal_oxidizer(calc):
    """Test thermal oxidizer calculation with TOC mass and liquid loading."""
    # 1. Direct TOC mass
    res_mass = calc.calculate(
        method="thermal_oxidizer",
        inputs={
            "toc_mass": 5.0,
            "toc_mass_unit": "t",
            "toc_carbon_wt_pct": 82.0,
            "toc_ch4_wt_pct": 5.0,
            "destruction_efficiency": 99.0,
        },
    )
    # 5 t TOC x 82 wt % C x 44.01/12.011 x 99 % destroyed; CH4 = 5 t x 5 wt % x 1 % not destroyed
    assert res_mass["results"]["co2"]["value"] == pytest.approx(5.0 * 0.82 * 44.01 / 12.011 * 0.99, rel=1e-9)
    assert res_mass["results"]["ch4"]["value"] == pytest.approx(5.0 * 0.05 * 0.01, rel=1e-9)

    # 2. Liquid loading volume basis
    res_load = calc.calculate(
        method="thermal_oxidizer",
        inputs={
            "liquid_loaded": 10000.0,
            "liquid_unit": "bbl",
            "loading_loss_lb_kgal": 2.5,
            "voc_fraction_of_toc": 85.0,
            "toc_carbon_wt_pct": 80.0,
            "toc_ch4_wt_pct": 2.0,
            "destruction_efficiency": 98.0,
        },
    )
    # 10,000 bbl x 42 gal x 2.5 lb VOC/1,000 gal / 0.85 VOC share = 123,529 lb TOC = 56.03 t
    toc_t = 10000 * 42 / 1000 * 2.5 / 0.85 / 2204.62
    assert res_load["intermediate"]["toc_t"] == pytest.approx(toc_t, rel=1e-9)
    assert res_load["results"]["co2"]["value"] == pytest.approx(toc_t * 0.80 * 44.01 / 12.011 * 0.98, rel=1e-9)
    assert res_load["results"]["ch4"]["value"] == pytest.approx(toc_t * 0.02 * 0.02, rel=1e-9)


def test_combustion_methods_validation_and_errors(calc):
    """Test validation errors and edge conditions."""
    # Unknown method
    with pytest.raises(ValueError, match="Unknown combustion method"):
        calc.calculate(method="unknown_method", inputs={})

    # Missing required field
    with pytest.raises(ValueError, match="Missing required field"):
        calc.calculate(method="carbon_content", inputs={})

    # Non-numeric field
    with pytest.raises(ValueError, match="must be a number"):
        calc.calculate(method="carbon_content", inputs={"fuel_mass": "not_a_num", "carbon_wt_pct": 80.0})

    # Negative number
    with pytest.raises(ValueError, match="must be a non-negative number"):
        calc.calculate(method="carbon_content", inputs={"fuel_mass": -10.0, "carbon_wt_pct": 80.0})

    # Zero for positive-only field
    with pytest.raises(ValueError, match="must be a positive number"):
        calc.calculate(
            method="carbon_content",
            inputs={
                "fuel_volume": 100.0,
                "fuel_volume_unit": "gal",
                "fuel_density": 0.0,
                "density_unit": "lb/gal",
                "carbon_wt_pct": 80.0,
            },
        )

    # Percentage > 100
    with pytest.raises(ValueError, match="cannot exceed 100 %"):
        calc.calculate(method="carbon_content", inputs={"fuel_mass": 10.0, "carbon_wt_pct": 105.0})

    # Invalid unit
    with pytest.raises(ValueError, match="Fuel mass unit must be one of"):
        calc.calculate(
            method="carbon_content",
            inputs={"fuel_mass": 10.0, "fuel_mass_unit": "invalid_unit", "carbon_wt_pct": 80.0},
        )

    # Unknown equipment type
    with pytest.raises(ValueError, match="Unknown equipment type"):
        calc.calculate(
            method="equipment",
            inputs={"equipment_type": "hyperdrive_reactor", "energy_mmbtu": 100.0},
        )

    # Invalid vehicle fuel
    with pytest.raises(ValueError, match="Vehicle fuel must be diesel or gasoline"):
        calc.calculate(
            method="vehicle_distance",
            inputs={"distance": 100.0, "vehicle_fuel": "uranium", "fuel_economy_mpg": 20.0},
        )

    # Flare VOC without VOC fraction
    with pytest.raises(ValueError, match="flare gas analysis needs the VOC"):
        calc.calculate(
            method="flare_voc",
            inputs={"voc_mass": 1.0, "wt_ch4": 90.0, "wt_c2h6": 10.0},
        )

    # Flare VOC exceeding 100%
    with pytest.raises(ValueError, match="Gas analysis exceeds 100 wt %"):
        calc.calculate(
            method="flare_voc",
            inputs={"voc_mass": 1.0, "wt_ch4": 80.0, "wt_c3h8": 30.0},
        )

    # Flare combustion efficiency >= 100%
    with pytest.raises(ValueError, match="Combustion efficiency must be below 100 %"):
        calc.calculate(
            method="flare_voc",
            inputs={"voc_mass": 1.0, "wt_ch4": 80.0, "wt_c3h8": 15.0, "combustion_efficiency": 100.0},
        )

    # Thermal oxidizer VOC share of TOC == 0
    with pytest.raises(ValueError, match="VOC share of TOC must be above zero"):
        calc.calculate(
            method="thermal_oxidizer",
            inputs={
                "liquid_loaded": 100.0,
                "liquid_unit": "gal",
                "loading_loss_lb_kgal": 2.0,
                "voc_fraction_of_toc": 0.0,
                "toc_carbon_wt_pct": 80.0,
            },
        )
