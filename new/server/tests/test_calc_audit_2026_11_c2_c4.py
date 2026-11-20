"""Regression tests for the clean-room calculation audit of November 2026, batches C2-C4 (upstream venting,
midstream / downstream, fugitives). Finding IDs refer to CALC_AUDIT_2026-11/REPORT.md. Expected values are
worked by hand from the inputs and the cited API Compendium 2021 table or equation, never read from the engine.
"""
import pytest

from app import app
from calculations.dispatcher import CalculationDispatcher

GWP = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}
LB_PER_T = 2204.62262
T_CH4_PER_SCF = 16.04 / 379.3 / LB_PER_T   # tonnes of CH4 per scf of pure CH4 (engine MW, Compendium 379.3)
CO2_PER_CH4 = 44.01 / 16.04


@pytest.fixture
def ctx():
    with app.app_context():
        yield


def _disp(process, inputs):
    return CalculationDispatcher().dispatch(process, dict(inputs), {}, {}, gwp_dict=GWP)["results"]


def _v(results, gas):
    r = results.get(gas)
    return float(r.get("value", 0.0)) if isinstance(r, dict) else float(r or 0.0)


# ---------------------------------------------------------------- C2 upstream venting
def test_f_vent1_02_produced_water_row_follows_pressure_and_salt():
    from calculations.vented_production_tank import TankFlashingCalculator as TankCalculator

    t = TankCalculator()
    hi = t.calculate(throughput=18250, method="produced_water", separator_pressure_psig=1000)
    assert _v(hi["results"], "ch4") == pytest.approx(18.25 * 0.0508, rel=1e-9)   # Table 6-26, 1,000 psi average
    lo = t.calculate(throughput=18250, method="produced_water", separator_pressure_psig=50, salt_content="20%")
    assert _v(lo["results"], "ch4") == pytest.approx(18.25 * 0.0015, rel=1e-9)    # 50 psi, 20 % salt
    with pytest.raises(ValueError, match="only 20 % salt"):
        t.calculate(throughput=18250, method="produced_water", separator_pressure_psig=50)
    with pytest.raises(ValueError, match="separator pressure"):
        t.calculate(throughput=18250, method="produced_water")


def test_f_vent1_07_small_condensate_tank_row():
    from calculations.vented_production_tank import TankFlashingCalculator as TankCalculator

    res = TankCalculator().calculate(throughput=1000, method="table_6_24", liquid_type="condensate", tank_size="small")
    assert _v(res["results"], "ch4") == pytest.approx(1000 * 0.119 / 1000, rel=1e-9)   # Table 6-24 small, 0.119 kg/bbl


def test_f_vent1_03_completion_efficiency_without_disposition_is_the_flares():
    from calculations.vented_completion import CompletionFlowbackCalculator

    res = CompletionFlowbackCalculator().calculate(tier="tier3", flowback_volume=1_472_610, volume_unit="scf",
                                                   ch4_content=70, control_efficiency=98)
    # Exhibit 6-3 gas: all of it to a 98 % flare (it was read as 98 % of the gas sent to a flare)
    assert _v(res["results"], "ch4") == pytest.approx(1_472_610 * 0.70 * T_CH4_PER_SCF * 0.02, rel=2e-3)


def test_f_vent1_04_drilling_reads_ch4_and_co2_content():
    res = _disp("drilling", {"factor_source": "specific", "amount": 30, "unit": "days", "mud_type": "water_based",
                             "ch4_content": 70, "co2_content": 9})
    ch4 = 30 * 0.0458 * 0.70 / 0.8385     # Table 6-2 onshore WBM, scaled to the site CH4 (Exhibit 6-1)
    assert _v(res, "ch4") == pytest.approx(ch4, rel=1e-6)
    assert _v(res, "co2") == pytest.approx(ch4 * 9 / 70 * CO2_PER_CH4, rel=1e-6)


def test_f_vent1_10_unknown_basin_is_refused():
    from calculations.vented_associated_gas import AssociatedGasVentingCalculator as A

    with pytest.raises(ValueError, match="Table 6-8"):
        A.resolve_basin_factor("Hassi Messaoud")
    assert A.resolve_basin_factor("Associated Gas Venting - US Average") is A.TABLE_6_8_FACTORS["us_average"]


def test_f_vent1_12_table_6_13_and_6_17_rows():
    from calculations.activity_factors import ACTIVITY_FACTORS

    assert ACTIVITY_FACTORS["cg_well_active"]["ch4"] == 0.0205
    assert ACTIVITY_FACTORS["cg_well_suspended"]["ch4"] == 0.0111
    assert ACTIVITY_FACTORS["dh_glycol_per_unit"]["ch4"] == 0.06149


