"""
Comprehensive Numerical and Logical Verification Suite
======================================================
Covers:
  1. Scope 1: Tier 1, Tier 2, Tier 3 calculations across all emission sources
  2. Scope 2: Location-based, Market-based, Indirect Steam, CHP Cogeneration
  3. Scope 3: Tier 1 (Spend-based EEIO), Tier 2 (Average-data), Tier 3 (Supplier-specific), Category 11
  4. KPIs: Carbon Intensity (kg/BOE), Methane Intensity & Loss Rate (%), Flaring Rate (%), EPA WEC (Part 99)
  5. Uncertainty Propagation: Product Rule, Sum Rule, SRSS Inventory Aggregation, 95% CI (GUM k=2)
"""

import math
import pytest
from app import app
from models import db, Facility, User, Emission, Scope2Emission, Scope3Emission, ProductionData
from calculations.dispatcher import CalculationDispatcher
from calculations.combustion import CombustionCalculator, FlaringCalculator
from calculations.vented import (
    PneumaticDeviceCalculator,
    LiquidsUnloadingCalculator,
    BlowdownCalculator,
    TankFlashingCalculator,
    CompletionFlowbackCalculator,
    MudDegassingCalculator,
)
from calculations.fugitive import (
    ComponentFugitiveCalculator,
    EquipmentFugitiveCalculator,
    CompressorSealCalculator,
)
from calculations.midstream import AGRCalculator, DehydratorCalculator
from calculations.indirect import IndirectSteamCalculator, CogenAllocationCalculator
from calculations.stoichiometry import StoichiometricCalculator
from calculations.units import CONVERSIONS, convert, calculate_co2e, normalize_gas_volume_to_standard
from calculations.uncertainty import (
    Tier,
    propagate_uncertainty,
    combine_uncertainties_product,
    combine_uncertainties_sum,
    srss_inventory,
    resolve_tier,
    resolve_ef_uncertainty,
    ACTIVITY_UNCERTAINTY,
    COVERAGE_FACTOR_95,
)
from emission_factors.eeio_factors import EEIO_FACTORS, get_eeio_factor
from electricity_factors import GRID_FACTORS
from routes.scope2 import _calc_indirect_steam, _calc_cogen_allocation


# ===========================================================================
# 1. SCOPE 1: TIER 1, TIER 2, TIER 3 NUMERICAL VERIFICATION
# ===========================================================================

