from flask import Blueprint, jsonify, request
from extensions import db
from models import JvPartner, FacilityEquityShare, Facility, Emission
from routes.auth import login_required
from utils import get_current_user, get_allowed_facility_ids, require_facility_access

equity_bp = Blueprint("equity", __name__)

DEFAULT_JV_PARTNERS = [
    {"name": "Sonatrach", "code": "SH", "country": "Algeria", "is_operator": True},
    {"name": "Occidental", "code": "OXY", "country": "United States", "is_operator": False},
    {"name": "Eni", "code": "ENI", "country": "Italy", "is_operator": False},
    {"name": "TotalEnergies", "code": "TTE", "country": "France", "is_operator": False},
    {"name": "Pertamina", "code": "PER", "country": "Indonesia", "is_operator": False},
    {"name": "Repsol", "code": "REP", "country": "Spain", "is_operator": False},
]


def ensure_default_partners():
    """Ensure baseline international JV partners are seeded."""
    added = False
    for p in DEFAULT_JV_PARTNERS:
        exists = JvPartner.query.filter_by(name=p["name"]).first()
        if not exists:
            partner = JvPartner(
                name=p["name"],
                code=p["code"],
                country=p["country"],
                is_operator=p["is_operator"],
            )
            db.session.add(partner)
            added = True
    if added:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


@equity_bp.route("/partners", methods=["GET"])
@login_required
def get_partners():
    user = get_current_user()
    if user and user.role in ["it", "it_admin", "it_manager"]:
        return jsonify({"error": "Forbidden: IT roles do not have access to Joint Venture equity data"}), 403
    ensure_default_partners()
    partners = JvPartner.query.order_by(JvPartner.name).all()
    return jsonify([
        {
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "country": p.country,
            "is_operator": p.is_operator,
        }
        for p in partners
    ])


@equity_bp.route("/shares", methods=["GET"])
@login_required
def get_equity_shares():
    user = get_current_user()
    if user and user.role in ["it", "it_admin", "it_manager"]:
        return jsonify({"error": "Forbidden: IT roles do not have access to Joint Venture equity data"}), 403
    allowed_fids = get_allowed_facility_ids(user)

    query = FacilityEquityShare.query
    if allowed_fids is not None:
        query = query.filter(FacilityEquityShare.facility_id.in_(allowed_fids))

    facility_id = request.args.get("facility_id") or request.args.get("facilityId")
    if facility_id and facility_id != "all":
        try:
            fid = int(facility_id)
            if allowed_fids is not None and fid not in allowed_fids:
                return jsonify({"error": "Unauthorized facility"}), 403
            query = query.filter(FacilityEquityShare.facility_id == fid)
        except ValueError:
            pass

    shares = query.all()
    return jsonify([
        {
            "id": s.id,
            "facility_id": s.facility_id,
            "facility_name": s.facility.name if s.facility else "Unknown",
            "partner_id": s.partner_id,
            "partner_name": s.partner.name if s.partner else "Unknown",
            "partner_code": s.partner.code if s.partner else "",
            "equity_share_pct": s.equity_share_pct,
            "effective_start_date": s.effective_start_date,
            "effective_end_date": s.effective_end_date,
            "agreement_reference": s.agreement_reference,
        }
        for s in shares
    ])


def _parse_date(value, field, required=True):
    import datetime as _dt
    from input_validation import ValidationError

    if value in (None, ""):
        if required:
            raise ValidationError(f"'{field}' is required", field)
        return None
    try:
        return _dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        raise ValidationError(f"'{field}' must be an ISO date (YYYY-MM-DD)", field)


def _overlap_days(start, end, lo, hi):
    """Inclusive day overlap between [start, end or +inf] and [lo, hi]."""
    s = max(start, lo)
    e = min(end or hi, hi)
    return max(0, (e - s).days + 1)


def effective_share_pct(slices, year, month=None):
    """BUG-046: time-weighted equity % of one partner over a calendar year (or one month of it).

    `slices` are FacilityEquityShare rows for one facility/partner. Each slice counts for the
    days of the period it covers; days no slice covers contribute nothing. Returns None when no
    slice overlaps the period (caller decides the fallback).
    """
    import calendar
    import datetime as _dt

    if month:
        lo, hi = _dt.date(year, month, 1), _dt.date(year, month, calendar.monthrange(year, month)[1])
    else:
        lo, hi = _dt.date(year, 1, 1), _dt.date(year, 12, 31)
    days_in_period = (hi - lo).days + 1
    total, covered = 0.0, 0
    for sl in slices:
        try:
            start = _dt.date.fromisoformat(str(sl.effective_start_date)[:10])
            end = _dt.date.fromisoformat(str(sl.effective_end_date)[:10]) if sl.effective_end_date else None
        except ValueError:
            continue
        d = _overlap_days(start, end, lo, hi)
        if d:
            total += float(sl.equity_share_pct or 0.0) * d
            covered += d
    if not covered:
        return None
    return total / days_in_period


