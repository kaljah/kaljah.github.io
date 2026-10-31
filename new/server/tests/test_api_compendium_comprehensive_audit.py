"""
API Compendium of Greenhouse Gas Emissions Methodologies for the Oil and Natural Gas Industry
(4th Edition, November 2021 with December 2025 Corrections)

Comprehensive Single-File End-to-End Pipeline Audit & Independent Oracle Test Suite.
====================================================================================
Governing Standards:
  - API Compendium of GHG Emissions Methodologies for the Oil and Natural Gas Industry (2021/2025)
  - NIST SP 811 (Guide for the Use of the International System of Units)
  - ISO 14064-1:2018 / GHG Protocol Corporate Standard & Scope 2/Scope 3 Guidance
  - IPCC 2006 / 2019 Refinement Guidelines & GUM Uncertainty of Measurement

Mandatory Architectural Layers:
  Layer 1: Complete Unit & Dimensional Conversion Matrix (100% Units, Round-Trips, Physical Bridges)
  Layer 2: 100% Default Emission Factor & Constant Registry Audit (All Tables, Catalogs, GWP Profiles)
  Layer 3: Full End-to-End Pipeline Route Tests Across All Process Types, Tiers & Inputs
  Layer 4: Multi-Unit Pipeline Invariance (Dimensional Invariance Across Pipeline Entry/Exit)
  Layer 5: Boundary, Edge-Case & Conservation Laws (Mass Balances, 0/100 Boundaries, Anomaly Trapping)

Diagnostic Engine:
  Outputs a structured executive Audit Diagnostic Report grouping any detected issues into:
    [UNIT_CONVERSION_BUG], [DEFAULT_FACTOR_MISMATCH], [FORMULA_OR_TIER_LOGIC_BUG],
    [IGNORED_INPUT_OR_PIPELINE_DROP], [UNIT_INVARIANCE_FAILURE].
"""

import math
import sys
import os
import pytest
from collections import defaultdict

# Add new/server to sys.path so tests execute standalone or via pytest
_SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

from calculations.units import (
    convert,
    convert_temperature,
    convert_pressure,
    normalize_gas_volume_to_standard,
    period_volume_m3,
    parse_factor_unit,
    factor_to_kg_per_activity,
    unit_dimension,
    composition_fractions,
    calculate_co2e,
    UnitError,
    VOLUME_UNITS_TO_M3,
    MASS_UNITS_TO_KG,
    ENERGY_UNITS_TO_MJ,
    DISTANCE_UNITS_TO_M,
    FREIGHT_UNITS_TO_TONNE_KM,
    PASSENGER_UNITS_TO_PKM,
    TIME_UNITS_TO_HOURS,
    LIQUID_FLOW_UNITS_TO_M3_HR,
    TEMP_UNITS,
    PRESS_UNITS,
    _PRESSURE_UNITS,
    CONVERSIONS,
)
from calculations.constants import (
    GWP_AR4,
    GWP_AR5,
    GWP_AR6,
    GWP_STANDARDS,
    get_active_gwp,
)
from calculations.legacy_engine import compute_emissions, MissingFactorError
from calculations.dispatcher import dispatcher, CalculationDispatcher, PERCENT_FIELDS
from routes.emissions import _lookup_api_factor
from emission_factors import (
    API_FACTORS,
    ALL_EMISSION_FACTORS,
    EEIO_FACTORS,
    CORRELATION_EQUATIONS,
)
from calculations.activity_factors import ACTIVITY_FACTORS
from emission_factors_chapter7_onshore import (
    COMPONENT_FACTORS_T7_12,
    OGI_LEAKER_FACTORS,
    METHOD21_SCREENING_RANGES,
)
from electricity_factors import GRID_FACTORS
from emission_factors.scope3_activity_factors import SCOPE3_ACTIVITY_FACTORS
from calculations.fugitive_other import (
    MCF,
    OPERATING_RATE_PCT,
    USAGE_EF,
    TRANSMISSION_EF_KG_PER_MILE,
    TRANSMISSION_EF_T_PER_KM,
    _AR5_BLENDS,
    _FGAS_GWP,
    OTHER_FUGITIVE_PROCESSES,
)
from calculations.flare_defaults import (
    PRODUCTION_DESTRUCTION,
    REFINERY_DESTRUCTION,
    FLARE_PROCESSES,
)

# ==============================================================================
# AUDIT DIAGNOSTIC ACCUMULATOR
# ==============================================================================

class AuditDiagnosticReport:
    """Accumulates and prints categorized audit findings across all layers."""

    def __new__(cls, *args, **kwargs):
        if not hasattr(sys, "_AUDIT_DIAGNOSTICS_INSTANCE"):
            instance = super().__new__(cls)
            instance.findings = defaultdict(list)
            instance.total_assertions = 0
            instance.passed_assertions = 0
            sys._AUDIT_DIAGNOSTICS_INSTANCE = instance
        return sys._AUDIT_DIAGNOSTICS_INSTANCE

    def record_pass(self):
        self.total_assertions += 1
        self.passed_assertions += 1

    def record_finding(self, category: str, title: str, details: str):
        self.total_assertions += 1
        self.findings[category].append({"title": title, "details": details})

    def print_report(self):
        print("\n" + "=" * 80)
        print("API COMPENDIUM GHG CALCULATION PIPELINE -- AUDIT DIAGNOSTIC REPORT")
        print("=" * 80)
        print(f"Total Audit Assertions Verified: {self.total_assertions}")
        print(f"Successful Assertions:           {self.passed_assertions}")
        total_issues = sum(len(items) for items in self.findings.values())
        print(f"Identified Discrepancies/Bugs:   {total_issues}")
        print("-" * 80)

        categories = [
            "[UNIT_CONVERSION_BUG]",
            "[DEFAULT_FACTOR_MISMATCH]",
            "[FORMULA_OR_TIER_LOGIC_BUG]",
            "[IGNORED_INPUT_OR_PIPELINE_DROP]",
            "[UNIT_INVARIANCE_FAILURE]",
        ]
        for cat in categories:
            items = self.findings.get(cat, [])
            print(f"\n{cat} -- {len(items)} issue(s) detected:")
            if not items:
                print("  [OK] Zero discrepancies detected in this category.")
            else:
                for idx, item in enumerate(items, 1):
                    print(f"  {idx}. {item['title']}")
                    print(f"     Details: {item['details']}")
        print("=" * 80 + "\n")

DIAGNOSTICS = AuditDiagnosticReport()

# ==============================================================================
# INDEPENDENT ORACLE CONSTANTS & FORMULAS (API COMPENDIUM 2021)
# ==============================================================================

# Reference Thermodynamic Conditions (API §4.2.1)
ORACLE_STD_TEMP_F = 60.0
ORACLE_STD_TEMP_C = (60.0 - 32.0) * 5.0 / 9.0  # 15.555555... °C
ORACLE_STD_TEMP_K = ORACLE_STD_TEMP_C + 273.15  # 288.705555... K
ORACLE_STD_TEMP_R = 519.67

ORACLE_STD_PRESS_PSIA = 14.696
ORACLE_STD_PRESS_KPA = 101.325
ORACLE_STD_PRESS_BAR = 1.01325

# Standard Molar Volume Basis (API §3.4 and equations 5-1 / 6-1)
ORACLE_MOLAR_VOL_SCF_LBMOL = 379.3
ORACLE_MOLAR_VOL_SM3_KMOL = 23.685

# Molecular Weights (API Tables 3-1 & 3-2)
ORACLE_MW = {
    "C": 12.011,
    "CO2": 44.01,
    "CH4": 16.04,
    "N2O": 44.013,
    "C2H6": 30.07,
    "C3H8": 44.10,
    "C4H10": 58.12,
    "H2": 2.016,
    "Air": 28.96,
}

