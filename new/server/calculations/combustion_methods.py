"""API Compendium 2021 combustion and waste-gas methods that are not fuel x catalog factor.

  carbon_content    liquid fuel volume x density x wt % carbon (Exhibit 4.5)
  equipment         equipment-specific CH4 / N2O on an energy-input basis (Tables 4-9, 4-11;
                    Exhibits 4.7, 4.8), energy from fuel x HHV, direct MMBtu, or engine hp x load x hours
  vehicle_distance  distance / fuel economy -> fuel volume -> fuel-basis CO2, per-volume CH4 / N2O
                    (Exhibit 4.12)
  flare_voc         flare emissions back-calculated from a known VOC emission (Exhibit 5.2)
  thermal_oxidizer  TOC to the oxidizer x carbon content x destruction efficiency (Exhibit 5.3)

All energy is on an HHV basis. Masses are returned in tonnes.
"""
import math

from .base import BaseCalculator
from .units import calculate_co2e
from .uncertainty import propagate_uncertainty, resolve_tier

MW_C, MW_CO2 = 12.011, 44.01
C_TO_CO2 = MW_CO2 / MW_C
SCF_TO_M3 = 0.028316846592
J_PER_MMBTU = 1.055056e9
PER_TJ_TO_PER_MMBTU = J_PER_MMBTU / 1e12  # tonne / 10^12 J -> tonne / MMBtu

# Table 4-5 (EPA Part 98 Table C-1): default HHV and CO2 factor (tonne CO2 / MMBtu HHV)
FUEL_BASIS = {
    "natural_gas": {"label": "Natural gas", "co2": 0.05306, "hhv": 1.026e-3, "hhv_unit": "MMBtu/scf",
                    "ch4": 1.0e-6, "n2o": 1.0e-7},
    "diesel": {"label": "Diesel (distillate No. 2)", "co2": 0.07396, "hhv": 0.138, "hhv_unit": "MMBtu/gal",
               "ch4": 3.0e-6, "n2o": 6.0e-7},
    "gasoline": {"label": "Motor gasoline", "co2": 0.07022, "hhv": 0.125, "hhv_unit": "MMBtu/gal",
                 "ch4": 3.0e-6, "n2o": 6.0e-7},
}


def _eq(label, fuel, ch4_pj, n2o_pj=None, toc=False, table="Table 4-11"):
    """ch4_pj / n2o_pj in tonne per 10^12 J (HHV) as printed; n2o None -> fuel basis (Table 4-6)."""
    return {"label": label, "fuel": fuel, "table": table, "toc": toc,
            "ch4": ch4_pj * PER_TJ_TO_PER_MMBTU,
            "n2o": None if n2o_pj is None else n2o_pj * PER_TJ_TO_PER_MMBTU}


# tonne / MMBtu (HHV). Table 4-9 is printed per 10^6 Btu; Table 4-11 per 10^12 J.
EQUIPMENT_FACTORS = {
    "boiler_ng_controlled": {"label": "Boiler / furnace / heater, natural gas, low-NOx (controlled)",
                             "fuel": "natural_gas", "table": "Table 4-9", "toc": False, "ch4": 1.0e-6, "n2o": 2.8e-7},
    "boiler_ng_uncontrolled": {"label": "Boiler / furnace / heater, natural gas, uncontrolled",
                               "fuel": "natural_gas", "table": "Table 4-9", "toc": False, "ch4": 1.0e-6, "n2o": 9.8e-7},
    "ic_2s_lean_ng": _eq("IC engine, 2-stroke lean burn, natural gas", "natural_gas", 0.623),
    "ic_4s_lean_ng": _eq("IC engine, 4-stroke lean burn, natural gas", "natural_gas", 0.537),
    "ic_4s_lean_ng_vaughn": _eq("IC engine, 4-stroke lean burn, natural gas (gathering station measurements)",
                                "natural_gas", 0.494),
    "ic_4s_rich_ng": _eq("IC engine, 4-stroke rich burn, natural gas, uncontrolled", "natural_gas", 0.10),
    "ic_4s_rich_ng_nscr": _eq("IC engine, 4-stroke rich burn, natural gas, with NSCR", "natural_gas", 0.043),
    "ic_gasoline": _eq("IC engine, gasoline", "gasoline", 1.30, toc=True),
    "ic_diesel": _eq("IC engine, diesel", "diesel", 0.15, toc=True),
    "ic_large_bore_diesel": _eq("IC engine, large-bore diesel (> 600 hp)", "diesel", 0.0035),
    "ic_dual_fuel": _eq("IC engine, dual fuel (95 % natural gas / 5 % diesel)", "natural_gas", 0.26),
    "turbine_ng_uncontrolled": _eq("Gas turbine, natural gas, uncontrolled", "natural_gas", 0.0037, 0.0013),
}
TOC_CH4_WT = 0.09  # AP-42: engine exhaust TOC is 9 wt % CH4 (Table 4-11 footnote a)
HP_HR_BTU = 7000.0  # Table 4-2: energy input per hp-hr output

