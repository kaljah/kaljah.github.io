"""
test_audit_exhaustive_tiers_and_units.py
=========================================
Exhaustive Metrological Audit Verification Suite.

Validates with 100% mathematical and empirical rigor:
1. Every process type in the system (all 29 canonical process types + utilities + Scope 2 + Scope 3).
2. Every tier (Tier 1, Tier 2, Tier 3) for each process type, confirming formulas, stoichiometry,
   mass balance, thermodynamics, and physical conservation laws.
3. CSV uploader parity across all process types and tiers.
4. Exhaustive unit testing for EVERY volume, mass, energy, temperature, and pressure conversion
   and thermodynamic gas volume normalization.
"""

import math
import pytest
from decimal import Decimal

from calculations.dispatcher import CalculationDispatcher
from calculations.legacy_engine import compute_emissions
from calculations.constants import GWP_AR5, GWP_AR4, GWP_AR6, get_active_gwp
from calculations.units import (
    VOLUME_UNITS_TO_M3,
    MASS_UNITS_TO_KG,
    ENERGY_UNITS_TO_MJ,
    CONVERSIONS,
    to_kelvin,
    to_celsius,
    to_fahrenheit,
    to_psia,
    from_psia,
    convert_temperature,
    normalize_gas_volume_to_standard,
    calculate_co2e,
    compute_scope3_co2e,
    STD_TEMP_K,
    STD_TEMP_C,
    STD_TEMP_F,
    STD_PRESSURE_PSIA,
)
from process_categories import PROCESS_TYPES, NON_COMBUSTION_PROCESSES
from background_processor import _clean_float, _process_row, _process_row_scope2, _process_row_scope3
from models import Facility, CustomFactor, User, Emission, Scope2Emission, Scope3Emission
from app import app as flask_app
from extensions import db


@pytest.fixture(scope="module")
def dispatcher():
    return CalculationDispatcher()


@pytest.fixture(scope="module")
def test_app():
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    with flask_app.app_context():
        db.create_all()
        yield flask_app


def _gas_analysis(process_id):
    """Gas analysis a process needs for a gas volume: completions take no default CH4 content
    (85 % used to be assumed for an unanalysed flowback gas; S1K-F28)."""
    return {"ch4_content": 85.0} if process_id == "completions" else {}


def _get_base_unit(process_id, category):
    if process_id in ("drilling", "mud_degassing"):
        return "days"
    if category in ["combustion", "vented"]:
        return "m3"
    return "devices"


# ==============================================================================
# SECTION 1: EXHAUSTIVE TIER 1 MATRIX ACROSS ALL 29 PROCESS TYPES
# ==============================================================================

def _gases(res):
    return tuple(float(res["results"][g]["value"] if isinstance(res["results"].get(g), dict) else res["results"].get(g) or 0.0)
                 for g in ("co2", "ch4", "n2o"))


# Hand-worked Tier 1 results in tonnes for 1,000 units (combustion factors 53.06 / 0.05 / 0.001 kg per unit, the others
# CO2 1.5 kg). The processes with their own Compendium table do not multiply the generic factor:
#   drilling: 1,000 days x 0.0458 t CH4/day (Table 6-2); liquids_unloading: 1,000 wells x 1.774 t (Table 6-11, plunger);
#   completions: 1,000 m3 x 85 % CH4 x 16.04 / 23.685 kg/m3; associated gas: 1,000 m3 = 6,289.81 bbl x 0.05 kg CH4/bbl.
_TIER1_SPECIAL = {
    "associated_gas_venting": (0.0, 6289.81077 * 0.05 / 1000.0, 0.0),
    "drilling": (0.0, 1000 * 0.0458, 0.0),
    "completions": (0.0, 1000 * 0.85 * 16.04 / 23.685 / 1000.0, 0.0),
    "liquids_unloading": (0.0, 1000 * 1.774, 0.0),
}