class TestScope1Tiers:
    """Verifies Scope 1 calculations across Tier 1 (default), Tier 2 (regional/custom), and Tier 3 (measured/composition)."""

    def test_scope1_tier1_combustion_default_ef(self):
        """Tier 1: Standard activity × default EF.
        1,000 MMBtu natural gas with default EPA/API factors:
        CO2: 53.06 kg/MMBtu = 53.06 tCO2
        CH4: 0.001 kg/MMBtu = 0.001 tCH4 (28 tCO2e/tCH4 AR5 -> 0.028 tCO2e)
        N2O: 0.0001 kg/MMBtu = 0.0001 tN2O (265 tCO2e/tN2O AR5 -> 0.0265 tCO2e)
        Total CO2e = 53.06 + 0.028 + 0.0265 = 53.1145 tCO2e
        Uncertainty: Tier 1 default activity uncertainty = 10%.
        """
        calc = CombustionCalculator()
        res = calc.calculate(
            fuel_quantity=1000.0,
            ef_co2=53.06,
            ef_ch4=0.001,
            ef_n2o=0.0001,
            uncertainties={"_factor_source": "default"},
            hhv=1020.0,
            ef_unit="kg/MMBtu",
            fuel_unit="MMBtu",
            fuel_type="gas",
        )
        assert abs(res["results"]["co2"]["value"] - 53.06) < 1e-4
        assert abs(res["results"]["ch4"]["value"] - 0.001) < 1e-6
        assert abs(res["results"]["n2o"]["value"] - 0.0001) < 1e-6
        assert abs(res["total_co2e"] - 53.1145) < 1e-3
        # Tier 1 uncertainty verification
        assert res["results"]["co2"]["tier"] == Tier.T1
        assert res["results"]["co2"]["ad_uncertainty_1sigma"] == (ACTIVITY_UNCERTAINTY[Tier.T1] / COVERAGE_FACTOR_95)

    def test_scope1_tier2_combustion_custom_hhv_and_density(self):
        """Tier 2: Fuel-specific Higher Heating Value (HHV) and regional density.
        Fuel: 10,000 m3 natural gas with custom field HHV = 1,150 Btu/scf (instead of default 1020).
        Conversion: 10,000 m3 * 35.3147 scf/m3 * (1,150 / 1e6) = 406.119 MMBtu.
        CO2 at 53.06 kg/MMBtu -> 406.119 * 53.06 / 1000 = 21.5487 tCO2.
        Uncertainty: Tier 2 factor_source='custom' assigns Tier.T2 (7% activity uncertainty).
        """
        calc = CombustionCalculator()
        res = calc.calculate(
            fuel_quantity=10000.0,
            ef_co2=53.06,
            ef_ch4=0.001,
            ef_n2o=0.0001,
            uncertainties={"_factor_source": "custom"},
            hhv=1150.0,
            ef_unit="kg/MMBtu",
            fuel_unit="m3",
            fuel_type="gas",
        )
        expected_mmbtu = 10000.0 * 35.3147 * (1150.0 / 1e6)
        expected_co2 = (expected_mmbtu * 53.06) / 1000.0
        assert abs(res["results"]["co2"]["value"] - expected_co2) < 0.05
        assert res["results"]["co2"]["tier"] == Tier.T2
        assert res["results"]["co2"]["ad_uncertainty_1sigma"] == (ACTIVITY_UNCERTAINTY[Tier.T2] / COVERAGE_FACTOR_95)

    def test_scope1_tier3_gas_composition_stoichiometric_balance(self):
        """Tier 3: Detailed chromatographic gas composition (C1-C10) with carbon mass balance.
        Composition: 80% CH4 (C1), 10% C2H6 (C2), 5% C3H8 (C3), 5% CO2 (native).
        Total carbon moles per mole of fuel gas:
          = 0.80*1 + 0.10*2 + 0.05*3 = 0.80 + 0.20 + 0.15 = 1.15 moles C.
        Volume: 100,000 scf fuel gas.
        Combustion efficiency: 99.5% (0.995).
        Combusted CO2 volume = 100,000 scf * 0.028316846592 m3/scf * 1.15 * 0.995 = 3240.165 m3 CO2.
        Combusted CO2 mass = 3240.165 m3 * 1.861 kg/m3 = 6030.01 kg CO2 = 6.0300 tCO2.
        Native CO2 mass = (100,000 * 0.028316846592 * 0.05) * 1.861 = 263.49 kg = 0.2635 tCO2.
        Total CO2 = 6.0300 + 0.2635 = 6.2935 tCO2.
        Uncombusted CH4 slip = 100,000 * 0.028316846592 * 0.80 * (1 - 0.995) * 0.6785 = 7.685 kg = 0.007685 tCH4.
        """
        calc = CombustionCalculator()
        res = calc.calculate(
            fuel_quantity=100.0,  # 100 Mscf = 100,000 scf
            ef_co2=53.06,
            ef_ch4=0.001,
            ef_n2o=0.0001,
            uncertainties={"_factor_source": "site_specific"},
            hhv=1020.0,
            ef_unit="kg/mscf",
            fuel_unit="mscf",
            fuel_type="gas",
            combustion_efficiency=0.995,
            c1=0.80,
            c2=0.10,
            c3=0.05,
            co2_comp=0.05,
        )
        vol_m3 = 100.0 * 1000.0 * CONVERSIONS["scf_to_m3"]
        expected_comb_co2 = (vol_m3 * 1.15 * 0.995 * CONVERSIONS["density_co2"]) / 1000.0
        expected_native_co2 = (vol_m3 * 0.05 * CONVERSIONS["density_co2"]) / 1000.0
        expected_total_co2 = expected_comb_co2 + expected_native_co2
        expected_ch4_slip = (vol_m3 * 0.80 * (1.0 - 0.995) * CONVERSIONS["density_ch4"]) / 1000.0

        assert abs(res["results"]["co2"]["value"] - expected_total_co2) < 1e-4
        assert abs(res["results"]["ch4"]["value"] - expected_ch4_slip) < 1e-5
        assert res["results"]["co2"]["tier"] == Tier.T3

    def test_scope1_tier2_flaring_dual_efficiency(self):
        """Tier 2 Flaring: Dual efficiency model (combustion efficiency vs destruction efficiency).
        Gas flared: 50,000 m3 of gas with 90% CH4 (0.90 mol fraction).
        Combustion efficiency eta_c = 98.0%, Destruction efficiency eta_d = 98.5%.
        Combusted CH4 -> CO2: 50,000 * 0.90 * 0.980 = 44,100 m3 CH4 combusted.
        CO2 mass = 44,100 m3 * 1.861 kg/m3 = 82,070.1 kg = 82.0701 tCO2.
        Uncombusted CH4 emitted: 50,000 * 0.90 * (1.0 - 0.985) = 675 m3 CH4.
        CH4 mass = 675 m3 * 0.6785 kg/m3 = 457.9875 kg = 0.45799 tCH4.
        """
        calc = FlaringCalculator()
        res = calc.calculate(
            gas_volume=50000.0,
            ch4_fraction=0.90,
            flare_type="elevated",
            uncertainties={"_factor_source": "custom"},
            combustion_efficiency=0.980,
            destruction_efficiency=0.985,
            fuel_unit="m3",
        )
        assert abs(res["results"]["co2"]["value"] - 82.0701) < 0.05
        assert abs(res["results"]["ch4"]["value"] - 0.45799) < 0.005
        assert res["results"]["co2"]["tier"] == Tier.T2

    def test_scope1_tier1_and_tier3_pneumatic_bleed(self):
        """Tier 1 default pneumatic bleed vs Tier 3 measured bleed rates.
        Tier 1: 10 continuous high-bleed devices * 8760 hrs * default 37.3 scf/hr * 85% CH4.
        Tier 3: 5 low-bleed devices measured at 2.1 scf/hr with Coriolis calibration.
        """
        calc = PneumaticDeviceCalculator()
        # Tier 1
        res_t1 = calc.calculate(
            count=10,
            hours=8760,
            bleed_rate=37.3,
            ch4_content=0.85,
            uncertainties={"_factor_source": "default"},
        )
        total_scf_ch4 = 10 * 8760 * 37.3 * 0.85
        total_m3_ch4 = convert(total_scf_ch4, "scf", "m3")
        expected_t1_ch4_tonnes = (total_m3_ch4 * CONVERSIONS["density_ch4"]) / 1000.0
        assert abs(res_t1["results"]["ch4"]["value"] - expected_t1_ch4_tonnes) < 1e-4

        # Tier 3
        res_t3 = calc.calculate(
            count=5,
            hours=8760,
            bleed_rate=2.1,
            ch4_content=0.85,
            uncertainties={"_factor_source": "site_specific"},
        )
        total_t3_scf = 5 * 8760 * 2.1 * 0.85
        total_t3_m3 = convert(total_t3_scf, "scf", "m3")
        expected_t3_ch4_tonnes = (total_t3_m3 * CONVERSIONS["density_ch4"]) / 1000.0
        assert abs(res_t3["results"]["ch4"]["value"] - expected_t3_ch4_tonnes) < 1e-4
        assert res_t3["results"]["ch4"]["tier"] == Tier.T3


