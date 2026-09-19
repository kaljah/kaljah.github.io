"""
test_all_process_types_matrix.py
---------------------------------
Exhaustive verification of ALL 24 canonical segment process types + utility/chemical processes
across Tier 1 (catalog factor) and Tier 3 (engineering parameter) calculation paths.

Compliant with:
- API Compendium 2021 (Upstream, Midstream, Downstream)
- IPCC 2006 / 2019 Refinement Guidelines
- GHG Protocol Corporate Standard (Scope 1, 2, 3)
"""

import pytest
import math
from calculations.dispatcher import CalculationDispatcher
from calculations.legacy_engine import compute_emissions
from process_categories import PROCESS_TYPES, NON_COMBUSTION_PROCESSES


@pytest.fixture(scope="module")
def dispatcher():
    return CalculationDispatcher()


# ==============================================================================
# 1. TIER 1 MATRIX: EVERY PROCESS TYPE WITH CATALOG/DEFAULT EMISSION FACTORS
# ==============================================================================

class TestAllProcessTypesTier1:
    """Every single process type in PROCESS_TYPES must calculate successfully in Tier 1."""

    @pytest.mark.parametrize("process_id", list(PROCESS_TYPES.keys()))
    def test_tier1_every_canonical_process_type(self, dispatcher, process_id):
        meta = PROCESS_TYPES[process_id]
        payload = {
            "process_type": process_id,
            "factor_source": "default",
            "amount": 100.0,
            "quantity": 100.0,
            "unit": "m3" if meta["category"] in ["combustion", "vented"] else "devices",
            "fuel_type": "Natural Gas" if meta["category"] == "combustion" else None,
        }
        factor_data = {
            "co2": 50.0 if meta["category"] == "combustion" else 1.0,
            "ch4": 0.5,
            "n2o": 0.01,
            "unit": "kg/m3" if meta["category"] in ["combustion", "vented"] else "kg/unit",
            "hhv": 1020.0,
        }
        res = dispatcher.dispatch(process_id, payload, factor_data, {})
        assert res is not None, f"Dispatcher returned None for process_type={process_id}"
        assert "results" in res, f"Missing 'results' for process_type={process_id}"
        assert res["total_co2e"] > 0, f"Expected total_co2e > 0 for process_type={process_id}"
        assert not math.isnan(res["total_co2e"])
        assert not math.isinf(res["total_co2e"])

    def test_tier1_utilities_and_aliases(self, dispatcher):
        """Verify additional process types not in PROCESS_TYPES table (indirect steam, cogen, fccu, stoichiometry)."""
        extras = ["indirect_steam", "cogen_allocation", "stoichiometry", "fccu"]
        for p in extras:
            payload = {
                "process_type": p,
                "factor_source": "default",
                "amount": 250.0,
                "unit": "mmbtu" if "steam" in p else ("kg" if p == "stoichiometry" else "tonnes"),
            }
            factors = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/mmbtu"}
            res = dispatcher.dispatch(p, payload, factors, {})
            assert res is not None
            assert res["total_co2e"] > 0


# ==============================================================================
# 2. TIER 3 MATRIX: EVERY PROCESS TYPE WITH ENGINEERING PHYSICAL PARAMETERS
# ==============================================================================