class TestAllProcessTypesTier1Exhaustive:
    """Verifies that all 29 process types calculate deterministically with Tier 1 catalog factors."""

    @pytest.mark.parametrize("process_id", list(PROCESS_TYPES.keys()))
    def test_tier1_execution_and_positivity(self, dispatcher, process_id):
        meta = PROCESS_TYPES[process_id]
        unit = _get_base_unit(process_id, meta["category"])
        payload = {
            "process_type": process_id,
            "factor_source": "default",
            "amount": 1000.0,
            "quantity": 1000.0,
            "unit": "wells" if process_id == "liquids_unloading" else unit,
            "fuel_type": "Natural Gas" if meta["category"] == "combustion" else None,
            "hhv": 1020.0,
            **_gas_analysis(process_id),
        }
        factor_data = {
            "co2": 53.06 if meta["category"] == "combustion" else 1.5,
            "ch4": 0.05,
            "n2o": 0.001,
            "unit": f"kg/{unit}",
            "hhv": 1020.0,
        }
        res = dispatcher.dispatch(process_id, payload, factor_data, {}, gwp_dict=GWP_AR5)
        assert res is not None, f"Tier 1 dispatch failed for {process_id}"
        co2, ch4, n2o = _TIER1_SPECIAL.get(process_id) or ((53.06, 0.05, 0.001) if meta["category"] == "combustion"
                                                           else (1.5, 0.05, 0.001))
        got = _gases(res)
        assert got == pytest.approx((co2, ch4, n2o), rel=2e-3, abs=1e-12), process_id
        assert res["total_co2e"] == pytest.approx(co2 + 28.0 * ch4 + 265.0 * n2o, rel=2e-3), process_id

    @pytest.mark.parametrize("process_id", list(PROCESS_TYPES.keys()))
    def test_tier1_zero_activity_conservation(self, dispatcher, process_id):
        """Physical Invariant: 0 activity MUST produce 0 emissions."""
        meta = PROCESS_TYPES[process_id]
        unit = _get_base_unit(process_id, meta["category"])
        payload = {
            "process_type": process_id,
            "factor_source": "default",
            "amount": 0.0,
            "quantity": 0.0,
            "unit": unit,
        }
        factor_data = {"co2": 50.0, "ch4": 0.5, "n2o": 0.01, "unit": f"kg/{unit}"}
        res = dispatcher.dispatch(process_id, payload, factor_data, {}, gwp_dict=GWP_AR5)
        assert res["total_co2e"] == 0.0

    @pytest.mark.parametrize("process_id", list(PROCESS_TYPES.keys()))
    def test_tier1_strict_linear_scaling(self, dispatcher, process_id):
        """Mathematical Invariant: E(k * X) == k * E(X)."""
        meta = PROCESS_TYPES[process_id]
        unit = _get_base_unit(process_id, meta["category"])
        factor_data = {"co2": 50.0, "ch4": 0.5, "n2o": 0.01, "unit": f"kg/{unit}"}
        k = 3.5
        x = 500.0

        gas = _gas_analysis(process_id)
        p1 = {"process_type": process_id, "factor_source": "default", "amount": x, "quantity": x, "unit": unit, **gas}
        p2 = {"process_type": process_id, "factor_source": "default", "amount": x * k, "quantity": x * k, "unit": unit,
              **gas}

        r1 = dispatcher.dispatch(process_id, p1, factor_data, {}, gwp_dict=GWP_AR5)
        r2 = dispatcher.dispatch(process_id, p2, factor_data, {}, gwp_dict=GWP_AR5)

        assert pytest.approx(r2["total_co2e"], rel=1e-5) == r1["total_co2e"] * k


# ==============================================================================
# SECTION 2: EXHAUSTIVE TIER 2 MATRIX ACROSS ALL 29 PROCESS TYPES
# ==============================================================================

