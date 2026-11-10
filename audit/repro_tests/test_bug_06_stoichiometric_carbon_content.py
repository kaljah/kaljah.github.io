"""
Verification of Remediation: BUG-10 / CALC-03
Stoichiometric calculator correctly rejects carbon_content > 1.0 when '%' is omitted.
"""

import sys
import pytest

sys.path.insert(0, "new/server")

from calculations.stoichiometry import StoichiometricCalculator

def test_stoichiometric_carbon_content_validation():
    calc = StoichiometricCalculator()

    # 1. Bare number > 1.0 must raise ValueError
    with pytest.raises(ValueError, match="carbon_content without '%' must be a fraction between 0 and 1"):
        calc.calculate(fuel_mass=1000.0, carbon_content=1.5, oxidation_factor=1.0)

    # 2. Percentage with '%' is valid
    res_pct = calc.calculate(fuel_mass=1000.0, carbon_content="1.5%", oxidation_factor=1.0)
    expected_pct = 1000.0 * 0.015 * (44.01 / 12.011) / 1000.0
    assert abs(res_pct["results"]["co2"]["value"] - expected_pct) < 1e-4

    # 3. Fraction in [0, 1] is valid
    res_frac = calc.calculate(fuel_mass=1000.0, carbon_content=0.85, oxidation_factor=1.0)
    expected_frac = 1000.0 * 0.85 * (44.01 / 12.011) / 1000.0
    assert abs(res_frac["results"]["co2"]["value"] - expected_frac) < 1e-4