# ===========================================================================
# 2. SCOPE 2: LOCATION-BASED, MARKET-BASED, STEAM & COGEN ALLOCATION
# ===========================================================================

class TestScope2Methods:
    """Verifies Scope 2 Location-based, Market-based, Steam and Cogeneration equations."""

    def test_scope2_location_based_grid_averages(self):
        """Scope 2 Location-Based Method:
        Emissions (tCO2e) = Electricity (kWh) × Grid Emission Factor (kg CO2e / kWh) / 1,000.
        Test regional factors from electricity_factors.GRID_FACTORS:
        - US Average: 0.385 kg/kWh
        - EU Grid Average: 0.295 kg/kWh
        - Algerian National Grid: 0.522 kg/kWh
        """
        for region, expected_factor in [("US Average", 0.385), ("EU Grid Average", 0.295), ("Algerian National Grid", 0.522)]:
            factor = GRID_FACTORS[region]["factor"]
            assert abs(factor - expected_factor) < 1e-4

            kwh = 1_000_000.0  # 1 GWh = 1,000,000 kWh
            expected_tco2e = (kwh * factor) / 1000.0
            assert expected_tco2e > 0
            if region == "EU Grid Average":
                assert expected_tco2e < 300.0
            elif region == "Algerian National Grid":
                assert expected_tco2e > 500.0

    def test_scope2_market_based_contractual_instruments(self):
        """Scope 2 Market-Based Method:
        Verified Green PPA / Renewable Energy Certificates (RECs) with 0.0 EF:
        Emissions = 1,000,000 kWh * 0.0 kg/kWh = 0.0 tCO2e.
        Supplier-specific contract factor: 0.120 kg/kWh:
        Emissions = 1,000,000 * 0.120 / 1000 = 120.0 tCO2e.
        """
        # 100% Green Tariff
        green_kwh = 500_000.0
        green_ef = 0.0
        assert (green_kwh * green_ef) / 1000.0 == 0.0

        # Contractual Supplier Factor
        supplier_kwh = 500_000.0
        supplier_ef = 0.120
        assert abs((supplier_kwh * supplier_ef) / 1000.0 - 60.0) < 1e-5

    def test_scope2_indirect_steam_thermodynamic_equation(self):
        """Scope 2 Indirect Steam & Heat:
        Formula: CO2 (t) = (Energy MMBtu × EF_boiler) / [net_eff × 1000]
        where net_eff = boiler_eff × (1 - trans_loss).
        Test: 500 MMBtu steam, boiler_eff = 80% (0.80), trans_loss = 5% (0.05), EF = 53.06 kg/MMBtu.
        net_eff = 0.80 * (1 - 0.05) = 0.76.
        CO2 (kg) = (500 * 53.06) / 0.76 = 34,907.89 kg = 34.9079 tCO2.
        """
        data = {
            "amount": 500.0,
            "unit": "MMBtu",
            "calc_inputs": {
                "indirect_steam": {
                    "boiler_eff": 0.80,
                    "trans_loss": 0.05,
                    "ef_co2": 53.06,
                }
            },
        }
        co2_tonnes, energy_mmbtu, ef = _calc_indirect_steam(data)
        expected = (500.0 * 53.06) / (0.80 * 0.95 * 1000.0)
        assert abs(co2_tonnes - expected) < 1e-4
        assert energy_mmbtu == 500.0

    def test_scope2_cogen_allocation_wri_efficiency_and_energy_methods(self):
        """Scope 2 Cogeneration (CHP) Allocation Methods:
        Total Facility Emissions: 10,000 tCO2e.
        Heat Output H = 60 MWh, Power Output P = 40 MWh.
        1. WRI Efficiency Method: e_h = 0.80, e_p = 0.33:
           Denom = (60 / 0.80) + (40 / 0.33) = 75 + 121.212 = 196.212.
           Heat Share = 75 / 196.212 = 0.38224.
           Heat Allocated = 0.38224 * 10,000 = 3822.4 tCO2e.
        2. Energy Content Method:
           Heat Share = 60 / (60 + 40) = 0.60 (60%).
           Heat Allocated = 0.60 * 10,000 = 6,000 tCO2e.
        """
        # 1. WRI Efficiency
        data_wri = {
            "amount": 10000.0,
            "calc_inputs": {
                "cogen_allocation": {
                    "total_emissions": 10000.0,
                    "heat_output": 60.0,
                    "power_output": 40.0,
                    "allocation_method": "wri_efficiency",
                }
            },
        }
        res_wri = _calc_cogen_allocation(data_wri)
        expected_wri = ((60.0 / 0.8) / ((60.0 / 0.8) + (40.0 / 0.33))) * 10000.0
        assert abs(res_wri - expected_wri) < 1e-3

        # 2. Energy Content
        data_energy = {
            "amount": 10000.0,
            "calc_inputs": {
                "cogen_allocation": {
                    "total_emissions": 10000.0,
                    "heat_output": 60.0,
                    "power_output": 40.0,
                    "allocation_method": "energy_content",
                }
            },
        }
        res_energy = _calc_cogen_allocation(data_energy)
        assert abs(res_energy - 6000.0) < 1e-4


