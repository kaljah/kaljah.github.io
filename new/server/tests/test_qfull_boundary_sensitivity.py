"""
test_qfull_boundary_sensitivity.py

QFULL END-TO-END CALCULATION PIPELINE VALIDATION
Phase 4: Boundary Conditions and OAT Sensitivity

Tests:
1. Boundary conditions: zero, negative, very large/small quantities, NaN, Inf
2. OAT (One-At-a-Time) sensitivity: changing ONE input changes output
   according to the mathematical relationship while others remain constant.

API Reference: API Compendium 2021
Date: 2026-09-21
"""

import sys
import os
import math
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from calculations.legacy_engine import compute_emissions
from calculations.units import calculate_co2e

# =====================================================================
# INDEPENDENT REFERENCE CONSTANTS
# =====================================================================
SCF_TO_M3 = 0.028316846592
M3_TO_SCF = 35.314666721
DENSITY_CH4 = 0.6785
DENSITY_CO2 = 1.861
STD_PRESS_PSIA = 14.696
STD_TEMP_K = 288.706
GWP_CO2 = 1.0
GWP_CH4_AR5 = 28.0
GWP_N2O_AR5 = 265.0
BBL_TO_M3 = 0.158987295


def ref_co2e(co2=0.0, ch4=0.0, n2o=0.0):
    return co2 * GWP_CO2 + ch4 * GWP_CH4_AR5 + n2o * GWP_N2O_AR5


# =====================================================================
# BASELINE PARAMETERS (used across OAT tests)
# =====================================================================
BASELINE_PAYLOAD = {
    "process_type": "combustion",
    "quantity": 1000.0,
    "unit": "m3",
    "factor_source": "default",
}
BASELINE_FACTOR = {
    "co2": 1.9,       # kg/m3
    "ch4": 0.00004,   # kg/m3
    "n2o": 0.000002,  # kg/m3
    "unit": "kg/m3",
    "hhv": 1020.0,
}
# INDEPENDENT EXPECTED BASELINE VALUES:
# co2  = 1000 * 1.9    / 1000 = 1.9      t
# ch4  = 1000 * 0.00004 / 1000 = 0.00004  t
# n2o  = 1000 * 0.000002/1000 = 0.000002 t
# co2e = 1.9*1 + 0.00004*28 + 0.000002*265 = 1.9 + 0.00112 + 0.00053 = 1.90165 t
BASELINE_CO2 = 1.9
BASELINE_CH4 = 0.00004
BASELINE_N2O = 0.000002
BASELINE_CO2E = ref_co2e(BASELINE_CO2, BASELINE_CH4, BASELINE_N2O)


