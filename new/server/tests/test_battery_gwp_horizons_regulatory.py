"""
Battery 5: GWP Horizons & Regulatory Standards Battery.
======================================================
Verifies multi-standard regulatory accounting:
1. GWP 20-Year vs 100-Year Horizons across IPCC AR4, AR5, and AR6.
2. Short-term methane climate forcing multiplier (20-yr vs 100-yr impact).
3. Physical Gas Mass Invariance under GWP transformation.
4. Custom GWP Dictionary Override Handling.
5. Flaring CH4 slip sensitivity under 20-yr vs 100-yr horizons.
"""
import pytest
import sys
from pathlib import Path

repo_root = str(Path(__file__).resolve().parents[3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from calculations.constants import get_active_gwp, GWP_AR4, GWP_AR5, GWP_AR6
from calculations.units import calculate_co2e
from calculations.combustion import CombustionCalculator, FlaringCalculator
from calculations.dispatcher import CalculationDispatcher


@pytest.fixture
def dispatcher():
    return CalculationDispatcher()


class TestGWPHorizonsAndProfilesBattery:
    """Verifies IPCC Assessment Report GWP horizons and factor resolution."""

    @pytest.mark.parametrize("std, horizon, exp_ch4, exp_n2o", [
        ("AR4", "100", 25.0, 298.0),
        ("AR4", "20",  72.0, 289.0),
        ("AR5", "100", 28.0, 265.0),
        ("AR5", "20",  82.5, 268.0),
        ("AR6", "100", 27.9, 273.0),
        ("AR6", "20",  82.5, 273.0),
    ])
    def test_gwp_profile_resolution(self, std, horizon, exp_ch4, exp_n2o):
        gwp = get_active_gwp(standard=std, horizon=horizon)
        assert gwp["CO2"] == 1.0
        assert gwp["CH4"] == exp_ch4
        assert gwp["N2O"] == exp_n2o

    def test_methane_short_term_forcing_multiplier(self):
        """
        Methane emissions under 20-year horizon reflect immediate near-term warming impact.
        For AR5: 82.5 / 28.0 = 2.9464x increase in reported CO2e.
        """
        ch4_mass_tonnes = 50.0

        gwp_100 = get_active_gwp("AR5", horizon="100")
        co2e_100 = calculate_co2e(ch4=ch4_mass_tonnes, gwp_dict=gwp_100)

        gwp_20 = get_active_gwp("AR5", horizon="20")
        co2e_20 = calculate_co2e(ch4=ch4_mass_tonnes, gwp_dict=gwp_20)

        assert co2e_100 == 50.0 * 28.0  # 1,400.0 tonnes CO2e
        assert co2e_20 == 50.0 * 82.5   # 4,125.0 tonnes CO2e
        assert pytest.approx(co2e_20 / co2e_100, rel=1e-5) == (82.5 / 28.0)

    def test_physical_gas_mass_invariance_across_gwp_profiles(self, dispatcher):
        """
        Changing GWP profile (AR4 vs AR5 vs AR6 vs 20-yr) must NEVER alter physical gas masses
        (metric tonnes of CO2, CH4, N2O produced).
        """
        payload = {"quantity": 100000.0, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0}
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}

        res_ar4 = dispatcher.dispatch("stationary_combustion", payload, ef, {}, gwp_dict=get_active_gwp("AR4"))
        res_ar5 = dispatcher.dispatch("stationary_combustion", payload, ef, {}, gwp_dict=get_active_gwp("AR5"))
        res_ar6_20 = dispatcher.dispatch("stationary_combustion", payload, ef, {}, gwp_dict=get_active_gwp("AR6", horizon="20"))

        # Physical gas masses MUST be bit-for-bit identical
        assert res_ar4["results"]["co2"]["value"] == res_ar5["results"]["co2"]["value"] == res_ar6_20["results"]["co2"]["value"]
        assert res_ar4["results"]["ch4"]["value"] == res_ar5["results"]["ch4"]["value"] == res_ar6_20["results"]["ch4"]["value"]
        assert res_ar4["results"]["n2o"]["value"] == res_ar5["results"]["n2o"]["value"] == res_ar6_20["results"]["n2o"]["value"]

        # Only total_co2e differs
        assert res_ar4["total_co2e"] != res_ar5["total_co2e"]
        assert res_ar5["total_co2e"] != res_ar6_20["total_co2e"]

    def test_custom_gwp_dictionary_override(self, dispatcher):
        """A user-supplied custom GWP dictionary must be strictly honored."""
        custom_gwp = {"CO2": 1.0, "CH4": 34.0, "N2O": 298.0}
        payload = {"quantity": 50000.0, "unit": "m3", "fuel_type": "natural_gas", "hhv": 1020.0}
        ef = {"co2": 53.06, "ch4": 0.05, "n2o": 0.001, "unit": "kg/MMBtu"}

        res = dispatcher.dispatch("stationary_combustion", payload, ef, {}, gwp_dict=custom_gwp)
        co2_t = res["results"]["co2"]["value"]
        ch4_t = res["results"]["ch4"]["value"]
        n2o_t = res["results"]["n2o"]["value"]

        expected_co2e = (co2_t * 1.0) + (ch4_t * 34.0) + (n2o_t * 298.0)
        assert pytest.approx(res["total_co2e"], rel=1e-5) == expected_co2e

    def test_flaring_methane_slip_20yr_sensitivity(self):
        """
        In flaring, unburnt methane slip is amplified under a 20-year horizon.
        """
        calc = FlaringCalculator()
        vol_m3 = 100000.0
        ch4_frac = 0.85
        dest_eff = 0.95  # 5% unburnt methane slip

        res_100 = calc.calculate(
            gas_volume=vol_m3,
            ch4_fraction=ch4_frac,
            flare_type="open_pit",
            destruction_efficiency=dest_eff,
            combustion_efficiency=0.95,
            uncertainties={},
            hhv=1020.0,
            ef_unit="kg/m3",
            fuel_unit="m3",
            fuel_type="gases",
            gwp_dict=get_active_gwp("AR5", horizon="100"),
        )
        res_20 = calc.calculate(
            gas_volume=vol_m3,
            ch4_fraction=ch4_frac,
            flare_type="open_pit",
            destruction_efficiency=dest_eff,
            combustion_efficiency=0.95,
            uncertainties={},
            hhv=1020.0,
            ef_unit="kg/m3",
            fuel_unit="m3",
            fuel_type="gases",
            gwp_dict=get_active_gwp("AR5", horizon="20"),
        )

        # Unburnt methane is (100000 * 0.85 * 0.05 * 0.6785) / 1000 = 2.8836 tonnes CH4
        unburnt_ch4 = res_100["results"]["ch4"]["value"]
        assert unburnt_ch4 == pytest.approx(res_20["results"]["ch4"]["value"], rel=1e-5)

        # Difference in total CO2e must equal unburnt CH4 * (GWP_20 - GWP_100) = 2.8836 * (82.5 - 28.0) = 157.158 tonnes CO2e
        co2e_diff = res_20["total_co2e"] - res_100["total_co2e"]
        expected_diff = unburnt_ch4 * (82.5 - 28.0)
        assert pytest.approx(co2e_diff, rel=1e-4) == expected_diff
