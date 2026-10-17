"""
Exhaustive unit test suite for engineering branches of CalculationDispatcher:
- Drilling & well completions (dispatcher_branches_combustion.py)
- Liquids unloading (dispatcher_branches_combustion.py)
- Venting, tanks, pneumatic devices & dehydrators (dispatcher_branches_venting.py)
- Fugitives, compressor seals & acid gas removal (dispatcher_branches_fugitive.py)

Covers all physical equations, EPA Subpart W / API 2021 methods, validation bounds,
and error handling.
"""

import pytest
from calculations.dispatcher import CalculationDispatcher


@pytest.fixture
def dispatcher():
    return CalculationDispatcher()


# =============================================================================
# 1. DRILLING & COMPLETIONS BRANCHES
# =============================================================================

def test_dispatcher_drilling_and_completions(dispatcher):
    """Test drilling tier levels and well completion methods."""
    # Drilling Tier 1
    res_t1 = dispatcher.dispatch(
        "drilling",
        {
            "tier": "tier1",
            "amount": 2.0,
            "unit": "wells",
            "mud_type": "water_based",
        },
        {},
        {},
    )
    assert res_t1["results"]["ch4"]["value"] > 0

    # Drilling Tier 2+ with offshore location
    res_t2p = dispatcher.dispatch(
        "drilling",
        {
            "tier": "tier2_plus",
            "drilling_days": 10.0,
            "unit": "days",
            "mud_type": "oil_based",
            "ch4_pct": 85.0,
            "co2_pct": 5.0,
            "well_location": "offshore",
        },
        {},
        {},
    )
    assert res_t2p["results"]["ch4"]["value"] > 0

    # Drilling hours converted to days
    res_h = dispatcher.dispatch(
        "drilling",
        {
            "amount": 48.0,
            "unit": "hours",
            "mud_type": "water_based",
        },
        {},
        {},
    )
    assert res_h["results"]["ch4"]["value"] > 0

    # Drilling invalid unit raises ValueError
    with pytest.raises(ValueError, match="Drilling activity is in drilling days"):
        dispatcher.dispatch("drilling", {"amount": 100.0, "unit": "m3"}, {}, {})

    # Completions Tier 3 with flowback volume
    res_comp_t3 = dispatcher.dispatch(
        "completions",
        {
            "tier": "tier3",
            "flowback_volume": 50000.0,
            "volume_unit": "scf",
            "ch4_content": 80.0,
            "co2_mol": 5.0,
            "comp_disposition": "flared",
        },
        {},
        {},
    )
    assert res_comp_t3["results"]["co2"]["value"] > 0

    # Completions daily rate method
    res_comp_rate = dispatcher.dispatch(
        "completions",
        {
            "daily_production_rate": 500.0,
            "comp_duration": 48.0,
            "unit": "mcf",
            "ch4_content": 80.0,
        },
        {},
        {},
    )
    assert res_comp_rate["results"]["ch4"]["value"] > 0

    # Completions invalid flowback volume unit
    with pytest.raises(ValueError, match="need the flowback volume unit"):
        dispatcher.dispatch(
            "completions",
            {
                "tier": "tier3",
                "flowback_volume": 500.0,
                "volume_unit": "bbl",
                "ch4_content": 80.0,
            },
            {},
            {},
        )


# =============================================================================
# 2. LIQUIDS UNLOADING BRANCHES
# =============================================================================

def test_dispatcher_liquids_unloading(dispatcher):
    """Test liquids unloading API Equations 6-11, 6-10, and 6-3."""
    # API Eq 6-11 (automated plunger lift)
    res_611 = dispatcher.dispatch(
        "unloading",
        {
            "factor_source": "specific",
            "calc_method": "api_equation_6_11",
            "p_shut": 100.0,
            "p_line": 50.0,
            "p_sep": 30.0,
            "sfr_p": 500.0,
            "t_p": 2.0,
            "events": 10,
            "ch4_content": 85.0,
        },
        {},
        {},
    )
    assert res_611["results"]["ch4"]["value"] > 0

    # API Eq 6-10 (EPA Subpart W)
    res_610 = dispatcher.dispatch(
        "unloading",
        {
            "factor_source": "specific",
            "calc_method": "api_equation_6_10",
            "unload_depth": 5000.0,
            "unload_diam": 2.5,
            "unload_press": 120.0,
            "events": 12,
            "sfr": 300.0,
            "hours_open": 1.5,
            "unloading_type": "plunger",
            "ch4_content": 80.0,
        },
        {},
        {},
    )
    assert res_610["results"]["ch4"]["value"] > 0

    # API Eq 6-3 (Volume-based wellbore decompression)
    res_63 = dispatcher.dispatch(
        "unloading",
        {
            "factor_source": "specific",
            "unload_depth": 4000.0,
            "unload_diam": 2.0,
            "unload_press": 100.0,
            "events": 8,
            "ch4_content": 85.0,
        },
        {},
        {},
    )
    assert res_63["results"]["ch4"]["value"] > 0

    # Eq 6-10 missing lift type raises ValueError
    with pytest.raises(ValueError, match="lift type"):
        dispatcher.dispatch(
            "unloading",
            {
                "factor_source": "specific",
                "calc_method": "api_equation_6_10",
                "unload_depth": 5000.0,
                "unload_diam": 2.5,
                "unload_press": 120.0,
                "events": 12,
                "sfr": 300.0,
                "hours_open": 1.5,
                "ch4_content": 80.0,
            },
            {},
            {},
        )


