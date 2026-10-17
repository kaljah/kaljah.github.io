"""
API Compendium 2021 - Sections 6.7 & 6.8: LNG Operations & Natural Gas Distribution
Vented and Process Emissions Calculation Modules

Governing Standard:
API Compendium of Greenhouse Gas Emissions Methodologies for the Oil and Natural Gas Industry
4th Edition, November 2021:
- §6.7 LNG Operations:
    * §6.7.1 Gas Treatment & Liquefaction Processes
    * §6.7.2 LNG Storage and Loading Operations (Table 6-44 BOG pipeline transfer loss rates)
    * §6.7.3 LNG Shipping
    * §6.7.4 LNG Import and Export Terminals
- §6.8 Natural Gas Distribution:
    * §6.8.1 Natural Gas-Driven Pneumatic Controllers (Table 6-45)
    * §6.8.2 Distribution Non-Routine Releases (Table 6-46, Exhibit 6-34):
      - M&R Station blowdowns
      - Odorizer and sampling vents
      - Distribution pipeline blowdowns (mains & services)
      - Distribution pipeline mishaps (dig-ins)
      - Distribution pressure relief valves (PRVs)
"""

from .base import BaseCalculator
from .units import convert, calculate_co2e, normalize_efficiency
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
)

MOLAR_VOL_US = 379.3   # scf / lb-mole
MW_CH4 = 16.04
MW_CO2 = 44.01
MW_N2O = 44.013
LB_PER_TONNE = 2204.6226218487757


def _split_vent_flare(total_gas_m3, ch4_tonnes, co2_tonnes, ctrl_eff=0.0, hhv=1020.0, ef_n2o=None, destruction_eff=None, control_type="flare"):
    ctrl = normalize_efficiency(ctrl_eff, default=0.0)
    vented_frac = 1.0 - ctrl

    vented_ch4 = ch4_tonnes * vented_frac
    vented_co2 = co2_tonnes * vented_frac

    flared_co2 = 0.0
    flared_unburnt_ch4 = 0.0
    flared_n2o = 0.0

    c_type = str(control_type or "flare").lower().strip()
    is_vru = c_type in ("vru", "recovery", "vapor_recovery", "vapor_recovery_unit")

    if ctrl > 0 and not is_vru:
        flared_ch4_mass = ch4_tonnes * ctrl
        flared_native_co2 = co2_tonnes * ctrl

        de = normalize_efficiency(destruction_eff, default=0.98) if destruction_eff is not None else 0.98
        slip = max(0.0, 1.0 - de)
        flared_ch4_combusted = flared_ch4_mass * de
        flared_co2 = (flared_ch4_combusted * (MW_CO2 / MW_CH4)) + flared_native_co2
        flared_unburnt_ch4 = flared_ch4_mass * slip

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


def _propagate_results(total_ch4, total_co2, flared_n2o, uncertainties, factor_source="default", category="vented"):
    _tier = resolve_tier(factor_source)
    ch4_res = propagate_uncertainty(
        total_ch4,
        resolve_ef_uncertainty(category, "ch4", _tier, (uncertainties or {}).get("ch4")),
        tier=_tier,
        process_category=category,
        gas="ch4",
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
            flared_n2o,
            resolve_ef_uncertainty(category, "n2o", _tier, (uncertainties or {}).get("n2o")),
            tier=_tier,
            process_category=category,
            gas="n2o",
        )
        if flared_n2o > 0
        else None
    )
    return ch4_res, co2_res, n2o_res


# ==============================================================================
# §6.7 LNG Operations
# ==============================================================================
from calculations.vented_midstream import _count, _pick, _route  # noqa: E402


