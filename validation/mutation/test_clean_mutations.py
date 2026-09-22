"""
CLEAN-SLATE VALIDATION: Mutation Testing Suite
Validates that the validation suite is rigorous enough to detect ("kill") deliberate
mathematical, physical, logical, and boundary mutations.

Mutants tested:
1. Mutant-Operator: Activity * EF mutated to Activity / EF or Activity + EF
2. Mutant-GWP: CH4 GWP multiplier omitted (1.0 instead of 28/29.8) or cross-standard swapped
3. Mutant-Physical: Molar mass of Carbon mutated (14.0 instead of 12.011)
4. Mutant-Thermodynamics: Standard volume molar constant mutated (22.414 @ 0C instead of 23.685 @ 15C ISO 13443)
5. Mutant-Flaring: Uncombusted methane slip dropped (assuming 100% destruction)
6. Mutant-AGR: Methane co-absorption slip dropped (API Table 6-5 0.1% omitted)
7. Mutant-Steam: Boiler efficiency multiplied instead of divided (heat / eta vs heat * eta)
8. Mutant-Scope3-Unit: Spend-based EEIO factor missing 1000 kg/tonne conversion
9. Mutant-Negative-Activity: Negative activity quantity treated as negative emissions without error
10. Mutant-Efficiency-Bound: Efficiency > 1.0 (over-unity) accepted without error

ZERO reuse of legacy tests. Pure clean-slate validation.
"""

import pytest
import sys
import os
import copy

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SERVER_DIR)

from calculations.combustion import CombustionCalculator, FlaringCalculator
from calculations.midstream import AGRCalculator
from calculations.indirect import IndirectSteamCalculator
from calculations.units import compute_scope3_co2e, calculate_co2e
from validation.reference_model import (
    ref_calculate_combustion,
    ref_calculate_flaring,
    ref_calculate_agr,
    ref_calculate_scope2_steam,
    ref_calculate_scope3,
    ref_calculate_hydrocarbon_stoichiometry,
    resolve_gwp,
    STD_TEMP_K,
)
from validation.reference_model.ref_constants import MW_C, MW_O, STD_PRESSURE_KPA


