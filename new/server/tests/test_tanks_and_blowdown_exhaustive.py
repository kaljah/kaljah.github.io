"""Exhaustive tests for AcidGasRemovalCalculator, TankFlashingCalculator, and BlowdownCalculator.
Targets: calculations/vented_production_tank.py to reach near 100% test coverage.
"""
import pytest
from calculations.vented_production_tank import (
    AcidGasRemovalCalculator,
    TankFlashingCalculator,
    BlowdownCalculator,
)
from calculations.constants import GWP_AR5


@pytest.fixture
def agr():
    return AcidGasRemovalCalculator()


@pytest.fixture
def tank():
    return TankFlashingCalculator()


@pytest.fixture
def blowdown():
    return BlowdownCalculator()


# =============================================================================
# 1. ACID GAS REMOVAL CALCULATOR (AGR)
# =============================================================================

def test_agr_scf_units_and_dispositions(agr):
    """Test AGR with sour_gas_scf_yr, percentage CO2, sweet_gas_scf_yr, and dispositions."""
    # 1. sour_gas_scf_yr and sweet_gas_scf_yr
    res_scf = agr.calculate(
        sour_gas_scf_yr=10_000_000.0,
        sour_co2_content=0.10,  # 10%
        sweet_gas_scf_yr=9_000_000.0,
        sweet_co2_content=0.01,  # 1%
        disposition="vented",
        gwp_dict=GWP_AR5,
    )
    assert res_scf["results"]["co2"]["value"] > 0
    assert res_scf["results"]["ch4"]["value"] > 0

    # 2. default sweet gas volume estimation when sweet_gas not provided
    res_def_sweet = agr.calculate(
        sour_gas_mmscf_yr=10.0,
        sour_co2_content=0.08,
        disposition="flared",
        control_efficiency=0.98,
        gwp_dict=GWP_AR5,
    )
    assert res_def_sweet["results"]["co2"]["value"] > 0
    assert res_def_sweet["inputs"]["disposition"] == "flared"

    # 3. Recovered disposition (zero emissions)
    res_rec = agr.calculate(
        sour_gas_mmscf_yr=10.0,
        sour_co2_content=0.05,
        disposition="recovered",
        gwp_dict=GWP_AR5,
    )
    assert res_rec["results"]["ch4"]["value"] == 0.0
    assert res_rec["results"]["co2"]["value"] == 0.0


# =============================================================================
# 2. TANK FLASHING CALCULATOR
# =============================================================================

def test_tank_method_auto_detection(tank):
    """Test auto-detection of tank methods: working_loss, produced_water, vbe, table_6_22, table_6_24."""
    # 1. Auto-detect working loss
    res_wl = tank.calculate(
        throughput=10000.0,
        ef_ch4=0.05,
    )
    assert res_wl["inputs"]["method"] == "working_loss"
    assert res_wl["results"]["ch4"]["value"] > 0

    # 2. Auto-detect produced water
    res_pw = tank.calculate(
        liquid_type="produced_water",
        throughput=50000.0,
        separator_pressure_psi=250.0,
        salt_content="unknown_salt_spec",  # falls back to "average"
        co2_content=0.02,
    )
    assert res_pw["inputs"]["method"] == "produced_water"
    assert res_pw["results"]["ch4"]["value"] > 0
    assert res_pw["results"]["co2"]["value"] > 0

    # 3. Auto-detect VBE correlation
    res_vbe = tank.calculate(
        throughput=10000.0,
        api_gravity=40.0,
        separator_pressure_psig=50.0,
        separator_temp_f=100.0,
        ch4_content=85.0,  # percentage
        co2_content=5.0,
    )
    assert res_vbe["inputs"]["method"] == "vbe"

    # 4. Auto-detect Table 6-22 (crude) and Table 6-24 (condensate)
    res_t22 = tank.calculate(liquid_type="crude", throughput=10000.0)
    assert res_t22["inputs"]["method"] == "table_6_22"

    res_t24 = tank.calculate(liquid_type="condensate", throughput=10000.0)
    assert res_t24["inputs"]["method"] == "table_6_24"


def test_tank_missing_separator_data_error(tank):
    """Correlation methods missing separator data raise ValueError."""
    with pytest.raises(ValueError, match="needs api_gravity, separator_pressure_psig"):
        tank.calculate(method="vbe", throughput=10000.0)

    with pytest.raises(ValueError, match="needs separator_pressure_psig"):
        tank.calculate(method="eub", throughput=10000.0)


