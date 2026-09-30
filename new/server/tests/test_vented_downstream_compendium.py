"""
Unit and Golden Tests for API Compendium 2021 Sections 6.11, 6.12, 6.14:
Downstream Refining, Petrochemical Manufacturing & Fire Suppression
"""

import pytest
import math
from calculations.vented_downstream import (
    RefiningCatalystRegenCalculator,
    RefiningCokerCalculator,
    RefiningHydrogenPlantCalculator,
    AsphaltBlowingCalculator,
    RefiningCokeCalciningCalculator,
    SulfurRecoveryTailGasCalculator,
    PetrochemicalManufacturingCalculator,
    FireSuppressionCalculator,
)


def _val(item):
    if item is None:
        return 0.0
    if isinstance(item, dict):
        return item.get("value", 0.0)
    return float(item)


class TestCatalystRegenerationCompendium:
    """Tests for API Compendium 2021 §6.11.1 Catalyst Regeneration."""

    def setup_method(self):
        self.calc = RefiningCatalystRegenCalculator()

    def test_exhibit_6_38_fccu_coke_burn_approach(self):
        """
        EXHIBIT 6-38 Method 1 (Equation 6-34):
        - Coke burn rate = 119,750 tonnes/yr
        - Carbon fraction CF = 0.93
        - Supplemental gas firing = 100 MMBtu/hr (8760 hr/yr)
        - Expected Coke Burn CO2 = 408,348 tonnes CO2/yr
        - Expected CO Boiler CO2 = 46,516 tonnes CO2/yr
        - Expected Coke Burn CH4 = 12.04 tonnes CH4/yr
        - Expected Coke Burn N2O = 2.40 tonnes N2O/yr
        """
        res = self.calc.calculate(
            approach="coke_burn",
            coke_burn_rate_tonnes_yr=119750.0,
            carbon_content_fraction=0.93,
            supplemental_fuel_mmbtu_hr=100.0,
        )
        assert pytest.approx(res["inputs"]["coke_burn_co2"], rel=1e-3) == 408348.0
        assert pytest.approx(res["inputs"]["supplemental_co2"], rel=1e-3) == 46516.0
        assert pytest.approx(res["inputs"]["coke_burn_ch4"], rel=2e-2) == 12.04
        assert pytest.approx(res["inputs"]["coke_burn_n2o"], rel=2e-2) == 2.40
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-3) == 408348.0 + 46516.0

    def test_exhibit_6_38_fccu_air_blower_approach(self):
        """
        EXHIBIT 6-38 Method 3 (Equation 6-36):
        - Air rate = 2150 m3/min
        - CO2 = 11%, CO = 9%
        - Operating hours = 8760 hr/yr
        - Expected Coke Burn CO2 = 419,859 tonnes CO2/yr
        """
        res = self.calc.calculate(
            approach="air_blower",
            air_rate_m3_min=2150.0,
            co2_pct=11.0,
            co_pct=9.0,
            operating_hours=8760.0,
        )
        assert pytest.approx(res["inputs"]["coke_burn_co2"], rel=1e-2) == 419859.0

    def test_exhibit_6_39_continuous_catalyst_regen(self):
        """
        EXHIBIT 6-39 Golden Test (Equation 6-40):
        - Catalyst circulation rate = 10 tonnes/hr
        - Operating hours = 8,280 hr/yr
        - Carbon on spent catalyst = 4 wt% (0.04)
        - Carbon on regenerated catalyst = 0 wt%
        - Expected CO2 = 12,144 tonnes CO2/yr
        """
        res = self.calc.calculate(
            approach="continuous",
            catalyst_circulation_rate_tonnes_hr=10.0,
            operating_hours=8280.0,
            fc_spent=0.04,
            fc_regen=0.0,
        )
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-3) == 12144.0

    def test_exhibit_6_40_intermittent_catalyst_regen(self):
        """
        EXHIBIT 6-40 Golden Test (Equation 6-41):
        - Catalyst inventory = 1,000 tonnes
        - Carbon on spent catalyst = 7 wt% (0.07)
        - Regenerations per year = 2
        - Expected CO2 = 513 tonnes CO2/yr
        """
        res = self.calc.calculate(
            approach="intermittent",
            catalyst_inventory_tonnes=1000.0,
            regeneration_cycles_per_yr=2.0,
            fc_spent=0.07,
            fc_regen=0.0,
        )
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-2) == 513.0


