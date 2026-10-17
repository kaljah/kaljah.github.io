"""calculations/vented_downstream.py: every method of API Compendium 2021 sections 6.11, 6.12 and 6.14 that
tests/test_vented_downstream_compendium.py does not run, with values computed here from the Compendium's
equations (6-34 to 6-56) and exhibits (6-38, 6-42, 6-43). Inputs the Compendium gives no default for are
refused; an entered 0 is a value.
"""
import math

import pytest

from calculations.vented_downstream import (
    AsphaltBlowingCalculator,
    FireSuppressionCalculator,
    PetrochemicalManufacturingCalculator,
    RefiningCatalystRegenCalculator,
    RefiningCokeCalciningCalculator,
    RefiningCokerCalculator,
    RefiningHydrogenPlantCalculator,
    SulfurRecoveryTailGasCalculator,
)

LB_T = 2204.6226218487757
SCF_PER_M3 = 35.3146667


def co2(res):
    r = res["results"]["co2"]
    return r["value"] if isinstance(r, dict) else r


def ch4(res):
    r = res["results"]["ch4"]
    return r["value"] if isinstance(r, dict) else r


def n2o(res):
    r = res["results"]["n2o"]
    return r["value"] if isinstance(r, dict) else r


# ---------------------------------------------------------------- 6.11.1 catalyst regeneration
@pytest.fixture
def regen():
    return RefiningCatalystRegenCalculator()


def test_coke_burn_per_day_and_from_throughput_eq_6_34_6_37(regen):
    per_day = regen.calculate(approach="coke_burn", coke_burn_rate_tonnes_day=328.0, operating_days=350,
                              carbon_content_fraction=1.0)
    assert co2(per_day) == pytest.approx(328.0 * 350 * 44 / 12)
    # Eq 6-37: CC = Q_unit x CBF x 0.001 (default CBF 7.3 kg/bbl for an FCCU)
    thr = regen.calculate(approach="coke_burn", unit_throughput_bbl_day=40_000, carbon_content_fraction=0.93)
    assert co2(thr) == pytest.approx(40_000 * 7.3 * 0.001 * 365 * 0.93 * 44 / 12)
    # Eq 6-38 / 6-39: CH4 and N2O in the ratio of the petroleum coke factors (Table 4-3 / 4-5)
    assert ch4(thr) == pytest.approx(co2(thr) * 3.0e-6 / 0.1021)
    assert n2o(thr) == pytest.approx(co2(thr) * 6.0e-7 / 0.1021)
    # an entered carbon fraction of 0 is 0, not the 0.93 default
    assert co2(regen.calculate(approach="coke_burn", coke_burn_rate_tonnes_yr=1000, carbon_content_fraction=0)) == 0


def test_k1_approach_eq_6_35_exhibit_6_38(regen):
    metric = regen.calculate(approach="k1_k2_k3", flue_gas_rate_dscm_min=2150, co2_pct=11, co_pct=9)
    assert co2(metric) == pytest.approx(411_862, rel=1e-5)                        # Exhibit 6-38, step 2
    imperial = regen.calculate(approach="k1_k2_k3", flue_gas_rate_dscf_min=2150 * SCF_PER_M3, co2_pct=11, co_pct=9)
    assert co2(imperial) == pytest.approx(411_862, rel=2e-3)                      # K1 0.0186 lb vs 0.2982 kg
    half = regen.calculate(approach="k1_k2_k3", flue_gas_rate_dscm_min=2150, co2_pct=11, co_pct=9, operating_hours=4380)
    assert co2(half) == pytest.approx(co2(metric) / 2)


def test_air_blower_eq_6_36(regen):
    m3 = regen.calculate(approach="air_blower", air_rate_m3_min=2150, co2_pct=11, co_pct=9)
    assert co2(m3) == pytest.approx(2150 * 0.20 * 44 / 23.685 * 525_600 / 1000)   # Exhibit 6-38 step 3: 419,859
    scf = regen.calculate(approach="air_blower", air_rate_scf_min=2150 * SCF_PER_M3, co2_pct=11, co_pct=9)
    assert co2(scf) == pytest.approx(co2(m3), rel=1e-3)
    with_o2 = regen.calculate(approach="air_blower", air_rate_m3_min=2000, sor_m3_min=150, co2_pct=11, co_pct=9)
    assert co2(with_o2) == pytest.approx(co2(m3))                                 # AR + SOR
    # concentrations are percent: 0.9 % is 0.009, not 90 %; 0 % is 0, not the 11 % default
    low = regen.calculate(approach="air_blower", air_rate_m3_min=2150, co2_pct=0.9, co_pct=0)
    assert co2(low) == pytest.approx(2150 * 0.009 * 44 / 23.685 * 525_600 / 1000)


