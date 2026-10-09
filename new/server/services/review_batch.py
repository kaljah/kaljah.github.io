"""Batch approve / reject of records awaiting review (Scope 1, 2, 3 and CAP).

Parses the batch body, validates the record ids, applies the decisions through services.maker_checker
and explains every requested record it did not decide (pilot check 2026-10-09, F7: the batch answered
"success" with 0 records and no reason when every record was the reviewer's own; F13: junk ids raised
a 500).
"""
from extensions import db
from services.maker_checker import REVIEWABLE_STATUSES, DecisionError, _model, decide
from utils import get_allowed_facility_ids


def batch_targets(data, all_flag):
    """Map the batch body to {scope: ids | None}. Plain `ids` are only unambiguous for one scope."""
    scope = str(data.get("scope", "1"))
    by_scope = data.get("by_scope") if isinstance(data.get("by_scope"), dict) else {}
    picked = {}
    for k in ("1", "2", "3", "cap"):
        ids = by_scope.get(k) or (by_scope.get(int(k)) if k.isdigit() else None)
        if ids:
            picked[k] = list(ids)
    if picked:
        return picked
    if scope == "all":
        if all_flag:
            return {"1": None, "2": None, "3": None}
        return None  # ids without by_scope would hit the same ids in every table
    if scope in ("1", "2", "3", "cap"):
        return {scope: None if all_flag else list(data.get("ids") or [])}
    return None


def valid_ids(ids):
    """Record ids of a batch body: positive integers (F13: junk values raised a 500)."""
    if not isinstance(ids, list):
        return None
    out = []
    for v in ids:
        if isinstance(v, bool) or not isinstance(v, (int, str)):
            return None
        try:
            n = int(v)
        except ValueError:
            return None
        if not 0 < n < 2**31:
            return None
        out.append(n)
    return out


def explain_skipped(user, scope, ids, decision):
    """Why each of `ids` was not decided by a batch call (pilot check 2026-10-09, F7: the batch answered
    "success" with 0 records and no reason when every record was the reviewer's own)."""
    model, _label = _model(scope)
    allowed = get_allowed_facility_ids(user)
    out = []
    for rec_id in ids:
        record = db.session.get(model, rec_id)
        if record is None:
            reason = "Record not found"
        elif allowed is not None and record.facility_id not in allowed:
            reason = "Outside your facilities or region"
        elif record.status not in REVIEWABLE_STATUSES:
            reason = f"Already {record.status}"
        elif decision == "approve" and user.id in {record.created_by, getattr(record, "updated_by", None)}:
            reason = "You created or last changed this record; another reviewer must approve it"
        else:
            reason = "Decided by another reviewer at the same time"
        out.append({"scope": scope, "id": rec_id, "reason": reason})
    return out


def run_batch(user, data, decision, request=None):
    """Decide the records of a batch body. Returns (decided ids, skipped records with the reason);
    raises DecisionError for a body that names no records or malformed ids."""
    all_flag = bool(data.get("approve_all") if decision == "approve" else data.get("reject_all"))
    targets = batch_targets(data, all_flag)
    if not targets:
        raise DecisionError("Provide by_scope ids, a single scope with ids, or scope='all' with the all flag", 400)
    for scope, ids in list(targets.items()):
        if ids is not None:
            targets[scope] = valid_ids(ids)
            if targets[scope] is None:
                raise DecisionError("ids must be a list of record numbers", 400)
    reason = str(data.get("reason") or "Batch rejected by reviewer")
    done, skipped = [], []
    for scope, ids in targets.items():
        if ids is not None and not ids:
            continue
        decided = decide(user, scope, ids, decision, reason=reason, request=request)
        done += decided
        if ids is not None:
            skipped += explain_skipped(user, scope, [i for i in ids if i not in set(decided)], decision)
    return done, skipped