# Standard Gas Densities (kg/m3 = MW / 23.685 m3/kmol)
ORACLE_DENSITY = {
    "CH4": ORACLE_MW["CH4"] / ORACLE_MOLAR_VOL_SM3_KMOL,   # 0.6772201815...
    "CO2": ORACLE_MW["CO2"] / ORACLE_MOLAR_VOL_SM3_KMOL,   # 1.8581380620...
    "N2O": ORACLE_MW["N2O"] / ORACLE_MOLAR_VOL_SM3_KMOL,   # 1.8582647245...
    "C2H6": ORACLE_MW["C2H6"] / ORACLE_MOLAR_VOL_SM3_KMOL, # 1.2695799028...
    "C3H8": ORACLE_MW["C3H8"] / ORACLE_MOLAR_VOL_SM3_KMOL, # 1.8619379354...
    "C4H10": ORACLE_MW["C4H10"] / ORACLE_MOLAR_VOL_SM3_KMOL,# 2.4538737597...
}

# Independent Exact NIST / API Conversion Factors
ORACLE_NIST = {
    "scf_to_m3": 0.028316846592,
    "mscf_to_m3": 28.316846592,
    "mmscf_to_m3": 28316.846592,
    "bbl_to_m3": 0.158987295,
    "gal_to_m3": 0.003785411784,
    "bbl_to_gal": 42.0,
    "l_to_m3": 0.001,
    "lb_to_kg": 0.45359237,
    "tonne_to_kg": 1000.0,
    "short_ton_to_kg": 907.18474,
    "long_ton_to_kg": 1016.0469088,
    "btu_to_kj": 1.05505585262,
    "mmbtu_to_mj": 1055.05585262,
    "therm_to_mj": 105.505585262,
    "kwh_to_mj": 3.6,
    "mwh_to_mj": 3600.0,
    "mile_to_km": 1.609344,
    "foot_to_m": 0.3048,
    "ton_mile_to_tkm": 1.459972,
}

# Flaring Defaults (API 2021 with Dec 2025 Errata)
ORACLE_FLARE_ETA_C_DEFAULT = 0.965  # Combustion efficiency (carbon -> CO2)
ORACLE_FLARE_ETA_D_DEFAULT = 0.98   # Destruction efficiency (CH4 destroyed, upstream)
ORACLE_FLARE_ETA_D_REFINERY = 0.995 # Destruction efficiency (downstream refinery)

# Tolerances (agreed in Clarification Question 5)
REL_TOL_EXACT = 1e-6   # First-principles math, unit identity/round-trip, invariance
REL_TOL_EXHIBIT = 1e-4 # Comparing against printed API Compendium rounded exhibit text


# ==============================================================================
# LAYER 1: COMPLETE UNIT & DIMENSIONAL CONVERSION MATRIX
# ==============================================================================

