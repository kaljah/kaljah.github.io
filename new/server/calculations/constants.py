"""
Global Warming Potential (GWP) Constants & Resolution Engine
Supports IPCC AR4 (2007), IPCC AR5 (2013), and IPCC AR6 (2021) standards.
"""

import time

# IPCC 4th Assessment Report (AR4 - 2007)
GWP_AR4 = {"CO2": 1.0, "CH4": 25.0, "N2O": 298.0, "CH4_20": 72.0, "N2O_20": 289.0}

# IPCC 5th Assessment Report (AR5 - 2013, WG1 Table 8.7): GWP-20 CH4 84, N2O 264 (BUG-013:
# the table held 82.5 - the AR6 fossil-CH4 value - and 268, which matches no AR5 value)
GWP_AR5 = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0, "CH4_20": 84.0, "N2O_20": 264.0}

# IPCC 6th Assessment Report (AR6 - 2021, WG1 Table 7.15): fossil methane 29.8 / 82.5 (oil and gas;
# owner decision 2026-10-09; non-fossil is 27.9 / 81.2). N2O 273 for both horizons.
GWP_AR6 = {"CO2": 1.0, "CH4": 29.8, "N2O": 273.0, "CH4_20": 82.5, "N2O_20": 273.0}

# Standard registry
GWP_STANDARDS = {"AR4": GWP_AR4, "AR5": GWP_AR5, "AR6": GWP_AR6}

# Legacy alias for backward compatibility (resolves to AR5)
GWP_DEFAULT_GWP = GWP_AR5

# Standard GWP for the application (default to AR5)
DEFAULT_GWP = GWP_AR5

_CACHED_GWP_STANDARD = None
_CACHED_GWP_STANDARD_TIME = 0.0


def invalidate_gwp_cache():
    global _CACHED_GWP_STANDARD, _CACHED_GWP_STANDARD_TIME
    _CACHED_GWP_STANDARD = None
    _CACHED_GWP_STANDARD_TIME = 0.0
    try:
        from flask import g, has_request_context

        if has_request_context():
            g.pop("_gwp_standard", None)
    except ImportError:  # pragma: no cover
        pass


def get_active_gwp(standard=None, gwp_dict=None, horizon="100"):
    """
    Dynamically resolve the active GWP factors dictionary based on standard and horizon.

    :param standard: Optional standard key ('AR4', 'AR5', 'AR6')
    :param gwp_dict: Optional explicit override dictionary
    :param horizon: '100' (default) or '20' for 20-year horizon
    :return: dict with 'CO2', 'CH4', 'N2O'
    """
    if gwp_dict is not None and isinstance(gwp_dict, dict):
        norm_dict = {str(k).upper(): float(v) for k, v in gwp_dict.items() if v is not None}
        if "CH4" in norm_dict:
            # Fall back to the active standard's values for any gas omitted from the custom dict,
            # so an AR6 installation gets N2O=273 instead of the hardcoded AR5 value of 265.
            _std_key = str(standard or "").upper().strip()
            _std = GWP_STANDARDS.get(_std_key, GWP_AR5)
            return {
                "CO2": norm_dict.get("CO2", 1.0),
                "CH4": norm_dict["CH4"],
                "N2O": norm_dict.get("N2O", _std["N2O"]),
            }


    std_key = str(standard or "").upper().strip()
    if std_key and std_key not in GWP_STANDARDS:
        # audit 2026-10-14 BUG-0050: an unknown standard was computed with AR5 without a word
        raise ValueError(f"Unknown GWP standard '{standard}': use one of {', '.join(sorted(GWP_STANDARDS))}")
    if not std_key:
        now = time.time()
        global _CACHED_GWP_STANDARD, _CACHED_GWP_STANDARD_TIME
        try:
            from flask import g, has_request_context
        except ImportError:  # pragma: no cover
            has_request_context = lambda: False  # noqa: E731
        # BUG-0053: within a request the setting is read from the database (once per request), so a
        # change made through another worker applies at once; the 30 s cache is for background jobs.
        in_request = has_request_context()
        if in_request and getattr(g, "_gwp_standard", None):
            std_key = g._gwp_standard
        elif not in_request and _CACHED_GWP_STANDARD and (now - _CACHED_GWP_STANDARD_TIME < 30.0):
            std_key = _CACHED_GWP_STANDARD
        else:
            try:
                from routes.auth import _app_settings, load_settings_from_db
                try:
                    load_settings_from_db()
                except Exception:
                    pass
                std_key = str(_app_settings.get("gwp_standard") or "AR5").upper().strip()
            except Exception:
                std_key = "AR5"
            if std_key not in GWP_STANDARDS:  # a stored setting is validated when saved; never guess silently
                import logging

                logging.getLogger(__name__).warning("Stored GWP standard %r is unknown; using AR5", std_key)
                std_key = "AR5"
            _CACHED_GWP_STANDARD = std_key
            _CACHED_GWP_STANDARD_TIME = now
            if in_request:
                g._gwp_standard = std_key

    std_profile = GWP_STANDARDS[std_key]

    if str(horizon) == "20":
        return {
            "CO2": 1.0,
            "CH4": std_profile.get("CH4_20", 84.0),
            "N2O": std_profile.get("N2O_20", 264.0),
        }

    return {
        "CO2": std_profile.get("CO2", 1.0),
        "CH4": std_profile.get("CH4", 28.0),
        "N2O": std_profile.get("N2O", 265.0),
    }