def _partner_pcts(fac, partners, slices_by_partner, year, month=None):
    """Equity % of every partner for the period. Audit 2026-10-14 BUG-0004: an operator without its
    own share row holds what the explicit partner shares leave (at most the facility's equity %),
    not 100 % on top of them."""
    explicit = {p.id: effective_share_pct(slices_by_partner[p.id], year, month) for p in partners}
    explicit_sum = sum(v for v in explicit.values() if v is not None)
    out = {}
    for p in partners:
        pct = explicit[p.id]
        if pct is None:
            pct = (min(float(fac.equity_share_pct or 0.0), max(0.0, 100.0 - explicit_sum))
                   if p.is_operator else 0.0)
        out[p.id] = pct
    return out


@equity_bp.route("/shares", methods=["POST"])
@login_required
def save_equity_share():
    from input_validation import parse_number

    user = get_current_user()
    # BUG-046: ownership is organisation configuration, not operational data entry
    if not user or user.role not in ("admin", "superuser"):
        return jsonify({"error": "Forbidden: only administrators and super users can change equity shares"}), 403
    data = request.get_json() or {}

    facility_id = int(parse_number(data.get("facility_id"), "facility_id", min_value=1))
    partner_id = int(parse_number(data.get("partner_id"), "partner_id", min_value=1))
    equity_pct = parse_number(data.get("equity_share_pct"), "equity_share_pct", min_value=0, max_value=100)

    if not require_facility_access(user, facility_id):
        return jsonify({"error": "Forbidden: You do not have access to this facility"}), 403
    if db.session.get(Facility, facility_id) is None:
        return jsonify({"error": f"Facility with ID {facility_id} does not exist"}), 404
    if db.session.get(JvPartner, partner_id) is None:
        return jsonify({"error": "Unknown partner"}), 400

    start = _parse_date(data.get("effective_start_date") or "2021-01-01", "effective_start_date")
    end = _parse_date(data.get("effective_end_date"), "effective_end_date", required=False)
    if end is not None and end < start:
        return jsonify({"error": "effective_end_date must not be before effective_start_date"}), 400

    share_id = data.get("id")
    if share_id:
        share = FacilityEquityShare.query.filter_by(id=int(share_id), facility_id=facility_id).first()
    else:
        share = FacilityEquityShare.query.filter_by(
            facility_id=facility_id, partner_id=partner_id, effective_start_date=start.isoformat()
        ).first()

    # Shares of all partners that overlap this period must not exceed 100 %
    import datetime as _dt

    far = _dt.date(9999, 12, 31)
    others = []
    for other in FacilityEquityShare.query.filter_by(facility_id=facility_id).all():
        if share is not None and other.id == share.id:
            continue
        o_start = _dt.date.fromisoformat(str(other.effective_start_date)[:10])
        o_end = _dt.date.fromisoformat(str(other.effective_end_date)[:10]) if other.effective_end_date else far
        if o_start <= (end or far) and start <= o_end:
            others.append((o_start, o_end, float(other.equity_share_pct or 0.0)))
    # the concurrent total can only change at a slice start, so check each start inside the period
    checkpoints = {start} | {o[0] for o in others if start <= o[0] <= (end or far)}
    pct_sum = max(
        equity_pct + sum(p for (o_s, o_e, p) in others if o_s <= day <= o_e) for day in checkpoints
    )
    if pct_sum > 100.0 + 1e-9:
        return jsonify({"error": f"Equity shares overlapping this period would total {pct_sum:.2f}% (max 100%)"}), 400

    if not share:
        share = FacilityEquityShare(facility_id=facility_id, partner_id=partner_id, effective_start_date=start.isoformat())
        db.session.add(share)
    else:
        share.effective_start_date = start.isoformat()

    share.equity_share_pct = equity_pct
    share.effective_end_date = end.isoformat() if end else None
    share.agreement_reference = data.get("agreement_reference")

    from utils import log_activity_and_notify
    from routes.dashboard import clear_dashboard_cache

    log_activity_and_notify(action="UPDATE", record_id=f"equity-{facility_id}-{partner_id}", user=user, request=request,
                            entity="FacilityEquityShare", facility_id=facility_id,
                            details=f"Equity share {equity_pct}% for partner {partner_id} from {start} to {end or 'open'}")
    db.session.commit()
    clear_dashboard_cache()
    return jsonify({"success": True, "id": share.id, "message": "Equity share saved successfully"})