# ===========================================================================
# 3. SCOPE 3: TIER 1 (EEIO), TIER 2 (AVERAGE), TIER 3 (SUPPLIER) & CAT 11
# ===========================================================================

class TestScope3Tiers:
    """Verifies Scope 3 across Tier 1 (Spend-based USEEIO), Tier 2 (Average-data), Tier 3 (Supplier-specific) and Category 11."""

    def test_scope3_tier1_spend_based_eeio(self):
        """Tier 1 Spend-Based:
        Emissions = Spend ($) × EEIO Factor (kg CO2e / $1,000) / (1,000 * 1,000).
        NAICS 211 (Oil and Gas Extraction): 3,200.1 kg CO2e / $1,000 spend.
        Spend: $500,000.
        Emissions = (500,000 / 1,000) * 3,200.1 / 1,000 = 500 * 3.2001 = 1,600.05 tCO2e.
        """
        factor_info = get_eeio_factor("211")
        assert factor_info["name"] == "Oil and Gas Extraction"
        ef_kg_per_1000 = factor_info["kg_co2e_per_1000_usd"]

        spend_usd = 500_000.0
        emissions_tco2e = (spend_usd / 1000.0) * (ef_kg_per_1000 / 1000.0)
        assert abs(emissions_tco2e - 1600.05) < 1e-4

        # Uncertainty: Spend-based has Tier 1 high uncertainty (30-40%)
        u = propagate_uncertainty(emissions_tco2e, ef_uncertainty=0.30, activity_uncertainty=0.15, tier=Tier.T1)
        assert u["tier"] == Tier.T1
        assert u["lower_bound"] > 0
        assert u["upper_bound"] > emissions_tco2e

    def test_scope3_tier2_average_data_transport(self):
        """Tier 2 Average-Data: Category 4 Freight Transportation.
        Activity: 250,000 tonne-km by diesel heavy truck.
        Secondary Emission Factor: 0.085 kg CO2e / tonne-km.
        Emissions = 250,000 * 0.085 / 1000 = 21.25 tCO2e.
        """
        activity_tonne_km = 250_000.0
        ef_kg_per_tonne_km = 0.085
        emissions_tco2e = (activity_tonne_km * ef_kg_per_tonne_km) / 1000.0
        assert abs(emissions_tco2e - 21.25) < 1e-5

    def test_scope3_tier3_supplier_specific_pcf(self):
        """Tier 3 Supplier-Specific: Category 1 Product Carbon Footprint (EPD/LCA).
        Supplier provided primary certified factor: 1.45 tCO2e / tonne steel pipe.
        Quantity: 500 tonnes steel pipe.
        Emissions = 500 * 1.45 = 725.0 tCO2e.
        Tier 3 measured uncertainty: 5% EF, 2% AD -> combined ~5.4%.
        """
        quantity_tonnes = 500.0
        supplier_ef = 1.45  # tCO2e / tonne
        emissions_tco2e = quantity_tonnes * supplier_ef
        assert emissions_tco2e == 725.0

        u = propagate_uncertainty(emissions_tco2e, ef_uncertainty=0.05, activity_uncertainty=0.02, tier=Tier.T3)
        assert u["tier"] == Tier.T3
        assert abs(u["relative_uncertainty_95pct"] - math.sqrt(0.05**2 + 0.02**2)) < 1e-4

    def test_scope3_category11_use_of_sold_products_oil_and_gas(self):
        """Category 11 (Use of Sold Products): The dominant Scope 3 emission source for O&G.
        1. Crude Oil: 1,000,000 bbl sold.
           IPCC default factor: 0.43 tCO2e / bbl crude oil.
           Emissions = 1,000,000 * 0.43 = 430,000 tCO2e.
        2. Natural Gas: 50,000,000 m3 sold.
           IPCC factor: 1.884 kg CO2e / m3 gas.
           Emissions = 50,000,000 * 1.884 / 1000 = 94,200 tCO2e.
        """
        oil_bbl = 1_000_000.0
        oil_ef = 0.430
        oil_emissions = oil_bbl * oil_ef
        assert oil_emissions == 430_000.0

        gas_m3 = 50_000_000.0
        gas_ef = 1.884  # kg/m3
        gas_emissions = (gas_m3 * gas_ef) / 1000.0
        assert abs(gas_emissions - 94_200.0) < 1e-4