# =====================================================================
# TEST CLASS: Boundary Conditions
# =====================================================================
class TestBoundaryConditions:
    """Tests that emission results at boundary inputs behave correctly."""

    # ------------------------------------------------------------------
    def test_zero_quantity_combustion_yields_zero(self):
        """
        BOUNDARY: Zero activity = zero emissions (all gases).
        Formula: Q * EF = 0 * anything = 0.
        """
        payload = {**BASELINE_PAYLOAD, "quantity": 0.0}
        em, _ = compute_emissions(payload, BASELINE_FACTOR)
        assert em["co2"] == 0.0, f"CO2 should be 0, got {em['co2']}"
        assert em["ch4"] == 0.0, f"CH4 should be 0, got {em['ch4']}"
        assert em["n2o"] == 0.0, f"N2O should be 0, got {em['n2o']}"
        assert em["totalCo2e"] == 0.0, f"CO2e should be 0, got {em['totalCo2e']}"

    def test_zero_quantity_mud_degassing_yields_zero(self):
        """BOUNDARY: Zero mud volume = zero CH4 from degassing."""
        em, _ = compute_emissions({
            "process_type": "drilling", "quantity": 0.0, "unit": "m3",
            "factor_source": "specific", "mud_type": "water_based"
        }, {})
        assert em["ch4"] == 0.0
        assert em["totalCo2e"] == 0.0

    def test_zero_quantity_completions_yields_zero(self):
        """BOUNDARY: Zero flowback gas = zero CH4 from completions."""
        em, _ = compute_emissions({
            "process_type": "completions", "quantity": 0.0, "unit": "m3",
            "factor_source": "specific", "ch4_content": 0.85,
            "comp_method": "metered_volume"
        }, {})
        assert em["ch4"] == 0.0
        assert em["totalCo2e"] == 0.0

    def test_zero_quantity_tank_flashing_yields_zero(self):
        """BOUNDARY: Zero tank throughput = zero emissions."""
        em, _ = compute_emissions({
            "process_type": "tank", "quantity": 0.0, "unit": "bbl",
            "factor_source": "specific", "tank_gor": 100.0,
            "tank_ch4_content": 0.85, "tank_control_eff": 0.0
        }, {})
        assert em["ch4"] == 0.0
        assert em["totalCo2e"] == 0.0

    def test_zero_quantity_blowdown_yields_zero(self):
        """BOUNDARY: Zero vessel volume = zero blowdown emissions."""
        em, _ = compute_emissions({
            "process_type": "blowdown", "quantity": 0.0, "unit": "m3",
            "factor_source": "specific", "blowdown_volume": 0.0,
            "blowdown_pressure": 500.0, "blowdown_events": 10,
            "ch4_content": 0.85
        }, {})
        assert em["ch4"] == 0.0

    def test_zero_ef_combustion_yields_zero(self):
        """
        BOUNDARY: Zero emission factor = zero emissions.
        Even with large quantity, EF=0 → 0 emissions.
        """
        factor_data = {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "unit": "kg/m3", "hhv": 1020.0}
        em, _ = compute_emissions({**BASELINE_PAYLOAD, "quantity": 10000.0}, factor_data)
        assert em["co2"] == 0.0
        assert em["ch4"] == 0.0
        assert em["n2o"] == 0.0
        assert em["totalCo2e"] == 0.0

    def test_zero_ch4_content_completions_yields_zero_ch4(self):
        """
        BOUNDARY: 100% CO2 gas in completions → zero CH4 emitted.
        (ch4_frac=0 → ch4_vol=0)
        """
        em, _ = compute_emissions({
            "process_type": "completions", "quantity": 1000.0, "unit": "m3",
            "factor_source": "specific", "ch4_content": 0.0,
            "comp_method": "metered_volume"
        }, {})
        assert em["ch4"] == 0.0

    def test_negative_quantity_raises_value_error(self):
        """
        BOUNDARY: Negative quantity is physically impossible.
        Dispatcher raises ValueError (validates on line 291 of dispatcher.py).
        """
        with pytest.raises(ValueError, match="cannot be negative"):
            compute_emissions({
                **BASELINE_PAYLOAD, "quantity": -100.0
            }, BASELINE_FACTOR)

    def test_negative_quantity_mud_raises(self):
        """BOUNDARY: Negative mud volume → ValueError."""
        with pytest.raises((ValueError, Exception)):
            compute_emissions({
                "process_type": "drilling", "quantity": -50.0, "unit": "m3",
                "factor_source": "specific", "mud_type": "water_based"
            }, {})

    def test_nan_quantity_raises(self):
        """
        BOUNDARY: NaN quantity is invalid.
        BaseCalculator.validate_inputs() checks math.isnan() and raises ValueError.
        """
        with pytest.raises((ValueError, Exception)):
            compute_emissions({
                **BASELINE_PAYLOAD, "quantity": float("nan")
            }, BASELINE_FACTOR)

    def test_very_large_quantity_scales_linearly(self):
        """
        BOUNDARY: 2e6 m3 should give exactly 2× the emissions of 1e6 m3.
        Linearity of emission formula: E = Q × EF → 2Q → 2E.
        """
        em_1M, _ = compute_emissions({**BASELINE_PAYLOAD, "quantity": 1_000_000.0}, BASELINE_FACTOR)
        em_2M, _ = compute_emissions({**BASELINE_PAYLOAD, "quantity": 2_000_000.0}, BASELINE_FACTOR)

        assert em_2M["co2"] == pytest.approx(2 * em_1M["co2"], rel=1e-6)
        assert em_2M["ch4"] == pytest.approx(2 * em_1M["ch4"], rel=1e-6)
        assert em_2M["n2o"] == pytest.approx(2 * em_1M["n2o"], rel=1e-6)
        assert em_2M["totalCo2e"] == pytest.approx(2 * em_1M["totalCo2e"], rel=1e-6)

    def test_very_small_quantity_is_positive(self):
        """
        BOUNDARY: 1e-6 m3 → very small but positive CO2.
        CO2 = 1e-6 * 1.9 / 1000 = 1.9e-9 t > 0
        """
        em, _ = compute_emissions({**BASELINE_PAYLOAD, "quantity": 1e-6}, BASELINE_FACTOR)
        expected_co2 = 1e-6 * 1.9 / 1000.0
        assert em["co2"] > 0.0
        assert em["co2"] == pytest.approx(expected_co2, rel=1e-4)

    def test_full_control_efficiency_tank_vs_no_control(self):
        """
        BOUNDARY: control_eff=1.0 (fully controlled) vs 0.0 (fully vented).
        Fully controlled → essentially all CH4 routed to flare (with 2% unburnt slip).
        Fully vented → all CH4 emitted.
        Result: ctrl=1.0 gives LESS ch4 than ctrl=0.0.
        """
        def run_tank(ctrl):
            return compute_emissions({
                "process_type": "tank", "quantity": 1000.0, "unit": "bbl",
                "factor_source": "specific", "tank_gor": 100.0,
                "tank_ch4_content": 0.85, "tank_control_eff": ctrl
            }, {})[0]

        em_no_ctrl = run_tank(0.0)
        em_full_ctrl = run_tank(1.0)

        # Full control should drastically reduce CH4
        assert em_full_ctrl["ch4"] < em_no_ctrl["ch4"], (
            f"Full control should reduce CH4: no_ctrl={em_no_ctrl['ch4']:.4f}, "
            f"full_ctrl={em_full_ctrl['ch4']:.4f}"
        )
        # With ctrl=1.0: all routed to flare, only 2% unburnt
        # Expected CH4 ≈ total_ch4 * 0.02 (2% of what would be flared)
        total_raw_ch4 = em_no_ctrl["ch4"]
        expected_ctrl_ch4 = total_raw_ch4 * 0.02   # flared_unburnt = 2%
        assert em_full_ctrl["ch4"] == pytest.approx(expected_ctrl_ch4, rel=1e-3)

    def test_combustion_efficiency_one_minimizes_ch4_slip(self):
        """
        BOUNDARY: T3 combustion with eta_c=1.0 → zero CH4 slip.
        ch4_slip = vol * c1 * (1-eta_c) = vol * c1 * 0 = 0
        """
        em, _ = compute_emissions({
            "process_type": "combustion", "quantity": 500.0, "unit": "m3",
            "factor_source": "specific", "c1": 0.95,
            "combustion_efficiency": 1.0, "hhv": 1020.0
        }, {"co2": 0, "ch4": 0, "n2o": 0, "unit": "kg/m3", "hhv": 1020.0})
        # At perfect combustion: no CH4 slip
        assert em["ch4"] == pytest.approx(0.0, abs=1e-10)

    def test_combustion_efficiency_zero_maximizes_ch4_slip(self):
        """
        BOUNDARY: T3 combustion with eta_c≈0.0 → maximum CH4 slip, minimum CO2.
        ch4_slip = vol * c1 * 1.0 (all uncombusted)
        """
        vol = 500.0
        c1 = 0.90
        eta_c = 0.0001  # Use near-zero (not exactly 0 to avoid division issues)

        em, _ = compute_emissions({
            "process_type": "combustion", "quantity": vol, "unit": "m3",
            "factor_source": "specific", "c1": c1,
            "combustion_efficiency": eta_c, "hhv": 1020.0
        }, {"co2": 0, "ch4": 0, "n2o": 0, "unit": "kg/m3", "hhv": 1020.0})

        # Nearly all gas becomes CH4 slip
        max_possible_ch4 = vol * c1 * DENSITY_CH4 / 1000.0
        # eta_c=0.0001 → slip = vol*c1*(1-0.0001) ≈ 99.99% of ch4
        expected_ch4 = vol * c1 * (1 - eta_c) * DENSITY_CH4 / 1000.0
        assert em["ch4"] == pytest.approx(expected_ch4, rel=1e-3)
        assert em["ch4"] > em["co2"]  # Most of gas is unburnt


