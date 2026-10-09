"""Flare defaults that depend on the facility, applied around the Scope 1 engine.

API Compendium 2021 corrections (December 2025, Section 5.1.2): flare CO2 uses a 96.5 % combustion
efficiency (carried by the catalog factors and the flare calculator), and CH4 a destruction
efficiency of 98 % for production flares or 99.5 % for well-designed and operated refinery flares.
The refinery value is applied here to Downstream facilities, unless an efficiency was entered.
"""
from .legacy_engine import compute_emissions as _compute_emissions

FLARE_PROCESSES = {"flaring", "routine_flaring", "non_routine_flaring", "safety_flaring"}
PRODUCTION_DESTRUCTION = 0.98
REFINERY_DESTRUCTION = 0.995
_EFFICIENCY_KEYS = ("destruction_efficiency", "destruction_eff", "eta_d", "control_efficiency", "flare_efficiency",
                    "flare_eff")


def facility_segment(payload):
    """The facility's segment (Upstream / Midstream / Downstream), lower-cased, or ''."""
    seg = payload.get("facility_segment")
    if seg in (None, "") and payload.get("facility_id") not in (None, ""):
        try:
            from models import Facility, db

            fac = db.session.get(Facility, int(payload["facility_id"]))
            seg = fac.segment if fac else None
        except Exception:  # no application context (offline calculations)
            seg = None
    return str(seg or "").strip().lower()


def _efficiency_given(payload):
    nested = (payload.get("calc_inputs") or {}).get(str(payload.get("process_type") or "").lower()) or {}
    return any(src.get(k) not in (None, "", "-") for src in (payload, nested) for k in _EFFICIENCY_KEYS)


def compute_emissions(payload, factor_data=None, gwp_dict=None, gwp_standard=None):
    process = str(payload.get("process_type") or "").strip().lower()
    if process in FLARE_PROCESSES and not _efficiency_given(payload) and facility_segment(payload) == "downstream":
        payload = {**payload, "destruction_efficiency": REFINERY_DESTRUCTION}
        if factor_data and factor_data.get("combustion_efficiency_ch4") == PRODUCTION_DESTRUCTION \
                and factor_data.get("ch4") not in (None, ""):
            # catalog factor: 2 % residual CH4 -> 0.5 %
            residual = (1 - REFINERY_DESTRUCTION) / (1 - PRODUCTION_DESTRUCTION)
            factor_data = {**factor_data, "ch4": float(factor_data["ch4"]) * residual,
                           "combustion_efficiency_ch4": REFINERY_DESTRUCTION}
    return _compute_emissions(payload, factor_data, gwp_dict=gwp_dict, gwp_standard=gwp_standard)
