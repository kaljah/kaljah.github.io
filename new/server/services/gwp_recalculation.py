"""Recalculation of stored CO2e after the organisation's GWP standard changes (moved out of
routes/auth_settings.py, which re-exports it)."""
import datetime
import json

from flask import current_app

from extensions import db
from utils import log_activity_and_notify


def _fgas_processes():
    """Process types whose CO2e is an F-gas result (HFC, SF6): it lives only in co2e_total, so the gas columns
    cannot re-weight it (changing the GWP standard used to set every such record to 0)."""
    from calculations.fugitive_other import OTHER_FUGITIVE_PROCESSES, WastewaterCalculator

    return frozenset([k for k, calc in OTHER_FUGITIVE_PROCESSES.items() if not isinstance(calc, WastewaterCalculator)]
                     + ["fire_suppression"])  # its HFC CO2e is re-run too (it was kept on AR4, BA-036)


def _recalculate_fgas(record, gwp_dict, standard):
    """Re-run an HFC / SF6 record from its saved inputs under the new GWP. False (record left as it was) when it
    cannot be re-run, e.g. a Table 7-84 blend, which is printed for AR5 only, under AR4 or AR6."""
    value = fgas_co2e(record, gwp_dict)
    if value is None:
        return False
    record.co2e_total = value
    record.gwp_version = standard
    return True


def reweighted_co2e(record, gwp_dict):
    """A Scope 1 record's CO2e under another GWP set, or None when it cannot be re-weighted and keeps its value:
    an HFC / SF6 record is re-run from its saved inputs (its CO2e is in co2e_total only), a record without any gas
    mass is left as it is. Both were set to 0 (audit 2026-11 F-CORE-01 on the recalculation route, F-AGG-07)."""
    if str(record.process_type or "").strip().lower() in _fgas_processes():
        return fgas_co2e(record, gwp_dict)
    gases = (record.co2_emissions, record.ch4_emissions, record.n2o_emissions)
    if all(g is None for g in gases):
        return None
    co2, ch4, n2o = (float(g or 0.0) for g in gases)
    return co2 * float(gwp_dict.get("CO2", 1.0)) + ch4 * float(gwp_dict["CH4"]) + n2o * float(gwp_dict["N2O"])


def fgas_horizon_deltas(query, live_statuses, by_facility):
    """{(year, process_type, facility_id or "total"): tCO2e to add to the GWP-100 totals of the HFC / SF6 records of `query`
    (an Emission query already scoped) to express them at GWP-20. horizon_delta re-weights CH4 / N2O only, so these
    records stayed on GWP-100 in the GWP-20 view (audit 2026-11 F-AGG-10: HFC-134a 130 t shown for 371 t)."""
    from sqlalchemy import func
    from calculations.constants import get_active_gwp
    from models import Emission

    g20 = get_active_gwp(horizon="20")
    out = {}
    query = query.filter(Emission.status.in_(live_statuses))
    for rec in query.filter(func.lower(func.coalesce(Emission.process_type, "")).in_(_fgas_processes())).all():
        v20 = fgas_co2e(rec, g20)
        if v20 is not None:
            key = (int(rec.year), rec.process_type, rec.facility_id if by_facility else "total")
            out[key] = out.get(key, 0.0) + float(v20) - float(rec.co2e_total or 0.0)
    return out


def known_gwp_dict(standard):
    """The GWP set of a standard name; an unknown one (e.g. "AR7") is refused, it was re-weighted with AR5 and stored
    under its own label (audit 2026-11 F-CORE-08)."""
    from calculations.constants import GWP_STANDARDS
    from input_validation import ValidationError

    key = str(standard or "").strip().upper()
    if key not in GWP_STANDARDS:
        raise ValidationError(f"Unknown GWP standard '{standard}': use one of {', '.join(GWP_STANDARDS)}",
                              "target_gwp_standard")
    return GWP_STANDARDS[key]