class TestCokerCompendium:
    """Tests for API Compendium 2021 §6.11.2 Refining Cokers."""

    def setup_method(self):
        self.calc = RefiningCokerCalculator()

    def test_exhibit_6_61_fluid_coker(self):
        """
        EXHIBIT 6-61 Golden Test (Equation 6-34):
        - Coke burned = 140e6 lb/yr
        - Carbon fraction = 1 - 0.015 = 0.985
        - Expected CO2 = 229,350 tonnes CO2/yr
        """
        res = self.calc.calculate(
            coker_type="fluid",
            coke_burned_lb_yr=140_000_000.0,
            hydrogen_wt_fraction=0.015,
        )
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-3) == 229350.0

    def test_dcu_decoking_operations_direct_steam(self):
        """Equation 6-42: DCU decoking operations from steam mass."""
        # 10 tonnes steam per cycle, 100 cycles, EF = 7.9 kg CH4 / tonne steam
        res = self.calc.calculate(
            coker_type="delayed",
            steam_mass_tonnes_cycle=10.0,
            num_cycles_per_yr=100.0,
            dcu_ch4_ef_kg_tonne_steam=7.9,
        )
        # CH4 = 10 * 7.9 * 100 * 0.001 = 7.9 tonnes CH4
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-3) == 7.9


class TestHydrogenPlantCompendium:
    """Tests for API Compendium 2021 §6.11.3 Refinery Hydrogen Plants."""

    def setup_method(self):
        self.calc = RefiningHydrogenPlantCalculator()

    def test_exhibit_6_42_feedstock_material_balance(self):
        """
        EXHIBIT 6-42 Golden Test (Equation 6-49):
        - Feedstock = 5e9 scf/yr
        - Composition: CH4 85%, C2H6 8%, C4H10 3%, N2 4%
        - Expected CO2 = 297,100 tonnes CO2/yr
        """
        comp = {"CH4": 0.85, "C2H6": 0.08, "C4H10": 0.03, "N2": 0.04}
        res = self.calc.calculate(
            method="feedstock_balance",
            feedstock_volume_scf_yr=5_000_000_000.0,
            feedstock_comp=comp,
        )
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-2) == 297100.0

    def test_exhibit_6_43_h2_stoichiometry(self):
        """
        EXHIBIT 6-43 Golden Test (Equation 6-50):
        - H2 production = 13e9 scf/yr
        - CO2/H2 molar ratio = 0.26
        - Expected CO2 = 177,800 tonnes CO2/yr
        """
        res = self.calc.calculate(
            method="h2_stoichiometry",
            h2_production_scf_yr=13_000_000_000.0,
            co2_to_h2_molar_ratio=0.26,
        )
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-2) == 177800.0

    def test_exhibit_6_44_simple_approach(self):
        """
        EXHIBIT 6-44 Golden Test (Table 6-51):
        - H2 production = 13e9 scf/yr
        - Factor = 13.41 tonnes CO2 / 10^6 scf H2
        - Expected CO2 = 174,300 tonnes CO2/yr
        """
        res = self.calc.calculate(
            method="simple_factor",
            simple_basis="h2_scf",
            h2_production_scf_yr=13_000_000_000.0,
        )
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-2) == 174300.0