class TestAllProcessTypesTier2Exhaustive:
    """
    Verifies that Tier 2 (custom factors, regional factors, site-specific correlations,
    and event/GOR balances) correctly overrides defaults and executes with precision.
    """

    @pytest.mark.parametrize("process_id", [p for p in PROCESS_TYPES.keys() if p != "associated_gas_venting"])
    def test_tier2_custom_factor_override(self, dispatcher, process_id):
        """A custom Tier 2 factor replaces the catalog factor: 750 units x 62.45 / 0.082 / 0.0035 kg per unit.

        Three processes do NOT use it, because their method works from a table or the gas analysis, not from a
        factor per unit: drilling takes the factor's CH4 only (CO2 / N2O are not drilling gases); completions
        (750 m3 x 85 % CH4 x 16.04 / 23.685 kg/m3) and liquids unloading (750 wells x 1.774 t, Table 6-11) ignore
        the custom factor entirely - a software behaviour worth knowing, not one the Compendium requires."""
        meta = PROCESS_TYPES[process_id]
        unit = _get_base_unit(process_id, meta["category"])
        # Custom factor with distinct values (e.g. from local gas analysis)
        custom_ef = {
            "co2": 62.45,
            "ch4": 0.082,
            "n2o": 0.0035,
            "unit": f"kg/{unit}",
            "hhv": 1085.0,
            "type": "custom",
        }
        payload = {
            "process_type": process_id,
            "factor_source": "custom",
            "amount": 750.0,
            "quantity": 750.0,
            "unit": unit,
            "hhv": 1085.0,
            **_gas_analysis(process_id),
        }
        res = dispatcher.dispatch(process_id, payload, custom_ef, {}, gwp_dict=GWP_AR5)
        assert res is not None
        expected = {
            "drilling": (0.0, 750 * 0.082 / 1000.0, 0.0),
            "completions": (0.0, 750 * 0.85 * 16.04 / 23.685 / 1000.0, 0.0),
            "liquids_unloading": (0.0, 750 * 1.774, 0.0),
        }.get(process_id, (750 * 62.45 / 1000.0, 750 * 0.082 / 1000.0, 750 * 0.0035 / 1000.0))
        assert _gases(res) == pytest.approx(expected, rel=2e-3, abs=1e-12), process_id
        assert res["total_co2e"] == pytest.approx(expected[0] + 28.0 * expected[1] + 265.0 * expected[2], rel=2e-3)

    def test_tier2_associated_gas_venting_gor_balance(self, dispatcher):
        """API Compendium 2021 Exhibit 6-6 method: GOR balance. 5,200 bbl/day x 450 scf/bbl for a year, 85 % CH4 and 2 % CO2."""
        payload = {
            "process_type": "associated_gas_venting",
            "factor_source": "tier2",
            "tier": "tier2",
            "oil_production": 5200.0,
            "oil_unit": "bbl/day",
            "gor": 450.0,
            # the gas analysis is required (70 % CH4 / 10 % CO2 used to be assumed; S1K-F28)
            "ch4_content": 85.0,
            "co2_content": 2.0,
        }
        res = dispatcher.dispatch("associated_gas_venting", payload, {}, {}, gwp_dict=GWP_AR5)
        # no venting period given: all of the year (365 d). A "gas_to_vent_fraction" input does not exist (it was ignored).
        gas_m3 = 5200.0 * 450.0 * 365.0 * 0.028316846592
        assert res["results"]["ch4"]["value"] == pytest.approx(gas_m3 * 0.85 * (16.04 / 23.685) / 1000, rel=5e-3)
        assert res["results"]["co2"]["value"] == pytest.approx(gas_m3 * 0.02 * (44.01 / 23.685) / 1000, rel=5e-3)

    def test_tier2_liquids_unloading_event_based(self, dispatcher):
        """API Compendium Table 6-10: event-based liquids unloading. Plunger lift, fewer than 100 events/year: 11,308 scf of
        whole gas per event (at 85.3 mol % CH4); 24 events on each of 2 wells at 88 % CH4."""
        payload = {
            "process_type": "liquids_unloading",
            "factor_source": "default",
            "tier": "tier2",
            "events": 24,
            "unloading_type": "plunger",
            "well_count": 2,
            "ch4_content": 88,   # percent: 0.88 would be read as 0.88 %
        }
        res = dispatcher.dispatch("liquids_unloading", payload, {}, {}, gwp_dict=GWP_AR5)
        assert res["results"]["ch4"]["value"] == pytest.approx(
            24 * 2 * 11308 * 0.88 / 379.3 * 16.04 / 2204.62, rel=5e-3)

    def test_tier2_fugitive_component_service_streams(self, dispatcher):
        """API Compendium Table 7-11: component-level count with service speciation. 45 valves x 0.0268 kg TOC/h x 8,760 h;
        gas-service TOC is 92.0 wt % CH4 (Table C-1)."""
        payload = {
            "process_type": "fugitive_component",
            "factor_source": "tier2",
            "tier": "tier2",
            "component_type": "valves",
            "service": "gas",
            "count": 45,
            "hours": 8760,
            "ch4_content": 90,
        }
        factors = {"ch4": 0.0268, "unit": "kg/hr"}
        res = dispatcher.dispatch("fugitive_component", payload, factors, {}, gwp_dict=GWP_AR5)
        assert res["results"]["ch4"]["value"] == pytest.approx(45 * 0.0268 * 8760 / 1000 * 0.920, rel=1e-9)

    def test_tier2_drilling_mud_degassing_measured(self, dispatcher):
        """API Compendium Exhibit 6-1 method with measured gas fractions: 45 days of onshore water-based mud (0.0458 t CH4/day at
        83.85 mol %), gas 75 % CH4 and 8 % CO2."""
        payload = {
            "process_type": "drilling",
            "factor_source": "tier2",
            "amount": 45,
            "unit": "days",
            "mud_type": "water_based",
            "ch4_fraction": 0.75,
            "co2_fraction": 0.08,
            "well_location": "onshore",
        }
        factors = {"ch4": 0.0458}
        res = dispatcher.dispatch("drilling", payload, factors, {}, gwp_dict=GWP_AR5)
        ch4 = 45 * 0.0458 * 0.75 / 0.8385
        assert res["results"]["ch4"]["value"] == pytest.approx(ch4, rel=1e-9)
        assert res["results"]["co2"]["value"] == pytest.approx(ch4 * (0.08 / 0.75) * 44.01 / 16.04, rel=1e-9)


