"""
API Compendium 2021 - Section 8: Indirect Emissions
Implementation of indirect steam/heat and cogeneration allocation methodologies.
"""

from .base import BaseCalculator
from .units import calculate_co2e, normalize_efficiency
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty


_ENERGY_MMBTU = {
    "btu": 1e-6, "mmbtu": 1.0, "mm_btu": 1.0, "mmbtus": 1.0, "therm": 0.1, "therms": 0.1,
    "mj": 947.817e-6, "megajoule": 947.817e-6, "mega_joule": 947.817e-6, "gj": 0.947817, "gigajoule": 0.947817,
    "kwh": 3412.142e-6, "kw-hr": 3412.142e-6, "kilowatthour": 3412.142e-6, "mwh": 3.412142, "mw-hr": 3.412142,
}
_STEAM_MASS_LB = {
    "lb": 1.0, "lbs": 1.0, "pound": 1.0, "pounds": 1.0, "klb": 1000.0, "mlb": 1000.0, "thousand_lbs": 1000.0,
    "kg": 2.20462262, "kilogram": 2.20462262, "short_ton": 2000.0, "us_ton": 2000.0,
    "tonne": 2204.62262, "tonnes": 2204.62262, "metric_ton": 2204.62262, "mt": 2204.62262,
}
STEAM_MASS_UNITS = frozenset(_STEAM_MASS_LB)


def heat_to_mmbtu(amount, unit, steam_enthalpy=None, steam_enthalpy_btu_lb=None):
    """Steam / heat in MMBtu. A steam mass needs its energy content (API Compendium 2021 Equation 8-1:
    mass x (enthalpy at the steam's pressure and temperature - enthalpy of saturated water at 212 F)):
    `steam_enthalpy_btu_lb` (that difference, Btu/lb) or `steam_enthalpy` (MMBtu per unit entered). It was
    taken as 1,000 Btu/lb, which the Compendium does not give (Exhibit 8.3's steam carries 1,170)."""
    amt = float(amount)
    if amt < 0:
        raise ValueError(f"Heat energy amount cannot be negative: {amount}")
    u = str(unit or "").strip().lower().replace(" ", "")
    if u in _ENERGY_MMBTU:
        return amt * _ENERGY_MMBTU[u]
    if u in ("ton", "tons"):
        raise ValueError("'ton' is ambiguous (short ton or metric tonne): write 'short_ton' or 'tonne'")
    if u not in _STEAM_MASS_LB:
        raise ValueError(f"Unknown unit '{unit}' for steam / heat: an energy unit (MMBtu, Btu, therm, GJ, MJ, kWh, "
                         "MWh) or a steam mass (lb, klb, kg, short_ton, tonne) with its enthalpy")
    if steam_enthalpy_btu_lb not in (None, ""):
        enth = float(steam_enthalpy_btu_lb)
        if enth < 0:
            raise ValueError(f"Steam enthalpy cannot be negative: {steam_enthalpy_btu_lb}")
        return amt * _STEAM_MASS_LB[u] * enth / 1e6
    if steam_enthalpy not in (None, ""):
        enth = float(steam_enthalpy)
        if enth < 0:
            raise ValueError(f"Steam enthalpy cannot be negative: {steam_enthalpy}")
        return amt * enth
    raise ValueError(f"A steam mass in '{unit}' needs its enthalpy (steam_enthalpy_btu_lb: Btu/lb above saturated "
                     "water at 212 F, from steam tables; API Compendium Equation 8-1)")


class IndirectSteamCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Indirect Steam/Heat", "Section 8.1")

    def calculate(
        self,
        heat_energy,
        ef_co2,
        boiler_efficiency,
        transmission_loss,
        uncertainties,
        heat_unit="btu",
        ef_ch4=0.0,
        ef_n2o=0.0,
        gwp_dict=None,
        steam_enthalpy=None,
        steam_enthalpy_btu_lb=None,
    ):
        """
        API Compendium 2021 section 8.1.5: steam / heat emissions = energy / net efficiency x boiler fuel EF,
        net efficiency = boiler efficiency x (1 - transmission loss) (docs/calculation-specification.md 5.2;
        Exhibit 8.3 subtracts the loss from the efficiency instead, 1 % more emissions at 92 % / 10 %)

        heat_unit: an energy unit, or a steam mass unit with its enthalpy (see heat_to_mmbtu)
        """
        self.validate_inputs({"energy": heat_energy}, ["energy"])

        energy_btu = heat_to_mmbtu(heat_energy, heat_unit or "btu", steam_enthalpy, steam_enthalpy_btu_lb) * 1e6

        def _parse_e(val, default):
            if val in (None, "", "-"):
                return default
            s = str(val).strip()
            v = float(s.replace("%", "").strip())
            return v / 100.0 if "%" in s else v

        b_eff = _parse_e(boiler_efficiency, 0.80)  # EPA Hub Table 7 basis
        t_loss = _parse_e(transmission_loss, 0.0)
        if not (0 <= b_eff <= 1 and 0 <= t_loss <= 1):
            raise ValueError(f"Boiler efficiency ({b_eff}) and transmission loss ({t_loss}) are fractions between 0 and 1")
        net_efficiency = b_eff * (1.0 - t_loss)
        if net_efficiency <= 0:
            raise ValueError(
                f"Net efficiency must be greater than 0 (got {net_efficiency:.4f}). "
                f"Check boiler efficiency ({b_eff}) and transmission loss ({t_loss})."
            )

        # ef_co2 is expected in kg/MMBtu
        if float(ef_co2) < 0:
            raise ValueError("CO2 emission factor cannot be negative")
        if float(ef_ch4 or 0.0) < 0:
            raise ValueError("CH4 emission factor cannot be negative")
        if float(ef_n2o or 0.0) < 0:
            raise ValueError("N2O emission factor cannot be negative")
        fuel_mmbtu = (energy_btu / 1_000_000.0) / net_efficiency
        co2_tonnes = fuel_mmbtu * float(ef_co2) / 1000.0
        # boiler fuel CH4 / N2O (kg/MMBtu of fuel, e.g. Table 4-6); they were left out (catalog check)
        ch4_tonnes = fuel_mmbtu * float(ef_ch4 or 0.0) / 1000.0
        n2o_tonnes = fuel_mmbtu * float(ef_n2o or 0.0) / 1000.0
        total_co2e = calculate_co2e(co2=co2_tonnes, ch4=ch4_tonnes, n2o=n2o_tonnes, gwp_dict=gwp_dict)

        _unc_dict = uncertainties or {}
        _tier = resolve_tier(_unc_dict.get("_factor_source", "default"))
        co2_res = propagate_uncertainty(
            co2_tonnes,
            resolve_ef_uncertainty("indirect", "co2", _tier, _unc_dict.get("co2")),
            tier=_tier,
            process_category="indirect",
            gas="co2",
        )

        return self.format_result(
            co2=co2_res,
            ch4=ch4_tonnes,
            n2o=n2o_tonnes,
            total_co2e=total_co2e,
            inputs={
                "heat_energy": heat_energy,
                "heat_unit": heat_unit,
                "energy_btu": energy_btu,
                "boiler_efficiency": boiler_efficiency,
                "transmission_loss": transmission_loss,
            },
        )


class CogenAllocationCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Cogeneration Allocation", "Section 8.3")

    def calculate(
        self,
        total_emissions,
        heat_output,
        power_output,
        method="wri_efficiency",
        uncertainties=None,
        heat_unit="mmbtu",
        power_unit="mmbtu",
        heat_efficiency=None,
        power_efficiency=None,
    ):
        """
        API Section 8.3 - Allocation of Cogeneration Emissions
        Methods: wri_efficiency (Equation 8-5), energy_content
        """
        self.validate_inputs(
            {
                "total_emissions": total_emissions,
                "heat_output": heat_output,
                "power_output": power_output,
            },
            ["total_emissions", "heat_output", "power_output"],
        )

        if float(total_emissions) < 0:
            raise ValueError(f"Total emissions cannot be negative: {total_emissions}")

        heat_mmbtu = heat_to_mmbtu(heat_output, heat_unit or "mmbtu")
        power_mmbtu = heat_to_mmbtu(power_output, power_unit or "mmbtu")
        if method not in ("wri_efficiency", "energy_content"):  # it was read as energy content
            raise ValueError(f"Unknown cogeneration allocation method '{method}' (wri_efficiency or energy_content)")

        if method == "wri_efficiency":
            # API Equation 8-5: WRI/WBCSD Efficiency Method. Without the plant's actual efficiencies,
            # the Compendium (section 8.2.2, EPA Climate Leaders / WRI tool) defaults are 80 % for heat
            # and 35 % for electricity (the 33 % in Exhibit 8.4 is that plant's known efficiency)
            def _eff(v, default, name):
                if v in (None, ""):
                    return default
                s = str(v).replace("%", "").strip()
                val = float(s)
                val = val / 100.0 if ("%" in str(v) or val > 1.0) else val
                if not 0 < val <= 1:
                    raise ValueError(f"{name} efficiency must be between 0 and 100 %")
                return val
            e_h = _eff(heat_efficiency, 0.80, "Heat")
            e_p = _eff(power_efficiency, 0.35, "Power")
            # Each output's "virtual fuel input" = its energy output / reference efficiency (Eq 8-5).
            # The denominator must be the sum of these efficiency-weighted shares, not the raw MMBtu
            # outputs (bug: the shared line below used to overwrite this with raw shares, making the
            # efficiency weighting have no effect on the allocation ratio).
            heat_share, power_share = heat_mmbtu / e_h, power_mmbtu / e_p
            denominator = heat_share + power_share
        else:
            # Energy-content allocation: shares are the raw energy outputs in MMBtu.
            heat_share, power_share = heat_mmbtu, power_mmbtu
            denominator = heat_share + power_share
        allocated_heat = heat_share / denominator * total_emissions if denominator > 0 else 0.0  # no heat bought
        allocated_power = power_share / denominator * total_emissions if denominator > 0 else 0.0

        _unc_dict = uncertainties or {}
        _tier = resolve_tier(_unc_dict.get("_factor_source", "default"))
        co2_res = propagate_uncertainty(
            allocated_heat,
            resolve_ef_uncertainty("indirect", "co2", _tier, _unc_dict.get("co2")),
            tier=_tier,
            process_category="indirect",
            gas="co2",
        )

        return self.format_result(
            co2=co2_res,
            total_co2e=calculate_co2e(co2=allocated_heat),
            inputs={
                "total_emissions": total_emissions,
                "heat_output": heat_output,
                "power_output": power_output,
                "method": method,
            },
            metadata={
                "allocated_heat_tonnes": allocated_heat,
                "allocated_power_tonnes": allocated_power,
                "allocation_method": f"api2021_cogen_{method}",
            },
        )
