"""Single maker-checker state machine for every approvable record type (audit RC-2).

Rules (one place, used by the single and batch approve/reject endpoints):
- Only admin / superuser may decide, and only on records inside their facility scope.
- Only records awaiting review (Pending / legacy "Pending Approval" / Draft) can be decided;
  an already Verified or Rejected record cannot be flipped (BUG-070).
- An approver may not approve a record they created or last modified (BUG-067).
- The decision is an atomic conditional UPDATE ... WHERE status IN (...) so concurrent
  decisions cannot both succeed (BUG-074).
- The approver's identity is snapshotted on the record (BUG-069) and the maker is notified
  of the outcome (BUG-092).
"""
import datetime

from sqlalchemy import or_

from extensions import db
from models import CapEmission, Emission, Notification, Scope2Emission, Scope3Emission
from utils import get_allowed_facility_ids, log_activity_and_notify, user_label

REVIEWABLE_STATUSES = ("Pending", "Pending Approval", "Draft")
APPROVER_ROLES = ("admin", "superuser")

RECORD_TYPES = {
    "1": (Emission, "Scope 1"),
    "2": (Scope2Emission, "Scope 2"),
    "3": (Scope3Emission, "Scope 3"),
    "cap": (CapEmission, "CAP"),
}


class DecisionError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _model(scope):
    try:
        return RECORD_TYPES[str(scope).lower()]
    except KeyError:
        raise DecisionError(f"Invalid scope: {scope}")


def _reviewable_query(model, user, ids=None, approving=True):
    q = model.query.filter(model.status.in_(REVIEWABLE_STATUSES))
    allowed = get_allowed_facility_ids(user)
    if allowed is not None:
        q = q.filter(model.facility_id.in_(allowed or [-1]))
    if approving:
        # segregation of duties: neither the maker nor the last modifier may approve
        q = q.filter(or_(model.created_by.is_(None), model.created_by != user.id))
        if hasattr(model, "updated_by"):
            q = q.filter(or_(model.updated_by.is_(None), model.updated_by != user.id))
    if ids is not None:
        q = q.filter(model.id.in_([int(i) for i in ids] or [-1]))
    return q


def _values(model, user, decision, reason):
    now = datetime.datetime.now(datetime.timezone.utc)
    vals = {
        "status": "Verified" if decision == "approve" else "Rejected",
        "approved_by": user.id,
        "approved_at": now,
    }
    if hasattr(model, "approved_by_name"):
        vals["approved_by_name"] = user_label(user)
    if decision == "reject" and hasattr(model, "qa_flag"):
        vals["qa_flag"] = f"Rejected: {reason}"[:255]
    return vals


def _notify_makers(rows, label, decision, user, reason):
    verb = "approved" if decision == "approve" else "rejected"
    for rec_id, maker_id, facility_id in rows:
        if not maker_id or maker_id == user.id:
            continue
        msg = f"Your {label} record #{rec_id} was {verb} by {user.fullName}."
        if decision == "reject":
            msg += f" Reason: {reason}. It is excluded from totals."
        Notification.create(
            title=f"{label} record {verb}",
            message=msg,
            type="APPROVAL" if decision == "approve" else "REJECTION",
            user_id=maker_id,
            metadata={"record_id": rec_id, "scope_label": label, "facility_id": facility_id, "decision": verb},
        )