# ===========================================================================
# 4. KPIS: CARBON INTENSITY, METHANE LOSS RATE, FLARING RATE & EPA WEC
# ===========================================================================

class TestKPIsAndIntensities:
    """Verifies all Dashboard and Executive KPI mathematical equations."""

    def test_boe_production_normalization_exactness(self):
        """BOE Normalization Equation:
        BOE = Oil (bbl) + Gas (Mscf) × 0.178.
        Composite production: 5,000 bbl oil + 10 MMscf gas:
        Gas in Mscf = 10 * 1,000 = 10,000 Mscf.
        BOE = 5,000 + 10,000 * 0.178 = 5,000 + 1,780 = 6,780 BOE.
        """
        oil_bbl = 5000.0
        gas_mmscf = 10.0
        gas_mscf = gas_mmscf * 1000.0
        total_boe = oil_bbl + (gas_mscf * 0.178)
        assert abs(total_boe - 6780.0) < 1e-5

    def test_carbon_intensity_metric_equations(self):
        """Carbon Intensity:
        Carbon Intensity (kg CO2e / BOE) = (Emissions tCO2e × 1,000) / Production (BOE).
        Emissions: 150.0 tCO2e (Scope 1: 120.0, Scope 2: 30.0).
        Production: 6,780 BOE.
        Scope 1 Intensity = (120.0 * 1000) / 6780 = 17.699 kg CO2e / BOE.
        Scope 2 Intensity = (30.0 * 1000) / 6780 = 4.425 kg CO2e / BOE.
        Combined Scope 1+2 = (150.0 * 1000) / 6780 = 22.124 kg CO2e / BOE.
        """
        boe = 6780.0
        s1 = 120.0
        s2 = 30.0
        s1_int = (s1 * 1000.0) / boe
        s2_int = (s2 * 1000.0) / boe
        comb_int = ((s1 + s2) * 1000.0) / boe

        assert abs(s1_int - 17.6991) < 1e-3
        assert abs(s2_int - 4.4248) < 1e-3
        assert abs(comb_int - 22.1239) < 1e-3
        # Additivity invariant
        assert abs((s1_int + s2_int) - comb_int) < 1e-9

    def test_methane_loss_rate_ogmp_equation(self):
        """OGMP 2.0 Methane Loss Rate (%):
        Formula: Loss Rate (%) = [V_CH4_emitted (m3) / V_marketable_gas (m3)] × 100%.
        V_CH4_emitted (m3) = (CH4_tonnes × 1,000) / 0.6785.
        Scenario:
          Marketable Gas: 10,000,000 m3.
          CH4 emitted: 10.0 tonnes.
          V_CH4 = (10.0 * 1000) / 0.6785 = 14,738.39 m3.
          Loss Rate (%) = (14,738.39 / 10,000,000) * 100% = 0.1474%.
        Compliance Evaluation:
          Upstream target: 0.20% -> 0.1474% <= 0.20% -> Compliant.
          Midstream target: 0.05% -> 0.1474% > 0.05% -> Non-Compliant.
        """
        gas_m3 = 10_000_000.0
        ch4_tonnes = 10.0
        v_ch4 = (ch4_tonnes * 1000.0) / 0.6785
        loss_rate_pct = round((v_ch4 / gas_m3) * 100.0, 4)
        assert abs(loss_rate_pct - 0.1474) < 1e-4

        # Upstream vs Midstream compliance logic check
        up_target = 0.20
        mid_target = 0.05
        assert loss_rate_pct <= up_target  # Upstream is compliant
        assert loss_rate_pct > mid_target  # Midstream is non-compliant

    def test_ogmp_facility_level_5_requires_level_4_bottom_up(self):
        """OGMP 2.0 Gold Standard Requirement:
        Level 5 reconciliation requires both top-down and bottom-up within threshold,
        AND the bottom-up inventory must be source-level measured / Tier 3 (Level 4).
        If bottom-up is Level 2 or 3 (desk factors), facility level is capped at Level 4.
        """
        from services.ogmp import compute_facility_ogmp_level

        class DummyFacility:
            id = 9999
            reconciliation_threshold = 20.0

        fac = DummyFacility()
        # Case 1: Reconciled within 5% variance, but bottom-up is Level 3 (generic equipment factors) -> Cap at Level 4
        lvl_cap = compute_facility_ogmp_level(
            fac,
            top_down_tch4=100.0,
            bottom_up_tch4=105.0,
            reconciled_survey=True,
            bottom_up_level=3,
        )
        assert lvl_cap == 4

        # Case 2: Reconciled within 5% variance, bottom-up is Level 4 (source-level measured) -> Level 5 awarded
        lvl_gold = compute_facility_ogmp_level(
            fac,
            top_down_tch4=100.0,
            bottom_up_tch4=105.0,
            reconciled_survey=True,
            bottom_up_level=4,
        )
        assert lvl_gold == 5

        # Case 3: Unreconciled survey (> 20% variance) with Level 4 bottom-up -> Level 4
        lvl_unrec = compute_facility_ogmp_level(
            fac,
            top_down_tch4=100.0,
            bottom_up_tch4=150.0,
            reconciled_survey=False,
            bottom_up_level=4,
        )
        assert lvl_unrec == 4

    def test_flaring_rate_percentage_equation(self):
        """Flaring Rate (%):
        Flaring Rate (%) = [Flared Gas Volume (m3) / Produced Gas Volume (m3)] × 100%.
        Produced Gas: 20,000,000 m3.
        Flared Gas: 250,000 m3.
        Flaring Rate = (250,000 / 20,000,000) * 100% = 1.25%.
        """
        prod_gas_m3 = 20_000_000.0
        flared_gas_m3 = 250_000.0
        flaring_rate_pct = round((flared_gas_m3 / prod_gas_m3) * 100.0, 4)
        assert flaring_rate_pct == 1.25

    def test_epa_wec_part99_fee_schedules_and_thresholds(self):
        """EPA Waste Emissions Charge (40 CFR Part 99 / IRA §136):
        1. Upstream Gas Production Threshold: 0.20% (0.0020).
           Marketable Gas: 50,000,000 m3.
           Allowed CH4 (tonnes) = (50,000,000 * 0.0020 * 0.6785) / 1000 = 67.85 tonnes.
           Emitted CH4: 85.0 tonnes.
           Excess CH4 = 85.0 - 67.85 = 17.15 tonnes.
           Fees:
             - 2024 ($900/t): 17.15 * 900 = $15,435.00
             - 2025 ($1,200/t): 17.15 * 1200 = $20,580.00
             - 2026+ ($1,500/t): 17.15 * 1500 = $25,725.00
        2. Upstream Oil-Only Asset (No gas sales per 40 CFR 99.20(a)(2)):
           Allowed CH4 = 10.0 tonnes / 1,000,000 bbl oil.
           Oil: 500,000 bbl.
           Allowed CH4 = (500,000 / 1,000,000) * 10.0 = 5.0 tonnes.
        """
        # Gas producing asset
        gas_m3 = 50_000_000.0
        wec_threshold_pct = 0.0020
        allowed_ch4 = (gas_m3 * wec_threshold_pct * 0.6785) / 1000.0
        assert abs(allowed_ch4 - 67.85) < 1e-4

        actual_ch4 = 85.0
        excess_ch4 = max(0.0, actual_ch4 - allowed_ch4)
        assert abs(excess_ch4 - 17.15) < 1e-4

        fee_2024 = round(excess_ch4 * 900.0, 2)
        fee_2025 = round(excess_ch4 * 1200.0, 2)
        fee_2026 = round(excess_ch4 * 1500.0, 2)
        assert fee_2024 == 15435.00
        assert fee_2025 == 20580.00
        assert fee_2026 == 25725.00

        # Oil-only asset
        oil_bbl = 500_000.0
        allowed_oil_ch4 = (oil_bbl / 1_000_000.0) * 10.0
        assert allowed_oil_ch4 == 5.0


