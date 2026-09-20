"""
Independent Combustion & Flaring Reference Models.
Source of Truth: API Compendium 2021 §5.1, §5.2 (Equations 5-3, 5-4).
Zero production dependencies.
"""
from .unit_conversions import (
    IndependentUnitConverter,
    normalize_to_standard_volume,
    DENSITY_CH4_STD,
    DENSITY_CO2_STD,
)
from .gwp import IndependentGWPModel


class IndependentCombustionModel:
    @staticmethod
    def calculate_tier1_2(
        fuel_quantity,
        fuel_unit,
        emission_factors,
        fuel_type="natural_gas",
        hhv=None,
        gwp_standard="AR5",
        gwp_horizon="100",
    ):
        qty = float(fuel_quantity or 0.0)
        u_fuel = str(fuel_unit or "m3").strip().lower()
        f_co2 = float(emission_factors.get("co2") or emission_factors.get("ef_co2") or 0.0)
        f_ch4 = float(emission_factors.get("ch4") or emission_factors.get("ef_ch4") or 0.0)
        f_n2o = float(emission_factors.get("n2o") or emission_factors.get("ef_n2o") or 0.0)
        f_unit = str(emission_factors.get("unit") or "kg/unit").strip().lower()

        # Handle Energy-based factor denominator (kg/MMBtu)
        if "mmbtu" in f_unit:
            if u_fuel in ["mmbtu", "mm_btu"]:
                energy_mmbtu = qty
            elif u_fuel in ["gj", "gigajoule"]:
                energy_mmbtu = qty * 0.947817
            elif u_fuel in ["therm", "therms"]:
                energy_mmbtu = qty * 0.1
            elif u_fuel in ["kwh"]:
                energy_mmbtu = qty * 0.003412142
            else:
                fuel_lower = str(fuel_type or "").lower()
                is_liquid = any(x in fuel_lower for x in ["oil", "diesel", "crude", "petrol", "gasoline", "liquid"]) or u_fuel in ["bbl", "gal", "l", "liter"]
                if is_liquid:
                    hhv_liq = float(hhv or 138000.0)
                    gal = IndependentUnitConverter.convert(qty, u_fuel, "gal")
                    energy_mmbtu = (gal * hhv_liq) / 1_000_000.0
                else:
                    hhv_gas = float(hhv or 1020.0)
                    scf = IndependentUnitConverter.convert(qty, u_fuel, "scf")
                    energy_mmbtu = (scf * hhv_gas) / 1_000_000.0

            co2_kg = energy_mmbtu * f_co2
            ch4_kg = energy_mmbtu * f_ch4
            n2o_kg = energy_mmbtu * f_n2o
        else:
            # Physical unit conversion: convert activity quantity to factor denominator unit
            f_denom = f_unit.split("/")[1].strip() if "/" in f_unit else "m3"
            qty_in_f_denom = IndependentUnitConverter.convert(qty, u_fuel, f_denom)
            co2_kg = qty_in_f_denom * f_co2
            ch4_kg = qty_in_f_denom * f_ch4
            n2o_kg = qty_in_f_denom * f_n2o

        # Check numerator unit of EF (kg vs tonne vs gram)
        f_num = (f_unit.split("/")[0].strip().lower() if "/" in f_unit else f_unit.lower())
        if f_num in ["t", "tonne", "tonnes", "metric_ton", "metric_tons", "t co2", "tco2", "mt"]:
            co2_t = co2_kg
            ch4_t = ch4_kg
            n2o_t = n2o_kg
        elif f_num in ["g", "gram", "grams"]:
            co2_t = co2_kg / 1_000_000.0
            ch4_t = ch4_kg / 1_000_000.0
            n2o_t = n2o_kg / 1_000_000.0
        else:
            # Default is kg
            co2_t = co2_kg / 1000.0
            ch4_t = ch4_kg / 1000.0
            n2o_t = n2o_kg / 1000.0

        co2e = IndependentGWPModel.calculate_co2e(co2_t, ch4_t, n2o_t, standard=gwp_standard, horizon=gwp_horizon)
        return {"co2": co2_t, "ch4": ch4_t, "n2o": n2o_t, "co2e": co2e}

    @staticmethod
    def calculate_tier3(
        fuel_quantity,
        fuel_unit,
        composition,
        combustion_efficiency=0.995,
        operating_temp=None,
        temp_unit="C",
        operating_press=None,
        press_unit="psig",
        z_factor=1.0,
        gwp_standard="AR5",
        gwp_horizon="100",
    ):
        qty = float(fuel_quantity or 0.0)
        u_fuel = str(fuel_unit or "m3").strip().lower()
        vol_m3_actual = IndependentUnitConverter.convert(qty, u_fuel, "m3")
        vol_m3_std = normalize_to_standard_volume(
            vol_m3_actual,
            operating_temp=operating_temp,
            temp_unit=temp_unit,
            operating_press=operating_press,
            press_unit=press_unit,
            z_factor=z_factor,
        )

        eta_c = float(combustion_efficiency or 0.995)
        if eta_c > 1.0:
            eta_c /= 100.0
        eta_c = max(0.0, min(1.0, eta_c))

        # Carbon moles per mole of gas from C1-C10
        moles_c = 0.0
        for i in range(1, 11):
            key = f"c{i}"
            val = float(composition.get(key) or 0.0)
            if val > 1.0:
                val /= 100.0
            moles_c += i * val

        co2_native = float(composition.get("co2_mol") or composition.get("co2_comp") or 0.0)
        if co2_native > 1.0:
            co2_native /= 100.0

        c1_frac = float(composition.get("c1") or 0.0)
        if c1_frac > 1.0:
            c1_frac /= 100.0

        # Emissions in kg
        co2_combusted_kg = vol_m3_std * moles_c * eta_c * DENSITY_CO2_STD
        co2_native_kg = vol_m3_std * co2_native * DENSITY_CO2_STD
        co2_t = (co2_combusted_kg + co2_native_kg) / 1000.0

        ch4_slip_kg = vol_m3_std * c1_frac * (1.0 - eta_c) * DENSITY_CH4_STD
        ch4_t = ch4_slip_kg / 1000.0
        n2o_t = 0.0

        co2e = IndependentGWPModel.calculate_co2e(co2_t, ch4_t, n2o_t, standard=gwp_standard, horizon=gwp_horizon)
        return {
            "co2": co2_t,
            "ch4": ch4_t,
            "n2o": n2o_t,
            "co2e": co2e,
            "vol_m3_std": vol_m3_std,
            "moles_c": moles_c,
        }


