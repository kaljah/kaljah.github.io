"""
Independent Midstream & Stoichiometric Process Models.
Source of Truth: API Compendium 2021 §4.1, §6.5, §6.6, Table 6-5.
Zero production dependencies.
"""
import math
from .unit_conversions import (
    IndependentUnitConverter,
    to_psia,
    to_fahrenheit,
    DENSITY_CH4_STD,
    DENSITY_CO2_STD,
)
from .gwp import IndependentGWPModel


class IndependentAGRModel:
    @staticmethod
    def calculate(
        throughput_mmscf,
        co2_in,
        co2_out=0.001,
        ch4_in=0.85,
        ch4_slip_fraction=0.001,
        control_eff=0.0,
        control_type="vent",
        gwp_standard="AR5",
        gwp_horizon="100",
    ):
        tp_scf = float(throughput_mmscf or 0.0) * 1_000_000.0

        cin = float(co2_in or 0.0)
        if cin > 1.0:
            cin /= 100.0
        cout = float(co2_out if co2_out is not None else 0.001)
        if cout > 1.0:
            cout /= 100.0
        if cout > cin:
            cout = cin

        diff_co2 = max(0.0, cin - cout)
        co2_scf = tp_scf * diff_co2
        co2_m3 = co2_scf * 0.028316846592
        co2_mass_kg = co2_m3 * DENSITY_CO2_STD

        c_ch4 = float(ch4_in or 0.85)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0
        slip = float(ch4_slip_fraction if ch4_slip_fraction is not None else 0.001)
        if slip > 1.0:
            slip /= 100.0

        ch4_slip_scf = tp_scf * c_ch4 * slip
        ch4_slip_m3 = ch4_slip_scf * 0.028316846592
        ch4_mass_kg = ch4_slip_m3 * DENSITY_CH4_STD

        ctrl = float(control_eff or 0.0)
        if ctrl > 1.0:
            ctrl /= 100.0
        ctrl = max(0.0, min(1.0, ctrl))

        ctype = str(control_type or "vent").strip().lower()
        if ctype in ["agi", "ccus", "injection", "sequestration"]:
            co2_emitted_kg = co2_mass_kg * (1.0 - ctrl)
            ch4_emitted_kg = ch4_mass_kg * (1.0 - ctrl)
        elif ctype in ["claus", "thermal_oxidizer", "incinerator", "flare", "combustor"]:
            ch4_destroyed_kg = ch4_mass_kg * ctrl
            combusted_co2_kg = ch4_destroyed_kg * (44.01 / 16.04)
            co2_emitted_kg = co2_mass_kg + combusted_co2_kg
            ch4_emitted_kg = ch4_mass_kg * (1.0 - ctrl)
        else:
            co2_emitted_kg = co2_mass_kg * (1.0 - ctrl)
            ch4_emitted_kg = ch4_mass_kg * (1.0 - ctrl)

        co2_t = co2_emitted_kg / 1000.0
        ch4_t = ch4_emitted_kg / 1000.0
        n2o_t = 0.0

        co2e = IndependentGWPModel.calculate_co2e(co2=co2_t, ch4=ch4_t, n2o=n2o_t, standard=gwp_standard, horizon=gwp_horizon)
        return {"co2": co2_t, "ch4": ch4_t, "n2o": n2o_t, "co2e": co2e}


