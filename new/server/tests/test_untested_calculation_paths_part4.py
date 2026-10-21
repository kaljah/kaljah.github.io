"""
Comprehensive Test Suite Part 4 for Untested Calculation Paths & Invariants
Focus: CCUS, Crude Transport, LNG Distribution, Downstream Refining, Petrochemicals,
Fire Suppression, Stoichiometry, Mud Degassing, Well Testing & Advanced Uncertainty.
Governing Standards: API Compendium 2021 4th Edition (Chapters 4, 6) & IPCC 2006 GL.
"""

import math
import pytest
import re

from calculations.base import BaseCalculator
from calculations.units import convert, calculate_co2e, UnitError
from calculations.uncertainty import (
    Tier,
    propagate_uncertainty,
    propagate_co2e_uncertainty,
    combine_uncertainties_product,
    combine_uncertainties_sum,
    srss_inventory,
    monte_carlo_simulation,
    resolve_tier,
    resolve_ef_uncertainty,
)
from calculations.stoichiometry import (
    mass_to_kg,
    StoichiometricCalculator,
    NitricAcidCalculator,
)
from calculations.vented_ccus_transport import (
    CCUSVentingCalculator,
    CrudeTransportLossesCalculator,
)
from calculations.vented_lng_distribution import (
    LNGVentingCalculator,
    DistributionPneumaticsCalculator,
    DistributionNonRoutineCalculator,
)
from calculations.vented_downstream import (
    RefiningCatalystRegenCalculator,
    RefiningCokerCalculator,
    RefiningHydrogenPlantCalculator,
    AsphaltBlowingCalculator,
    RefiningCokeCalciningCalculator,
    SulfurRecoveryTailGasCalculator,
    PetrochemicalManufacturingCalculator,
    FireSuppressionCalculator,
    FIRE_AGENT_GWPS,
)
from calculations.vented_mud import MudDegassingCalculator
from calculations.vented_exploration import (
    WellTestingCalculator,
    CoalSeamDrillingCalculator,
)


