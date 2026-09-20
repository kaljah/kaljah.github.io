"""
Independent Fugitive Emissions Reference Models.
Source of Truth: API Compendium 2021 §7.2, Table 7-1, Table 7-3.
Zero production dependencies.
"""
from .unit_conversions import IndependentUnitConverter
from .gwp import IndependentGWPModel


class IndependentFugitiveModel:
    @staticmethod
    def calculate_component(component_counts, ch4_content=0.85, gwp_standard="AR5", gwp_horizon="100"):
        c1 = float(ch4_content or 0.85)
        if c1 > 1.0:
            c1 /= 100.0

        total_ch4_kg_hr = 0.0
        for comp, data in component_counts.items():
            if isinstance(data, dict):
                cnt = float(data.get("count", 0) or 0)
                ef = float(data.get("ef", 0) or 0)
                is_m = bool(data.get("is_methane")) or any(x in str(data.get("unit", "")).lower() for x in ["ch4", "methane"])
            else:
                cnt = float(data or 0)
                ef = 0.0
                is_m = False
            scaling = 1.0 if is_m else c1
            total_ch4_kg_hr += cnt * ef * scaling

        ch4_t = (total_ch4_kg_hr * 8760.0) / 1000.0
        co2e = IndependentGWPModel.calculate_co2e(ch4=ch4_t, standard=gwp_standard, horizon=gwp_horizon)
        return {"ch4": ch4_t, "co2": 0.0, "n2o": 0.0, "co2e": co2e}

    @staticmethod
    def calculate_equipment(count, ef, ef_unit="kg/hr", ch4_content=0.85, gwp_standard="AR5", gwp_horizon="100"):
        cnt = float(count or 0.0)
        f = float(ef or 0.0)
        u = str(ef_unit or "kg/hr").strip().lower()
        c1 = float(ch4_content or 0.85)
        if c1 > 1.0:
            c1 /= 100.0

        is_tonne = "tonne" in u or "mt" in u
        is_methane = any(x in u for x in ["ch4", "methane"])
        is_annual = "yr" in u or "year" in u

        raw = cnt * f
        if not is_methane:
            raw *= c1

        if is_annual:
            ch4_t = raw if is_tonne else (raw / 1000.0)
        else:
            annual_kg = raw * 8760.0
            ch4_t = annual_kg if is_tonne else (annual_kg / 1000.0)

        co2e = IndependentGWPModel.calculate_co2e(ch4=ch4_t, standard=gwp_standard, horizon=gwp_horizon)
        return {"ch4": ch4_t, "co2": 0.0, "n2o": 0.0, "co2e": co2e}

    @staticmethod
    def calculate_compressor_seal(count, seal_type="reciprocating", gwp_standard="AR5", gwp_horizon="100"):
        cnt = float(count or 0.0)
        st = str(seal_type or "reciprocating").strip().lower()
        if "dry" in st:
            ef = 1.5
        elif "wet" in st:
            ef = 15.0
        else:
            ef = 1.2

        total_kg_hr = cnt * ef
        ch4_t = (total_kg_hr * 8760.0) / 1000.0
        co2e = IndependentGWPModel.calculate_co2e(ch4=ch4_t, standard=gwp_standard, horizon=gwp_horizon)
        return {"ch4": ch4_t, "co2": 0.0, "n2o": 0.0, "co2e": co2e, "ef_used": ef}

    @staticmethod
    def calculate_screening(comp_count, ef_base, ppm, hours=8760.0, ch4_fraction=1.0, is_tonne=False, is_annual=False, is_methane=True, gwp_standard="AR5", gwp_horizon="100"):
        cnt = float(comp_count or 0.0)
        ef = float(ef_base or 0.0)
        p = float(ppm or 0.0)
        c1 = float(ch4_fraction or 1.0)
        if c1 > 1.0:
            c1 /= 100.0

        mult = 2.5 if p >= 10000.0 else 1.0
        h = float(hours or 8760.0)

        if is_annual:
            ratio = h / 8760.0
            raw = cnt * ef * mult * ratio
        else:
            raw = cnt * ef * mult * h

        if not is_methane:
            raw *= c1

        ch4_t = raw if is_tonne else (raw / 1000.0)
        co2e = IndependentGWPModel.calculate_co2e(ch4=ch4_t, standard=gwp_standard, horizon=gwp_horizon)
        return {"ch4": ch4_t, "co2": 0.0, "n2o": 0.0, "co2e": co2e, "mult": mult}
