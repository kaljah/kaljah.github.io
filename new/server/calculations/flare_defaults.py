"""Flare defaults that depend on the facility, applied around the Scope 1 engine.

API Compendium 2021 corrections (December 2025, Section 5.1.2): flare CO2 uses a 96.5 % combustion
efficiency (carried by the catalog factors and the flare calculator), and CH4 a destruction
efficiency of 98 % for production flares or 99.5 % for well-designed and operated refinery flares.
The refinery value is applied here to Downstream facilities, unless an efficiency was entered.
"""
from .legacy_engine import compute_emissions as _compute_emissions

FLARE_PROCESSES = {
    "flaring",
    "routine_flaring",
    "non_routine_flaring",
    "safety_flaring",
    "combustion_flaring",
    "flare",
    "flaring_routine",
    "flaring_non_routine",
}
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


def _entered_efficiency(payload, keys):
    """The first entered efficiency among `keys` (top level, then calc_inputs[process]) as a fraction; percent, always."""
    from .dispatcher import percent_to_fraction

    nested = (payload.get("calc_inputs") or {}).get(str(payload.get("process_type") or "").lower()) or {}
    for src in (payload, nested):
        for k in keys:
            if src.get(k) not in (None, "", "-"):
                return percent_to_fraction(src[k], k)
    return None


def catalog_flare_at_efficiency(payload, factor_data):
    """A catalog flare row (Eq 5-2 / 5-4 / 5-6 at 96.5 % combustion and 98 % destruction) at the entered efficiency.

    Blind audit BA-001: on Tier 1 an entered flare efficiency was accepted and ignored. CH4 is the unburnt share of
    the row's methane (x (1 - DE) / (1 - DE_row)); CO2 is the row's combustion CO2 at the entered combustion
    efficiency plus the gas's own CO2 (`co2_native`); N2O follows the CO2 (Eq 5-6). One efficiency
    (control / flare efficiency) sets both, as on Tier 3; destruction / combustion efficiencies override it.
    """
    if not factor_data or factor_data.get("combustion_efficiency_ch4") in (None, "") \
            or str(payload.get("factor_source") or "default").lower() not in ("default", ""):
        return factor_data
    single = _entered_efficiency(payload, ("control_efficiency", "flare_efficiency", "flare_eff"))
    de = _entered_efficiency(payload, ("destruction_efficiency", "destruction_eff", "eta_d"))
    ce = _entered_efficiency(payload, ("combustion_efficiency", "combustion_eff", "eta_c"))
    de = single if de is None else de
    ce = single if ce is None else ce
    if de is None and ce is None:
        return factor_data
    out = dict(factor_data)
    row_de = float(factor_data["combustion_efficiency_ch4"])
    row_ce = float(factor_data.get("combustion_efficiency_co2") or row_de)
    if de is not None and factor_data.get("ch4") not in (None, ""):
        out["ch4"] = float(factor_data["ch4"]) * (1.0 - de) / (1.0 - row_de)
        out["combustion_efficiency_ch4"] = de
    if ce is not None and factor_data.get("co2") not in (None, ""):
        native = float(factor_data.get("co2_native") or 0.0)
        co2 = (float(factor_data["co2"]) - native) * ce / row_ce + native
        if factor_data.get("n2o") not in (None, "") and float(factor_data["co2"]) > native:
            # Eq 5-6: N2O follows the combustion CO2 (not the gas's own CO2)
            out["n2o"] = float(factor_data["n2o"]) * (co2 - native) / (float(factor_data["co2"]) - native)
        out["co2"] = co2
        out["combustion_efficiency_co2"] = ce
    return out


def compute_emissions(payload, factor_data=None, gwp_dict=None, gwp_standard=None):
    process = str(payload.get("process_type") or "").strip().lower()
    if process in FLARE_PROCESSES:
        factor_data = catalog_flare_at_efficiency(payload, factor_data)
    if process in FLARE_PROCESSES and not _efficiency_given(payload) and facility_segment(payload) == "downstream":
        payload = {**payload, "destruction_efficiency": REFINERY_DESTRUCTION * 100.0}  # percent, as every entered efficiency (BA-012)
        if factor_data and factor_data.get("combustion_efficiency_ch4") == PRODUCTION_DESTRUCTION \
                and factor_data.get("ch4") not in (None, ""):
            # catalog factor: 2 % residual CH4 -> 0.5 %
            residual = (1 - REFINERY_DESTRUCTION) / (1 - PRODUCTION_DESTRUCTION)
            factor_data = {**factor_data, "ch4": float(factor_data["ch4"]) * residual,
                           "combustion_efficiency_ch4": REFINERY_DESTRUCTION}
    return _compute_emissions(payload, factor_data, gwp_dict=gwp_dict, gwp_standard=gwp_standard)
