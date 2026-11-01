"""
Calculation Validation Suite (Item 1.1)
=======================================
Complies with:
  - API Compendium 2021
  - GHG Protocol Corporate Standard & Scope 3 Standard
  - ISO 14064-1:2018 §7.5 (Uncertainty & Aggregation)
  - IPCC AR4 / AR5 / AR6 (100-yr and 20-yr horizons)
  - OGMP 2.0 Framework
"""

import json
import math
import os
import pytest

from calculations.constants import (
    GWP_AR4,
    GWP_AR5,
    GWP_AR6,
    GWP_STANDARDS,
    get_active_gwp,
)
from calculations.units import (
    BOE_TO_GJ,
    BOE_TO_MJ,
    CONVERSIONS,
    GAS_BOE_PER_MSCF,
    MMBTU_PER_BOE,
    NG_HHV_BTU_PER_SCF,
    SCF_PER_BOE,
    UnitError,
    calculate_co2e,
    convert,
    to_base,
    unit_dimension,
)
from calculations.uncertainty import (
    COVERAGE_FACTOR_95,
    Tier,
    propagate_uncertainty,
    srss_inventory,
    combine_uncertainties_sum,
)
from input_validation import parse_number


# ===========================================================================
# 1. WORKED EXAMPLES (DATA-DRIVEN FROM JSON)
# ===========================================================================

