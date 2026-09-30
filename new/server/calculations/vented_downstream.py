"""
API Compendium 2021 - Sections 6.11, 6.12, 6.14: Downstream Refining, Petrochemicals & Fire Suppression
Vented and Process Emissions Calculation Modules

Governing Standard:
API Compendium of Greenhouse Gas Emissions Methodologies for the Oil and Natural Gas Industry
4th Edition, November 2021:
- §6.11 Refining:
    * §6.11.1 Catalyst Regeneration:
        - FCCU coke burn rate (Eq 6-34, Eq 6-37, Exhibit 6-38)
        - FCCU flue gas K1/K2/K3 rate (Eq 6-35)
        - FCCU air blower capacity rate (Eq 6-36)
        - Catalyst coke CH4 and N2O combustion (Eq 6-38, Eq 6-39)
        - Other continuous catalyst regenerators (Eq 6-40, Exhibit 6-39)
        - Other intermittent catalyst regenerators (Eq 6-41, Exhibit 6-40)
    * §6.11.2 Cokers:
        - Fluid coker coke combustion (Eq 6-34, Exhibit 6-61)
        - Delayed coking unit (DCU) decoking operations (Eq 6-42 to Eq 6-47)
    * §6.11.3 Refinery Hydrogen Plants:
        - Feedstock material balance (Eq 6-49, Exhibit 6-42)
        - Hydrogen production stoichiometric balance (Eq 6-50, Exhibit 6-43)
        - Simple conversion emission factors (Table 6-51, Exhibit 6-44)
    * §6.11.4 Asphalt Blowing:
        - Uncontrolled blowing (Table 6-52, Exhibit 6-45)
        - Controlled blowing with combustion/incineration (Eq 6-51, Eq 6-52)
    * §6.11.5 Coke Calcining:
        - Mass balance on green coke vs product & dust (Eq 6-53)
    * §6.11.6 Other Refining Related Process Vents:
        - Sulfur Recovery Unit (SRU) sour gas feed / tail gas (Eq 6-54)
        - Refinery process blowdowns default factor (137,000 scf CH4 / MMbbl)
- §6.12 Petrochemical Manufacturing:
    * Table 6-53 chemical production factors (Acrylonitrile, Carbon Black, Ethylene, EDC, EO, Methanol, Nitric Acid, Adipic Acid)
    * Petrochemical material balance (Eq 6-55)
- §6.14 Fire Suppression Emissions:
    * Material balance on fire extinguishing agents (Eq 6-56)
    * Agents: CO2, HFC-227ea, HFC-125, HFC-236fa, Halon 1301, FK-5-1-12
"""

import math
from .base import BaseCalculator
from .units import (
    CONVERSIONS,
    STD_PRESSURE_PSIA,
    convert,
    calculate_co2e,
    normalize_efficiency,
)
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
)

MOLAR_VOL_US = 379.3   # scf / lb-mole at 60 °F, 14.696 psia
MOLAR_VOL_METRIC = 23.685  # Sm3 / kg-mole at 15 °C, 101.325 kPa
MW_CH4 = 16.04
MW_CO2 = 44.01
MW_N2O = 44.013
MW_C = 12.011
LB_PER_TONNE = 2204.6226218487757

# Default emission factors for petroleum coke combustion from Tables 4-3 and 4-5
# in tonnes / MMBtu
EF_COKE_CO2_MMBTU = 0.1021   # tonne CO2 / MMBtu (Table 4-3)
EF_COKE_CH4_MMBTU = 3.0e-6   # tonne CH4 / MMBtu (Table 4-5)
EF_COKE_N2O_MMBTU = 6.0e-7   # tonne N2O / MMBtu (Table 4-5)

# GWP values for fire suppression agents (IPCC AR4 / AR5 standard)
FIRE_AGENT_GWPS = {
    "co2": 1.0,
    "hfc_227ea": 3220.0,   # FM-200
    "hfc_125": 3500.0,     # FE-25
    "hfc_236fa": 9810.0,   # FE-36
    "halon_1301": 7140.0,
    "fk_5_1_12": 1.0,      # Novec 1230
    "other": 1.0,
}


def _split_vent_flare(total_gas_m3, ch4_tonnes, co2_tonnes, ctrl_eff=0.0, hhv=1020.0, ef_n2o=None):
    ctrl = normalize_efficiency(ctrl_eff, default=0.0)
    vented_frac = 1.0 - ctrl

    vented_ch4 = ch4_tonnes * vented_frac
    vented_co2 = co2_tonnes * vented_frac

    flared_co2 = 0.0
    flared_unburnt_ch4 = 0.0
    flared_n2o = 0.0

    if ctrl > 0:
        flared_ch4_mass = ch4_tonnes * ctrl
        flared_native_co2 = co2_tonnes * ctrl

        flared_ch4_combusted = flared_ch4_mass * 0.98
        flared_co2 = (flared_ch4_combusted * (MW_CO2 / MW_CH4)) + flared_native_co2
        flared_unburnt_ch4 = flared_ch4_mass * 0.02

        flared_m3 = total_gas_m3 * ctrl
        flared_scf = convert(flared_m3, "m3", "scf")
        hhv_val = float(hhv or 1020.0)
        flared_mmbtu = (flared_scf * hhv_val) / 1_000_000.0
        n2o_ef_kg = float(ef_n2o if ef_n2o is not None else 0.0001)
        flared_n2o = (flared_mmbtu * n2o_ef_kg) / 1000.0

    total_ch4 = vented_ch4 + flared_unburnt_ch4
    total_co2 = vented_co2 + flared_co2

    return {
        "vented_ch4": vented_ch4,
        "vented_co2": vented_co2,
        "flared_co2": flared_co2,
        "flared_unburnt_ch4": flared_unburnt_ch4,
        "flared_n2o": flared_n2o,
        "total_ch4": total_ch4,
        "total_co2": total_co2,
    }


