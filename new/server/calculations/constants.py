# AR4 GWP Values (IPCC 4th Assessment Report, 2007) — kept for reference only
# NOTE: This dict is NOT used anywhere. DEFAULT_GWP correctly points to GWP_AR5 below.
GWP_DEFAULT_GWP = {
    'CO2': 1,
    'CH4': 25,  # AR4
    'N2O': 298  # AR4
}

GWP_AR4 = {
    'CO2': 1,
    'CH4': 25,
    'N2O': 298
}

GWP_AR5 = {
    'CO2': 1,
    'CH4': 28,   # IPCC AR5 WG1 Table 8.7 (2013)
    'N2O': 264   # IPCC AR5 WG1 Table 8.7 (2013) — correct value; 265 was wrong (CALC-04 FIX)
}

GWP_AR6 = {
    'CO2': 1,
    'CH4': 27.9, # AR6 (2021)
    'N2O': 273   # AR6 (2021)
}

# Standard GWP for the application (default to AR5)
DEFAULT_GWP = GWP_AR5
