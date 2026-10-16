"""QA/QC dashboard data (GET /api/qaqc/dashboard): the flagged-record queue, inventory uncertainty and the
data-health diagnostics. Split out of routes/qaqc.get_qaqc_dashboard (a 606-line function) on 2026-10-16;
the response is unchanged.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, distinct, func, or_

from extensions import db
from models import CustomFactor, Emission, Facility, Scope2Emission, Scope3Emission
from process_categories import NON_COMBUSTION_PROCESSES

MAX_FLAGGED_RECORDS = 500  # flagged records returned per request (prevents OOM on large databases)
SCOPE_MODELS = (Emission, Scope2Emission, Scope3Emission)

# per scope: model, ordering column, record id column, "process" column, CO2e column
_QUEUE = {
    "1": (Emission, "timestamp", "record_id", "process_type", "co2e_total"),
    "2": (Scope2Emission, "created_at", None, "source_type", "co2e"),
    "3": (Scope3Emission, "created_at", None, "category", "co2e"),
}


class DashboardFilter:
    """The request's facility scope, year and status filters."""

    def __init__(self, allowed_fids, args):
        self.allowed_fids = allowed_fids  # None = all, [] = none
        year_arg = args.get("year")
        # audit 2026-10-14 BUG-0066: an out-of-range year is ignored like any malformed one (the documented
        # QA/QC rule); a huge number overflowed the database integer and answered 500
        if year_arg and not (year_arg.strip().isdigit() and 1900 <= int(year_arg.strip()) <= 2100):
            year_arg = None
        self.year = int(year_arg) if year_arg and year_arg not in ("all", "") else None
        self.status = (args.get("status") or "all").lower().strip()

    def scope(self, q, model):
        """Facility scope and year."""
        if self.allowed_fids is not None:
            q = q.filter(model.facility_id.in_(self.allowed_fids))
        if self.year is not None:
            q = q.filter(model.year == self.year)
        return q

    def by_status(self, q, model):
        status = model.status
        if self.status == "rejected":
            return q.filter(status.ilike("%rejected%"))
        if self.status == "verified":
            return q.filter(status.ilike("%verified%"))
        if self.status == "pending":
            return q.filter(or_(status.ilike("%pending%"), status.is_(None)))
        if self.status == "active":
            # the active anomalies queue excludes both Verified and Rejected records
            return q.filter(or_(status.is_(None), and_(~status.ilike("%rejected%"), ~status.ilike("%verified%"))))
        if self.status == "all":
            # "all statuses" leaves out rejected records: they appear in the dedicated Rejected tab only
            return q.filter(or_(status.is_(None), ~status.ilike("%rejected%")))
        return q  # "any", "include_rejected" or unknown


def paging(args):
    try:
        limit = max(1, min(int(args.get("limit", 100)), MAX_FLAGGED_RECORDS))
    except (ValueError, TypeError):
        limit = 100
    try:
        offset = max(0, int(args.get("offset", 0)))
    except (ValueError, TypeError):
        offset = 0
    return limit, offset


def _flagged(f, scope_no, scope_arg, limit, offset):
    """(count, rows) of one scope's records that carry a QA flag."""
    model, order_col, rid_col, proc_col, co2e_col = _QUEUE[scope_no]
    q = f.by_status(f.scope(model.query.filter(model.qa_flag.isnot(None)), model), model)
    count = q.count()
    q = q.order_by(getattr(model, order_col).desc())
    q = q.offset(offset).limit(limit) if scope_arg == scope_no else q.limit(MAX_FLAGGED_RECORDS)
    rows = [{
        "id": r.id, "record_id": getattr(r, rid_col) if rid_col else None, "scope": int(scope_no),
        "facility_id": r.facility_id, "year": r.year, "month": r.month, "process_type": getattr(r, proc_col),
        "qa_flag": r.qa_flag, "status": r.status, "co2e": getattr(r, co2e_col),
    } for r in q]
    return count, rows