def test_ccus_venting_and_crude_transport_thorough():
    ccus = CCUSVentingCalculator()

    # 1. Stripper off-gas mass balance with inlet CO2 & capture efficiency
    res_stripper = ccus.calculate(
        activity="stripper_vent",
        inlet_co2_tonnes=1000.0,
        capture_efficiency=90.0,  # 90% capture rate -> 10% vented = 100 t CO2
        ch4_slip_tonnes=2.5,
    )
    assert res_stripper["results"]["co2"]["value"] == pytest.approx(100.0)
    assert res_stripper["results"]["ch4"]["value"] == pytest.approx(2.5)
    assert res_stripper["total_co2e"] > 100.0

    # Stripper off-gas with direct measured vented quantities
    res_stripper_direct = ccus.calculate(
        activity="stripper_vent",
        vented_co2_tonnes=75.0,
        vented_ch4_tonnes=1.2,
    )
    assert res_stripper_direct["results"]["co2"]["value"] == pytest.approx(75.0)
    assert res_stripper_direct["results"]["ch4"]["value"] == pytest.approx(1.2)

    # 2. Supercritical CO2 injection wellhead blowdown (Eq 6-27)
    # E = N * V * rho * wt_frac * 0.001
    # 2 events * 50 m3 * 1.85 kg/m3 * 95% * 0.001 = 0.17575 t CO2
    res_blowdown = ccus.calculate(
        activity="wellhead_blowdown",
        events=2.0,
        physical_volume_m3=50.0,
        co2_density_kg_m3=1.85,
        co2_weight_fraction=95.0,
    )
    expected_co2 = 2.0 * 50.0 * 1.85 * 0.95 * 0.001
    assert res_blowdown["results"]["co2"]["value"] == pytest.approx(expected_co2)

    # 3. Monitoring vent releases
    res_mon = ccus.calculate(activity="monitoring_vent", vented_co2_tonnes=12.5, vented_ch4_tonnes=0.5)
    assert res_mon["results"]["co2"]["value"] == pytest.approx(12.5)
    assert res_mon["results"]["ch4"]["value"] == pytest.approx(0.5)

    # CCUS Validations
    with pytest.raises(ValueError, match="Unknown CCUS activity"):
        ccus.calculate(activity="unsupported_act")
    with pytest.raises(ValueError, match="stripper vent mass balance needs the capture efficiency"):
        ccus.calculate(activity="stripper_vent", inlet_co2_tonnes=500.0)
    with pytest.raises(ValueError, match="inlet_co2_tonnes or vented_co2_tonnes must be provided"):
        ccus.calculate(activity="stripper_vent")

    # 4. CrudeTransportLossesCalculator: Loading losses
    crude = CrudeTransportLossesCalculator()
    for service in crude.TABLE_6_47_LOADING:
        res_load = crude.calculate(
            activity="loading",
            loading_service=service,
            volume_loaded_bbl=10000.0,
            ch4_weight_pct=15.0,
        )
        assert res_load["results"]["ch4"]["value"] > 0
        assert res_load["total_co2e"] > 0

    # Volume loaded in gal
    res_load_gal = crude.calculate(
        activity="loading",
        loading_service="splash_dedicated",
        volume_loaded_gal=420000.0,  # 10,000 bbl
        ch4_weight_pct=15.0,
    )
    assert res_load_gal["results"]["ch4"]["value"] > 0

    # 5. Ballasting losses
    for bcond in crude.TABLE_6_48_BALLASTING:
        res_ballast = crude.calculate(
            activity="ballasting",
            ballast_condition=bcond,
            ballast_water_bbl=5000.0,
        )
        assert res_ballast["results"]["ch4"]["value"] > 0

    # 6. Marine Transit losses (Eq 6-37)
    res_transit = crude.calculate(
        activity="transit",
        volume_transported_bbl=50000.0,
        trip_duration_days=14.0,
        trips_per_year=12.0,
        control_efficiency=0.90,  # 90% VRU control
    )
    assert res_transit["results"]["ch4"]["value"] > 0

    # Crude Transport Validations
    with pytest.raises(ValueError, match="Unknown crude transport activity"):
        crude.calculate(activity="invalid_activity")
    with pytest.raises(ValueError, match="volume_loaded_bbl or volume_loaded_gal must be provided"):
        crude.calculate(activity="loading")
    with pytest.raises(ValueError, match="ballast_water_bbl or ballast_water_gal must be provided"):
        crude.calculate(activity="ballasting")
    with pytest.raises(ValueError, match="ch4_weight_pct cannot be negative"):
        crude.calculate(activity="loading", volume_loaded_bbl=100.0, ch4_weight_pct=-5.0)