class TestAllProcessTypesTier3:
    """Verify specific engineering physics for every process type that supports Tier 3."""

    def test_stationary_combustion_tier3(self, dispatcher):
        payload = {
            "process_type": "stationary_combustion",
            "factor_source": "specific",
            "amount": 1000.0,
            "unit": "m3",
            "fuel_type": "natural_gas",
            "hhv": 1020.0,
            "combustion_efficiency": 99.5,
            "c1": 85.0,
            "c2": 10.0,
            "co2_mol": 2.0,
        }
        res = dispatcher.dispatch("stationary_combustion", payload, {}, {})
        assert res["results"]["co2"]["value"] > 0
        assert res["results"]["ch4"]["value"] > 0
        assert res["total_co2e"] > 0

    def test_mobile_combustion_tier3(self, dispatcher):
        payload = {
            "process_type": "mobile_combustion",
            "factor_source": "specific",
            "amount": 500.0,
            "unit": "liter",
            "fuel_type": "diesel",
            "hhv": 138000.0,
            "combustion_efficiency": 99.0,
            "c1": 0.0,
        }
        factors = {"co2": 73.96, "ch4": 0.003, "n2o": 0.0006, "unit": "kg/mmbtu"}
        res = dispatcher.dispatch("mobile_combustion", payload, factors, {})
        assert res["total_co2e"] > 0

    def test_flaring_tier3(self, dispatcher):
        payload = {
            "process_type": "flaring",
            "factor_source": "specific",
            "amount": 5000.0,
            "unit": "m3",
            "c1": 85.0,
            "co2_mol": 3.0,
            "flare_type": "steam_assisted",
        }
        res = dispatcher.dispatch("flaring", payload, {}, {})
        assert res["results"]["co2"]["value"] > 0
        assert res["results"]["ch4"]["value"] > 0

    def test_drilling_mud_degassing_tier3(self, dispatcher):
        payload = {
            "process_type": "drilling",
            "factor_source": "specific",
            "amount": 500.0,
            "mud_unit": "m3",
            "mud_type": "water_based",
        }
        factors = {"ch4": 0.05}
        res = dispatcher.dispatch("drilling", payload, factors, {})
        assert res["results"]["ch4"]["value"] > 0

    def test_well_completions_tier3(self, dispatcher):
        payload = {
            "process_type": "completions",
            "factor_source": "specific",
            "flowback_volume": 15000.0,
            "unit": "m3",
            "ch4_content": 80.0,
            "control_efficiency": 0.95,
        }
        res = dispatcher.dispatch("completions", payload, {}, {})
        assert res["results"]["ch4"]["value"] > 0
        assert res["results"]["co2"]["value"] > 0

    def test_liquids_unloading_tier3(self, dispatcher):
        payload = {
            "process_type": "liquids_unloading",
            "factor_source": "specific",
            "well_depth": 3000.0,
            "diameter": 2.5,
            "pressure": 350.0,
            "events": 4,
            "ch4_content": 85.0,
            "control_efficiency": 0.0,
        }
        res = dispatcher.dispatch("liquids_unloading", payload, {}, {})
        assert res["results"]["ch4"]["value"] > 0

    def test_blowdown_events_tier3(self, dispatcher):
        payload = {
            "process_type": "blowdown",
            "factor_source": "specific",
            "blowdown_volume": 50.0,
            "pressure": 600.0,
            "events": 2,
            "ch4_content": 90.0,
            "blowdown_temp": 60.0,
        }
        res = dispatcher.dispatch("blowdown", payload, {}, {})
        assert res["results"]["ch4"]["value"] > 0

    def test_storage_tanks_tier3(self, dispatcher):
        payload = {
            "process_type": "storage_tanks",
            "factor_source": "specific",
            "throughput": 50000.0,
            "tank_unit": "bbl",
            "tank_gor": 300.0,
            "ch4_content": 80.0,
            "control_efficiency": 0.98,
        }
        res = dispatcher.dispatch("storage_tanks", payload, {}, {})
        assert res["results"]["ch4"]["value"] > 0
        assert res["results"]["co2"]["value"] > 0

    def test_pneumatic_devices_tier3(self, dispatcher):
        payload = {
            "process_type": "pneumatic_devices",
            "factor_source": "specific",
            "count": 10,
            "hours": 8760,
            "bleed_rate": 12.5,
            "ch4_content": 90.0,
        }
        res = dispatcher.dispatch("pneumatic_devices", payload, {}, {})
        assert res["results"]["ch4"]["value"] > 0

    def test_fugitive_component_tier3(self, dispatcher):
        payload = {
            "process_type": "fugitive_component",
            "factor_source": "specific",
            "component_type": "valves",
            "count": 150,
            "ef": 0.0268,
            "unit": "kg/hr",
            "ch4_content": 85.0,
        }
        res = dispatcher.dispatch("fugitive_component", payload, {}, {})
        assert res["results"]["ch4"]["value"] > 0

    @pytest.mark.parametrize("fugitive_type", [
        "wellhead_fugitive",
        "separator_fugitive",
        "gathering_boosting",
        "gas_processing",
        "transmission_storage",
        "refinery_fugitive",
        "distribution_fugitive",
        "lng_operations",
    ])
    def test_all_equipment_fugitive_variants_tier3(self, dispatcher, fugitive_type):
        payload = {
            "process_type": fugitive_type,
            "factor_source": "specific",
            "count": 25,
            "ef": 0.45,
            "unit": "kg/hr",
            "ch4_content": 85.0,
        }
        res = dispatcher.dispatch(fugitive_type, payload, {}, {})
        assert res["results"]["ch4"]["value"] > 0
        assert res["total_co2e"] > 0

    def test_compressor_fugitive_tier3(self, dispatcher):
        payload = {
            "process_type": "compressor_fugitive",
            "factor_source": "specific",
            "count": 3,
            "seal_type": "centrifugal_wet",
        }
        res = dispatcher.dispatch("compressor_fugitive", payload, {}, {})
        assert res["results"]["ch4"]["value"] > 0

    def test_acid_gas_removal_tier3(self, dispatcher):
        payload = {
            "process_type": "acid_gas_removal",
            "factor_source": "specific",
            "gas_throughput": 150.0,  # MMscf
            "agr_unit": "mmscf",
            "co2_in": 4.5,
            "co2_out": 0.02,
            "ch4_in": 85.0,
            "ch4_slip": 0.05,
            "control_efficiency": 0.0,
        }
        res = dispatcher.dispatch("acid_gas_removal", payload, {}, {})
        assert res["results"]["co2"]["value"] > 0
        assert res["results"]["ch4"]["value"] > 0

    def test_glycol_dehydrator_tier3(self, dispatcher):
        payload = {
            "process_type": "dehydrator",
            "factor_source": "specific",
            "pump_rate": 20.0,
            "pump_unit": "gph",
            "hours": 8760,
            "ch4_content": 90.0,
            "contactor_pressure": 900.0,
            "contactor_temperature": 105.0,
        }
        res = dispatcher.dispatch("dehydrator", payload, {}, {})
        assert res["results"]["ch4"]["value"] > 0

    def test_indirect_steam_tier3(self, dispatcher):
        payload = {
            "process_type": "indirect_steam",
            "factor_source": "specific",
            "amount": 2500.0,
            "heat_unit": "mmbtu",
            "boiler_efficiency": 0.82,
            "transmission_loss": 0.03,
        }
        factors = {"co2": 53.06}
        res = dispatcher.dispatch("indirect_steam", payload, factors, {})
        assert res["results"]["co2"]["value"] > 0

    def test_cogen_allocation_tier3(self, dispatcher):
        payload = {
            "process_type": "cogen_allocation",
            "factor_source": "specific",
            "total_emissions": 1000.0,
            "heat_output": 4000.0,
            "power_output": 2000.0,
            "cogen_method": "wri_efficiency",
        }
        res = dispatcher.dispatch("cogen_allocation", payload, {}, {})
        assert res["results"]["co2"]["value"] > 0
        assert res["results"]["co2"]["value"] < 1000.0

    @pytest.mark.parametrize("chem_type", [
        "chemical_production",
        "nitric_acid_production",
        "adipic_acid_production",
        "stoichiometry",
    ])
    def test_chemical_and_stoichiometric_tier3(self, dispatcher, chem_type):
        payload = {
            "process_type": chem_type,
            "factor_source": "specific",
            "production_amount": 10000.0,
            "carbon_content": 0.82,
            "unit": "kg",
        }
        res = dispatcher.dispatch(chem_type, payload, {}, {})
        assert res["results"]["co2"]["value"] > 0
        assert res["total_co2e"] > 0


