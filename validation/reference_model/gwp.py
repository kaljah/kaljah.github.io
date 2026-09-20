"""
Independent Global Warming Potential (GWP) and CO2e Normalization Model.
Source of Truth: IPCC AR4 (2007), IPCC AR5 (2013), IPCC AR6 (2021).
Zero production dependencies.
"""

INDEPENDENT_GWP_REGISTRY = {
    "AR4": {
        "100": {"CO2": 1.0, "CH4": 25.0, "N2O": 298.0},
        "20": {"CO2": 1.0, "CH4": 72.0, "N2O": 289.0},
    },
    "AR5": {
        "100": {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0},
        "20": {"CO2": 1.0, "CH4": 82.5, "N2O": 268.0},
    },
    "AR6": {
        "100": {"CO2": 1.0, "CH4": 27.9, "N2O": 273.0},
        "20": {"CO2": 1.0, "CH4": 82.5, "N2O": 273.0},
    },
}

DEFAULT_STANDARD = "AR5"
DEFAULT_HORIZON = "100"


class IndependentGWPModel:
    @staticmethod
    def get_gwp(standard=DEFAULT_STANDARD, horizon=DEFAULT_HORIZON, custom_override=None):
        if custom_override and isinstance(custom_override, dict) and "CH4" in custom_override:
            return {
                "CO2": float(custom_override.get("CO2", 1.0)),
                "CH4": float(custom_override.get("CH4", 28.0)),
                "N2O": float(custom_override.get("N2O", 265.0)),
            }
        std = str(standard or DEFAULT_STANDARD).upper().strip()
        hz = str(horizon or DEFAULT_HORIZON).strip()
        profile = INDEPENDENT_GWP_REGISTRY.get(std, INDEPENDENT_GWP_REGISTRY["AR5"])
        return profile.get(hz, profile["100"])

    @staticmethod
    def calculate_co2e(co2=0.0, ch4=0.0, n2o=0.0, standard=DEFAULT_STANDARD, horizon=DEFAULT_HORIZON, gwp_dict=None):
        factors = IndependentGWPModel.get_gwp(standard=standard, horizon=horizon, custom_override=gwp_dict)
        c = float(co2 or 0.0)
        m = float(ch4 or 0.0)
        n = float(n2o or 0.0)
        return (c * factors["CO2"]) + (m * factors["CH4"]) + (n * factors["N2O"])
