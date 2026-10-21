"""
API Compendium 2021 - Section 6.2: Oil and Natural Gas Exploration
Vented and Process Emissions Calculation Modules

Governing Standard:
API Compendium of Greenhouse Gas Emissions Methodologies for the Oil and Natural Gas Industry
4th Edition, November 2021, Section 6.2:
- §6.2.1 Well Drilling (Table 6-2, Table 6-3, Exhibit 6-1)
- §6.2.2 Well Testing (Equation 6-1, Equation 6-2, Equation 6-3, Table 6-4, Exhibit 6-2)
- §6.2.3 Well Completions (Table 6-5, Table 6-6, Table 6-7, Equation 6-4, Equation 6-5, Equation 6-6, Equation 6-7, Exhibit 6-3)
- §6.2.4 Coal Seam Exploratory Drilling and Well Testing (Exhibit 6-5)
"""

from .base import BaseCalculator
from .vented_production import _split_vent_flare  # noqa: F401  (one flare split)
from .units import convert, calculate_co2e
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
)
from .constants import get_active_gwp

# Standard molar volume conversions
MOLAR_VOL_US = 379.3  # scf / lb-mole at 60°F, 14.696 psia
MOLAR_VOL_SI = 23.685  # Sm³ / kg-mole at 15.56°C, 101.325 kPa
MW_CH4 = 16.04
MW_CO2 = 44.01
MW_C = 12.011
LB_PER_TONNE = 2204.6226218487757
_M3_SCF, _M3_BBL = convert(1.0, "m3", "scf"), convert(1.0, "m3", "bbl")
_GAS_SCF = {"scf": 1.0, "mscf": 1e3, "mcf": 1e3, "mmscf": 1e6, "m3": _M3_SCF, "sm3": _M3_SCF}
_RATE_SCF_DAY = {"scf/day": 1.0, "scf/d": 1.0, "scfd": 1.0, "mscf/day": 1e3, "mcf/day": 1e3, "mmscf/day": 1e6,
                 "scf/hr": 24.0, "scf/hour": 24.0, "m3/day": _M3_SCF, "sm3/day": _M3_SCF, "m3/hr": 24 * _M3_SCF,
                 "sm3/hr": 24 * _M3_SCF}
_GOR_SCF_BBL = {"scf/bbl": 1.0, "m3/m3": _M3_SCF / _M3_BBL, "sm3/m3": _M3_SCF / _M3_BBL}
_OIL_BBL_DAY = {"bbl/day": 1.0, "m3/day": _M3_BBL, "sm3/day": _M3_BBL}


def _per(table, unit, default, what):
    """Factor of a unit in its table; an unknown unit was read as the default unit."""
    u = str(unit or default).lower().strip()
    if u not in table:
        raise ValueError(f"Unknown {what} unit '{unit}' ({', '.join(table)})")
    return table[u]


def _parse_testing_composition(ch4_content, co2_content):
    c_ch4 = 0.816
    if ch4_content is not None:
        s_ch4 = str(ch4_content).strip()
        c_ch4 = float(s_ch4.replace("%", "").strip())
        if "%" in s_ch4 or c_ch4 > 1.0:
            c_ch4 /= 100.0
        if c_ch4 < 0.0 or c_ch4 > 1.0:
            raise ValueError(f"ch4_content must be between 0 and 1 (or 0% to 100%): {ch4_content}")

    c_co2 = 0.0
    if co2_content is not None:
        s_co2 = str(co2_content).strip()
        c_co2 = float(s_co2.replace("%", "").strip())
        if "%" in s_co2 or c_co2 > 1.0:
            c_co2 /= 100.0
        if c_co2 < 0.0 or c_co2 > 1.0:
            raise ValueError(f"co2_content must be between 0 and 1 (or 0% to 100%): {co2_content}")

    if (c_ch4 + c_co2) > 1.0001:
        raise ValueError(f"Sum of CH4 ({c_ch4*100:.1f}%) and CO2 ({c_co2*100:.1f}%) cannot exceed 100%")
    return c_ch4, c_co2