# =====================================================================
# TEST CLASS: OAT (One-At-a-Time) Sensitivity Tests
# =====================================================================
class TestOATSensitivity:
    """
    One-at-a-time sensitivity tests: perturb ONE input, verify
    mathematical relationship holds while ALL other outputs remain unchanged.
    """

    def _baseline(self):
        """Run the standard baseline."""
        em, _ = compute_emissions(BASELINE_PAYLOAD, BASELINE_FACTOR)
        return em

    # ------------------------------------------------------------------
    def test_double_quantity_doubles_all_emissions(self):
        """
        OAT: Q → 2Q, EFs unchanged.
        Mathematical relationship: E_i = Q × EF_i → 2Q × EF_i = 2 × E_i
        ALL gases and CO2e should double exactly.
        """
        em_base = self._baseline()

        factor_2x = {**BASELINE_FACTOR}
        em_2x, _ = compute_emissions({**BASELINE_PAYLOAD, "quantity": 2000.0}, factor_2x)

        assert em_2x["co2"] == pytest.approx(2 * em_base["co2"], rel=1e-6), (
            f"2× quantity: CO2 expected {2*em_base['co2']:.6f}, got {em_2x['co2']:.6f}"
        )
        assert em_2x["ch4"] == pytest.approx(2 * em_base["ch4"], rel=1e-6)
        assert em_2x["n2o"] == pytest.approx(2 * em_base["n2o"], rel=1e-6)
        assert em_2x["totalCo2e"] == pytest.approx(2 * em_base["totalCo2e"], rel=1e-6)

    def test_double_ef_co2_only_changes_co2(self):
        """
        OAT: EF_co2 → 2×EF_co2, quantity/EF_ch4/EF_n2o unchanged.
        CO2 should double, CH4 and N2O must remain EXACTLY unchanged.
        """
        em_base = self._baseline()

        factor_2co2 = {**BASELINE_FACTOR, "co2": BASELINE_FACTOR["co2"] * 2}
        em_2co2, _ = compute_emissions(BASELINE_PAYLOAD, factor_2co2)

        assert em_2co2["co2"] == pytest.approx(2 * em_base["co2"], rel=1e-6), (
            f"2× EF_co2: CO2 expected {2*em_base['co2']:.6f}, got {em_2co2['co2']:.6f}"
        )
        # CH4 and N2O must be UNCHANGED (only EF_co2 changed)
        assert em_2co2["ch4"] == pytest.approx(em_base["ch4"], rel=1e-8), (
            f"2× EF_co2 should NOT change CH4: base={em_base['ch4']:.8f}, got={em_2co2['ch4']:.8f}"
        )
        assert em_2co2["n2o"] == pytest.approx(em_base["n2o"], rel=1e-8), (
            f"2× EF_co2 should NOT change N2O: base={em_base['n2o']:.8f}, got={em_2co2['n2o']:.8f}"
        )

    def test_double_ef_ch4_only_changes_ch4(self):
        """
        OAT: EF_ch4 → 2×EF_ch4, quantity/EF_co2/EF_n2o unchanged.
        CH4 should double, CO2 and N2O unchanged.
        """
        em_base = self._baseline()

        factor_2ch4 = {**BASELINE_FACTOR, "ch4": BASELINE_FACTOR["ch4"] * 2}
        em_2ch4, _ = compute_emissions(BASELINE_PAYLOAD, factor_2ch4)

        assert em_2ch4["ch4"] == pytest.approx(2 * em_base["ch4"], rel=1e-6)
        assert em_2ch4["co2"] == pytest.approx(em_base["co2"], rel=1e-8)
        assert em_2ch4["n2o"] == pytest.approx(em_base["n2o"], rel=1e-8)

    def test_double_ef_n2o_only_changes_n2o(self):
        """
        OAT: EF_n2o → 2×EF_n2o, everything else unchanged.
        N2O should double, CO2 and CH4 unchanged.
        """
        em_base = self._baseline()

        factor_2n2o = {**BASELINE_FACTOR, "n2o": BASELINE_FACTOR["n2o"] * 2}
        em_2n2o, _ = compute_emissions(BASELINE_PAYLOAD, factor_2n2o)

        assert em_2n2o["n2o"] == pytest.approx(2 * em_base["n2o"], rel=1e-6)
        assert em_2n2o["co2"] == pytest.approx(em_base["co2"], rel=1e-8)
        assert em_2n2o["ch4"] == pytest.approx(em_base["ch4"], rel=1e-8)

    def test_mud_oil_over_water_ratio_exact(self):
        """
        OAT: Same mud volume, change mud_type: oil_based vs water_based.
        oil_based EF = 0.35 kg/m3, water_based EF = 0.15 kg/m3.
        Ratio = 0.35 / 0.15 = 2.3333...

        Both have IDENTICAL CO2 and N2O (zero), only CH4 differs.
        """
        vol = 100.0

        em_water, _ = compute_emissions({
            "process_type": "drilling", "quantity": vol, "unit": "m3",
            "factor_source": "specific", "mud_type": "water_based"
        }, {})
        em_oil, _ = compute_emissions({
            "process_type": "drilling", "quantity": vol, "unit": "m3",
            "factor_source": "specific", "mud_type": "oil_based"
        }, {})

        expected_ratio = 0.35 / 0.15   # = 2.3333...
        actual_ratio = em_oil["ch4"] / em_water["ch4"]

        assert actual_ratio == pytest.approx(expected_ratio, rel=1e-4), (
            f"Oil/water ratio: expected {expected_ratio:.4f}, got {actual_ratio:.4f}\n"
            f"  water CH4={em_water['ch4']:.6f} t, oil CH4={em_oil['ch4']:.6f} t"
        )
        # CO2 and N2O are zero for both
        assert em_water["co2"] == 0.0
        assert em_oil["co2"] == 0.0

    def test_pneumatic_count_linear_scaling(self):
        """
        OAT: 20 devices vs 10 devices (same hours, bleed_rate, CH4).
        CH4 must be exactly 2× (linear: CH4 = count × hours × bleed × ch4_frac × density).
        """
        base_payload = {
            "process_type": "pneumatic_devices", "quantity": 10.0, "unit": "m3",
            "factor_source": "specific", "pneu_count": 10.0,
            "pneu_hours": 8760.0, "pneu_bleed_rate": 5.0,
            "pneu_bleed_unit": "scf", "pneu_ch4_content": 0.85
        }
        em_10, _ = compute_emissions(base_payload, {})
        em_20, _ = compute_emissions({**base_payload, "pneu_count": 20.0, "quantity": 20.0}, {})

        assert em_20["ch4"] == pytest.approx(2 * em_10["ch4"], rel=1e-6), (
            f"2× count: expected {2*em_10['ch4']:.6f}, got {em_20['ch4']:.6f}"
        )

    def test_pneumatic_hours_linear_scaling(self):
        """
        OAT: 8760 hr vs 4380 hr (same count, bleed_rate, CH4).
        CH4 must be exactly 2× for double hours.
        """
        base_payload = {
            "process_type": "pneumatic_devices", "quantity": 10.0, "unit": "m3",
            "factor_source": "specific", "pneu_count": 10.0,
            "pneu_hours": 4380.0, "pneu_bleed_rate": 5.0,
            "pneu_bleed_unit": "scf", "pneu_ch4_content": 0.85
        }
        em_half, _ = compute_emissions(base_payload, {})
        em_full, _ = compute_emissions({**base_payload, "pneu_hours": 8760.0}, {})

        assert em_full["ch4"] == pytest.approx(2 * em_half["ch4"], rel=1e-6)

    def test_gwp_ar5_vs_ar4_ratio_for_ch4_process(self):
        """
        OAT: Same mud degassing (CH4-only), GWP AR4 vs AR5.
        AR5 GWP_CH4=28, AR4 GWP_CH4=25 → CO2e ratio = 28/25 = 1.12

        For a CH4-only emission: totalCo2e = ch4_tonnes × GWP_CH4
        AR4 totalCo2e = ch4 × 25
        AR5 totalCo2e = ch4 × 28
        Ratio = 28/25 = 1.12
        """
        gwp_ar5 = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}
        gwp_ar4 = {"CO2": 1.0, "CH4": 25.0, "N2O": 298.0}

        payload = {
            "process_type": "drilling", "quantity": 1000.0, "unit": "m3",
            "factor_source": "specific", "mud_type": "water_based"
        }

        em_ar5, _ = compute_emissions(payload, {}, gwp_dict=gwp_ar5)
        em_ar4, _ = compute_emissions(payload, {}, gwp_dict=gwp_ar4)

        # Same physical CH4 mass
        assert em_ar5["ch4"] == pytest.approx(em_ar4["ch4"], rel=1e-8)

        # Different CO2e (GWP difference)
        assert em_ar5["totalCo2e"] > em_ar4["totalCo2e"]

        # Ratio = 28/25 = 1.12 (since this is pure CH4 process)
        ratio = em_ar5["totalCo2e"] / em_ar4["totalCo2e"]
        assert ratio == pytest.approx(28.0 / 25.0, rel=1e-4), (
            f"AR5/AR4 CO2e ratio: expected {28/25:.4f}, got {ratio:.4f}"
        )

    def test_agr_co2_removal_doubles_with_double_differential(self):
        """
        OAT: AGR, double the CO2 removal (co2_in 4% vs 8%, same co2_out=0%).
        CO2 vented should double exactly (linear: co2_vented = throughput × (co2_in - co2_out)).
        """
        base = {
            "process_type": "agr", "quantity": 10.0, "unit": "mmscf",
            "factor_source": "specific",
            "agr_co2_in": 4.0, "agr_co2_out": 0.0,
            "agr_ch4_in": 85.0, "agr_ch4_slip_pct": 0.0
        }
        em_4pct, _ = compute_emissions(base, {})
        em_8pct, _ = compute_emissions({**base, "agr_co2_in": 8.0}, {})

        assert em_8pct["co2"] == pytest.approx(2 * em_4pct["co2"], rel=1e-3), (
            f"Double CO2 diff: expected {2*em_4pct['co2']:.4f}, got {em_8pct['co2']:.4f}"
        )

    def test_blowdown_pressure_increases_gas_volume(self):
        """
        OAT: Higher pressure → more gas expelled at standard conditions.
        v_std = v_vessel × (p_abs / p_std)
        500 psig: p_factor = 514.696/14.696 = 35.023
        1000 psig: p_factor = 1014.696/14.696 = 69.044

        ratio of CH4 emissions = p_factor_1000 / p_factor_500
        """
        p_500_psig = 500.0
        p_1000_psig = 1000.0

        p_factor_500 = (p_500_psig + STD_PRESS_PSIA) / STD_PRESS_PSIA
        p_factor_1000 = (p_1000_psig + STD_PRESS_PSIA) / STD_PRESS_PSIA
        expected_ratio = p_factor_1000 / p_factor_500

        base = {
            "process_type": "blowdown", "quantity": 5.0, "unit": "m3",
            "factor_source": "specific", "blowdown_volume": 5.0,
            "blowdown_events": 10, "ch4_content": 0.85
        }
        em_500, _ = compute_emissions({**base, "blowdown_pressure": p_500_psig}, {})
        em_1000, _ = compute_emissions({**base, "blowdown_pressure": p_1000_psig}, {})

        assert em_1000["ch4"] > em_500["ch4"], "Higher pressure should yield more CH4"

        actual_ratio = em_1000["ch4"] / em_500["ch4"]
        assert actual_ratio == pytest.approx(expected_ratio, rel=1e-3), (
            f"Pressure scaling:\n"
            f"  p_factor_500={p_factor_500:.4f}, p_factor_1000={p_factor_1000:.4f}\n"
            f"  expected ratio={expected_ratio:.4f}, got={actual_ratio:.4f}"
        )

    def test_flaring_destruction_efficiency_reduces_ch4(self):
        """
        OAT: Higher eta_d → less CH4 undestroyed → less CH4 emitted.
        ch4_undestroyed = vol × c1 × (1 - eta_d)

        eta_d=0.95: ch4_factor = 0.05
        eta_d=0.98: ch4_factor = 0.02
        Ratio = 0.05/0.02 = 2.5 (eta_d=0.95 emits 2.5× more CH4)
        """
        base = {
            "process_type": "flaring", "quantity": 500.0, "unit": "m3",
            "factor_source": "specific", "c1": 0.90, "flare_type": "elevated",
            "hhv": 1020.0,
        }

        # Override destruction efficiency
        em_d95, _ = compute_emissions({**base, "destruction_efficiency": 0.95}, {})
        em_d98, _ = compute_emissions({**base, "destruction_efficiency": 0.98}, {})

        assert em_d95["ch4"] > em_d98["ch4"], (
            f"eta_d=0.95 should produce more CH4 than eta_d=0.98\n"
            f"  eta_d=0.95: {em_d95['ch4']:.6f} t\n"
            f"  eta_d=0.98: {em_d98['ch4']:.6f} t"
        )

        expected_ratio = (1 - 0.95) / (1 - 0.98)   # 0.05 / 0.02 = 2.5
        actual_ratio = em_d95["ch4"] / em_d98["ch4"]
        assert actual_ratio == pytest.approx(expected_ratio, rel=1e-4), (
            f"Destruction efficiency ratio: expected {expected_ratio:.4f}, got {actual_ratio:.4f}"
        )

    def test_completions_ch4_content_linear(self):
        """
        OAT: Increase CH4 content from 0.85 to 0.90 in completions.
        CH4 should scale proportionally: ch4 ∝ ch4_frac.
        ratio = 0.90 / 0.85 = 1.0588...
        """
        base = {
            "process_type": "completions", "quantity": 1000.0, "unit": "m3",
            "factor_source": "specific", "comp_method": "metered_volume",
        }
        em_085, _ = compute_emissions({**base, "ch4_content": 0.85}, {})
        em_090, _ = compute_emissions({**base, "ch4_content": 0.90}, {})

        expected_ratio = 0.90 / 0.85
        actual_ratio = em_090["ch4"] / em_085["ch4"]
        assert actual_ratio == pytest.approx(expected_ratio, rel=1e-4), (
            f"CH4 content ratio: expected {expected_ratio:.4f}, got {actual_ratio:.4f}"
        )

    def test_tank_gor_linear_scaling(self):
        """
        OAT: Double GOR → double gas volume → double CH4.
        total_gas = throughput × GOR → 2×GOR → 2×gas → 2×ch4.
        """
        base = {
            "process_type": "tank", "quantity": 1000.0, "unit": "bbl",
            "factor_source": "specific", "tank_ch4_content": 0.85,
            "tank_control_eff": 0.0
        }
        em_gor100, _ = compute_emissions({**base, "tank_gor": 100.0}, {})
        em_gor200, _ = compute_emissions({**base, "tank_gor": 200.0}, {})

        assert em_gor200["ch4"] == pytest.approx(2 * em_gor100["ch4"], rel=1e-6), (
            f"2× GOR: expected {2*em_gor100['ch4']:.6f}, got {em_gor200['ch4']:.6f}"
        )


