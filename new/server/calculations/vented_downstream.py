"""
API Compendium 2021 - Sections 6.11, 6.12, 6.14: Downstream Refining, Petrochemicals & Fire Suppression
Vented and Process Emissions Calculation Modules (Catalyst Regen, Cokers, H2 Plants, Asphalt, SRU, Petrochem, Fire).
"""

import math
from .base import BaseCalculator
from .units import calculate_co2e, normalize_efficiency
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty

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
    "co2": 1.0, "hfc_227ea": 3220.0, "hfc_125": 3500.0, "hfc_236fa": 9810.0,
    "halon_1301": 7140.0, "fk_5_1_12": 1.0, "other": 1.0,
}


def _given(value, default):
    return float(default) if value is None or value == "" else float(value)


def _parse_fraction(val, default=0.0, name="fraction"):
    if val is None or val == "" or val == "-":
        return default
    try:
        s = str(val).strip()
        has_pct = "%" in s
        v = float(s.replace("%", "").strip())
    except (ValueError, TypeError):
        raise ValueError(f"Invalid numeric value for {name}: {val}")
    if v < 0.0:
        raise ValueError(f"{name} cannot be negative: {val}")
    if has_pct or v > 1.0:
        if v <= 100.0:
            v /= 100.0
        else:
            raise ValueError(f"{name} cannot exceed 100%: {val}")
    return v