def test_lng_distribution_and_non_routine_thorough():
    # 1. LNGVentingCalculator
    lng = LNGVentingCalculator()

    # Table 6-44 BOG transfer pipe losses for foam, powder, vacuum
    for ins in ("foam", "powder", "vacuum"):
        res_lng = lng.calculate(
            activity="loading_transfer",
            transfer_volume_m3=10000.0,
            pipe_length_km=2.5,
            insulation_type=ins,
            ch4_content=95.0,
            co2_content=1.0,
        )
        assert res_lng["results"]["ch4"]["value"] > 0
        assert res_lng["results"]["co2"]["value"] > 0

    # LNG Transfer volume in bbl
    res_lng_bbl = lng.calculate(
        activity="loading_transfer",
        transfer_volume_bbl=50000.0,
        pipe_length_km=1.0,
        insulation_type="foam",
    )
    assert res_lng_bbl["results"]["ch4"]["value"] > 0

    # Direct BOG venting vs flaring vs VRU
    res_bog_vent = lng.calculate(
        activity="direct_bog_vent",
        vented_gas_scf=100000.0,
        disposition="vented",
    )
    res_bog_flare = lng.calculate(
        activity="direct_bog_vent",
        vented_gas_scf=100000.0,
        disposition="flared",
        control_efficiency=0.98,
    )
    res_bog_rec = lng.calculate(
        activity="direct_bog_vent",
        vented_gas_scf=100000.0,
        disposition="recovered",
    )
    assert res_bog_flare["results"]["ch4"]["value"] < res_bog_vent["results"]["ch4"]["value"]
    assert res_bog_flare["results"]["co2"]["value"] > res_bog_vent["results"]["co2"]["value"]
    assert res_bog_flare["results"]["n2o"]["value"] > 0
    assert res_bog_rec["total_co2e"] == 0.0

    # LNG Validations
    with pytest.raises(ValueError, match="Unknown disposition"):
        lng.calculate(activity="direct_bog_vent", vented_gas_scf=100000.0, disposition="invalid_disp")
    with pytest.raises(ValueError, match="Unknown LNG activity"):
        lng.calculate(activity="invalid_act")
    with pytest.raises(ValueError, match="transfer_volume_m3 or transfer_volume_bbl must be provided"):
        lng.calculate(activity="loading_transfer")
    with pytest.raises(ValueError, match="vented_gas_scf or vented_gas_m3 must be provided"):
        lng.calculate(activity="direct_bog_vent")

    # 2. DistributionPneumaticsCalculator (Table 6-45)
    pneu = DistributionPneumaticsCalculator()
    for ctype in pneu.TABLE_6_45:
        res_p = pneu.calculate(
            controller_type=ctype,
            controller_count=5.0,
            ch4_content=92.0,
            co2_content=1.5,
        )
        assert res_p["results"]["ch4"]["value"] > 0
        assert res_p["results"]["co2"]["value"] > 0

    # 3. DistributionNonRoutineCalculator (Table 6-46 & Exhibit 6-34)
    nr = DistributionNonRoutineCalculator()
    for act in nr.TABLE_6_46:
        res_nr = nr.calculate(
            activity=act,
            count_or_miles=10.0,
            ch4_content=90.0,
            co2_content=2.0,
            disposition="flared",
            control_efficiency=0.95,
        )
        assert res_nr["results"]["ch4"]["value"] > 0
        assert res_nr["results"]["co2"]["value"] > 0
        assert res_nr["results"]["n2o"]["value"] > 0


