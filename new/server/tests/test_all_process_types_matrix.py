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

def _activity_unit(process_id, category):
    """Activity unit of a generic test row; mud degassing (Table 6-2) is per drilling day."""
    if process_id in ("drilling", "mud_degassing"):
        return "days"
    return "m3" if category in ["combustion", "vented"] else "devices"



@pytest.fixture(scope="module")
def dispatcher():
    return CalculationDispatcher()


# ==============================================================================
# 1. TIER 1 MATRIX: EVERY PROCESS TYPE WITH CATALOG/DEFAULT EMISSION FACTORS
# ==============================================================================

# Hand-worked Tier 1 results of the generic rows below (100 units, factors CO2 1.0 / CH4 0.5 / N2O 0.01 kg per unit,
# combustion CO2 50 kg per m3), in tonnes. The processes with their own Compendium table ignore (or reinterpret) the
# generic factor, so their values come from that table:
#   drilling: 100 drilling days x 0.0458 t CH4/day (Table 6-2, water-based mud, onshore);
#   completions: 100 m3 of metered flowback x 80 % CH4 x 16.04 kg/kmol / 23.685 m3/kmol = 54.18 kg CH4 (Eq 6-4);
#   liquids_unloading: 100 wells x 1.774 t CH4/well-year (Table 6-11, plunger lift);
#   associated_gas_venting: 100 m3 = 628.981 bbl of oil x 0.5 kg CH4/bbl (the dispatcher reads a Tier 1 CH4 factor of
#   this process as kg per bbl).
_COMBUSTION_TIER1 = (5.0, 0.05, 0.001)
_GENERIC_TIER1 = (0.1, 0.05, 0.001)
_SPECIAL_TIER1 = {
    "associated_gas_venting": (0.0, 628.981077 * 0.5 / 1000.0, 0.0),
    "drilling": (0.0, 100 * 0.0458, 0.0),
    "completions": (0.0, 100 * 0.80 * 16.04 / 23.685 / 1000.0, 0.0),
    "liquids_unloading": (0.0, 100 * 1.774, 0.0),
}
_AR5 = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}


def _gas(res, gas):
    r = res["results"].get(gas)
    return float(r["value"] if isinstance(r, dict) else (r or 0.0))


def _expected_tier1(process_id, category):
    if process_id in _SPECIAL_TIER1:
        return _SPECIAL_TIER1[process_id]
    return _COMBUSTION_TIER1 if category == "combustion" else _GENERIC_TIER1