# Table 4-16 rows used as vehicle defaults (tonne per 1,000 gal fuel)
VEHICLE_FACTORS = {
    "hd_diesel_advanced": {"label": "Heavy-duty diesel vehicle, advanced control", "fuel": "diesel",
                           "ch4": 4.2e-4, "n2o": 5.7e-4},
}

LIQ_TO_GAL = {"gal": 1.0, "bbl": 42.0, "m3": 264.172052, "l": 0.264172052}
GAS_TO_SCF = {"scf": 1.0, "mcf": 1e3, "mscf": 1e3, "mmscf": 1e6, "m3": 1 / SCF_TO_M3, "sm3": 1 / SCF_TO_M3}
MASS_TO_T = {"t": 1.0, "tonne": 1.0, "tonnes": 1.0, "kg": 1e-3, "lb": 1 / 2204.62,
             "short_ton": 0.90718474, "ton": 0.90718474, "tons": 0.90718474}
DENSITY_TO_LB_GAL = {"lb/gal": 1.0, "kg/m3": 1 / 119.826427, "kg/l": 8.34540445, "g/ml": 8.34540445}
DIST_TO_MILE = {"mile": 1.0, "mi": 1.0, "miles": 1.0, "km": 0.621371192}

# molecular weights, gross HHV at 60 F (Btu/scf, Table 3-8 basis of Exhibit 5.2: mix 1,838.9 Btu/scf) and
# the natural gas N2O fuel factor of Table 4-6 (tonne / MMBtu HHV); C6+ as hexane
HC_MW = {"ch4": 16.04, "c2h6": 30.07, "c3h8": 44.10, "c4h10": 58.12, "c5h12": 72.15, "c6plus": 86.18}
HC_HHV_BTU_SCF = {"ch4": 1010.0, "c2h6": 1769.7, "c3h8": 2516.1, "c4h10": 3262.4, "c5h12": 4008.9, "c6plus": 4755.9}
FLARE_N2O_T_PER_MMBTU = 9.50e-8
# carbon mass fraction of hydrocarbons (Exhibit 5.2); C6+ as hexane
HC_CARBON = {"ch4": 12.011 / 16.043, "c2h6": 2 * 12.011 / 30.069, "c3h8": 3 * 12.011 / 44.096,
             "c4h10": 4 * 12.011 / 58.122, "c5h12": 5 * 12.011 / 72.149, "c6plus": 6 * 12.011 / 86.175}


def _num(v, name, default=None, positive=False):
    if v in (None, ""):
        if default is None:
            raise ValueError(f"Missing required field: {name}")
        return float(default)
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"'{name}' must be a number")
    if not math.isfinite(x) or x < 0 or (positive and x == 0):
        raise ValueError(f"'{name}' must be a {'positive' if positive else 'non-negative'} number")
    return x


def _frac(v, name, default=None):
    x = _num(v, name, default)
    if x > 100.0:
        raise ValueError(f"'{name}' cannot exceed 100 %")
    return x / 100.0  # inputs are percentages (0-100)


def _unit(v, table, name, default=None):
    u = str(v or default or "").strip().lower().replace("³", "3").replace(" ", "_")
    if u not in table:
        raise ValueError(f"{name} unit must be one of: {', '.join(table)}")
    return table[u]


def equipment_factor_list():
    return [{"key": k, "label": v["label"], "fuel": v["fuel"], "table": v["table"]} for k, v in EQUIPMENT_FACTORS.items()]