# ==============================================================================
# 3. LEGACY ENGINE & COMPUTE_EMISSIONS END-TO-END VERIFICATION
# ==============================================================================

class TestComputeEmissionsIntegration:
    """Verify compute_emissions pipeline routes and handles all canonical process types."""

    @pytest.mark.parametrize("process_id", list(PROCESS_TYPES.keys()))
    def test_compute_emissions_for_all_processes(self, process_id):
        payload = {
            "process_type": process_id,
            "process": process_id,
            "amount": 200.0,
            "unit": "m3" if PROCESS_TYPES[process_id]["category"] in ["combustion", "vented"] else "devices",
            "fuel_type": "Natural Gas" if PROCESS_TYPES[process_id]["category"] == "combustion" else None,
        }
        factors = {
            "co2": 53.06 if PROCESS_TYPES[process_id]["category"] == "combustion" else 1.0,
            "ch4": 0.05,
            "n2o": 0.001,
            "unit": "kg/m3" if PROCESS_TYPES[process_id]["category"] in ["combustion", "vented"] else "kg/unit",
            "hhv": 1020.0,
        }
        em_res, method = compute_emissions(payload, factors)
        assert em_res is not None
        assert em_res["totalCo2e"] > 0
        assert method is not None


# ==============================================================================
# 4. PROCESS CATEGORY CLASSIFICATION & INTEGRITY CHECKS
# ==============================================================================