def _propagate_results(total_ch4, total_co2, n2o, uncertainties, factor_source="default", category="vented"):
    _tier = resolve_tier(factor_source)
    ch4_res = (
        propagate_uncertainty(
            total_ch4,
            resolve_ef_uncertainty(category, "ch4", _tier, (uncertainties or {}).get("ch4")),
            tier=_tier,
            process_category=category,
            gas="ch4",
        )
        if total_ch4 > 0
        else None
    )
    co2_res = (
        propagate_uncertainty(
            total_co2,
            resolve_ef_uncertainty(category, "co2", _tier, (uncertainties or {}).get("co2")),
            tier=_tier,
            process_category=category,
            gas="co2",
        )
        if total_co2 > 0
        else None
    )
    n2o_res = (
        propagate_uncertainty(
            n2o,
            resolve_ef_uncertainty(category, "n2o", _tier, (uncertainties or {}).get("n2o")),
            tier=_tier,
            process_category=category,
            gas="n2o",
        )
        if n2o > 0
        else None
    )
    return ch4_res, co2_res, n2o_res


# ==============================================================================
# §6.11.1 Refining Catalyst Regeneration
# ==============================================================================
class RefiningCatalystRegenCalculator(BaseCalculator):
    """
    API Compendium 2021 §6.11.1 - Catalyst Regeneration:
    - FCCU Coke Burn Rate Approach (Equation 6-34, Equation 6-37, Exhibit 6-38)
    - FCCU Exhaust Gas Flow & Composition / K1, K2, K3 Approach (Equation 6-35)
    - FCCU Air Blower Capacity Approach (Equation 6-36)
    - Continuous Catalyst Regenerators (Equation 6-40, Exhibit 6-39)
    - Intermittent Catalyst Regenerators (Equation 6-41, Exhibit 6-40)
    - Coke combustion CH4 and N2O emissions (Equations 6-38 and 6-39)
    """

    def __init__(self):
        super().__init__("Refining Catalyst Regeneration", "Section 6.11.1")

    def calculate(
        self,
        approach="coke_burn",  # "coke_burn", "k1_k2_k3", "air_blower", "continuous", "intermittent"
        # 1. Coke burn inputs (Eq 6-34 & Eq 6-37)
        coke_burn_rate_tonnes_day=None,
        coke_burn_rate_tonnes_yr=None,
        unit_throughput_bbl_day=None,
        coke_burn_off_factor_kg_bbl=7.3,  # default 7.3 kg/bbl for FCCU, 11 for fluid coker
        operating_days=365.0,
        carbon_content_fraction=0.93,     # Exhibit 6-38 default 0.93 or 1.0
        # 2. Exhaust gas flow approach (Eq 6-35)
        flue_gas_rate_dscm_min=None,
        flue_gas_rate_dscf_min=None,
        operating_hours=8760.0,
        co2_pct=11.0,
        co_pct=9.0,
        # 3. Air blower rate approach (Eq 6-36)
        air_rate_m3_min=None,
        air_rate_scf_min=None,
        sor_m3_min=0.0,                   # supplemental oxygen rate
        sor_scf_min=0.0,
        # 4. Continuous catalyst regeneration (Eq 6-40)
        catalyst_circulation_rate_tonnes_hr=None,
        fc_spent=0.04,                    # wt fraction carbon on spent catalyst
        fc_regen=0.0,                     # wt fraction carbon on regenerated catalyst
        # 5. Intermittent catalyst regeneration (Eq 6-41)
        catalyst_inventory_tonnes=None,
        regeneration_cycles_per_yr=None,
        # 6. Supplemental fuel firing (e.g. CO boiler firing natural gas, Exhibit 6-38)
        supplemental_fuel_mmbtu_hr=0.0,
        supplemental_co2_ef_tonne_mmbtu=0.0531,  # pipeline gas Table 4-3
        supplemental_ch4_ef_tonne_mmbtu=1.0e-6,  # boiler Table 4-7
        supplemental_n2o_ef_tonne_mmbtu=9.8e-7,  # boiler Table 4-7
        uncertainties=None,
        factor_source="API 2021 §6.11.1",
        gwp_dict=None,
        **kwargs,
    ):
        co2_coke = 0.0

        if approach == "coke_burn":
            annual_coke = 0.0
            if coke_burn_rate_tonnes_yr is not None and coke_burn_rate_tonnes_yr > 0:
                annual_coke = float(coke_burn_rate_tonnes_yr)
            elif coke_burn_rate_tonnes_day is not None and coke_burn_rate_tonnes_day > 0:
                annual_coke = float(coke_burn_rate_tonnes_day) * float(operating_days)
            elif unit_throughput_bbl_day is not None and unit_throughput_bbl_day > 0:
                daily_coke = float(unit_throughput_bbl_day) * (float(coke_burn_off_factor_kg_bbl) * 0.001)
                annual_coke = daily_coke * float(operating_days)

            cf = float(carbon_content_fraction or 0.93)
            # Equation 6-34: ECO2 = CCAvg * CF * (44 / 12) * T
            co2_coke = annual_coke * cf * (44.0 / 12.0)

        elif approach == "k1_k2_k3":
            p_co2 = float(co2_pct or 0.0)
            p_co = float(co_pct or 0.0)
            hrs = float(8760.0 if operating_hours is None else operating_hours)
            if flue_gas_rate_dscm_min is not None:
                qr = float(flue_gas_rate_dscm_min)
                k1 = 0.2982
                co2_coke = k1 * qr * (p_co2 + p_co) * (44.0 / 12.0) * hrs / 1000.0
            elif flue_gas_rate_dscf_min is not None:
                qr = float(flue_gas_rate_dscf_min)
                k1 = 0.0186
                co2_coke = (k1 * qr * (p_co2 + p_co) * (44.0 / 12.0) * hrs) / LB_PER_TONNE

        elif approach == "air_blower":
            f_co2 = float(co2_pct or 11.0) / 100.0 if co2_pct > 1.0 else float(co2_pct)
            f_co = float(co_pct or 9.0) / 100.0 if co_pct > 1.0 else float(co_pct)
            total_min = float(8760.0 if operating_hours is None else operating_hours) * 60.0

            if air_rate_m3_min is not None:
                ar = float(air_rate_m3_min) + float(sor_m3_min or 0.0)
                kg_co2 = ar * (f_co2 + f_co) * (44.0 / 23.685) * total_min
                co2_coke = kg_co2 / 1000.0
            elif air_rate_scf_min is not None:
                ar = float(air_rate_scf_min) + float(sor_scf_min or 0.0)
                lb_co2 = ar * (f_co2 + f_co) * (44.0 / 379.3) * total_min
                co2_coke = lb_co2 / LB_PER_TONNE

        elif approach == "continuous":
            crr = float(catalyst_circulation_rate_tonnes_hr or 0.0)
            h = float(8760.0 if operating_hours is None else operating_hours)
            c_diff = float(fc_spent or 0.0) - float(fc_regen or 0.0)
            co2_coke = crr * h * c_diff * (44.0 / 12.0)

        elif approach == "intermittent":
            crr = float(catalyst_inventory_tonnes or 0.0)
            n_cycles = float(regeneration_cycles_per_yr or 1.0)
            c_diff = float(fc_spent or 0.0) - float(fc_regen or 0.0)
            co2_coke = crr * n_cycles * c_diff * (44.0 / 12.0)

        # Equations 6-38 and 6-39 for coke combustion CH4 and N2O
        ratio_ch4 = EF_COKE_CH4_MMBTU / EF_COKE_CO2_MMBTU
        ratio_n2o = EF_COKE_N2O_MMBTU / EF_COKE_CO2_MMBTU

        ch4_coke = co2_coke * ratio_ch4
        n2o_coke = co2_coke * ratio_n2o

        # Supplemental fuel firing (e.g. CO boiler firing gas)
        supp_co2 = 0.0
        supp_ch4 = 0.0
        supp_n2o = 0.0
        if supplemental_fuel_mmbtu_hr > 0:
            hrs = float(8760.0 if operating_hours is None else operating_hours)
            total_supp_mmbtu = float(supplemental_fuel_mmbtu_hr) * hrs
            supp_co2 = total_supp_mmbtu * float(supplemental_co2_ef_tonne_mmbtu)
            supp_ch4 = total_supp_mmbtu * float(supplemental_ch4_ef_tonne_mmbtu)
            supp_n2o = total_supp_mmbtu * float(supplemental_n2o_ef_tonne_mmbtu)

        total_co2 = co2_coke + supp_co2
        total_ch4 = ch4_coke + supp_ch4
        total_n2o = n2o_coke + supp_n2o

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4, total_co2, total_n2o, uncertainties, factor_source, "refining_catalyst"
        )
        co2e = calculate_co2e(total_ch4, total_co2, total_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            co2=co2_res or total_co2,
            ch4=ch4_res or total_ch4,
            n2o=n2o_res or total_n2o,
            total_co2e=co2e,
            inputs={
                "approach": approach,
                "coke_burn_co2": co2_coke,
                "coke_burn_ch4": ch4_coke,
                "coke_burn_n2o": n2o_coke,
                "supplemental_co2": supp_co2,
                "supplemental_ch4": supp_ch4,
                "supplemental_n2o": supp_n2o,
            },
            metadata={"standard": "API Compendium 2021 §6.11.1", "equations": "Eq 6-34 to 6-41"},
        )