def stored_outliers(f):
    """BUG-084: flags written at import time are not enough - scan the STORED Scope 1 inventory for implausible
    values (above the plausibility bound, or more than 1000x the median of the same process type)."""
    from statistics import median

    from calculations.anomaly import PLAUSIBILITY_FLAG_TCO2E

    rows = f.by_status(f.scope(Emission.query, Emission), Emission).filter(Emission.qa_flag.is_(None)).with_entities(
        Emission.id, Emission.record_id, Emission.facility_id, Emission.year, Emission.month,
        Emission.process_type, Emission.status, Emission.co2e_total).all()
    by_proc = {}
    for r in rows:
        by_proc.setdefault((r.process_type or "").lower(), []).append(float(r.co2e_total or 0))
    medians = {k: median([v for v in vals if v > 0]) for k, vals in by_proc.items() if any(v > 0 for v in vals)}
    out = []
    for r in rows:
        v = float(r.co2e_total or 0)
        med = medians.get((r.process_type or "").lower())
        reason = None
        if v > PLAUSIBILITY_FLAG_TCO2E:
            reason = f"Stored-data scan: {v:,.0f} tCO2e exceeds the {PLAUSIBILITY_FLAG_TCO2E:,.0f} t plausibility bound"
        elif med and v > 1000 * med:
            reason = f"Stored-data scan: {v / med:,.0f}x the median of '{r.process_type}' records"
        if reason:
            out.append({
                "id": r.id, "record_id": r.record_id, "scope": 1, "facility_id": r.facility_id,
                "year": r.year, "month": r.month, "process_type": r.process_type, "qa_flag": reason,
                "status": r.status, "co2e": v, "source": "stored_scan",
            })
    return out


def flagged_queue(f, scope_arg, limit, offset):
    """(records for this page, total flagged count, stored-scan outliers)."""
    total, records, outliers = 0, [], []
    for scope_no in ("1", "2", "3"):
        if scope_arg not in (None, "all", scope_no):
            continue
        count, rows = _flagged(f, scope_no, scope_arg, limit, offset)
        total += count
        records.extend(rows)
        if scope_no == "1":
            outliers = stored_outliers(f)
            total += len(outliers)
            records.extend(outliers)
    records.sort(key=lambda x: (x["co2e"] or 0), reverse=True)
    if scope_arg in (None, "all"):  # all scopes together: one ordering, then the page
        records = records[offset:offset + limit]
    return records, total, outliers


def uncertainty(f):
    """BUG-055: the Uncertainty page's service - Verified records, CO2e-weighted per gas, EF correlated within a
    factor, at 95 % (k = 2) - for the chosen year or the latest year with Verified records."""
    from services.inventory_uncertainty import inventory_uncertainty

    cy = datetime.now(timezone.utc).year
    year = f.year
    if year is None:
        year = db.session.query(func.max(Emission.year)).filter(
            Emission.status == "Verified", Emission.year <= cy).scalar() or cy
    unc = {sc: inventory_uncertainty(year, allowed_fids=f.allowed_fids, scope=sc) for sc in ("all", "1", "2", "3")}
    return {
        "overall": unc["all"]["inventory_uncertainty_decimal"],
        "scope1": unc["1"]["inventory_uncertainty_decimal"],
        "scope2": unc["2"]["inventory_uncertainty_decimal"],
        "scope3": unc["3"]["inventory_uncertainty_decimal"],
        "confidence_level_pct": 95,
        "coverage_factor": 2,
        "year": year,
        "status_basis": "Verified",
        "s1_total_tco2e": unc["1"]["total_inventory_emissions"],
        "s2_total_tco2e": unc["2"]["total_inventory_emissions"],
        "s3_total_tco2e": unc["3"]["total_inventory_emissions"],
    }


def _recent_count(q, column, cutoff):
    try:
        return q.filter(column >= cutoff).count()
    except Exception:
        return 0