class CombustionMethodCalculator(BaseCalculator):
    METHODS = ("carbon_content", "equipment", "vehicle_distance", "flare_voc", "thermal_oxidizer")

    def __init__(self):
        super().__init__("Combustion / waste gas method", "Sections 4 and 5")

    # ---- energy input (MMBtu HHV) for the equipment method ----
    def _energy_mmbtu(self, i, fuel):
        if i.get("energy_mmbtu") not in (None, ""):
            return _num(i["energy_mmbtu"], "energy input (MMBtu)")
        if i.get("engine_hp") not in (None, ""):
            hp = _num(i["engine_hp"], "engine rating (hp)")
            load = _frac(i.get("load_pct"), "load", 100)
            hours = _num(i.get("operating_hours"), "operating hours")
            rate = _num(i.get("heat_rate_btu_hphr"), "heat rate (Btu/hp-hr)", HP_HR_BTU, positive=True)
            return hp * load * hours * rate / 1e6
        vol = _num(i.get("fuel_volume") if i.get("fuel_volume") not in (None, "") else i.get("amount"), "fuel volume")
        unit = str(i.get("fuel_volume_unit") or i.get("unit") or "").strip().lower()
        if fuel == "natural_gas":
            scf = vol * _unit(unit, GAS_TO_SCF, "Fuel gas volume")
            hhv_btu_scf = _num(i.get("hhv_btu_scf") or i.get("hhv"), "HHV (Btu/scf)", FUEL_BASIS["natural_gas"]["hhv"] * 1e6)
            return scf * hhv_btu_scf / 1e6
        gal = vol * _unit(unit, LIQ_TO_GAL, "Fuel volume")
        return gal * _num(i.get("hhv_mmbtu_gal"), "HHV (MMBtu/gal)", FUEL_BASIS[fuel]["hhv"], positive=True)

    def calculate(self, method, inputs, uncertainties=None, gwp_dict=None):
        m = str(method or "").strip().lower()
        i = inputs or {}
        inter = {"method": m}
        co2 = ch4 = n2o = 0.0

        if m == "carbon_content":
            if i.get("fuel_mass") not in (None, ""):
                mass_t = _num(i["fuel_mass"], "fuel mass") * _unit(i.get("fuel_mass_unit"), MASS_TO_T, "Fuel mass", "t")
            else:
                gal = _num(i.get("fuel_volume") if i.get("fuel_volume") not in (None, "") else i.get("amount"), "fuel volume") \
                    * _unit(i.get("fuel_volume_unit") or i.get("unit"), LIQ_TO_GAL, "Fuel volume")
                dens = _num(i.get("fuel_density"), "fuel density", positive=True) \
                    * _unit(i.get("density_unit"), DENSITY_TO_LB_GAL, "Density", "lb/gal")
                mass_t = gal * dens / 2204.62
            c = _frac(i.get("carbon_wt_pct"), "carbon content (wt %)")
            ox = _frac(i.get("oxidation_pct"), "carbon oxidised", 100)
            co2 = mass_t * c * ox * C_TO_CO2
            inter.update(fuel_mass_t=mass_t, carbon_wt=c)

        elif m == "equipment":
            key = str(i.get("equipment_type") or "").strip()
            row = EQUIPMENT_FACTORS.get(key)
            if row is None:
                raise ValueError(f"Unknown equipment type '{key}'")
            fuel = row["fuel"]
            e = self._energy_mmbtu(i, fuel)
            ch4 = e * row["ch4"] * (TOC_CH4_WT if row["toc"] else 1.0)
            n2o = e * (row["n2o"] if row["n2o"] is not None else FUEL_BASIS[fuel]["n2o"])
            co2_ef = _num(i.get("co2_ef_t_mmbtu"), "CO2 factor (t/MMBtu)", FUEL_BASIS[fuel]["co2"])
            co2 = e * co2_ef
            inter.update(equipment=row["label"], energy_mmbtu=e, api_table=row["table"])

        elif m == "vehicle_distance":
            miles = _num(i.get("distance") if i.get("distance") not in (None, "") else i.get("amount"), "distance") \
                * _unit(i.get("distance_unit") or "mile", DIST_TO_MILE, "Distance")
            vrow = VEHICLE_FACTORS.get(str(i.get("vehicle_type") or ""))
            fuel = str(i.get("vehicle_fuel") or (vrow or {}).get("fuel") or "").strip().lower()
            if fuel not in ("diesel", "gasoline"):
                raise ValueError("Vehicle fuel must be diesel or gasoline")
            mpg = _num(i.get("fuel_economy_mpg"), "fuel economy (miles/gal)", positive=True)
            gal = miles / mpg
            hhv = _num(i.get("hhv_mmbtu_gal"), "HHV (MMBtu/gal)", FUEL_BASIS[fuel]["hhv"], positive=True)
            e = gal * hhv
            co2 = e * _num(i.get("co2_ef_t_mmbtu"), "CO2 factor (t/MMBtu)", FUEL_BASIS[fuel]["co2"])
            ch4_k = i.get("ch4_t_per_kgal") if i.get("ch4_t_per_kgal") not in (None, "") else (vrow or {}).get("ch4")
            n2o_k = i.get("n2o_t_per_kgal") if i.get("n2o_t_per_kgal") not in (None, "") else (vrow or {}).get("n2o")
            ch4 = gal / 1000.0 * _num(ch4_k, "CH4 factor") if ch4_k is not None else e * FUEL_BASIS[fuel]["ch4"]
            n2o = gal / 1000.0 * _num(n2o_k, "N2O factor") if n2o_k is not None else e * FUEL_BASIS[fuel]["n2o"]
            inter.update(fuel_gal=gal, energy_mmbtu=e)

        elif m == "flare_voc":
            voc_t = _num(i.get("voc_mass") if i.get("voc_mass") not in (None, "") else i.get("amount"), "VOC emitted") \
                * _unit(i.get("voc_mass_unit") or i.get("unit"), MASS_TO_T, "VOC mass", "t")
            w = {k: _frac(i.get(f"wt_{k}"), f"{k} wt %", 0) for k in HC_CARBON}
            w_co2 = _frac(i.get("wt_co2"), "CO2 wt %", 0)
            w_voc = w["c3h8"] + w["c4h10"] + w["c5h12"] + w["c6plus"]
            w_hc = w_voc + w["ch4"] + w["c2h6"]
            if w_voc <= 0:
                raise ValueError("The flare gas analysis needs the VOC (C3+) weight %")
            if w_hc + w_co2 > 1.0001:
                raise ValueError("Gas analysis exceeds 100 wt %")
            eff = _frac(i.get("combustion_efficiency"), "combustion efficiency", 98)
            if eff >= 1.0:
                raise ValueError("Combustion efficiency must be below 100 % for a VOC back-calculation")
            c_mix = sum(w[k] * HC_CARBON[k] for k in HC_CARBON) / w_hc
            hc_emitted = voc_t * w_hc / w_voc
            co2 = hc_emitted * c_mix * eff / (1 - eff) * C_TO_CO2 + voc_t * w_co2 / w_voc
            ch4 = hc_emitted * w["ch4"] / w_hc
            # N2O (Exhibit 5.2 step 3): hydrocarbon flared -> scf (MW of the mix) x HHV of the mix (Eq 3-11)
            # x the natural gas fuel factor of Table 4-6, 9.50e-8 t N2O / MMBtu. It was stored as 0.
            mol = {k: w[k] / HC_MW[k] for k in HC_CARBON}
            mw_mix = w_hc / sum(mol.values())
            hhv_btu_scf = sum(mol[k] * HC_HHV_BTU_SCF[k] for k in HC_CARBON) / sum(mol.values())
            hc_flared_scf = hc_emitted / (1 - eff) * 1000.0 / 0.45359237 / mw_mix * 379.3
            n2o = hc_flared_scf * hhv_btu_scf / 1e6 * FLARE_N2O_T_PER_MMBTU
            inter.update(hc_emitted_t=hc_emitted, hc_carbon_wt=c_mix, hc_mw=mw_mix, hc_hhv_btu_scf=hhv_btu_scf)

        elif m == "thermal_oxidizer":
            if i.get("toc_mass") not in (None, ""):
                toc_t = _num(i["toc_mass"], "TOC to oxidizer") * _unit(i.get("toc_mass_unit"), MASS_TO_T, "TOC mass", "t")
            else:
                gal = _num(i.get("liquid_loaded") if i.get("liquid_loaded") not in (None, "") else i.get("amount"), "liquid loaded") \
                    * _unit(i.get("liquid_unit") or i.get("unit"), LIQ_TO_GAL, "Liquid volume")
                loss = _num(i.get("loading_loss_lb_kgal"), "loading loss (lb VOC/1,000 gal)")
                voc_toc = _frac(i.get("voc_fraction_of_toc"), "VOC share of TOC", 85)
                if voc_toc == 0:
                    raise ValueError("VOC share of TOC must be above zero")
                toc_t = gal / 1000.0 * loss / voc_toc / 2204.62
            c = _frac(i.get("toc_carbon_wt_pct"), "TOC carbon content (wt %)")
            w_ch4 = _frac(i.get("toc_ch4_wt_pct"), "CH4 in TOC (wt %)")
            eff = _frac(i.get("destruction_efficiency"), "destruction efficiency", 98)
            co2 = toc_t * c * C_TO_CO2 * eff
            ch4 = toc_t * w_ch4 * (1 - eff)
            inter.update(toc_t=toc_t)

        else:
            raise ValueError(f"Unknown combustion method '{method}'. Use one of: {', '.join(self.METHODS)}")

        _tier = resolve_tier((uncertainties or {}).get("_factor_source", "specific"))
        return {
            "results": {g: propagate_uncertainty(v, 0.05 if g == "co2" else 0.5, tier=_tier, gas=g) if v else 0.0
                        for g, v in (("co2", co2), ("ch4", ch4), ("n2o", n2o))},
            "total_co2e": calculate_co2e(co2=co2, ch4=ch4, n2o=n2o, gwp_dict=gwp_dict),
            "intermediate": inter,
        }