# ==============================================================================
# §6.11.2 Refining Cokers (DCU Steam Venting & Fluid Coker)
# ==============================================================================
class RefiningCokerCalculator(BaseCalculator):
    """
    API Compendium 2021 §6.11.2 - Cokers:
    - Fluid coker coke burner emissions (Equation 6-34, Exhibit 6-61)
    - Delayed coking unit (DCU) steam venting and decoking (Equations 6-42 through 6-47)
    """

    def __init__(self):
        super().__init__("Refining Cokers", "Section 6.11.2")

    def calculate(
        self,
        coker_type="delayed",            # "delayed" or "fluid"
        # DCU inputs:
        steam_mass_tonnes_cycle=None,    # Msteam if known directly
        num_cycles_per_yr=1.0,           # N
        dcu_ch4_ef_kg_tonne_steam=7.9,   # EFDCU default 7.9 kg CH4 / tonne steam
        # DCU vessel dimensions if steam mass unknown (Eq 6-43 to 6-47):
        vessel_diameter_ft=None,         # D
        vessel_height_ft=None,           # Hdrum
        coke_drum_outage_ft=0.0,         # Houtage
        water_height_ft=None,            # Hwater (distance bottom to top of water)
        bulk_density_tonne_cuft=0.0191,  # rho_bulk
        particle_density_tonne_cuft=0.0382, # rho_particle
        water_density_tonne_cuft=0.0270,    # rho_water
        t_overhead_f=None,
        t_bottom_f=None,
        p_overhead_psig=None,
        t_final_f=212.0,
        f_conv_loss=0.10,
        cp_water=2205.0,                 # Btu / tonne-°F
        cp_coke=584.0,                   # Btu / tonne-°F
        delta_h_vap=2116000.0,           # Btu / tonne
        # Fluid coker inputs:
        coke_burned_lb_yr=None,
        coke_burned_tonnes_yr=None,
        hydrogen_wt_fraction=0.015,      # 1.5% H2 default
        carbon_wt_fraction=None,
        uncertainties=None,
        factor_source="API 2021 §6.11.2",
        gwp_dict=None,
        **kwargs,
    ):
        total_ch4 = 0.0
        total_co2 = 0.0
        m_steam_calculated = 0.0
        m_coke_calculated = 0.0
        m_water_calculated = 0.0

        if coker_type == "delayed":
            m_steam = 0.0
            if steam_mass_tonnes_cycle is not None and steam_mass_tonnes_cycle > 0:
                m_steam = float(steam_mass_tonnes_cycle)
            elif vessel_diameter_ft is not None and vessel_height_ft is not None:
                d = float(vessel_diameter_ft)
                h_drum = float(vessel_height_ft)
                h_outage = float(coke_drum_outage_ft or 0.0)
                vessel_area = math.pi * (d ** 2) / 4.0

                m_coke_calculated = float(bulk_density_tonne_cuft) * ((h_drum - h_outage) * vessel_area)

                h_w = float(water_height_ft if water_height_ft is not None else (h_drum - h_outage))
                bed_volume = h_w * vessel_area
                coke_displaced_vol = m_coke_calculated / float(particle_density_tonne_cuft)
                water_vol = max(0.0, bed_volume - coke_displaced_vol)
                m_water_calculated = float(water_density_tonne_cuft) * water_vol

                if p_overhead_psig is not None:
                    p = float(p_overhead_psig)
                    t_initial = -0.039 * (p ** 2) + 3.13 * p + 220.0
                elif t_overhead_f is not None and t_bottom_f is not None:
                    t_ov = max(216.0, float(t_overhead_f))
                    t_bt = max(212.0, float(t_bottom_f))
                    t_initial = (t_ov + t_bt) / 2.0
                else:
                    t_initial = 220.0

                delta_t = max(0.0, t_initial - float(t_final_f or 212.0))
                heat_water = m_water_calculated * float(cp_water)
                heat_coke = m_coke_calculated * float(cp_coke)
                total_heat = (1.0 - float(f_conv_loss or 0.10)) * (heat_water + heat_coke) * delta_t
                m_steam = total_heat / float(delta_h_vap)
                m_steam_calculated = m_steam

            ef_dcu = float(dcu_ch4_ef_kg_tonne_steam or 7.9)
            n_cycles = float(num_cycles_per_yr or 1.0)
            total_ch4 = m_steam * ef_dcu * n_cycles * 0.001

        elif coker_type == "fluid":
            if carbon_wt_fraction is not None:
                cf = float(carbon_wt_fraction)
            else:
                cf = 1.0 - float(hydrogen_wt_fraction or 0.015)

            if coke_burned_lb_yr is not None and coke_burned_lb_yr > 0:
                total_co2 = (float(coke_burned_lb_yr) * cf * (44.0 / 12.0)) / LB_PER_TONNE
            elif coke_burned_tonnes_yr is not None and coke_burned_tonnes_yr > 0:
                total_co2 = float(coke_burned_tonnes_yr) * cf * (44.0 / 12.0)

        ch4_res, co2_res, _ = _propagate_results(
            total_ch4, total_co2, 0.0, uncertainties, factor_source, "refining_coker"
        )
        co2e = calculate_co2e(total_ch4, total_co2, 0.0, gwp_dict=gwp_dict)

        return self.format_result(
            co2=co2_res or total_co2,
            ch4=ch4_res or total_ch4,
            n2o=0.0,
            total_co2e=co2e,
            inputs={
                "coker_type": coker_type,
                "steam_mass_per_cycle_tonnes": m_steam_calculated or steam_mass_tonnes_cycle,
                "coke_mass_tonnes": m_coke_calculated,
                "water_mass_tonnes": m_water_calculated,
            },
            metadata={"standard": "API Compendium 2021 §6.11.2", "equations": "Eq 6-42 to 6-47"},
        )


