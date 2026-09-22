"""
INDEPENDENT GOLDEN DATASET GENERATOR
Generates independent golden test cases with mathematically derived expected results.
ZERO production dependencies. Uses independent reference models only.
"""

import json
import sys
import os

# Ensure clean imports from validation.reference_model
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from validation.reference_model import (
    ref_calculate_combustion,
    ref_calculate_flaring,
    ref_calculate_pneumatic_devices,
    ref_calculate_blowdown,
    ref_calculate_tank_flashing,
    ref_calculate_agr,
    ref_calculate_dehydrator,
    ref_calculate_component_fugitives,
    ref_calculate_equipment_fugitives,
    ref_calculate_scope2_electricity,
    ref_calculate_scope2_steam,
    ref_calculate_scope2_cooling,
    ref_calculate_scope3,
    ref_calculate_hydrocarbon_stoichiometry,
    ref_normalize_gas_volume,
    resolve_gwp,
)


def generate_all_golden_cases():
    cases = []

    # =========================================================================
    # 1. SCOPE 1: STATIONARY COMBUSTION (Normal, Boundary, Multi-GWP, Multi-Fuel)
    # =========================================================================
    combustion_scenarios = [
        # Normal Natural Gas (m3, Tier 1/2)
        {
            "id": "GOLDEN-S1-COMB-001",
            "type": "stationary_combustion",
            "desc": "Natural gas combustion - standard conditions (AR5 100-yr)",
            "inputs": {"fuel_quantity": 10000.0, "ef_co2": 1.93, "ef_ch4": 0.0001, "ef_n2o": 0.00003},
            "units": {"fuel_unit": "m3", "ef_unit": "kg/m3"},
            "methodology": "API Compendium 2021 Section 5.1 (Standard EF)",
            "factor": {"co2": 1.93, "ch4": 0.0001, "n2o": 0.00003},
            "gwp_std": "AR5", "horizon": "100",
            "source": "API Compendium 2021 Table 5-1",
            "assumptions": "Standard temperature and pressure, Tier 2 default factors",
            "tolerance": 1e-4,
        },
        # Thermodynamic Normalization (Hot & Pressurized Fuel Gas)
        {
            "id": "GOLDEN-S1-COMB-002",
            "type": "stationary_combustion",
            "desc": "Natural gas combustion with thermodynamic normalization (50°C, 100 psig)",
            "inputs": {
                "fuel_quantity": 5000.0, "ef_co2": 1.93, "ef_ch4": 0.0001, "ef_n2o": 0.00003,
                "temp": 50.0, "temp_unit": "C", "press": 100.0, "press_unit": "psig", "z_factor": 0.98,
            },
            "units": {"fuel_unit": "m3", "ef_unit": "kg/m3"},
            "methodology": "API Compendium 2021 Section 4.2.1 (Thermodynamic Normalization)",
            "factor": {"co2": 1.93, "ch4": 0.0001, "n2o": 0.00003},
            "gwp_std": "AR5", "horizon": "100",
            "source": "API Compendium 2021 Eq. 4-4",
            "assumptions": "Ideal gas with Z=0.98 real gas correction",
            "tolerance": 1e-3,
        },
        # Tier 3 Gas Composition Override (Carbon Balance)
        {
            "id": "GOLDEN-S1-COMB-003",
            "type": "stationary_combustion",
            "desc": "Fuel gas combustion - Tier 3 detailed gas composition carbon balance",
            "inputs": {
                "fuel_quantity": 20000.0, "combustion_efficiency": 0.995,
                "gas_composition": {"c1": 0.88, "c2": 0.06, "c3": 0.03, "ic4": 0.01, "nc4": 0.01, "co2": 0.01},
            },
            "units": {"fuel_unit": "m3", "ef_unit": "stoichiometric"},
            "methodology": "API Compendium 2021 Section 5.1.3 (Tier 3 Carbon Mass Balance)",
            "factor": "Gas Composition",
            "gwp_std": "AR5", "horizon": "100",
            "source": "API Compendium 2021 Table 5-4",
            "assumptions": "Dual carbon moles balance + methane slip (1-eta_c)",
            "tolerance": 1e-3,
        },
        # Diesel Fuel Combustion (Liquid, bbl, AR6)
        {
            "id": "GOLDEN-S1-COMB-004",
            "type": "stationary_combustion",
            "desc": "Diesel fuel combustion in generators (bbl, AR6 100-yr)",
            "inputs": {"fuel_quantity": 500.0, "ef_co2": 432.0, "ef_ch4": 0.018, "ef_n2o": 0.0035, "fuel_type": "liquids"},
            "units": {"fuel_unit": "bbl", "ef_unit": "kg/bbl"},
            "methodology": "API Compendium 2021 Table 5-3 (Liquid Fuels)",
            "factor": {"co2": 432.0, "ch4": 0.018, "n2o": 0.0035},
            "gwp_std": "AR6", "horizon": "100",
            "source": "API Compendium 2021 Table 5-3",
            "assumptions": "Standard diesel density 850 kg/m3",
            "tolerance": 1e-3,
        },
        # Boundary: Zero Activity
        {
            "id": "GOLDEN-S1-COMB-005",
            "type": "stationary_combustion",
            "desc": "Boundary: Zero fuel quantity must yield exactly zero emissions",
            "inputs": {"fuel_quantity": 0.0, "ef_co2": 1.93, "ef_ch4": 0.0001, "ef_n2o": 0.00003},
            "units": {"fuel_unit": "m3", "ef_unit": "kg/m3"},
            "methodology": "Mathematical boundary condition f(0)=0",
            "factor": {"co2": 1.93, "ch4": 0.0001, "n2o": 0.00003},
            "gwp_std": "AR5", "horizon": "100",
            "source": "Conservation of Mass",
            "assumptions": "No fuel, no emissions",
            "tolerance": 0.0,
        },
        # Boundary: Large Quantity (1 Million m3)
        {
            "id": "GOLDEN-S1-COMB-006",
            "type": "stationary_combustion",
            "desc": "Boundary: High volume fuel combustion (1,000,000 m3)",
            "inputs": {"fuel_quantity": 1_000_000.0, "ef_co2": 1.93, "ef_ch4": 0.0001, "ef_n2o": 0.00003},
            "units": {"fuel_unit": "m3", "ef_unit": "kg/m3"},
            "methodology": "Large scale industrial stationary combustion",
            "factor": {"co2": 1.93, "ch4": 0.0001, "n2o": 0.00003},
            "gwp_std": "AR5", "horizon": "100",
            "source": "API Compendium 2021",
            "assumptions": "Linear scaling without numerical overflow",
            "tolerance": 1e-2,
        },
    ]

    for sc in combustion_scenarios:
        res = ref_calculate_combustion(
            fuel_quantity=sc["inputs"]["fuel_quantity"],
            ef_co2=sc["inputs"].get("ef_co2"),
            ef_ch4=sc["inputs"].get("ef_ch4"),
            ef_n2o=sc["inputs"].get("ef_n2o"),
            fuel_unit=sc["units"]["fuel_unit"],
            ef_unit=sc["units"]["ef_unit"],
            combustion_efficiency=sc["inputs"].get("combustion_efficiency", 0.995),
            temp=sc["inputs"].get("temp"),
            temp_unit=sc["inputs"].get("temp_unit", "C"),
            press=sc["inputs"].get("press"),
            press_unit=sc["inputs"].get("press_unit", "psig"),
            z_factor=sc["inputs"].get("z_factor", 1.0),
            gwp_standard=sc["gwp_std"],
            gwp_horizon=sc["horizon"],
            gas_composition=sc["inputs"].get("gas_composition"),
        )
        norm_q = ref_normalize_gas_volume(
            sc["inputs"]["fuel_quantity"],
            temp=sc["inputs"].get("temp"),
            press=sc["inputs"].get("press"),
            press_unit=sc["inputs"].get("press_unit", "psig"),
            z_factor=sc["inputs"].get("z_factor", 1.0),
        )
        cases.append({
            "test_id": sc["id"],
            "calculation_type": sc["type"],
            "description": sc["desc"],
            "inputs": sc["inputs"],
            "units": sc["units"],
            "methodology": sc["methodology"],
            "factor": sc["factor"],
            "GWP": {"standard": sc["gwp_std"], "horizon": sc["horizon"], "values": resolve_gwp(sc["gwp_std"], sc["horizon"])},
            "independent_intermediate_values": {"normalized_quantity": norm_q},
            "independent_expected_result": res,
            "tolerance": sc["tolerance"],
            "source": sc["source"],
            "assumptions": sc["assumptions"],
        })

    # =========================================================================
    # 2. SCOPE 1: FLARING (Dual-Efficiency Model)
    # =========================================================================
    flaring_scenarios = [
        # Elevated Flare (Normal)
        {
            "id": "GOLDEN-S1-FLARE-001",
            "type": "flaring",
            "desc": "Elevated flare - dual efficiency 98.4% combustion, 1.6% methane slip",
            "inputs": {"gas_volume": 50000.0, "ch4_fraction": 0.88, "flare_type": "elevated", "gas_composition": {"co2": 0.02}},
            "units": {"gas_unit": "m3"},
            "methodology": "API Compendium 2021 Section 5.2 (Dual-efficiency)",
            "factor": {"eta_c": 0.984, "eta_d": 0.980},
            "gwp_std": "AR5", "horizon": "100",
            "source": "API Compendium 2021 Eq. 5-3, 5-4",
            "assumptions": "Uncombusted CH4 slip = 1 - eta_c; CO2 from combusted HC + native CO2",
            "tolerance": 1e-3,
        },
        # Enclosed Ground Flare (Higher Efficiency 99.6%)
        {
            "id": "GOLDEN-S1-FLARE-002",
            "type": "flaring",
            "desc": "Enclosed ground flare - high efficiency 99.6% (AR6 100-yr)",
            "inputs": {"gas_volume": 25000.0, "ch4_fraction": 0.92, "flare_type": "enclosed"},
            "units": {"gas_unit": "m3"},
            "methodology": "API Compendium 2021 Section 5.2 (Enclosed Ground)",
            "factor": {"eta_c": 0.996, "eta_d": 0.995},
            "gwp_std": "AR6", "horizon": "100",
            "source": "API Compendium 2021 Table 5-11",
            "assumptions": "Enclosed combustion chamber with lower unburnt hydrocarbon slip",
            "tolerance": 1e-3,
        },
        # Open Pit Flare (Lower Efficiency 92.0%)
        {
            "id": "GOLDEN-S1-FLARE-003",
            "type": "flaring",
            "desc": "Open pit flare - lower efficiency 92.0% (8% uncombusted methane slip)",
            "inputs": {"gas_volume": 10000.0, "ch4_fraction": 0.85, "flare_type": "pit"},
            "units": {"gas_unit": "m3"},
            "methodology": "API Compendium 2021 Section 5.2 (Open Pit)",
            "factor": {"eta_c": 0.920, "eta_d": 0.950},
            "gwp_std": "AR5", "horizon": "100",
            "source": "API Compendium 2021 Table 5-11",
            "assumptions": "Sub-optimal air mixing in open pit",
            "tolerance": 1e-3,
        },
    ]

    for sc in flaring_scenarios:
        res = ref_calculate_flaring(
            gas_volume=sc["inputs"]["gas_volume"],
            ch4_fraction=sc["inputs"].get("ch4_fraction", 0.90),
            flare_type=sc["inputs"].get("flare_type", "elevated"),
            gas_unit=sc["units"]["gas_unit"],
            gwp_standard=sc["gwp_std"],
            gwp_horizon=sc["horizon"],
            gas_composition=sc["inputs"].get("gas_composition"),
        )
        cases.append({
            "test_id": sc["id"],
            "calculation_type": sc["type"],
            "description": sc["desc"],
            "inputs": sc["inputs"],
            "units": sc["units"],
            "methodology": sc["methodology"],
            "factor": sc["factor"],
            "GWP": {"standard": sc["gwp_std"], "horizon": sc["horizon"], "values": resolve_gwp(sc["gwp_std"], sc["horizon"])},
            "independent_intermediate_values": {},
            "independent_expected_result": res,
            "tolerance": sc["tolerance"],
            "source": sc["source"],
            "assumptions": sc["assumptions"],
        })

    # =========================================================================
    # 3. SCOPE 1: VENTING, BLOWDOWN & MIDSTREAM
    # =========================================================================
    vent_scenarios = [
        # Pneumatic Devices
        {
            "id": "GOLDEN-S1-VENT-001",
            "type": "pneumatic_devices",
            "desc": "Intermittent pneumatic controllers (10 devices, 8760 hrs)",
            "inputs": {"device_count": 10, "hours": 8760, "device_type": "intermittent", "ch4_fraction": 0.90},
            "units": {"rate_unit": "scf/hr/device"},
            "methodology": "API Compendium 2021 Table 5-15",
            "factor": 13.5,
            "gwp_std": "AR5", "horizon": "100",
            "source": "API Compendium 2021 Table 5-15",
            "assumptions": "Continuous operation 8760 hours, 13.5 scf/hr",
            "tolerance": 1e-3,
        },
        # Blowdown / Depressuring
        {
            "id": "GOLDEN-S1-VENT-002",
            "type": "blowdown",
            "desc": "Compressor station emergency depressuring blowdown (50 m3 vessel, 600 psig -> 0 psig)",
            "inputs": {"vessel_volume_m3": 50.0, "initial_press": 600.0, "final_press": 0.0, "events": 2, "ch4_fraction": 0.88},
            "units": {"volume_unit": "m3", "press_unit": "psig"},
            "methodology": "API Compendium 2021 Section 5.4 (Blowdown)",
            "factor": "Boyle-Mariotte Ideal Gas Law",
            "gwp_std": "AR5", "horizon": "100",
            "source": "API Compendium 2021 Eq. 5-14",
            "assumptions": "Isothermal depressurization to standard atmosphere",
            "tolerance": 1e-3,
        },
        # Acid Gas Removal (AGR)
        {
            "id": "GOLDEN-S1-MID-001",
            "type": "acid_gas_removal",
            "desc": "Amine AGR sweetening unit CO2 venting (100,000 m3 gas, 4% CO2 in, 0.01% out)",
            "inputs": {"feed_gas_volume": 100000.0, "co2_inlet_fraction": 0.04, "co2_outlet_fraction": 0.0001, "control_eff": 0.0},
            "units": {"volume_unit": "m3"},
            "methodology": "API Compendium 2021 Section 5.5",
            "factor": "Mass balance delta CO2",
            "gwp_std": "AR5", "horizon": "100",
            "source": "API Compendium 2021 Eq. 5-18",
            "assumptions": "100% amine regeneration venting to atmosphere without carbon capture",
            "tolerance": 1e-3,
        },
        # Component Fugitives
        {
            "id": "GOLDEN-S1-FUG-001",
            "type": "component_fugitive",
            "desc": "Gas plant valve screening leaks (150 valves, 8760 hrs)",
            "inputs": {"component_count": 150, "hours": 8760, "component_type": "valve", "ch4_fraction": 0.90},
            "units": {"count_unit": "components"},
            "methodology": "API Compendium 2021 Table 6-1",
            "factor": 0.0045,
            "gwp_std": "AR5", "horizon": "100",
            "source": "API Compendium 2021 Table 6-1",
            "assumptions": "Gas service valves default screening emission factor 0.0045 kg/hr/comp",
            "tolerance": 1e-3,
        },
    ]

    for sc in vent_scenarios:
        if sc["type"] == "pneumatic_devices":
            res = ref_calculate_pneumatic_devices(
                device_count=sc["inputs"]["device_count"],
                hours=sc["inputs"]["hours"],
                device_type=sc["inputs"]["device_type"],
                ch4_fraction=sc["inputs"]["ch4_fraction"],
                gwp_standard=sc["gwp_std"],
                gwp_horizon=sc["horizon"],
            )
        elif sc["type"] == "blowdown":
            res = ref_calculate_blowdown(
                vessel_volume_m3=sc["inputs"]["vessel_volume_m3"],
                initial_press=sc["inputs"]["initial_press"],
                final_press=sc["inputs"]["final_press"],
                events=sc["inputs"]["events"],
                ch4_fraction=sc["inputs"]["ch4_fraction"],
                gwp_standard=sc["gwp_std"],
                gwp_horizon=sc["horizon"],
            )
        elif sc["type"] == "acid_gas_removal":
            res = ref_calculate_agr(
                feed_gas_volume=sc["inputs"]["feed_gas_volume"],
                co2_inlet_fraction=sc["inputs"]["co2_inlet_fraction"],
                co2_outlet_fraction=sc["inputs"]["co2_outlet_fraction"],
                control_eff=sc["inputs"]["control_eff"],
                gwp_standard=sc["gwp_std"],
                gwp_horizon=sc["horizon"],
            )
        elif sc["type"] == "component_fugitive":
            res = ref_calculate_component_fugitives(
                component_count=sc["inputs"]["component_count"],
                hours=sc["inputs"]["hours"],
                component_type=sc["inputs"]["component_type"],
                ch4_fraction=sc["inputs"]["ch4_fraction"],
                gwp_standard=sc["gwp_std"],
                gwp_horizon=sc["horizon"],
            )

        cases.append({
            "test_id": sc["id"],
            "calculation_type": sc["type"],
            "description": sc["desc"],
            "inputs": sc["inputs"],
            "units": sc["units"],
            "methodology": sc["methodology"],
            "factor": sc["factor"],
            "GWP": {"standard": sc["gwp_std"], "horizon": sc["horizon"], "values": resolve_gwp(sc["gwp_std"], sc["horizon"])},
            "independent_intermediate_values": {},
            "independent_expected_result": res,
            "tolerance": sc["tolerance"],
            "source": sc["source"],
            "assumptions": sc["assumptions"],
        })

    # =========================================================================
    # 4. SCOPE 2: INDIRECT EMISSIONS (Location, Market, Steam, Cooling)
    # =========================================================================
    scope2_scenarios = [
        {
            "id": "GOLDEN-S2-ELEC-001",
            "type": "scope2_electricity",
            "desc": "Purchased electricity - Location-based method (500,000 kWh)",
            "inputs": {"electricity_kwh": 500000.0, "emission_factor_kg_kwh": 0.582, "method": "location_based"},
            "units": {"electricity_unit": "kWh", "ef_unit": "kg CO2e/kWh"},
            "methodology": "GHG Protocol Scope 2 Guidance (Location-based)",
            "factor": 0.582,
            "gwp_std": "AR5", "horizon": "100",
            "source": "IEA National Grid Emission Factors",
            "assumptions": "Standard grid average emission intensity without contractual instruments",
            "tolerance": 1e-4,
        },
        {
            "id": "GOLDEN-S2-ELEC-002",
            "type": "scope2_electricity",
            "desc": "Purchased electricity - Market-based method with zero-emission PPA",
            "inputs": {"electricity_kwh": 250000.0, "emission_factor_kg_kwh": 0.0, "method": "market_based"},
            "units": {"electricity_unit": "kWh", "ef_unit": "kg CO2e/kWh"},
            "methodology": "GHG Protocol Scope 2 Guidance (Market-based)",
            "factor": 0.0,
            "gwp_std": "AR5", "horizon": "100",
            "source": "Renewable Power Purchase Agreement (PPA)",
            "assumptions": "Guaranteed origin contractual zero-emission solar/wind power",
            "tolerance": 0.0,
        },
        {
            "id": "GOLDEN-S2-STEAM-001",
            "type": "scope2_steam",
            "desc": "Purchased industrial steam (1,200 tonnes, 80% boiler efficiency, 5% line loss)",
            "inputs": {"steam_tonnes": 1200.0, "ef_kg_per_tonne": 180.0, "boiler_efficiency": 0.80, "loss_factor": 0.05},
            "units": {"steam_unit": "tonnes", "ef_unit": "kg CO2e/tonne"},
            "methodology": "GHG Protocol Scope 2 Guidance (Purchased Steam)",
            "factor": 180.0,
            "gwp_std": "AR5", "horizon": "100",
            "source": "Supplier Steam Delivery Invoices",
            "assumptions": "Boiler thermal efficiency 80%, pipe distribution loss 5%",
            "tolerance": 1e-3,
        },
    ]

    for sc in scope2_scenarios:
        if sc["type"] == "scope2_electricity":
            res = ref_calculate_scope2_electricity(
                sc["inputs"]["electricity_kwh"],
                sc["inputs"]["emission_factor_kg_kwh"],
                method=sc["inputs"]["method"],
            )
        elif sc["type"] == "scope2_steam":
            res = ref_calculate_scope2_steam(
                sc["inputs"]["steam_tonnes"],
                ef_kg_per_tonne=sc["inputs"]["ef_kg_per_tonne"],
                boiler_efficiency=sc["inputs"]["boiler_efficiency"],
                loss_factor=sc["inputs"]["loss_factor"],
            )
        cases.append({
            "test_id": sc["id"],
            "calculation_type": sc["type"],
            "description": sc["desc"],
            "inputs": sc["inputs"],
            "units": sc["units"],
            "methodology": sc["methodology"],
            "factor": sc["factor"],
            "GWP": {"standard": sc["gwp_std"], "horizon": sc["horizon"], "values": resolve_gwp(sc["gwp_std"], sc["horizon"])},
            "independent_intermediate_values": {},
            "independent_expected_result": res,
            "tolerance": sc["tolerance"],
            "source": sc["source"],
            "assumptions": sc["assumptions"],
        })

    # =========================================================================
    # 5. SCOPE 3: VALUE CHAIN CATEGORIES (Categories 1, 4, 6, 11)
    # =========================================================================
    scope3_scenarios = [
        {
            "id": "GOLDEN-S3-CAT1-001",
            "type": "scope3",
            "desc": "Category 1: Purchased Goods & Services (Spend-based $150,000)",
            "inputs": {"category_id": 1, "activity_value": 150000.0, "emission_factor": 0.42, "ef_unit": "kg/USD"},
            "units": {"activity_unit": "USD", "ef_unit": "kg CO2e/USD"},
            "methodology": "GHG Protocol Scope 3 Category 1 (Spend-based)",
            "factor": 0.42,
            "gwp_std": "AR5", "horizon": "100",
            "source": "US EPA USEEIO Supply Chain Factors",
            "assumptions": "Sector spend-based input-output multiplier",
            "tolerance": 1e-4,
        },
        {
            "id": "GOLDEN-S3-CAT4-001",
            "type": "scope3",
            "desc": "Category 4: Upstream Freight Transport (100,000 tonne-km, diesel truck)",
            "inputs": {"category_id": 4, "activity_value": 100000.0, "emission_factor": 0.095, "ef_unit": "kg/tkm"},
            "units": {"activity_unit": "tonne-km", "ef_unit": "kg CO2e/tkm"},
            "methodology": "GHG Protocol Scope 3 Category 4 (Activity-based)",
            "factor": 0.095,
            "gwp_std": "AR5", "horizon": "100",
            "source": "GLEC Framework Freight Factors",
            "assumptions": "Heavy duty commercial freight transport",
            "tolerance": 1e-4,
        },
        {
            "id": "GOLDEN-S3-CAT6-001",
            "type": "scope3",
            "desc": "Category 6: Business Travel (40,000 passenger-km, long-haul aviation)",
            "inputs": {"category_id": 6, "activity_value": 40000.0, "emission_factor": 0.102, "ef_unit": "kg/pkm"},
            "units": {"activity_unit": "passenger-km", "ef_unit": "kg CO2e/pkm"},
            "methodology": "GHG Protocol Scope 3 Category 6 (Distance-based)",
            "factor": 0.102,
            "gwp_std": "AR5", "horizon": "100",
            "source": "UK DEFRA / BEIS Flight Conversion Factors",
            "assumptions": "Long-haul flights without radiative forcing multiplier",
            "tolerance": 1e-4,
        },
        {
            "id": "GOLDEN-S3-CAT11-001",
            "type": "scope3",
            "desc": "Category 11: Use of Sold Products (Direct combustion of 10,000 bbl sold crude oil)",
            "inputs": {"category_id": 11, "activity_value": 10000.0, "emission_factor": 432.0, "ef_unit": "kg/bbl"},
            "units": {"activity_unit": "bbl", "ef_unit": "kg CO2e/bbl"},
            "methodology": "GHG Protocol Scope 3 Category 11 (Sold Fuel Combustion)",
            "factor": 432.0,
            "gwp_std": "AR5", "horizon": "100",
            "source": "IPIECA / API Guidelines for Scope 3 Category 11",
            "assumptions": "End-use combustion factor for light sweet crude oil",
            "tolerance": 1e-3,
        },
    ]

    for sc in scope3_scenarios:
        res = ref_calculate_scope3(
            category_id=sc["inputs"]["category_id"],
            activity_value=sc["inputs"]["activity_value"],
            emission_factor=sc["inputs"]["emission_factor"],
            ef_unit=sc["inputs"]["ef_unit"],
        )
        cases.append({
            "test_id": sc["id"],
            "calculation_type": sc["type"],
            "description": sc["desc"],
            "inputs": sc["inputs"],
            "units": sc["units"],
            "methodology": sc["methodology"],
            "factor": sc["factor"],
            "GWP": {"standard": sc["gwp_std"], "horizon": sc["horizon"], "values": resolve_gwp(sc["gwp_std"], sc["horizon"])},
            "independent_intermediate_values": {},
            "independent_expected_result": res,
            "tolerance": sc["tolerance"],
            "source": sc["source"],
            "assumptions": sc["assumptions"],
        })

    # =========================================================================
    # 6. STOICHIOMETRY & HYDROCARBON MASS BALANCE
    # =========================================================================
    stoich_scenarios = [
        {"id": "GOLDEN-STOICH-001", "name": "Methane", "n": 1, "m": 4},
        {"id": "GOLDEN-STOICH-002", "name": "Ethane", "n": 2, "m": 6},
        {"id": "GOLDEN-STOICH-003", "name": "Propane", "n": 3, "m": 8},
        {"id": "GOLDEN-STOICH-004", "name": "Butane", "n": 4, "m": 10},
    ]

    for sc in stoich_scenarios:
        res = ref_calculate_hydrocarbon_stoichiometry(sc["n"], sc["m"])
        cases.append({
            "test_id": sc["id"],
            "calculation_type": "stoichiometry",
            "description": f"Stoichiometric reaction and carbon balance for {sc['name']} (C{sc['n']}H{sc['m']})",
            "inputs": {"n_carbons": sc["n"], "m_hydrogens": sc["m"], "fuel": sc["name"]},
            "units": {"n": "moles", "m": "moles", "yield": "kg product / kg fuel"},
            "methodology": "Lavoisier Atomic Mass Conservation",
            "factor": "NIST IUPAC Atomic Weights",
            "GWP": "N/A",
            "independent_intermediate_values": {"molecular_weight": res["mw_fuel"]},
            "independent_expected_result": res,
            "tolerance": 1e-6,
            "source": "NIST Physical Reference Data",
            "assumptions": "Complete stoichiometric conversion to CO2 and H2O",
        })

    return cases


if __name__ == "__main__":
    out_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "golden_cases.json"))
    cases = generate_all_golden_cases()
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)
    print(f"Generated {len(cases)} clean-slate golden test cases saved to {out_file}")
