"""
Tests for previously untested calculation paths - Part 11
Forensic audit and remediation for Bugs 61 through 70+:
  - Bug 61: CombustionCalculator rejects negative fuel_quantity.
  - Bug 62: CombustionCalculator gas composition percentage normalization for small percentages (c1="1%", co2_comp="0.5%") and negative bounds.
  - Bug 63: FlaringCalculator rejects negative gas_volume and negative ch4_fraction.
  - Bug 64: FlaringCalculator gas composition percentage scaling for ch4_fraction="1%" / "0.5%".
  - Bug 65: user_hhv rejects negative heating value (HHV).
  - Bug 66: AssociatedGasVentingCalculator._normalize_fraction scales "0.5%" and "1%" without 100x error.
  - Bug 67: AssociatedGasVentingCalculator rejects negative ef_ch4 in Tier 1 and negative duration in Tier 3.
  - Bug 68: CompletionFlowbackCalculator._normalize_fraction scales "0.5%" and "1%" without 100x error.
  - Bug 69: CompletionFlowbackCalculator c2plus_content accepts percentage strings ("1%", "0.5%"), normalizes, and rejects negative.
  - Bug 70: MudDegassingCalculator _parse_conc scales "1%" and "0.5%" without 100x error, rejects negative concentration, and rejects negative ef_ch4.
  - Bonus: WellTestingCalculator and CoalSeamDrillingCalculator validation & percentage normalization.
"""
import pytest
from calculations.combustion import CombustionCalculator, FlaringCalculator, user_hhv
from calculations.vented_associated_gas import AssociatedGasVentingCalculator
from calculations.vented_completion import CompletionFlowbackCalculator
from calculations.vented_mud import MudDegassingCalculator
from calculations.vented_exploration import WellTestingCalculator, CoalSeamDrillingCalculator


# --- Bug 61: CombustionCalculator Negative Fuel Quantity ---
def test_combustion_calculator_negative_fuel_quantity():
    calc = CombustionCalculator()
    with pytest.raises(ValueError, match="quantity cannot be negative"):
        calc.calculate(fuel_quantity=-50.0, ef_co2=53.06, ef_unit="kg/mmbtu", fuel_unit="scf")


# --- Bug 62: CombustionCalculator Gas Composition Small Percentages and Negative Bounds ---
def test_combustion_calculator_gas_composition_percentage_scaling():
    calc = CombustionCalculator()
    # Fuel gas with 1% methane and 0.5% native CO2
    res_pct = calc.calculate(
        fuel_quantity=1000.0,
        fuel_unit="m3",
        fuel_type="natural_gas",
        c1="1%",
        co2_comp="0.5%",
    )
    # Fuel gas with exact decimal ratios 0.01 and 0.005
    res_dec = calc.calculate(
        fuel_quantity=1000.0,
        fuel_unit="m3",
        fuel_type="natural_gas",
        c1=0.01,
        co2_comp=0.005,
    )
    # The percentage string "1%" must yield identical emissions to 0.01 fraction
    assert pytest.approx(res_pct["results"]["co2"]["value"], rel=1e-4) == res_dec["results"]["co2"]["value"]
    assert pytest.approx(res_pct["results"]["ch4"]["value"], rel=1e-4) == res_dec["results"]["ch4"]["value"]

    # Negative gas component concentration must raise ValueError
    with pytest.raises(ValueError, match="Gas component concentration cannot be negative"):
        calc.calculate(fuel_quantity=100.0, fuel_unit="m3", fuel_type="natural_gas", c1=-0.5)


# --- Bug 63: FlaringCalculator Negative Gas Volume and CH4 Fraction ---
def test_flaring_calculator_negative_inputs():
    calc = FlaringCalculator()
    with pytest.raises(ValueError, match="volume cannot be negative"):
        calc.calculate(gas_volume=-1000.0, ch4_fraction=0.85, flare_type="steam_assisted", uncertainties={})

    with pytest.raises(ValueError, match="ch4_fraction cannot be negative"):
        calc.calculate(gas_volume=1000.0, ch4_fraction=-0.1, flare_type="steam_assisted", uncertainties={})

    with pytest.raises(ValueError, match="CH4 fraction cannot be negative"):
        calc.calculate(gas_volume=1000.0, ch4_fraction="-5%", flare_type="steam_assisted", uncertainties={})


# --- Bug 64: FlaringCalculator Small Percentage Scaling ---
def test_flaring_calculator_percentage_scaling():
    calc = FlaringCalculator()
    # Flare gas with lean 1% methane
    res_pct = calc.calculate(gas_volume=1000.0, ch4_fraction="1%", flare_type="unassisted", uncertainties={})
    res_dec = calc.calculate(gas_volume=1000.0, ch4_fraction=0.01, flare_type="unassisted", uncertainties={})

    assert pytest.approx(res_pct["results"]["co2"]["value"], rel=1e-4) == res_dec["results"]["co2"]["value"]
    assert pytest.approx(res_pct["results"]["ch4"]["value"], rel=1e-4) == res_dec["results"]["ch4"]["value"]


# --- Bug 65: user_hhv Negative Heating Value ---
def test_user_hhv_negative_bounds():
    with pytest.raises(ValueError, match="Heating value \\(HHV\\) cannot be negative"):
        user_hhv(-1000.0, "btu/scf")

    with pytest.raises(ValueError, match="Heating value \\(HHV\\) cannot be negative"):
        user_hhv(-50.0, "btu/unit")