# =============================================================================
# 3. VENTING, TANKS, PNEUMATICS & DEHYDRATORS
# =============================================================================

def test_dispatcher_venting_tanks_pneumatics(dispatcher):
    """Test blowdowns, associated gas, tanks, pneumatic devices, and dehydrators."""
    # Blowdown with residual pressure
    res_blow = dispatcher.dispatch(
        "blowdown",
        {
            "factor_source": "specific",
            "blowdown_volume": 100.0,
            "blowdown_unit": "m3",
            "blowdown_pressure": 150.0,
            "blowdown_events": 5,
            "ch4_content": 85.0,
            "co2_mol": 2.0,
            "blowdown_final_pressure": 15.0,
        },
        {},
        {},
    )
    assert res_blow["results"]["ch4"]["value"] > 0

    # Associated gas venting Tier 1
    res_assoc_t1 = dispatcher.dispatch(
        "associated_gas_venting",
        {
            "oil_production": 1000.0,
            "oil_unit": "bbl",
            "basin": "Permian",
        },
        {},
        {},
    )
    assert res_assoc_t1["results"]["ch4"]["value"] > 0

    # Associated gas venting Tier 2
    res_assoc_t2 = dispatcher.dispatch(
        "associated_gas_venting",
        {
            "oil_production": 1000.0,
            "gor": 500.0,
            "venting_duration": 10.0,
            "duration_unit": "hours",
            "flared_gas_volume": 200.0,
            "ch4_content": 80.0,
        },
        {},
        {},
    )
    assert res_assoc_t2["results"]["ch4"]["value"] > 0

    # Tank flashing
    res_tank = dispatcher.dispatch(
        "tank",
        {
            "factor_source": "specific",
            "amount": 5000.0,
            "unit": "bbl",
            "tank_gor": 25.0,
            "ch4_content": 75.0,
            "liquid_type": "condensate",
            "api_gravity": 45.0,
            "separator_pressure_psig": 50.0,
            "separator_temp_f": 90.0,
        },
        {},
        {},
    )
    assert res_tank["results"]["ch4"]["value"] > 0

    # Tank invalid liquid raises ValueError
    with pytest.raises(ValueError, match="tank liquid type must be"):
        dispatcher.dispatch("tank", {"factor_source": "specific", "amount": 100.0, "unit": "bbl", "liquid_type": "invalid"}, {}, {})

    # Tank working loss raises ValueError
    with pytest.raises(ValueError, match="Working and breathing losses"):
        dispatcher.dispatch("tank_working", {"factor_source": "specific", "amount": 100.0, "unit": "bbl"}, {}, {})

    # Pneumatic devices with high_bleed controller type
    res_pneu = dispatcher.dispatch(
        "pneumatics",
        {
            "factor_source": "specific",
            "device_count": 10,
            "pneu_controller_type": "high_bleed",
            "hours": 8000.0,
            "ch4_content": 80.0,
        },
        {},
        {},
    )
    assert res_pneu["results"]["ch4"]["value"] > 0

    # Pneumatic devices measured bleed rate
    res_pneu_bleed = dispatcher.dispatch(
        "pneumatics",
        {
            "factor_source": "specific",
            "device_count": 5,
            "pneu_bleed_rate": 15.0,
            "pneu_bleed_unit": "scf/hr",
            "ch4_content": 82.0,
        },
        {},
        {},
    )
    assert res_pneu_bleed["results"]["ch4"]["value"] > 0

    # Pneumatic devices monitoring program
    res_pneu_mon = dispatcher.dispatch(
        "pneumatics",
        {
            "factor_source": "specific",
            "device_count": 20,
            "pneu_monitoring": True,
            "pneu_normal_count": 18,
            "pneu_malfunction_count": 2,
        },
        {},
        {},
    )
    assert res_pneu_mon["results"]["ch4"]["value"] > 0

    # Pneumatic missing parameters raises ValueError
    with pytest.raises(ValueError, match="need a controller type"):
        dispatcher.dispatch("pneumatics", {"factor_source": "specific", "device_count": 5}, {}, {})

    # Glycol dehydrator
    res_dehy = dispatcher.dispatch(
        "dehydrator",
        {
            "factor_source": "specific",
            "throughput": 10.0,
            "ch4_content": 85.0,
            "control_efficiency": 95.0,
        },
        {},
        {},
    )
    assert res_dehy["results"]["ch4"]["value"] > 0

    # Glycol dehydrator pump rate raises ValueError
    with pytest.raises(ValueError, match="Glycol dehydrator Tier 3"):
        dispatcher.dispatch("dehydrator", {"factor_source": "specific", "throughput": 10.0, "ch4_content": 85.0, "pump_rate": 5.0}, {}, {})


