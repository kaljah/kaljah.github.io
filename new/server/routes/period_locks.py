"""
Reporting Period Lock API Routes (Part 2.3)
===========================================
Endpoints:
- GET  /api/period-locks           : List all locked and historical periods
- GET  /api/period-locks/status/<y>: Check lock status of a specific year
- POST /api/period-locks/lock      : Lock a reporting period with signatory & notes (Admin/Auditor)
- POST /api/period-locks/unlock    : Unlock a locked period with mandatory justification (Admin only)
"""
import datetime
from flask import Blueprint, request, jsonify, session
from extensions import db
from models import PeriodLock, User
from routes.auth import login_required, admin_required
from utils import get_current_tenant_id, get_current_user, log_activity_and_notify, tenant_matches

period_locks_bp = Blueprint("period_locks", __name__, url_prefix="/api/period-locks")


@period_locks_bp.route("", methods=["GET"])
@period_locks_bp.route("/", methods=["GET"])
@login_required
def get_period_locks():
    """List all period locks for the caller's tenant."""
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)
    locks = (
        PeriodLock.query.filter(tenant_matches(PeriodLock.tenant_id, caller_tenant))
        .order_by(PeriodLock.year.desc(), PeriodLock.month.asc())
        .all()
    )
    return jsonify([l.to_dict() for l in locks]), 200


@period_locks_bp.route("/status/<int:year>", methods=["GET"])
@login_required
def get_period_lock_status(year):
    """Check if a specific reporting year is locked for the caller's tenant."""
    from services.period_lock_service import is_period_locked
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)
    locked = is_period_locked(year, tenant_id=caller_tenant)
    lock_record = (
        PeriodLock.query.filter(
            tenant_matches(PeriodLock.tenant_id, caller_tenant),
            PeriodLock.year == year,
            PeriodLock.status == "locked",
        )
        .first()
    )
    return jsonify({
        "year": year,
        "is_locked": locked,
        "lock_details": lock_record.to_dict() if lock_record else None,
    }), 200


@period_locks_bp.route("/lock", methods=["POST"])
@login_required
def lock_period():
    """Part 2.3: Lock a reporting period after formal sign-off (Admin or Auditor)."""
    user = get_current_user()
    if not user or user.role not in ("admin", "auditor", "superuser"):
        return jsonify({"error": "Only Administrators or Lead Auditors can lock a reporting period"}), 403
    caller_tenant = get_current_tenant_id(user)

    data = request.get_json() or {}
    year = data.get("year")
    if not year:
        return jsonify({"error": "Reporting year is required", "field": "year"}), 400
    try:
        y = int(year)
    except (ValueError, TypeError):
        return jsonify({"error": "Year must be an integer", "field": "year"}), 400

    month = data.get("month")
    m = int(month) if month is not None else None

    signatory = str(data.get("signoff_signatory") or "").strip()
    if not signatory:
        return jsonify({"error": "Sign-off signatory name/title is required for statutory period locking", "field": "signoff_signatory"}), 400

    notes = str(data.get("signoff_notes") or "").strip()

    # Find existing or create new lock scoped to caller's tenant
    lock = (
        PeriodLock.query.filter(
            tenant_matches(PeriodLock.tenant_id, caller_tenant),
            PeriodLock.year == y,
            PeriodLock.month == m,
        )
        .first()
    )
    if not lock:
        lock = PeriodLock(
            tenant_id=caller_tenant,
            year=y,
            month=m,
            status="locked",
            locked_at=datetime.datetime.now(datetime.timezone.utc),
            locked_by=user.id,
            signoff_signatory=signatory,
            signoff_notes=notes,
        )
        db.session.add(lock)
    else:
        lock.tenant_id = caller_tenant
        lock.status = "locked"
        lock.locked_at = datetime.datetime.now(datetime.timezone.utc)
        lock.locked_by = user.id
        lock.signoff_signatory = signatory
        lock.signoff_notes = notes
        lock.unlocked_at = None
        lock.unlocked_by = None
        lock.unlock_reason = None

    db.session.commit()

    log_activity_and_notify(
        action="PERIOD_LOCKED",
        record_id=str(lock.id),
        user=user,
        request=request,
        entity="PeriodLock",
        details=f"Reporting period {y}{f'-M{m}' if m else ''} locked by {user.fullName} with sign-off signatory '{signatory}'",
    )

    return jsonify({
        "message": f"Reporting period {y} successfully locked after sign-off",
        "lock": lock.to_dict(),
    }), 201


@period_locks_bp.route("/unlock", methods=["POST"])
@admin_required
def unlock_period():
    """Part 2.3: Unlock a locked reporting period with mandatory justification (Admin only)."""
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)
    data = request.get_json() or {}
    year = data.get("year")
    if not year:
        return jsonify({"error": "Reporting year is required", "field": "year"}), 400
    try:
        y = int(year)
    except (ValueError, TypeError):
        return jsonify({"error": "Year must be an integer", "field": "year"}), 400

    reason = str(data.get("reason") or "").strip()
    if len(reason) < 10:
        return jsonify({
            "error": "A detailed justification is mandatory to unlock a statutory reporting period (minimum 10 characters)",
            "field": "reason",
        }), 400

    month = data.get("month")
    m = int(month) if month is not None else None

    locks = PeriodLock.query.filter(
        tenant_matches(PeriodLock.tenant_id, caller_tenant),
        PeriodLock.year == y,
    ).all()
    if m is not None:
        locks = [l for l in locks if l.month == m or l.month is None]

    if not locks:
        return jsonify({"error": f"No active lock found for year {y}"}), 404

    now = datetime.datetime.now(datetime.timezone.utc)
    for l in locks:
        l.status = "open"
        l.unlocked_at = now
        l.unlocked_by = user.id
        l.unlock_reason = reason

    db.session.commit()

    log_activity_and_notify(
        action="PERIOD_UNLOCKED",
        record_id=str(locks[0].id),
        user=user,
        request=request,
        entity="PeriodLock",
        details=f"HIGH SEVERITY: Reporting period {y} unlocked by Administrator {user.fullName}. Justification: {reason}",
    )

    return jsonify({
        "message": f"Reporting period {y} unlocked successfully",
        "unlocked_by": user.fullName,
        "reason": reason,
    }), 200
