"""
Grid Emission Factors - electricity_factors.py
Central registry for location-based Scope 2 electricity emission factors.

co2 / ch4 / n2o are kg per kWh (= tonne per MWh). routes/scope2.resolve_electricity_factor converts
them to kg CO2e/kWh with the active GWP set; `factor` is that value at AR5 (reference only).

Sources: API Compendium 2021 Table 8-2 (U.S. eGRID2019 subregions, CO2 / CH4 / N2O) and Table 8-6
(European grid averages, AIB 2020 production mix, CO2 only). The Algerian grid is not in the
Compendium: its value is carried over from the original catalog and is NOT verified.
"""

_AR5 = {"CH4": 28.0, "N2O": 265.0}


def _grid(co2, ch4=0.0, n2o=0.0, description="", source="", verified=True):
    return {"co2": co2, "ch4": ch4, "n2o": n2o,
            "factor": round(co2 + ch4 * _AR5["CH4"] + n2o * _AR5["N2O"], 6),
            "unit": "kg CO2e/kWh", "description": description, "source": source, "verified": verified}


GRID_FACTORS = {
    # not in the API Compendium; value from the original catalog ("Sonelgaz / IEA typical"), unverified:
    # replace with the published Sonelgaz / IEA factor, or enter a supplier factor
    "Algerian National Grid": {"co2": 0.522, "ch4": 0.0, "n2o": 0.0, "factor": 0.522, "unit": "kg CO2e/kWh",
                               "description": "Algerian electricity mix (primarily natural gas)",
                               "source": "Not in the API Compendium - unverified catalog value", "verified": False},
    "US Average": _grid(0.401, 3.40e-05, 4.99e-06, "U.S. average (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-AKGD (ASCC Alaska Grid)": _grid(0.505, 4.44e-05, 5.9e-06, "ASCC Alaska Grid (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-AKMS (ASCC Miscellaneous)": _grid(0.249, 1.18e-05, 1.81e-06, "ASCC Miscellaneous (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-AZNM (WECC Southwest)": _grid(0.432, 3.08e-05, 4.54e-06, "WECC Southwest (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-CAMX (WECC California)": _grid(0.206, 1.5e-05, 1.81e-06, "WECC California (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-ERCT (ERCOT All)": _grid(0.394, 2.59e-05, 3.63e-06, "ERCOT All (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-FRCC (FRCC All)": _grid(0.391, 2.49e-05, 3.17e-06, "FRCC All (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-HIMS (HICC Miscellaneous)": _grid(0.538, 6.49e-05, 9.98e-06, "HICC Miscellaneous (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-HIOA (HICC Oahu)": _grid(0.769, 8.39e-05, 1.27e-05, "HICC Oahu (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-MROE (MRO East)": _grid(0.682, 6.67e-05, 9.98e-06, "MRO East (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-MROW (MRO West)": _grid(0.498, 5.4e-05, 7.71e-06, "MRO West (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-NEWE (NPCC New England)": _grid(0.222, 3.49e-05, 4.54e-06, "NPCC New England (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-NWPP (WECC Northwest)": _grid(0.324, 3.08e-05, 4.54e-06, "WECC Northwest (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-NYCW (NPCC NYC/Westchester)": _grid(0.251, 9.52e-06, 9.07e-07, "NPCC NYC/Westchester (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-NYLI (NPCC Long Island)": _grid(0.548, 7.12e-05, 9.07e-06, "NPCC Long Island (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-NYUP (NPCC Upstate NY)": _grid(0.105, 7.71e-06, 9.07e-07, "NPCC Upstate NY (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-PRMS (Puerto Rico Miscellaneous)": _grid(0.697, 3.81e-05, 5.9e-06, "Puerto Rico Miscellaneous (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-RFCE (RFC East)": _grid(0.315, 2.4e-05, 3.17e-06, "RFC East (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-RFCM (RFC Michigan)": _grid(0.539, 5.17e-05, 7.26e-06, "RFC Michigan (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-RFCW (RFC West)": _grid(0.484, 4.49e-05, 6.35e-06, "RFC West (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-RMPA (WECC Rockies)": _grid(0.564, 5.31e-05, 7.71e-06, "WECC Rockies (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-SPNO (SPP North)": _grid(0.485, 5.08e-05, 7.26e-06, "SPP North (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-SPSO (SPP South)": _grid(0.454, 3.17e-05, 4.54e-06, "SPP South (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-SRMV (SERC Mississippi Valley)": _grid(0.366, 1.95e-05, 2.72e-06, "SERC Mississippi Valley (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-SRMW (SERC Midwest)": _grid(0.719, 7.67e-05, 1.13e-05, "SERC Midwest (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-SRSO (SERC South)": _grid(0.440, 3.22e-05, 4.54e-06, "SERC South (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-SRTV (SERC Tennessee Valley)": _grid(0.431, 3.95e-05, 5.9e-06, "SERC Tennessee Valley (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "US-SRVC (SERC Virginia/Carolina)": _grid(0.306, 2.63e-05, 3.63e-06, "SERC Virginia/Carolina (eGRID2019)", "API Compendium 2021 Table 8-2"),
    "Austria (grid average)": _grid(0.1112, description="Austria production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Belgium (grid average)": _grid(0.1619, description="Belgium production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Bulgaria (grid average)": _grid(0.3721, description="Bulgaria production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Switzerland (grid average)": _grid(0.0115, description="Switzerland production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Croatia (grid average)": _grid(0.2270, description="Croatia production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Cyprus (grid average)": _grid(0.6429, description="Cyprus production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Czech Republic (grid average)": _grid(0.4955, description="Czech Republic production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Denmark (grid average)": _grid(0.1425, description="Denmark production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Estonia (grid average)": _grid(0.5987, description="Estonia production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Finland (grid average)": _grid(0.0953, description="Finland production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "France (grid average)": _grid(0.0513, description="France production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Germany (grid average)": _grid(0.3387, description="Germany production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Greece (grid average)": _grid(0.4100, description="Greece production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Hungary (grid average)": _grid(0.2438, description="Hungary production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Ireland (grid average)": _grid(0.3360, description="Ireland production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Iceland (grid average)": _grid(0.0001, description="Iceland production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Italy (grid average)": _grid(0.3238, description="Italy production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Lithuania (grid average)": _grid(0.2536, description="Lithuania production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Luxembourg (grid average)": _grid(0.1014, description="Luxembourg production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Latvia (grid average)": _grid(0.2157, description="Latvia production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Malta (grid average)": _grid(0.3906, description="Malta production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Netherlands (grid average)": _grid(0.3743, description="Netherlands production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Norway (grid average)": _grid(0.0076, description="Norway production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Poland (grid average)": _grid(0.7596, description="Poland production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Portugal (grid average)": _grid(0.3016, description="Portugal production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Romania (grid average)": _grid(0.2618, description="Romania production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Serbia (grid average)": _grid(0.7767, description="Serbia production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Spain (grid average)": _grid(0.1710, description="Spain production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Sweden (grid average)": _grid(0.0057, description="Sweden production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Slovenia (grid average)": _grid(0.2241, description="Slovenia production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "Slovakia (grid average)": _grid(0.1555, description="Slovakia production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
    "United Kingdom (grid average)": _grid(0.1964, description="United Kingdom production mix 2020, CO2 only", source="API Compendium 2021 Table 8-6"),
}

# former names of rows that now carry a Compendium value
GRID_ALIASES = {
    "UK National Grid": "United Kingdom (grid average)",
    "US-ERCOT": "US-ERCT (ERCOT All)",
}


def grid_entry(name):
    """(canonical name, entry) of a grid region, case-insensitive, aliases resolved; (name, None) if unknown."""
    n = str(name or "").strip()
    n = GRID_ALIASES.get(n, n)
    for k, v in GRID_FACTORS.items():
        if k.lower() == n.lower():
            return k, v
    return n, None


def grid_factor_kg_co2e_per_kwh(entry, gwp=None):
    """kg CO2e / kWh of a grid entry with the given (or the active) GWP set."""
    if gwp is None:
        from calculations.constants import get_active_gwp
        gwp = get_active_gwp()
    return float(entry["co2"]) + float(entry.get("ch4") or 0) * float(gwp["CH4"]) + float(entry.get("n2o") or 0) * float(gwp["N2O"])