def test_f_gstd_02_current_table_w1_offered_and_labelled():
    from calculations.vented_production_pneumatic import PneumaticDeviceCalculator as P

    p = P()
    assert p._table_rate("high_bleed", "subpart_w_2024_production") == 21.0      # 40 CFR 98 Table W-1 (2024)
    assert p._table_rate("intermittent_average", "subpart_w_2024_transmission") == 2.3
    assert p._table_rate("high_bleed", "subpart_w") == 37.3                        # pre-2024 W-1A, kept, relabelled
    assert "before the 2024 amendments" in P.STANDARD_LABELS["subpart_w"]


def test_f_gui2_02_equation_6_13_reaches_the_calculator():
    res = _disp("pneumatic", {"factor_source": "specific", "pneu_count": 2, "id_pipe_inches": 0.5,
                              "length_pipe_ft": 10, "delta_vol_bonnet_scf": 0.1, "p_control_psig": 30,
                              "actuations_per_year": 1000, "pneu_ch4_content": 81.6, "year": 2024})
    import math
    v_act = math.pi / 4 * (0.5 / 12) ** 2 * 10 + 0.1
    scf = 2 * v_act * (30 + 14.7) / 14.696 * 1000     # Eq 6-13
    assert _v(res, "ch4") == pytest.approx(scf * 0.816 * T_CH4_PER_SCF, rel=2e-3)


def test_f_upl_14_vapour_recovery_has_no_combustion_co2():
    from calculations.vented_production_tank import TankFlashingCalculator as TankCalculator

    t = TankCalculator()
    vru = t.calculate(throughput=1000, method="table_6_22", tank_size="large", control_efficiency=0.95, control_type="vru")
    flare = t.calculate(throughput=1000, method="table_6_22", tank_size="large", control_efficiency=0.95)
    assert _v(vru["results"], "co2") < _v(flare["results"], "co2")
    assert _v(vru["results"], "ch4") == pytest.approx(1000 * 0.193 / 1000 * 0.05, rel=1e-6)


def test_f_grest_06_flashing_row_refused_for_working_losses(ctx):
    from services.scope1_calc import resolve_factor
    from input_validation import ValidationError

    with pytest.raises(ValidationError, match="flashing-loss factor"):
        resolve_factor({"process_type": "tank_working", "fuel": "Tank - Crude Oil (Large, >10 bbl/d)",
                        "factor_source": "default", "amount": 10000, "unit": "bbl"})


# ---------------------------------------------------------------- C3 midstream / downstream
def test_f_vent2_01_record_amount_is_the_pipeline_length():
    res = _disp("transmission_non_routine", {"factor_source": "specific", "activity": "pipeline_blowdown",
                                             "amount": 50, "unit": "miles", "year": 2023})
    assert _v(res, "ch4") == pytest.approx(50 * 0.6135, rel=1e-3)   # Table 6-43 / Exhibit 6-33, per mile-year


def test_f_vent2_10_gathering_prv_scaled_to_the_month():
    res = _disp("gathering_non_routine", {"factor_source": "specific", "activity": "prv_releases", "amount": 6,
                                          "year": 2023, "month": 1})
    assert _v(res, "ch4") == pytest.approx(6 * 0.00065 * 31 / 365, rel=2e-3)   # Table 6-33, per PRV-year


def test_f_vent2_04_zero_hours_is_zero():
    from calculations.vented_midstream import TransmissionCompressorCalculator

    res = TransmissionCompressorCalculator().calculate(compressor_type="centrifugal", wet_seal_count=1,
                                                       operating_hours=0, ch4_content=95)
    assert _v(res["results"], "ch4") == 0.0


def test_f_vent2_03_and_09_catalyst_regeneration_inputs():
    from calculations.vented_downstream import RefiningCatalystRegenCalculator

    r = RefiningCatalystRegenCalculator()
    res = r.calculate(approach="coke_burn", coke_burn_rate_tonnes_yr=119_750)
    assert res["inputs"]["coke_burn_co2"] == pytest.approx(119_750 * 1.0 * 44.01 / 12.011, rel=1e-9)  # CF 1.0
    with pytest.raises(ValueError, match="CO2 % and CO %"):
        r.calculate(approach="k1_k2_k3", flue_gas_rate_dscm_min=2150)
    with pytest.raises(ValueError, match="more carbon"):
        r.calculate(approach="continuous", catalyst_circulation_rate_tonnes_hr=10, fc_spent=0.01, fc_regen=0.02)