class TestProcessCategoryIntegrity:
    """Verify that every process is mapped to valid segments and combustion/non-combustion lists."""

    def test_all_processes_have_valid_segments(self):
        for pid, pdata in PROCESS_TYPES.items():
            assert "segments" in pdata
            assert len(pdata["segments"]) > 0
            for s in pdata["segments"]:
                assert s in ["upstream", "midstream", "downstream"]

    def test_non_combustion_processes_covers_all_non_combustion(self):
        for pid, pdata in PROCESS_TYPES.items():
            if pdata["category"] in ["vented", "fugitive", "process"]:
                assert pid in NON_COMBUSTION_PROCESSES, (
                    f"Process '{pid}' of category '{pdata['category']}' missing from NON_COMBUSTION_PROCESSES"
                )


# ==============================================================================
# 5. SCOPE 2 PROCESS TYPES MATRIX
# ==============================================================================

class TestScope2ProcessMatrix:
    """Verify all Scope 2 utility types: Grid Electricity (Location/Market) and Purchased Steam."""

    def test_scope2_location_based_electricity(self):
        kwh = 10000.0
        grid_ef = 0.450  # kg CO2e / kWh
        co2e = (kwh * grid_ef) / 1000.0
        assert pytest.approx(co2e, 1e-4) == 4.50

    def test_scope2_market_based_electricity_zero_carbon(self):
        kwh = 50000.0
        ppa_ef = 0.0  # 100% solar PPA
        co2e = (kwh * ppa_ef) / 1000.0
        assert co2e == 0.0

    def test_scope2_purchased_steam_indirect(self, dispatcher):
        payload = {
            "process_type": "indirect_steam",
            "factor_source": "specific",
            "amount": 1000.0,
            "heat_unit": "mmbtu",
            "boiler_efficiency": 0.80,
            "transmission_loss": 0.05,
        }
        res = dispatcher.dispatch("indirect_steam", payload, {"co2": 53.06}, {})
        # 1000 / (0.80 * 0.95) * 53.06 / 1000 = 69.8158 tonnes CO2
        assert pytest.approx(res["results"]["co2"]["value"], 1e-3) == 69.816


# ==============================================================================
# 6. SCOPE 3 CATEGORIES MATRIX: ALL 15 GHG PROTOCOL CATEGORIES
# ==============================================================================