class IndependentDehydratorModel:
    @staticmethod
    def calculate_tier1(throughput_mmscf, control_eff=0.0, gwp_standard="AR5", gwp_horizon="100"):
        tp = float(throughput_mmscf or 0.0)
        ctrl = float(control_eff or 0.0)
        if ctrl > 1.0:
            ctrl /= 100.0
        ctrl = max(0.0, min(1.0, ctrl))

        default_ef = 0.266 * (1.0 - ctrl)
        ch4_t = tp * default_ef
        co2e = IndependentGWPModel.calculate_co2e(ch4=ch4_t, standard=gwp_standard, horizon=gwp_horizon)
        return {"ch4": ch4_t, "co2": 0.0, "n2o": 0.0, "co2e": co2e}

    @staticmethod
    def calculate_tier3(
        pump_rate,
        pump_unit="gph",
        hours=8760.0,
        ch4_content=0.85,
        contactor_press=800.0,
        press_unit="psig",
        contactor_temp=100.0,
        temp_unit="F",
        has_flash_tank=True,
        control_eff=0.0,
        flash_control_eff=0.0,
        still_control_type="none",
        flash_control_type="none",
        gwp_standard="AR5",
        gwp_horizon="100",
    ):
        rate_gph = IndependentUnitConverter.convert(pump_rate, pump_unit, "gal/hr") if pump_unit != "gph" else float(pump_rate or 0.0)
        h = float(hours or 8760.0)
        c1 = float(ch4_content or 0.85)
        if c1 > 1.0:
            c1 /= 100.0

        p_psia = to_psia(contactor_press, press_unit)
        t_f = to_fahrenheit(contactor_temp, temp_unit)

        # Henry's Law correlation for TEG: S = 0.0032 * (P_psia)^0.96 * exp(-0.0022 * (T_F - 60)) * X_CH4
        p_term = math.pow(max(14.7, p_psia), 0.96)
        t_term = math.exp(-0.0022 * (t_f - 60.0))
        solubility_scf_gal = 0.0032 * p_term * t_term * c1

        total_ch4_scf = rate_gph * solubility_scf_gal * h

        still_eff = float(control_eff or 0.0)
        if still_eff > 1.0:
            still_eff /= 100.0
        flash_eff = float(flash_control_eff or 0.0)
        if flash_eff > 1.0:
            flash_eff /= 100.0

        stype = str(still_control_type or "").strip().lower()
        if still_eff == 0.0:
            if stype in ["flare", "combustor"]:
                still_eff = 0.98
            elif stype == "thermal_oxidizer":
                still_eff = 0.99
            elif stype == "condenser":
                still_eff = 0.75
            elif stype == "vru":
                still_eff = 0.95

        still_is_comb = stype in ("flare", "combustor", "thermal_oxidizer", "incinerator")
        ftype = str(flash_control_type or "").strip().lower()
        flash_is_comb = ftype in ("flare", "combustor", "thermal_oxidizer", "incinerator")

        if has_flash_tank:
            flash_gas_scf = total_ch4_scf * 0.80
            still_gas_scf = total_ch4_scf * 0.20
            ch4_emitted_scf = (flash_gas_scf * (1.0 - flash_eff)) + (still_gas_scf * (1.0 - still_eff))
            ch4_comb_scf = (still_gas_scf * still_eff if still_is_comb else 0.0) + (flash_gas_scf * flash_eff if flash_is_comb else 0.0)
        else:
            ch4_emitted_scf = total_ch4_scf * (1.0 - still_eff)
            ch4_comb_scf = (total_ch4_scf * still_eff) if still_is_comb else 0.0

        ch4_m3 = ch4_emitted_scf * 0.028316846592
        ch4_t = (ch4_m3 * DENSITY_CH4_STD) / 1000.0

        if ch4_comb_scf > 0:
            ch4_comb_m3 = ch4_comb_scf * 0.028316846592
            ch4_comb_t = (ch4_comb_m3 * DENSITY_CH4_STD) / 1000.0
            co2_comb_t = ch4_comb_t * (44.01 / 16.04)
        else:
            co2_comb_t = 0.0

        co2e = IndependentGWPModel.calculate_co2e(co2=co2_comb_t, ch4=ch4_t, n2o=0.0, standard=gwp_standard, horizon=gwp_horizon)
        return {
            "ch4": ch4_t,
            "co2": co2_comb_t,
            "n2o": 0.0,
            "co2e": co2e,
            "solubility_scf_gal": solubility_scf_gal,
            "total_ch4_scf": total_ch4_scf,
        }


class IndependentStoichiometryModel:
    @staticmethod
    def calculate(fuel_mass, mass_unit="kg", carbon_content=0.85, gwp_standard="AR5", gwp_horizon="100"):
        mass_kg = IndependentUnitConverter.convert(fuel_mass, mass_unit, "kg")
        c = float(carbon_content or 0.85)
        if c > 1.0:
            c /= 100.0

        ratio = 44.01 / 12.011
        co2_kg = mass_kg * c * ratio
        co2_t = co2_kg / 1000.0
        co2e = IndependentGWPModel.calculate_co2e(co2=co2_t, ch4=0.0, n2o=0.0, standard=gwp_standard, horizon=gwp_horizon)
        return {"co2": co2_t, "ch4": 0.0, "n2o": 0.0, "co2e": co2e, "mass_kg": mass_kg}