def test_continuous_and_intermittent_eq_6_40_6_41(regen):
    cont = regen.calculate(approach="continuous", catalyst_circulation_rate_tonnes_hr=10, operating_hours=8280,
                           fc_spent=0.04, fc_regen=0.005)
    assert co2(cont) == pytest.approx(10 * 8280 * 0.035 * 44 / 12)
    inter = regen.calculate(approach="intermittent", catalyst_inventory_tonnes=1000, regeneration_cycles_per_yr=0,
                            fc_spent=0.07)
    assert co2(inter) == 0                                                         # 0 regenerations, not 1


def test_supplemental_firing_exhibit_6_38(regen):
    res = regen.calculate(approach="continuous", catalyst_circulation_rate_tonnes_hr=0, supplemental_fuel_mmbtu_hr=100)
    assert res["inputs"]["supplemental_co2"] == pytest.approx(46_516, rel=1e-4)
    assert res["inputs"]["supplemental_ch4"] == pytest.approx(0.876, rel=1e-3)    # printed 0.88
    assert res["inputs"]["supplemental_n2o"] == pytest.approx(0.858, rel=1e-3)    # printed 0.86


@pytest.mark.parametrize("kwargs,match", [
    (dict(approach="coke_burn"), "coke burn rate"),
    (dict(approach="k1_k2_k3"), "flue gas rate"),
    (dict(approach="air_blower"), "air rate"),
    (dict(approach="fcc"), "Unknown catalyst regeneration approach"),
])
def test_regeneration_refusals(regen, kwargs, match):
    with pytest.raises(ValueError, match=match):
        regen.calculate(**kwargs)


# ---------------------------------------------------------------- 6.11.2 cokers
def _dcu_steam(d, h_drum, h_out, h_water, t_initial, f_loss=0.10, t_final=212.0):
    """Equations 6-43, 6-44 and 6-47 with the Compendium defaults."""
    area = math.pi * d ** 2 / 4
    m_coke = 0.0191 * (h_drum - h_out) * area
    m_water = 0.0270 * (h_water * area - m_coke / 0.0382)
    return (1 - f_loss) * (m_water * 2205 + m_coke * 584) * (t_initial - t_final) / 2_116_000


@pytest.fixture
def coker():
    return RefiningCokerCalculator()


def test_dcu_steam_from_vessel_and_pressure_eq_6_42_to_6_47(coker):
    res = coker.calculate(vessel_diameter_ft=20, vessel_height_ft=80, coke_drum_outage_ft=10, water_height_ft=70,
                          p_overhead_psig=10, num_cycles_per_yr=300)
    t_init = -0.039 * 10 ** 2 + 3.13 * 10 + 220                                   # Eq 6-46: 247.4 F
    steam = _dcu_steam(20, 80, 10, 70, t_init)
    assert res["inputs"]["steam_mass_per_cycle_tonnes"] == pytest.approx(steam)
    assert ch4(res) == pytest.approx(steam * 7.9 * 300 * 0.001)                   # Eq 6-42
    assert co2(res) == 0                                                           # delayed cokers: no process CO2


def test_dcu_temperatures_eq_6_45_with_floors(coker):
    res = coker.calculate(vessel_diameter_ft=20, vessel_height_ft=80, water_height_ft=60, t_overhead_f=200,
                          t_bottom_f=205, num_cycles_per_yr=1, f_conv_loss=0)
    # overhead below 216 F counts as 216, bottom below 212 F as 212: T_initial 214 F
    assert res["inputs"]["steam_mass_per_cycle_tonnes"] == pytest.approx(_dcu_steam(20, 80, 0, 60, 214.0, f_loss=0.0))
    hot = coker.calculate(vessel_diameter_ft=20, vessel_height_ft=80, water_height_ft=60, t_overhead_f=300,
                          t_bottom_f=260, t_final_f=212)
    assert hot["inputs"]["steam_mass_per_cycle_tonnes"] == pytest.approx(_dcu_steam(20, 80, 0, 60, 280.0))