def decide(user, scope, ids, decision, reason=None, request=None):
    """Approve or reject `ids` (None = every reviewable record in scope). Returns affected ids."""
    if decision not in ("approve", "reject"):
        raise DecisionError("decision must be approve or reject")
    if not user or user.role not in APPROVER_ROLES:
        raise DecisionError("Only admins and super users can review records", 403)
    model, label = _model(scope)
    reason = (reason or "Rejected by reviewer").strip() if decision == "reject" else None

    candidates = _reviewable_query(model, user, ids, approving=decision == "approve")
    rows = candidates.with_entities(model.id, model.created_by, model.facility_id).all()
    if not rows:
        return []
    # Atomic per record: the UPDATE re-applies the status / segregation predicate, and only a
    # rowcount of 1 proves that *this* call made the decision (BUG-074: the same reviewer
    # clicking twice, or two reviewers racing, can never both succeed).
    values = _values(model, user, decision, reason)
    won = set()
    for rec_id, _maker, _fac in rows:
        n = _reviewable_query(model, user, [rec_id], approving=decision == "approve").update(
            values, synchronize_session=False
        )
        if n == 1:
            won.add(rec_id)
    rows = [r for r in rows if r[0] in won]
    target = [r[0] for r in rows]
    _notify_makers(rows, label, decision, user, reason)
    for rec_id, _maker, facility_id in rows:
        log_activity_and_notify(
            action="APPROVE" if decision == "approve" else "REJECT",
            record_id=f"{label}-{rec_id}",
            details=f"{label} record {rec_id} {'approved' if decision == 'approve' else 'rejected'} by {user.fullName}"
            + (f": {reason}" if reason else ""),
            user=user,
            request=request,
            entity=model.__name__,
            entity_id=rec_id,
            facility_id=facility_id,
        )
    return target


def decide_single(user, scope, record_id, decision, reason=None, request=None):
    """Single-record variant with precise error codes (404 / 403 / 409)."""
    model, label = _model(scope)
    record = db.session.get(model, record_id)
    if record is None:
        raise DecisionError("Record not found", 404)
    if not user or user.role not in APPROVER_ROLES:
        raise DecisionError("Only admins and super users can review records", 403)
    allowed = get_allowed_facility_ids(user)
    if allowed is not None and record.facility_id not in allowed:
        raise DecisionError("Access to record facility is denied", 403)
    if record.status not in REVIEWABLE_STATUSES:
        raise DecisionError(f"Record is already {record.status}; only records awaiting review can be decided", 409)
    if decision == "approve" and user.id in {record.created_by, getattr(record, "updated_by", None)}:
        raise DecisionError("Maker-Checker violation: you cannot approve a record you created or last modified", 403)
    done = decide(user, scope, [record_id], decision, reason, request)
    if not done:
        raise DecisionError("Record was decided concurrently by another reviewer", 409)
    return label


# ── Edit / delete rules (BUG-067) ───────────────────────────────────────────────

def on_edit(record, user):
    """Call on every accepted edit. Records the last modifier and sends decided records back
    to review unless the editor is an admin (admins' own entries are auto-verified, D-04)."""
    if hasattr(record, "updated_by"):
        record.updated_by = user.id
    if record.status in ("Verified", "Rejected") and user.role != "admin":
        record.status = "Pending"
        record.approved_by = None
        record.approved_at = None
        if hasattr(record, "approved_by_name"):
            record.approved_by_name = None
    elif record.status in ("Verified", "Rejected") and user.role == "admin":
        # an admin edit re-verifies under the admin's own name (maker = checker = admin, D-04)
        if record.status == "Verified":
            record.approved_by = user.id
            record.approved_at = datetime.datetime.now(datetime.timezone.utc)
            if hasattr(record, "approved_by_name"):
                record.approved_by_name = user_label(user)


def delete_denied_reason(user, record):
    """None when `user` may delete `record`, else the reason (HTTP 403)."""
    if not user or user.role in ("auditor", "it_admin", "it_manager", "it"):
        return "Forbidden: this account cannot delete emission records"
    allowed = get_allowed_facility_ids(user)
    if allowed is not None and record.facility_id not in allowed:
        return "Forbidden: Outside your region"
    if user.role == "admin":
        return None
    if record.status == "Verified":
        return "Forbidden: approved (Verified) records can only be deleted by an administrator"
    if user.role == "user" and record.created_by != user.id:
        return "Forbidden: You do not have permission to delete records created by another user"
    return None