def _parse_content(ch4, co2, default_ch4=0.95):
    def _extract(v, d):
        if v in (None, "", "-"):
            return d, False, False
        s = str(v).strip()
        has_pct = "%" in s
        val = float(s.replace("%", "").strip())
        return val, has_pct, True

    v_ch4, pct_ch4, has_ch4 = _extract(ch4, default_ch4)
    v_co2, pct_co2, has_co2 = _extract(co2, 0.0)

    in_pct = (has_ch4 and not pct_ch4 and v_ch4 > 1.0) or (has_co2 and not pct_co2 and v_co2 > 1.0)
    c_ch4 = (v_ch4 / 100.0) if (pct_ch4 or (in_pct and has_ch4 and v_ch4 > 0)) else v_ch4
    c_co2 = (v_co2 / 100.0) if (pct_co2 or (in_pct and has_co2 and v_co2 > 0)) else v_co2

    if c_ch4 < 0:
        raise ValueError(f"ch4_content cannot be negative: {c_ch4}")
    if c_co2 < 0:
        raise ValueError(f"co2_content cannot be negative: {c_co2}")
    if (c_ch4 + c_co2) > 1.0001:
        raise ValueError(f"Sum of CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) cannot exceed 100%")
    return c_ch4, c_co2


class LNGVentingCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.7 - LNG Operations
    Supports:
      - Table 6-44 Typical Pipeline Loss Rates of Boil-Off Gas (BOG):
          * Foam insulation: 0.0012% per km transfer pipe
          * Powder insulation: 0.0006% per km transfer pipe
          * Vacuum insulation: 0.00012% per km transfer pipe
      - Direct BOG venting / flaring / recovery during ship loading/unloading
      - LNG storage station peak-shaving blowdowns
    """

    TABLE_6_44_LOSS_RATE = {
        "foam": 0.000012,    # 0.0012% per km
        "powder": 0.000006,  # 0.0006% per km
        "vacuum": 0.0000012, # 0.00012% per km
    }

    def __init__(self):
        super().__init__("LNG Vented Emissions", "Section 6.7")

    def calculate(
        self,
        activity="loading_transfer",  # "loading_transfer", "direct_bog_vent", "peak_shaving_blowdown"
        # Table 6-44 Pipeline transfer inputs
        transfer_volume_m3=None,      # liquid LNG transferred
        transfer_volume_bbl=None,
        pipe_length_km=1.0,
        insulation_type="foam",       # "foam", "powder", "vacuum"
        # Direct volume inputs
        vented_gas_scf=None,
        vented_gas_m3=None,
        # Gas composition: section 6.7 converts LNG losses at 95 mol % CH4 (the 98 % / 0.1 % CO2 defaults had no source)
        ch4_content=None,
        co2_content=None,
        control_efficiency=None,
        disposition="vented",
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        act = str(activity or "loading_transfer").lower().strip()
        if act not in ("loading_transfer", "direct_bog_vent", "peak_shaving_blowdown"):
            raise ValueError(f"Unknown LNG activity '{activity}': loading_transfer, direct_bog_vent or peak_shaving_blowdown")

        c_ch4, c_co2 = _parse_content(ch4_content, co2_content, default_ch4=0.95)

        total_gas_scf = 0.0

        if act == "loading_transfer":
            if transfer_volume_m3 is not None:
                v_lng_m3 = float(transfer_volume_m3)
            elif transfer_volume_bbl is not None:
                v_lng_m3 = float(transfer_volume_bbl) * 0.1589873
            else:
                raise ValueError("transfer_volume_m3 or transfer_volume_bbl must be provided")
            if v_lng_m3 < 0:
                raise ValueError(f"transfer_volume cannot be negative: {v_lng_m3}")

            _, loss_rate_per_km = _pick(self.TABLE_6_44_LOSS_RATE, insulation_type or "foam", "pipe insulation")
            l_km = _count(pipe_length_km)  # 0 km is 0 (it was 1 km; any length took at least 10 m)

            # Liquid LNG loss volume (m3)
            lng_lost_m3 = v_lng_m3 * loss_rate_per_km * l_km
            # liquid to gas: section 6.7 describes LNG as "more than 600" times smaller than the gas
            gas_lost_m3 = lng_lost_m3 * 600.0
            total_gas_scf = convert(gas_lost_m3, "m3", "scf")

        else:
            if vented_gas_scf is not None:
                total_gas_scf = float(vented_gas_scf)
            elif vented_gas_m3 is not None:
                total_gas_scf = convert(float(vented_gas_m3), "m3", "scf")
            else:
                raise ValueError("vented_gas_scf or vented_gas_m3 must be provided")
            if total_gas_scf < 0:
                raise ValueError(f"vented_gas cannot be negative: {total_gas_scf}")

        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        gross_ch4_tonnes = total_gas_scf * c_ch4 * (MW_CH4 / MOLAR_VOL_US) / LB_PER_TONNE
        gross_co2_tonnes = total_gas_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        # a flare keeps its entered efficiency (it was 100 %, every entry ignored), else 98 %
        disp, eff, de, gross_ch4_tonnes, gross_co2_tonnes = _route(disposition, control_efficiency, gross_ch4_tonnes,
                                                               gross_co2_tonnes)

        split = _split_vent_flare(total_gas_m3, gross_ch4_tonnes, gross_co2_tonnes, ctrl_eff=eff, destruction_eff=de)
        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=split["flared_n2o"],
            uncertainties=uncertainties,
            factor_source="API_Section_6.7",
            category="lng_venting",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=split["flared_n2o"], gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"activity": act, "total_gas_scf": total_gas_scf, "total_gas_m3": total_gas_m3},
            metadata={"standard": "API Compendium 2021 Section 6.7", "tables": "Table 6-44"},
        )


# ==============================================================================
# §6.8 Natural Gas Distribution
# ==============================================================================
class DistributionPneumaticsCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.8.1 - Gas-Driven Pneumatic Controllers in Distribution
    Table 6-45:
      - Pneumatic isolation valves: 0.366 tonnes CH4/controller-yr (2.33 scf gas/hr)
      - Pneumatic control loops: 3.465 tonnes CH4/controller-yr (21.84 scf gas/hr)
      - Distribution average: 2.941 tonnes CH4/controller-yr (18.44 scf gas/hr)
      - Industrial meter regulator venting: 3.847 tonnes CH4/controller-yr (24.51 scf gas/hr)
    """

    TABLE_6_45 = {
        "isolation_valves": {"ef_tonnes_ch4": 0.366, "scf_gas_hr": 2.33, "baseline_ch4_mol": 0.934},
        "control_loops": {"ef_tonnes_ch4": 3.465, "scf_gas_hr": 21.84, "baseline_ch4_mol": 0.944},
        "average": {"ef_tonnes_ch4": 2.941, "scf_gas_hr": 18.44, "baseline_ch4_mol": 0.949},
        "industrial_meter_regulator": {"ef_tonnes_ch4": 3.847, "scf_gas_hr": 24.51, "baseline_ch4_mol": 0.934},
    }

    def __init__(self):
        super().__init__("Distribution Pneumatics", "Section 6.8.1")

    def calculate(
        self,
        controller_type="average",  # "isolation_valves", "control_loops", "average", "industrial_meter_regulator"
        controller_count=1.0,
        ch4_content=None,
        co2_content=0.0,
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        n = _count(controller_count)  # 0 controllers is 0 (it was 1)
        ctype, factor_info = _pick(self.TABLE_6_45, "average" if str(controller_type or "").lower().strip() in ("", "unknown")
                                   else controller_type, "distribution controller type")

        c_ch4, c_co2 = _parse_content(ch4_content, co2_content, default_ch4=factor_info["baseline_ch4_mol"])

        gross_ch4_tonnes = n * factor_info["ef_tonnes_ch4"] * (c_ch4 / factor_info["baseline_ch4_mol"])
        total_gas_scf = n * factor_info["scf_gas_hr"] * 8760.0
        gross_co2_tonnes = total_gas_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=gross_ch4_tonnes,
            total_co2=gross_co2_tonnes,
            flared_n2o=0.0,
            uncertainties=uncertainties,
            factor_source="API_Table_6_45",
            category="distribution_pneumatics",
        )

        total_co2e = calculate_co2e(ch4=gross_ch4_tonnes, co2=gross_co2_tonnes, n2o=0.0, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"controller_type": ctype, "controller_count": n, "gross_ch4_tonnes": gross_ch4_tonnes},
            metadata={"standard": "API Compendium 2021 Section 6.8.1", "table": "Table 6-45"},
        )


