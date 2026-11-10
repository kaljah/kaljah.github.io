"""
Reproduction Test: BUG-05 / CALC-05
Indirect steam net efficiency uses subtraction (b_eff - t_loss) instead of multiplication
in new/server/calculations/indirect.py:95
When transmission_loss >= boiler_efficiency, net efficiency is zero or negative and raises ValueError,
even though physical net efficiency is strictly positive (b_eff * (1 - t_loss)).
"""

import sys
import pytest

sys.path.insert(0, "new/server")

from calculations.indirect import IndirectSteamCalculator

def test_indirect_net_efficiency_subtraction_bug():
    calc = IndirectSteamCalculator()

    # Case 1: boiler_efficiency = 0.50 (50%), transmission_loss = 0.50 (50%)
    # Thermodynamically valid: Steam is generated at 50% efficiency, and 50% reaches consumer
    # Physical net efficiency = 0.50 * (1 - 0.50) = 0.25 (25%)
    # But app calculates net_efficiency = 0.50 - 0.50 = 0.0, raising ValueError
    with pytest.raises(ValueError) as excinfo:
        calc.calculate(
            heat_energy=100.0,
            heat_unit="mmbtu",
            ef_co2=53.06,
            boiler_efficiency=0.50,
            transmission_loss=0.50,
            uncertainties={}
        )

    assert "Net efficiency must be greater than 0" in str(excinfo.value)
    print("Confirmed: App falsely rejected physical system with net_efficiency = 0.0:", excinfo.value)

    # Case 2: boiler_efficiency = 0.80, transmission_loss = 0.10
    # Thermodynamic net efficiency = 0.80 * 0.90 = 0.72 -> Fuel = 100 / 0.72 = 138.89 MMBtu
    # App net efficiency = 0.80 - 0.10 = 0.70 -> Fuel = 100 / 0.70 = 142.86 MMBtu (~2.86% systematic error)
    res = calc.calculate(
        heat_energy=100.0,
        heat_unit="mmbtu",
        ef_co2=53.06,
        boiler_efficiency=0.80,
        transmission_loss=0.10,
        uncertainties={}
    )
    actual_co2 = res["results"]["co2"]["value"]
    # 100 / 0.70 * 53.06 / 1000 = 7.5800 tonnes
    # expected 100 / 0.72 * 53.06 / 1000 = 7.3694 tonnes
    assert abs(actual_co2 - 7.5800) < 0.01, f"Expected subtractive 7.5800t, got {actual_co2}"
    print(f"Confirmed: App calculated {actual_co2:.4f}t (subtractive 0.70) instead of 7.3694t (multiplicative 0.72)")