class TestAllProcessTypesTier1:
    """Every process type in PROCESS_TYPES dispatches with catalog-style factors and returns the hand-worked gases and
    CO2e (AR5: 1 / 28 / 265)."""

    @pytest.mark.parametrize("process_id", list(PROCESS_TYPES.keys()))
    def test_tier1_every_canonical_process_type(self, dispatcher, process_id):
        meta = PROCESS_TYPES[process_id]
        payload = {
            "process_type": process_id,
            "factor_source": "default",
            "amount": 100.0,
            "quantity": 100.0,
            "unit": "wells" if process_id == "liquids_unloading" else _activity_unit(process_id, meta["category"]),
            "fuel_type": "Natural Gas" if meta["category"] == "combustion" else None,
        }
        if process_id == "completions":
            # without a catalog code the 100 m3 is a measured flowback volume: it needs the gas analysis
            payload["ch4_content"] = 80
        factor_data = {
            "co2": 50.0 if meta["category"] == "combustion" else 1.0,
            "ch4": 0.5,
            "n2o": 0.01,
            "unit": "kg/m3" if meta["category"] in ["combustion", "vented"] else "kg/unit",
            "hhv": 1020.0,
        }
        res = dispatcher.dispatch(process_id, payload, factor_data, {}, gwp_dict=_AR5)
        co2, ch4, n2o = _expected_tier1(process_id, meta["category"])
        assert _gas(res, "co2") == pytest.approx(co2, rel=2e-3, abs=1e-12), process_id
        assert _gas(res, "ch4") == pytest.approx(ch4, rel=2e-3, abs=1e-12), process_id
        assert _gas(res, "n2o") == pytest.approx(n2o, rel=2e-3, abs=1e-12), process_id
        assert res["total_co2e"] == pytest.approx(co2 + 28.0 * ch4 + 265.0 * n2o, rel=2e-3), process_id

    def test_tier1_utilities_and_aliases(self, dispatcher):
        """Process types outside PROCESS_TYPES (indirect steam, cogen, fccu, stoichiometry) take the generic factor
        rows: 250 mmbtu x 53.06 kg CO2 / 0.001 kg CH4 / 0.0001 kg N2O per mmbtu = 13.265 / 0.00025 / 0.000025 t."""
        for p in ["indirect_steam", "cogen_allocation", "stoichiometry", "fccu"]:
            payload = {
                "process_type": p,
                "factor_source": "default",
                "amount": 250.0,
                # audit BUG-027: a kg/MMBtu factor applied to tonnes needs a heating value; these
                # generic dispatch checks therefore use the factor's energy unit
                "unit": "mmbtu",
            }
            factors = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/mmbtu"}
            res = dispatcher.dispatch(p, payload, factors, {}, gwp_dict=_AR5)
            assert _gas(res, "co2") == pytest.approx(250 * 53.06 / 1000.0, rel=1e-9), p
            assert _gas(res, "ch4") == pytest.approx(250 * 0.001 / 1000.0, rel=1e-9), p
            assert _gas(res, "n2o") == pytest.approx(250 * 0.0001 / 1000.0, rel=1e-9), p
            assert res["total_co2e"] == pytest.approx(13.265 + 28 * 0.00025 + 265 * 0.000025, rel=1e-9), p


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
        # carbon balance on 1,000 m3: 0.85 CH4 + 2 x 0.10 C2H6 = 1.05 mol C/mol at 99.5 % combustion, plus 2 % CO2;
        # slip = 0.5 % of the CH4. 60 F molar volume 23.685 m3/kmol; AR5 GWP of CH4 28.
        rho_co2, rho_ch4 = 44.01 / 23.685, 16.04 / 23.685
        co2 = 1000 * (1.05 * 0.995 + 0.02) * rho_co2 / 1000
        ch4 = 1000 * 0.85 * 0.005 * rho_ch4 / 1000
        assert res["results"]["co2"]["value"] == pytest.approx(co2, rel=1e-9)
        assert res["results"]["ch4"]["value"] == pytest.approx(ch4, rel=1e-9)
        assert res["total_co2e"] == pytest.approx(co2 + 28.0 * ch4, rel=1e-9)

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
        # 500 L = 132.086 gal x 138,000 Btu/gal = 18.228 MMBtu; kg/MMBtu factors; AR5 GWP 28 (CH4) and 265 (N2O)
        mmbtu = 500 * 0.264172052 * 138000 / 1e6
        assert res["results"]["co2"]["value"] == pytest.approx(mmbtu * 73.96 / 1000, rel=1e-6)
        assert res["total_co2e"] == pytest.approx(mmbtu * (73.96 + 0.003 * 28 + 0.0006 * 265) / 1000, rel=1e-6)

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
        # 5,000 m3 at 85 % CH4 and 3 % CO2; default flare: 96.5 % of the carbon to CO2, 98 % of the CH4 destroyed
        rho_co2, rho_ch4 = 44.01 / 23.685, 16.04 / 23.685
        assert res["results"]["co2"]["value"] == pytest.approx(5000 * (0.85 * 0.965 + 0.03) * rho_co2 / 1000, rel=1e-9)
        assert res["results"]["ch4"]["value"] == pytest.approx(5000 * 0.85 * 0.02 * rho_ch4 / 1000, rel=1e-9)

    def test_drilling_mud_degassing_tier3(self, dispatcher):
        payload = {
            "process_type": "drilling",
            "factor_source": "specific",
            "amount": 30.0,
            "unit": "days",  # Table 6-2 is per drilling day
            "mud_type": "water_based",
        }
        factors = {"ch4": 0.05}
        res = dispatcher.dispatch("drilling", payload, factors, {})
        # Table 6-2 onshore water-based mud: 0.0458 t CH4 per drilling day (the factor passed in is not used)
        assert res["results"]["ch4"]["value"] == pytest.approx(30 * 0.0458, rel=1e-9)

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
        # 15,000 m3 flowback at 80 % CH4; control_efficiency 0.95 = 95 % of the gas to a flare at the default 98 %
        # CH4 destruction / 96.5 % carbon conversion, the other 5 % vented
        v_ch4 = 15000 * 0.80
        rho_co2, rho_ch4 = 44.01 / 23.685, 16.04 / 23.685
        assert res["results"]["ch4"]["value"] == pytest.approx(v_ch4 * rho_ch4 / 1000 * (0.05 + 0.95 * 0.02), rel=1e-6)
        assert res["results"]["co2"]["value"] == pytest.approx(v_ch4 * rho_co2 / 1000 * 0.95 * 0.965, rel=1e-6)

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
        # Eq 6-10 without a flow-line term: 4 events x 0.37e-3 x D^2 (2.5 in) x depth (3,000 ft) x 350 psig = 9,712.5 scf
        # of whole gas, 85 % CH4, uncontrolled
        scf = 4 * 0.37e-3 * 2.5 ** 2 * 3000 * 350
        assert res["results"]["ch4"]["value"] == pytest.approx(scf / 379.3 * 0.85 * 16.04 / 2204.62, rel=5e-3)

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
        # 50 m3 at 600 psig and 60 (C, the default unit), 2 events, 90 % CH4: V_std = V x P_abs/14.696 x 288.706 K/T, Z = 1
        v_std = 50 * (600 + 14.696) / 14.696 * 288.706 / (60 + 273.15)
        assert res["results"]["ch4"]["value"] == pytest.approx(2 * v_std * 0.90 * (16.04 / 23.685) / 1000, rel=1e-5)

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
        # flash gas = 50,000 bbl x 300 scf/bbl = 15e6 scf, 80 % CH4. An entered efficiency of 0.98 is the efficiency of the
        # flare: 98 % of the CH4 destroyed and 98 % of the carbon converted to CO2 (the same figure for both)
        v_ch4 = 50000 * 300 * 0.028316846592 * 0.80
        rho_co2, rho_ch4 = 44.01 / 23.685, 16.04 / 23.685
        assert res["results"]["ch4"]["value"] == pytest.approx(v_ch4 * rho_ch4 / 1000 * 0.02, rel=1e-6)
        assert res["results"]["co2"]["value"] == pytest.approx(v_ch4 * rho_co2 / 1000 * 0.98, rel=1e-6)

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
        # 10 devices x 8,760 h x 12.5 scf/h = 1,095,000 scf of gas at 90 % CH4
        assert res["results"]["ch4"]["value"] == pytest.approx(
            10 * 8760 * 12.5 * 0.028316846592 * 0.90 * (16.04 / 23.685) / 1000, rel=1e-9)

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
        # 150 valves x 0.0268 kg TOC/h x 8,760 h = 35.2 t TOC; gas-service TOC is 92.0 wt % CH4 (Compendium Table C-1)
        assert res["results"]["ch4"]["value"] == pytest.approx(150 * 0.0268 * 8760 / 1000 * 0.920, rel=1e-9)

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
        # 25 sources x 0.45 kg/h x 8,760 h = 98.55 t of gas; the equipment route takes ch4_content (85 %) as the CH4 share
        assert res["results"]["ch4"]["value"] == pytest.approx(25 * 0.45 * 8760 / 1000 * 0.85, rel=1e-9)
        assert res["total_co2e"] == pytest.approx(28.0 * res["results"]["ch4"]["value"], rel=1e-9)

    def test_compressor_fugitive_tier3(self, dispatcher):
        payload = {
            "process_type": "compressor_fugitive",
            "factor_source": "specific",
            "count": 3,
            "seal_type": "centrifugal_wet",
        }
        res = dispatcher.dispatch("compressor_fugitive", payload, {}, {})
        # production wet-seal degassing 0.026 t CH4/compressor-hour (Compendium 6.4.2) x 3 compressors x 8,760 h
        assert res["results"]["ch4"]["value"] == pytest.approx(3 * 0.026 * 8760, rel=1e-9)

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
        # 150 MMscf in: CO2 removed = V x (4.5 % - 0.02 %) / (1 - 0.02 %) vented; CH4 slip = V x 85 % x 0.05 (a FRACTION of the
        # inlet CH4: 5 %). 60 F molar volume 23.685 m3/kmol.
        v_in = 150e6 * 0.028316846592
        assert res["results"]["co2"]["value"] == pytest.approx(
            v_in * (0.045 - 0.0002) / (1 - 0.0002) * (44.01 / 23.685) / 1000, rel=1e-9)
        assert res["results"]["ch4"]["value"] == pytest.approx(v_in * 0.85 * 0.05 * (16.04 / 23.685) / 1000, rel=1e-9)

    def test_glycol_dehydrator_tier3(self, dispatcher):
        # Tier 3 = process simulation (GRI-GLYCalc) or measured result (API Compendium 6.3.8.1); the former
        # unsourced solubility model was removed (audit/TIER3_BROWSER_TEST.md #12)
        payload = {
            "process_type": "dehydrator",
            "factor_source": "specific",
            "vent_method": "reported_mass",
            "ch4_mass": 12.0,
            "co2_mass": 0.5,
        }
        res = dispatcher.dispatch("dehydrator", payload, {}, {})
        assert res["results"]["ch4"]["value"] == pytest.approx(12.0)

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
        # Exhibit 8.3 method: net efficiency = boiler 0.82 - transmission loss 0.03 = 0.79; 2,500 MMBtu / 0.79 x 53.06 kg/MMBtu
        assert res["results"]["co2"]["value"] == pytest.approx(2500 / 0.79 * 53.06 / 1000, rel=1e-9)

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
        # Eq 8-5, default reference efficiencies 80 % (heat) and 35 % (power): the share of the heat is
        # (4,000 / 0.80) / (4,000 / 0.80 + 2,000 / 0.35) of the 1,000 t
        assert res["results"]["co2"]["value"] == pytest.approx(1000.0 * (4000 / 0.80) / (4000 / 0.80 + 2000 / 0.35), rel=1e-9)

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
        # a carbon content selects the stoichiometric balance on every one of these process types:
        # 10,000 kg x 0.82 x 44.01 / 12.011 = 30.05 t CO2
        assert res["results"]["co2"]["value"] == pytest.approx(10000 * 0.82 * 44.01 / 12.011 / 1000, rel=1e-9)
        assert res["total_co2e"] == pytest.approx(res["results"]["co2"]["value"], rel=1e-9)