def test_refining_downstream_catalyst_and_cokers():
    # 1. RefiningCatalystRegenCalculator
    cat = RefiningCatalystRegenCalculator()

    # Approach 1: Coke burn rate per year / per day / unit throughput
    res_cb_yr = cat.calculate(approach="coke_burn", coke_burn_rate_tonnes_yr=5000.0, carbon_content_fraction=0.93)
    # CO2 = 5000 * 0.93 * (44 / 12) = 17050 t
    assert res_cb_yr["results"]["co2"]["value"] == pytest.approx(5000.0 * 0.93 * (44.0 / 12.0))
    assert res_cb_yr["results"]["ch4"]["value"] > 0
    assert res_cb_yr["results"]["n2o"]["value"] > 0

    res_cb_tp = cat.calculate(approach="coke_burn", unit_throughput_bbl_day=20000.0, operating_days=350.0)
    assert res_cb_tp["results"]["co2"]["value"] > 0

    # Approach 2: Exhaust gas flow approach (K1 method)
    res_k1_m3 = cat.calculate(approach="k1_k2_k3", flue_gas_rate_dscm_min=1500.0, co2_pct=12.0, co_pct=1.0)
    res_k1_scf = cat.calculate(approach="k1_k2_k3", flue_gas_rate_dscf_min=50000.0, co2_pct=12.0, co_pct=1.0)
    assert res_k1_m3["results"]["co2"]["value"] > 0
    assert res_k1_scf["results"]["co2"]["value"] > 0

    # Approach 3: Air blower rate approach (m3/min and scf/min with SOR)
    res_air_m3 = cat.calculate(approach="air_blower", air_rate_m3_min=800.0, sor_m3_min=50.0, co2_pct=10.0, co_pct=2.0)
    res_air_scf = cat.calculate(approach="air_blower", air_rate_scf_min=30000.0, sor_scf_min=2000.0, co2_pct=10.0, co_pct=2.0)
    assert res_air_m3["results"]["co2"]["value"] > 0
    assert res_air_scf["results"]["co2"]["value"] > 0

    # Approach 4 & 5: Continuous and Intermittent catalyst regeneration
    res_cont = cat.calculate(approach="continuous", catalyst_circulation_rate_tonnes_hr=25.0, fc_spent=0.05, fc_regen=0.005)
    res_inter = cat.calculate(approach="intermittent", catalyst_inventory_tonnes=100.0, regeneration_cycles_per_yr=4.0, fc_spent=0.04)
    assert res_cont["results"]["co2"]["value"] > 0
    assert res_inter["results"]["co2"]["value"] > 0

    # Supplemental fuel firing (CO boiler firing gas)
    res_supp = cat.calculate(approach="coke_burn", coke_burn_rate_tonnes_yr=1000.0, supplemental_fuel_mmbtu_hr=50.0)
    assert res_supp["results"]["co2"]["value"] > res_cb_yr["results"]["co2"]["value"] / 5.0

    # Validation
    with pytest.raises(ValueError, match="Unknown catalyst regeneration approach"):
        cat.calculate(approach="unknown_app")

    # 2. RefiningCokerCalculator
    coker = RefiningCokerCalculator()

    # Delayed coker with direct steam mass
    res_dcu_direct = coker.calculate(coker_type="delayed", steam_mass_tonnes_cycle=20.0, num_cycles_per_yr=365.0)
    assert res_dcu_direct["results"]["ch4"]["value"] > 0

    # Delayed coker with vessel dimensions & pressure (Eq 6-46)
    res_dcu_geom_p = coker.calculate(
        coker_type="delayed",
        vessel_diameter_ft=25.0,
        vessel_height_ft=90.0,
        coke_drum_outage_ft=10.0,
        water_height_ft=70.0,
        p_overhead_psig=25.0,
        num_cycles_per_yr=300.0,
    )
    assert res_dcu_geom_p["results"]["ch4"]["value"] > 0

    # Delayed coker with vessel dimensions & temperatures (Eq 6-45)
    res_dcu_geom_t = coker.calculate(
        coker_type="delayed",
        vessel_diameter_ft=25.0,
        vessel_height_ft=90.0,
        water_height_ft=70.0,
        t_overhead_f=250.0,
        t_bottom_f=240.0,
    )
    assert res_dcu_geom_t["results"]["ch4"]["value"] > 0

    # Fluid coker with coke burned in lb/yr and tonnes/yr
    res_fluid_lb = coker.calculate(coker_type="fluid", coke_burned_lb_yr=1000000.0, carbon_wt_fraction=0.90)
    res_fluid_t = coker.calculate(coker_type="fluid", coke_burned_tonnes_yr=500.0, hydrogen_wt_fraction=0.015)
    assert res_fluid_lb["results"]["co2"]["value"] > 0
    assert res_fluid_t["results"]["co2"]["value"] > 0

    # Coker validation
    with pytest.raises(ValueError, match="Unknown coker type"):
        coker.calculate(coker_type="invalid_coker")
    with pytest.raises(ValueError, match="Delayed coker steam.*needs the water height"):
        coker.calculate(coker_type="delayed", vessel_diameter_ft=20.0, vessel_height_ft=80.0)