# ==============================================================================
# §6.11.3 Refinery Hydrogen Plants
# ==============================================================================
class RefiningHydrogenPlantCalculator(BaseCalculator):
    """
    API Compendium 2021 §6.11.3 - Refinery Hydrogen Plants:
    - Rigorous feedstock carbon balance (Equation 6-49, Exhibit 6-42)
    - Rigorous hydrogen production stoichiometry (Equation 6-50, Exhibit 6-43)
    - Simple stoichiometric conversion factor approach (Table 6-51, Exhibit 6-44)
    """

    FACTORS_TABLE_6_51 = {
        "feedstock_scf": 54.42 / 1_000_000.0,  # tonnes CO2 / scf feedstock
        "feedstock_m3": 1922.0 / 1_000_000.0,   # tonnes CO2 / m3 feedstock
        "h2_scf": 13.41 / 1_000_000.0,          # tonnes CO2 / scf H2 produced
        "h2_m3": 473.6 / 1_000_000.0,           # tonnes CO2 / m3 H2 produced
    }

    def __init__(self):
        super().__init__("Refining Hydrogen Plant", "Section 6.11.3")

    def calculate(
        self,
        method="feedstock_balance",      # "feedstock_balance", "h2_stoichiometry", "simple_factor"
        # 1. Feedstock balance (Eq 6-49, Exhibit 6-42)
        feedstock_rate_tonnes_yr=None,
        feedstock_volume_scf_yr=None,
        feedstock_volume_m3_yr=None,
        feedstock_carbon_fraction=None,  # CF (wt fraction C)
        feedstock_comp=None,             # dict of mole fractions: {"CH4": 0.85, "C2H6": 0.08, "C4H10": 0.03, "N2": 0.04}
        # 2. H2 stoichiometry (Eq 6-50, Exhibit 6-43)
        h2_production_scf_yr=None,
        h2_production_m3_yr=None,
        co2_to_h2_molar_ratio=None,      # e.g. 0.26 in Exhibit 6-43
        # 3. Simple factor (Table 6-51, Exhibit 6-44)
        simple_basis="h2_scf",           # "h2_scf", "h2_m3", "feedstock_scf", "feedstock_m3"
        simple_volume=None,
        uncertainties=None,
        factor_source="API 2021 §6.11.3",
        gwp_dict=None,
        **kwargs,
    ):
        total_co2 = 0.0

        if method == "feedstock_balance":
            cf = feedstock_carbon_fraction
            fr_tonnes = feedstock_rate_tonnes_yr

            if feedstock_comp is not None and (cf is None or fr_tonnes is None):
                species_data = {
                    "CH4": (16.04, 1),
                    "C2H6": (30.07, 2),
                    "C3H8": (44.10, 3),
                    "C4H10": (58.12, 4),
                    "C5H12": (72.15, 5),
                    "CO": (28.01, 1),
                    "CO2": (44.01, 1),
                    "N2": (28.01, 0),
                    "H2": (2.016, 0),
                }
                mix_mw = sum(mol_frac * species_data.get(k, (28.0, 0))[0] for k, mol_frac in feedstock_comp.items())
                total_c_wt = sum(mol_frac * species_data.get(k, (28.0, 0))[1] * 12.011 for k, mol_frac in feedstock_comp.items())
                cf = total_c_wt / mix_mw

                if fr_tonnes is None:
                    if feedstock_volume_scf_yr is not None:
                        lbmoles = float(feedstock_volume_scf_yr) / MOLAR_VOL_US
                        lb_feed = lbmoles * mix_mw
                        fr_tonnes = lb_feed / LB_PER_TONNE
                    elif feedstock_volume_m3_yr is not None:
                        kgmoles = float(feedstock_volume_m3_yr) / MOLAR_VOL_METRIC
                        kg_feed = kgmoles * mix_mw
                        fr_tonnes = kg_feed / 1000.0

            if fr_tonnes is not None and cf is not None:
                total_co2 = float(fr_tonnes) * float(cf) * (44.0 / 12.0)

        elif method == "h2_stoichiometry":
            ratio = co2_to_h2_molar_ratio
            if ratio is None and feedstock_comp is not None:
                rxn_h2 = {"CH4": 4.0, "C2H6": 7.0, "C3H8": 10.0, "C4H10": 13.0, "C5H12": 16.0}
                rxn_c = {"CH4": 1.0, "C2H6": 2.0, "C3H8": 3.0, "C4H10": 4.0, "C5H12": 5.0}
                moles_c = sum(feedstock_comp.get(k, 0.0) * rxn_c.get(k, 0.0) for k in rxn_c)
                moles_h2 = sum(feedstock_comp.get(k, 0.0) * rxn_h2.get(k, 0.0) for k in rxn_h2)
                ratio = moles_c / moles_h2 if moles_h2 > 0 else 0.25

            ratio_val = float(ratio or 0.25)
            if h2_production_scf_yr is not None:
                lbmoles_h2 = float(h2_production_scf_yr) / MOLAR_VOL_US
                lb_co2 = lbmoles_h2 * ratio_val * 44.0
                total_co2 = lb_co2 / LB_PER_TONNE
            elif h2_production_m3_yr is not None:
                kgmoles_h2 = float(h2_production_m3_yr) / MOLAR_VOL_METRIC
                kg_co2 = kgmoles_h2 * ratio_val * 44.0
                total_co2 = kg_co2 / 1000.0

        elif method == "simple_factor":
            ef = self.FACTORS_TABLE_6_51.get(simple_basis, self.FACTORS_TABLE_6_51["h2_scf"])
            vol = float(simple_volume if simple_volume is not None else (h2_production_scf_yr or 0.0))
            total_co2 = vol * ef

        _, co2_res, _ = _propagate_results(
            0.0, total_co2, 0.0, uncertainties, factor_source, "refining_h2_plant"
        )
        co2e = total_co2

        return self.format_result(
            co2=co2_res or total_co2,
            ch4=0.0,
            n2o=0.0,
            total_co2e=co2e,
            inputs={"method": method, "total_co2": total_co2},
            metadata={"standard": "API Compendium 2021 §6.11.3", "table": "Table 6-51"},
        )


