import json
from flask import Blueprint, jsonify, request, session
from routes.auth import login_required
from extensions import db
from models import Notification

notifications_bp = Blueprint("notifications", __name__)


def _is_read_for_user(n, uid):
    if n.user_id is not None:
        return bool(n.is_read)
    if n.metadata_json:
        try:
            meta = json.loads(n.metadata_json)
            if uid in meta.get("read_by", []):
                return True
        except Exception:
            pass
    return False


@notifications_bp.route("/", methods=["GET"])
@login_required
def get_notifications():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    notifs = (
        Notification.query.filter(
            (Notification.user_id == user_id) | (Notification.user_id == None)
        )
        .order_by(Notification.created_at.desc())
        .limit(100)
        .all()
    )

    result = []
    for n in notifs:
        if n.user_id is None and n.metadata_json:
            try:
                meta = json.loads(n.metadata_json)
                dismissed = meta.get("dismissed_by", []) or meta.get("deleted_by", [])
                if user_id in dismissed:
                    continue
            except Exception:
                pass
        result.append(
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "is_read": _is_read_for_user(n, user_id),
                "time": n.created_at.isoformat() + "Z",
                "metadata": n.metadata_json,
            }
        )
    return jsonify(result[:50])


from utils import get_current_user


@notifications_bp.route("/<int:id>/read", methods=["PUT", "PATCH"])
@login_required
def mark_read(id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    n = Notification.query.get_or_404(id)
    if n.user_id is None:
        try:
            meta = json.loads(n.metadata_json) if n.metadata_json else {}
        except Exception:
            meta = {}
        read_by = meta.get("read_by", [])
        if user.id not in read_by:
            read_by.append(user.id)
            meta["read_by"] = read_by
            n.metadata_json = json.dumps(meta)
    elif n.user_id != user.id and user.role not in ["admin", "superuser", "it_manager"]:
        return jsonify({"error": "Unauthorized"}), 403
    else:
        n.is_read = True

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update notification"}), 500
    return jsonify({"success": True})


@notifications_bp.route("/dismiss-all", methods=["POST"])
@login_required
def dismiss_all():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    Notification.query.filter_by(user_id=user.id, is_read=False).update(
        {"is_read": True}
    )
    broadcasts = Notification.query.filter(
        Notification.user_id.is_(None)
    ).all()
    for b in broadcasts:
        try:
            meta = json.loads(b.metadata_json) if b.metadata_json else {}
        except Exception:
            meta = {}
        read_by = meta.get("read_by", [])
        if user.id not in read_by:
            read_by.append(user.id)
            meta["read_by"] = read_by
        if user.role in ["admin", "superuser", "it_manager"]:
            b.is_read = True
        b.metadata_json = json.dumps(meta)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to dismiss notifications"}), 500
    return jsonify({"success": True})


@notifications_bp.route("/<int:id>", methods=["DELETE"])
@login_required
def delete_notification(id):
    """Permanently delete a user notification or soft-dismiss a system broadcast for the current user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    n = Notification.query.get_or_404(id)
    if n.user_id is None:
        # Check if an explicit global purge is requested by a privileged administrator
        is_global = request.args.get("global", "").lower() in ("true", "1")
        if is_global:
            if user.role not in ["admin", "superuser"]:
                return jsonify({"error": "Only global administrators can delete system notifications globally"}), 403
            try:
                db.session.delete(n)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return jsonify({"error": "Failed to delete notification"}), 500
            return jsonify({"success": True})

        # Soft-dismiss for this specific user
        try:
            meta = json.loads(n.metadata_json) if n.metadata_json else {}
        except Exception:
            meta = {}
        dismissed_by = meta.get("dismissed_by", [])
        if user.id not in dismissed_by:
            dismissed_by.append(user.id)
            meta["dismissed_by"] = dismissed_by
            n.metadata_json = json.dumps(meta)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Failed to dismiss notification"}), 500
        return jsonify({"success": True})

    elif n.user_id != user.id and user.role not in ["admin", "superuser", "it_manager"]:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        db.session.delete(n)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete notification"}), 500
    return jsonify({"success": True})


@notifications_bp.route("/all", methods=["DELETE"])
@login_required
def delete_all_notifications():
    """Permanently delete all notifications for the current user and soft-dismiss broadcasts."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        deleted = Notification.query.filter_by(user_id=user.id).delete()
        broadcasts = Notification.query.filter(Notification.user_id.is_(None)).all()
        for b in broadcasts:
            try:
                meta = json.loads(b.metadata_json) if b.metadata_json else {}
            except Exception:
                meta = {}
            dismissed_by = meta.get("dismissed_by", [])
            if user.id not in dismissed_by:
                dismissed_by.append(user.id)
                meta["dismissed_by"] = dismissed_by
                b.metadata_json = json.dumps(meta)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete notifications"}), 500
    return jsonify({"success": True, "deleted": deleted})