def test_refining_downstream_h2_asphalt_calcining_sru_petro_fire():
    # 1. RefiningHydrogenPlantCalculator
    h2_calc = RefiningHydrogenPlantCalculator()

    # Feedstock balance with detailed gas composition
    res_h2_comp = h2_calc.calculate(
        method="feedstock_balance",
        feedstock_volume_scf_yr=50000000.0,
        feedstock_comp={"CH4": 0.85, "C2H6": 0.08, "C3H8": 0.04, "CO2": 0.01, "N2": 0.02},
    )
    assert res_h2_comp["results"]["co2"]["value"] > 0

    # Feedstock balance with direct tonnes & carbon fraction
    res_h2_tonnes = h2_calc.calculate(
        method="feedstock_balance",
        feedstock_rate_tonnes_yr=10000.0,
        feedstock_carbon_fraction=0.75,
    )
    # CO2 = 10000 * 0.75 * (44 / 12) = 27500 t
    assert res_h2_tonnes["results"]["co2"]["value"] == pytest.approx(27500.0)

    # H2 stoichiometry (Eq 6-50) with auto-computed ratio from feed composition
    res_h2_stoich = h2_calc.calculate(
        method="h2_stoichiometry",
        h2_production_scf_yr=100000000.0,
        feedstock_comp={"CH4": 0.90, "C2H6": 0.10},
    )
    assert res_h2_stoich["results"]["co2"]["value"] > 0

    # Simple factors (Table 6-51) for all 4 bases
    for basis in h2_calc.FACTORS_TABLE_6_51:
        res_simple = h2_calc.calculate(method="simple_factor", simple_basis=basis, simple_volume=100000.0)
        assert res_simple["results"]["co2"]["value"] > 0

    # H2 Plant Validations
    with pytest.raises(ValueError, match="Unknown feed gas species"):
        h2_calc.calculate(method="feedstock_balance", feedstock_comp={"UNKNOWN_GAS": 1.0})
    with pytest.raises(ValueError, match="no hydrocarbon to reform"):
        h2_calc.calculate(method="h2_stoichiometry", h2_production_scf_yr=1e6, feedstock_comp={"N2": 1.0})

    # 2. AsphaltBlowingCalculator
    asphalt = AsphaltBlowingCalculator()
    for u in ("bbl", "m3", "short_ton", "tonne"):
        res_asp_un = asphalt.calculate(throughput=1000.0, unit=u, controlled=False)
        res_asp_ctrl = asphalt.calculate(throughput=1000.0, unit=u, controlled=True, destruction_efficiency=0.98)
        assert res_asp_un["results"]["ch4"]["value"] > res_asp_ctrl["results"]["ch4"]["value"]
        assert res_asp_ctrl["results"]["co2"]["value"] > res_asp_un["results"]["co2"]["value"]

    # 3. RefiningCokeCalciningCalculator (Eq 6-53)
    calciner = RefiningCokeCalciningCalculator()
    res_calc = calciner.calculate(
        green_coke_mass_tonnes_yr=10000.0,
        green_coke_carbon_fraction=0.88,
        calcined_coke_mass_tonnes_yr=8000.0,
        calcined_coke_carbon_fraction=0.98,
        dust_collected_tonnes_yr=200.0,
        dust_recycled_tonnes_yr=50.0,
    )
    assert res_calc["results"]["co2"]["value"] > 0

    with pytest.raises(ValueError, match="Coke calcining.*needs the carbon fractions"):
        calciner.calculate(green_coke_mass_tonnes_yr=10000.0)

    # 4. SulfurRecoveryTailGasCalculator (Eq 6-54) & Refinery Blowdowns
    sru = SulfurRecoveryTailGasCalculator()
    res_sru_scf = sru.calculate(sour_gas_scf_yr=5000000.0, carbon_mole_fraction=0.15)
    res_sru_m3 = sru.calculate(sour_gas_m3_yr=100000.0, carbon_mole_fraction=0.20)
    res_blowdown = sru.calculate(refinery_throughput_bbl_yr=10000000.0)
    assert res_sru_scf["results"]["co2"]["value"] > 0
    assert res_sru_m3["results"]["co2"]["value"] > 0
    assert res_blowdown["results"]["ch4"]["value"] > 0

    # 5. PetrochemicalManufacturingCalculator (Table 6-53 & Eq 6-55)
    petro = PetrochemicalManufacturingCalculator()
    for ptype in petro.TABLE_6_53:
        res_p = petro.calculate(process_type=ptype, production_tonnes=5000.0)
        assert res_p["total_co2e"] >= 0

    # Material balance Eq 6-55
    res_mb = petro.calculate(
        feedstocks=[(10000.0, 0.85), (5000.0, 0.80)],
        primary_product_tonnes=11000.0,
        primary_product_c_frac=0.82,
        secondary_products=[(1000.0, 0.70)],
    )
    assert res_mb["results"]["co2"]["value"] > 0

    # 6. FireSuppressionCalculator (Eq 6-56)
    fire = FireSuppressionCalculator()
    for agent in FIRE_AGENT_GWPS:
        res_fire = fire.calculate(
            agent_type=agent,
            total_charge_kg=500.0,
            annual_release_rate=0.03,  # 3% annual leakage
            direct_discharge_kg=50.0,
        )
        assert res_fire["total_co2e"] > 0

    with pytest.raises(ValueError, match="Unknown fire suppression agent"):
        fire.calculate(agent_type="halon_unknown")
    with pytest.raises(ValueError, match="Fire suppression leakage.*needs the fraction"):
        fire.calculate(agent_type="hfc_227ea", total_charge_kg=100.0)