def fgas_co2e(record, gwp_dict):
    """CO2e of an HFC / SF6 record re-run from its saved inputs, or None when it cannot be re-run."""
    from calculations import compute_emissions
    from services.scope1_calc import canonicalize

    try:
        stored = json.loads(record.source_payload or "{}")
    except ValueError:
        return None
    if not isinstance(stored, dict) or not stored:
        return None
    base = {"process_type": record.process_type, "process": record.process_type, "fuel_type": record.fuel_type,
            "fuel": record.fuel_type, "unit": record.unit, "quantity": record.quantity, "amount": record.quantity,
            "factor_source": record.factor_source}
    payload = canonicalize({**base, **{k: v for k, v in stored.items() if v is not None}})
    payload["year"], payload["month"], payload["facility_id"] = record.year, record.month, record.facility_id
    try:
        result, _method = compute_emissions(payload, {}, gwp_dict=gwp_dict)
    except (ValueError, TypeError, KeyError):
        return None
    return result["totalCo2e"]


def recalculate_all_emissions_gwp(standard, previous=None, user=None):
    """
    Recalculates co2e_total for all stored Emission records in the database
    using the specified GWP standard ('AR4', 'AR5', 'AR6').
    Also updates gwp_version on the records and invalidates dashboard caches.

    Scope 2 follows (audit 2026-09-30): grid electricity is recalculated from its grid region's
    CO2 / CH4 / N2O, and steam from the default natural-gas boiler has its CH4 / N2O re-weighted
    (the boiler fuel energy is recovered from the stored CO2e with the `previous` standard).
    DEC-3: Verified records are recalculated too (from their stored gas masses, so a round trip is
    lossless); one GWP_RECALCULATION audit entry records the totals before and after.
    """
    from models import Emission, Scope2Emission, Scope3Emission
    from calculations.constants import GWP_STANDARDS, GWP_AR5, invalidate_gwp_cache
    from sqlalchemy import func

    invalidate_gwp_cache()  # a cached standard would keep new records on the old GWP for 30 s

    std_dict = GWP_STANDARDS.get(standard, GWP_AR5)
    co2_factor = float(std_dict.get("CO2", 1.0))
    ch4_factor = float(std_dict.get("CH4", 28.0))
    n2o_factor = float(std_dict.get("N2O", 265.0))

    def _totals():
        s1 = db.session.query(func.count(Emission.id), func.coalesce(func.sum(Emission.co2e_total), 0.0)).one()
        s2 = db.session.query(func.coalesce(func.sum(Scope2Emission.co2e), 0.0)).scalar()
        s3 = db.session.query(func.count(Scope3Emission.id), func.coalesce(func.sum(Scope3Emission.co2e), 0.0)).one()
        return {
            "scope1_records": s1[0],
            "scope1_tco2e": round(float(s1[1]), 4),
            "scope2_tco2e": round(float(s2), 4),
            "scope3_records": s3[0],
            "scope3_tco2e": round(float(s3[1]), 4),
        }

    before = _totals()
    fgas = _fgas_processes()
    # rows without any gas mass keep their CO2e (they were set to 0; audit 2026-11 F-AGG-07)
    has_gas = db.or_(Emission.co2_emissions.isnot(None), Emission.ch4_emissions.isnot(None),
                    Emission.n2o_emissions.isnot(None))
    db.session.query(Emission).filter(~func.lower(func.coalesce(Emission.process_type, "")).in_(fgas), has_gas).update(
        {
            Emission.co2e_total: (
                func.coalesce(Emission.co2_emissions, 0.0) * co2_factor
                + func.coalesce(Emission.ch4_emissions, 0.0) * ch4_factor
                + func.coalesce(Emission.n2o_emissions, 0.0) * n2o_factor
            ),
            Emission.gwp_version: standard,
            Emission.updated_at: datetime.datetime.now(datetime.timezone.utc),
        },
        synchronize_session=False,
    )
    from calculations.constants import get_active_gwp

    new_dict = get_active_gwp(standard=standard)
    fgas_kept = 0
    for rec in Emission.query.filter(func.lower(func.coalesce(Emission.process_type, "")).in_(fgas)).all():
        if not _recalculate_fgas(rec, new_dict, standard):
            fgas_kept += 1
    if fgas_kept:
        current_app.logger.warning(f"GWP standard {standard}: {fgas_kept} HFC / SF6 records kept their previous CO2e "
                                   "(blend GWP not printed for this report, or no saved inputs)")
    db.session.query(Scope3Emission).update(
        {
            Scope3Emission.updated_at: datetime.datetime.now(datetime.timezone.utc),
        },
        synchronize_session=False,
    )

    from electricity_factors import grid_entry, grid_factor_kg_co2e_per_kwh
    from routes.scope2 import _LEGACY_BOILER_EF_KG_PER_MMBTU as _NG_BOILER  # records saved before gas masses
    from services.scope2_gases import gas_split

    new_gwp = {"CH4": ch4_factor, "N2O": n2o_factor}
    old_std = GWP_STANDARDS.get(str(previous or "").upper()) if previous else None

    def _steam_k(g):  # kg CO2e per MMBtu of boiler fuel (routes.scope2._calc_indirect_steam)
        return _NG_BOILER + 0.001 * float(g["CH4"]) + 0.0001 * float(g["N2O"])

    for e in Scope2Emission.query.all():
        st = str(e.source_type or "").lower()
        if "electric" in st:
            entry = grid_entry(e.grid_region)[1] if e.grid_region else None
            if entry is not None and e.electricity_kwh:
                e.emission_factor = grid_factor_kg_co2e_per_kwh(entry, gwp=new_gwp)
                e.co2e = e.electricity_kwh * e.emission_factor / 1000.0
                e.co2e_location_based = e.co2e
                if getattr(e, "market_emission_factor", None) is not None:
                    # a contractual (supplier / instrument) factor is kg CO2e/kWh as given: it does not change
                    # with the GWP set (it was overwritten with the location value and lost, BA-004)
                    e.co2e_market_based = e.electricity_kwh * float(e.market_emission_factor) / 1000.0
                elif not getattr(e, "market_instrument_type", None) or e.market_instrument_type in (
                        "None", "Grid Average / Residual Mix"):
                    e.co2e_market_based = e.co2e  # grid-average fallback follows the re-weighted grid (BA-005)
                # an instrument without a stored factor keeps its market value: nothing to recalculate it from
                g = gas_split(e)
                e.co2_emissions, e.ch4_emissions, e.n2o_emissions = g["co2"], g["ch4"], g["n2o"]
        elif "steam" in st and getattr(e, "ch4_emissions", None) is not None and e.co2_emissions is not None:
            # gases stored with the record: CO2e = CO2 + CH4 x GWP + N2O x GWP of the new set
            new_co2e = (float(e.co2_emissions) + float(e.ch4_emissions) * float(ch4_factor)
                        + float(e.n2o_emissions or 0) * float(n2o_factor))
            for attr in ("co2e", "co2e_location_based", "co2e_market_based"):
                if getattr(e, attr, None) is not None:
                    setattr(e, attr, new_co2e)
        elif "steam" in st and old_std and e.co2e and abs(float(e.emission_factor or 0) - _NG_BOILER) < 1e-4:
            ratio = _steam_k(new_gwp) / _steam_k(old_std)
            e.co2e = e.co2e * ratio
            if getattr(e, "co2e_location_based", None) is not None:
                e.co2e_location_based = e.co2e_location_based * ratio
            if getattr(e, "co2e_market_based", None) is not None:
                e.co2e_market_based = e.co2e_market_based * ratio

    db.session.flush()
    after = _totals()
    log_activity_and_notify(
        action="GWP_RECALCULATION", record_id=str(standard), user=user, request=None, entity="SystemSetting",
        details=(f"GWP standard {previous or '?'} -> {standard}: {after['scope1_records']} Scope 1 records recalculated "
                 f"(Verified included); Scope 1 {before['scope1_tco2e']:,.2f} -> {after['scope1_tco2e']:,.2f} tCO2e, "
                 f"Scope 2 {before['scope2_tco2e']:,.2f} -> {after['scope2_tco2e']:,.2f} tCO2e, "
                 f"Scope 3 {before['scope3_tco2e']:,.2f} -> {after['scope3_tco2e']:,.2f} tCO2e (not re-weighted: "
                 "Scope 3 factors are fixed CO2e values at their source's GWP set; audit 2026-11 F-AGG-16)"
                 + (f"; {fgas_kept} HFC / SF6 records kept their previous CO2e and GWP standard (a Table 7-84 blend is "
                    "printed for AR5 only: enter its GWP on the record)" if fgas_kept else "")),
        old_values=json.dumps(dict(before, gwp_standard=previous)), new_values=json.dumps(dict(after, gwp_standard=standard)),
    )
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"Failed to commit GWP recalculations: {exc}")
        raise

    # Clear dashboard cache
    try:
        from routes.dashboard import DASHBOARD_CACHE, clear_dashboard_cache

        DASHBOARD_CACHE.clear()
        clear_dashboard_cache()
    except Exception as e:
        current_app.logger.warning(f"Failed to clear dashboard cache: {e}")