def _propagate_results(total_ch4, total_co2, n2o, uncertainties, factor_source="default", category="vented"):
    _tier = resolve_tier(factor_source)
    unc = uncertainties or {}
    def _p(val, gas):
        if val <= 0:
            return None
        return propagate_uncertainty(val, resolve_ef_uncertainty(category, gas, _tier, unc.get(gas)), tier=_tier, process_category=category, gas=gas)
    return _p(total_ch4, "ch4"), _p(total_co2, "co2"), _p(n2o, "n2o")


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
        if approach not in ("coke_burn", "k1_k2_k3", "air_blower", "continuous", "intermittent"):
            raise ValueError(f"Unknown catalyst regeneration approach '{approach}'")

        if approach == "coke_burn":
            annual_coke = 0.0
            if coke_burn_rate_tonnes_yr is not None and coke_burn_rate_tonnes_yr > 0:
                annual_coke = float(coke_burn_rate_tonnes_yr)
            elif coke_burn_rate_tonnes_day is not None and coke_burn_rate_tonnes_day > 0:
                annual_coke = float(coke_burn_rate_tonnes_day) * float(operating_days)
            elif unit_throughput_bbl_day is not None and unit_throughput_bbl_day > 0:
                daily_coke = float(unit_throughput_bbl_day) * (float(coke_burn_off_factor_kg_bbl) * 0.001)
                annual_coke = daily_coke * float(operating_days)
            else:
                raise ValueError("Coke burn approach needs the coke burn rate (per year or per day) or the unit throughput")

            cf = _given(carbon_content_fraction, 0.93)
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
            else:
                raise ValueError("K1 approach (Eq 6-35) needs the flue gas rate (dscm/min or dscf/min)")

        elif approach == "air_blower":
            # percent, as in the K1 approach (a value of 1 or less was read as a fraction: 0.9 % became 90 %,
            # and 0 % became the 11 % / 9 % defaults)
            f_co2 = float(co2_pct or 0.0) / 100.0
            f_co = float(co_pct or 0.0) / 100.0
            total_min = float(8760.0 if operating_hours is None else operating_hours) * 60.0

            if air_rate_m3_min is not None:
                ar = float(air_rate_m3_min) + float(sor_m3_min or 0.0)
                kg_co2 = ar * (f_co2 + f_co) * (44.0 / 23.685) * total_min
                co2_coke = kg_co2 / 1000.0
            elif air_rate_scf_min is not None:
                ar = float(air_rate_scf_min) + float(sor_scf_min or 0.0)
                lb_co2 = ar * (f_co2 + f_co) * (44.0 / 379.3) * total_min
                co2_coke = lb_co2 / LB_PER_TONNE
            else:
                raise ValueError("Air blower approach (Eq 6-36) needs the air rate (m3/min or scf/min)")

        elif approach == "continuous":
            crr = float(catalyst_circulation_rate_tonnes_hr or 0.0)
            h = float(8760.0 if operating_hours is None else operating_hours)
            c_diff = float(fc_spent or 0.0) - float(fc_regen or 0.0)
            co2_coke = crr * h * c_diff * (44.0 / 12.0)

        else:  # intermittent (approaches checked above)
            crr = float(catalyst_inventory_tonnes or 0.0)
            n_cycles = _given(regeneration_cycles_per_yr, 1.0)
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
        co2e = calculate_co2e(co2=total_co2, ch4=total_ch4, n2o=total_n2o, gwp_dict=gwp_dict)

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

        if coker_type not in ("delayed", "fluid"):
            raise ValueError(f"Unknown coker type '{coker_type}': delayed or fluid")
        if coker_type == "delayed":
            n_cycles = _given(num_cycles_per_yr, 1.0)
            if n_cycles < 0:
                raise ValueError("Delayed coker number of cycles cannot be negative")
            m_steam = 0.0
            if steam_mass_tonnes_cycle is not None:
                m_steam = float(steam_mass_tonnes_cycle)
                if m_steam < 0:
                    raise ValueError("Delayed coker steam mass cannot be negative")
            elif vessel_diameter_ft is not None and vessel_height_ft is not None:
                d, h_drum = float(vessel_diameter_ft), float(vessel_height_ft)
                if d <= 0 or h_drum <= 0:
                    raise ValueError("Delayed coker vessel dimensions must be positive")
                h_outage = float(coke_drum_outage_ft or 0.0)
                vessel_area = math.pi * (d ** 2) / 4.0

                m_coke_calculated = float(bulk_density_tonne_cuft) * ((h_drum - h_outage) * vessel_area)

                if water_height_ft is None:  # Eq 6-44 has no default water level
                    raise ValueError("Delayed coker steam (Eq 6-44) needs the water height in the vessel (ft)")
                h_w = float(water_height_ft)
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
                else:  # Eq 6-45 / 6-46: no default initial temperature
                    raise ValueError("Delayed coker steam needs the overhead pressure (Eq 6-46) or the overhead and "
                                     "bottom temperatures (Eq 6-45)")

                delta_t = max(0.0, t_initial - _given(t_final_f, 212.0))
                heat_water = m_water_calculated * float(cp_water)
                heat_coke = m_coke_calculated * float(cp_coke)
                total_heat = (1.0 - _given(f_conv_loss, 0.10)) * (heat_water + heat_coke) * delta_t
                m_steam = total_heat / float(delta_h_vap)
                m_steam_calculated = m_steam
            else:
                raise ValueError("Delayed coker needs the steam per cycle or the vessel diameter and height")

            ef_dcu = _given(dcu_ch4_ef_kg_tonne_steam, 7.9)
            total_ch4 = m_steam * ef_dcu * n_cycles * 0.001

        else:  # fluid (types checked above)
            cf = float(carbon_wt_fraction) if carbon_wt_fraction is not None else 1.0 - _given(hydrogen_wt_fraction, 0.015)
            if coke_burned_lb_yr is not None:
                cb = float(coke_burned_lb_yr)
                if cb < 0:
                    raise ValueError("Coke burned cannot be negative")
                total_co2 = (cb * cf * (44.0 / 12.0)) / LB_PER_TONNE
            elif coke_burned_tonnes_yr is not None:
                cb = float(coke_burned_tonnes_yr)
                if cb < 0:
                    raise ValueError("Coke burned cannot be negative")
                total_co2 = cb * cf * (44.0 / 12.0)
            else:
                raise ValueError("Fluid coker needs the coke burned (lb or tonnes per year)")

        ch4_res, co2_res, _ = _propagate_results(
            total_ch4, total_co2, 0.0, uncertainties, factor_source, "refining_coker"
        )
        co2e = calculate_co2e(co2=total_co2, ch4=total_ch4, n2o=0.0, gwp_dict=gwp_dict)

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

    SPECIES = {  # molecular weight, carbon atoms
        "CH4": (16.04, 1), "C2H6": (30.07, 2), "C3H8": (44.10, 3), "C4H10": (58.12, 4), "C5H12": (72.15, 5),
        "CO": (28.01, 1), "CO2": (44.01, 1), "N2": (28.01, 0), "H2": (2.016, 0),
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
        if method not in ("feedstock_balance", "h2_stoichiometry", "simple_factor"):
            raise ValueError(f"Unknown hydrogen plant method '{method}'")
        unknown = sorted(set(feedstock_comp or {}) - set(self.SPECIES))
        if unknown:
            raise ValueError(f"Unknown feed gas species {unknown}: use {sorted(self.SPECIES)}")

        if method == "feedstock_balance":
            cf = _parse_fraction(feedstock_carbon_fraction, default=None, name="Feedstock carbon fraction") if feedstock_carbon_fraction is not None else None
            fr_tonnes = feedstock_rate_tonnes_yr
            if fr_tonnes is not None and float(fr_tonnes) < 0:
                raise ValueError("Feedstock rate cannot be negative")

            if feedstock_comp is not None and (cf is None or fr_tonnes is None):
                species_data = self.SPECIES
                mix_mw = sum(mol_frac * species_data[k][0] for k, mol_frac in feedstock_comp.items())
                total_c_wt = sum(mol_frac * species_data[k][1] * 12.011 for k, mol_frac in feedstock_comp.items())
                cf = total_c_wt / mix_mw

                if fr_tonnes is None:
                    if feedstock_volume_scf_yr is not None:
                        if float(feedstock_volume_scf_yr) < 0:
                            raise ValueError("Feedstock volume cannot be negative")
                        lbmoles = float(feedstock_volume_scf_yr) / MOLAR_VOL_US
                        lb_feed = lbmoles * mix_mw
                        fr_tonnes = lb_feed / LB_PER_TONNE
                    elif feedstock_volume_m3_yr is not None:
                        if float(feedstock_volume_m3_yr) < 0:
                            raise ValueError("Feedstock volume cannot be negative")
                        kgmoles = float(feedstock_volume_m3_yr) / MOLAR_VOL_METRIC
                        kg_feed = kgmoles * mix_mw
                        fr_tonnes = kg_feed / 1000.0

            if fr_tonnes is None or cf is None:
                raise ValueError("Feedstock balance (Eq 6-49) needs the feedstock rate (tonnes, scf or m3) and its "
                                 "carbon fraction or composition")
            total_co2 = float(fr_tonnes) * float(cf) * (44.0 / 12.0)

        elif method == "h2_stoichiometry":
            ratio = co2_to_h2_molar_ratio
            if ratio is not None and float(ratio) < 0:
                raise ValueError("CO2 to H2 molar ratio cannot be negative")
            if ratio is None and feedstock_comp is not None:
                rxn_h2 = {"CH4": 4.0, "C2H6": 7.0, "C3H8": 10.0, "C4H10": 13.0, "C5H12": 16.0}
                rxn_c = {"CH4": 1.0, "C2H6": 2.0, "C3H8": 3.0, "C4H10": 4.0, "C5H12": 5.0}
                moles_c = sum(feedstock_comp.get(k, 0.0) * rxn_c.get(k, 0.0) for k in rxn_c)
                moles_h2 = sum(feedstock_comp.get(k, 0.0) * rxn_h2.get(k, 0.0) for k in rxn_h2)
                if moles_h2 <= 0:
                    raise ValueError("The feed gas composition has no hydrocarbon to reform (Eq 6-48)")
                ratio = moles_c / moles_h2
            if ratio is None:
                raise ValueError("H2 stoichiometry (Eq 6-50) needs the CO2/H2 molar ratio or the feed composition")

            ratio_val = float(ratio)
            if h2_production_scf_yr is not None:
                if float(h2_production_scf_yr) < 0:
                    raise ValueError("H2 production volume cannot be negative")
                lbmoles_h2 = float(h2_production_scf_yr) / MOLAR_VOL_US
                lb_co2 = lbmoles_h2 * ratio_val * 44.0
                total_co2 = lb_co2 / LB_PER_TONNE
            elif h2_production_m3_yr is not None:
                if float(h2_production_m3_yr) < 0:
                    raise ValueError("H2 production volume cannot be negative")
                kgmoles_h2 = float(h2_production_m3_yr) / MOLAR_VOL_METRIC
                kg_co2 = kgmoles_h2 * ratio_val * 44.0
                total_co2 = kg_co2 / 1000.0
            else:
                raise ValueError("H2 stoichiometry (Eq 6-50) needs the hydrogen produced (scf or m3)")

        else:  # simple_factor (methods checked above)
            if simple_basis not in self.FACTORS_TABLE_6_51:
                raise ValueError(f"Unknown Table 6-51 basis '{simple_basis}': {sorted(self.FACTORS_TABLE_6_51)}")
            ef = self.FACTORS_TABLE_6_51[simple_basis]
            vol = float(simple_volume if simple_volume is not None else (h2_production_scf_yr or 0.0))
            if vol < 0:
                raise ValueError("Hydrogen production or feedstock volume cannot be negative")
            total_co2 = vol * ef
        _, co2_res, _ = _propagate_results(
            0.0, total_co2, 0.0, uncertainties, factor_source, "refining_h2_plant"
        )
        return self.format_result(
            co2=co2_res or total_co2,
            ch4=0.0,
            n2o=0.0,
            total_co2e=total_co2,
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
        "bbl": {"ch4": 5.55e-4, "co2": 1.01e-3}, "m3": {"ch4": 3.49e-3, "co2": 6.38e-3},
        "short_ton": {"ch4": 3.07e-3, "co2": 5.61e-3}, "tonne": {"ch4": 3.38e-3, "co2": 6.19e-3},
    }

    def __init__(self):
        super().__init__("Asphalt Blowing", "Section 6.11.4")

    def calculate(
        self,
        throughput=0.0,
        unit="short_ton",                # "bbl", "m3", "short_ton", "tonne"
        controlled=False,
        destruction_efficiency=0.98,     # DE default 98%
        uncertainties=None,
        factor_source="API 2021 Table 6-52",
        gwp_dict=None,
        **kwargs,
    ):
        q = float(throughput or 0.0)
        if q < 0:
            raise ValueError("Asphalt blowing throughput cannot be negative")
        u = str(unit).strip().lower().replace(" ", "_")
        u = {"short_tons": "short_ton", "us_ton": "short_ton", "tonnes": "tonne", "t": "tonne", "metric_ton": "tonne",
             "barrel": "bbl", "barrels": "bbl"}.get(u, u)
        if u not in self.TABLE_6_52:
            raise ValueError(f"Asphalt blowing throughput unit '{unit}' must be bbl, m3, short_ton or tonne")
        efs = self.TABLE_6_52[u]
        ef_ch4, ef_co2 = efs["ch4"], efs["co2"]

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
        co2e = calculate_co2e(co2=total_co2, ch4=total_ch4, n2o=0.0, gwp_dict=gwp_dict)

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
        green_coke_carbon_fraction=None,     # CCGC, facility measurement (Eq 6-53 has no default)
        calcined_coke_mass_tonnes_yr=0.0,    # PCout
        calcined_coke_carbon_fraction=None,  # CCPC, facility measurement
        dust_collected_tonnes_yr=0.0,        # PCdust
        dust_recycled_tonnes_yr=0.0,
        uncertainties=None,
        factor_source="API 2021 §6.11.5",
        gwp_dict=None,
        **kwargs,
    ):
        gc = float(green_coke_mass_tonnes_yr or 0.0)
        pcout = float(calcined_coke_mass_tonnes_yr or 0.0)
        if gc < 0 or pcout < 0:
            raise ValueError("Coke calcining masses cannot be negative")
        if green_coke_carbon_fraction in (None, "") or calcined_coke_carbon_fraction in (None, ""):
            raise ValueError("Coke calcining (Eq 6-53) needs the carbon fractions of the green and the calcined coke from facility measurements")
        cc_gc = _parse_fraction(green_coke_carbon_fraction, name="Green coke carbon fraction")
        cc_pc = _parse_fraction(calcined_coke_carbon_fraction, name="Calcined coke carbon fraction")
        pcdust = max(0.0, float(dust_collected_tonnes_yr or 0.0) - float(dust_recycled_tonnes_yr or 0.0))

        c_burned = max(0.0, (gc * cc_gc) - ((pcout + pcdust) * cc_pc))
        total_co2 = (44.0 / 12.0) * c_burned

        _, co2_res, _ = _propagate_results(0.0, total_co2, 0.0, uncertainties, factor_source, "coke_calcining")
        return self.format_result(
            co2=co2_res or total_co2, ch4=0.0, n2o=0.0, total_co2e=total_co2,
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
        total_co2, total_ch4 = 0.0, 0.0

        if sour_gas_scf_yr is not None:
            fsg = float(sour_gas_scf_yr)
            if fsg < 0:
                raise ValueError("Sour gas volume cannot be negative")
            if fsg > 0:
                fc = _parse_fraction(carbon_mole_fraction, default=0.20, name="Carbon mole fraction")
                total_co2 = (fsg * (44.0 / MOLAR_VOL_US) * fc) / LB_PER_TONNE
        elif sour_gas_m3_yr is not None:
            fsg = float(sour_gas_m3_yr)
            if fsg < 0:
                raise ValueError("Sour gas volume cannot be negative")
            if fsg > 0:
                fc = _parse_fraction(carbon_mole_fraction, default=0.20, name="Carbon mole fraction")
                total_co2 = (fsg * (44.0 / MOLAR_VOL_METRIC) * fc) / 1000.0

        if refinery_throughput_bbl_yr is not None:
            bbl = float(refinery_throughput_bbl_yr)
            if bbl < 0:
                raise ValueError("Refinery throughput cannot be negative")
            if bbl > 0:
                scf_ch4 = (bbl / 1_000_000.0) * 137_000.0
                total_ch4 = scf_ch4 / MOLAR_VOL_US * MW_CH4 / LB_PER_TONNE

        ch4_res, co2_res, _ = _propagate_results(
            total_ch4, total_co2, 0.0, uncertainties, factor_source, "refining_other_vents"
        )
        co2e = calculate_co2e(co2=total_co2, ch4=total_ch4, n2o=0.0, gwp_dict=gwp_dict)

        return self.format_result(
            co2=co2_res or total_co2, ch4=ch4_res or total_ch4, n2o=0.0, total_co2e=co2e,
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
        total_ch4, total_co2, total_n2o = 0.0, 0.0, 0.0

        if feedstocks is not None and primary_product_tonnes is not None:
            c_feed = 0.0
            for f in feedstocks:
                f_t = float(f[0])
                if f_t < 0:
                    raise ValueError("Feedstock tonnes cannot be negative")
                c_feed += f_t * _parse_fraction(f[1], name="Feedstock carbon fraction")
            p_t = float(primary_product_tonnes)
            if p_t < 0:
                raise ValueError("Primary product tonnes cannot be negative")
            c_primary = p_t * _parse_fraction(primary_product_c_frac, default=0.0, name="Primary product carbon fraction")
            c_sec = 0.0
            for s in (secondary_products or []):
                s_t = float(s[0])
                if s_t < 0:
                    raise ValueError("Secondary product tonnes cannot be negative")
                c_sec += s_t * _parse_fraction(s[1], default=0.0, name="Secondary product carbon fraction")
            c_emitted = max(0.0, c_feed - (c_primary + c_sec))
            total_co2 = c_emitted * (44.0 / 12.0)
        elif process_type is not None:
            pt = str(process_type).lower().strip().replace(" ", "_").replace("-", "_")
            efs = self.TABLE_6_53.get(pt)
            if not efs:  # a partial name picked whichever row came first ("ethylene" -> ethane feedstock)
                raise ValueError(f"Unknown Table 6-53 process '{process_type}': {sorted(self.TABLE_6_53)}")
            prod = float(production_tonnes or 0.0)
            if prod < 0:
                raise ValueError("Production tonnes cannot be negative")
            total_ch4 = prod * efs["ch4"]
            total_co2 = prod * efs["co2"]
            total_n2o = prod * efs["n2o"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4, total_co2, total_n2o, uncertainties, factor_source, "petrochemical"
        )
        co2e = calculate_co2e(co2=total_co2, ch4=total_ch4, n2o=total_n2o, gwp_dict=gwp_dict)

        return self.format_result(
            co2=co2_res or total_co2, ch4=ch4_res or total_ch4, n2o=n2o_res or total_n2o, total_co2e=co2e,
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
        annual_release_rate=None,        # r, fraction released per year (Eq 6-56 has no default)
        direct_discharge_kg=0.0,         # discharge during testing or fire suppression events
        uncertainties=None,
        factor_source="API 2021 §6.14",
        gwp_dict=None,
        **kwargs,
    ):
        agent = str(agent_type).lower().strip().replace("-", "_")
        if agent not in FIRE_AGENT_GWPS:
            raise ValueError(f"Unknown fire suppression agent '{agent_type}': {sorted(FIRE_AGENT_GWPS)}")
        gwp = FIRE_AGENT_GWPS[agent]
        charge, discharge = float(total_charge_kg or 0.0), float(direct_discharge_kg or 0.0)
        if charge < 0 or discharge < 0:
            raise ValueError("Fire suppression agent quantities cannot be negative")
        if charge > 0 and annual_release_rate in (None, ""):
            raise ValueError("Fire suppression leakage (Eq 6-56) needs the fraction of the charge released per year")

        rel_rate = normalize_efficiency(annual_release_rate, default=0.0)
        leakage_kg = charge * rel_rate
        total_released_kg = leakage_kg + discharge
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