def test_dcu_zero_cycles_and_factor_are_zero(coker):
    assert ch4(coker.calculate(steam_mass_tonnes_cycle=10, num_cycles_per_yr=0)) == 0
    assert ch4(coker.calculate(steam_mass_tonnes_cycle=10, dcu_ch4_ef_kg_tonne_steam=0)) == 0


def test_fluid_coker_tonnes_and_carbon_fraction(coker):
    res = coker.calculate(coker_type="fluid", coke_burned_tonnes_yr=63_503, hydrogen_wt_fraction=0.015)
    assert co2(res) == pytest.approx(63_503 * 0.985 * 44 / 12)
    assert co2(coker.calculate(coker_type="fluid", coke_burned_tonnes_yr=100, carbon_wt_fraction=0.9)) == pytest.approx(
        100 * 0.9 * 44 / 12)
    assert co2(coker.calculate(coker_type="fluid", coke_burned_tonnes_yr=100, hydrogen_wt_fraction=0)) == pytest.approx(
        100 * 44 / 12)                                                             # 0 % H2 is 0, not 1.5 %
    assert co2(coker.calculate(coker_type="fluid", coke_burned_tonnes_yr=0)) == 0


@pytest.mark.parametrize("kwargs,match", [
    (dict(vessel_diameter_ft=20, vessel_height_ft=80, p_overhead_psig=5), "water height"),
    (dict(vessel_diameter_ft=20, vessel_height_ft=80, water_height_ft=60), "overhead pressure"),
    (dict(vessel_diameter_ft=20, vessel_height_ft=80, water_height_ft=60, t_overhead_f=250), "overhead pressure"),
    (dict(), "steam per cycle"),
    (dict(coker_type="fluid"), "coke burned"),
    (dict(coker_type="flexi"), "Unknown coker type"),
])
def test_coker_refusals(coker, kwargs, match):
    with pytest.raises(ValueError, match=match):
        coker.calculate(**kwargs)


# ---------------------------------------------------------------- 6.11.3 hydrogen plants
EXHIBIT_FEED = {"CH4": 0.85, "C2H6": 0.08, "C4H10": 0.03, "N2": 0.04}


@pytest.fixture
def h2():
    return RefiningHydrogenPlantCalculator()


def test_feedstock_balance_in_m3_and_tonnes_eq_6_49(h2):
    scf = h2.calculate(method="feedstock_balance", feedstock_volume_scf_yr=5e9, feedstock_comp=EXHIBIT_FEED)
    m3 = h2.calculate(method="feedstock_balance", feedstock_volume_m3_yr=5e9 / SCF_PER_M3, feedstock_comp=EXHIBIT_FEED)
    assert co2(m3) == pytest.approx(co2(scf), rel=2e-3) and co2(scf) == pytest.approx(297_100, rel=5e-3)  # Exhibit 6-42
    t = h2.calculate(method="feedstock_balance", feedstock_rate_tonnes_yr=100_000, feedstock_carbon_fraction=0.7185)
    assert co2(t) == pytest.approx(100_000 * 0.7185 * 44 / 12)
    # tonnes given with the composition: the composition supplies the carbon fraction
    mw = 0.85 * 16.04 + 0.08 * 30.07 + 0.03 * 58.12 + 0.04 * 28.01
    cf = (0.85 + 0.08 * 2 + 0.03 * 4) * 12.011 / mw
    tc = h2.calculate(method="feedstock_balance", feedstock_rate_tonnes_yr=100_000, feedstock_comp=EXHIBIT_FEED)
    assert co2(tc) == pytest.approx(100_000 * cf * 44 / 12)


def test_h2_stoichiometry_from_composition_exhibit_6_43(h2):
    res = h2.calculate(method="h2_stoichiometry", h2_production_scf_yr=13e9, feedstock_comp=EXHIBIT_FEED)
    ratio = (0.85 + 0.16 + 0.12) / (0.85 * 4 + 0.08 * 7 + 0.03 * 13)               # 1.13 / 4.35 (Eq 6-48)
    assert co2(res) == pytest.approx(13e9 / 379.3 * ratio * 44 / LB_T)
    assert co2(res) == pytest.approx(177_800, rel=5e-3)                             # the exhibit rounds the ratio to 0.26
    m3 = h2.calculate(method="h2_stoichiometry", h2_production_m3_yr=13e9 / SCF_PER_M3, co2_to_h2_molar_ratio=0.26)
    assert co2(m3) == pytest.approx(13e9 / 379.3 * 0.26 * 44 / LB_T, rel=2e-3)
    zero = h2.calculate(method="h2_stoichiometry", h2_production_scf_yr=1e6, co2_to_h2_molar_ratio=0)
    assert co2(zero) == 0