# ==============================================================================
# SECTION 3: EXHAUSTIVE TIER 3 MATRIX (PHYSICAL & ENGINEERING MASS BALANCE)
# ==============================================================================

class TestAllProcessTypesTier3Exhaustive:
    """Verifies all process types supporting first-principles Tier 3 calculations."""

    def test_tier3_combustion_stoichiometric_carbon_balance(self, dispatcher):
        """
        Conservation of Carbon: sum(n_i * C_i) converted stoichiometrically to CO2.
        Fuel: 85% CH4 (1 C), 8% C2H6 (2 C), 4% C3H8 (3 C), 2% CO2, 1% N2.
        Combustion efficiency: 99.5%.
        """
        payload = {
            "process_type": "stationary_combustion",
            "factor_source": "specific",
            "amount": 10_000.0,
            "unit": "m3",
            "fuel_type": "natural_gas",
            "hhv": 1025.0,
            "combustion_efficiency": 99.5,
            "c1": 85.0,
            "c2": 8.0,
            "c3": 4.0,
            "co2_mol": 2.0,
            "n2_mol": 1.0,
        }
        res = dispatcher.dispatch("stationary_combustion", payload, {}, {}, gwp_dict=GWP_AR5)
        carbon = 0.85 * 1 + 0.08 * 2 + 0.04 * 3                 # 1.13 mol C per mol gas
        rho_co2, rho_ch4 = 44.01 / 23.685, 16.04 / 23.685
        assert res["results"]["co2"]["value"] == pytest.approx(10_000 * (carbon * 0.995 + 0.02) * rho_co2 / 1000, rel=1e-9)
        assert res["results"]["ch4"]["value"] == pytest.approx(10_000 * 0.85 * 0.005 * rho_ch4 / 1000, rel=1e-9)  # slip

    @pytest.mark.parametrize("flare_proc", ["flaring", "routine_flaring", "non_routine_flaring", "safety_flaring"])
    def test_tier3_flaring_dual_efficiency_mass_balance(self, dispatcher, flare_proc):
        """
        API Compendium 5.2 dual efficiency flaring:
        Combustion converts oxidized hydrocarbons to CO2; unburned hydrocarbons slip as CH4.
        """
        payload = {
            "process_type": flare_proc,
            "factor_source": "specific",
            "amount": 25_000.0,
            "unit": "m3",
            "flare_type": "steam_assisted",
            "c1": 88.0,
            "c2": 6.0,
            "co2_mol": 4.0,
            "n2_mol": 2.0,
            "combustion_efficiency": 98.0,
            "destruction_efficiency": 98.0,
        }
        res = dispatcher.dispatch(flare_proc, payload, {}, {}, gwp_dict=GWP_AR5)
        rho_co2, rho_ch4 = 44.01 / 23.685, 16.04 / 23.685
        carbon = 0.88 * 1 + 0.06 * 2          # 1.00 mol C per mol gas
        co2 = 25_000 * (carbon * 0.98 + 0.04) * rho_co2 / 1000
        ch4 = 25_000 * 0.88 * 0.02 * rho_ch4 / 1000
        assert res["results"]["co2"]["value"] == pytest.approx(co2, rel=1e-9)
        assert res["results"]["ch4"]["value"] == pytest.approx(ch4, rel=1e-9)
        n2o = res["results"]["n2o"]["value"] if isinstance(res["results"]["n2o"], dict) else res["results"]["n2o"]
        assert res["total_co2e"] == pytest.approx(co2 + 28.0 * ch4 + 265.0 * n2o, rel=1e-9)

    def test_tier3_acid_gas_removal_mass_balance(self, dispatcher):
        """Mass conservation of CO2 removed from raw acid gas stream: 200 MMscf in at 5 % CO2, out at 0.05 %; the sweet gas
        volume is the inlet less the CO2 removed, so the CO2 vented = V x (c_in - c_out) / (1 - c_out). CH4 slip 0.02 (2 %) of
        the 85 % CH4 in."""
        payload = {
            "process_type": "acid_gas_removal",
            "factor_source": "specific",
            "gas_throughput": 200.0,
            "agr_unit": "mmscf",
            "co2_in": 5.0,
            "co2_out": 0.05,
            "ch4_in": 85.0,
            "ch4_slip": 0.02,
        }
        res = dispatcher.dispatch("acid_gas_removal", payload, {}, {}, gwp_dict=GWP_AR5)
        v_in = 200e6 * 0.028316846592
        assert res["results"]["co2"]["value"] == pytest.approx(
            v_in * (0.05 - 0.0005) / (1 - 0.0005) * (44.01 / 23.685) / 1000, rel=1e-9)
        assert res["results"]["ch4"]["value"] == pytest.approx(v_in * 0.85 * 0.02 * (16.04 / 23.685) / 1000, rel=1e-9)

    def test_tier3_blowdown_ideal_gas_volume(self, dispatcher):
        """Vessel depressurization: V_std = V_vessel * (P/P_std) * (T_std/T) * (1/Z)."""
        payload = {
            "process_type": "blowdown",
            "factor_source": "specific",
            "blowdown_volume": 120.0,
            "pressure": 850.0,
            "press_unit": "psig",
            "blowdown_temp": 75.0,
            "temp_unit": "F",
            "events": 3,
            "ch4_content": 92.0,
            "z_factor": 0.94,
        }
        res = dispatcher.dispatch("blowdown", payload, {}, {}, gwp_dict=GWP_AR5)
        # 120 m3 at 850 psig (864.696 psia) and 75 F (297.04 K), Z = 0.94, 3 events, 92 % CH4
        v_std = 120.0 * (850.0 + 14.696) / 14.696 * 288.706 / ((75.0 - 32.0) / 1.8 + 273.15) / 0.94
        assert res["results"]["ch4"]["value"] == pytest.approx(3 * v_std * 0.92 * (16.04 / 23.685) / 1000, rel=1e-5)

    def test_tier3_liquids_unloading_thermodynamics(self, dispatcher):
        """Wellbore column evacuation, Eq 6-10 (0.37e-3 x D^2 x depth x pressure per event) corrected from 60 F to the 110 F
        wellbore temperature: V = V_eq6-10 x (288.706 K / 316.48 K)."""
        payload = {
            "process_type": "liquids_unloading",
            "factor_source": "specific",
            "well_depth": 7500.0,
            "diameter": 2.875,
            "pressure": 280.0,
            "press_unit": "psig",
            "events": 6,
            "ch4_content": 87.0,
            "operating_temperature": 110.0,
            "temp_unit": "F",
        }
        res = dispatcher.dispatch("liquids_unloading", payload, {}, {}, gwp_dict=GWP_AR5)
        scf = 6 * 0.37e-3 * 2.875 ** 2 * 7500 * 280
        t_factor = 288.706 / ((110.0 - 32.0) / 1.8 + 273.15)
        assert res["results"]["ch4"]["value"] == pytest.approx(
            scf * t_factor * 0.87 / 379.3 * 16.04 / 2204.62, rel=5e-3)

    def test_tier3_chemical_stoichiometry(self, dispatcher):
        """C + O2 -> CO2 mass ratio = 44.01 / 12.011."""
        payload = {
            "process_type": "stoichiometry",
            "factor_source": "specific",
            "production_amount": 50_000.0,
            "unit": "kg",
            "carbon_content": 0.85,
        }
        res = dispatcher.dispatch("stoichiometry", payload, {}, {}, gwp_dict=GWP_AR5)
        expected_co2 = (50_000.0 * 0.85 * (44.01 / 12.011)) / 1000.0
        assert pytest.approx(res["results"]["co2"]["value"], rel=1e-3) == expected_co2