class TestAsphaltBlowingCompendium:
    """Tests for API Compendium 2021 §6.11.4 Asphalt Blowing."""

    def setup_method(self):
        self.calc = AsphaltBlowingCalculator()

    def test_exhibit_6_45_uncontrolled(self):
        """
        EXHIBIT 6-45 Golden Test:
        - 100,000 tons asphalt treated
        - Uncontrolled
        - Expected CO2 = 561 tonnes CO2/yr
        - Expected CH4 = 307 tonnes CH4/yr
        """
        res = self.calc.calculate(
            throughput=100000.0,
            unit="ton",
            controlled=False,
        )
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-2) == 561.0
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-2) == 307.0

    def test_controlled_incineration(self):
        """Equations 6-51 & 6-52: 98% destruction efficiency incineration."""
        res = self.calc.calculate(
            throughput=100000.0,
            unit="ton",
            controlled=True,
            destruction_efficiency=0.98,
        )
        # Residual CH4 = 307 * 0.02 = 6.14 tonnes
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-2) == 307.0 * 0.02
        assert _val(res["results"]["co2"]) > 561.0


class TestCokeCalciningAndSRUCompendium:
    """Tests for §6.11.5 Coke Calcining & §6.11.6 SRU Tail Gas."""

    def test_coke_calcining_eq_6_53(self):
        """Equation 6-53: Coke Calcining carbon mass balance."""
        calc = RefiningCokeCalciningCalculator()
        res = calc.calculate(
            green_coke_mass_tonnes_yr=100000.0,
            green_coke_carbon_fraction=0.88,
            calcined_coke_mass_tonnes_yr=80000.0,
            calcined_coke_carbon_fraction=0.98,
            dust_collected_tonnes_yr=2000.0,
        )
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-3) == 7640.0 * (44.0 / 12.0)

    def test_sru_tail_gas_eq_6_54(self):
        """Equation 6-54: Sulfur recovery unit sour gas carbon feed."""
        calc = SulfurRecoveryTailGasCalculator()
        res = calc.calculate(
            sour_gas_scf_yr=100_000_000.0,
            carbon_mole_fraction=0.20,
        )
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-2) == 1052.36


class TestPetrochemicalCompendium:
    """Tests for API Compendium 2021 §6.12 Petrochemical Manufacturing."""

    def setup_method(self):
        self.calc = PetrochemicalManufacturingCalculator()

    def test_acrylonitrile_factors(self):
        """Table 6-53: Acrylonitrile production."""
        res = self.calc.calculate(
            process_type="acrylonitrile",
            production_tonnes=10000.0,
        )
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-3) == 10000.0 * 1.00
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-3) == 10000.0 * 0.00018

    def test_nitric_acid_n2o(self):
        """Table 6-53: Nitric acid with and without NSCR abatement."""
        res_unabated = self.calc.calculate(
            process_type="nitric_acid_unabated",
            production_tonnes=1000.0,
        )
        res_nscr = self.calc.calculate(
            process_type="nitric_acid_nscr",
            production_tonnes=1000.0,
        )
        assert pytest.approx(_val(res_unabated["results"]["n2o"]), rel=1e-3) == 9.0
        assert pytest.approx(_val(res_nscr["results"]["n2o"]), rel=1e-3) == 2.0


class TestFireSuppressionCompendium:
    """Tests for API Compendium 2021 §6.14 Fire Suppression Emissions."""

    def setup_method(self):
        self.calc = FireSuppressionCalculator()

    def test_hfc_227ea_leakage_and_discharge(self):
        """Equation 6-56: HFC-227ea (FM-200, GWP 3220)."""
        res = self.calc.calculate(
            agent_type="hfc_227ea",
            total_charge_kg=5000.0,
            annual_release_rate=0.02,
            direct_discharge_kg=200.0,
        )
        assert pytest.approx(res["inputs"]["chemical_released_tonnes"], rel=1e-3) == 0.3
        assert pytest.approx(res["total_co2e"], rel=1e-3) == 966.0