@pytest.mark.parametrize("basis,qty,factor", [
    ("feedstock_scf", 1e6, 54.42), ("feedstock_m3", 1e6, 1922.0), ("h2_scf", 1e6, 13.41), ("h2_m3", 1e6, 473.6),
])
def test_table_6_51_bases(h2, basis, qty, factor):
    assert co2(h2.calculate(method="simple_factor", simple_basis=basis, simple_volume=qty)) == pytest.approx(factor)


@pytest.mark.parametrize("kwargs,match", [
    (dict(method="smr"), "Unknown hydrogen plant method"),
    (dict(method="feedstock_balance", feedstock_volume_scf_yr=1e6, feedstock_comp={"CH4": 0.9, "iC4H10": 0.1}),
     "Unknown feed gas species"),
    (dict(method="feedstock_balance", feedstock_volume_scf_yr=1e6), "feedstock rate"),
    (dict(method="feedstock_balance", feedstock_rate_tonnes_yr=10), "feedstock rate"),
    (dict(method="feedstock_balance", feedstock_comp=EXHIBIT_FEED), "feedstock rate"),
    (dict(method="h2_stoichiometry", h2_production_scf_yr=1e6), "molar ratio or the feed composition"),
    (dict(method="h2_stoichiometry", h2_production_scf_yr=1e6, feedstock_comp={"N2": 0.5, "CO2": 0.5}),
     "no hydrocarbon"),
    (dict(method="h2_stoichiometry", co2_to_h2_molar_ratio=0.26), "hydrogen produced"),
    (dict(method="simple_factor", simple_basis="h2_tonnes", simple_volume=1), "Unknown Table 6-51 basis"),
])
def test_hydrogen_refusals(h2, kwargs, match):
    with pytest.raises(ValueError, match=match):
        h2.calculate(**kwargs)


def test_dispatcher_reads_the_feed_analysis_as_mol_percent():
    """0.5 mol % butane was read as 50 % (a value of 1 or less was taken as a fraction)."""
    from calculations.dispatcher import CalculationDispatcher

    d = CalculationDispatcher()
    pct = d.dispatch("hydrogen_plant", {"feed_ch4": 95, "feed_c4h10": 0.5, "feed_n2": 4.5, "feedstock_scf": 1e9}, {}, {})
    mw = 0.95 * 16.04 + 0.005 * 58.12 + 0.045 * 28.01
    cf = (0.95 + 0.005 * 4) * 12.011 / mw
    expected = 1e9 / 379.3 * mw * cf * 44 / 12 / LB_T
    total = pct["results"]["co2"]
    assert (total["value"] if isinstance(total, dict) else total) == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------- 6.11.4 asphalt blowing
@pytest.mark.parametrize("unit,key", [("bbl", "bbl"), ("barrels", "bbl"), ("m3", "m3"), ("tonne", "tonne"),
                                      ("metric_ton", "tonne"), ("short tons", "short_ton"), ("US_TON", "short_ton")])
def test_asphalt_units_table_6_52(unit, key):
    t = AsphaltBlowingCalculator.TABLE_6_52[key]
    res = AsphaltBlowingCalculator().calculate(throughput=1000, unit=unit)
    assert ch4(res) == pytest.approx(1000 * t["ch4"]) and co2(res) == pytest.approx(1000 * t["co2"])


def test_asphalt_controlled_eq_6_51_6_52_and_unit_refusal():
    res = AsphaltBlowingCalculator().calculate(throughput=1000, unit="bbl", controlled=True, destruction_efficiency=95)
    assert ch4(res) == pytest.approx(1000 * 5.55e-4 * 0.05)
    assert co2(res) == pytest.approx(1000 * 1.01e-3 + 1000 * 5.55e-4 * 0.95 * 44 / 16)
    with pytest.raises(ValueError, match="must be bbl, m3, short_ton or tonne"):
        AsphaltBlowingCalculator().calculate(throughput=1, unit="ton")


