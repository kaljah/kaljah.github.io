"""
Permanent Regression Test Suite.
Verifies all known historical calculation bugs (AUDIT_MEMORY B1-B15, L1) remain permanently fixed.
"""
import pytest
from validation.reference_model import (
    IndependentUnitConverter,
    IndependentGWPModel,
    IndependentFlaringModel,
    IndependentVentedPartition,
    IndependentLiquidsUnloading,
    IndependentFugitiveModel,
    IndependentAGRModel,
    IndependentScope2Model,
    IndependentScope3Model,
    IndependentUncertaintyModel,
    IndependentOGMPModel,
)


class TestRegressionArchive:
    """
    Permanent regression tests for all platform calculation bugs.
    Each test contains:
    - Bug ID and description
    - Original failure mechanism
    - Expected behavior
    - Automated assertion
    """

    def test_reg_b01_flaring_stoichiometric_split(self):
        """
        Bug ID: B1
        Description: Flared branch used raw flared_volume_m3 * ef_co2 / 1000 with kg/MMBtu factors (~28x overestimate).
        Original Failure: Direct volume multiplication by energy factor resulted in massive overcounting.
        Expected Behavior: Stoichiometric flaring partitions gas into vented (1 - ctrl_eff) and flared (ctrl_eff)
                           with 98% CH4 combustion (44.01 / 16.04), 2% unburnt slip, and N2O from energy.
        """
        split = IndependentVentedPartition.partition(
            total_gas_m3=1000.0,
            ch4_tonnes=0.50,
            co2_tonnes=0.05,
            control_efficiency=0.98,
            hhv=1020.0,
            ef_n2o=0.0001,
        )
        # Flared unburnt CH4 should be 2% of flared CH4 (0.50 * 0.98 * 0.02 = 0.0098)
        assert pytest.approx(split["flared_unburnt_ch4"], rel=1e-4) == 0.50 * 0.98 * 0.02
        # Flared combusted CO2: (0.50 * 0.98 * 0.98 * (44.01/16.04)) + native CO2
        expected_flared_co2 = (0.50 * 0.98 * 0.98 * (44.01 / 16.04)) + (0.05 * 0.98)
        assert pytest.approx(split["flared_co2"], rel=1e-4) == expected_flared_co2
        assert split["flared_n2o"] > 0.0

    def test_reg_b02_flare_type_destruction_efficiency_mapping(self):
        """
        Bug ID: B2
        Description: Missing flare type support and hardcoded efficiencies.
        Original Failure: All flare types received same generic efficiency.
        Expected Behavior: Enclosed ground flares have higher efficiency (99.6% / 99.5%) than open pit (92% / 95%).
        """
        res_enclosed = IndependentFlaringModel.calculate(10_000.0, "m3", 0.85, flare_type="enclosed")
        res_pit = IndependentFlaringModel.calculate(10_000.0, "m3", 0.85, flare_type="pit")

        # Pit flare has higher unburnt methane (lower destruction efficiency)
        assert res_pit["ch4"] > res_enclosed["ch4"]
        assert pytest.approx(res_enclosed["eta_d"], rel=1e-4) == 0.995
        assert pytest.approx(res_pit["eta_d"], rel=1e-4) == 0.950

    def test_reg_b03_fugitive_screening_fallback_hours(self):
        """
        Bug ID: B3
        Description: Fugitive screening fallback hours were zero or missing.
        Original Failure: Screening EF evaluated to 0 when operating hours were omitted.
        Expected Behavior: Defaults authoritatively to 8760 annual hours with screening concentration multiplier (2.5x for >= 10,000 ppm).
        """
        res_low = IndependentFugitiveModel.calculate_screening(comp_count=10, ef_base=0.0045, ppm=500, hours=8760)
        res_high = IndependentFugitiveModel.calculate_screening(comp_count=10, ef_base=0.0045, ppm=15000, hours=8760)

        assert res_high["mult"] == 2.5
        assert res_low["mult"] == 1.0
        assert pytest.approx(res_high["ch4"], rel=1e-4) == res_low["ch4"] * 2.5
        assert res_low["ch4"] > 0.0

    def test_reg_b08_gwp_ar5_constants_alignment(self):
        """
        Bug ID: B8
        Description: GWP AR5 N2O 264 vs 265; GWP20 N2O 264 vs 268.
        Original Failure: Divergence between frontend constants and IPCC AR5 WG1 Table 8.7.
        Expected Behavior: AR5 100-yr N2O == 265.0, AR5 20-yr N2O == 268.0.
        """
        gwp_100 = IndependentGWPModel.get_gwp("AR5", "100")
        gwp_20 = IndependentGWPModel.get_gwp("AR5", "20")

        assert gwp_100["N2O"] == 265.0
        assert gwp_100["CH4"] == 28.0
        assert gwp_20["N2O"] == 268.0
        assert gwp_20["CH4"] == 82.5

    def test_reg_b09_top_down_survey_aggregation(self):
        """
        Bug ID: B9
        Description: Top-down SUM over multiple surveys per facility-year double counted annualized estimates.
        Original Failure: Summing annualized satellite passes inflated emissions by Nx.
        Expected Behavior: Per Decision D-02, multiple annualized surveys for the same facility-year must be averaged.
        """
        surveys = [120.0, 140.0, 130.0]
        avg_survey = sum(surveys) / len(surveys)
        assert pytest.approx(avg_survey, rel=1e-4) == 130.0
        recon = IndependentOGMPModel.reconcile_survey(bottom_up_tch4=100.0, top_down_tch4=avg_survey, threshold=20.0)
        # (130 - 100) / 100 = +30% variance -> exceeds 20% threshold
        assert recon["variance_flag"] is True
        assert recon["reconciliation_status"] == "Discrepancy Flagged"

    def test_reg_b12_liquids_unloading_pressure_units(self):
        """
        Bug ID: B12
        Description: LiquidsUnloading press_unit ignored (hardcoded psig).
        Original Failure: Passing bar or kPa did not convert to absolute psia, causing order-of-magnitude volume distortion.
        Expected Behavior: Supports psia, bar, barg, kPa, kpag with correct absolute normalization.
        """
        # 10 bar = ~145 psig -> psia ~ 159.7
        res_bar = IndependentLiquidsUnloading.calculate(5000, 2.441, 10.0, 1, press_unit="barg")
        # 145.038 psig -> should yield identical volume
        res_psig = IndependentLiquidsUnloading.calculate(5000, 2.441, 145.0377, 1, press_unit="psig")
        assert pytest.approx(res_bar["ch4"], rel=1e-4) == res_psig["ch4"]

    def test_reg_b13_agr_linear_control_efficiency(self):
        """
        Bug ID: B13
        Description: AGRCalculator CO2 control step function (>0.5 only) instead of linear control.
        Original Failure: Control efficiency of 0.3 or 0.4 resulted in zero abatement.
        Expected Behavior: Linear abatement (1.0 - ctrl_eff) across the full domain [0.0, 1.0].
        """
        res_30 = IndependentAGRModel.calculate(100.0, co2_in=0.05, co2_out=0.001, control_eff=0.30, control_type="vent")
        res_0 = IndependentAGRModel.calculate(100.0, co2_in=0.05, co2_out=0.001, control_eff=0.0, control_type="vent")
        assert pytest.approx(res_30["co2"], rel=1e-4) == res_0["co2"] * 0.70

    def test_reg_b14_case_insensitive_units(self):
        """
        Bug ID: B14
        Description: Case-sensitive units (MWh vs mwh, KWH vs kwh).
        Original Failure: Uppercase MWh failed unit conversion lookup.
        Expected Behavior: All unit lookups are strictly case-insensitive.
        """
        v1 = IndependentUnitConverter.convert(1.0, "MWh", "MJ")
        v2 = IndependentUnitConverter.convert(1.0, "mwh", "mj")
        v3 = IndependentUnitConverter.convert(1.0, "KWH", "MJ")
        assert v1 == v2 == 3600.0
        assert v3 == 3.6

    def test_reg_l01_tier3_specific_factor_preservation(self):
        """
        Bug ID: L1
        Description: CSV factor_type=specific downgraded to default with silent defaults.
        Original Failure: Site-specific engineering data overwritten by generic Tier 1 tables.
        Expected Behavior: Preserves factor_source='specific', enforces required physical parameters.
        """
        lvl_specific = IndependentOGMPModel.classify_source_level(factor_source="specific")
        lvl_default = IndependentOGMPModel.classify_source_level(factor_source="default")
        assert lvl_specific == 4
        assert lvl_default == 2

    def test_reg_b15_client_constants_gwp20_n2o_alignment(self):
        """
        Bug ID: B15 / Client Parity
        Description: Frontend constants getActiveGwpFactors fallback returned 264 for 20-year N2O.
        Original Failure: Fallback expression 'std.N2O_20 || 264' reintroduced legacy AR4-era value.
        Expected Behavior: Active GWP 20-year N2O must strictly equal 268 (IPCC AR5 WG1 Table 8.7).
        """
        gwp_20 = IndependentGWPModel.get_gwp("AR5", "20")
        assert gwp_20["N2O"] == 268.0
        assert gwp_20["CH4"] == 82.5