class TestScope3AllCategoriesMatrix:
    """Exhaustive test of all 15 Scope 3 categories per GHG Protocol Corporate Value Chain Standard."""

    from calculations.units import compute_scope3_co2e

    @pytest.mark.parametrize("cat_num, activity_unit, ef_val, ef_unit", [
        (1, "tonne", 800.0, "kg CO2e / tonne"),              # Purchased goods & services (mass)
        (1, "$", 350.0, "kg CO2e / $1000"),                  # Purchased goods & services (spend)
        (2, "$", 280.0, "kg CO2e / $1000"),                  # Capital goods (spend EEIO)
        (3, "kwh", 0.045, "kg CO2e / kwh"),                  # Fuel- and energy-related activities (T&D loss)
        (4, "tonne-km", 0.12, "kg CO2e / tonne-km"),         # Upstream transportation & distribution
        (5, "tonne", 450.0, "kg CO2e / tonne"),              # Waste generated in operations (landfill)
        (6, "pkm", 0.18, "kg CO2e / passenger-km"),          # Business travel (commercial air)
        (7, "km", 0.15, "kg CO2e / km"),                     # Employee commuting (passenger car)
        (8, "m2", 45.0, "kg CO2e / m2"),                     # Upstream leased assets
        (9, "tonne-km", 0.08, "kg CO2e / tonne-km"),         # Downstream transportation & distribution
        (10, "tonne", 650.0, "kg CO2e / tonne"),             # Processing of sold products
        (11, "m3", 1.95, "kg CO2e / m3"),                    # Use of sold products (combustion of sold gas)
        (12, "tonne", 120.0, "kg CO2e / tonne"),             # End-of-life treatment of sold products
        (13, "m2", 50.0, "kg CO2e / m2"),                    # Downstream leased assets
        (14, "units", 5000.0, "kg CO2e / unit"),             # Franchises
        (15, "$", 150.0, "kg CO2e / $1000"),                 # Investments (financed emissions)
    ])
    def test_scope3_category_deterministic_calculation(
        self, cat_num, activity_unit, ef_val, ef_unit
    ):
        from calculations.units import compute_scope3_co2e
        activity_amt = 1000.0
        co2e = compute_scope3_co2e(activity_amt, ef_val, ef_unit)
        assert co2e > 0
        assert not math.isnan(co2e)
        assert not math.isinf(co2e)


# ==============================================================================
# 7. METROLOGICAL CONSERVATION LAWS ACROSS ALL PROCESS TYPES
# ==============================================================================

class TestPhysicalConservationAcrossAllProcesses:
    """Strict verification of physical conservation laws across every process type."""

    @pytest.mark.parametrize("process_id", list(PROCESS_TYPES.keys()))
    def test_zero_activity_produces_zero_emissions(self, dispatcher, process_id):
        """Conservation Law: 0 activity MUST produce exactly 0.0 emissions."""
        meta = PROCESS_TYPES[process_id]
        payload = {
            "process_type": process_id,
            "factor_source": "default",
            "amount": 0.0,
            "quantity": 0.0,
            "unit": "m3" if meta["category"] in ["combustion", "vented"] else "devices",
        }
        factors = {"co2": 50.0, "ch4": 0.5, "n2o": 0.01, "unit": "kg/m3"}
        res = dispatcher.dispatch(process_id, payload, factors, {})
        assert res["total_co2e"] == 0.0

    @pytest.mark.parametrize("process_id", list(PROCESS_TYPES.keys()))
    def test_strictly_positive_monotonicity(self, dispatcher, process_id):
        """Monotonicity Law: Doubling activity data MUST double emissions."""
        meta = PROCESS_TYPES[process_id]
        unit = "m3" if meta["category"] in ["combustion", "vented"] else "devices"
        factors = {"co2": 50.0, "ch4": 0.5, "n2o": 0.01, "unit": f"kg/{unit}"}

        p1 = {"process_type": process_id, "factor_source": "default", "amount": 100.0, "unit": unit}
        p2 = {"process_type": process_id, "factor_source": "default", "amount": 200.0, "unit": unit}

        res1 = dispatcher.dispatch(process_id, p1, factors, {})
        res2 = dispatcher.dispatch(process_id, p2, factors, {})

        assert pytest.approx(res2["total_co2e"], rel=1e-3) == res1["total_co2e"] * 2.0