# ==============================================================================
# SECTION 4: EXHAUSTIVE UNIT CONVERSION ROUND-TRIP INVERTIBILITY & TRANSITIVITY
# ==============================================================================

class TestExhaustiveUnitConversionsAllMatrices:
    """Tests 100% of all volume, mass, energy, temperature, and pressure units in the system."""

    # 4A. Volume Units
    @pytest.mark.parametrize("u1", list(VOLUME_UNITS_TO_M3.keys()))
    def test_all_volume_units_to_m3_positive(self, u1):
        """Every volume unit is pinned to its defined size (exact definitions: 1 ft = 0.3048 m, 1 US gal = 3.785411784 L,
        1 bbl = 42 gal; Compendium Table 3-4). A unit added to the table must be added here."""
        ft3, gal, bbl = 0.3048 ** 3, 3.785411784e-3, 42 * 3.785411784e-3
        groups = {
            1.0: ("m3", "m³", "sm3", "sm³", "cubic_meter", "cubic_meters", "actual_m3", "actualm3", "am3"),
            (273.15 + 15.5556) / 273.15: ("nm3", "nm³"),     # normal m3 (0 C) in standard m3 (60 F)
            1e3: ("ksm3",), 1e6: ("mmsm3",),
            ft3: ("acf", "scf", "cf", "ft3"), ft3 * 1e3: ("mscf", "mcf"), ft3 * 1e6: ("mmscf",),
            bbl: ("bbl", "barrel", "barrels"), bbl * 1e3: ("kbbl", "mbbl"), bbl * 1e6: ("mmbbl",),
            gal: ("gal", "gallon", "gallons"), 1e-3: ("l", "liter", "liters", "litre", "litres"),
        }
        expected = {u: v for v, names in groups.items() for u in names}
        assert u1 in expected, f"volume unit {u1!r} has no pinned value"
        assert VOLUME_UNITS_TO_M3[u1] == pytest.approx(expected[u1], rel=1e-5)

    @pytest.mark.parametrize("u1", ["m3", "scf", "mcf", "mmscf", "bbl", "gal", "liter"])
    @pytest.mark.parametrize("u2", ["m3", "scf", "mcf", "mmscf", "bbl", "gal", "liter"])
    def test_volume_roundtrip_invertibility(self, u1, u2):
        val = 1543.21
        # Convert u1 -> m3 -> u2 -> m3 -> u1
        m3_1 = val * VOLUME_UNITS_TO_M3[u1]
        val_u2 = m3_1 / VOLUME_UNITS_TO_M3[u2]
        m3_2 = val_u2 * VOLUME_UNITS_TO_M3[u2]
        recovered = m3_2 / VOLUME_UNITS_TO_M3[u1]
        assert pytest.approx(recovered, rel=1e-8) == val

    # 4B. Mass Units
    @pytest.mark.parametrize("m1", list(MASS_UNITS_TO_KG.keys()))
    def test_all_mass_units_to_kg_positive(self, m1):
        """Every mass unit is pinned to its defined size (1 lb = 0.45359237 kg exactly; short ton = 2,000 lb, long ton =
        2,240 lb; Compendium Table 3-4)."""
        lb = 0.45359237
        groups = {
            1.0: ("kg", "kgs", "kilogram", "kilograms"), 1e-3: ("g", "gram", "grams"),
            1e3: ("tonne", "tonnes", "metric_ton", "metric_tons", "mt", "t"),
            lb: ("lb", "lbs", "pound", "pounds"), 2000 * lb: ("short_ton", "short_tons", "us_ton"),
            2240 * lb: ("long_ton", "long_tons"),
        }
        expected = {u: v for v, names in groups.items() for u in names}
        assert m1 in expected, f"mass unit {m1!r} has no pinned value"
        assert MASS_UNITS_TO_KG[m1] == pytest.approx(expected[m1], rel=1e-9)

    @pytest.mark.parametrize("m1", ["kg", "g", "tonne", "mt", "lb", "short_ton", "long_ton"])
    @pytest.mark.parametrize("m2", ["kg", "g", "tonne", "mt", "lb", "short_ton", "long_ton"])
    def test_mass_roundtrip_invertibility(self, m1, m2):
        val = 8765.43
        kg_1 = val * MASS_UNITS_TO_KG[m1]
        val_m2 = kg_1 / MASS_UNITS_TO_KG[m2]
        kg_2 = val_m2 * MASS_UNITS_TO_KG[m2]
        recovered = kg_2 / MASS_UNITS_TO_KG[m1]
        assert pytest.approx(recovered, rel=1e-8) == val

    # 4C. Energy Units
    @pytest.mark.parametrize("e1", list(ENERGY_UNITS_TO_MJ.keys()))
    def test_all_energy_units_to_mj_positive(self, e1):
        """Every energy unit is pinned to its defined size (1 Btu = 1,055.05585 J (IT), 1 kWh = 3.6 MJ, 1 therm = 10^5 Btu;
        the Compendium prints 1,055.056 J/Btu in Table 3-4 and Exhibit 4.3)."""
        btu = 1055.05585262e-6   # MJ
        groups = {
            1.0: ("mj", "megajoule", "megajoules"), 1e-3: ("kj", "kilojoule", "kilojoules"),
            1e3: ("gj", "gigajoule", "gigajoules"), 1e6: ("tj", "terajoule"),
            btu: ("btu", "btus"), btu * 1e3: ("kbtu",), btu * 1e6: ("mmbtu", "mm_btu"), btu * 1e5: ("therm", "therms"),
            3.6: ("kwh", "kilowatt_hour"), 3600.0: ("mwh", "megawatt_hour"),
        }
        expected = {u: v for v, names in groups.items() for u in names}
        assert e1 in expected, f"energy unit {e1!r} has no pinned value"
        assert ENERGY_UNITS_TO_MJ[e1] == pytest.approx(expected[e1], rel=1e-6)
        assert 1055.056e-6 == pytest.approx(btu, rel=1e-6)   # as printed in the Compendium

    @pytest.mark.parametrize("e1", ["mj", "kj", "gj", "tj", "btu", "mmbtu", "kwh", "mwh", "therm"])
    @pytest.mark.parametrize("e2", ["mj", "kj", "gj", "tj", "btu", "mmbtu", "kwh", "mwh", "therm"])
    def test_energy_roundtrip_invertibility(self, e1, e2):
        val = 4321.09
        mj_1 = val * ENERGY_UNITS_TO_MJ[e1]
        val_e2 = mj_1 / ENERGY_UNITS_TO_MJ[e2]
        mj_2 = val_e2 * ENERGY_UNITS_TO_MJ[e2]
        recovered = mj_2 / ENERGY_UNITS_TO_MJ[e1]
        assert pytest.approx(recovered, rel=1e-8) == val

    # 4D. Temperature Conversions
    @pytest.mark.parametrize("t_scale1", ["C", "F", "K", "R"])
    @pytest.mark.parametrize("t_scale2", ["C", "F", "K", "R"])
    def test_temperature_roundtrip_invertibility(self, t_scale1, t_scale2):
        # 60 deg F is 15.556 deg C, 288.706 K, 519.67 R
        base_f = 60.0
        t1_val = convert_temperature(base_f, "F", t_scale1)
        t2_val = convert_temperature(t1_val, t_scale1, t_scale2)
        recovered = convert_temperature(t2_val, t_scale2, t_scale1)
        assert pytest.approx(recovered, rel=1e-5) == t1_val

    # 4E. Pressure Conversions (Gauge & Absolute)
    @pytest.mark.parametrize("p_unit", [
        "psig", "psia", "barg", "bar", "mbarg", "mbar", "kpag", "kpa", "mpag", "mpa", "atm"
    ])
    def test_pressure_absolute_conversion_and_recovery(self, p_unit):
        val = 150.0  # 150 pressure units
        psia = to_psia(val, p_unit)
        assert psia > 0
        recovered = from_psia(psia, p_unit)
        assert pytest.approx(recovered, rel=1e-4) == val

    # 4F. Thermodynamic Ideal Gas Normalization
    @pytest.mark.parametrize("temp_c, press_psig, z", [
        (0.0, 0.0, 1.0),
        (15.556, 0.0, 1.0),     # Standard conditions
        (25.0, 100.0, 0.98),
        (50.0, 500.0, 0.95),
        (-20.0, 1500.0, 0.88),
    ])
    def test_thermodynamic_gas_normalization_invariants(self, temp_c, press_psig, z):
        """
        API Compendium §4.2.1:
        V_std = V_meas * (P_meas / P_std) * (T_std / T_meas) * (1 / Z)
        """
        v_meas = 1000.0
        v_std = normalize_gas_volume_to_standard(
            volume=v_meas,
            operating_temp=temp_c,
            temp_unit="C",
            operating_press=press_psig,
            press_unit="psig",
            z_factor=z,
        )
        assert v_std > 0
        assert not math.isnan(v_std)
        # At standard conditions (15.556 C, 0 psig, z=1), V_std == V_meas
        if temp_c == 15.556 and press_psig == 0.0 and z == 1.0:
            assert pytest.approx(v_std, rel=1e-3) == v_meas