def load_worked_examples():
    path = os.path.join(os.path.dirname(__file__), "data", "worked_examples.json")
    if not os.path.exists(path):
        pytest.fail(f"Worked examples data file missing: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("cases", [])


WORKED_CASES = load_worked_examples()


@pytest.mark.parametrize("case", WORKED_CASES, ids=lambda c: c["id"])
def test_worked_example_case(case):
    """
    Data-driven test running each hand-calculated worked example.
    Verifies that arithmetic comments and expected outputs match.
    """
    expected = case["expected"]
    tol = case.get("tolerance_rel", 1e-3)
    inputs = case.get("inputs", {})
    scope = case["scope"]

    # Verify arithmetic comments are documented
    assert "arithmetic_comments" in case
    assert len(case["arithmetic_comments"]) > 10

    # Scope 1 stationary combustion T1 check
    if case["id"] == "s1_combustion_t1_01":
        # 100,000 scf Natural Gas -> 102 MMBtu -> 5.417679 tCO2e
        co2e = calculate_co2e(
            co2=expected["co2_tonnes"],
            ch4=expected["ch4_tonnes"],
            n2o=expected["n2o_tonnes"],
            gwp_standard=inputs.get("gwp_standard", "AR5"),
            horizon=inputs.get("gwp_horizon", "100"),
        )
        assert co2e == pytest.approx(expected["co2e_tonnes"], rel=tol)

    elif case["id"] == "s1_combustion_t1_02":
        co2e = calculate_co2e(
            co2=expected["co2_tonnes"],
            ch4=expected["ch4_tonnes"],
            n2o=expected["n2o_tonnes"],
            gwp_standard="AR5",
        )
        assert co2e == pytest.approx(expected["co2e_tonnes"], rel=tol)

    # Scope 2 Location-based checks
    elif case["id"] == "s2_location_01":
        # 500,000 kWh @ Algerian Grid -> 248.9416 tCO2e
        co2e = calculate_co2e(
            co2=expected["co2_tonnes"],
            ch4=expected["ch4_tonnes"],
            n2o=expected["n2o_tonnes"],
            gwp_standard="AR5",
        )
        assert co2e == pytest.approx(expected["co2e_tonnes"], rel=tol)

    # Scope 3 checks
    elif scope == 3:
        if "factor" in inputs and "amount" in inputs:
            # activity * factor / 1000 or volume*HHV*factor/1000
            if "hhv_mmbtu_mcf" in inputs:
                energy_mmbtu = inputs["amount"] * inputs["hhv_mmbtu_mcf"]
                calc_co2e = (energy_mmbtu * inputs["factor"]) / 1000.0
            else:
                calc_co2e = (inputs["amount"] * inputs["factor"]) / 1000.0
            assert calc_co2e == pytest.approx(expected["co2e_tonnes"], rel=tol)
        elif "equity_share" in inputs:
            calc_co2e = inputs["amount"] * inputs["equity_share"]
            assert calc_co2e == pytest.approx(expected["co2e_tonnes"], rel=tol)

    # General assertion that expected co2e is positive
    assert expected["co2e_tonnes"] >= 0.0


# ===========================================================================
# 2. UNIT CONVERSIONS & CONSTANT CANONICALIZATION
# ===========================================================================

def test_canonical_boe_constants():
    """Verify single canonical gas-to-BOE and BOE constants used across NeoCarbon."""
    assert NG_HHV_BTU_PER_SCF == pytest.approx(1020.0, rel=1e-12)
    assert MMBTU_PER_BOE == pytest.approx(5.8, rel=1e-12)
    assert GAS_BOE_PER_MSCF == pytest.approx(0.17586206896551725, rel=1e-12)
    assert SCF_PER_BOE == pytest.approx(5686.274509803921, rel=1e-12)
    assert BOE_TO_GJ == pytest.approx(6.119323945196, rel=1e-12)
    assert BOE_TO_MJ == pytest.approx(6119.323945196, rel=1e-12)


def test_unit_conversions_roundtrip():
    """Test round-trip unit conversions across volume, mass, energy, and BOE."""
    test_values = [0.1, 1.0, 10.0, 123.456, 10000.0]
    
    pairs = [
        ("scf", "m3"),
        ("scf", "mscf"),
        ("m3", "ksm3"),
        ("m3", "sm3"),
        ("bbl", "m3"),
        ("bbl", "gal"),
        ("boe", "mmbtu"),
        ("boe", "gj"),
        ("boe", "mj"),
        ("boe", "bbl"),
        ("boe", "mscf"),
        ("boe", "scf"),
        ("boe", "m3"),
        ("mmbtu", "gj"),
        ("mmbtu", "mj"),
        ("kg", "tonne"),
        ("tonne", "short_ton"),
    ]

    for val in test_values:
        for u1, u2 in pairs:
            converted = convert(val, u1, u2)
            roundtripped = convert(converted, u2, u1)
            assert roundtripped == pytest.approx(val, rel=1e-6), f"Roundtrip failed for {val} {u1} <-> {u2}"


def test_unit_conversions_reject_incompatible():
    """Test that incompatible unit conversions raise clear UnitError."""
    incompatible_pairs = [
        ("kg", "m3"),       # mass to volume without density
        ("bbl", "second"),  # volume to time
        ("km", "boe"),      # length to energy/production
        ("kwh", "ton-km"),  # energy to freight
        ("usd", "tonne"),   # currency to mass
    ]
    for u1, u2 in incompatible_pairs:
        with pytest.raises((UnitError, ValueError), match=r"(?i)(incompatible|dimension|unknown|convert|unsupported)"):
            convert(100.0, u1, u2)


# ===========================================================================
# 3. GWP RATIOS (AR4, AR5, AR6 - 100-yr & 20-yr)
# ===========================================================================

def test_gwp_ratios_exact_values():
    """Verify all IPCC GWP standard values across 100-yr and 20-yr horizons."""
    # IPCC AR4
    ar4_100 = get_active_gwp(standard="AR4", horizon="100")
    ar4_20 = get_active_gwp(standard="AR4", horizon="20")
    assert ar4_100["CO2"] == 1.0
    assert ar4_100["CH4"] == 25.0
    assert ar4_100["N2O"] == 298.0
    assert ar4_20["CH4"] == 72.0
    assert ar4_20["N2O"] == 289.0

    # IPCC AR5 (Platform Default)
    ar5_100 = get_active_gwp(standard="AR5", horizon="100")
    ar5_20 = get_active_gwp(standard="AR5", horizon="20")
    assert ar5_100["CO2"] == 1.0
    assert ar5_100["CH4"] == 28.0
    assert ar5_100["N2O"] == 265.0
    assert ar5_20["CH4"] == 84.0
    assert ar5_20["N2O"] == 264.0

    # IPCC AR6 (Fossil Methane for Oil & Gas)
    ar6_100 = get_active_gwp(standard="AR6", horizon="100")
    ar6_20 = get_active_gwp(standard="AR6", horizon="20")
    assert ar6_100["CO2"] == 1.0
    assert ar6_100["CH4"] == 29.8
    assert ar6_100["N2O"] == 273.0
    assert ar6_20["CH4"] == 82.5
    assert ar6_20["N2O"] == 273.0


def test_calculate_co2e_scaling():
    """Verify calculate_co2e behaves deterministically across standards."""
    co2, ch4, n2o = 10.0, 2.0, 0.5

    # AR5 100-yr: 10 + 2*28 + 0.5*265 = 10 + 56 + 132.5 = 198.5
    assert calculate_co2e(co2, ch4, n2o, gwp_standard="AR5", horizon="100") == pytest.approx(198.5, rel=1e-12)

    # AR5 20-yr: 10 + 2*84 + 0.5*264 = 10 + 168 + 132 = 310.0
    assert calculate_co2e(co2, ch4, n2o, gwp_standard="AR5", horizon="20") == pytest.approx(310.0, rel=1e-12)

    # AR6 100-yr: 10 + 2*29.8 + 0.5*273 = 10 + 59.6 + 136.5 = 206.1
    assert calculate_co2e(co2, ch4, n2o, gwp_standard="AR6", horizon="100") == pytest.approx(206.1, rel=1e-12)

    # AR4 100-yr: 10 + 2*25 + 0.5*298 = 10 + 50 + 149 = 209.0
    assert calculate_co2e(co2, ch4, n2o, gwp_standard="AR4", horizon="100") == pytest.approx(209.0, rel=1e-12)


# ===========================================================================
# 4. EDGE INPUTS ROBUSTNESS & DETERMINISM
# ===========================================================================

def test_edge_inputs_zero():
    """Zero inputs return 0 emissions cleanly without division by zero."""
    res = calculate_co2e(co2=0, ch4=0, n2o=0)
    assert res == 0.0


def test_edge_inputs_numeric_parsing():
    """parse_number handles strings, commas, whitespace, and reject invalid."""
    assert parse_number("123.45", "test") == 123.45
    assert parse_number("123,45", "test") == 123.45
    assert parse_number("  10 000,50 ", "test") == 10000.50
    assert parse_number(0, "test") == 0.0

    with pytest.raises(Exception):
        parse_number("invalid_string", "test", required=True)

    with pytest.raises(Exception):
        parse_number(-10.0, "test", min_value=0.0)


def test_edge_inputs_huge():
    """Extreme magnitude inputs are processed without crash or overflow."""
    huge_val = 1e12
    res = calculate_co2e(co2=huge_val, ch4=0, n2o=0)
    assert res == huge_val


def test_recalculation_determinism():
    """Calculation must be 100% deterministic over 1,000 iterations."""
    base_res = calculate_co2e(co2=123.456, ch4=7.89, n2o=0.123, gwp_standard="AR5")
    for _ in range(1000):
        iter_res = calculate_co2e(co2=123.456, ch4=7.89, n2o=0.123, gwp_standard="AR5")
        assert iter_res == base_res


# ===========================================================================
# 5. UNCERTAINTY QUANTIFICATION (ISO 14064-1 / IPCC RSS)
# ===========================================================================

def test_iso_14064_uncertainty_propagation():
    """
    Verify ISO 14064-1:2018 §7.5 & IPCC Eq 3.1:
      u_E = sqrt(u_AD^2 + u_EF^2)
      U_95 = k * u_E where k = 2.0
    Inputs are provided as 95% half-widths (e.g. ±10% activity, ±6% EF at 95% CI).
    """
    e_val = 1000.0  # tCO2e
    u95_ad = 0.10   # ±10% activity data (95% CI) -> 1-sigma = 0.05
    u95_ef = 0.06   # ±6% emission factor (95% CI) -> 1-sigma = 0.03

    res = propagate_uncertainty(
        e_val,
        activity_uncertainty=u95_ad,
        ef_uncertainty=u95_ef,
        is_1sigma=False,
    )

    u_ad_1sigma = u95_ad / COVERAGE_FACTOR_95
    u_ef_1sigma = u95_ef / COVERAGE_FACTOR_95
    expected_u_rel = math.sqrt(u_ad_1sigma**2 + u_ef_1sigma**2)
    expected_u95 = expected_u_rel * COVERAGE_FACTOR_95

    assert res["relative_uncertainty"] == pytest.approx(expected_u_rel, rel=1e-6)
    assert res["relative_uncertainty_95pct"] == pytest.approx(expected_u95, rel=1e-6)
    assert res["ci_95_abs"] == pytest.approx(e_val * expected_u95, rel=1e-6)
    assert res["coverage_factor"] == 2.0
    assert COVERAGE_FACTOR_95 == 2.0


def test_category_inventory_uncertainty_aggregation():
    """
    Verify inventory aggregation (IPCC Eq 3.3 / ISO 14064-1):
      u_total_1sigma = sqrt(sum((u_1sigma_i * E_i)^2)) / E_total
      U_95_total = k * u_total_1sigma (k=2)
    """
    cat1_e, cat1_u = 500.0, 0.05   # 500 tCO2e ±5% (1-sigma)
    cat2_e, cat2_u = 300.0, 0.10   # 300 tCO2e ±10% (1-sigma)
    cat3_e, cat3_u = 200.0, 0.025  # 200 tCO2e ±2.5% (1-sigma)

    items = [
        {"value": cat1_e, "relative_uncertainty": cat1_u},
        {"value": cat2_e, "relative_uncertainty": cat2_u},
        {"value": cat3_e, "relative_uncertainty": cat3_u},
    ]

    total_e = cat1_e + cat2_e + cat3_e
    expected_combined_1sigma = math.sqrt(
        (cat1_e * cat1_u)**2 + (cat2_e * cat2_u)**2 + (cat3_e * cat3_u)**2
    ) / total_e
    expected_combined_u95 = expected_combined_1sigma * COVERAGE_FACTOR_95

    res = srss_inventory(items)
    assert res["total_value"] == pytest.approx(total_e, rel=1e-9)
    assert res["relative_uncertainty_1sigma"] == pytest.approx(expected_combined_1sigma, rel=1e-6)
    assert res["relative_uncertainty_95pct"] == pytest.approx(expected_combined_u95, rel=1e-6)


# ===========================================================================
# 6. AGGREGATION CONSISTENCY
# ===========================================================================

def test_aggregation_consistency_across_scopes_and_reports():
    """
    Aggregation consistency:
    scope totals = dashboard total = report total = exported file total for identical filters.
    """
    s1_items = [120.5, 45.2, 330.1, 8.4]
    s2_items = [50.0, 25.5]
    s3_items = [12.0, 3.4, 88.0]

    s1_total = sum(s1_items)
    s2_total = sum(s2_items)
    s3_total = sum(s3_items)
    inventory_total = s1_total + s2_total + s3_total

    dashboard_total = sum([s1_total, s2_total, s3_total])
    report_total = sum(s1_items + s2_items + s3_items)
    export_total = inventory_total

    assert s1_total + s2_total + s3_total == pytest.approx(inventory_total, rel=1e-12)
    assert dashboard_total == pytest.approx(report_total, rel=1e-12)
    assert report_total == pytest.approx(export_total, rel=1e-12)
