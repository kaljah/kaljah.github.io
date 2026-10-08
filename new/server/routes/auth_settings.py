"""Application settings routes and the in-memory settings store.

Split out of routes/auth.py unchanged (hardening plan, task 5.3). The routes are registered on the
same ``auth_bp`` blueprint, and routes.auth re-exports every name, so imports and URLs are the same.
"""
import datetime
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


def recalculate_all_emissions_gwp(standard, previous=None):
    """
    Recalculates co2e_total for all stored Emission records in the database
    using the specified GWP standard ('AR4', 'AR5', 'AR6').
    Also updates gwp_version on the records and invalidates dashboard caches.

    Scope 2 follows (audit 2026-09-30): grid electricity is recalculated from its grid region's
    CO2 / CH4 / N2O, and steam from the default natural-gas boiler has its CH4 / N2O re-weighted
    (the boiler fuel energy is recovered from the stored CO2e with the `previous` standard).
    """
    from models import Emission, Scope2Emission
    from calculations.constants import GWP_STANDARDS, GWP_AR5, invalidate_gwp_cache
    from sqlalchemy import func

    invalidate_gwp_cache()  # a cached standard would keep new records on the old GWP for 30 s

    std_dict = GWP_STANDARDS.get(standard, GWP_AR5)
    co2_factor = float(std_dict.get("CO2", 1.0))
    ch4_factor = float(std_dict.get("CH4", 28.0))
    n2o_factor = float(std_dict.get("N2O", 265.0))

    # Perform database update
    db.session.query(Emission).update(
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
        elif "steam" in st and old_std and e.co2e and e.emission_factor == _NG_BOILER:
            ratio = _steam_k(new_gwp) / _steam_k(old_std)
            e.co2e = e.co2e * ratio
            if getattr(e, "co2e_location_based", None) is not None:
                e.co2e_location_based = e.co2e_location_based * ratio
            if getattr(e, "co2e_market_based", None) is not None:
                e.co2e_market_based = e.co2e_market_based * ratio

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"Failed to commit GWP recalculations: {exc}")
        raise

    # Clear dashboard cache
    try:
        from routes.dashboard import DASHBOARD_CACHE

        DASHBOARD_CACHE.clear()
    except Exception:
        pass


@auth_bp.route("/settings", methods=["GET"])
@login_required
def get_settings():
    import json

    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None

    # Load fresh persistent settings from DB
    load_settings_from_db()

    # Merge global settings with user preferences
    resp = dict(_app_settings)
    if user and user.preferences:
        try:
            prefs = json.loads(user.preferences)
            if isinstance(prefs, dict):
                resp.update(prefs)
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

    is_admin = user and user.role in ["admin", "superuser"]
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
                recalculate_all_emissions_gwp(_app_settings["gwp_standard"], previous=previous_gwp)
            except Exception as e:
                current_app.logger.error(f"Error recalculating emissions with new GWP: {e}")

    if user:
        try:
            existing = json.loads(user.preferences) if user.preferences else {}
        except Exception:
            existing = {}
        user_pref_keys = ["theme", "unit_system", "consolidation", "notifications", "language"]
        for k, v in data.items():
            if is_admin or k in user_pref_keys or k not in operational_keys:
                if k in ["copernicus_password", "copernicus_client_secret"] and str(v).strip() in ["********", ""]:
                    continue
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
