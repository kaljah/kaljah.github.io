"""
Independent Scope 3 Value Chain Reference Models.
Source of Truth: GHG Protocol Corporate Value Chain (Scope 3) Standard, EPA USEEIO v1.3.
Zero production dependencies.
"""

class IndependentScope3Model:
    @staticmethod
    def calculate(activity_amount, emission_factor, factor_unit="", calc_method=""):
        amt = float(activity_amount or 0.0)
        ef = float(emission_factor or 0.0)
        if amt <= 0.0 or ef <= 0.0:
            return {"co2e": 0.0}

        u = str(factor_unit or "").lower().strip()
        m = str(calc_method or "").lower().strip()

        # 1. EEIO / Spend-based per-$1,000 factor check
        is_per_thousand = any(k in u for k in ["1000", "1,000", "1k", "$1000", "$1k"]) or ("eeio" in m and not any(t in u for t in ["tonne", "tco2", "mtco2"]))
        if is_per_thousand:
            co2e_t = (amt * ef) / 1_000_000.0
            return {"co2e": co2e_t, "method": "spend_eeio"}

        # 2. Extract numerator before '/' or ' per '
        num = u.split("/")[0].split(" per ")[0].strip()

        # 3. Check if numerator specifies metric tonnes
        is_tonne_num = False
        if not any(p in num for p in ["kg", "kilogram", " g", "gram", "lb", "pound"]):
            if any(t in num for t in ["tonne", "metric_ton", "tco2", "mtco2", "t/"]) or num.startswith("t ") or num == "t":
                is_tonne_num = True

        if is_tonne_num:
            co2e_t = amt * ef
            return {"co2e": co2e_t, "method": "tonne_factor"}
        else:
            # Standard kg CO2e / unit -> metric tonnes
            co2e_t = (amt * ef) / 1000.0
            return {"co2e": co2e_t, "method": "kg_factor"}
