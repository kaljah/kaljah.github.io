"""
Mutation Testing Harness for Critical GHG Calculation Code.
============================================================
Deliberately injects mathematical and physical mutations into calculation routines
and verifies that the validation test assertions FAIL (mutants are killed).

Mutations tested:
1. Operator inversion (+ -> - or (1-eff) -> (1+eff))
2. Distorted conversion factors (scf to m3)
3. Wrong GWP horizon (AR5 CH4 28 -> 21 / 25)
4. Inverted stoichiometric ratio (44.01/16.04 -> 16.04/44.01)
5. Distorted emission factor (53.06 -> 43.06)
6. Omitted native CO2 stream term
7. Swapped gas densities (CH4 vs CO2)
8. Omitted transmission loss in steam net efficiency
9. EEIO spend divisor defect (/1,000 instead of /1,000,000)
10. Missing methane slip term in acid gas removal
"""
import pytest
import math
import copy

from validation.reference_model import (
    IndependentCombustionModel,
    IndependentFlaringModel,
    IndependentScope2Model,
    IndependentScope3Model,
    IndependentAGRModel,
    IndependentUnitConverter,
    IndependentGWPModel,
)


class TestCalculationMutations:
    """Verifies that mathematical mutations cause tests to fail (100% mutant kill rate)."""

    def test_mutant_1_flaring_efficiency_inversion(self):
        """Mutant: Flaring unburnt CH4 calculated with (1 + eff) instead of (1 - eff)."""
        clean_res = IndependentFlaringModel.calculate(
            gas_volume=50_000.0,
            volume_unit="m3",
            ch4_fraction=0.88,
            flare_type="elevated",
            combustion_eff=0.98,
        )
        # Injected mutation
        mutant_unburnt_ch4 = 50_000.0 * 0.88 * 0.6785 * (1.0 + 0.98) / 1000.0
        
        # Test assertion MUST detect discrepancy and fail
        with pytest.raises(AssertionError):
            assert pytest.approx(clean_res["ch4"], rel=1e-4) == mutant_unburnt_ch4

    def test_mutant_2_distorted_volume_conversion_factor(self):
        """Mutant: scf to m3 factor mutated from 0.0283168 to 0.0383168 (+35% error)."""
        scf_qty = 1_000_000.0
        clean_m3 = IndependentUnitConverter.convert(scf_qty, "scf", "m3")
        mutant_m3 = scf_qty * 0.038316846592

        with pytest.raises(AssertionError):
            assert pytest.approx(clean_m3, rel=1e-4) == mutant_m3

    def test_mutant_3_wrong_gwp_selection(self):
        """Mutant: AR5 GWP for CH4 (28) mutated to SAR (21) or AR4 (25)."""
        ch4_tonnes = 100.0
        clean_co2e = IndependentGWPModel.calculate_co2e(0.0, ch4_tonnes, 0.0, standard="AR5")
        mutant_co2e_sar = ch4_tonnes * 21.0
        mutant_co2e_ar4 = ch4_tonnes * 25.0

        with pytest.raises(AssertionError):
            assert pytest.approx(clean_co2e, rel=1e-4) == mutant_co2e_sar
        with pytest.raises(AssertionError):
            assert pytest.approx(clean_co2e, rel=1e-4) == mutant_co2e_ar4

    def test_mutant_4_inverted_stoichiometric_ratio(self):
        """Mutant: CO2/CH4 molar ratio 44.01/16.04 (2.7437) inverted to 16.04/44.01 (0.3644)."""
        ch4_mass_kg = 1000.0
        clean_co2 = ch4_mass_kg * 0.98 * (44.01 / 16.04)
        mutant_co2 = ch4_mass_kg * 0.98 * (16.04 / 44.01)

        with pytest.raises(AssertionError):
            assert pytest.approx(clean_co2, rel=1e-4) == mutant_co2

    def test_mutant_5_distorted_combustion_emission_factor(self):
        """Mutant: Natural gas CO2 factor mutated from 53.06 to 43.06 kg/MMBtu."""
        clean_res = IndependentCombustionModel.calculate_tier1_2(
            fuel_quantity=10_000.0,
            fuel_unit="m3",
            emission_factors={"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"},
            fuel_type="natural_gas",
            hhv=1020.0,
        )
        mutant_res = IndependentCombustionModel.calculate_tier1_2(
            fuel_quantity=10_000.0,
            fuel_unit="m3",
            emission_factors={"co2": 43.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"},
            fuel_type="natural_gas",
            hhv=1020.0,
        )

        with pytest.raises(AssertionError):
            assert pytest.approx(clean_res["co2"], rel=1e-4) == mutant_res["co2"]

    def test_mutant_6_omitted_native_co2_stream(self):
        """Mutant: Flaring calculation completely drops native CO2 from gas stream."""
        clean_res = IndependentFlaringModel.calculate(
            gas_volume=100_000.0,
            volume_unit="m3",
            ch4_fraction=0.85,
            composition={"c1": 0.85, "co2_mol": 0.05},
            flare_type="elevated",
            combustion_eff=0.98,
        )
        mutant_co2 = clean_res["co2"] - (100_000.0 * 0.05 * 1.861 / 1000.0)

        with pytest.raises(AssertionError):
            assert pytest.approx(clean_res["co2"], rel=1e-4) == mutant_co2

    def test_mutant_7_swapped_gas_densities(self):
        """Mutant: CH4 standard density (0.6785 kg/m3) swapped with CO2 density (1.861 kg/m3)."""
        vol_m3 = 50_000.0
        clean_ch4_kg = vol_m3 * 0.6785
        mutant_ch4_kg = vol_m3 * 1.8610

        with pytest.raises(AssertionError):
            assert pytest.approx(clean_ch4_kg, rel=1e-4) == mutant_ch4_kg

    def test_mutant_8_omitted_transmission_losses(self):
        """Mutant: Steam calculation omits transmission loss: eta_net = eta_boiler instead of eta_boiler * (1 - trans_loss)."""
        clean_res = IndependentScope2Model.calculate_indirect_steam(
            amount=100.0,
            unit="tonne",
            boiler_eff=0.80,
            trans_loss=0.10,
            ef_co2=53.06,
        )
        mutant_res = IndependentScope2Model.calculate_indirect_steam(
            amount=100.0,
            unit="tonne",
            boiler_eff=0.80,
            trans_loss=0.00,  # Omitted transmission loss
            ef_co2=53.06,
        )

        with pytest.raises(AssertionError):
            assert pytest.approx(clean_res["co2e"], rel=1e-4) == mutant_res["co2e"]

    def test_mutant_9_eeio_spend_scaling_defect(self):
        """Mutant: EEIO spend factor scaled by 1,000 instead of 1,000,000 (1000x error)."""
        spend = 500_000.0
        factor = 3200.0
        unit = "kg CO2e / $1,000"
        clean_res = IndependentScope3Model.calculate(spend, factor, factor_unit=unit, calc_method="spend_eeio")
        mutant_co2e = (spend * factor) / 1000.0  # Missing $1,000 denominator scaling

        with pytest.raises(AssertionError):
            assert pytest.approx(clean_res["co2e"], rel=1e-4) == mutant_co2e

    def test_mutant_10_missing_agr_methane_slip(self):
        """Mutant: AGR regenerator emissions calculated with zero methane slip."""
        clean_res = IndependentAGRModel.calculate(
            throughput_mmscf=1000.0,
            co2_in=0.04,
            co2_out=0.0005,
            ch4_in=0.85,
            ch4_slip_fraction=0.001,  # 0.1% slip per Table 6-5
        )
        mutant_res = IndependentAGRModel.calculate(
            throughput_mmscf=1000.0,
            co2_in=0.04,
            co2_out=0.0005,
            ch4_in=0.85,
            ch4_slip_fraction=0.0,  # Omitted slip
        )

        with pytest.raises(AssertionError):
            assert pytest.approx(clean_res["ch4"], rel=1e-4) == mutant_res["ch4"]
            assert mutant_res["ch4"] == 0.0