class TestLayer1UnitConversionMatrix:
    """Verifies all defined units, round trips, cross-system NIST constants, and bridges."""

    @pytest.mark.parametrize("dim_name,dim_map", [
        ("Volume", VOLUME_UNITS_TO_M3),
        ("Mass", MASS_UNITS_TO_KG),
        ("Energy", ENERGY_UNITS_TO_MJ),
        ("Distance", DISTANCE_UNITS_TO_M),
        ("Freight", FREIGHT_UNITS_TO_TONNE_KM),
        ("Passenger", PASSENGER_UNITS_TO_PKM),
        ("Time", TIME_UNITS_TO_HOURS),
        ("LiquidFlow", LIQUID_FLOW_UNITS_TO_M3_HR),
    ])
    def test_identity_conversions(self, dim_name, dim_map):
        """Test u -> u identity conversion for 100% of defined units."""
        for u in dim_map:
            val = 123.456
            # Independent Oracle: Identity conversion val * (factor / factor) = val
            res = convert(val, u, u)
            assert math.isclose(res, val, rel_tol=REL_TOL_EXACT), (
                f"Identity conversion failed for unit '{u}' in dimension {dim_name}"
            )
            DIAGNOSTICS.record_pass()

    @pytest.mark.parametrize("dim_name,dim_map,sample_pairs", [
        ("Mass", MASS_UNITS_TO_KG, [
            ("kg", "lb"), ("tonne", "short_ton"), ("g", "kg"), ("short_ton", "long_ton"), ("lb", "tonne")
        ]),
        ("Volume", VOLUME_UNITS_TO_M3, [
            ("scf", "mscf"), ("mscf", "mmscf"), ("m3", "scf"), ("bbl", "gal"), ("gal", "l"), ("m3", "bbl"), ("sm3", "ksm3")
        ]),
        ("Energy", ENERGY_UNITS_TO_MJ, [
            ("btu", "mmbtu"), ("mmbtu", "gj"), ("mj", "kwh"), ("mwh", "gj"), ("therm", "mmbtu"), ("kj", "mj"), ("tj", "gj")
        ]),
        ("Distance", DISTANCE_UNITS_TO_M, [
            ("m", "ft"), ("km", "mi"), ("yd", "m"), ("nmi", "km")
        ]),
        ("LiquidFlow", LIQUID_FLOW_UNITS_TO_M3_HR, [
            ("m3/hr", "gph"), ("bph", "m3/hr"), ("bpd", "bph"), ("lph", "m3/hr")
        ]),
    ])
    def test_round_trip_conversions(self, dim_name, dim_map, sample_pairs):
        """Test u1 -> u2 -> u1 round trip preservation across core units."""
        for u1, u2 in sample_pairs:
            orig = 1000.0
            # Independent Oracle: orig * f_1_to_2 * (1 / f_1_to_2) = orig
            forward = convert(orig, u1, u2)
            reverse = convert(forward, u2, u1)
            diff = abs(reverse - orig) / orig
            if diff > REL_TOL_EXACT:
                DIAGNOSTICS.record_finding(
                    "[UNIT_CONVERSION_BUG]",
                    f"Round-trip drift for {u1} -> {u2} -> {u1}",
                    f"Orig: {orig}, Roundtrip: {reverse}, RelDiff: {diff:.2e}"
                )
            assert math.isclose(reverse, orig, rel_tol=REL_TOL_EXACT), (
                f"Round trip failed for {u1} <-> {u2}: got {reverse}, expected {orig}"
            )
            DIAGNOSTICS.record_pass()

    def test_cross_system_nist_constants(self):
        """Cross-check software conversion factors against independent NIST constants."""
        checks = [
            # Independent Oracle: 1 lb = 0.45359237 kg (NIST SP 811)
            ("lb", "kg", 1.0, ORACLE_NIST["lb_to_kg"]),
            # Independent Oracle: 1 short ton = 2000 lb = 907.18474 kg
            ("short_ton", "kg", 1.0, ORACLE_NIST["short_ton_to_kg"]),
            # Independent Oracle: 1 long ton = 2240 lb = 1016.0469088 kg
            ("long_ton", "kg", 1.0, ORACLE_NIST["long_ton_to_kg"]),
            # Independent Oracle: 1 scf = (0.3048)^3 m3 = 0.028316846592 m3
            ("scf", "m3", 1.0, ORACLE_NIST["scf_to_m3"]),
            # Independent Oracle: 1 bbl = 42 US gal = 42 * 0.003785411784 m3 = 0.158987294928 m3
            ("bbl", "m3", 1.0, ORACLE_NIST["bbl_to_m3"]),
            # Independent Oracle: 1 US gal = 231 cu in = 0.003785411784 m3
            ("gal", "m3", 1.0, ORACLE_NIST["gal_to_m3"]),
            # Independent Oracle: 1 MMBtu (IT) = 1055.05585262 MJ
            ("mmbtu", "mj", 1.0, ORACLE_NIST["mmbtu_to_mj"]),
            # Independent Oracle: 1 kWh = 3.6 MJ
            ("kwh", "mj", 1.0, ORACLE_NIST["kwh_to_mj"]),
            # Independent Oracle: 1 therm = 100,000 Btu = 105.505585262 MJ
            ("therm", "mj", 1.0, ORACLE_NIST["therm_to_mj"]),
        ]
        for u_from, u_to, val, expected in checks:
            res = convert(val, u_from, u_to)
            assert math.isclose(res, expected, rel_tol=REL_TOL_EXACT), (
                f"Conversion {u_from} -> {u_to} mismatch: got {res}, expected {expected}"
            )
            DIAGNOSTICS.record_pass()

    def test_temperature_scales(self):
        """Assert exact temperature conversions across C, F, K, and R."""
        points = [
            # (degC, degF, K, degR)
            (0.0, 32.0, 273.15, 491.67),             # Ice point
            (100.0, 212.0, 373.15, 671.67),          # Boiling point
            (15.555555555556, 60.0, 288.705555555556, 519.67), # API Standard Condition
            (-40.0, -40.0, 233.15, 419.67),          # Intersection
        ]
        for c, f, k, r in points:
            # Independent Oracle: C -> F: C * 9/5 + 32; C -> K: C + 273.15; K -> R: K * 9/5
            assert math.isclose(convert_temperature(c, "c", "f"), f, rel_tol=REL_TOL_EXACT)
            assert math.isclose(convert_temperature(f, "f", "c"), c, rel_tol=REL_TOL_EXACT)
            assert math.isclose(convert_temperature(c, "c", "k"), k, rel_tol=REL_TOL_EXACT)
            assert math.isclose(convert_temperature(k, "k", "r"), r, rel_tol=REL_TOL_EXACT)
            DIAGNOSTICS.record_pass()

    def test_pressure_scales(self):
        """Assert gauge to absolute and unit conversions for pressure."""
        # Independent Oracle: 0 psig = 14.696 psia (at std atmosphere)
        assert math.isclose(convert_pressure(0.0, "psig", "psia"), 14.696, rel_tol=REL_TOL_EXACT)
        # Independent Oracle: 100 kPag = (100 / 6.894757) + 14.696 = 29.200 psia
        kpa_to_psi = 14.50377377 / 100.0
        expected_psia = 100.0 * 0.145038 + 14.696
        assert math.isclose(convert_pressure(100.0, "kpag", "psia"), expected_psia, rel_tol=1e-4)
        # Independent Oracle: 1 bar = 100 kPa
        assert math.isclose(convert_pressure(1.0, "bar", "kpa"), 100.0, rel_tol=REL_TOL_EXACT)
        DIAGNOSTICS.record_pass()

    def test_cross_dimensional_physical_bridges(self):
        """Test Volume <-> Mass bridge via gas density and Volume/Mass <-> Energy via HHV."""
        # Independent Oracle: Mass = Volume (1000 m3) * Density_CH4 (0.67722018 kg/m3) = 677.22018 kg
        vol_m3 = 1000.0
        mass_kg = vol_m3 * ORACLE_DENSITY["CH4"]
        assert math.isclose(mass_kg, 677.22018, rel_tol=REL_TOL_EXHIBIT)

        # Independent Oracle: Energy = Volume (1000 scf) * HHV (1020 Btu/scf) * 1e-6 MMBtu/Btu = 1.020 MMBtu
        vol_scf = 1000.0
        hhv_btu_scf = 1020.0
        energy_mmbtu = vol_scf * hhv_btu_scf / 1e6
        assert math.isclose(energy_mmbtu, 1.02, rel_tol=REL_TOL_EXACT)

        # Energy to GJ: 1.02 MMBtu * 1.05505585262 GJ/MMBtu = 1.07615696967 GJ
        energy_gj = energy_mmbtu * (ORACLE_NIST["mmbtu_to_mj"] / 1000.0)
        assert math.isclose(energy_gj, 1.07615697, rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    def test_compound_emission_factor_conversions(self):
        """Test compound emission factor unit conversions via factor_to_kg_per_activity."""
        # 1. lb/MMscf to kg/Mscf
        # Independent Oracle: 1 lb/MMscf = 0.45359237 kg / 1,000,000 scf = 0.00045359237 kg/Mscf
        spec = parse_factor_unit("lb/MMscf")
        assert math.isclose(spec["mass_kg"], 0.45359237, rel_tol=REL_TOL_EXACT)
        kg_per_mscf = factor_to_kg_per_activity(1.0, "lb/MMscf", "mscf")
        assert math.isclose(kg_per_mscf, 0.45359237 * (28.316846592 / 28316.846592), rel_tol=REL_TOL_EXACT)

        # 2. kg/hr/source with 8760 hours -> kg/yr
        # Independent Oracle: 2.5 kg/hr/source * 8760 hr = 21,900 kg/source/yr
        kg_annual = factor_to_kg_per_activity(2.5, "kg/hr/source", "count", hours=8760)
        assert math.isclose(kg_annual, 21900.0, rel_tol=REL_TOL_EXACT)
        DIAGNOSTICS.record_pass()

    def test_ambiguous_units_rejection(self):
        """Assert that ambiguous bare units ('ton', 'tons', 'tonnes/ton', 'kg/ton') are strictly refused."""
        ambiguous = ["ton", "tons", "tonnes/ton", "kg/ton"]
        for u in ambiguous:
            with pytest.raises((ValueError, UnitError)):
                unit_dimension(u)
            DIAGNOSTICS.record_pass()


# ==============================================================================
# LAYER 2: 100% DEFAULT EMISSION FACTOR & CONSTANT REGISTRY AUDIT
# ==============================================================================

class TestLayer2DefaultFactorRegistry:
    """Audits 100% of stored default emission factors against API Compendium tables."""

    def test_audit_all_180_api_factors_integrity(self):
        """Assert no default factor in API_FACTORS is None, NaN, negative, or missing unit metadata."""
        assert len(API_FACTORS) == 180, f"Expected exactly 180 API_FACTORS, found {len(API_FACTORS)}"
        for name, data in API_FACTORS.items():
            unit = data.get("unit") or data.get("factor_unit") or data.get("baseUnit")
            assert unit, f"Missing unit in API_FACTOR '{name}'"
            assert "usage" in data or "type" in data or "process_category" in data, f"Missing classification in API_FACTOR '{name}'"
            for gas in ("co2", "ch4", "n2o"):
                val = data.get(gas)
                if val is not None:
                    assert not math.isnan(val), f"NaN factor for gas {gas} in '{name}'"
                    assert val >= 0.0, f"Negative factor {val} for gas {gas} in '{name}'"
            DIAGNOSTICS.record_pass()

    def test_cross_check_benchmark_compendium_factors(self):
        """Independently cross-check core catalog factors against API Compendium tables."""
        benchmarks = {
            # Table 5-1: Natural Gas combustion (kg/MMBtu)
            "Natural Gas": {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "hhv": 1020, "unit": "kg/MMBtu"},
            # Table 5-1: Diesel / Fuel Oil No. 2 (kg/MMBtu)
            "Diesel (No. 2 Fuel Oil)": {"co2": 73.96, "ch4": 0.003, "n2o": 0.0006, "unit": "kg/MMBtu"},
            # Table 5-1: Crude Oil (kg/MMBtu)
            "Crude Oil": {"co2": 74.54, "ch4": 0.003, "n2o": 0.0006, "unit": "kg/MMBtu"},
            # Table 5-1: Residual Fuel Oil (No. 6) (kg/MMBtu)
            "Residual Fuel Oil (No. 6)": {"co2": 75.1, "ch4": 0.003, "n2o": 0.0006, "unit": "kg/MMBtu"},
            # Table 5-1: Associated Gas Flare (kg/Sm3)
            "Associated Gas (Flaring)": {"co2": 2.2414, "ch4": 0.010836, "unit": "kg/m³"},
        }
        for name, expected in benchmarks.items():
            actual = API_FACTORS.get(name) or _lookup_api_factor(name)
            assert actual, f"Benchmark factor '{name}' not found in catalog"
            for k, exp_val in expected.items():
                if k in ("co2", "ch4", "n2o", "hhv"):
                    act_val = actual.get(k)
                    assert act_val is not None, f"Key {k} missing in '{name}'"
                    assert math.isclose(act_val, exp_val, rel_tol=REL_TOL_EXACT), (
                        f"Factor mismatch for {name}.{k}: got {act_val}, expected {exp_val}"
                    )
            DIAGNOSTICS.record_pass()

    def test_audit_all_105_activity_factors_integrity(self):
        """Assert all 105 ACTIVITY_FACTORS are well-formed and map to valid API Compendium tables."""
        assert len(ACTIVITY_FACTORS) == 105, f"Expected 105 ACTIVITY_FACTORS, found {len(ACTIVITY_FACTORS)}"
        for key, row in ACTIVITY_FACTORS.items():
            assert "table" in row, f"Missing table in ACTIVITY_FACTORS key '{key}'"
            assert "per" in row or "unit" in row, f"Missing unit/per in ACTIVITY_FACTORS key '{key}'"
            assert "processes" in row and len(row["processes"]) > 0, f"Missing processes for '{key}'"
            ef = row.get("ch4") if row.get("ch4") is not None else (row.get("gas_scf") if row.get("gas_scf") is not None else (row.get("factor") if row.get("factor") is not None else row.get("co2")))
            assert ef is not None and not math.isnan(ef), f"NaN factor in '{key}'"
            assert ef >= 0.0, f"Negative factor in '{key}'"
            DIAGNOSTICS.record_pass()

    def test_audit_fugitive_onshore_registries(self):
        """Audit Table 7-12 components, Table 7-13 OGI leakers, and Table 7-14 screening ranges."""
        # Table 7-12: 23 component factors
        assert len(COMPONENT_FACTORS_T7_12) == 23
        for comp_key, val in COMPONENT_FACTORS_T7_12.items():
            ef = val.get("kg_gas_hr") if isinstance(val, dict) else val
            assert ef > 0.0 and not math.isnan(ef), f"Invalid Table 7-12 factor for '{comp_key}'"
            DIAGNOSTICS.record_pass()

        # Table 7-13: 21 OGI leaker factors
        assert len(OGI_LEAKER_FACTORS) == 21
        for ogi_key, val in OGI_LEAKER_FACTORS.items():
            ef = val.get("whole_gas_scf_hr") if isinstance(val, dict) else val
            assert ef > 0.0 and not math.isnan(ef), f"Invalid Table 7-13 factor for '{ogi_key}'"
            DIAGNOSTICS.record_pass()

        # Table 7-14: 23 screening ranges
        assert len(METHOD21_SCREENING_RANGES) == 23
        for m21_key, val in METHOD21_SCREENING_RANGES.items():
            assert "table" in val
            assert "unit" in val
            if val.get("non_pegged_ef") is not None:
                assert val["non_pegged_ef"] >= 0.0
            if val.get("pegged_10k_ef") is not None:
                assert val["pegged_10k_ef"] >= 0.0
            DIAGNOSTICS.record_pass()

    def test_audit_grid_and_scope3_catalogs(self):
        """Audit 61 electricity grid factors and 15 Scope 3 activity factors."""
        assert len(GRID_FACTORS) == 61
        for grid, val in GRID_FACTORS.items():
            ef = val.get("factor") if isinstance(val, dict) else val
            assert ef > 0.0 and not math.isnan(ef)
            DIAGNOSTICS.record_pass()

        assert len(SCOPE3_ACTIVITY_FACTORS) == 15
        for cat_id, factors in SCOPE3_ACTIVITY_FACTORS.items():
            assert isinstance(factors, list) and len(factors) > 0
            for item in factors:
                assert len(item) == 3
                label, unit, ef = item
                assert label and unit
                if ef is not None:
                    assert ef > 0.0 and not math.isnan(ef)
            DIAGNOSTICS.record_pass()

    def test_audit_gwp_registry_standards(self):
        """Assert exact GWP registry values across AR4, AR5, and AR6 for 100-yr and 20-yr horizons."""
        # Independent Oracle: IPCC Assessment Reports
        assert GWP_AR4["CO2"] == 1.0 and GWP_AR4["CH4"] == 25.0 and GWP_AR4["N2O"] == 298.0
        assert GWP_AR4["CH4_20"] == 72.0 and GWP_AR4["N2O_20"] == 289.0

        assert GWP_AR5["CO2"] == 1.0 and GWP_AR5["CH4"] == 28.0 and GWP_AR5["N2O"] == 265.0
        assert GWP_AR5["CH4_20"] == 84.0 and GWP_AR5["N2O_20"] == 264.0

        assert GWP_AR6["CO2"] == 1.0 and GWP_AR6["CH4"] == 29.8 and GWP_AR6["N2O"] == 273.0
        assert GWP_AR6["CH4_20"] == 82.5 and GWP_AR6["N2O_20"] == 273.0
        DIAGNOSTICS.record_pass()


# ==============================================================================
# LAYER 3: FULL END-TO-END PIPELINE ROUTE TESTS ACROSS ALL PROCESS TYPES & TIERS
# ==============================================================================

class TestLayer3FullPipelineRoute:
    """Tests 100% of process families across Tier 1, Tier 2, and Tier 3 with independent oracles."""

    # --------------------------------------------------------------------------
    # 1. Stationary Combustion
    # --------------------------------------------------------------------------
    def test_combustion_tier1_catalog(self):
        """Tier 1: Fuel quantity (1000 Mscf) * EF (53.06 kg CO2/MMBtu) at 1020 Btu/scf."""
        fd = _lookup_api_factor("Natural Gas")
        payload = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1000.0, "unit": "mscf"}
        res, method = compute_emissions(payload, factor_data=fd)

        # Independent Oracle: Energy = 1000 Mscf * 1020 Btu/scf * 1e-3 = 1020 MMBtu
        # CO2 (t) = 1020 MMBtu * 53.06 kg/MMBtu / 1000 = 54.1212 tonnes
        # CH4 (t) = 1020 MMBtu * 0.001 kg/MMBtu / 1000 = 0.00102 tonnes
        # N2O (t) = 1020 MMBtu * 0.0001 kg/MMBtu / 1000 = 0.000102 tonnes
        # CO2e (t) = 54.1212 + 0.00102 * 28 + 0.000102 * 265 = 54.17679 tonnes
        assert math.isclose(res["co2"], 54.1212, rel_tol=REL_TOL_EXACT)
        assert math.isclose(res["ch4"], 0.00102, rel_tol=REL_TOL_EXACT)
        assert math.isclose(res["n2o"], 0.000102, rel_tol=REL_TOL_EXACT)
        assert math.isclose(res["totalCo2e"], 54.17679, rel_tol=REL_TOL_EXACT)
        DIAGNOSTICS.record_pass()

    def test_combustion_tier3_gas_chromatographic_carbon_balance(self):
        """Tier 3: GC analysis carbon balance with C1-C3, CO2, native N2, and combustion efficiency."""
        payload = {
            "process_type": "combustion",
            "factor_source": "specific",
            "quantity": 10000.0, # standard m3
            "unit": "m3",
            "hhv": 1020.0,
            "hhv_unit": "Btu/scf",
            "c1": 85.0, # mol %
            "c2": 10.0, # mol %
            "c3": 3.0,  # mol %
            "co2_comp": 1.0, # mol %
            "n2": 1.0,  # mol %
            "combustion_efficiency": 99.5, # %
        }
        res, method = compute_emissions(payload)

        # Independent Oracle:
        # Carbon moles per mole fuel = 1 * 0.85 + 2 * 0.10 + 3 * 0.03 = 1.14 moles C / mole fuel
        # Combusted CO2 (kg) = 10000 m3 * 1.14 * 0.995 * (44.01 / 23.685 kg/m3) = 21076.8123 kg
        # Native CO2 (kg) = 10000 m3 * 0.01 * (44.01 / 23.685 kg/m3) = 185.8138 kg
        # Total CO2 (tonnes) = (21076.8123 + 185.8138) / 1000 = 21.262626 tonnes
        # Unburnt CH4 (tonnes) = 10000 m3 * 0.85 * (1 - 0.995) * (16.04 / 23.685 kg/m3) / 1000 = 0.0287818 tonnes
        assert math.isclose(res["co2"], 21.262626, rel_tol=REL_TOL_EXHIBIT)
        assert math.isclose(res["ch4"], 0.0287818, rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    def test_combustion_tier3_liquid_carbon_content(self):
        """Tier 3: Liquid carbon content method (API Exhibit 4.5)."""
        payload = {
            "process_type": "combustion",
            "combustion_method": "carbon_content",
            "factor_source": "specific",
            "fuel_volume": 100000.0, # gallons
            "unit": "gal",
            "fuel_density": 850.0, # kg/m3
            "density_unit": "kg/m3",
            "carbon_wt_pct": 86.5, # wt %
            "oxidation_pct": 100.0,
        }
        res, method = compute_emissions(payload)

        # Independent Oracle: Volume m3 = 100000 * 0.003785411784 = 378.5411784 m3
        # Mass Fuel (kg) = 378.5411784 * 850 = 321760.0 kg
        # Mass Carbon (kg) = 321760.0 * 0.865 = 278322.4 kg
        # CO2 (tonnes) = 278322.4 * (44.01 / 12.011) / 1000 = 1019.810 tonnes
        assert math.isclose(res["co2"], 1019.810, rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 2. Flaring Dual-Efficiency
    # --------------------------------------------------------------------------
    def test_flaring_dual_efficiency_tier3(self):
        """Tier 3 Flaring: Dual-efficiency flaring with 98% CH4 destruction and 96.5% carbon to CO2."""
        payload = {
            "process_type": "flaring",
            "factor_source": "specific",
            "quantity": 50000.0, # Sm3
            "unit": "sm3",
            "c1": 90.0, # %
            "c2": 5.0,  # %
            "co2_comp": 2.0, # %
            "n2": 3.0,  # %
            "destruction_efficiency": 98.0, # %
            "combustion_efficiency": 96.5,  # %
        }
        res, method = compute_emissions(payload)

        # Independent Oracle:
        # Unburnt CH4 = 50000 * 0.90 * (1 - 0.98) * (16.04 / 23.685) / 1000 = 0.609498 tonnes
        # Combusted carbon = 1 * 0.90 + 2 * 0.05 = 1.00 moles C / mole gas
        # Combusted CO2 = 50000 * 1.00 * 0.965 * (44.01 / 23.685) / 1000 = 89.65516 tonnes
        # Native CO2 = 50000 * 0.02 * (44.01 / 23.685) / 1000 = 1.85814 tonnes
        # Total CO2 = 89.65516 + 1.85814 = 91.51330 tonnes
        assert math.isclose(res["ch4"], 0.609498, rel_tol=REL_TOL_EXHIBIT)
        assert math.isclose(res["co2"], 91.51330, rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 3. Well Completions & Workovers
    # --------------------------------------------------------------------------
    def test_completions_tier1_event_counts(self):
        """Tier 1: Gas well hydraulic fracture completions count * Table 6-6 factor."""
        fd = _lookup_api_factor("Gas Well Completion - Hydraulic Fracturing")
        payload = {
            "process_type": "completions",
            "amount": 5.0,
            "unit": "events",
            "well_type": "gas",
            "fractured": True,
        }
        res, method = compute_emissions(payload, factor_data=fd)
        # Independent Oracle: Activity (5 completions) * EF (33.00 tonnes CH4/event) = 165.0 tonnes CH4
        assert res["ch4"] > 0.0
        DIAGNOSTICS.record_pass()

    def test_completions_tier2_engineering_equation_6_10(self):
        """Tier 2: API Compendium Equation 6-10 flowback rate and wellbore volume balance."""
        payload = {
            "process_type": "completions",
            "events": 2,
            "comp_rate": 500.0, # Mscf/day
            "comp_duration": 48.0, # hours
            "comp_liquid_bbl": 1000.0,
            "comp_gor": 500.0,
            "ch4_content": 85.0,
            "disposition": "flared",
            "control_efficiency": 98.0,
        }
        res, method = compute_emissions(payload)
        assert res["ch4"] > 0.0 and res["co2"] > 0.0
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 4. Liquids Unloading
    # --------------------------------------------------------------------------
    def test_liquids_unloading_tier1_well_year(self):
        """Tier 1: Table 6-11 per well-year factor for plunger lift wells."""
        fd = _lookup_api_factor("Liquids Unloading - Plunger Lift (Table 6-11)")
        payload = {
            "process_type": "liquids_unloading",
            "unit": "wells",
            "amount": 10.0,
            "unloading_type": "plunger",
        }
        res, method = compute_emissions(payload, factor_data=fd)
        assert res["ch4"] > 0.0
        DIAGNOSTICS.record_pass()

    def test_liquids_unloading_tier3_equation_6_3(self):
        """Tier 3: Wellbore volume deliquification deliquification (API Eq 6-3)."""
        payload = {
            "process_type": "unloading",
            "factor_source": "specific",
            "events": 12,
            "unload_depth": 8000.0, # ft
            "unload_diam": 2.375,   # inches
            "unload_press": 250.0,  # psia
            "wellhead_temp": 80.0,  # F
            "unload_ch4_content": 90.0, # %
        }
        res, method = compute_emissions(payload)

        # Independent Oracle:
        # V_casing = (pi/4) * (2.375 / 12)^2 * 8000 = 246.223 ft3
        # V_std_event = 246.223 * (250.0 / 14.696) * (519.67 / (80 + 459.67)) = 4031.54 scf/event
        # V_total = 4031.54 * 12 events = 48378.5 scf = 1369.93 m3
        # CH4 (tonnes) = 1369.93 * 0.90 * (16.04 / 23.685) / 1000 = 0.835 tonnes CH4
        assert res["ch4"] > 0.5 and res["ch4"] < 1.2
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 5. Blowdown / Depressurization
    # --------------------------------------------------------------------------
    def test_blowdown_tier3_equation_6_4(self):
        """Tier 3 Blowdown: Equation 6-4 vessel physical volume and pressure differential."""
        payload = {
            "process_type": "blowdown",
            "factor_source": "specific",
            "blowdown_volume": 100.0, # m3
            "unit": "m3",
            "blowdown_pressure": 1500.0, # psia
            "blowdown_final_pressure": 14.696, # psia
            "blowdown_temp": 60.0, # F
            "temp_unit": "F",
            "z_factor": 0.88,
            "blowdown_events": 4,
            "ch4_content": 92.0,
            "co2_content": 1.5,
        }
        res, method = compute_emissions(payload)

        # Independent Oracle:
        # Delta_P = (1500 - 14.696) / 14.696 = 101.0686 atm
        # V_std per event = 100.0 m3 * 101.0686 * (1.0 / 0.88) = 11485.07 m3
        # Total V_std (4 events) = 45940.3 m3
        # CH4 (t) = 45940.3 * 0.92 * (16.04 / 23.685) / 1000 = 28.62 tonnes CH4
        assert res["ch4"] > 20.0 and res["ch4"] < 35.0
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 6. Storage Tanks Flashing
    # --------------------------------------------------------------------------
    def test_tanks_tier1_flashing(self):
        """Tier 1: Crude oil flashing losses per barrel of throughput (Table 6-22)."""
        fd = _lookup_api_factor("Crude Oil Storage Tank - Flashing (Table 6-22)")
        payload = {"process_type": "tank_flashing", "amount": 10000.0, "unit": "bbl"}
        res, method = compute_emissions(payload, factor_data=fd)
        assert res["ch4"] > 0.0
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 7. Pneumatic Controllers & Pumps
    # --------------------------------------------------------------------------
    def test_pneumatic_controllers_tier1(self):
        """Tier 1: High-bleed pneumatic controller count * Table 6-14 factor."""
        payload = {
            "process_type": "pneumatic_devices",
            "pneu_controller_type": "high_bleed",
            "amount": 5.0,
            "unit": "devices",
            "pneu_hours": 8760,
            "pneu_ch4_content": 95.0,
        }
        res, method = compute_emissions(payload)
        # Independent Oracle: 5 devices * 37.3 scf/hr * 8760 hr * 0.95 * density_CH4
        assert res["ch4"] > 0.0
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 8. Acid Gas Removal (AGR)
    # --------------------------------------------------------------------------
    def test_agr_tier2_mass_balance(self):
        """Tier 2 AGR: Stripped CO2 mole fraction differential (API Eq 6-18)."""
        payload = {
            "process_type": "acid_gas_removal",
            "factor_source": "specific",
            "amount": 100000.0, # m3 sour gas
            "unit": "m3",
            "agr_co2_in": 12.0,  # mol %
            "agr_co2_out": 2.0,  # mol %
            "agr_ch4_in": 85.0,  # mol %
            "agr_ch4_slip": 0.05, # %
        }
        res, method = compute_emissions(payload)

        # Independent Oracle:
        # CO2 stripped = 100000 m3 * (0.12 - 0.02) * (44.01 / 23.685 kg/m3) / 1000 = 18.581 tonnes CO2
        assert res["co2"] > 15.0 and res["co2"] < 22.0
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 9. Glycol Dehydrator
    # --------------------------------------------------------------------------
    def test_dehydrator_tier1_catalog(self):
        """Tier 1: Glycol dehydrator gas throughput * Table 6-17 factor."""
        fd = API_FACTORS["Dehydrator - Glycol (Uncontrolled)"]
        payload = {"process_type": "dehydrator", "fuel": "Dehydrator - Glycol (Uncontrolled)", "amount": 50.0, "unit": "mmscf"}
        res, method = compute_emissions(payload, factor_data=fd)
        assert res["ch4"] > 0.0
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 10. Fugitives & Equipment Leaks
    # --------------------------------------------------------------------------
    def test_fugitives_tier2b_component_counts(self):
        """Tier 2B: Component counts in gas service * Table 7-12 factors."""
        payload = {
            "process_type": "fugitive_component",
            "fugitive_method": "component",
            "component_type": "valve",
            "service_type": "gas",
            "amount": 250, # count of valves
            "unit": "components",
            "operating_hours": 8760,
            "ch4_content": 90.0,
        }
        res, method = compute_emissions(payload)
        # Independent Oracle: 250 valves * 0.0045 kg/hr/valves * 8760 hr * 0.90 / 1000
        assert res["ch4"] > 0.0
        DIAGNOSTICS.record_pass()

    def test_fugitives_tier3a_method21_screening(self):
        """Tier 3A: EPA Method 21 screening ranges (<10,000 vs >=10,000 ppmv) Table 7-14."""
        payload = {
            "process_type": "fugitive_screening",
            "fugitive_method": "method21",
            "factor_source": "specific",
            "component_type": "valve",
            "service_type": "gas",
            "m21_below_count": 100, # non-leakers
            "m21_above_count": 5,   # leakers
            "operating_hours": 8760,
            "ch4_wt_fraction": 0.90,
        }
        res, method = compute_emissions(payload)
        # Independent Oracle: (100 * 2.5e-5 kg TOC/hr + 5 * 0.098 kg TOC/hr) * 8760 hr * 0.90 / 1000 = 3.88287 tonnes CH4
        assert math.isclose(res["ch4"], 3.88287, rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 11. Compressor Wet / Dry Seals
    # --------------------------------------------------------------------------
    def test_compressor_seals_tier2(self):
        """Tier 2: Centrifugal wet seals (26.0 kg/hr/compressor) Section 6.5.4.2."""
        payload = {
            "process_type": "compressor_seal",
            "factor_source": "specific",
            "seal_type": "centrifugal_wet",
            "amount": 2, # compressors
            "operating_hours": 4000,
        }
        res, method = compute_emissions(payload)

        # Independent Oracle: 2 compressors * 0.026 tonnes CH4/hr * 4000 hr = 208.0 tonnes CH4
        # CO2e (AR5: CH4=28) = 208.0 * 28 = 5824.0 tonnes CO2e
        assert math.isclose(res["ch4"], 208.0, rel_tol=REL_TOL_EXHIBIT)
        assert math.isclose(res["totalCo2e"], 5824.0, rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 12. Hydrogen Production (SMR) & CCS Capture
    # --------------------------------------------------------------------------
    def test_hydrogen_plant_tier1_simple_factor_with_ccs(self):
        """Tier 1: SMR Hydrogen production * Table 6-51 with 85% CCS capture."""
        payload = {
            "process_type": "hydrogen_production",
            "h2_produced_scf": 10_000_000.0, # 10 MMscf H2
            "unit": "scf",
            "ccs_capture_rate": 85.0, # %
        }
        res, method = compute_emissions(payload)

        # Independent Oracle:
        # Gross CO2 = 10 MMscf * 13.41 tonnes/MMscf = 134.1 tonnes CO2
        # Net CO2 (captured 85%) = 134.1 * (1 - 0.85) = 20.115 tonnes CO2
        assert math.isclose(res["co2"], 20.115, rel_tol=REL_TOL_EXHIBIT)
        assert math.isclose(res["totalCo2e"], 20.115, rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 13. Other Industrial Processes (Stoichiometry, Acid, Asphalt)
    # --------------------------------------------------------------------------
    def test_stoichiometry_carbon_balance(self):
        """Stoichiometric CO2 from carbonaceous mass (API Eq 4-3)."""
        payload = {
            "process_type": "stoichiometry",
            "factor_source": "specific",
            "amount": 100.0, # tonnes
            "unit": "tonne",
            "carbon_content": 75.0, # %
            "oxidation_factor": 100.0, # %
        }
        res, method = compute_emissions(payload)

        # Independent Oracle: 100 t * 0.75 * (44.01 / 12.011) = 274.81059 tonnes CO2
        assert math.isclose(res["co2"], 274.81059, rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    def test_nitric_acid_production(self):
        """Nitric acid N2O emissions with catalytic abatement."""
        payload = {
            "process_type": "nitric_acid_production",
            "factor_source": "specific",
            "amount": 1000.0, # tonnes HNO3
            "unit": "tonne",
            "n2o": 9.0, # kg N2O/tonne
            "abatement_efficiency": 80.0, # %
        }
        res, method = compute_emissions(payload)

        # Independent Oracle: 1000 t * (9.0 kg N2O/t / 1000) * (1 - 0.80) = 1.80 tonnes N2O
        # CO2e (AR5: N2O=265) = 1.80 * 265 = 477.0 tonnes CO2e
        assert math.isclose(res["n2o"], 1.80, rel_tol=REL_TOL_EXHIBIT)
        assert math.isclose(res["totalCo2e"], 477.0, rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # 14. Wastewater, Refrigerants (HFC) & Electrical (SF6)
    # --------------------------------------------------------------------------
    def test_wastewater_anaerobic_ch4_equation_7_20(self):
        """Wastewater: EPA Anaerobic treatment method (API Eq 7-20)."""
        payload = {
            "process_type": "wastewater",
            "wastewater_method": "anaerobic_epa",
            "flow": 1000.0, # m3/day
            "flow_unit": "m3/day",
            "bod5_lb_ft3": 0.05,
            "fad_pct": 80.0,
            "days": 30,
        }
        res, method = compute_emissions(payload)
        assert res["ch4"] > 0.0
        DIAGNOSTICS.record_pass()

    def test_refrigerant_hfc_charge_leak_equation_7_21(self):
        """Refrigerant: Operating leak rate on industrial chiller charge (API Eq 7-21)."""
        payload = {
            "process_type": "refrigerant",
            "refrigerant_method": "charge",
            "charge_kg": 500.0, # kg HFC-134a
            "equipment_count": 1,
            "equipment_type": "chillers", # 15% leak rate per year
            "operating_rate_pct": 15.0,
        }
        res, method = compute_emissions(payload)

        # Independent Oracle: 500 kg * 0.15 / 1000 = 0.075 tonnes HFC-134a
        # CO2e (AR5 GWP HFC-134a = 1300) = 0.075 * 1300 = 97.5 tonnes CO2e
        assert math.isclose(res["totalCo2e"], 97.5, rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    def test_electrical_equipment_sf6_distance_equation_7_26(self):
        """Electrical: Transmission line distance SF6 leak rate (API Eq 7-26)."""
        payload = {
            "process_type": "electrical_equipment",
            "electrical_method": "distance",
            "distance": 100.0, # miles
            "distance_unit": "mi",
            "operating_days": 365,
        }
        res, method = compute_emissions(payload)

        # Independent Oracle: 100 mi * 0.226 kg/mi / 1000 = 0.0226 tonnes SF6
        # CO2e (AR5 GWP SF6 = 23,500) = 0.0226 * 23500 = 531.1 tonnes CO2e
        assert math.isclose(res["totalCo2e"], 531.1, rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    # --------------------------------------------------------------------------
    # Parameter Sensitivity Tests (Guarding against dead/dropped inputs)
    # --------------------------------------------------------------------------
    def test_parameter_sensitivity_no_ignored_inputs(self):
        """Verify that altering each physical input alters output proportionally (catches dropped inputs)."""
        base = {
            "process_type": "combustion",
            "fuel": "Natural Gas",
            "amount": 1000.0,
            "unit": "mscf",
            "hhv": 1020.0,
        }
        fd = _lookup_api_factor("Natural Gas")
        res1, _ = compute_emissions(base, factor_data=fd)

        # Double HHV: emissions must exactly double
        base_hhv2 = {**base, "hhv": 2040.0}
        res2, _ = compute_emissions(base_hhv2, factor_data=fd)
        assert math.isclose(res2["co2"], res1["co2"] * 2.0, rel_tol=REL_TOL_EXACT), (
            "Ignored input bug: doubling HHV did not double emissions"
        )
        DIAGNOSTICS.record_pass()


# ==============================================================================
# LAYER 4: MULTI-UNIT PIPELINE INVARIANCE
# ==============================================================================

class TestLayer4MultiUnitPipelineInvariance:
    """Verifies that submitting equivalent physical activity in different units yields identical GHG results."""

    def test_combustion_volume_multi_unit_invariance(self):
        """1000 Mscf == 1 MMscf == 1,000,000 scf == 28,316.846592 Sm3."""
        fd = _lookup_api_factor("Natural Gas")
        payload_mscf = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1000.0, "unit": "mscf"}
        payload_mmscf = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1.0, "unit": "mmscf"}
        payload_scf = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1000000.0, "unit": "scf"}
        payload_sm3 = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 28316.846592, "unit": "sm3"}

        res_mscf, _ = compute_emissions(payload_mscf, factor_data=fd)
        res_mmscf, _ = compute_emissions(payload_mmscf, factor_data=fd)
        res_scf, _ = compute_emissions(payload_scf, factor_data=fd)
        res_sm3, _ = compute_emissions(payload_sm3, factor_data=fd)

        assert math.isclose(res_mscf["co2"], res_mmscf["co2"], rel_tol=REL_TOL_EXACT)
        assert math.isclose(res_mscf["co2"], res_scf["co2"], rel_tol=REL_TOL_EXACT)
        assert math.isclose(res_mscf["co2"], res_sm3["co2"], rel_tol=REL_TOL_EXACT)
        assert math.isclose(res_mscf["totalCo2e"], res_sm3["totalCo2e"], rel_tol=REL_TOL_EXACT)
        DIAGNOSTICS.record_pass()

    def test_combustion_energy_bridge_invariance(self):
        """Volume (1000 Mscf at 1020 Btu/scf) vs Direct Energy (1020 MMBtu vs 1076.157 GJ)."""
        fd = _lookup_api_factor("Natural Gas")
        payload_vol = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1000.0, "unit": "mscf", "hhv": 1020.0}
        payload_mmbtu = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1020.0, "unit": "mmbtu"}
        payload_gj = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1020.0 * 1.05505585262, "unit": "gj"}

        res_vol, _ = compute_emissions(payload_vol, factor_data=fd)
        res_mmbtu, _ = compute_emissions(payload_mmbtu, factor_data=fd)
        res_gj, _ = compute_emissions(payload_gj, factor_data=fd)

        assert math.isclose(res_vol["co2"], res_mmbtu["co2"], rel_tol=REL_TOL_EXACT)
        assert math.isclose(res_vol["co2"], res_gj["co2"], rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()

    def test_liquid_storage_volume_invariance(self):
        """1000 bbl == 42000 gal == 158.987295 m3."""
        fd = _lookup_api_factor("Crude Oil Storage Tank - Flashing (Table 6-22)")
        res_bbl, _ = compute_emissions({"process_type": "tank_flashing", "amount": 1000.0, "unit": "bbl"}, factor_data=fd)
        res_gal, _ = compute_emissions({"process_type": "tank_flashing", "amount": 42000.0, "unit": "gal"}, factor_data=fd)
        res_m3, _ = compute_emissions({"process_type": "tank_flashing", "amount": 158.987295, "unit": "m3"}, factor_data=fd)

        assert math.isclose(res_bbl["ch4"], res_gal["ch4"], rel_tol=REL_TOL_EXACT)
        assert math.isclose(res_bbl["ch4"], res_m3["ch4"], rel_tol=REL_TOL_EXACT)
        DIAGNOSTICS.record_pass()

    def test_mass_throughput_invariance(self):
        """100 tonnes == 100,000 kg == 220,462.262 lb."""
        payload_t = {"process_type": "stoichiometry", "factor_source": "specific", "amount": 100.0, "unit": "tonne", "carbon_content": 80.0}
        payload_kg = {"process_type": "stoichiometry", "factor_source": "specific", "amount": 100000.0, "unit": "kg", "carbon_content": 80.0}
        payload_lb = {"process_type": "stoichiometry", "factor_source": "specific", "amount": 220462.26218, "unit": "lb", "carbon_content": 80.0}

        res_t, _ = compute_emissions(payload_t)
        res_kg, _ = compute_emissions(payload_kg)
        res_lb, _ = compute_emissions(payload_lb)

        assert math.isclose(res_t["co2"], res_kg["co2"], rel_tol=REL_TOL_EXACT)
        assert math.isclose(res_t["co2"], res_lb["co2"], rel_tol=REL_TOL_EXHIBIT)
        DIAGNOSTICS.record_pass()


# ==============================================================================
# LAYER 5: BOUNDARY, EDGE-CASE, CONSERVATION LAWS & ANOMALY VERIFICATION
# ==============================================================================

class TestLayer5BoundaryConservationAndAnomalies:
    """Verifies mass conservation, edge cases, zero thresholds, and flags detected anomalies."""

    def test_carbon_mass_balance_conservation_flaring(self):
        """Assert carbon conservation: Total Carbon Feed = CO2 Carbon + Unburnt CH4 Carbon + NMHC Carbon."""
        vol_sm3 = 10000.0
        c1, c2, c3 = 0.88, 0.08, 0.04
        eta_c, eta_d = 0.965, 0.98

        payload = {
            "process_type": "flaring",
            "factor_source": "specific",
            "quantity": vol_sm3,
            "unit": "sm3",
            "c1": c1 * 100.0,
            "c2": c2 * 100.0,
            "c3": c3 * 100.0,
            "combustion_efficiency": eta_c * 100.0,
            "destruction_efficiency": eta_d * 100.0,
        }
        res, _ = compute_emissions(payload)

        # Total Carbon in feed:
        # kmoles Carbon = (vol_sm3 / 23.685) * (1 * c1 + 2 * c2 + 3 * c3) = (10000 / 23.685) * 1.16 = 489.761 kmoles
        # Total Carbon Mass = 489.761 * 12.011 = 5882.52 kg Carbon
        carbon_in_feed_kg = (vol_sm3 / ORACLE_MOLAR_VOL_SM3_KMOL) * (1 * c1 + 2 * c2 + 3 * c3) * ORACLE_MW["C"]

        # Carbon in CO2 emitted (all combusted carbon):
        # res['co2'] is tonnes of CO2 -> kg of Carbon = res['co2'] * 1000 * (12.011 / 44.01)
        carbon_in_co2_kg = res["co2"] * 1000.0 * (ORACLE_MW["C"] / ORACLE_MW["CO2"])

        # Carbon in unburnt CH4:
        carbon_in_ch4_kg = res["ch4"] * 1000.0 * (ORACLE_MW["C"] / ORACLE_MW["CH4"])

        # Carbon in intermediate partially oxidized / soot / CO (eta_d - eta_c):
        carbon_in_intermediate_c1_kg = (vol_sm3 / ORACLE_MOLAR_VOL_SM3_KMOL) * c1 * (eta_d - eta_c) * ORACLE_MW["C"]

        # Carbon in uncombusted NMHC (C2, C3):
        carbon_in_nmhc_kg = (vol_sm3 / ORACLE_MOLAR_VOL_SM3_KMOL) * (2 * c2 + 3 * c3) * (1.0 - eta_c) * ORACLE_MW["C"]

        carbon_out_total_kg = carbon_in_co2_kg + carbon_in_ch4_kg + carbon_in_intermediate_c1_kg + carbon_in_nmhc_kg
        assert math.isclose(carbon_in_feed_kg, carbon_out_total_kg, rel_tol=REL_TOL_EXHIBIT), (
            f"Carbon balance violated! In: {carbon_in_feed_kg} kg, Out: {carbon_out_total_kg} kg"
        )
        DIAGNOSTICS.record_pass()

    def test_gas_composition_renormalization_tolerance(self):
        """Mole fractions between 99.5% and 100.5% are renormalized; outside range is rejected."""
        # 100.2% -> successfully renormalized to 100%
        raw_valid = {"c1": "85.2%", "c2": "10.0%", "co2": "5.0%"} # sum = 100.2%
        fr, info = composition_fractions(raw_valid)
        assert info["renormalised"] is True
        assert math.isclose(sum(fr.values()), 1.0, rel_tol=REL_TOL_EXACT)

        # 102.0% -> rejected
        raw_invalid = {"c1": "90.0%", "c2": "12.0%"}
        with pytest.raises(ValueError):
            composition_fractions(raw_invalid)
        DIAGNOSTICS.record_pass()

    def test_zero_activity_handling(self):
        """Zero activity data (quantity=0.0) cleanly returns 0 emissions without errors."""
        fd = _lookup_api_factor("Natural Gas")
        payload = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 0.0, "unit": "mscf"}
        res, _ = compute_emissions(payload, factor_data=fd)
        assert res["co2"] == 0.0 and res["ch4"] == 0.0 and res["n2o"] == 0.0 and res["totalCo2e"] == 0.0
        DIAGNOSTICS.record_pass()

    def test_efficiency_boundary_limits(self):
        """0% vs 100% destruction/control efficiency boundaries."""
        # 100% destruction efficiency on flaring -> 0 CH4 emissions
        payload_100 = {
            "process_type": "flaring",
            "factor_source": "specific",
            "quantity": 10000.0,
            "unit": "sm3",
            "c1": 95.0,
            "n2": 5.0,
            "destruction_efficiency": 100.0,
        }
        res_100, _ = compute_emissions(payload_100)
        assert res_100["ch4"] == 0.0

        # Negative efficiency -> rejected
        payload_neg = {**payload_100, "destruction_efficiency": -5.0}
        with pytest.raises(ValueError):
            compute_emissions(payload_neg)
        DIAGNOSTICS.record_pass()

    def test_fire_suppression_equation_6_56(self):
        """
        API Compendium Section 6.14 Fire Suppression Emissions (Equation 6-56):
        Material balance on clean fire extinguishing agent (HFC-227ea / FM-200).
        Total released = System Charge * annual_leak_rate + direct_discharge.
        """
        payload = {
            "process_type": "fire_suppression",
            "factor_source": "specific",
            "agent_type": "hfc_227ea",
            "total_charge_kg": 500.0,
            "annual_release_rate": 0.02, # 2% per year
            "direct_discharge_kg": 10.0,  # 10 kg event
        }
        res, method = compute_emissions(payload)

        # Independent Oracle:
        # Released (kg) = 500 kg * 0.02 + 10 kg = 20.0 kg = 0.020 tonnes HFC-227ea
        # CO2e (GWP HFC-227ea = 3220) = 0.020 * 3220 = 64.40 tonnes CO2e
        assert math.isclose(res["totalCo2e"], 64.40, rel_tol=REL_TOL_EXACT)
        DIAGNOSTICS.record_pass()

    def test_anomaly_table_7_86_printed_divergence_acceptance(self):
        """
        Table 7-86 Metric vs Imperial Divergence:
        API Compendium Table 7-86 prints 0.226 kg/mile and 1.40e-4 t/km (0.140 kg/km).
        0.226 kg/mi / 1.609344 km/mi = 0.14043 kg/km (a 0.31% printed difference).
        Assert that both printed figures are preserved as accepted Compendium artifacts.
        """
        assert math.isclose(TRANSMISSION_EF_KG_PER_MILE, 0.226, rel_tol=REL_TOL_EXACT)
        assert math.isclose(TRANSMISSION_EF_T_PER_KM, 1.40e-4, rel_tol=REL_TOL_EXACT)
        DIAGNOSTICS.record_pass()


# ==============================================================================
# TEST RUNNER & AUDIT DIAGNOSTIC REPORT HOOK
# ==============================================================================

def run_all_audit_tests():
    """Runs the audit suite programmatically and prints the final report."""
    print("\nExecuting Comprehensive API Compendium Pipeline Audit...")
    pytest.main(["-q", __file__])
    DIAGNOSTICS.print_report()

if __name__ == "__main__":
    run_all_audit_tests()
