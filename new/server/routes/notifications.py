import json
import time
from flask import (
    Blueprint,
    jsonify,
    request,
    session,
    Response,
    stream_with_context,
    current_app,
)
from routes.auth import login_required
from extensions import db
from models import Notification

notifications_bp = Blueprint("notifications", __name__)


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
        .limit(50)
        .all()
    )

    return jsonify(
        [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "time": n.created_at.isoformat() + "Z",
                "metadata": n.metadata_json,
            }
            for n in notifs
        ]
    )


@notifications_bp.route("/stream")
@login_required
def stream_notifications():
    """
    Server-Sent Events endpoint for real-time notification delivery.

    Deployment-ready: uses DB polling (2 s interval) so every worker in a
    multi-process gunicorn deployment reads from the shared database.  No
    Redis or message broker is required.

    The client connects with ?last_id=<int> as a cursor so that reconnects
    (browser tab restored, network blip) never miss events.

    X-Accel-Buffering: no  — disables nginx proxy buffering so events flow
    through immediately in production deployments behind nginx/gunicorn.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    last_id = request.args.get("last_id", 0, type=int)

    def generate(uid, lid):
        yield ": connected\n\n"

        start_time = time.time()
        last_heartbeat = start_time
        MAX_STREAM_DURATION = 45  # Cycle worker threads every 45s to prevent Gunicorn worker starvation
        POLL_INTERVAL = 2
        HEARTBEAT_INTERVAL = 20

        try:
            while time.time() - start_time < MAX_STREAM_DURATION:
                try:
                    new_notifs = (
                        Notification.query.filter(
                            ((Notification.user_id == uid) | (Notification.user_id == None)),
                            Notification.id > lid,
                        )
                        .order_by(Notification.id.asc())
                        .all()
                    )

                    for n in new_notifs:
                        payload = json.dumps(
                            {
                                "id": n.id,
                                "type": n.type,
                                "title": n.title,
                                "message": n.message,
                                "is_read": n.is_read,
                                "time": n.created_at.isoformat() + "Z",
                            }
                        )
                        yield f"data: {payload}\n\n"
                        lid = n.id

                    now = time.time()
                    if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                        yield ": heartbeat\n\n"
                        last_heartbeat = now

                    time.sleep(POLL_INTERVAL)

                except GeneratorExit:
                    return
                except Exception as exc:
                    try:
                        current_app.logger.error(f"SSE stream error for user {uid}: {exc}")
                    except Exception:
                        pass
                    time.sleep(POLL_INTERVAL)

            # Instruct browser EventSource to reconnect cleanly without treating end-of-stream as an error
            yield "retry: 1000\n\n"
            yield ": session-cycle\n\n"
        finally:
            # Explicitly return DB connection to pool when worker thread finishes or client disconnects
            try:
                db.session.remove()
            except Exception:
                pass

    return Response(
        stream_with_context(generate(user_id, last_id)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


from utils import get_current_user


@notifications_bp.route("/<int:id>/read", methods=["PUT"])
@login_required
def mark_read(id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    n = Notification.query.get_or_404(id)
    if n.user_id is None:
        # Broadcast/system notification: allowed to mark read by any authenticated user
        pass
    elif n.user_id != user.id and user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Unauthorized"}), 403

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

    if user.role in ["admin", "superuser"]:
        Notification.query.filter(
            ((Notification.user_id == user.id) | (Notification.user_id == None)),
            Notification.is_read == False,
        ).update({"is_read": True}, synchronize_session="fetch")
    else:
        Notification.query.filter_by(user_id=user.id, is_read=False).update(
            {"is_read": True}
        )
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to dismiss notifications"}), 500
    return jsonify({"success": True})


@notifications_bp.route("/<int:id>", methods=["DELETE"])
@login_required
def delete_notification(id):
    """Permanently delete a single notification."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    n = Notification.query.get_or_404(id)
    if n.user_id is None:
        if user.role not in ["admin", "superuser"]:
            return jsonify({"error": "Only administrators can delete system notifications"}), 403
    elif n.user_id != user.id and user.role not in ["admin", "superuser"]:
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
    """Permanently delete all notifications for the current user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        deleted = Notification.query.filter_by(user_id=user.id).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete notifications"}), 500
    return jsonify({"success": True, "deleted": deleted})
