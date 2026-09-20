"""
Independent Scope 2 Purchased Energy Reference Models.
Source of Truth: GHG Protocol Scope 2 Guidance, API Compendium 2021 §8.1, §8.3 (Equation 8-2, 8-5).
Zero production dependencies.
"""
from .unit_conversions import IndependentUnitConverter


class IndependentScope2Model:
    @staticmethod
    def calculate_electricity(kwh, grid_ef):
        k = float(kwh or 0.0)
        ef = float(grid_ef or 0.0)
        co2e_t = (k * ef) / 1000.0
        return {"co2e": co2e_t, "co2": co2e_t, "ch4": 0.0, "n2o": 0.0}

    @staticmethod
    def calculate_indirect_steam(amount, unit="mmbtu", boiler_eff=0.80, trans_loss=0.0, ef_co2=53.06):
        amt = float(amount or 0.0)
        u = str(unit or "mmbtu").strip().lower().replace(" ", "")

        # Normalization to MMBtu from first principles
        if u in ["btu"]:
            energy_mmbtu = amt / 1_000_000.0
        elif u in ["mj"]:
            energy_mmbtu = amt * 0.0009478171203133172
        elif u in ["gj"]:
            energy_mmbtu = amt * 0.9478171203133172
        elif u in ["kwh"]:
            energy_mmbtu = amt * 0.003412141633
        elif u in ["mwh"]:
            energy_mmbtu = amt * 3.412141633
        elif u in ["therm", "therms"]:
            energy_mmbtu = amt * 0.1
        elif u in ["ton", "us_ton", "short_ton"]:
            energy_mmbtu = amt * 2.0  # standard saturated steam enthalpy (2.0 MMBtu / ton)
        elif u in ["tonne", "metric_ton", "mt"]:
            energy_mmbtu = amt * 2.20462  # 2.20462 MMBtu / tonne steam
        elif u in ["mlb", "klb", "thousand_lbs"]:
            energy_mmbtu = amt * 1.0  # 1,000 lbs steam = 1.0 MMBtu
        elif u in ["lb", "lbs"]:
            energy_mmbtu = amt * 0.001
        elif u in ["kg"]:
            energy_mmbtu = amt * 0.00220462
        else:
            energy_mmbtu = amt

        b_eff = float(boiler_eff or 0.80)
        if b_eff > 1.0:
            b_eff /= 100.0
        t_loss = float(trans_loss or 0.0)
        if t_loss > 1.0:
            t_loss /= 100.0

        net_eff = b_eff * (1.0 - t_loss)
        if net_eff <= 0:
            raise ValueError(f"Net efficiency must be > 0 (got {net_eff})")

        f_co2 = float(ef_co2 or 53.06)
        co2_kg = (energy_mmbtu * f_co2) / net_eff
        co2_t = co2_kg / 1000.0
        return {
            "co2e": co2_t,
            "co2": co2_t,
            "ch4": 0.0,
            "n2o": 0.0,
            "energy_mmbtu": energy_mmbtu,
            "net_efficiency": net_eff,
        }

    @staticmethod
    def calculate_cogen_allocation(total_emissions, heat_output, power_output, method="wri_efficiency"):
        tot = float(total_emissions or 0.0)
        heat = float(heat_output or 0.0)
        power = float(power_output or 0.0)
        m = str(method or "wri_efficiency").lower().strip()

        if m == "wri_efficiency":
            e_h = 0.80
            e_p = 0.33
            denom = (heat / e_h) + (power / e_p)
            allocated_heat = ((heat / e_h) / denom) * tot if denom > 0 else 0.0
            allocated_power = ((power / e_p) / denom) * tot if denom > 0 else 0.0
        else:
            denom = heat + power
            allocated_heat = (heat / denom) * tot if denom > 0 else 0.0
            allocated_power = (power / denom) * tot if denom > 0 else 0.0

        return {
            "allocated_heat_co2e": allocated_heat,
            "allocated_power_co2e": allocated_power,
            "total_emissions": tot,
        }