def _missing_facility(f):
    """(count, Scope 1 query) of records without a facility; 0 for a facility-scoped user."""
    s1 = Emission.query.filter(Emission.facility_id.is_(None))
    if f.allowed_fids is not None:
        return 0, s1
    s2 = Scope2Emission.query.filter(Scope2Emission.facility_id.is_(None))
    s3 = Scope3Emission.query.filter(Scope3Emission.facility_id.is_(None))
    if f.year is not None:
        s1, s2, s3 = (q.filter(m.year == f.year) for q, m in ((s1, Emission), (s2, Scope2Emission), (s3, Scope3Emission)))
    return s1.count() + s2.count() + s3.count(), s1


def health_counts(f):
    """Record counts and the gap checks (with the Scope 1 queries the findings sample from)."""
    s1, s2, s3 = (f.scope(m.query, m) for m in SCOPE_MODELS)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    h = {"s1": s1.count(), "s2": s2.count(), "s3": s3.count()}
    h["total"] = h["s1"] + h["s2"] + h["s3"]
    h["recent"] = (_recent_count(s1, Emission.timestamp, cutoff) + _recent_count(s2, Scope2Emission.created_at, cutoff)
                   + _recent_count(s3, Scope3Emission.created_at, cutoff))
    h["missing_facility"], h["missing_facility_q"] = _missing_facility(f)

    # the fuel check applies to combustion processes and records without a process type
    proc_norm = func.lower(func.replace(Emission.process_type, " ", "_"))
    comb = s1.filter(or_(Emission.process_type.is_(None), ~proc_norm.in_(NON_COMBUSTION_PROCESSES)))
    h["combustion"] = comb.count()
    h["missing_fuel_q"] = comb.filter(or_(Emission.fuel_type.is_(None), Emission.fuel_type == ""))
    h["missing_fuel"] = h["missing_fuel_q"].count()

    h["missing_amount_q"] = s1.filter(or_(Emission.quantity.is_(None), Emission.quantity <= 0))
    s2_no_amount = s2.filter(
        (Scope2Emission.electricity_kwh.is_(None) | (Scope2Emission.electricity_kwh <= 0))
        & (Scope2Emission.steam_ton.is_(None) | (Scope2Emission.steam_ton <= 0))
        & (Scope2Emission.heat_mmbtu.is_(None) | (Scope2Emission.heat_mmbtu <= 0))
        & (Scope2Emission.cooling_ton.is_(None) | (Scope2Emission.cooling_ton <= 0))
    ).count()
    s3_no_amount = s3.filter(or_(Scope3Emission.activity_data.is_(None), Scope3Emission.activity_data <= 0)).count()
    h["missing_amount"] = h["missing_amount_q"].count() + s2_no_amount + s3_no_amount

    h["missing_co2e_q"] = s1.filter(or_(Emission.co2e_total.is_(None), Emission.co2e_total < 0))
    s2_no_co2e = s2.filter(or_(Scope2Emission.co2e.is_(None), Scope2Emission.co2e < 0)).count()
    s3_no_co2e = s3.filter(or_(Scope3Emission.co2e.is_(None), Scope3Emission.co2e < 0)).count()
    h["missing_co2e"] = h["missing_co2e_q"].count() + s2_no_co2e + s3_no_co2e
    return h


def _active_facility_ids(f):
    """Facilities with records in any scope (for the scope and year)."""
    active = set()
    for model in SCOPE_MODELS:
        q = db.session.query(distinct(model.facility_id)).filter(model.facility_id.isnot(None))
        if f.allowed_fids is not None:
            q = q.filter(model.facility_id.in_(f.allowed_fids))
        if f.year is not None:
            q = q.filter(model.year == f.year)
        active |= {r[0] for r in q.all()}
    return active


def anomaly_status_counts(f, outliers):
    """{pending, verified, rejected} of flagged records, the stored-scan outliers included (browser test D5:
    "0 flagged" above a queue showing one flagged record)."""
    counts = {"pending": 0, "verified": 0, "rejected": 0}
    for model in SCOPE_MODELS:
        q = f.scope(model.query.filter(model.qa_flag.isnot(None)), model)
        counts["pending"] += q.filter(or_(model.status.ilike("%pending%"), model.status.is_(None))).count()
        counts["verified"] += q.filter(model.status.ilike("%verified%")).count()
        counts["rejected"] += q.filter(model.status.ilike("%rejected%")).count()
    for o in outliers:
        st = str(o.get("status") or "").lower()
        counts["rejected" if "rejected" in st else "verified" if "verified" in st else "pending"] += 1
    return counts


