"""API Compendium 2021 Section 7.5 and 7.6: wastewater treatment, refrigerant (HFC) and electrical equipment (SF6).

* 7.5.1  Wastewater: Equation 7-17 (IPCC CH4), 7-18 (N2O), 7-19 (aerobic CO2, Exhibit 7-6), 7-20 (EPA anaerobic CH4,
         Exhibit 7-7); MCF values of Tables 7-81 / 7-82.
* 7.6.1  Air conditioning and refrigeration: Equation 7-21 (charge x operating leak rate, Table 7-83) and the mass
         balance of Equation 7-22 (Exhibit 7-8); GWPs of Table 7-84.
* 7.6.2  Electrical equipment: Equations 7-23 to 7-26 and Tables 7-85 / 7-86 (Exhibit 7-9).

Fluorinated gases have no column of their own: the result carries them in ``results["f_gas"]`` (tonnes of the gas, its
GWP and CO2e) and in ``total_co2e``. CO2, CH4 and N2O are zero for an HFC or SF6 record.

Mass balances: the Compendium prints Equations 7-22 and 7-27 as "S_E - S_B + P - S + C", which gives a lower emission when
the year-end stock is larger, the opposite of Equation 7-23. All three are implemented the way Equation 7-23 and the
GHG Protocol worksheets state them: (begin stock - end stock) + purchases - sales - increase in equipment capacity.
"""
import math

from .base import BaseCalculator
from .units import calculate_co2e

LB_PER_TONNE = 2204.62
KG_PER_LB = 1000.0 / LB_PER_TONNE
L_PER_GAL = 3.785412
FT3_PER_M3 = 35.3147
M3_PER_GAL = L_PER_GAL / 1000.0
M3_PER_FT3 = 1.0 / FT3_PER_M3
CH4_PER_COD = 0.25  # B, kg CH4 / kg COD (Equation 7-17)
N2O_EF_DEFAULT = 0.005  # kg N2O-N / kg N (Equation 7-18)

# Table 7-81 (aerobic) and Table 7-82 (anaerobic): default MCF
MCF = {
    "aerobic_centralized": 0.0,
    "anaerobic_reactor": 0.8,
    "anaerobic_shallow_lagoon": 0.2,
    "anaerobic_deep_lagoon": 0.8,
}

# Table 7-83: operating emission rate, % of charge per year (the high end of the range, as the table's note says)
OPERATING_RATE_PCT = {
    "domestic_refrigeration": 0.5,
    "stand_alone_commercial": 15.0,
    "medium_large_commercial_refrigeration": 35.0,
    "transport_refrigeration": 50.0,
    "industrial_refrigeration": 25.0,
    "chillers": 15.0,
    "residential_commercial_ac": 10.0,
    "mobile_ac_railway": 20.0,
    "mobile_ac_maritime": 40.0,
    "mobile_ac_other": 20.0,
}

# Table 7-85 (fraction of nameplate capacity per year) and Table 7-86 (kg SF6 per mile of line per year)
USAGE_EF = {
    "sealed_pressure_europe": 0.002,
    "sealed_pressure_japan": 0.007,
    "closed_pressure_europe": 0.026,
    "closed_pressure_japan": 0.007,
    "closed_pressure_us": 0.14,
    "gas_insulated_transformer_japan": 0.007,
}
TRANSMISSION_EF_KG_PER_MILE = 0.226
TRANSMISSION_EF_T_PER_KM = 1.40e-4