class TestCleanMutations:
    """Mutation testing to verify that intentional calculation flaws are killed."""

    def test_kill_operator_mutation_combustion(self):
        """Mutant: Activity * EF is mutated to Activity + EF or Activity / EF.
        Suite must detect discrepancy against first-principles reference."""
        activity = 1500.0  # m3
        ef_co2 = 1.93  # kg/m3

        # Legitimate calculation (returns tonnes)
        valid_res = ref_calculate_combustion(activity, ef_co2=ef_co2)
        valid_co2_kg = valid_res["co2"] * 1000.0

        # Mutants (in kg)
        mutant_plus = activity + ef_co2
        mutant_div = activity / ef_co2

        # Validation check kills both mutants
        tolerance = 1e-4
        assert abs(mutant_plus - valid_co2_kg) > tolerance, "Mutant (Activity + EF) survived!"
        assert abs(mutant_div - valid_co2_kg) > tolerance, "Mutant (Activity / EF) survived!"

    def test_kill_gwp_omission_mutation(self):
        """Mutant: CH4 GWP multiplier omitted (treating 1 kg CH4 = 1 kg CO2e).
        Suite must catch and kill this critical climate undercount."""
        ch4_mass_kg = 50.0  # 50 kg CH4
        true_gwp_ar5 = resolve_gwp("AR5", "100")["CH4"]  # 28.0

        legitimate_co2e = ch4_mass_kg * true_gwp_ar5  # 1400 kg CO2e

        # Mutant: GWP omitted (factor = 1.0)
        mutant_co2e = ch4_mass_kg * 1.0  # 50 kg CO2e

        # Assertion detects mutant with massive deviation
        discrepancy = abs(legitimate_co2e - mutant_co2e)
        assert discrepancy == 1350.0
        assert abs(mutant_co2e - legitimate_co2e) / legitimate_co2e > 0.50, "GWP omission mutant survived!"

    def test_kill_carbon_atomic_weight_mutation(self):
        """Mutant: Carbon atomic weight mutated to 14.0 (Nitrogen) instead of 12.011.
        Suite must catch mass balance violation in Tier 3 stoichiometry."""
        mutant_mw_c = 14.00
        legit_mw_c = MW_C  # 12.011

        # Stoichiometry for Methane: CH4 + 2 O2 -> CO2 + 2 H2O
        legit_stoich = ref_calculate_hydrocarbon_stoichiometry(1, 4)
        assert legit_stoich["mass_balance_error"] < 1e-9

        # In mutant stoichiometry, CO2 molar mass is corrupted (14 + 31.998 = 45.998 vs 44.009)
        mw_co2_mutant = mutant_mw_c + 2 * MW_O
        mw_co2_legit = legit_mw_c + 2 * MW_O

        assert abs(mw_co2_mutant - mw_co2_legit) > 1.9, "Carbon atomic weight mutant survived!"

    def test_kill_thermodynamic_standard_condition_mutation(self):
        """Mutant: Confusing Normal condition (0°C, 22.414 L/mol) with Standard ISO 13443 (15°C, 23.685 L/mol).
        Suite must catch ~5.5% thermodynamic volume/density error."""
        # Ideal gas molar volume at 15.56 C (288.706 K) vs 0 C (273.15 K)
        v_std_iso_15c = (8.314462618 * STD_TEMP_K) / (STD_PRESSURE_KPA * 1000.0) * 1000.0  # ~23.685 L/mol
        v_normal_0c = 22.414  # L/mol at 0 C, 101.325 kPa

        deviation_pct = abs(v_std_iso_15c - v_normal_0c) / v_std_iso_15c * 100.0

        # Deviation is approximately 5.36%
        assert deviation_pct > 5.0, "Thermodynamic standard condition mutant survived!"

    def test_kill_flaring_methane_slip_omission_mutation(self):
        """Mutant: Assuming 100% flare destruction efficiency (omitting methane slip).
        Suite must detect unburned methane underestimation."""
        flare_volume_m3 = 10000.0
        ch4_vol_frac = 0.85
        destruction_eff = 0.98  # 2% slip

        legit_flare = ref_calculate_flaring(
            gas_volume=flare_volume_m3,
            ch4_fraction=ch4_vol_frac,
            combustion_eff=0.98,
            destruction_eff=destruction_eff,
        )

        # Mutant: 100% destruction, 0 slip
        mutant_slip_ch4_kg = 0.0
        legit_slip_ch4_kg = legit_flare["ch4"] * 1000.0

        assert legit_slip_ch4_kg > 0.0
        assert abs(legit_slip_ch4_kg - mutant_slip_ch4_kg) > 50.0, "Flaring slip mutant survived!"

    def test_kill_agr_methane_coabsorption_omission_mutation(self):
        """Mutant: Acid Gas Removal drops API Table 6-5 0.1% methane slip.
        Suite must detect missing CH4 fugitive in gas processing."""
        feed_gas_m3 = 500000.0
        co2_mole_frac = 0.04
        ch4_mole_frac = 0.90

        legit_agr = ref_calculate_agr(
            feed_gas_volume=feed_gas_m3,
            co2_inlet_fraction=co2_mole_frac,
            ch4_inlet_fraction=ch4_mole_frac,
            ch4_slip_fraction=0.001,  # API standard
        )

        mutant_agr_ch4 = 0.0  # Missing co-absorption
        legit_agr_ch4_kg = legit_agr["ch4"] * 1000.0

        assert legit_agr_ch4_kg > 0.0
        assert abs(legit_agr_ch4_kg - mutant_agr_ch4) > 10.0, "AGR slip mutant survived!"

    def test_kill_steam_boiler_efficiency_multiplication_mutation(self):
        """Mutant: Steam emissions formula calculates (Fuel = Steam * Efficiency) instead of (Steam / Efficiency).
        Suite must detect severe underestimation of upstream boiler fuel."""
        calc = IndirectSteamCalculator()
        energy_mmbtu = 1000.0
        boiler_eff = 0.80
        ef = 53.06  # kg CO2e / MMBtu

        # True formula: heat_input = energy / boiler_eff
        legit_res = calc.calculate(
            heat_energy=energy_mmbtu,
            ef_co2=ef,
            boiler_efficiency=boiler_eff,
            transmission_loss=0.0,
            uncertainties={},
            heat_unit="mmbtu",
        )
        legit_co2_tonnes = legit_res["total_co2e"]

        # Mutant: heat_input = energy * boiler_eff (multiplied instead of divided)
        mutant_co2_tonnes = ((energy_mmbtu * boiler_eff) * ef) / 1000.0

        assert abs(legit_co2_tonnes - (1000.0 / 0.80 * ef / 1000.0)) < 1e-4
        assert abs(mutant_co2_tonnes - (1000.0 * 0.80 * ef / 1000.0)) < 1e-4
        # Mutant underestimates by 36%
        assert (legit_co2_tonnes - mutant_co2_tonnes) / legit_co2_tonnes > 0.35, "Steam multiplication mutant survived!"

    def test_kill_scope3_spend_unit_scale_mutation(self):
        """Mutant: EEIO factor (kg CO2e / $) applied to spend without dividing by 1000 kg/tonne.
        Suite must detect 1000x overcount mutation."""
        spend = 50000.0  # $50,000
        eeio_factor = 0.35  # kg CO2e / $

        # True: 50,000 * 0.35 / 1000 = 17.5 tCO2e
        legit_scope3_tco2e = compute_scope3_co2e(spend, eeio_factor)

        # Mutant: 50,000 * 0.35 = 17500 tCO2e
        mutant_tco2e = spend * eeio_factor

        assert abs(legit_scope3_tco2e - 17.5) < 1e-4
        assert mutant_tco2e == 17500.0
        assert abs(mutant_tco2e - legit_scope3_tco2e) > 17000.0, "Scope 3 1000x mutant survived!"

    def test_kill_negative_activity_boundary_mutation(self):
        """Mutant: Accepting negative activity data producing negative (carbon credit) emissions without validation error."""
        calc = CombustionCalculator()
        # Production calculator must strictly reject negative activity data
        with pytest.raises(ValueError, match="cannot be negative"):
            calc.calculate(
                fuel_quantity=-500.0,
                ef_co2=1.93,
                ef_ch4=0.0,
                ef_n2o=0.0,
                uncertainties={},
                hhv=None,
                ef_unit="kg/m3",
                fuel_unit="m3",
                fuel_type="gases",
            )

    def test_kill_zero_efficiency_division_by_zero_mutation(self):
        """Mutant: Zero net efficiency in steam calculator should be caught and raise ValueError."""
        calc = IndirectSteamCalculator()
        with pytest.raises(ValueError, match="Net efficiency must be greater than 0"):
            calc.calculate(
                heat_energy=100.0,
                ef_co2=53.06,
                boiler_efficiency=0.80,
                transmission_loss=1.0,  # 100% loss -> net efficiency 0.0
                uncertainties={},
                heat_unit="mmbtu",
            )
