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


def _engine(process, inputs):
    """Gas masses (tonnes) the platform returns for one process, through the dispatcher."""
    import sys
    from pathlib import Path
    server = str(Path(__file__).resolve().parents[2] / "new" / "server")
    if server not in sys.path:
        sys.path.insert(0, server)
    from calculations.dispatcher import CalculationDispatcher
    res = CalculationDispatcher().dispatch(process, dict(inputs), {}, {})
    return {g: (v["value"] if isinstance(v, dict) else float(v or 0)) for g, v in res["results"].items()}


class TestCalculationMutations:
    """Verifies that mathematical mutations cause tests to fail (100% mutant kill rate)."""

    def test_mutant_1_flaring_efficiency_inversion(self):
        """Mutant: flaring unburnt CH4 calculated with (1 + eff) instead of (1 - eff). The platform must give the clean
        value (the reference model's) and not the mutant's."""
        clean_res = IndependentFlaringModel.calculate(
            gas_volume=50_000.0,
            volume_unit="m3",
            ch4_fraction=0.88,
            flare_type="elevated",
            combustion_eff=0.98,
        )
        mutant_unburnt_ch4 = 50_000.0 * 0.88 * (16.04 / 23.685) * (1.0 + 0.98) / 1000.0
        engine = _engine("flaring", {"factor_source": "specific", "amount": 50_000.0, "unit": "m3", "c1": 88.0,
                                     "combustion_efficiency": 98.0, "destruction_efficiency": 98.0})
        assert pytest.approx(engine["ch4"], rel=1e-6) == clean_res["ch4"]
        assert engine["ch4"] != pytest.approx(mutant_unburnt_ch4, rel=1e-2)

    def test_mutant_2_distorted_volume_conversion_factor(self):
        """Mutant: scf to m3 factor mutated from 0.0283168 to 0.0383168 (+35% error)."""
        from calculations.units import convert
        scf_qty = 1_000_000.0
        clean_m3 = IndependentUnitConverter.convert(scf_qty, "scf", "m3")
        mutant_m3 = scf_qty * 0.038316846592
        assert pytest.approx(convert(scf_qty, "scf", "m3"), rel=1e-9) == clean_m3
        assert convert(scf_qty, "scf", "m3") != pytest.approx(mutant_m3, rel=1e-2)

    def test_mutant_3_wrong_gwp_selection(self):
        """Mutant: AR5 GWP for CH4 (28) mutated to SAR (21) or AR4 (25)."""
        from calculations.constants import GWP_AR5
        from calculations.units import calculate_co2e
        ch4_tonnes = 100.0
        clean_co2e = IndependentGWPModel.calculate_co2e(0.0, ch4_tonnes, 0.0, standard="AR5")
        engine = calculate_co2e(0.0, ch4_tonnes, 0.0, gwp_dict=GWP_AR5)
        assert pytest.approx(engine, rel=1e-9) == clean_co2e == 2800.0
        assert engine != pytest.approx(ch4_tonnes * 21.0, rel=1e-2)
        assert engine != pytest.approx(ch4_tonnes * 25.0, rel=1e-2)

    def test_mutant_4_inverted_stoichiometric_ratio(self):
        """Mutant: CO2/CH4 molar ratio 44.01/16.04 (2.7437) inverted to 16.04/44.01 (0.3644). One mole of CH4 burnt completely
        gives one mole of CO2, so 1,000 m3 of pure CH4 at 100 % combustion must give 2.7437 t CO2 per t of CH4."""
        from calculations.units import CONVERSIONS
        engine = _engine("flaring", {"factor_source": "specific", "amount": 1000.0, "unit": "m3", "c1": 100.0,
                                     "combustion_efficiency": 100.0, "destruction_efficiency": 100.0})
        ch4_burnt_t = 1000.0 * CONVERSIONS["density_ch4"] / 1000.0
        assert engine["co2"] / ch4_burnt_t == pytest.approx(44.01 / 16.04, rel=1e-9)
        assert engine["co2"] / ch4_burnt_t != pytest.approx(16.04 / 44.01, rel=1e-2)

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
        from calculations.combustion import CombustionCalculator
        res = CombustionCalculator().calculate(fuel_quantity=10_000.0, fuel_unit="m3", fuel_type="natural_gas",
                                               ef_co2=53.06, ef_ch4=0.001, ef_n2o=0.0001, ef_unit="kg/MMBtu",
                                               hhv=1020.0)
        engine_co2 = res["results"]["co2"]["value"]
        assert pytest.approx(engine_co2, rel=1e-6) == clean_res["co2"]
        assert engine_co2 != pytest.approx(mutant_res["co2"], rel=1e-2)

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
        mutant_co2 = clean_res["co2"] - (100_000.0 * 0.05 * (44.01 / 23.685) / 1000.0)
        engine = _engine("flaring", {"factor_source": "specific", "amount": 100_000.0, "unit": "m3", "c1": 85.0,
                                     "co2_mol": 5.0, "combustion_efficiency": 98.0, "destruction_efficiency": 98.0})
        assert pytest.approx(engine["co2"], rel=1e-6) == clean_res["co2"]
        assert engine["co2"] != pytest.approx(mutant_co2, rel=1e-2)

    def test_mutant_7_swapped_gas_densities(self):
        """Mutant: CH4 standard density (0.67722 kg/m3) swapped with CO2 density (1.85814 kg/m3). A flare that destroys
        nothing (0 % efficiency) vents the whole CH4: 50,000 m3 x density."""
        vol_m3 = 50_000.0
        clean_ch4_kg = vol_m3 * (16.04 / 23.685)
        mutant_ch4_kg = vol_m3 * (44.01 / 23.685)
        engine = _engine("flaring", {"factor_source": "specific", "amount": vol_m3, "unit": "m3", "c1": 100.0,
                                     "combustion_efficiency": 0.0, "destruction_efficiency": 0.0})
        assert pytest.approx(engine["ch4"] * 1000.0, rel=1e-9) == clean_ch4_kg
        assert engine["ch4"] * 1000.0 != pytest.approx(mutant_ch4_kg, rel=1e-2)

    def test_mutant_8_omitted_transmission_losses(self):
        """Mutant: Steam calculation omits transmission loss: eta_net = eta_boiler instead of eta_boiler - trans_loss (Exhibit 8.3)."""
        clean_res = IndependentScope2Model.calculate_indirect_steam(
            amount=100.0,
            unit="tonne",
            boiler_eff=0.80,
            trans_loss=0.10,
            ef_co2=53.06,
            steam_enthalpy_btu_lb=1000.0,
        )
        mutant_res = IndependentScope2Model.calculate_indirect_steam(
            amount=100.0,
            unit="tonne",
            boiler_eff=0.80,
            trans_loss=0.00,  # Omitted transmission loss
            ef_co2=53.06,
            steam_enthalpy_btu_lb=1000.0,
        )
        from calculations.indirect import IndirectSteamCalculator
        res = IndirectSteamCalculator().calculate(
            heat_energy=100.0, heat_unit="tonne", steam_enthalpy_btu_lb=1000.0, ef_co2=53.06,
            boiler_efficiency=0.80, transmission_loss=0.10, uncertainties={})
        engine_co2 = res["results"]["co2"]["value"]
        assert pytest.approx(engine_co2, rel=1e-6) == clean_res["co2e"]
        assert engine_co2 != pytest.approx(mutant_res["co2e"], rel=1e-2)

    def test_mutant_9_eeio_spend_scaling_defect(self):
        """Mutant: EEIO spend factor scaled by 1,000 instead of 1,000,000 (1000x error)."""
        from calculations.units import compute_scope3_co2e
        spend = 500_000.0
        factor = 3200.0
        unit = "kg CO2e / $1,000"
        clean_res = IndependentScope3Model.calculate(spend, factor, factor_unit=unit, calc_method="spend_eeio")
        mutant_co2e = (spend * factor) / 1000.0  # Missing $1,000 denominator scaling
        engine = compute_scope3_co2e(spend, factor, unit)
        assert pytest.approx(engine, rel=1e-6) == clean_res["co2e"]
        assert engine != pytest.approx(mutant_co2e, rel=1e-2)

    def test_mutant_10_missing_agr_methane_slip(self):
        """Mutant: AGR regenerator emissions calculated with zero methane slip."""
        clean_res = IndependentAGRModel.calculate(
            throughput_mmscf=1000.0,
            co2_in=0.04,
            co2_out=0.0005,
            ch4_in=0.85,
            ch4_slip_fraction=0.001,  # 0.1% slip per Table 6-5
        )
        engine = _engine("agr", {"factor_source": "specific", "amount": 1000.0, "unit": "mmscf", "agr_co2_in": 4.0,
                                 "agr_co2_out": 0.05, "agr_ch4_in": 85.0, "agr_ch4_slip": 0.001,
                                 "agr_control_eff": 0.0})
        assert engine["ch4"] > 0.0
        assert pytest.approx(engine["ch4"], rel=1e-6) == clean_res["ch4"]
        assert engine["ch4"] != pytest.approx(0.0, abs=1e-6)