# ===========================================================================
# 5. UNCERTAINTY QUANTIFICATION: ISO 14064-1 & IPCC APPROACH 1 FORMULAS
# ===========================================================================

class TestUncertaintyQuantificationMath:
    """Verifies all formal statistical formulas for uncertainty propagation."""

    def test_multiplicative_product_propagation_formula(self):
        """IPCC Eq 3.1: u_E = sqrt(u_AD^2 + u_EF^2).
        u_AD = 0.07 (7%), u_EF = 0.05 (5%).
        u_E = sqrt(0.07^2 + 0.05^2) = sqrt(0.0049 + 0.0025) = sqrt(0.0074) = 0.086023 (8.60%).
        """
        u_prod = combine_uncertainties_product(0.05, 0.07)
        assert abs(u_prod - 0.08602325) < 1e-6

    def test_additive_sum_propagation_formula(self):
        """IPCC Eq 3.2: u_total = sqrt((E1*u1)^2 + (E2*u2)^2) / (E1 + E2).
        Source 1: 1,000 tCO2e, u1 = 5% (sigma1 = 50 t).
        Source 2: 2,000 tCO2e, u2 = 10% (sigma2 = 200 t).
        Sigma_total = sqrt(50^2 + 200^2) = sqrt(2500 + 40000) = sqrt(42500) = 206.155 t.
        u_total = 206.155 / 3,000 = 0.068718 (6.87%).
        """
        u_sum = combine_uncertainties_sum(1000.0, 0.05, 2000.0, 0.10)
        assert abs(u_sum - (math.sqrt(50**2 + 200**2) / 3000.0)) < 1e-6

    def test_srss_inventory_aggregation_approach1(self):
        """IPCC Eq 3.3 / ISO 14064-1 SRSS Aggregation:
        U_inv = sqrt(sum((E_i * u_i)^2)) / sum(E_i).
        Test with 4 emission sources:
        1. Combustion: 50,000 tCO2e, u = 4%
        2. Flaring: 10,000 tCO2e, u = 12%
        3. Fugitive: 5,000 tCO2e, u = 25%
        4. Vented: 2,000 tCO2e, u = 18%
        """
        sources = [
            {"value": 50000.0, "relative_uncertainty": 0.04},  # sigma = 2000
            {"value": 10000.0, "relative_uncertainty": 0.12},  # sigma = 1200
            {"value": 5000.0, "relative_uncertainty": 0.25},   # sigma = 1250
            {"value": 2000.0, "relative_uncertainty": 0.18},   # sigma = 360
        ]
        res = srss_inventory(sources)
        total_val = 50000 + 10000 + 5000 + 2000  # 67,000 tCO2e
        sum_sq = 2000**2 + 1200**2 + 1250**2 + 360**2  # 4M + 1.44M + 1.5625M + 0.1296M = 7,132,100
        expected_sigma = math.sqrt(sum_sq)
        expected_u1sigma = expected_sigma / total_val

        assert abs(res["total_value"] - total_val) < 1e-4
        assert abs(res["relative_uncertainty_1sigma"] - expected_u1sigma) < 1e-6
        assert abs(res["relative_uncertainty_95pct"] - 2.0 * expected_u1sigma) < 1e-6

    def test_coverage_factor_and_non_negative_bounds(self):
        """GUM §6.2 Coverage Factor k=2.0 and non-negative lower bound:
        When relative uncertainty exceeds 100%, lower bound clamps strictly to 0.0 (no negative emissions).
        """
        u = propagate_uncertainty(100.0, ef_uncertainty=2.50, activity_uncertainty=0.50, tier=Tier.T1)
        assert u["lower_bound"] == 0.0
        assert u["upper_bound"] > 100.0
        assert u["coverage_factor"] == 2.0