@equity_bp.route("/shares/<int:share_id>", methods=["DELETE"])
@login_required
def delete_equity_share(share_id):
    user = get_current_user()
    if not user or user.role not in ("admin", "superuser"):
        return jsonify({"error": "Forbidden: only administrators and super users can delete equity shares"}), 403
    share = db.session.get(FacilityEquityShare, share_id)
    if not share:
        return jsonify({"error": "Equity share not found"}), 404
    if not require_facility_access(user, share.facility_id):
        return jsonify({"error": "Forbidden: You do not have access to this facility"}), 403
    fac_id = share.facility_id
    partner_id = share.partner_id
    db.session.delete(share)
    from utils import log_activity_and_notify
    from routes.dashboard import clear_dashboard_cache
    log_activity_and_notify(action="DELETE", record_id=f"equity-{fac_id}-{partner_id}-{share_id}", user=user, request=request,
                            entity="FacilityEquityShare", facility_id=fac_id,
                            details=f"Deleted equity share ID {share_id} for partner {partner_id}")
    db.session.commit()
    clear_dashboard_cache()
    return jsonify({"success": True, "message": "Equity share deleted successfully"})


@equity_bp.route("/allocation", methods=["GET"])
@login_required
def get_equity_allocation():
    """
    Allocates annual GHG (Scope 1 + Scope 2 tCO2e) and methane (tCH4) emissions to JV partners
    based on their effective equity share percentages.
    """
    ensure_default_partners()
    user = get_current_user()
    if user and user.role in ["it", "it_admin", "it_manager"]:
        return jsonify({"error": "Forbidden: IT roles do not have access to Joint Venture equity data"}), 403
    allowed_fids = get_allowed_facility_ids(user)

    year = (request.args.get("year") or "").strip()
    yr = int(year) if year.isdigit() and 1900 <= int(year) <= 2100 else 2025  # malformed or out of range (F13): 2025

    facility_id = request.args.get("facility_id") or request.args.get("facilityId")
    fac_q = Facility.query
    if allowed_fids is not None:
        fac_q = fac_q.filter(Facility.id.in_(allowed_fids))
    if facility_id and facility_id != "all":
        try:
            fid = int(facility_id)
        except (ValueError, TypeError):
            return jsonify({"error": "facility_id must be a valid integer"}), 400
        if allowed_fids is not None and fid not in allowed_fids:
            return jsonify({"error": "Unauthorized facility"}), 403
        fac_q = fac_q.filter(Facility.id == fid)

    facilities = fac_q.all()
    partners = JvPartner.query.order_by(JvPartner.name).all()

    # Get totals per facility
    allocation_by_facility = []

    for fac in facilities:
        # Audit 2026-10-14 BUG-0023: allocate month by month, so a share that changes mid-year
        # applies to the emissions of the months it covers (records without a month use the
        # year's time-weighted share)
        from models import Scope2Emission

        periods = {}  # month (or None) -> [scope 1 tCO2e, scope 2 tCO2e, tCH4]
        # verified emissions of this facility and year, per month
        for m, co2e, ch4 in db.session.query(
                Emission.month, db.func.sum(Emission.co2e_total), db.func.sum(Emission.ch4_emissions)
        ).filter(Emission.facility_id == fac.id, Emission.year == yr, Emission.status == "Verified"
                 ).group_by(Emission.month).all():
            row = periods.setdefault(m if m in range(1, 13) else None, [0.0, 0.0, 0.0])
            row[0] += float(co2e or 0.0)
            row[2] += float(ch4 or 0.0)
        # GHG Protocol equity-share approach: the partners take their share of the operation's
        # Scope 1 and Scope 2 (purchased energy); Scope 2 used to be left out
        for m, co2e in db.session.query(Scope2Emission.month, db.func.sum(Scope2Emission.co2e)).filter(
                Scope2Emission.facility_id == fac.id, Scope2Emission.year == yr,
                Scope2Emission.status == "Verified").group_by(Scope2Emission.month).all():
            periods.setdefault(m if m in range(1, 13) else None, [0.0, 0.0, 0.0])[1] += float(co2e or 0.0)
        total_s1 = sum(v[0] for v in periods.values())
        total_s2 = sum(v[1] for v in periods.values())
        total_ch4 = sum(v[2] for v in periods.values())
        total_co2e = total_s1 + total_s2

        # BUG-046: time-weighted share of every slice that is effective during year yr
        shares = FacilityEquityShare.query.filter_by(facility_id=fac.id).all()
        by_partner = {p.id: [s for s in shares if s.partner_id == p.id] for p in partners}
        annual = _partner_pcts(fac, partners, by_partner, yr)
        alloc = {p.id: [0.0, 0.0, 0.0] for p in partners}
        for m, amounts in periods.items():
            pcts = annual if m is None else _partner_pcts(fac, partners, by_partner, yr, m)
            for pid, pct in pcts.items():
                for i in range(3):
                    alloc[pid][i] += amounts[i] * pct / 100.0

        partner_allocations = []
        for p in partners:
            allocated_s1, allocated_s2, allocated_ch4 = alloc[p.id]
            allocated_co2e = allocated_s1 + allocated_s2

            partner_allocations.append({
                "partner_id": p.id,
                "partner_name": p.name,
                "partner_code": p.code,
                "equity_pct": round(annual[p.id], 4),
                "allocated_co2e": round(allocated_co2e, 2),
                "allocated_scope1": round(allocated_s1, 2),
                "allocated_scope2": round(allocated_s2, 2),
                "allocated_ch4": round(allocated_ch4, 2),
            })

        # DEFECT-AG1-06: GHG Protocol Chapter 3 - Unallocated working interest identification
        allocated_pct_sum = round(sum(p["equity_pct"] for p in partner_allocations), 4)
        unallocated_pct = round(max(0.0, 100.0 - allocated_pct_sum), 4)
        is_fully_allocated = bool(unallocated_pct <= 0.001)

        unallocated_s1 = round(max(0.0, total_s1 - sum(v[0] for v in alloc.values())), 2)
        unallocated_s2 = round(max(0.0, total_s2 - sum(v[1] for v in alloc.values())), 2)
        unallocated_co2e = round(unallocated_s1 + unallocated_s2, 2)
        unallocated_ch4 = round(max(0.0, total_ch4 - sum(v[2] for v in alloc.values())), 2)

        unallocated_share = None
        if not is_fully_allocated:
            unallocated_share = {
                "partner_id": None,
                "partner_name": "Unallocated Third-Party Interest",
                "partner_code": "THIRD_PARTY",
                "equity_pct": round(unallocated_pct, 2),
                "allocated_co2e": unallocated_co2e,
                "allocated_scope1": unallocated_s1,
                "allocated_scope2": unallocated_s2,
                "allocated_ch4": unallocated_ch4,
                "standards_reference": "GHG Protocol Corporate Standard Chapter 3 (Unallocated Working Interest)",
            }

        allocation_by_facility.append({
            "facility_id": fac.id,
            "facility_name": fac.name,
            "year": yr,
            "total_co2e": round(total_co2e, 2),
            "total_scope1": round(total_s1, 2),
            "total_scope2": round(total_s2, 2),
            "total_ch4": round(total_ch4, 2),
            "total_allocated_equity_pct": round(allocated_pct_sum, 2),
            "unallocated_equity_pct": round(unallocated_pct, 2),
            "unallocated_co2e": unallocated_co2e,
            "unallocated_scope1": unallocated_s1,
            "unallocated_scope2": unallocated_s2,
            "unallocated_ch4": unallocated_ch4,
            "is_fully_allocated": is_fully_allocated,
            "allocation_status": "Fully Allocated" if is_fully_allocated else f"Partial ({unallocated_pct:.2f}% unallocated third-party interest)",
            "ghg_protocol_boundary_note": "Consolidated joint venture interest fully allocated (100.0%)." if is_fully_allocated else f"Pursuant to GHG Protocol Chapter 3, unallocated equity ({unallocated_pct:.2f}%) represents external third-party or non-reporting operating partner interest.",
            "unallocated_share": unallocated_share,
            "partners": partner_allocations,
        })

    return jsonify(allocation_by_facility)