def test_tank_default_factors_and_dump_valve(tank):
    """Test Table 6-22/6-24 default factors, small tank size, and dump valve without hours."""
    # Small tank size for crude
    res_small = tank.calculate(
        method="table_6_22",
        liquid_type="crude",
        tank_size="small",
        throughput=5000.0,
        co2_content=0.03,
    )
    assert res_small["results"]["ch4"]["value"] > 0
    assert res_small["results"]["co2"]["value"] > 0

    # Dump valve without hours
    res_dv = tank.calculate(
        method="dump_valve",
        liquid_type="crude",
        throughput=10000.0,
        co2_content=0.05,
    )
    assert res_dv["results"]["ch4"]["value"] > 0
    assert res_dv["results"]["co2"]["value"] > 0

    # Recovered/controlled on tanks
    res_rec = tank.calculate(
        method="table_6_22",
        throughput=10000.0,
        control_type="vru",
        control_efficiency=1.0,
    )
    assert res_rec["results"]["ch4"]["value"] == 0.0


# =============================================================================
# 3. BLOWDOWN CALCULATOR
# =============================================================================

def test_blowdown_table_6_32_and_errors(blowdown):
    """Test Table 6-32 equipment factors, CO2 content, and negative input errors."""
    # Table 6-32 activity factor with CO2 content
    res_t32 = blowdown.calculate(
        activity_type="vessel",
        equipment_count=5.0,
        ch4_content=80.0,  # percentage
        co2_content=10.0,
        gwp_dict=GWP_AR5,
    )
    assert res_t32["results"]["ch4"]["value"] > 0
    assert res_t32["results"]["co2"]["value"] > 0

    # Negative equipment count
    with pytest.raises(ValueError, match="cannot be negative"):
        blowdown.calculate(activity_type="vessel", equipment_count=-2.0)

    # Negative events
    with pytest.raises(ValueError, match="cannot be negative"):
        blowdown.calculate(pressure=100.0, events=-1.0, blowdown_volume=10.0)

    # Negative volume
    with pytest.raises(ValueError, match="cannot be negative"):
        blowdown.calculate(pressure=100.0, events=1.0, blowdown_volume=-5.0)

    # Negative pressure error
    with pytest.raises(ValueError, match="cannot be negative"):
        blowdown.calculate(pressure=-50.0, events=1.0, blowdown_volume=10.0)



def test_blowdown_high_pressure_and_differential(blowdown):
    """Test automatic Z-factor in high-pressure regime and differential blowdown."""
    # High pressure >= 1000 psia invokes real gas compressibility estimate_gas_z_factor
    res_hp = blowdown.calculate(
        pressure=1500.0,  # psia
        press_unit="psia",
        operating_temperature=80.0,
        temp_unit="F",
        events=1.0,
        blowdown_volume=50.0,
        ch4_content=0.85,
    )
    assert res_hp["results"]["ch4"]["value"] > 0

    # Differential blowdown with final pressure
    res_diff = blowdown.calculate(
        blowdown_mode="differential",
        pressure=500.0,
        final_pressure=50.0,
        press_unit="psig",
        operating_temperature=60.0,
        events=2.0,
        blowdown_volume=20.0,
        ch4_content=0.80,
    )
    assert res_diff["results"]["ch4"]["value"] > 0

    # Final pressure below absolute vacuum raises error
    with pytest.raises(ValueError, match="below absolute vacuum"):
        blowdown.calculate(
            blowdown_mode="differential",
            pressure=100.0,
            final_pressure=-50.0,
            press_unit="psia",
            events=1.0,
            blowdown_volume=10.0,
        )


def test_tank_agr_blowdown_edge_branches(agr, tank, blowdown):
    """Test 100% boundary conditions for AGR percentages, VBE heavy oil, and blowdown errors."""
    # AGR percentage inputs > 1.0
    res_agr = agr.calculate(
        sour_gas_scf_yr=100000.0,
        sour_co2_content=5.0,  # 5%
        sweet_co2_content=2.0,  # 2%
    )
    assert res_agr["results"]["co2"]["value"] > 0

    # VBE heavy oil (API <= 30.0)
    res_vbe_heavy = tank.calculate(
        method="vbe",
        throughput=5000.0,
        api_gravity=25.0,
        separator_pressure_psig=50.0,
        separator_temp_f=100.0,
    )
    assert res_vbe_heavy["results"]["ch4"]["value"] > 0

    # Blowdown negative events
    with pytest.raises(ValueError, match="cannot be negative"):
        blowdown.calculate(
            pressure=100.0,
            events=-1.0,
            blowdown_volume=10.0,
        )

    # Blowdown negative volume
    with pytest.raises(ValueError, match="cannot be negative"):
        blowdown.calculate(
            pressure=100.0,
            events=1.0,
            blowdown_volume=-10.0,
        )

    # Blowdown initial pressure negative
    with pytest.raises(ValueError, match="cannot be negative"):
        blowdown.calculate(
            pressure=-20.0,
            press_unit="psig",
            events=1.0,
            blowdown_volume=10.0,
        )