# ==============================================================================
# §6.11.4 Asphalt Blowing
# ==============================================================================
class AsphaltBlowingCalculator(BaseCalculator):
    """
    API Compendium 2021 §6.11.4 - Asphalt Blowing:
    - Table 6-52 Default Emission Factors
    - Uncontrolled Venting (Exhibit 6-45)
    - Controlled Venting / Incineration (Equations 6-51 and 6-52)
    """

    TABLE_6_52 = {
        "bbl": {"ch4": 5.55e-4, "co2": 1.01e-3},
        "m3": {"ch4": 3.49e-3, "co2": 6.38e-3},
        "ton": {"ch4": 3.07e-3, "co2": 5.61e-3},
        "tonne": {"ch4": 3.38e-3, "co2": 6.19e-3},
    }

    def __init__(self):
        super().__init__("Asphalt Blowing", "Section 6.11.4")

    def calculate(
        self,
        throughput=0.0,
        unit="ton",                      # "bbl", "m3", "ton", "tonne"
        controlled=False,
        destruction_efficiency=0.98,     # DE default 98%
        uncertainties=None,
        factor_source="API 2021 Table 6-52",
        gwp_dict=None,
        **kwargs,
    ):
        q = float(throughput or 0.0)
        u = str(unit).lower()
        efs = self.TABLE_6_52.get(u, self.TABLE_6_52["ton"])
        ef_ch4 = efs["ch4"]
        ef_co2 = efs["co2"]

        if not controlled:
            total_ch4 = q * ef_ch4
            total_co2 = q * ef_co2
        else:
            de = normalize_efficiency(destruction_efficiency, default=0.98)
            total_ch4 = q * ef_ch4 * (1.0 - de)
            total_co2 = (q * ef_co2) + (q * ef_ch4 * de * (44.0 / 16.0))

        ch4_res, co2_res, _ = _propagate_results(
            total_ch4, total_co2, 0.0, uncertainties, factor_source, "asphalt_blowing"
        )
        co2e = calculate_co2e(total_ch4, total_co2, 0.0, gwp_dict=gwp_dict)

        return self.format_result(
            co2=co2_res or total_co2,
            ch4=ch4_res or total_ch4,
            n2o=0.0,
            total_co2e=co2e,
            inputs={"throughput": q, "unit": u, "controlled": controlled},
            metadata={"standard": "API Compendium 2021 §6.11.4", "table": "Table 6-52"},
        )