# ---------------------------------------------------------------- 6.11.5 coke calcining, 6.11.6 SRU / blowdowns
def test_coke_calcining_dust_recycle_and_required_carbon_contents():
    c = RefiningCokeCalciningCalculator()
    res = c.calculate(green_coke_mass_tonnes_yr=100_000, green_coke_carbon_fraction=0.88, calcined_coke_mass_tonnes_yr=80_000,
                      calcined_coke_carbon_fraction=0.98, dust_collected_tonnes_yr=3000, dust_recycled_tonnes_yr=1000)
    assert co2(res) == pytest.approx((100_000 * 0.88 - (80_000 + 2000) * 0.98) * 44 / 12)    # Eq 6-53
    with pytest.raises(ValueError, match="carbon fractions"):
        c.calculate(green_coke_mass_tonnes_yr=100_000, calcined_coke_mass_tonnes_yr=80_000)
    over = c.calculate(green_coke_mass_tonnes_yr=10, green_coke_carbon_fraction=0.5, calcined_coke_mass_tonnes_yr=10,
                       calcined_coke_carbon_fraction=0.9)
    assert co2(over) == 0                                                                     # never negative


def test_sru_metric_zero_fraction_and_refinery_blowdowns():
    s = SulfurRecoveryTailGasCalculator()
    assert co2(s.calculate(sour_gas_m3_yr=1e6)) == pytest.approx(1e6 * 44 / 23.685 * 0.20 / 1000)   # Eq 6-54, FC 0.20
    assert co2(s.calculate(sour_gas_scf_yr=1e6, carbon_mole_fraction=0)) == 0
    blow = s.calculate(refinery_throughput_bbl_yr=36.5e6)                                     # 137,000 scf CH4 / MMbbl
    assert ch4(blow) == pytest.approx(36.5 * 137_000 / 379.3 * 16.04 / LB_T, rel=1e-3)


# ---------------------------------------------------------------- 6.12 petrochemicals
def test_petrochemical_material_balance_eq_6_55():
    res = PetrochemicalManufacturingCalculator().calculate(
        feedstocks=[(1000, 0.80), (200, 0.75)], primary_product_tonnes=900, primary_product_c_frac=0.857,
        secondary_products=[(50, 0.80)])
    c = 1000 * 0.80 + 200 * 0.75 - (900 * 0.857 + 50 * 0.80)
    assert co2(res) == pytest.approx(c * 44 / 12)
    nothing = PetrochemicalManufacturingCalculator().calculate(feedstocks=[(10, 0.5)], primary_product_tonnes=10)
    assert co2(nothing) == pytest.approx(5 * 44 / 12)


@pytest.mark.parametrize("name,key", [("Adipic Acid Thermal", "adipic_acid_thermal"), ("methanol", "methanol"),
                                      ("ethylene-oxide-abated", "ethylene_oxide_abated")])
def test_petrochemical_names(name, key):
    t = PetrochemicalManufacturingCalculator.TABLE_6_53[key]
    res = PetrochemicalManufacturingCalculator().calculate(process_type=name, production_tonnes=100)
    assert (co2(res), ch4(res), n2o(res)) == pytest.approx((100 * t["co2"], 100 * t["ch4"], 100 * t["n2o"]))


@pytest.mark.parametrize("name", ["ethylene", "nitric", "polyethylene"])
def test_petrochemical_partial_names_are_refused(name):
    with pytest.raises(ValueError, match="Unknown Table 6-53 process"):
        PetrochemicalManufacturingCalculator().calculate(process_type=name, production_tonnes=100)


def test_petrochemical_without_inputs_is_zero():
    assert co2(PetrochemicalManufacturingCalculator().calculate()) == 0


# ---------------------------------------------------------------- 6.14 fire suppression
def test_fire_suppression_co2_agent_and_discharge_only():
    f = FireSuppressionCalculator()
    res = f.calculate(agent_type="CO2", total_charge_kg=1000, annual_release_rate=0.05, direct_discharge_kg=450)
    assert co2(res) == pytest.approx(0.5) and res["total_co2e"] == pytest.approx(0.5)
    halon = f.calculate(agent_type="halon-1301", direct_discharge_kg=10)
    assert halon["total_co2e"] == pytest.approx(10 / 1000 * 7140)


@pytest.mark.parametrize("kwargs,match", [
    (dict(agent_type="HFC-134a", direct_discharge_kg=1), "Unknown fire suppression agent"),
    (dict(agent_type="hfc_125", total_charge_kg=100), "fraction of the charge released"),
])
def test_fire_suppression_refusals(kwargs, match):
    with pytest.raises(ValueError, match=match):
        FireSuppressionCalculator().calculate(**kwargs)