# =====================================================================
# TEST CLASS: CO2e Sensitivity
# =====================================================================
class TestCO2eSensitivity:
    """Verify CO2e responds correctly to GWP changes."""

    def test_co2e_increases_with_ch4_gwp(self):
        """
        CO2e = CO2*1 + CH4*GWP_CH4 + N2O*GWP_N2O
        If GWP_CH4 increases, totalCo2e increases (for CH4 > 0).
        """
        # Mud degassing: pure CH4 emission
        em, _ = compute_emissions({
            "process_type": "drilling", "quantity": 100.0, "unit": "m3",
            "factor_source": "specific", "mud_type": "water_based"
        }, {}, gwp_dict={"CO2": 1.0, "CH4": 28.0, "N2O": 265.0})

        ch4_tonnes = em["ch4"]
        # Manual verification
        expected_co2e = ch4_tonnes * 28.0
        assert em["totalCo2e"] == pytest.approx(expected_co2e, rel=1e-6)

    def test_co2e_ar4_less_than_ar5_for_high_ch4(self):
        """
        AR4: CH4=25, AR5: CH4=28 → for CH4-dominant emissions:
        AR5 totalCo2e > AR4 totalCo2e.
        """
        payload = {
            "process_type": "drilling", "quantity": 500.0, "unit": "m3",
            "factor_source": "specific", "mud_type": "water_based"
        }
        em_ar4, _ = compute_emissions(payload, {}, gwp_dict={"CO2": 1.0, "CH4": 25.0, "N2O": 298.0})
        em_ar5, _ = compute_emissions(payload, {}, gwp_dict={"CO2": 1.0, "CH4": 28.0, "N2O": 265.0})
        em_ar6, _ = compute_emissions(payload, {}, gwp_dict={"CO2": 1.0, "CH4": 27.9, "N2O": 273.0})

        assert em_ar5["totalCo2e"] > em_ar4["totalCo2e"]  # 28 > 25
        assert em_ar5["totalCo2e"] > em_ar6["totalCo2e"]  # 28 > 27.9

        # All have same CH4 mass
        assert em_ar4["ch4"] == pytest.approx(em_ar5["ch4"], rel=1e-8)
        assert em_ar4["ch4"] == pytest.approx(em_ar6["ch4"], rel=1e-8)

    def test_co2_process_unaffected_by_gwp_ch4(self):
        """
        For a pure CO2 process, totalCo2e = CO2 × 1.0 regardless of GWP_CH4.
        """
        # Combustion with zero CH4 and N2O EF
        factor_data = {"co2": 2.0, "ch4": 0.0, "n2o": 0.0, "unit": "kg/m3", "hhv": 1020.0}
        payload = {
            "process_type": "combustion", "quantity": 1000.0,
            "unit": "m3", "factor_source": "default"
        }

        em_ar5, _ = compute_emissions(payload, factor_data, gwp_dict={"CO2": 1.0, "CH4": 28.0, "N2O": 265.0})
        em_ar4, _ = compute_emissions(payload, factor_data, gwp_dict={"CO2": 1.0, "CH4": 25.0, "N2O": 298.0})

        # CO2 same regardless of GWP standard
        assert em_ar5["co2"] == pytest.approx(em_ar4["co2"], rel=1e-8)
        # CO2e same (since CH4=0 and N2O=0)
        assert em_ar5["totalCo2e"] == pytest.approx(em_ar4["totalCo2e"], rel=1e-8)
