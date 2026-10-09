"""Application settings routes and the in-memory settings store.

Split out of routes/auth.py unchanged (hardening plan, task 5.3). The routes are registered on the
same ``auth_bp`` blueprint, and routes.auth re-exports every name, so imports and URLs are the same.
"""
from extensions import db
from flask import current_app, jsonify, request, session
from models import User
from utils import log_activity_and_notify
from . import auth_bp
from routes.auth import login_required


_DEFAULT_APP_SETTINGS = {
    "gwp_standard": "AR5",
    "ogmp_default_base_year": 2023,
    "reconciliation_threshold": 20.0,
    "ogmp_upstream_target_pct": 0.20,
    "ogmp_midstream_target_pct": 0.05,
    "copernicus_username": "",
    "copernicus_password": "",
    "copernicus_client_id": "",
    "copernicus_client_secret": "",
    "copernicus_qa_threshold": 0.5,
    "copernicus_enabled": False,
    # CAA s.136 as amended by P.L. 119-21: the charge starts with 2034 emissions at $1,500 / t
    "wec_fee_rates": {"2034": 1500.0},
    "wec_first_year": 2034,
    "theme": "light",
    "unit_system": "metric",
    "auto_flag_discrepancy": True,
    "gwp_values": {
        "AR5": {"ch4_100": 28.0, "ch4_20": 84.0, "n2o_100": 265.0, "n2o_20": 264.0, "co2": 1.0},
        "AR6": {"ch4_100": 27.9, "ch4_20": 81.2, "n2o_100": 273.0, "n2o_20": 273.0, "co2": 1.0},
        "AR4": {"ch4_100": 25.0, "ch4_20": 72.0, "n2o_100": 298.0, "n2o_20": 289.0, "co2": 1.0},
    },
}


_app_settings = dict(_DEFAULT_APP_SETTINGS)

# Organisation-wide keys (SystemSetting); never stored in or overridden by user preferences.
# theme / unit_system stay per-user display preferences.
GLOBAL_SETTING_KEYS = (set(_DEFAULT_APP_SETTINGS) - {"theme", "unit_system"}) | {"gwp_standard"}


def load_settings_from_db():
    """Loads all system settings from SystemSetting table in DB into _app_settings."""
    import json
    try:
        from models import SystemSetting
        settings = SystemSetting.query.all()
        for s in settings:
            try:
                _app_settings[s.key] = json.loads(s.value)
            except Exception:
                _app_settings[s.key] = s.value
    except Exception as e:
        # Table might not exist yet during migration
        pass
    return _app_settings


def save_setting_to_db(key: str, val):
    """Saves a setting to the SystemSetting table and syncs _app_settings."""
    import json
    from models import SystemSetting
    _app_settings[key] = val
    try:
        row = db.session.get(SystemSetting, key)
        if not row:
            row = SystemSetting(key=key, value=json.dumps(val))
            db.session.add(row)
        else:
            row.value = json.dumps(val)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to persist system setting '{key}': {e}")


from services.gwp_recalculation import recalculate_all_emissions_gwp  # noqa: E402,F401  (re-export)


@auth_bp.route("/settings", methods=["GET"])
@login_required
def get_settings():
    import json

    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None

    # Load fresh persistent settings from DB
    load_settings_from_db()

    # Merge global settings with user preferences (display preferences only: a copy of an
    # organisation-wide key saved earlier must not mask the current global value, audit A-03)
    resp = dict(_app_settings)
    if user and user.preferences:
        try:
            prefs = json.loads(user.preferences)
            if isinstance(prefs, dict):
                resp.update({k: v for k, v in prefs.items() if k not in GLOBAL_SETTING_KEYS})
        except Exception:
            pass

    # Mask secrets before returning
    if resp.get("copernicus_password"):
        resp["copernicus_password"] = "********"
    if resp.get("copernicus_client_secret"):
        resp["copernicus_client_secret"] = "********"

    return jsonify(resp)