class DistributionNonRoutineCalculator(BaseCalculator):
    """
    API Compendium 2021 Section 6.8.2 - Gas Distribution Non-Routine Releases
    Table 6-46 & Exhibit 6-34:
      - M&R Station blowdowns: 0.002895 tonnes CH4/station-yr (159 scf gas/yr)
      - Odorizer & gas sampling vents: 0.02275 tonnes CH4/station-yr (1,251 scf gas/yr)
      - Distribution pipeline blowdowns: 0.03220 tonnes CH4/mile-yr (1,798 scf gas/mile-yr)
      - Distribution pipeline mishaps (dig-ins): 0.03040 tonnes CH4/mile-yr (1,697 scf gas/mile-yr)
      - Pressure relief valves: 9.591e-4 tonnes CH4/mile-yr (53.5 scf gas/mile-yr)
    Verified against Exhibit 6-34.
    """

    TABLE_6_46 = {
        "mr_station_blowdown": {"ef_tonnes_ch4": 0.002895, "scf_gas": 159.0, "baseline_ch4_mol": 0.948},
        "odorizer_sampling": {"ef_tonnes_ch4": 0.02275, "scf_gas": 1251.0, "baseline_ch4_mol": 0.948},
        "pipeline_blowdown": {"ef_tonnes_ch4": 0.03220, "scf_gas": 1798.0, "baseline_ch4_mol": 0.934},
        "pipeline_dig_in": {"ef_tonnes_ch4": 0.03040, "scf_gas": 1697.0, "baseline_ch4_mol": 0.934},
        "prv_releases": {"ef_tonnes_ch4": 9.591e-4, "scf_gas": 53.5, "baseline_ch4_mol": 0.934},
    }

    def __init__(self):
        super().__init__("Distribution Non-Routine Releases", "Section 6.8.2")

    def calculate(
        self,
        activity="mr_station_blowdown",  # "mr_station_blowdown", "odorizer_sampling", "pipeline_blowdown", "pipeline_dig_in", "prv_releases"
        count_or_miles=1.0,
        ch4_content=None,
        co2_content=0.0,
        control_efficiency=None,
        disposition="vented",
        uncertainties=None,
        gwp_dict=None,
    ):
        uncertainties = uncertainties or {}
        act, factor_info = _pick(self.TABLE_6_46, activity or "mr_station_blowdown", "Table 6-46 activity")
        n = _count(count_or_miles)  # 0 stations / miles is 0 (it was 1)

        c_ch4, c_co2 = _parse_content(ch4_content, co2_content, default_ch4=factor_info["baseline_ch4_mol"])

        # Exhibit 6-34 multiplies directly by count/miles
        gross_ch4_tonnes = n * factor_info["ef_tonnes_ch4"] * (c_ch4 / factor_info["baseline_ch4_mol"])
        total_gas_scf = n * factor_info["scf_gas"]
        gross_co2_tonnes = total_gas_scf * c_co2 * (MW_CO2 / MOLAR_VOL_US) / LB_PER_TONNE
        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        disp, eff, de, gross_ch4_tonnes, gross_co2_tonnes = _route(disposition, control_efficiency, gross_ch4_tonnes,
                                                               gross_co2_tonnes)

        split = _split_vent_flare(total_gas_m3, gross_ch4_tonnes, gross_co2_tonnes, ctrl_eff=eff, destruction_eff=de)
        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]

        ch4_res, co2_res, n2o_res = _propagate_results(
            total_ch4=total_ch4,
            total_co2=total_co2,
            flared_n2o=split["flared_n2o"],
            uncertainties=uncertainties,
            factor_source="API_Table_6_46",
            category="distribution_non_routine",
        )

        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=split["flared_n2o"], gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"activity": act, "count_or_miles": n, "gross_ch4_tonnes": gross_ch4_tonnes},
            metadata={"standard": "API Compendium 2021 Section 6.8.2", "table": "Table 6-46", "exhibit": "Exhibit 6-34"},
        )