# ==============================================================================
# §6.11.5 Coke Calcining
# ==============================================================================
class RefiningCokeCalciningCalculator(BaseCalculator):
    """
    API Compendium 2021 §6.11.5 - Coke Calcining:
    - Mass balance approach (Equation 6-53)
    """

    def __init__(self):
        super().__init__("Refining Coke Calcining", "Section 6.11.5")

    def calculate(
        self,
        green_coke_mass_tonnes_yr=0.0,       # GC
        green_coke_carbon_fraction=0.88,     # CCGC (default ~0.88)
        calcined_coke_mass_tonnes_yr=0.0,    # PCout
        calcined_coke_carbon_fraction=0.98,  # CCPC (default ~0.98)
        dust_collected_tonnes_yr=0.0,        # PCdust
        dust_recycled_tonnes_yr=0.0,
        uncertainties=None,
        factor_source="API 2021 §6.11.5",
        gwp_dict=None,
        **kwargs,
    ):
        gc = float(green_coke_mass_tonnes_yr or 0.0)
        cc_gc = float(green_coke_carbon_fraction or 0.88)
        pcout = float(calcined_coke_mass_tonnes_yr or 0.0)
        cc_pc = float(calcined_coke_carbon_fraction or 0.98)
        pcdust = max(0.0, float(dust_collected_tonnes_yr or 0.0) - float(dust_recycled_tonnes_yr or 0.0))

        c_in = gc * cc_gc
        c_out = (pcout + pcdust) * cc_pc
        c_burned = max(0.0, c_in - c_out)
        total_co2 = (44.0 / 12.0) * c_burned

        _, co2_res, _ = _propagate_results(
            0.0, total_co2, 0.0, uncertainties, factor_source, "coke_calcining"
        )
        co2e = total_co2

        return self.format_result(
            co2=co2_res or total_co2,
            ch4=0.0,
            n2o=0.0,
            total_co2e=co2e,
            inputs={"carbon_consumed_tonnes": c_burned},
            metadata={"standard": "API Compendium 2021 §6.11.5", "equation": "Eq 6-53"},
        )