# --- Bug 66: AssociatedGasVentingCalculator Percentage Scaling ---
def test_associated_gas_normalize_fraction_small_percentages():
    # "0.5%" must normalize to 0.005, not 0.5
    f_half_pct = AssociatedGasVentingCalculator._normalize_fraction("0.5%")
    assert pytest.approx(f_half_pct, rel=1e-5) == 0.005

    # "1%" must normalize to 0.01, not 1.0
    f_one_pct = AssociatedGasVentingCalculator._normalize_fraction("1%")
    assert pytest.approx(f_one_pct, rel=1e-5) == 0.01

    # "85%" normalizes to 0.85
    f_eighty_five = AssociatedGasVentingCalculator._normalize_fraction("85%")
    assert pytest.approx(f_eighty_five, rel=1e-5) == 0.85

    # 0.85 decimal normalizes to 0.85
    assert pytest.approx(AssociatedGasVentingCalculator._normalize_fraction(0.85), rel=1e-5) == 0.85


# --- Bug 67: AssociatedGasVentingCalculator Negative ef_ch4 and Duration ---
def test_associated_gas_negative_ef_and_duration():
    ag = AssociatedGasVentingCalculator()
    with pytest.raises(ValueError, match="CH4 emission factor cannot be negative"):
        ag.calculate(tier="Tier 1", oil_production=1000.0, ef_ch4=-1.5)

    with pytest.raises(ValueError, match="Venting duration cannot be negative"):
        ag.calculate(tier="Tier 3", vent_volume=1000.0, ch4_content=0.85, venting_duration=-10.0)


# --- Bug 68: CompletionFlowbackCalculator Percentage Normalization ---
def test_completion_normalize_fraction_small_percentages():
    cf = CompletionFlowbackCalculator()
    # "0.5%" must normalize to 0.005, not 0.5
    assert pytest.approx(cf._normalize_fraction("0.5%", "test"), rel=1e-5) == 0.005
    # "1%" must normalize to 0.01, not 1.0
    assert pytest.approx(cf._normalize_fraction("1%", "test"), rel=1e-5) == 0.01
    # Negative raises ValueError
    with pytest.raises(ValueError, match="test cannot be negative"):
        cf._normalize_fraction("-5%", "test")


# --- Bug 69: CompletionFlowbackCalculator c2plus_content Normalization ---
def test_completion_c2plus_content_percentage_and_bounds():
    cf = CompletionFlowbackCalculator()
    # Accepts string percentage "1%" and normalizes to 0.01
    c2_norm = cf._normalize_c2("1%")
    assert pytest.approx(c2_norm, rel=1e-5) == 0.01

    # Accepts "0.5%" and normalizes to 0.005
    c2_half = cf._normalize_c2("0.5%")
    assert pytest.approx(c2_half, rel=1e-5) == 0.005

    # Rejects negative c2plus_content
    with pytest.raises(ValueError, match="c2plus_content cannot be negative"):
        cf._normalize_c2("-0.05")

    # In calculation: verify flared CO2 includes ethane combustion with percentage string
    res = cf.calculate(
        tier="tier3",
        flowback_volume=1000.0,
        volume_unit="scf",
        ch4_content=0.85,
        c2plus_content="1%",
        disposition="flared",
    )
    assert res["results"]["co2"]["value"] > 0


# --- Bug 70: MudDegassingCalculator Percentage Scaling and ef_ch4 Validation ---
def test_mud_degassing_calculator_percentages_and_negative_ef():
    md = MudDegassingCalculator()
    # Tier 2+ with small percentage string "1%"
    res_pct = md.calculate(tier="tier2_plus", drilling_days=10.0, ch4_concentration="1%")
    res_dec = md.calculate(tier="tier2_plus", drilling_days=10.0, ch4_concentration=0.01)
    assert pytest.approx(res_pct["results"]["ch4"]["value"], rel=1e-5) == res_dec["results"]["ch4"]["value"]

    # Rejects negative gas concentration
    with pytest.raises(ValueError, match="Gas concentration cannot be negative"):
        md.calculate(tier="tier2_plus", drilling_days=10.0, ch4_concentration="-5%")

    # Rejects negative custom ef_ch4 in Tier 1
    with pytest.raises(ValueError, match="ef_ch4 cannot be negative"):
        md.calculate(tier="tier1", wells=5.0, ef_ch4=-0.05)

    # Rejects negative custom ef_ch4 in Tier 2
    with pytest.raises(ValueError, match="ef_ch4 cannot be negative"):
        md.calculate(tier="tier2", drilling_days=10.0, ef_ch4=-0.05)


# --- Bonus: WellTestingCalculator and CoalSeamDrillingCalculator ---
def test_exploration_calculators_robustness():
    wt = WellTestingCalculator()
    with pytest.raises(ValueError, match="Number of events cannot be negative"):
        wt.calculate(events=-2.0)

    # Test percentage strings in well testing
    res_wt_pct = wt.calculate(events=1.0, ch4_content="85%", co2_content="5%")
    res_wt_dec = wt.calculate(events=1.0, ch4_content=0.85, co2_content=0.05)
    assert pytest.approx(res_wt_pct["results"]["ch4"]["value"], rel=1e-4) == res_wt_dec["results"]["ch4"]["value"]

    cs = CoalSeamDrillingCalculator()
    # Percentages with % in CoalSeamDrillingCalculator
    res_cs = cs.calculate(drilling_gas_vented_scf=10000.0, ch4_content="88.7%", co2_content="10.9%")
    assert res_cs["results"]["ch4"]["value"] > 0

    with pytest.raises(ValueError, match="drilling_gas_vented_scf cannot be negative"):
        cs.calculate(drilling_gas_vented_scf=-100.0)

    with pytest.raises(ValueError, match="well_testing_gas_flared_scf cannot be negative"):
        cs.calculate(well_testing_gas_flared_scf=-50.0)