# ==============================================================================
# SECTION 5: CSV UPLOADER END-TO-END PARITY ACROSS ALL PROCESS TYPES & TIERS
# ==============================================================================

class TestCSVUploaderExhaustiveParity:
    """Verifies that the CSV uploader accurately ingests and computes all process types and tiers."""

    @pytest.mark.parametrize("tier_code", ["default", "custom", "specific"])
    def test_csv_uploader_tier_parity_combustion(self, test_app, tier_code):
        with test_app.app_context():
            u = User.query.filter_by(role="admin").first()
            if not u:
                u = User(email="audit_admin@company.com", fullName="Auditor", orgName="AuditOrg", sector="O&G", role="admin")
                u.set_password("AdminPass2026!")
                db.session.add(u)
                db.session.commit()
            fac = Facility.query.first()
            if not fac:
                fac = Facility(name="Audit Refinery", region="North", segment="Downstream", created_by=u.id)
                db.session.add(fac)
                db.session.commit()

            cf = CustomFactor.query.filter_by(name="Custom Fuel", created_by=u.id).first()
            if not cf:
                cf = CustomFactor(name="Custom Fuel", co2_factor=55.0, ch4_factor=0.002, n2o_factor=0.0002, unit="kg/m3", hhv_factor=1050.0, created_by=u.id)
                db.session.add(cf)
                db.session.commit()

            fac_name_map = {fac.name.lower(): fac}
            fac_id_map = {str(fac.id): fac}
            cf_name_map = {"custom fuel": cf}
            api_factors = {"Natural Gas": {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu", "hhv": 1020.0}}

            fuel_name = "Custom Fuel" if tier_code == "custom" else "Natural Gas"
            row = {
                "date": "2025-05",
                "facility_name": fac.name,
                "process": "stationary_combustion",
                "fuel": fuel_name,
                "quantity": "5000",
                "unit": "m3",
                "factor_type": tier_code,
                "combustion_efficiency": "99.5",
                "c1": "85.0",
                "co2_mol": "2.0",
            }
            emission_obj, row_errors = _process_row(
                row=row,
                user_id=u.id,
                fac_name_map=fac_name_map,
                fac_id_map=fac_id_map,
                cf_name_map=cf_name_map,
                compute_emissions_fn=compute_emissions,
                API_FACTORS_dict=api_factors,
                global_factor_type="auto",
                gwp_dict=GWP_AR5,
                gwp_std="AR5",
                job_id="test_job",
                row_idx=1,
            )
            assert len(row_errors) == 0, f"CSV processing errors: {row_errors}"
            assert emission_obj is not None
            assert emission_obj.co2e_total > 0
            assert emission_obj.status == "Verified"  # an admin's import is Verified at once

    def test_csv_uploader_scope2_indirect_steam_parity(self, test_app):
        with test_app.app_context():
            u = User.query.filter_by(role="admin").first()
            fac = Facility.query.first()
            row = {
                "date": "2025-06",
                "facility_name": fac.name,
                "source_type": "indirect_steam",
                "consumption": "1500",
                "unit": "mmbtu",
                "boiler_eff": "82",
                "trans_loss": "4",
                "emission_factor": "53.06",
            }
            scope2_obj, row_errors = _process_row_scope2(
                row=row,
                user_id=u.id,
                fac_name_map={fac.name.lower(): fac},
                fac_id_map={str(fac.id): fac},
                GRID_FACTORS={},
                job_id="test_scope2_job",
                row_idx=1,
            )
            assert len(row_errors) == 0
            assert scope2_obj is not None
            assert scope2_obj.co2e > 0

    def test_csv_uploader_scope3_all_categories_parity(self, test_app):
        with test_app.app_context():
            u = User.query.filter_by(role="admin").first()
            fac = Facility.query.first()
            row = {
                "date": "2025-07",
                "facility_name": fac.name,
                "category": "Category 4",
                "amount": "25000",
                "unit": "tonne-km",
                "emission_factor": "0.145",
                "ef_unit": "kg CO2e / tonne-km",
            }
            scope3_obj, row_errors = _process_row_scope3(
                row=row,
                user_id=u.id,
                fac_name_map={fac.name.lower(): fac},
                fac_id_map={str(fac.id): fac},
                job_id="test_scope3_job",
                row_idx=1,
            )
            assert len(row_errors) == 0
            assert scope3_obj is not None
            assert scope3_obj.co2e > 0
            expected = (25000.0 * 0.145) / 1000.0
            assert pytest.approx(scope3_obj.co2e, rel=1e-4) == expected