# 100-year / 20-year GWPs of the fluorinated gases, by IPCC report. Blends: Table 7-84 prints AR5 values only.
_FGAS_GWP = {
    "SF6": {"AR4": (22800.0, 16300.0), "AR5": (23500.0, 17500.0), "AR6": (25200.0, 18300.0)},
    "HFC-134A": {"AR4": (1430.0, 3830.0), "AR5": (1300.0, 3710.0), "AR6": (1530.0, 4140.0)},
}
_AR5_BLENDS = {  # Table 7-84 (IPCC AR5, 100 years); "na" entries are absent
    "R-401A": 18, "R-401B": 15, "R-401C": 21, "R-402A": 1902, "R-402B": 1205, "R-403A": 1780, "R-403B": 3471,
    "R-404A": 3943, "R-407A": 1923, "R-407B": 2547, "R-407C": 1624, "R-407D": 1487, "R-407E": 1425, "R-408A": 2430,
    "R-410A": 1924, "R-410B": 2048, "R-411A": 15, "R-411B": 4, "R-412A": 445, "R-415A": 25,
    "R-415B": 104, "R-416A": 767, "R-417A": 2127, "R-418A": 3, "R-419A": 2688, "R-420A": 1144, "R-500": 36,
    "R-503": 4972, "R-504": 326, "R-507": 3985, "R-507A": 3985, "R-509": 4984, "R-509A": 4984,
}
_ALIASES = {"R-134A": "HFC-134A", "HFC134A": "HFC-134A", "R134A": "HFC-134A", "FREON-134A": "HFC-134A"}
_STANDARD_BY_CH4 = {25.0: ("AR4", 0), 28.0: ("AR5", 0), 29.8: ("AR6", 0), 72.0: ("AR4", 1), 84.0: ("AR5", 1),
                    82.5: ("AR6", 1)}


