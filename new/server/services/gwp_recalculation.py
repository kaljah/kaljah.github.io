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

    return frozenset(k for k, calc in OTHER_FUGITIVE_PROCESSES.items() if not isinstance(calc, WastewaterCalculator))


def _recalculate_fgas(record, gwp_dict, standard):
    """Re-run an HFC / SF6 record from its saved inputs under the new GWP. False (record left as it was) when it
    cannot be re-run, e.g. a Table 7-84 blend, which is printed for AR5 only, under AR4 or AR6."""
    from calculations import compute_emissions
    from services.scope1_calc import canonicalize

    try:
        stored = json.loads(record.source_payload or "{}")
    except ValueError:
        return False
    if not isinstance(stored, dict) or not stored:
        return False
    base = {"process_type": record.process_type, "process": record.process_type, "fuel_type": record.fuel_type,
            "fuel": record.fuel_type, "unit": record.unit, "quantity": record.quantity, "amount": record.quantity,
            "factor_source": record.factor_source}
    payload = canonicalize({**base, **{k: v for k, v in stored.items() if v is not None}})
    payload["year"], payload["month"], payload["facility_id"] = record.year, record.month, record.facility_id
    try:
        result, _method = compute_emissions(payload, {}, gwp_dict=gwp_dict)
    except (ValueError, TypeError, KeyError):
        return False
    record.co2e_total = result["totalCo2e"]
    record.gwp_version = standard
    return True


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
    db.session.query(Emission).filter(~func.lower(func.coalesce(Emission.process_type, "")).in_(fgas)).update(
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
    from routes.scope2 import _DEFAULT_BOILER_EF_KG_PER_MMBTU as _NG_BOILER

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
                if not getattr(e, "market_instrument_type", None) or e.market_instrument_type in ("None", "Grid Average / Residual Mix"):
                    e.co2e_market_based = e.co2e
                elif getattr(e, "market_emission_factor", None) is not None:
                    e.co2e_market_based = e.electricity_kwh * float(e.market_emission_factor) / 1000.0
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
                 f"Scope 3 {before['scope3_tco2e']:,.2f} -> {after['scope3_tco2e']:,.2f} tCO2e"
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