def completeness(h):
    """Per-dimension completeness (%) and their mean."""
    denom = h["total"] if h["total"] > 0 else h["s1"]
    if denom <= 0:
        return {"facility": 100.0, "fuel_source": 100.0, "activity_amount": 100.0, "calculation": 100.0}, 100.0

    def pct(missing, of):
        return round(max(0.0, (of - missing) / of * 100), 1)

    dims = {
        "facility": pct(h["missing_facility"], denom),
        "fuel_source": pct(h["missing_fuel"], h["combustion"]) if h["combustion"] > 0 else 100.0,
        "activity_amount": pct(h["missing_amount"], denom),
        "calculation": pct(h["missing_co2e"], denom),
    }
    return dims, round(sum(dims.values()) / 4, 1)


def _samples(q, fields):
    """Up to ten sample records from a query, as dicts built by `fields` (a row -> dict function)."""
    try:
        return [fields(r) for r in q.limit(10).all()]
    except Exception:
        return []


def _finding(fid, kind, title, description, count, impact, action, url, samples=None):
    out = {"id": fid, "type": kind, "title": title, "description": description, "affected_count": count,
           "impact": impact, "action": action, "action_url": url}
    if samples is not None:
        out["sample_records"] = samples
    return out


def _record_sample(fac_map, extra):
    def build(r):
        row = {"id": r.id, "facility_id": r.facility_id,
               "facility": fac_map.get(r.facility_id, f"Facility {r.facility_id}"),
               "year": r.year, "process": r.process_type or "Unassigned"}
        row.update(extra(r))
        return row
    return build


def _inactive_facility_samples(f, active):
    samples = []
    try:
        q = Facility.query if f.allowed_fids is None else Facility.query.filter(Facility.id.in_(f.allowed_fids))
        for fac in q.all():
            if fac.id not in active:
                samples.append({"id": fac.id, "name": fac.name, "location": fac.location or fac.field or "General"})
                if len(samples) >= 10:
                    break
    except Exception:
        pass
    return samples


def findings(f, h, active, unused, custom_factor_count):
    """(issues, warnings, suggestions) of the data-health check."""
    try:
        fac_map = dict(Facility.query.with_entities(Facility.id, Facility.name).all())
    except Exception:
        fac_map = {}
    issues, warnings, suggestions = [], [], []
    if h["missing_facility"] > 0:
        samples = _samples(h["missing_facility_q"], lambda r: {
            "id": r.id, "year": r.year, "process": r.process_type or "Unassigned", "quantity": r.quantity,
            "co2e": r.co2e_total})
        issues.append(_finding(
            "missing_facility", "critical", "Unassigned Facility Boundary",
            f"{h['missing_facility']} emission record(s) lack facility assignment, breaking GHG Protocol "
            "organizational boundary requirements.", h["missing_facility"], "High", "Manage Facilities",
            "/manage-data?tab=facilities", samples))
    if h["missing_co2e"] > 0:
        samples = _samples(h["missing_co2e_q"], _record_sample(fac_map, lambda r: {"quantity": r.quantity}))
        issues.append(_finding(
            "missing_co2e", "critical", "Uncalculated Emission Values",
            f"{h['missing_co2e']} record(s) have uncalculated or negative CO₂e totals.", h["missing_co2e"], "High",
            "Review in Manage Data", "/manage-data?tab=pending", samples))
    if h["missing_fuel"] > 0:
        samples = _samples(h["missing_fuel_q"], _record_sample(fac_map, lambda r: {"quantity": r.quantity}))
        warnings.append(_finding(
            "missing_fuel", "warning", "Missing Fuel or Source Classification",
            f"{h['missing_fuel']} Scope 1 combustion record(s) are missing explicit fuel or process types, using "
            "generic defaults.", h["missing_fuel"], "Medium", "Classify in Manage Data", "/manage-data?tab=sources",
            samples))
    if h["missing_amount"] > 0:
        samples = _samples(h["missing_amount_q"],
                           _record_sample(fac_map, lambda r: {"fuel": r.fuel_type or "Unspecified"}))
        warnings.append(_finding(
            "missing_amount", "warning", "Zero or Null Activity Quantities",
            f"{h['missing_amount']} record(s) contain zero or unrecorded activity amounts.", h["missing_amount"],
            "Medium", "Review in Manage Data", "/manage-data?tab=pending", samples))
    if h["total"] > 0 and h["recent"] == 0:
        warnings.append(_finding(
            "stale_data", "warning", "Data Freshness Advisory",
            "No emissions or activity records ingested during the last 30 days.", 0, "Low", "Review Ingestion",
            "/manage-data?tab=pending"))
    if unused > 0:
        suggestions.append(_finding(
            "unused_facilities", "info", "Inactive Facilities In Scope",
            f"{unused} facility boundary(ies) are registered in master data but have no emissions reported for this "
            "period.", unused, "Low", "Manage Facilities", "/manage-data?tab=facilities",
            _inactive_facility_samples(f, active)))
    if custom_factor_count == 0:
        suggestions.append(_finding(
            "no_custom_factors", "info", "Tier 1 Default Factor Reliance",
            "No custom or site-specific emission factors registered. Adding facility-calibrated factors reduces "
            "Tier 1 uncertainty.", 0, "Low", "Manage Factors", "/manage-data?tab=factors"))
    return issues, warnings, suggestions