def test_stoichiometry_and_uncertainty_advanced():
    # 1. mass_to_kg conversions
    assert mass_to_kg(1.0, "kg") == pytest.approx(1.0)
    assert mass_to_kg(1.0, "tonne") == pytest.approx(1000.0)
    assert mass_to_kg(1.0, "short ton") == pytest.approx(907.18474)
    assert mass_to_kg(1.0, "Short-Ton") == pytest.approx(907.18474)
    assert mass_to_kg(1.0, "us_ton") == pytest.approx(907.18474)
    assert mass_to_kg(1.0, "long ton") == pytest.approx(1016.0469088)
    assert mass_to_kg(1000.0, "g") == pytest.approx(1.0)
    assert mass_to_kg(2.20462, "lb") == pytest.approx(1.0, rel=1e-3)

    with pytest.raises(ValueError, match="Unknown mass unit"):
        mass_to_kg(10.0, "furlong_mass")

    # 2. StoichiometricCalculator
    stoich = StoichiometricCalculator()
    res_st1 = stoich.calculate(fuel_mass=1000.0, carbon_content=85.0, mass_unit="kg", oxidation_factor=99.0)
    # CO2 = 1000 * 0.85 * 0.99 * (44.01 / 12.011) / 1000 = 3.0837 t CO2
    expected_co2 = 1000.0 * 0.85 * 0.99 * (44.01 / 12.011) / 1000.0
    assert res_st1["results"]["co2"]["value"] == pytest.approx(expected_co2, rel=1e-3)

    # 3. NitricAcidCalculator
    acid = NitricAcidCalculator()
    res_nitric = acid.calculate(production_amount=100.0, process_type="nitric_acid_production", abatement_efficiency=90.0)
    # N2O = 100 t * 9.0 kg/t * (1 - 0.90) / 1000 = 0.09 t N2O
    assert res_nitric["results"]["n2o"]["value"] == pytest.approx(0.09)

    res_adipic = acid.calculate(production_amount=50.0, process_type="adipic_acid_production", abatement_efficiency=0.0)
    # N2O = 50 t * 300 kg/t / 1000 = 15.0 t N2O
    assert res_adipic["results"]["n2o"]["value"] == pytest.approx(15.0)

    with pytest.raises(ValueError, match="N2O emission factor cannot be negative"):
        acid.calculate(100.0, ef_n2o=-5.0)
    with pytest.raises(ValueError, match="Abatement efficiency cannot exceed 100 %"):
        acid.calculate(100.0, abatement_efficiency=120.0)
    with pytest.raises(ValueError, match="Abatement efficiency cannot be negative"):
        acid.calculate(100.0, abatement_efficiency=-10.0)

    # 4. propagate_co2e_uncertainty
    res_prop_gwp = propagate_co2e_uncertainty(
        e_co2=1000.0, u_co2=0.05,
        e_ch4=10.0, u_ch4=0.15,
        e_n2o=1.0, u_n2o=0.20,
        include_gwp_uncertainty=True,
    )
    assert res_prop_gwp["total_co2e"] == pytest.approx(1000.0 + 10.0 * 28.0 + 1.0 * 265.0)
    assert res_prop_gwp["sigma_co2e"] > 0
    assert res_prop_gwp["lower_bound_95"] < res_prop_gwp["total_co2e"]
    assert res_prop_gwp["upper_bound_95"] > res_prop_gwp["total_co2e"]

    # Without GWP uncertainty: variance is strictly smaller
    res_prop_nogwp = propagate_co2e_uncertainty(
        e_co2=1000.0, u_co2=0.05,
        e_ch4=10.0, u_ch4=0.15,
        e_n2o=1.0, u_n2o=0.20,
        include_gwp_uncertainty=False,
    )
    assert res_prop_nogwp["sigma_co2e"] < res_prop_gwp["sigma_co2e"]

    # 5. combine_uncertainties_product & combine_uncertainties_sum
    u_prod_std = combine_uncertainties_product(0.10, 0.05, exact=False)
    u_prod_exact = combine_uncertainties_product(0.10, 0.05, exact=True)
    assert u_prod_exact > u_prod_std
    assert u_prod_std == pytest.approx(math.sqrt(0.10**2 + 0.05**2))

    u_sum = combine_uncertainties_sum(100.0, 0.10, 200.0, 0.05)
    assert u_sum > 0
    assert combine_uncertainties_sum(0.0, 0.10, 0.0, 0.05) == 0.0

    # 6. Monte Carlo simulation percentiles & histogram
    sources = [
        {"value": 100.0, "relative_uncertainty": 0.10},
        {"value": 200.0, "relative_uncertainty": 0.15},
    ]
    mc = monte_carlo_simulation(sources, iterations=2000, seed=123)
    assert mc["mean"] == pytest.approx(300.0, rel=0.05)
    assert mc["ci_lower"] < mc["median"] < mc["ci_upper"]
    assert len(mc["histogram"]) == 18
    assert "p5" in mc["percentiles"] and "p95" in mc["percentiles"]