class IndependentFlaringModel:
    @staticmethod
    def calculate(
        gas_volume,
        volume_unit,
        ch4_fraction,
        flare_type="elevated",
        combustion_eff=None,
        destruction_eff=None,
        composition=None,
        ef_n2o=0.0,
        ef_unit="kg/m3",
        hhv=1020.0,
        operating_temp=None,
        temp_unit="C",
        operating_press=None,
        press_unit="psig",
        z_factor=1.0,
        gwp_standard="AR5",
        gwp_horizon="100",
    ):
        qty = float(gas_volume or 0.0)
        u_vol = str(volume_unit or "m3").strip().lower()
        vol_m3_actual = IndependentUnitConverter.convert(qty, u_vol, "m3")
        vol_m3_std = normalize_to_standard_volume(
            vol_m3_actual,
            operating_temp=operating_temp,
            temp_unit=temp_unit,
            operating_press=operating_press,
            press_unit=press_unit,
            z_factor=z_factor,
        )

        # Default efficiencies by flare type
        ft = str(flare_type or "elevated").lower().strip().replace("-", "_").replace(" ", "_")
        if ft in ["enclosed", "enclosed_ground", "ground"]:
            default_eta_c, default_eta_d = 0.996, 0.995
        elif ft in ["pit", "open_pit", "candle"]:
            default_eta_c, default_eta_d = 0.920, 0.950
        else:  # elevated, pipe, default
            default_eta_c, default_eta_d = 0.984, 0.980

        eta_c = float(combustion_eff if combustion_eff is not None else default_eta_c)
        if eta_c > 1.0:
            eta_c /= 100.0
        eta_c = max(0.0, min(1.0, eta_c))

        eta_d = float(destruction_eff if destruction_eff is not None else default_eta_d)
        if eta_d > 1.0:
            eta_d /= 100.0
        eta_d = max(0.0, min(1.0, eta_d))

        comps = composition or {}
        c1 = float(comps.get("c1") if comps.get("c1") is not None else ch4_fraction or 0.0)
        if c1 > 1.0:
            c1 /= 100.0

        moles_c = 0.0
        for i in range(1, 11):
            key = f"c{i}"
            val = float(comps.get(key) if comps.get(key) is not None else (c1 if i == 1 else 0.0))
            if val > 1.0:
                val /= 100.0
            moles_c += i * val

        co2_native = float(comps.get("co2_mol") or comps.get("co2_comp") or 0.0)
        if co2_native > 1.0:
            co2_native /= 100.0

        # 1. Unburnt Methane Emissions
        ch4_unburnt_kg = vol_m3_std * c1 * (1.0 - eta_d) * DENSITY_CH4_STD
        ch4_t = ch4_unburnt_kg / 1000.0

        # 2. Total CO2 (Combusted Hydrocarbons + Native CO2)
        co2_combusted_kg = vol_m3_std * moles_c * eta_c * DENSITY_CO2_STD
        co2_native_kg = vol_m3_std * co2_native * DENSITY_CO2_STD
        co2_t = (co2_combusted_kg + co2_native_kg) / 1000.0

        # 3. Flared N2O
        n2o_t = 0.0
        if ef_n2o and float(ef_n2o) > 0:
            ef_u = str(ef_unit or "kg/m3").lower()
            if "mmbtu" in ef_u:
                scf = vol_m3_std / 0.028316846592
                mmbtu = (scf * float(hhv or 1020.0)) / 1_000_000.0
                n2o_t = (mmbtu * float(ef_n2o)) / 1000.0
            else:
                n2o_kg = vol_m3_std * float(ef_n2o)
                n2o_t = n2o_kg / 1000.0

        co2e = IndependentGWPModel.calculate_co2e(co2_t, ch4_t, n2o_t, standard=gwp_standard, horizon=gwp_horizon)
        return {
            "co2": co2_t,
            "ch4": ch4_t,
            "n2o": n2o_t,
            "co2e": co2e,
            "vol_m3_std": vol_m3_std,
            "eta_c": eta_c,
            "eta_d": eta_d,
        }