# ==============================================================================
# 3. LEGACY ENGINE & COMPUTE_EMISSIONS END-TO-END VERIFICATION
# ==============================================================================

class TestComputeEmissionsIntegration:
    """compute_emissions routes every canonical process type and returns the hand-worked gases (200 units, factors
    CO2 1.0 or 53.06 / CH4 0.05 / N2O 0.001 kg per unit; the special rows use their Compendium tables as in the Tier 1
    matrix above, with 200 units: 200 drilling days x 0.0458, 200 wells x 1.774 t, 1,257.962 bbl x 0.05 kg CH4/bbl,
    200 m3 x 80 % CH4 x 16.04 / 23.685 kg)."""

    _SPECIAL = {
        "associated_gas_venting": (0.0, 1257.962154 * 0.05 / 1000.0, 0.0),
        "drilling": (0.0, 200 * 0.0458, 0.0),
        "completions": (0.0, 200 * 0.80 * 16.04 / 23.685 / 1000.0, 0.0),
        "liquids_unloading": (0.0, 200 * 1.774, 0.0),
    }

    @pytest.mark.parametrize("process_id", list(PROCESS_TYPES.keys()))
    def test_compute_emissions_for_all_processes(self, process_id):
        category = PROCESS_TYPES[process_id]["category"]
        payload = {
            "process_type": process_id,
            "process": process_id,
            "amount": 200.0,
            "unit": "wells" if process_id == "liquids_unloading" else _activity_unit(process_id, category),
            "fuel_type": "Natural Gas" if category == "combustion" else None,
        }
        if process_id == "completions":
            payload["ch4_content"] = 80  # a measured flowback volume needs the gas analysis
        factors = {
            "co2": 53.06 if category == "combustion" else 1.0,
            "ch4": 0.05,
            "n2o": 0.001,
            "unit": "kg/m3" if category in ["combustion", "vented"] else "kg/unit",
            "hhv": 1020.0,
        }
        em_res, method = compute_emissions(payload, factors, gwp_dict=_AR5)
        co2, ch4, n2o = self._SPECIAL.get(process_id) or ((10.612, 0.01, 0.0002) if category == "combustion"
                                                          else (0.2, 0.01, 0.0002))
        assert em_res["co2"] == pytest.approx(co2, rel=2e-3, abs=1e-12), process_id
        assert em_res["ch4"] == pytest.approx(ch4, rel=2e-3, abs=1e-12), process_id
        assert em_res["n2o"] == pytest.approx(n2o, rel=2e-3, abs=1e-12), process_id
        assert em_res["totalCo2e"] == pytest.approx(co2 + 28.0 * ch4 + 265.0 * n2o, rel=2e-3), process_id
        assert method


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
        from routes.scope2 import resolve_electricity_factor
        kwh = 10000.0
        grid_ef, region = resolve_electricity_factor(None, 0.450)   # a supplier factor, kg CO2e / kWh, through the platform
        assert region is None
        assert pytest.approx(kwh * grid_ef / 1000.0, 1e-9) == 4.50
        # a known grid region uses the catalog factor (US-RMPA: 0.564 t CO2 + 5.31e-5 t CH4 x 28 + 7.71e-6 t N2O x 265 per MWh)
        rmpa, name = resolve_electricity_factor("US-RMPA (WECC Rockies)", None)
        assert rmpa == pytest.approx(0.564 + 5.31e-5 * 28 + 7.71e-6 * 265, rel=1e-6)

    def test_scope2_market_based_electricity_zero_carbon(self):
        from routes.scope2 import resolve_electricity_factor
        kwh = 50000.0
        ppa_ef, _ = resolve_electricity_factor(None, 0.0)   # 100 % solar PPA: a zero supplier factor is accepted
        assert kwh * ppa_ef / 1000.0 == 0.0

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
        # Exhibit 8.3: 1000 / (0.80 - 0.05) * 53.06 / 1000 = 70.7467 tonnes CO2
        assert pytest.approx(res["results"]["co2"]["value"], 1e-3) == 70.7467


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
        # tonnes CO2e = amount x factor (kg per unit) / 1,000; a "per $1000" factor applies to each 1,000 $ of spend
        per = 1000.0 if "$1000" in ef_unit else 1.0
        assert co2e == pytest.approx(activity_amt / per * ef_val / 1000.0, rel=1e-9)


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
            "unit": _activity_unit(process_id, meta["category"]),
        }
        factors = {"co2": 50.0, "ch4": 0.5, "n2o": 0.01, "unit": "kg/m3"}
        res = dispatcher.dispatch(process_id, payload, factors, {})
        assert res["total_co2e"] == 0.0

    @pytest.mark.parametrize("process_id", list(PROCESS_TYPES.keys()))
    def test_strictly_positive_monotonicity(self, dispatcher, process_id):
        """Monotonicity Law: Doubling activity data MUST double emissions."""
        meta = PROCESS_TYPES[process_id]
        unit = _activity_unit(process_id, meta["category"])
        factors = {"co2": 50.0, "ch4": 0.5, "n2o": 0.01, "unit": f"kg/{unit}"}

        p1 = {"process_type": process_id, "factor_source": "default", "amount": 100.0, "unit": unit}
        p2 = {"process_type": process_id, "factor_source": "default", "amount": 200.0, "unit": unit}
        if process_id == "completions":
            p1["ch4_content"] = p2["ch4_content"] = 80  # a measured flowback volume needs the gas analysis

        res1 = dispatcher.dispatch(process_id, p1, factors, {})
        res2 = dispatcher.dispatch(process_id, p2, factors, {})

        assert pytest.approx(res2["total_co2e"], rel=1e-3) == res1["total_co2e"] * 2.0