def test_vented_mud_and_exploration_advanced():
    # 1. MudDegassingCalculator
    mud = MudDegassingCalculator()

    # Tier 1 default
    res_mud_t1 = mud.calculate(wells=3.0, tier="tier1")
    assert res_mud_t1["results"]["ch4"]["value"] == pytest.approx(3.0 * 0.0524)

    # Tier 2 onshore water vs oil vs offshore
    res_on_water = mud.calculate(drilling_days=20.0, mud_type="water_based", location="onshore")
    res_on_oil = mud.calculate(drilling_days=20.0, mud_type="oil_based", location="onshore")
    res_off_water = mud.calculate(drilling_days=20.0, mud_type="water_based", location="offshore")
    assert res_on_water["results"]["ch4"]["value"] == pytest.approx(20.0 * 0.0458)
    assert res_on_oil["results"]["ch4"]["value"] == pytest.approx(20.0 * 0.0103)
    assert res_off_water["results"]["ch4"]["value"] == pytest.approx(20.0 * 0.2605)

    # Tier 2+ Site-specific composition with CO2 stoichiometric conversion
    res_mud_t2p = mud.calculate(
        drilling_days=10.0,
        mud_type="water_based",
        ch4_concentration=75.0,
        co2_concentration=5.0,
        tier="tier2_plus",
    )
    assert res_mud_t2p["results"]["ch4"]["value"] > 0
    assert res_mud_t2p["results"]["co2"]["value"] > 0
    expected_co2 = 10.0 * 0.0458 * (0.05 / 0.8385) * (44.01 / 16.04)
    assert res_mud_t2p["results"]["co2"]["value"] == pytest.approx(expected_co2, rel=1e-3)

    # Mud Validations
    with pytest.raises(ValueError, match="Unknown mud type"):
        mud.calculate(drilling_days=5.0, mud_type="unknown_mud")
    with pytest.raises(ValueError, match="Unknown well location"):
        mud.calculate(drilling_days=5.0, location="deep_space")
    with pytest.raises(ValueError, match="Sum of gas concentrations cannot exceed 100%"):
        mud.calculate(drilling_days=5.0, ch4_concentration=60.0, co2_concentration=50.0, tier="tier2_plus")

    # 2. WellTestingCalculator
    wt = WellTestingCalculator()

    # Tier 2 gas well rates: scf/hr, m3/hr, mmscf/day
    res_wt_scf_hr = wt.calculate(
        well_type="gas_well", tier="tier2",
        gas_production_rate=50000.0, rate_unit="scf/hr",
        test_duration_hours=24.0, ch4_content=81.6,
    )
    assert res_wt_scf_hr["results"]["ch4"]["value"] > 0

    res_wt_m3_hr = wt.calculate(
        well_type="gas_well", tier="tier2",
        gas_production_rate=1000.0, rate_unit="m3/hr",
        test_duration_hours=48.0, ch4_content=81.6,
    )
    assert res_wt_m3_hr["results"]["ch4"]["value"] > 0

    # Tier 2 oil well: GOR in m3/m3 and total oil in bbl
    res_wt_oil_m3 = wt.calculate(
        well_type="oil_well", tier="tier2",
        gor=100.0, gor_unit="m3/m3",  # 100 m3/m3 ~ 561.46 scf/bbl
        oil_production_total=5000.0, ch4_content=81.6,
    )
    assert res_wt_oil_m3["results"]["ch4"]["value"] > 0

    # Disposition routing: fractional vented, flared, recovered
    res_disp_split = wt.calculate(
        well_type="gas_well", tier="tier1",
        frac_vented=0.20, frac_flared=0.60, frac_recovered=0.20,
    )
    assert res_disp_split["results"]["ch4"]["value"] > 0
    assert res_disp_split["results"]["co2"]["value"] > 0
    assert res_disp_split["results"]["n2o"]["value"] > 0

    # 100% Recovered -> 0 emissions
    res_rec = wt.calculate(well_type="gas_well", tier="tier1", disposition="recovered")
    assert res_rec["total_co2e"] == 0.0

    # Well Testing Validations
    with pytest.raises(ValueError, match="Sum of disposition fractions.*cannot exceed 1.0"):
        wt.calculate(well_type="gas_well", tier="tier1", frac_vented=0.5, frac_flared=0.6)
    with pytest.raises(ValueError, match="Gas well testing Tier 2 requires non-negative gas_production_rate"):
        wt.calculate(well_type="gas_well", tier="tier2", gas_production_rate=-10.0, test_duration_days=1.0)

    # 3. CoalSeamDrillingCalculator (Exhibit 6-5)
    coal = CoalSeamDrillingCalculator()
    res_coal = coal.calculate(
        wells_data=[
            {"duration_days": 3.0, "gas_consumption_mmscf_day": 1.2},
            {"duration_days": 4.0, "gas_consumption_mmscf_day": 0.8},
        ],
        well_testing_gas_flared_scf=500000.0,
        flare_combustion_efficiency=0.985,
    )
    assert res_coal["results"]["ch4"]["value"] > 0
    assert res_coal["results"]["co2"]["value"] > 0
    assert res_coal["results"]["n2o"]["value"] > 0
