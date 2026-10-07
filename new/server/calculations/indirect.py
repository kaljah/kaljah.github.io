"""
API Compendium 2021 - Section 8: Indirect Emissions
Implementation of indirect steam/heat and cogeneration allocation methodologies.
"""

from .base import BaseCalculator
from .units import calculate_co2e
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty


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
    ):
        """
        API Equation 8-2: Indirect emissions from steam/heat
        Emissions = Energy / (Eff_boiler - Eff_loss) * EF

        heat_unit: 'btu' (default), 'mmbtu', or 'kwh'  — CALC-02 FIX
        """
        self.validate_inputs({"energy": heat_energy}, ["energy"])

        # Normalize input energy or steam mass to BTU
        u = str(heat_unit or "btu").lower().replace(" ", "")
        if u in ["kwh", "kw-hr", "kilowatthour"]:
            energy_btu = heat_energy * 3412.142  # 1 kWh = 3412.142 BTU
        elif u in ["mmbtu", "mm_btu"]:
            energy_btu = heat_energy * 1_000_000.0
        elif u in ["gj", "gigajoule"]:
            energy_btu = heat_energy * 947817.12  # 1 GJ = 947,817 BTU
        elif u in ["mj", "megajoule"]:
            energy_btu = heat_energy * 947.817
        elif u in ["therm", "therms"]:
            energy_btu = heat_energy * 100_000.0
        elif u in ["mwh", "mw-hr"]:
            energy_btu = heat_energy * 3_412_142.0
        elif u in ["ton", "us_ton", "short_ton"]:
            # Standard saturated steam (~1000 BTU/lb): 1 US ton = 2,000,000 BTU
            energy_btu = heat_energy * 2_000_000.0
        elif u in ["tonne", "metric_ton", "mt"]:
            # 1 metric tonne = 2204.62 lb -> 2,204,620 BTU
            energy_btu = heat_energy * 2_204_620.0
        elif u in ["mlb", "klb", "thousand_lbs"]:
            # 1,000 lbs steam -> 1,000,000 BTU
            energy_btu = heat_energy * 1_000_000.0
        elif u in ["lb", "lbs", "pound", "pounds"]:
            energy_btu = heat_energy * 1000.0
        elif u in ["kg", "kilogram"]:
            energy_btu = heat_energy * 2204.62
        else:  # assume BTU
            energy_btu = heat_energy

        # GHG Protocol Scope 2 & API Eq 8-2: Multiplicative net efficiency
        # Net efficiency = Boiler Efficiency * (1 - Transmission Loss)
        b_eff = float(0.80 if boiler_efficiency in (None, "") else boiler_efficiency)
        t_loss = float(0.0 if transmission_loss in (None, "") else transmission_loss)
        net_efficiency = b_eff * (1.0 - t_loss)
        if net_efficiency <= 0:
            raise ValueError(
                f"Net efficiency must be greater than 0 (got {net_efficiency:.4f}). "
                f"Check boiler efficiency ({b_eff}) and transmission loss ({t_loss})."
            )

        # ef_co2 is expected in kg/MMBtu
        fuel_mmbtu = (energy_btu / 1_000_000.0) / net_efficiency
        co2_tonnes = fuel_mmbtu * ef_co2 / 1000.0
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
        Methods: wri_efficiency, energy_content, uk_ets
        """
        self.validate_inputs(
            {
                "total_emissions": total_emissions,
                "heat_output": heat_output,
                "power_output": power_output,
            },
            ["total_emissions", "heat_output", "power_output"],
        )

        p_unit = str(power_unit or "mmbtu").lower().strip()
        if p_unit in ["mwh", "megawatt_hours", "kwh"]:
            mult = 3.412142 if p_unit != "kwh" else 0.003412142
            power_mmbtu = power_output * mult
        else:
            power_mmbtu = power_output

        if method == "wri_efficiency":
            # API Equation 8-5: WRI/WBCSD Efficiency Method. Without the plant's actual efficiencies,
            # the Compendium (section 8.2.2, EPA Climate Leaders / WRI tool) defaults are 80 % for heat
            # and 35 % for electricity (the 33 % in Exhibit 8.4 is that plant's known efficiency)
            def _eff(v, default, name):
                if v in (None, ""):
                    return default
                v = float(v)
                v = v / 100.0 if v > 1.0 else v
                if not 0 < v <= 1:
                    raise ValueError(f"{name} efficiency must be between 0 and 100 %")
                return v
            e_h = _eff(heat_efficiency, 0.80, "Heat")
            e_p = _eff(power_efficiency, 0.35, "Power")
            denominator = (heat_output / e_h) + (power_mmbtu / e_p)
            allocated_heat = ((heat_output / e_h) / denominator) * total_emissions if denominator > 0 else 0.0
            allocated_power = ((power_mmbtu / e_p) / denominator) * total_emissions if denominator > 0 else 0.0
        else:
            # Energy content allocation
            denominator = heat_output + power_mmbtu
            allocated_heat = (heat_output / denominator) * total_emissions if denominator > 0 else 0.0
            allocated_power = (power_mmbtu / denominator) * total_emissions if denominator > 0 else 0.0

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
