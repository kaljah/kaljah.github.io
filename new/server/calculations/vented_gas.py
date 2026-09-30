"""Vented or flared gas volume x composition (API Compendium 2021, Equations 6-2, 6-3, 6-16/6-17,
Section 5 flare stoichiometry) and CO2 blowdown mass (Equation 6-20).

Gas volume methods ("method"):
  volume      direct volume in scf / Mcf / MMscf / m3 (standard conditions)
  gor         GOR (scf/bbl) x oil rate (bbl/day) x vent duration (hours)          (Eq 6-3, Exhibit 6-2)
  rate_days   gas rate (scf/day, Mcf/day, MMscf/day or m3/day) x days              (Exhibit 6-5)
  actual      actual volume (ft3, bbl, gal or m3) at temperature (F) and pressure (atm), corrected to 60 F / 1 atm
                                                                                   (Eq 3-5, Exhibit 6-29)
  desiccant   vessel height and diameter (ft), gas pressure (psig), gas fraction of the packed vessel, refills
                                                                                   (Eq 6-16, Exhibit 6-15)
  co2_mass    physical volume (m3) x CO2 density (kg/m3) x CO2 weight fraction      (Eq 6-20, Exhibit 6-22)
  agr_balance sour gas volume x CO2 % - sweet gas volume x CO2 %, CH4 by Table 6-19   (Eq 6-18, Exhibit 6-17)
  reported_mass  CH4 / CO2 mass from a process simulation (e.g. GRI-GLYCalc) or measurement, less control
  thc_mass    total hydrocarbon loss (AP-42 Ch. 7 / simulation) x vent CH4 and CO2 wt %  (Section 6.3.9.3)

Vented gas:  CH4 = V x y_CH4 ; CO2 = V x y_CO2
Flared gas:  CH4 = V x y_CH4 x (1 - eff) ; CO2 = V x y_CO2 + V x (y_CH4 + 2 y_C2+) x eff   (C2+ as ethane)
"""
import math

from .base import BaseCalculator
from .units import CONVERSIONS, calculate_co2e
from .uncertainty import propagate_uncertainty, resolve_tier

SCF_TO_M3 = 0.028316846592
FT3_PER_BBL = 5.61458333
FT3_PER_GAL = 0.133680556
GAS_UNITS = {"scf": 1.0, "mcf": 1e3, "mscf": 1e3, "mmscf": 1e6, "m3": 1 / SCF_TO_M3, "sm3": 1 / SCF_TO_M3}
RATE_UNITS = {"scf/day": 1.0, "mcf/day": 1e3, "mmscf/day": 1e6, "m3/day": 1 / SCF_TO_M3}
ACTUAL_UNITS = {"ft3": 1.0, "acf": 1.0, "bbl": FT3_PER_BBL, "gal": FT3_PER_GAL, "m3": 1 / SCF_TO_M3}


def _frac(v, name, required=False):
    if v in (None, ""):
        if required:
            raise ValueError(f"Missing required field: {name}")
        return 0.0
    x = float(v)
    if not math.isfinite(x) or x < 0:
        raise ValueError(f"'{name}' must be a non-negative number")
    if x > 100.0:
        raise ValueError(f"'{name}' cannot exceed 100 %")
    return x / 100.0  # composition and efficiency inputs are percentages (0-100)


def _or(v, default):
    return default if v in (None, "") else v


def _num(v, name, required=True, default=None):
    if v in (None, ""):
        if required and default is None:
            raise ValueError(f"Missing required field: {name}")
        return default
    x = float(v)
    if not math.isfinite(x) or x < 0:
        raise ValueError(f"'{name}' must be a non-negative number")
    return x


class VentedGasCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Vented / flared gas volume", "Sections 5 and 6")

    def gas_volume_scf(self, method, i):
        m = str(method or "volume").lower()
        if m == "volume":
            u = str(i.get("gas_volume_unit") or i.get("unit") or "").lower().replace("³", "3")
            if u not in GAS_UNITS:
                raise ValueError("Gas volume unit must be scf, Mcf, MMscf or m3")
            return _num(i.get("gas_volume") if i.get("gas_volume") not in (None, "") else i.get("amount"), "gas volume") * GAS_UNITS[u]
        if m == "gor":
            return (_num(i.get("gor"), "GOR (scf/bbl)") * _num(i.get("oil_rate"), "oil rate (bbl/day)")
                    * _num(i.get("vent_hours"), "vent duration (hours)") / 24.0)
        if m == "rate_days":
            u = str(i.get("gas_rate_unit") or "scf/day").lower()
            if u not in RATE_UNITS:
                raise ValueError("Gas rate unit must be scf/day, Mcf/day, MMscf/day or m3/day")
            return _num(i.get("gas_rate"), "gas rate") * RATE_UNITS[u] * _num(i.get("days"), "days")
        if m == "actual":
            u = str(i.get("actual_unit") or "ft3").lower().replace("³", "3")
            if u not in ACTUAL_UNITS:
                raise ValueError("Actual volume unit must be ft3, bbl, gal or m3")
            v_ft3 = _num(i.get("actual_volume"), "actual volume") * ACTUAL_UNITS[u]
            t_f = _num(i.get("gas_temp_f"), "gas temperature (F)", default=60.0)
            p_atm = _num(i.get("gas_pressure_atm"), "gas pressure (atm)", default=1.0)
            return v_ft3 * p_atm * (60.0 + 459.67) / (t_f + 459.67)
        if m == "desiccant":
            h = _num(i.get("vessel_height_ft"), "vessel height (ft)")
            d = _num(i.get("vessel_diameter_ft"), "vessel diameter (ft)")
            p_psig = _num(i.get("vessel_pressure_psig"), "vessel pressure (psig)")
            g = _frac(_or(i.get("gas_fraction"), 45), "gas fraction of packed vessel")
            n = _num(i.get("refills"), "refills per year")
            # refills are per year; a monthly record carries its month's share (a full year of refills
            # was booked in every monthly record)
            from .dispatcher import record_period
            n *= record_period(i)[2]
            return h * d * d * math.pi / 4.0 * ((p_psig + 14.7) / 14.7) * g * n
        raise ValueError(f"Unknown gas volume method '{method}'")

    def calculate(self, method, inputs, uncertainties=None, gwp_dict=None):
        i = inputs
        activity = None
        if str(method).lower() == "reported_mass":
            u = str(i.get("mass_unit") or "t").strip().lower()
            to_t = {"t": 1.0, "tonne": 1.0, "kg": 1e-3, "lb": 1 / 2204.62, "short_ton": 0.90718474}
            if u not in to_t:
                raise ValueError("Mass unit must be t, kg, lb or short_ton")
            ch4 = _num(i.get("ch4_mass"), "CH4 emitted") * to_t[u]
            co2 = _num(i.get("co2_mass"), "CO2 emitted", default=0.0) * to_t[u]
            eff = _frac(i.get("control_efficiency"), "control efficiency")
            ch4, co2, v_scf = ch4 * (1 - eff), co2 * (1 - eff), None
            activity = (ch4 / (1 - eff) if eff < 1 else ch4, "t CH4 before control")
        elif str(method).lower() == "thc_mass":
            u = str(i.get("thc_loss_unit") or "t").strip().lower()
            to_t = {"t": 1.0, "tonne": 1.0, "kg": 1e-3, "lb": 1 / 2204.62, "short_ton": 0.90718474}
            if u not in to_t:
                raise ValueError("Hydrocarbon loss unit must be t, kg, lb or short_ton")
            m = _num(i.get("thc_loss") if i.get("thc_loss") not in (None, "") else i.get("amount"),
                     "total hydrocarbon loss") * to_t[u]
            w_ch4 = _frac(i.get("ch4_wt_pct"), "CH4 in vent (wt %)", required=True)
            w_co2 = _frac(i.get("co2_wt_pct"), "CO2 in vent (wt %)")
            if w_ch4 + w_co2 > 1.0001:
                raise ValueError("Vent composition exceeds 100 wt %")
            ch4, co2, v_scf = m * w_ch4, m * w_co2, None
            activity = (m, "t hydrocarbon")
        elif str(method).lower() == "agr_balance":
            u = str(i.get("gas_volume_unit") or i.get("unit") or "").lower().replace("³", "3")
            if u not in GAS_UNITS:
                raise ValueError("Gas volume unit must be scf, Mcf, MMscf or m3")
            v_sour = _num(i.get("sour_gas_volume") if i.get("sour_gas_volume") not in (None, "") else i.get("amount"),
                          "sour (inlet) gas volume") * GAS_UNITS[u]
            v_sweet = _num(i.get("sweet_gas_volume"), "sweet (outlet) gas volume") * GAS_UNITS[u]
            y_sour = _frac(i.get("sour_co2_content"), "sour gas CO2 (mol %)", required=True)
            y_sweet = _frac(i.get("sweet_co2_content"), "sweet gas CO2 (mol %)")
            co2_scf = v_sour * y_sour - v_sweet * y_sweet
            if co2_scf < 0:
                raise ValueError("Sweet gas carries more CO2 than the sour gas; check the volumes and CO2 contents")
            co2 = co2_scf * SCF_TO_M3 * CONVERSIONS["density_co2"] / 1000.0
            # Table 6-19 throughput factor: 0.0185 tonne CH4 per 10^6 scf treated
            ch4 = v_sour / 1e6 * 0.0185 if str(i.get("include_ch4", "true")).lower() not in ("false", "0", "no") else 0.0
            v_scf = v_sour
        elif str(method).lower() == "co2_mass":
            v = _num(i.get("physical_volume_m3"), "physical volume (m3)")
            rho = _num(i.get("co2_density"), "CO2 density at release conditions (kg/m3)")
            w = _frac(_or(i.get("co2_wt_pct"), 100), "CO2 weight %")
            n = _num(i.get("events"), "blowdown events", default=1.0)
            co2 = n * v * rho * w / 1000.0
            ch4 = 0.0
            v_scf = None
            activity = (n * v, "m3 released")
        else:
            v_scf = self.gas_volume_scf(method, i)
            y_ch4 = _frac(i.get("ch4_content"), "CH4 content (mol %)", required=True)
            y_co2 = _frac(i.get("co2_content"), "CO2 content (mol %)")
            y_c2 = _frac(i.get("c2plus_content"), "C2+ content (mol %)")
            if y_ch4 + y_co2 + y_c2 > 1.0001:
                raise ValueError("Gas composition exceeds 100 %")
            v_m3 = v_scf * SCF_TO_M3
            rho_ch4, rho_co2 = CONVERSIONS["density_ch4"], CONVERSIONS["density_co2"]
            if str(i.get("disposition") or "vented").lower() == "flared":
                eff = _frac(_or(i.get("combustion_efficiency"), 98), "combustion efficiency")
                ch4 = v_m3 * y_ch4 * (1 - eff) * rho_ch4 / 1000.0
                co2 = (v_m3 * y_co2 + v_m3 * (y_ch4 + 2 * y_c2) * eff) * rho_co2 / 1000.0
            else:
                ch4 = v_m3 * y_ch4 * rho_ch4 / 1000.0
                co2 = v_m3 * y_co2 * rho_co2 / 1000.0

        _tier = resolve_tier((uncertainties or {}).get("_factor_source", "specific"))
        return {
            "results": {"ch4": propagate_uncertainty(ch4, 0.10 if ch4 else 0.0, tier=_tier, gas="ch4"),
                        "co2": propagate_uncertainty(co2, 0.10 if co2 else 0.0, tier=_tier, gas="co2"),
                        "n2o": 0.0},
            "total_co2e": calculate_co2e(co2=co2, ch4=ch4, gwp_dict=gwp_dict),
            "intermediate": {"method": method, "gas_volume_scf": v_scf,
                             "activity_amount": activity[0] if activity else None,
                             "activity_unit": activity[1] if activity else None,
                             "disposition": str(i.get("disposition") or "vented").lower()},
        }
