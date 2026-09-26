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
    db.session.commit()


@equity_bp.route("/partners", methods=["GET"])
@login_required
def get_partners():
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
    allowed_fids = get_allowed_facility_ids(user)

    query = FacilityEquityShare.query
    if allowed_fids is not None:
        query = query.filter(FacilityEquityShare.facility_id.in_(allowed_fids))

    facility_id = request.args.get("facility_id")
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


@equity_bp.route("/shares", methods=["POST"])
@login_required
def save_equity_share():
    user = get_current_user()
    data = request.get_json() or {}

    facility_id = data.get("facility_id")
    partner_id = data.get("partner_id")
    equity_pct = data.get("equity_share_pct")

    if not facility_id or not partner_id or equity_pct is None:
        return jsonify({"error": "facility_id, partner_id, and equity_share_pct are required"}), 400

    if not require_facility_access(user, int(facility_id)):
        return jsonify({"error": "Forbidden: You do not have access to this facility"}), 403

    start_date = data.get("effective_start_date", "2021-01-01")

    share = FacilityEquityShare.query.filter_by(
        facility_id=int(facility_id),
        partner_id=int(partner_id),
        effective_start_date=start_date,
    ).first()

    if not share:
        share = FacilityEquityShare(
            facility_id=int(facility_id),
            partner_id=int(partner_id),
            effective_start_date=start_date,
        )
        db.session.add(share)

    share.equity_share_pct = float(equity_pct)
    share.effective_end_date = data.get("effective_end_date")
    share.agreement_reference = data.get("agreement_reference")

    db.session.commit()
    return jsonify({"success": True, "id": share.id, "message": "Equity share saved successfully"})


@equity_bp.route("/allocation", methods=["GET"])
@login_required
def get_equity_allocation():
    """
    Allocates annual GHG (tCO2e) and Methane (tCH4) emissions to JV partners
    based on their effective equity share percentages.
    """
    ensure_default_partners()
    user = get_current_user()
    allowed_fids = get_allowed_facility_ids(user)

    year = request.args.get("year")
    try:
        yr = int(year) if year else 2025
    except ValueError:
        yr = 2025

    facility_id = request.args.get("facility_id")
    fac_q = Facility.query
    if allowed_fids is not None:
        fac_q = fac_q.filter(Facility.id.in_(allowed_fids))
    if facility_id and facility_id != "all":
        try:
            fac_q = fac_q.filter(Facility.id == int(facility_id))
        except ValueError:
            pass

    facilities = fac_q.all()
    partners = JvPartner.query.order_by(JvPartner.name).all()

    # Get totals per facility
    allocation_by_facility = []

    for fac in facilities:
        # Sum verified emissions for this facility and year
        em_q = db.session.query(
            db.func.sum(Emission.co2e_total),
            db.func.sum(Emission.ch4_emissions)
        ).filter(
            Emission.facility_id == fac.id,
            Emission.year == yr,
            Emission.status == "Verified"
        )
        total_co2e, total_ch4 = em_q.first()
        total_co2e = float(total_co2e or 0.0)
        total_ch4 = float(total_ch4 or 0.0)

        # Get equity shares for this facility active during year yr
        shares = FacilityEquityShare.query.filter_by(facility_id=fac.id).all()
        # Find active share for the year
        partner_allocations = []
        for p in partners:
            # Match share
            p_share = next((s for s in shares if s.partner_id == p.id), None)
            pct = p_share.equity_share_pct if p_share else (fac.equity_share_pct if p.is_operator else 0.0)
            allocated_co2e = total_co2e * (pct / 100.0)
            allocated_ch4 = total_ch4 * (pct / 100.0)

            partner_allocations.append({
                "partner_id": p.id,
                "partner_name": p.name,
                "partner_code": p.code,
                "equity_pct": pct,
                "allocated_co2e": round(allocated_co2e, 2),
                "allocated_ch4": round(allocated_ch4, 2),
            })

        allocation_by_facility.append({
            "facility_id": fac.id,
            "facility_name": fac.name,
            "year": yr,
            "total_co2e": round(total_co2e, 2),
            "total_ch4": round(total_ch4, 2),
            "partners": partner_allocations,
        })

    return jsonify(allocation_by_facility)