class WellTestingCalculator(BaseCalculator):
    """
    API Compendium 2021 - Section 6.2.2: Well Testing Emissions

    Covers gas well and oil well testing:
      - Tier 1: Table 6-4 Default emission factors
          * Gas Well Testing: 0.728 tonnes CH4 / well test (46,625 scf whole gas at 81.6 mol% CH4)
          * Oil Well Testing: 0.057 tonnes CH4 / well test (3,613 scf whole gas at 81.6 mol% CH4)
      - Tier 2:
          * Gas Well Testing (Equation 6-1): V_WT = V_P * T
          * Oil Well Testing (Equation 6-3): V_WT = GOR * PR * T
      - Tier 3:
          * Metered total vent volume V_std and GC composition (Equation 6-2):
            E_x = VR * F_x * (MW_x / Molar_Volume)
      - Fate / Routing:
          * Vented: 100% directly emitted
          * Flared: Stoichiometric flaring (98% combustion, unburnt CH4, native CO2, N2O)
          * Recovered: 0% emitted (captured to pipeline/sales)
    """

    TABLE_6_4_DEFAULT = {
        "gas_well": {
            "ef_ch4_tonnes": 0.7288,  # 728.8 kg CH4 / well test
            "whole_gas_scf": 46625.0,
            "baseline_ch4_pct": 81.6,
            "uncertainty": {"ch4": 0.30, "co2": 0.30},
        },
        "oil_well": {
            "ef_ch4_tonnes": 0.0565,  # 56.5 kg CH4 / well test
            "whole_gas_scf": 3613.0,
            "baseline_ch4_pct": 81.6,
            "uncertainty": {"ch4": 0.30, "co2": 0.30},
        },
    }

    def __init__(self):
        super().__init__("Well Testing", "Section 6.2.2")

    def calculate(
        self,
        tier=None,
        well_type="oil_well",  # "gas_well" or "oil_well"
        events=1.0,
        test_duration_hours=None,
        test_duration_days=None,
        gas_production_rate=None,  # scf/day or Sm3/day (for gas well)
        rate_unit="scf/day",
        oil_production_rate=None,  # bbl/day or m3/day (for oil well)
        oil_rate_unit="bbl/day",
        oil_production_total=None,  # total bbl tested
        gor=None,  # scf gas / bbl oil or Sm3/m3
        gor_unit="scf/bbl",
        measured_gas_volume=None,  # Tier 3 direct volume
        volume_unit="scf",
        ch4_content=None,  # mole fraction or % (default 81.6%)
        co2_content=None,  # mole fraction or %
        control_efficiency=0.0,  # flaring efficiency
        disposition="vented",  # "vented", "flared", "recovered"
        frac_vented=None,
        frac_flared=None,
        frac_recovered=None,
        hhv=1020.0,
        ef_n2o=None,
        uncertainties=None,
        gwp_dict=None,
        **kwargs,
    ):
        uncertainties = uncertainties or {}
        gwp_dict = gwp_dict or get_active_gwp()

        # Parse well type
        wt = str(well_type or "oil_well").lower().strip()
        if ("gas" in wt) == ("oil" in wt):  # it was read as an oil well
            raise ValueError(f"Unknown well type '{well_type}' (gas_well or oil_well)")
        is_gas_well = "gas" in wt
        well_key = "gas_well" if is_gas_well else "oil_well"

        # Normalize duration
        duration_days = 0.0
        if test_duration_days is not None and float(test_duration_days) > 0:
            duration_days = float(test_duration_days)
        elif test_duration_hours is not None and float(test_duration_hours) > 0:
            duration_days = float(test_duration_hours) / 24.0

        if events is not None and float(events) < 0:
            raise ValueError(f"Number of events cannot be negative: {events}")
        num_events = float(1.0 if events is None else events)

        # Gas composition parsing
        c_ch4, c_co2 = _parse_testing_composition(ch4_content, co2_content)

        # Determine calculation tier
        raw_tier = str(tier or kwargs.get("calculation_tier") or "").lower().strip()
        if not raw_tier:
            if measured_gas_volume is not None and float(measured_gas_volume) > 0:
                raw_tier = "tier3"
            elif (is_gas_well and gas_production_rate is not None and duration_days > 0) or (
                not is_gas_well and gor is not None and (oil_production_rate is not None or oil_production_total is not None)
            ):
                raw_tier = "tier2"
            else:
                raw_tier = "tier1"

        total_gas_scf = 0.0
        calculation_equation = ""

        # --- TIER 3: DIRECT METERED VOLUME ---
        if raw_tier in ["tier3", "tier_3", "direct_measurement", "measurement"]:
            if measured_gas_volume is None or float(measured_gas_volume) < 0:
                raise ValueError("Tier 3 well testing requires non-negative measured_gas_volume")
            total_gas_scf = float(measured_gas_volume) * _per(_GAS_SCF, volume_unit, "scf", "gas volume")
            calculation_equation = "Equation 6-2 (Direct Metered Volume)"

        # --- TIER 2: ENGINEERING CALCULATION ---
        elif raw_tier in ["tier2", "tier_2", "engineering", "engineering_estimate"]:
            if is_gas_well:
                # API Equation 6-1: V_WT = V_P * T
                if gas_production_rate is None or float(gas_production_rate) < 0:
                    raise ValueError("Gas well testing Tier 2 requires non-negative gas_production_rate")
                if duration_days <= 0:
                    raise ValueError("Gas well testing Tier 2 requires positive duration (days or hours)")
                g_rate_scf_day = float(gas_production_rate) * _per(_RATE_SCF_DAY, rate_unit, "scf/day", "gas rate")
                total_gas_scf = g_rate_scf_day * duration_days * num_events
                calculation_equation = "Equation 6-1 (Gas Well Testing: V_WT = V_P * T)"
            else:
                # API Equation 6-3: V_WT = GOR * PR * T (or GOR * total_oil)
                if gor is None or float(gor) < 0:
                    raise ValueError("Oil well testing Tier 2 requires non-negative GOR")
                gor_scf_bbl = float(gor) * _per(_GOR_SCF_BBL, gor_unit, "scf/bbl", "GOR")
                if oil_production_total is not None and float(oil_production_total) > 0:
                    total_oil_bbl = float(oil_production_total)
                elif oil_production_rate is not None and float(oil_production_rate) > 0:
                    if duration_days <= 0:
                        raise ValueError("Oil well testing requires positive duration when using production rate")
                    pr_val = float(oil_production_rate) * _per(_OIL_BBL_DAY, oil_rate_unit, "bbl/day", "oil rate")
                    total_oil_bbl = pr_val * duration_days
                else:
                    raise ValueError("Oil well testing Tier 2 requires oil_production_rate or oil_production_total")

                total_gas_scf = gor_scf_bbl * total_oil_bbl * num_events
                calculation_equation = "Equation 6-3 (Oil Well Testing: V_WT = GOR * PR * T)"

        # --- TIER 1: DEFAULT EMISSION FACTORS ---
        else:
            default_entry = self.TABLE_6_4_DEFAULT[well_key]
            whole_gas_per_event = default_entry["whole_gas_scf"]
            total_gas_scf = whole_gas_per_event * num_events
            calculation_equation = "Table 6-4 (Default Well Testing Emission Factors)"

        total_gas_m3 = convert(total_gas_scf, "scf", "m3")

        # Mass conversion using API Equation 6-2:
        gross_ch4_tonnes = (total_gas_scf / MOLAR_VOL_US) * c_ch4 * MW_CH4 / LB_PER_TONNE
        gross_co2_tonnes = (total_gas_scf / MOLAR_VOL_US) * c_co2 * MW_CO2 / LB_PER_TONNE

        # Routing & Disposition logic:
        ctrl_eff = 0.0
        disp = str(disposition or "").lower().strip()
        if frac_vented is not None or frac_flared is not None or frac_recovered is not None:
            f_vent, f_flare, f_rec = float(frac_vented or 0.0), float(frac_flared or 0.0), float(frac_recovered or 0.0)
            tot_f = f_vent + f_flare + f_rec
            if tot_f > 1.0001:
                raise ValueError(f"Sum of disposition fractions ({tot_f:.3f}) cannot exceed 1.0")
            unrec_f = f_vent + f_flare
            ctrl_eff = (f_flare / unrec_f) if unrec_f > 0 else 0.0
            gross_ch4_tonnes *= unrec_f
            gross_co2_tonnes *= unrec_f
            total_gas_m3 *= unrec_f
        elif disp == "flared":
            ctrl_eff = 1.0
        elif disp in ["recovered", "rec", "sales"]:
            ctrl_eff = 0.0
            gross_ch4_tonnes = gross_co2_tonnes = total_gas_m3 = 0.0
        elif disp in ("", "vented", "vent"):
            ctrl_eff = float(control_efficiency or 0.0)
        else:  # it was read as vented
            raise ValueError(f"Unknown disposition '{disposition}' (vented, flared or recovered)")

        if ch4_content in (None, "") and total_gas_m3 > 0 and not calculation_equation.startswith("Table 6-4"):
            # Tier 2 / 3 gas released or flared is the well's own: the Table 6-4 basis (81.6 %) was assumed
            raise ValueError("Missing required field: CH4 content of the test gas (mol %)")
        split = _split_vent_flare(
            total_gas_m3=total_gas_m3,
            ch4_tonnes=gross_ch4_tonnes,
            co2_tonnes=gross_co2_tonnes,
            ctrl_eff=ctrl_eff,
            hhv=hhv,
            ef_n2o=ef_n2o,
        )

        total_ch4 = split["total_ch4"]
        total_co2 = split["total_co2"]
        flared_n2o = split["flared_n2o"]

        total_co2e = calculate_co2e(total_co2, total_ch4, flared_n2o, gwp_dict)

        _tier_name = resolve_tier(raw_tier)
        ch4_unc = (uncertainties or {}).get("ch4") or 0.30
        co2_unc = (uncertainties or {}).get("co2") or 0.30
        ch4_res = propagate_uncertainty(total_ch4, ch4_unc, tier=_tier_name, process_category="vented", gas="ch4")
        co2_res = propagate_uncertainty(total_co2, co2_unc, tier=_tier_name, process_category="vented", gas="co2")
        n2o_res = propagate_uncertainty(flared_n2o, 0.50, tier=_tier_name, process_category="vented", gas="n2o") if flared_n2o > 0 else None

        return self.format_result(
            co2=co2_res,
            ch4=ch4_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "well_type": well_key,
                "tier": raw_tier,
                "events": num_events,
                "duration_days": duration_days,
                "total_gas_scf": total_gas_scf,
                "total_gas_m3": total_gas_m3,
                "ch4_content_mol_frac": c_ch4,
                "co2_content_mol_frac": c_co2,
                "disposition": disp,
                "control_efficiency": ctrl_eff,
            },
            metadata={
                "api_reference": "Section 6.2.2",
                "equation": calculation_equation,
                "source": "API Compendium 2021 Table 6-4 / Eq 6-1 / Eq 6-3",
                "split_details": split,
            },
        )