def diagnostics(f, total_flagged, outliers):
    """The data-health block: completeness, coverage, anomaly counts, findings and a composite score."""
    h = health_counts(f)
    total_facilities = len(f.allowed_fids) if f.allowed_fids is not None else Facility.query.count()
    active = _active_facility_ids(f)
    unused = max(0, total_facilities - len(active))
    try:
        custom_factor_count = CustomFactor.query.count()
    except Exception:
        custom_factor_count = 0
    anomalies = anomaly_status_counts(f, outliers)
    dims, overall = completeness(h)
    issues, warnings, suggestions = findings(f, h, active, unused, custom_factor_count)
    penalty = len(issues) * 10 + len(warnings) * 5 + min(15, anomalies["pending"] * 2)
    return {
        "health_score": max(0, min(100, int(round(overall - penalty)))),
        "completeness": overall,
        "dimension_completeness": dims,
        "total_records": h["total"],
        "records_by_scope": {"scope1": h["s1"], "scope2": h["s2"], "scope3": h["s3"]},
        "recent_records_30d": h["recent"],
        "total_facilities": total_facilities,
        "active_facilities": len(active),
        "unused_facilities": unused,
        "total_custom_factors": custom_factor_count,
        "anomalies_summary": {"total": total_flagged, **anomalies},
        "issues": issues,
        "warnings": warnings,
        "suggestions": suggestions,
    }


def build_dashboard(allowed_fids, args):
    """The full dashboard response for a user's facility scope and the request's query arguments."""
    f = DashboardFilter(allowed_fids, args)
    scope_arg = args.get("scope")  # "1", "2", "3" or "all"
    limit, offset = paging(args)
    records, total_flagged, outliers = flagged_queue(f, scope_arg, limit, offset)
    tier1 = uncertainty(f)
    diag = diagnostics(f, total_flagged, outliers)
    pending_review = sum(f.scope(m.query, m).filter(m.status.in_(("Pending", "Pending Approval", "Pending Review")))
                         .count() for m in SCOPE_MODELS)
    return {
        "status": "success",
        "total_flagged_count": total_flagged,
        "stored_scan_outlier_count": len(outliers),
        "pending_review_count": pending_review,
        "returned_count": len(records),
        "limit": limit,
        "offset": offset,
        "tier1_uncertainty": tier1,
        "flagged_records": records,
        "diagnostics": diag,
    }
