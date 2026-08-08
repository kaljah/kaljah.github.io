"""
Global Warming Potential (GWP) Constants & Resolution Engine
Supports IPCC AR4 (2007), IPCC AR5 (2013), and IPCC AR6 (2021) standards.
"""

# IPCC 4th Assessment Report (AR4 - 2007)
GWP_AR4 = {
    'CO2': 1.0,
    'CH4': 25.0,
    'N2O': 298.0,
    'CH4_20': 72.0,
    'N2O_20': 289.0
}

# IPCC 5th Assessment Report (AR5 - 2013, WG1 Table 8.7)
GWP_AR5 = {
    'CO2': 1.0,
    'CH4': 28.0,
    'N2O': 265.0,
    'CH4_20': 82.5,
    'N2O_20': 268.0
}

# IPCC 6th Assessment Report (AR6 - 2021)
GWP_AR6 = {
    'CO2': 1.0,
    'CH4': 27.9,
    'N2O': 273.0,
    'CH4_20': 82.5,
    'N2O_20': 273.0
}

# Standard registry
GWP_STANDARDS = {
    'AR4': GWP_AR4,
    'AR5': GWP_AR5,
    'AR6': GWP_AR6
}

# Legacy alias for backward compatibility (resolves to AR5)
GWP_DEFAULT_GWP = GWP_AR5

# Standard GWP for the application (default to AR5)
DEFAULT_GWP = GWP_AR5


def get_active_gwp(standard=None, gwp_dict=None, horizon='100'):
    """
    Dynamically resolve the active GWP factors dictionary based on standard and horizon.
    
    :param standard: Optional standard key ('AR4', 'AR5', 'AR6')
    :param gwp_dict: Optional explicit override dictionary
    :param horizon: '100' (default) or '20' for 20-year horizon
    :return: dict with 'CO2', 'CH4', 'N2O'
    """
    if gwp_dict is not None and isinstance(gwp_dict, dict) and 'CH4' in gwp_dict:
        return gwp_dict

    std_key = str(standard or '').upper().strip()
    if not std_key:
        try:
            from routes.auth import _app_settings
            std_key = str(_app_settings.get('gwp_standard') or 'AR5').upper().strip()
        except Exception:
            std_key = 'AR5'

    std_profile = GWP_STANDARDS.get(std_key, GWP_AR5)

    if str(horizon) == '20':
        return {
            'CO2': 1.0,
            'CH4': std_profile.get('CH4_20', 82.5),
            'N2O': std_profile.get('N2O_20', 268.0)
        }

    return {
        'CO2': std_profile.get('CO2', 1.0),
        'CH4': std_profile.get('CH4', 28.0),
        'N2O': std_profile.get('N2O', 265.0)
    }