def test_f_vent2_07_feed_volume_needs_molecular_weight():
    from calculations.vented_downstream import RefiningHydrogenPlantCalculator as HydrogenProductionCalculator

    with pytest.raises(ValueError, match="molecular weight"):
        HydrogenProductionCalculator().calculate(method="feedstock_balance", feedstock_volume_scf_yr=5e9,
                                                 feedstock_carbon_fraction=0.7185)


def test_f_vent2_09_negative_displacement_refused():
    from calculations.vented_midstream import ProcessingBlanketedTankCalculator

    with pytest.raises(ValueError, match="cannot be negative"):
        ProcessingBlanketedTankCalculator().calculate(liquid_displacement_bbl=-10, vapor_temperature_f=75, ch4_content=80)


def test_f_vent2_11_lng_needs_an_expansion_ratio():
    from calculations.vented_lng_distribution import LNGVentingCalculator

    with pytest.raises(ValueError, match="expansion ratio"):
        LNGVentingCalculator().calculate(transfer_volume_m3=1000, pipe_length_km=1)
    a = LNGVentingCalculator().calculate(transfer_volume_m3=1000, pipe_length_km=1, expansion_ratio=600)
    b = LNGVentingCalculator().calculate(transfer_volume_m3=1000, pipe_length_km=1, expansion_ratio=300)
    assert _v(a["results"], "ch4") == pytest.approx(2 * _v(b["results"], "ch4"), rel=1e-9)


def test_f_vent2_13_co2_share_is_percent():
    from calculations.vented_ccus_transport import CCUSVentingCalculator

    c = CCUSVentingCalculator()
    half = c.calculate(activity="wellhead_blowdown", physical_volume_m3=100, co2_density_kg_m3=800,
                       co2_weight_fraction=0.5)
    assert _v(half["results"], "co2") == pytest.approx(100 * 800 * 0.005 / 1000, rel=1e-9)   # 0.5 % (was 50 %)


def test_f_vent2_08_loading_flare_ce_and_carbon():
    from calculations.vented_ccus_transport import CrudeTransportLossesCalculator as C

    with pytest.raises(ValueError, match="toc_carbon_wt_pct"):
        C().calculate(activity="loading", volume_loaded_bbl=1e5, control_efficiency=98, control_type="flare")


def test_f_vent2_16_vented_gas_flare_n2o_is_eq_5_6():
    from calculations.vented_gas import VentedGasCalculator

    res = VentedGasCalculator().calculate("volume", {"gas_volume": 1, "gas_volume_unit": "MMscf", "ch4_content": 90,
                                                     "disposition": "flared"})
    native = 0.0
    comb_co2 = _v(res["results"], "co2") - native
    assert _v(res["results"], "n2o") == pytest.approx(comb_co2 * 1e-4 / 60, rel=1e-9)


# ---------------------------------------------------------------- C4 fugitives
def test_f_fug_03_facility_leak_co2_from_the_ratio():
    from calculations.fugitive_onshore import OnshoreFacilityFugitiveCalculator as F

    res = F().calculate(production=1000, production_unit="MMscf", facility_type="gas_production", ch4_content=0.85,
                        co2_content=0.02)
    ch4 = 1000 * 2.601e-2 * 0.85 / 0.788       # Table 7-8, scaled to the site CH4
    assert _v(res["results"], "ch4") == pytest.approx(ch4, rel=1e-9)
    assert _v(res["results"], "co2") == pytest.approx(ch4 * 0.02 / 0.85 * CO2_PER_CH4, rel=1e-9)   # ~1.81 t


def test_f_fug_04_oil_row_scales_to_the_site_ch4():
    from calculations.fugitive_onshore import OnshoreFacilityFugitiveCalculator as F

    res = F().calculate(production=1e6, production_unit="bbl", facility_type="oil_production", ch4_content=0.60)
    assert _v(res["results"], "ch4") == pytest.approx(1e6 * 2.346e-4 * 0.60 / 0.788, rel=1e-9)   # 178.6 t


def test_f_fug_08_method21_ch4_share_is_percent():
    from calculations.fugitive_onshore import OnshoreScreeningMeasurementCalculator as S

    res = S().calculate_method21_ranges(component_type="valve", service_type="gas", non_pegged_count=90,
                                        pegged_count=10, operating_hours=8760, ch4_content=1)
    assert _v(res["results"], "ch4") == pytest.approx((10 * 0.098 + 90 * 2.5e-5) * 0.01 * 8760 / 1000, rel=1e-6)