# ==============================================================================
# §6.11.6 Sulfur Recovery & Other Refining Process Vents
# ==============================================================================
class SulfurRecoveryTailGasCalculator(BaseCalculator):
    """
    API Compendium 2021 §6.11.6 - Sulfur Recovery Unit (SRU) Tail Gas & Refining Vents:
    - SRU Sour Gas Feed Carbon Material Balance (Equation 6-54)
    - Refinery Process Blowdowns simplified factor (137,000 scf CH4 / MMbbl crude)
    """

    def __init__(self):
        super().__init__("Sulfur Recovery Tail Gas", "Section 6.11.6")

    def calculate(
        self,
        # Equation 6-54 inputs:
        sour_gas_scf_yr=None,
        sour_gas_m3_yr=None,
        carbon_mole_fraction=0.20,       # FC default 0.20 mole C/mole gas
        # Refinery blowdowns factor:
        refinery_throughput_bbl_yr=None,
        uncertainties=None,
        factor_source="API 2021 §6.11.6",
        gwp_dict=None,
        **kwargs,
    ):
        total_co2 = 0.0
        total_ch4 = 0.0

        if sour_gas_scf_yr is not None and sour_gas_scf_yr > 0:
            fsg = float(sour_gas_scf_yr)
            fc = float(carbon_mole_fraction or 0.20)
            lb_co2 = fsg * (44.0 / MOLAR_VOL_US) * fc
            total_co2 = lb_co2 / LB_PER_TONNE
        elif sour_gas_m3_yr is not None and sour_gas_m3_yr > 0:
            fsg = float(sour_gas_m3_yr)
            fc = float(carbon_mole_fraction or 0.20)
            kg_co2 = fsg * (44.0 / MOLAR_VOL_METRIC) * fc
            total_co2 = kg_co2 / 1000.0

        if refinery_throughput_bbl_yr is not None and refinery_throughput_bbl_yr > 0:
            bbl = float(refinery_throughput_bbl_yr)
            scf_ch4 = (bbl / 1_000_000.0) * 137_000.0
            total_ch4 = convert(scf_ch4, "scf", "tonne_ch4")

        ch4_res, co2_res, _ = _propagate_results(
            total_ch4, total_co2, 0.0, uncertainties, factor_source, "refining_other_vents"
        )
        co2e = calculate_co2e(total_ch4, total_co2, 0.0, gwp_dict=gwp_dict)

        return self.format_result(
            co2=co2_res or total_co2,
            ch4=ch4_res or total_ch4,
            n2o=0.0,
            total_co2e=co2e,
            inputs={"sru_co2": total_co2, "blowdown_ch4": total_ch4},
            metadata={"standard": "API Compendium 2021 §6.11.6", "equation": "Eq 6-54"},
        )