def _num(inputs, key, what=None, required=True, minimum=0.0):
    v = inputs.get(key)
    if v in (None, "", "-"):
        if required:
            raise ValueError(f"{what or key} is required")
        return None
    if isinstance(v, str) and "," in v:  # "1,5" was read as 15 and "1,000" as 1000: the decimal mark is not guessed
        raise ValueError(f"{what or key} contains a comma ({v!r}): send a plain number such as 1234.5")
    try:
        x = float(str(v).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{what or key} must be a number (got {v!r})") from None
    if not math.isfinite(x) or (minimum is not None and x < minimum):
        raise ValueError(f"{what or key} must be a finite number of at least {minimum} (got {v!r})")
    return x


def fgas_gwp(gas, gwp_dict=None, override=None):
    """GWP of an HFC, a refrigerant blend or SF6 for the report and horizon the CH4 GWP of ``gwp_dict`` belongs to.

    ``override`` (a GWP entered by the site) always wins. Refuses a gas without a printed value instead of guessing."""
    if override not in (None, ""):
        try:
            g = _num({"gwp": override}, "gwp", "The entered GWP", minimum=None)
        except ValueError as err:
            raise ValueError(f"The entered GWP must be a positive number ({err})") from None
        if g <= 0:
            raise ValueError("The entered GWP must be a positive number")
        return g
    key = str(gas or "").strip().upper().replace(" ", "")
    key = _ALIASES.get(key, key)
    std, horizon = "AR5", 0
    if gwp_dict and gwp_dict.get("CH4") is not None:
        std, horizon = _STANDARD_BY_CH4.get(round(float(gwp_dict["CH4"]), 1), ("AR5", 0))
    if key in _FGAS_GWP:
        return _FGAS_GWP[key][std][horizon]
    if key in _AR5_BLENDS:
        if std != "AR5" or horizon:
            raise ValueError(f"Table 7-84 prints the GWP of {gas} for IPCC AR5 (100 years) only: enter its GWP for the "
                             f"{std}{' 20-year' if horizon else ''} basis")
        return float(_AR5_BLENDS[key])
    raise ValueError(f"No GWP for '{gas}': use SF6, HFC-134a or a Table 7-84 blend, or enter the GWP")


def _result(calc, co2=0.0, ch4=0.0, n2o=0.0, f_gas=None, inputs=None, gwp_dict=None):
    total = calculate_co2e(co2=co2, ch4=ch4, n2o=n2o, gwp_dict=gwp_dict) + (f_gas["co2e"] if f_gas else 0.0)
    out = calc.format_result(co2=co2 if co2 else None, ch4=ch4 if ch4 else None, n2o=n2o if n2o else None,
                             total_co2e=total, inputs=inputs or {},
                             metadata={"standard": "API Compendium 2021 " + calc.section_ref})
    if f_gas:
        out["results"]["f_gas"] = f_gas
    return out


class WastewaterCalculator(BaseCalculator):
    """Section 7.5.1: aerobic CO2 (Eq 7-19), anaerobic CH4 (Eq 7-20 EPA / Eq 7-17 IPCC) and N2O (Eq 7-18)."""

    VOLUME_UNITS = {  # unit -> (m3 per unit, "rate per day" / "rate per year" / "total in the period")
        "gal/day": (M3_PER_GAL, "day"), "ft3/day": (M3_PER_FT3, "day"), "m3/day": (1.0, "day"),
        "gal/yr": (M3_PER_GAL, "year"), "ft3/yr": (M3_PER_FT3, "year"), "m3/yr": (1.0, "year"),
        "gal": (M3_PER_GAL, "total"), "ft3": (M3_PER_FT3, "total"), "m3": (1.0, "total"),
    }

    def __init__(self):
        super().__init__("Wastewater Treatment", "Section 7.5.1")

    def _volume_m3(self, flow, unit, days, year_fraction):
        u = str(unit or "").strip().lower().replace("³", "3").replace("per", "/").replace(" ", "")
        if u not in self.VOLUME_UNITS:
            raise ValueError(f"Unknown wastewater flow unit '{unit}': {sorted(self.VOLUME_UNITS)}")
        m3_per, basis = self.VOLUME_UNITS[u]
        factor = days if basis == "day" else year_fraction if basis == "year" else 1.0
        return flow * m3_per * factor

    def calculate(self, method, inputs, days=365.0, year_fraction=1.0, gwp_dict=None, uncertainties=None):
        m = str(method or "").strip().lower()
        flow = _num(inputs, "flow", "Wastewater flow")
        volume_m3 = self._volume_m3(flow, inputs.get("flow_unit"), days, year_fraction)
        co2 = ch4 = n2o = 0.0
        detail = {"method": m, "volume_m3": volume_m3}
        if m in ("aerobic", "aerobic_co2", "eq_7_19"):
            bod5 = _num(inputs, "bod5_mg_l", "BOD5 removed (mg/L)")
            co2 = volume_m3 * 1000.0 * bod5 / 0.7 * 44.0 / 32.0 / 1e9  # Eq 7-19, tonnes (mg -> t is 1e9)
            detail["ultimate_bod_mg_l"] = bod5 / 0.7
        elif m in ("anaerobic_epa", "epa", "eq_7_20"):
            bod_lb_ft3 = _num(inputs, "bod5_lb_ft3", "BOD5 loading (lb/ft3)")
            fad_pct = _num(inputs, "fad_pct", "Fraction anaerobically digested (%)")
            if fad_pct > 100:
                raise ValueError("Fraction anaerobically digested must be 0 to 100 %")
            ch4 = volume_m3 * FT3_PER_M3 * (fad_pct / 100.0) * bod_lb_ft3 * 0.22 / LB_PER_TONNE  # Eq 7-20
        elif m in ("ipcc", "ipcc_ch4", "eq_7_17"):
            cod = _num(inputs, "cod_kg_m3", "COD (kg/m3)")
            treatment = str(inputs.get("treatment_type") or "").strip().lower()
            mcf = _num(inputs, "mcf", required=False)
            if mcf is None:
                if treatment not in MCF:
                    raise ValueError(f"Give the treatment type {sorted(MCF)} or its MCF (Tables 7-81 / 7-82)")
                mcf = MCF[treatment]
            if mcf > 1:
                raise ValueError("MCF is a fraction between 0 and 1")
            sludge = _num(inputs, "sludge_cod_kg", required=False) or 0.0
            b = _num(inputs, "ch4_capacity_kg_per_kg_cod", required=False) or CH4_PER_COD
            organic = volume_m3 * cod - sludge
            if organic < 0:
                raise ValueError("Organic component removed as sludge exceeds the COD of the wastewater")
            ch4 = organic * b * mcf * 0.001  # Eq 7-17
            detail.update(mcf=mcf, organic_kg_cod=organic)
        else:
            raise ValueError("Wastewater method must be aerobic, anaerobic_epa or ipcc")
        nitrogen = _num(inputs, "n_effluent_kg_m3", required=False)
        if nitrogen:
            ef = _num(inputs, "n2o_ef_kg_n2o_n_per_kg_n", required=False)
            ef = N2O_EF_DEFAULT if ef is None else ef
            n2o = volume_m3 * nitrogen * ef * 44.0 / 28.0 * 0.001  # Eq 7-18
        return _result(self, co2=co2, ch4=ch4, n2o=n2o, inputs=detail, gwp_dict=gwp_dict)


def _mass_kg(value, unit):
    u = str(unit or "kg").strip().lower()
    if u in ("kg", "kilogram", "kilograms"):
        return value
    if u in ("lb", "lbs", "pound", "pounds"):
        return value * KG_PER_LB
    if u in ("t", "tonne", "tonnes", "metric_ton"):
        return value * 1000.0
    raise ValueError(f"Unknown mass unit '{unit}': kg, lb or tonne")


def _mass_balance_kg(inputs, what):
    """(begin stock - end stock) + purchases - sales - increase in equipment capacity, kg."""
    unit = inputs.get("mass_unit")
    begin = _mass_kg(_num(inputs, "stock_begin", f"{what} stock at the beginning of the year"), unit)
    end = _mass_kg(_num(inputs, "stock_end", f"{what} stock at the end of the year"), unit)
    bought = _mass_kg(_num(inputs, "purchases", f"{what} purchases"), unit)
    sold = _mass_kg(_num(inputs, "sales", f"{what} sales and disbursements"), unit)
    cap = _mass_kg(_num(inputs, "capacity_increase", f"net increase in {what} equipment capacity", required=False,
                        minimum=None) or 0.0, unit)
    emitted = (begin - end) + bought - sold - cap
    if emitted < -1e-9:
        raise ValueError(f"The {what} balance is negative ({emitted:g} kg): check the stocks, purchases and sales")
    return max(emitted, 0.0)


class RefrigerantCalculator(BaseCalculator):
    """Section 7.6.1: HFC emissions from refrigeration and air conditioning (Equations 7-21 and 7-22)."""

    def __init__(self):
        super().__init__("Refrigerant (HFC) Emissions", "Section 7.6.1")

    def calculate(self, method, inputs, year_fraction=1.0, gwp_dict=None, uncertainties=None):
        m = str(method or "").strip().lower()
        gas = inputs.get("refrigerant") or inputs.get("substance") or "HFC-134a"
        gwp = fgas_gwp(gas, gwp_dict, inputs.get("gwp"))
        detail = {"method": m, "refrigerant": gas, "gwp": gwp}
        if m in ("charge", "default", "eq_7_21", "operating"):
            count = _num(inputs, "equipment_count", "Number of units")
            charge = _num(inputs, "charge_kg", "Full charge per unit (kg)")
            rate = _num(inputs, "operating_rate_pct", required=False)
            if rate is None:
                et = str(inputs.get("equipment_type") or "").strip().lower()
                if et not in OPERATING_RATE_PCT:
                    raise ValueError(f"Give the operating leak rate (%) or the equipment type {sorted(OPERATING_RATE_PCT)}")
                rate = OPERATING_RATE_PCT[et]
            if rate > 100:
                raise ValueError("Operating emission rate must be 0 to 100 % of the charge per year")
            tonnes = count * charge * rate / 100.0 / 1000.0 * year_fraction  # Eq 7-21
            detail.update(operating_rate_pct=rate)
        elif m in ("mass_balance", "eq_7_22"):
            tonnes = _mass_balance_kg(inputs, "refrigerant") / 1000.0
        else:
            raise ValueError("Refrigerant method must be charge or mass_balance")
        f_gas = {"gas": str(gas), "value": tonnes, "gwp": gwp, "co2e": tonnes * gwp}
        return _result(self, f_gas=f_gas, inputs=detail, gwp_dict=gwp_dict)


class ElectricalEquipmentCalculator(BaseCalculator):
    """Section 7.6.2: SF6 from electrical transmission and distribution equipment (Equations 7-23 to 7-26)."""

    def __init__(self):
        super().__init__("Electrical Equipment (SF6) Emissions", "Section 7.6.2")

    def calculate(self, method, inputs, year_fraction=1.0, gwp_dict=None, uncertainties=None):
        m = str(method or "").strip().lower()
        gwp = fgas_gwp("SF6", gwp_dict, inputs.get("gwp"))
        detail = {"method": m, "gwp": gwp}
        unit = inputs.get("mass_unit")
        if m in ("mass_balance", "eq_7_23"):
            tonnes = _mass_balance_kg(inputs, "SF6") / 1000.0
        elif m in ("recharge", "eq_7_24", "eq_7_25", "usage_factor"):
            recharged = _mass_kg(_num(inputs, "recharge", "SF6 used to recharge equipment"), unit)
            recovered = _mass_kg(_num(inputs, "recovered", "SF6 recovered from equipment"), unit)
            if recovered > recharged:
                raise ValueError("SF6 recovered cannot exceed the SF6 used to recharge")
            kg = recharged - recovered  # Eq 7-24
            capacity = _num(inputs, "nameplate_capacity", required=False)
            if m in ("eq_7_25", "usage_factor") or capacity is not None:
                if capacity is None:
                    raise ValueError("Equation 7-25 needs the nameplate capacity of the equipment installed")
                ef = _num(inputs, "usage_ef", required=False)
                if ef is None:
                    et = str(inputs.get("equipment_type") or "").strip().lower()
                    if et not in USAGE_EF:
                        raise ValueError(f"Give the usage factor (fraction/yr) or equipment type {sorted(USAGE_EF)}")
                    ef = USAGE_EF[et]
                kg += _mass_kg(capacity, unit) * ef * year_fraction  # Eq 7-25
                detail["usage_ef"] = ef
            tonnes = kg / 1000.0
        elif m in ("distance", "transmission", "eq_7_26"):
            dist = _num(inputs, "distance", "Length of line at or above 34.5 kV")
            du = str(inputs.get("distance_unit") or "mi").strip().lower()
            if du in ("mi", "mile", "miles"):
                tonnes = dist * TRANSMISSION_EF_KG_PER_MILE / 1000.0 * year_fraction
            elif du in ("km", "kilometre", "kilometer", "kilometres", "kilometers"):
                tonnes = dist * TRANSMISSION_EF_T_PER_KM * year_fraction
            else:
                raise ValueError("Distance unit must be mi or km")
        else:
            raise ValueError("Electrical equipment method must be mass_balance, recharge or distance")
        f_gas = {"gas": "SF6", "value": tonnes, "gwp": gwp, "co2e": tonnes * gwp}
        return _result(self, f_gas=f_gas, inputs=detail, gwp_dict=gwp_dict)


# ------------------------------------------------------------------ dispatcher glue ------------------------------------

OTHER_FUGITIVE_PROCESSES = {
    **{p: WastewaterCalculator() for p in ("wastewater", "wastewater_treatment")},
    **{p: RefrigerantCalculator() for p in ("refrigerant", "refrigerants", "hfc", "air_conditioning", "refrigeration")},
    **{p: ElectricalEquipmentCalculator() for p in ("electrical_equipment", "sf6", "electrical_transmission")},
}


def dispatch_other_fugitive(process_type, inputs, emission_factors, uncertainties, gwp_dict=None, gwp_standard=None):
    """Same call signature as CalculationDispatcher._dispatch_impl for the Section 7.5 / 7.6 process types.

    The inputs are read from the record or from ``calc_inputs[process_type]``. Time-based inputs (flows per day,
    annual leak rates, distances) cover the record's period: its calendar month for a monthly record, else a year;
    ``operating_days`` overrides it. Measured quantities (mass balances, recharges) are the amounts of the record.
    """
    from .constants import get_active_gwp
    from .dispatcher import record_period

    calc = OTHER_FUGITIVE_PROCESSES[process_type]
    flat = {**(inputs or {}), **((inputs or {}).get("calc_inputs") or {}).get(process_type, {})}
    gwp = gwp_dict if gwp_dict is not None else get_active_gwp(standard=gwp_standard)
    days = _num(flat, "operating_days", required=False)
    days = record_period(flat)[1] if days is None else days
    if days > 366:
        raise ValueError("'operating_days' must be between 0 and 366")
    year_fraction = days / 365.0 if _num(flat, "operating_days", required=False) is not None else record_period(flat)[2]
    if isinstance(calc, WastewaterCalculator):
        if flat.get("flow") in (None, ""):  # the record's activity amount and unit are the flow
            flat = {**flat, "flow": flat.get("amount", flat.get("quantity")), "flow_unit": flat.get("flow_unit") or flat.get("unit")}
        return calc.calculate(flat.get("wastewater_method") or flat.get("method"), flat, days=days,
                              year_fraction=year_fraction, gwp_dict=gwp, uncertainties=uncertainties)
    key = "refrigerant_method" if isinstance(calc, RefrigerantCalculator) else "electrical_method"
    return calc.calculate(flat.get(key) or flat.get("method"), flat, year_fraction=year_fraction, gwp_dict=gwp,
                          uncertainties=uncertainties)