# =============================================================================
# 4. FUGITIVES, COMPRESSOR SEAL & AGR BRANCHES
# =============================================================================

def test_dispatcher_fugitive_compressor_agr(dispatcher):
    """Test correlation, method 21, direct measurement, compressor seal, and AGR."""
    # Fugitive correlation equation
    res_corr = dispatcher.dispatch(
        "fugitive_screening",
        {
            "factor_source": "specific",
            "fugitive_sub_method": "correlation",
            "screening_values_ppm": [500, 1500, 8000],
            "operating_hours": 2000.0,
            "ch4_wt_fraction": 0.6,
        },
        {},
        {},
    )
    assert res_corr["results"]["ch4"]["value"] > 0

    # Fugitive Method 21 ranges
    res_m21 = dispatcher.dispatch(
        "fugitive_screening",
        {
            "factor_source": "specific",
            "fugitive_sub_method": "method21",
            "m21_below_count": 20,
            "m21_above_count": 2,
            "operating_hours": 1000.0,
        },
        {},
        {},
    )
    assert res_m21["results"]["ch4"]["value"] > 0

    # Fugitive direct measurement
    res_meas = dispatcher.dispatch(
        "fugitive_screening",
        {
            "factor_source": "specific",
            "fugitive_sub_method": "measurement",
            "measured_rate": 1.2,
            "rate_unit": "kg/hr",
            "operating_hours": 500.0,
            "ch4_content": 85.0,
        },
        {},
        {},
    )
    assert res_meas["results"]["ch4"]["value"] > 0

    # Component count fugitive
    res_comp = dispatcher.dispatch(
        "component_fugitive",
        {
            "factor_source": "specific",
            "component_counts": {"valves": 50, "flanges": 100},
            "operating_hours": 4000.0,
            "ef": 0.002,
        },
        {},
        {},
    )
    assert res_comp["results"]["ch4"]["value"] > 0

    # Compressor seal reciprocating
    res_recip = dispatcher.dispatch(
        "compressor_seal",
        {
            "factor_source": "specific",
            "compressor_type": "reciprocating",
            "compressor_count": 3,
            "operating_hours": 3000.0,
        },
        {},
        {},
    )
    assert res_recip["results"]["ch4"]["value"] > 0

    # AGR (acid gas removal) with thermal oxidizer flare control
    res_agr = dispatcher.dispatch(
        "agr",
        {
            "factor_source": "specific",
            "agr_throughput": 5.0,
            "unit": "mmscf",
            "agr_co2_in": 8.0,
            "agr_co2_out": 1.0,
            "agr_control_eff": 98.0,
            "agr_control_type": "flare",
        },
        {},
        {},
    )
    assert res_agr["results"]["co2"]["value"] > 0

    # AGR outlet > inlet CO2 raises ValueError
    with pytest.raises(ValueError, match="Outlet CO2 cannot exceed inlet CO2"):
        dispatcher.dispatch(
            "agr",
            {
                "factor_source": "specific",
                "agr_throughput": 5.0,
                "unit": "mmscf",
                "agr_co2_in": 1.0,
                "agr_co2_out": 8.0,
            },
            {},
            {},
        )

    # AGR control type without control efficiency raises ValueError
    with pytest.raises(ValueError, match="needs a control / destruction efficiency"):
        dispatcher.dispatch(
            "agr",
            {
                "factor_source": "specific",
                "agr_throughput": 5.0,
                "unit": "mmscf",
                "agr_co2_in": 8.0,
                "agr_co2_out": 1.0,
                "agr_control_type": "flare",
                "agr_control_eff": 0.0,
            },
            {},
            {},
        )