# ==============================================================================
# §6.12 Petrochemical Manufacturing
# ==============================================================================
class PetrochemicalManufacturingCalculator(BaseCalculator):
    """
    API Compendium 2021 §6.12 - Petrochemical Manufacturing:
    - Table 6-53 Chemical Production Emission Factors (CH4, CO2, N2O)
    - Material Balance Approach (Equation 6-55)
    """

    TABLE_6_53 = {
        "acrylonitrile": {"ch4": 0.00018, "co2": 1.00, "n2o": 0.0},
        "carbon_black_unabated": {"ch4": 0.0287, "co2": 2.63, "n2o": 0.0},
        "carbon_black_abated": {"ch4": 0.00006, "co2": 2.63, "n2o": 0.0},
        "ethylene_ethane_feed": {"ch4": 0.006, "co2": 0.77, "n2o": 0.0},
        "ethylene_other_feed": {"ch4": 0.003, "co2": 0.77, "n2o": 0.0},
        "ethylene_dichloride": {"ch4": 0.0, "co2": 0.041, "n2o": 0.0},
        "ethylene_oxide_unabated": {"ch4": 0.00179, "co2": 0.46, "n2o": 0.0},
        "ethylene_oxide_abated": {"ch4": 0.00079, "co2": 0.46, "n2o": 0.0},
        "methanol": {"ch4": 0.0023, "co2": 0.67, "n2o": 0.0},
        "nitric_acid_unabated": {"ch4": 0.0, "co2": 0.0, "n2o": 0.009},
        "nitric_acid_nscr": {"ch4": 0.0, "co2": 0.0, "n2o": 0.002},
        "adipic_acid_unabated": {"ch4": 0.0, "co2": 0.0, "n2o": 0.3},
        "adipic_acid_catalytic": {"ch4": 0.0, "co2": 0.0, "n2o": 0.053},
        "adipic_acid_thermal": {"ch4": 0.0, "co2": 0.0, "n2o": 0.013},
    }

    def __init__(self):
        super().__init__("Petrochemical Manufacturing", "Section 6.12")

    def calculate(
        self,
        process_type=None,               # key from TABLE_6_53
        production_tonnes=0.0,
        # Equation 6-55 material balance inputs:
        feedstocks=None,                 # list of (tonnes_feed, c_frac_feed)
        primary_product_tonnes=None,
        primary_product_c_frac=None,
        secondary_products=None,         # list of (tonnes_sec, c_frac_sec)
        uncertainties=None,
        factor_source="API 2021 Table 6-53",
        gwp_dict=None,
        **kwargs,
    ):
        total_ch4 = 0.0
        total_co2 = 0.0
        total_n2o = 0.0

        if feedstocks is not None and primary_product_tonnes is not None:
            c_feed = sum(float(f[0]) * float(f[1]) for f in feedstocks)
            c_primary = float(primary_product_tonnes) * float(primary_product_c_frac or 0.0)
            c_sec = sum(float(s[0]) * float(s[1]) for s in (secondary_products or []))
            c_emitted = max(0.0, c_feed - (c_primary + c_sec))
            total_co2 = c_emitted * (44.0 / 12.0)
        elif process_type is not None:
            pt = str(process_type).lower().strip()
            efs = self.TABLE_6_53.get(pt)
            if not efs:
                for k, v in self.TABLE_6_53.items():
                    if pt in k or k in pt:
                        efs = v
                        break
            if efs:
                prod = float(production_tonnes or 0.0)
                total_ch4 = prod * efs["ch4"]
                total_co2 = prod * efs["co2"]
                total_n2o = prod * efs["n2o"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4, total_co2, total_n2o, uncertainties, factor_source, "petrochemical"
        )
        co2e = calculate_co2e(total_ch4, total_co2, total_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            co2=co2_res or total_co2,
            ch4=ch4_res or total_ch4,
            n2o=n2o_res or total_n2o,
            total_co2e=co2e,
            inputs={"process_type": process_type, "production_tonnes": production_tonnes},
            metadata={"standard": "API Compendium 2021 §6.12", "table": "Table 6-53"},
        )


# ==============================================================================
# §6.14 Fire Suppression Emissions
# ==============================================================================
class FireSuppressionCalculator(BaseCalculator):
    """
    API Compendium 2021 §6.14 - Fire Suppression Emissions:
    - Equation 6-56 Material balance on fire extinguishing agents
    - Supports clean agents: CO2, HFC-227ea (FM-200), HFC-125, HFC-236fa, Halon 1301, FK-5-1-12 (Novec 1230)
    """

    def __init__(self):
        super().__init__("Fire Suppression Emissions", "Section 6.14")

    def calculate(
        self,
        agent_type="hfc_227ea",          # key in FIRE_AGENT_GWPS
        total_charge_kg=0.0,             # total system inventory
        annual_release_rate=0.02,        # r (default 2% annual leakage)
        direct_discharge_kg=0.0,         # discharge during testing or fire suppression events
        uncertainties=None,
        factor_source="API 2021 §6.14",
        gwp_dict=None,
        **kwargs,
    ):
        agent = str(agent_type).lower().strip().replace("-", "_")
        gwp = FIRE_AGENT_GWPS.get(agent, 1.0)

        leakage_kg = float(total_charge_kg or 0.0) * float(annual_release_rate or 0.0)
        total_released_kg = leakage_kg + float(direct_discharge_kg or 0.0)
        total_released_tonnes = total_released_kg / 1000.0

        total_co2 = 0.0
        total_co2e = 0.0

        if agent == "co2":
            total_co2 = total_released_tonnes
            total_co2e = total_co2
        else:
            total_co2e = total_released_tonnes * gwp

        co2_res = (
            propagate_uncertainty(
                total_co2,
                resolve_ef_uncertainty("fire_suppression", "co2", resolve_tier(factor_source), (uncertainties or {}).get("co2")),
                tier=resolve_tier(factor_source),
                process_category="fire_suppression",
                gas="co2",
            )
            if total_co2 > 0
            else None
        )

        return self.format_result(
            co2=co2_res or total_co2,
            ch4=0.0,
            n2o=0.0,
            total_co2e=total_co2e,
            inputs={
                "agent_type": agent,
                "chemical_released_tonnes": total_released_tonnes,
                "gwp": gwp,
            },
            metadata={"standard": "API Compendium 2021 §6.14", "equation": "Eq 6-56"},
        )
