"""Exhaustive branch and edge-case tests for CompletionFlowbackCalculator.
Targets: calculations/vented_completion.py to reach near 100% test coverage.
"""
import pytest
from calculations.vented import CompletionFlowbackCalculator
from calculations.constants import GWP_AR5


@pytest.fixture
def calc():
    return CompletionFlowbackCalculator()


def test_completion_input_validations(calc):
    """Test validation helpers for non-negative values and fractions."""
    # Invalid numeric value
    with pytest.raises(ValueError, match="Invalid numeric value"):
        calc._validate_non_negative("not-a-number", "Test Field")

    # Fraction percentage scaling (50% entered as 50)
    assert calc._normalize_fraction(50, "Test Fraction") == 0.50

    # Fraction out of range (> 100%)
    with pytest.raises(ValueError, match="must be between 0 and 1"):
        calc._normalize_fraction(150, "Test Fraction")

    # Sum of CH4 + CO2 > 1.001
    with pytest.raises(ValueError, match="cannot exceed 100%"):
        calc.calculate(ch4_content=0.90, co2_content=0.20, flowback_volume=1000)


def test_completion_zero_events_clean_zero(calc):
    """Zero events should yield zero emissions immediately."""
    res = calc.calculate(events=0.0, tier="tier1")
    assert res["results"]["ch4"]["value"] == 0.0
    assert res["results"]["co2"]["value"] == 0.0
    assert res["total_co2e"] == 0.0


def test_completion_offshore_table_6_7(calc):
    """Test API Table 6-7 offshore completions."""
    # Offshore gas well: 136.2 tonnes CH4/completion-day
    res_gas = calc.calculate(
        tier="tier1",
        location="offshore",
        well_type="gas",
        events=2.0,
        gwp_dict=GWP_AR5,
    )
    assert pytest.approx(res_gas["results"]["ch4"]["value"], rel=1e-3) == 136.2 * 2.0
    assert "Table 6-7" in res_gas["metadata"]["standard"]

    # Offshore oil well has no Table 6-7 factor and must be rejected
    with pytest.raises(ValueError, match="offshore completion factor for gas wells only"):
        calc.calculate(tier="tier1", location="offshore", well_type="oil")


def test_completion_tier1_flared_and_factor_code(calc):
    """Test Tier 1 flaring and factor_code with NoHF."""
    # Flared Tier 1 with N2O and combustion CO2
    res_flared = calc.calculate(
        tier="tier1",
        well_type="gas",
        fracturing=True,
        control_type="flared",
        control_efficiency=0.98,
        events=1.0,
        gwp_dict=GWP_AR5,
    )
    assert res_flared["results"]["co2"]["value"] > 0
    assert res_flared["results"]["ch4"]["value"] > 0
    assert res_flared["results"]["n2o"]["value"] > 0

    # Fracturing auto-detected from factor_code
    res_nohf = calc.calculate(
        tier="tier1",
        factor_code="CompGasNoHF_Vented",
        control_type="uncontrolled",
        events=1.0,
    )
    assert pytest.approx(res_nohf["results"]["ch4"]["value"], rel=1e-3) == 1.7376

    # Fracturing string "true" / "yes"
    res_str_hf = calc.calculate(
        tier="tier1",
        fracturing="yes",
        well_type="oil_producing_well",
        control_type="uncontrolled",
    )
    assert pytest.approx(res_str_hf["results"]["ch4"]["value"], rel=1e-3) == 14.419


def test_completion_tier2_production_rate_units_and_durations(calc):
    """Test Eq 6-7 with mmscf/day, m3/day, and vent duration in days."""
    # mmscf/day
    res_mmscf = calc.calculate(
        tier="tier2",
        daily_production_rate=2.0,
        prod_rate_unit="mmscf/day",
        vent_duration_days=3.0,
        ch4_content=0.85,
    )
    # 2 MMscf/day * 3 days = 6 MMscf
    assert res_mmscf["inputs"]["net_flowback_scf"] == 6_000_000.0

    # m3/day
    res_m3 = calc.calculate(
        tier="tier2",
        daily_production_rate=1000.0,
        prod_rate_unit="m3/day",
        flowback_duration_hours=48.0,
        ch4_content=0.85,
    )
    assert res_m3["inputs"]["net_flowback_m3"] > 0

    # Rate unit error: plain volume without time unit
    with pytest.raises(ValueError, match="must be a rate"):
        calc.calculate(
            tier="tier2",
            flowback_rate=100.0,
            rate_unit="mcf",
            flowback_duration_hours=10.0,
            ch4_content=0.85,
        )


def test_completion_tier3_volume_units_and_n2_units(calc):
    """Test Tier 3 metered volume units (mcf, mmscf) and N2 units (mcf, mmscf)."""
    # Flowback volume in mcf, N2 in mcf
    res_mcf = calc.calculate(
        tier="tier3",
        flowback_volume=5000.0,  # 5,000 Mcf = 5,000,000 scf
        volume_unit="mcf",
        injected_n2_volume=1000.0,  # 1,000 Mcf = 1,000,000 scf
        injected_n2_unit="mcf",
        injected_gas_type="n2",
        ch4_content=0.80,
    )
    # Net = 4,000,000 scf
    assert abs(res_mcf["inputs"]["net_flowback_scf"] - 4_000_000.0) < 1.0

    # Flowback volume in mmscf, N2 in mmscf
    res_mmscf = calc.calculate(
        tier="tier3",
        flowback_volume=10.0,  # 10 MMscf
        volume_unit="mmscf",
        injected_n2_volume=2.0,  # 2 MMscf
        injected_n2_unit="mmscf",
        ch4_content=0.80,
    )
    # Net = 8 MMscf
    assert abs(res_mmscf["inputs"]["net_flowback_scf"] - 8_000_000.0) < 1.0


def test_completion_tier3_initial_flowback_zero_duration_error(calc):
    """Initial flowback specified but metered flowback duration Tm <= 0 raises ValueError."""
    with pytest.raises(ValueError, match="Metered flowback duration .* cannot be zero"):
        calc.calculate(
            tier="tier3",
            flowback_volume=10000.0,
            initial_flowback_hours=5.0,
            flowback_duration_hours=0.0,
            ch4_content=0.80,
        )


def test_completion_disposition_fallbacks_and_c2plus(calc):
    """Test unstated disposition fallback to control_efficiency and c2plus content combustion."""
    # Disposition unstated, control_efficiency given
    res_disp_ctrl = calc.calculate(
        tier="tier3",
        flowback_volume=100000.0,
        volume_unit="scf",
        control_efficiency=0.95,
        ch4_content=0.80,
        c2plus_content=5.0,  # 5% ethane-equivalent
    )
    assert res_disp_ctrl["inputs"]["frac_flared"] == 0.95
    assert res_disp_ctrl["inputs"]["frac_vented"] == pytest.approx(0.05)
    assert res_disp_ctrl["results"]["co2"]["value"] > 0

    # Unknown disposition string falls back to 100% vented
    res_disp_unk = calc.calculate(
        tier="tier3",
        flowback_volume=100000.0,
        volume_unit="scf",
        disposition="other_pipeline",
        ch4_content=0.80,
    )
    assert res_disp_unk["inputs"]["frac_vented"] == 1.0
    assert res_disp_unk["inputs"]["frac_flared"] == 0.0

    # Missing CH4 content when flowback volume > 0 raises ValueError
    with pytest.raises(ValueError, match="Missing required field: CH4 content"):
        calc.calculate(tier="tier3", flowback_volume=100000.0)