@auth_bp.route("/settings", methods=["PUT", "POST"])
@login_required
def update_settings():
    import json
    from models import SystemSetting

    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    data = request.get_json() or {}

    load_settings_from_db()

    operational_keys = {
        "gwp_standard",
        "ogmp_default_base_year",
        "reconciliation_threshold",
        "ogmp_upstream_target_pct",
        "ogmp_midstream_target_pct",
        "copernicus_username",
        "copernicus_password",
        "copernicus_client_id",
        "copernicus_client_secret",
        "copernicus_qa_threshold",
        "copernicus_enabled",
        "auto_flag_discrepancy",
        "wec_fee_rates",
    }
    has_operational_keys = any(k in data for k in operational_keys)

    if user and user.role == "it":
        return jsonify({"error": "IT role is not authorized to modify settings."}), 403

    if user and user.role in ["it_admin", "it_manager"] and has_operational_keys:
        return jsonify({"error": "IT administrators are not authorized to modify operational GHG calculation standards or settings."}), 403

    # organisation-wide settings are admin only; superusers are limited to one facility/region
    is_admin = bool(user and user.role == "admin")
    if has_operational_keys and not is_admin:
        return jsonify({"error": "Administrator privileges are required to modify system-wide calculation standards."}), 403

    # Global system & GWP standards updates
    gwp_changed = False
    if is_admin:
        previous_gwp = _app_settings.get("gwp_standard") or "AR5"
        if "gwp_standard" in data and data["gwp_standard"] in ["AR4", "AR5", "AR6"]:
            new_gwp = data["gwp_standard"]
            if _app_settings.get("gwp_standard") != new_gwp:
                _app_settings["gwp_standard"] = new_gwp
                save_setting_to_db("gwp_standard", new_gwp)
                gwp_changed = True

        system_setting_keys = [
            "ogmp_default_base_year",
            "reconciliation_threshold",
            "ogmp_upstream_target_pct",
            "ogmp_midstream_target_pct",
            "copernicus_username",
            "copernicus_password",
            "copernicus_client_id",
            "copernicus_client_secret",
            "copernicus_qa_threshold",
            "copernicus_enabled",
            "theme",
            "unit_system",
            "auto_flag_discrepancy",
        ]

        for k in system_setting_keys:
            if k in data:
                val = data[k]
                if k in ["copernicus_password", "copernicus_client_secret"] and str(val).strip() in ["********", ""]:
                    continue  # Do not overwrite existing secret with mask or empty string
                try:
                    if k == "ogmp_default_base_year":
                        val = int(val)
                    elif k in ["reconciliation_threshold", "ogmp_upstream_target_pct", "ogmp_midstream_target_pct", "copernicus_qa_threshold"]:
                        val = float(val)
                    elif k in ["copernicus_enabled", "auto_flag_discrepancy"]:
                        val = bool(val)
                except (ValueError, TypeError):
                    return jsonify({"error": f"Invalid numerical value for '{k}'"}), 400
                _app_settings[k] = val
                save_setting_to_db(k, val)

        if "wec_fee_rates" in data and isinstance(data["wec_fee_rates"], dict):
            rates = _app_settings.get("wec_fee_rates", {})
            try:
                rates.update({str(k): float(v) for k, v in data["wec_fee_rates"].items()})
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid numerical rate in wec_fee_rates"}), 400
            _app_settings["wec_fee_rates"] = rates
            save_setting_to_db("wec_fee_rates", rates)

        # If GWP standard was changed or set, recalculate existing emissions
        if gwp_changed:
            try:
                recalculate_all_emissions_gwp(_app_settings["gwp_standard"], previous=previous_gwp, user=user)
            except Exception as e:
                current_app.logger.error(f"Error recalculating emissions with new GWP: {e}")

    if user:
        try:
            existing = json.loads(user.preferences) if user.preferences else {}
        except Exception:
            existing = {}
        # Audit A-03: organisation-wide keys live in SystemSetting only. Copying them into the
        # admin's preferences stored the Copernicus secrets in plain text and pinned a stale GWP
        # standard on that admin's Settings page (re-saving it reverted the global standard).
        existing = {k: v for k, v in existing.items() if k not in GLOBAL_SETTING_KEYS}
        for k, v in data.items():
            if k not in GLOBAL_SETTING_KEYS:
                existing[k] = v
        user.preferences = json.dumps(existing)

        if "consolidation" in data:
            user.consolidationApproach = data["consolidation"]

        try:
            log_activity_and_notify(
                action="UPDATE",
                record_id=str(user.id),
                user=user,
                request=request,
                entity="User",
                details=f"Updated settings for user: {user.email} (GWP: {_app_settings.get('gwp_standard', 'AR4')})",
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Audit Log Error on update_settings: {e}")
            return jsonify({"error": "Failed to update settings"}), 500

    try:
        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
    except Exception:
        pass

    out_settings = dict(_app_settings)
    if out_settings.get("copernicus_password"):
        out_settings["copernicus_password"] = "********"
    if out_settings.get("copernicus_client_secret"):
        out_settings["copernicus_client_secret"] = "********"

    return jsonify(
        {"message": "Settings saved successfully", "settings": out_settings}
    )