class CoalSeamDrillingCalculator(BaseCalculator):
    """
    API Compendium 2021 - Section 6.2.4: Coal Seam Exploratory Drilling and Well Testing
    Reference: Exhibit 6-5

    Accounts for:
      - Drilling gas vented (material balance: sum of Q_i * duration_i)
      - Well testing gas vented or flared (with 98% combustion efficiency)
    """

    def __init__(self):
        super().__init__("Coal Seam Drilling & Testing", "Section 6.2.4")

    def calculate(
        self,
        wells_data=None,  # list of dicts: [{"duration_days": 5, "gas_consumption_mmscf_day": 1.5}, ...]
        drilling_gas_vented_scf=None,  # or direct total drilling gas
        well_testing_gas_flared_scf=None,  # flared gas during testing
        ch4_content=0.887,  # Exhibit 6-5 default: 88.7 mole %
        co2_content=0.109,  # Exhibit 6-5 default: 10.9 mole %
        flare_combustion_efficiency=0.98,
        gwp_dict=None,
        uncertainties=None,
        **kwargs,
    ):
        uncertainties = uncertainties or {}
        gwp_dict = gwp_dict or get_active_gwp()

        def _parse_cs_frac(v, default, name):
            if v in (None, ""):
                return default
            s = str(v).strip()
            f = float(s.replace("%", "").strip())
            if f < 0:
                raise ValueError(f"{name} cannot be negative: {v}")
            if "%" in s or f > 1.0:
                f /= 100.0
            if f > 1.0:
                raise ValueError(f"{name} cannot exceed 100%: {v}")
            return f

        c_ch4 = _parse_cs_frac(ch4_content, 0.887, "ch4_content")
        c_co2 = _parse_cs_frac(co2_content, 0.109, "co2_content")
        if (c_ch4 + c_co2) > 1.0001:
            raise ValueError(f"Sum of gas concentrations cannot exceed 100%: {(c_ch4 + c_co2)*100:.1f}%")

        if drilling_gas_vented_scf is not None and float(drilling_gas_vented_scf) < 0:
            raise ValueError(f"drilling_gas_vented_scf cannot be negative: {drilling_gas_vented_scf}")
        if well_testing_gas_flared_scf is not None and float(well_testing_gas_flared_scf) < 0:
            raise ValueError(f"well_testing_gas_flared_scf cannot be negative: {well_testing_gas_flared_scf}")

        total_drilling_scf = 0.0
        if drilling_gas_vented_scf is not None and float(drilling_gas_vented_scf) >= 0:
            total_drilling_scf = float(drilling_gas_vented_scf)
        elif wells_data and isinstance(wells_data, list):
            for w in wells_data:
                days = float(w.get("duration_days") or w.get("days") or 0.0)
                rate_mmscf = float(w.get("gas_consumption_mmscf_day") or w.get("rate_mmscf") or 0.0)
                total_drilling_scf += days * rate_mmscf * 1_000_000.0

        drilling_ch4_tonnes = (total_drilling_scf / MOLAR_VOL_US) * c_ch4 * MW_CH4 / LB_PER_TONNE
        drilling_co2_tonnes = (total_drilling_scf / MOLAR_VOL_US) * c_co2 * MW_CO2 / LB_PER_TONNE

        flared_testing_scf = float(well_testing_gas_flared_scf or 0.0)
        flared_ch4_tonnes = 0.0
        flared_co2_tonnes = 0.0
        flared_n2o_tonnes = 0.0

        if flared_testing_scf > 0:
            eta_c = float(0.98 if flare_combustion_efficiency is None else flare_combustion_efficiency)
            flared_moles_gas = flared_testing_scf / MOLAR_VOL_US
            moles_ch4 = flared_moles_gas * c_ch4
            moles_native_co2 = flared_moles_gas * c_co2

            moles_co2_formed = moles_ch4 * eta_c + moles_native_co2
            flared_co2_tonnes = (moles_co2_formed * MW_CO2) / LB_PER_TONNE
            flared_ch4_tonnes = (moles_ch4 * (1.0 - eta_c) * MW_CH4) / LB_PER_TONNE

            flared_mmbtu = (flared_testing_scf * 1020.0) / 1_000_000.0
            flared_n2o_tonnes = (flared_mmbtu * 0.0001) / 1000.0

        total_ch4 = drilling_ch4_tonnes + flared_ch4_tonnes
        total_co2 = drilling_co2_tonnes + flared_co2_tonnes
        total_co2e = calculate_co2e(total_co2, total_ch4, flared_n2o_tonnes, gwp_dict)

        ch4_res = propagate_uncertainty(total_ch4, 0.25, tier="Tier 2", process_category="vented", gas="ch4")
        co2_res = propagate_uncertainty(total_co2, 0.25, tier="Tier 2", process_category="vented", gas="co2")
        n2o_res = propagate_uncertainty(flared_n2o_tonnes, 0.50, tier="Tier 2", process_category="vented", gas="n2o") if flared_n2o_tonnes > 0 else None

        return self.format_result(
            co2=co2_res,
            ch4=ch4_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "total_drilling_scf": total_drilling_scf,
                "flared_testing_scf": flared_testing_scf,
                "ch4_content": c_ch4,
                "co2_content": c_co2,
            },
            metadata={
                "api_reference": "Section 6.2.4",
                "equation": "Exhibit 6-5 Material Balance",
                "drilling_ch4_tonnes": drilling_ch4_tonnes,
                "drilling_co2_tonnes": drilling_co2_tonnes,
                "flared_co2_tonnes": flared_co2_tonnes,
                "flared_ch4_tonnes": flared_ch4_tonnes,
            },
        )
