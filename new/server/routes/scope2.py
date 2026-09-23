from flask import Blueprint, request, jsonify, session
from models import User, Scope2Emission, Facility
from extensions import db
from sqlalchemy import func
from electricity_factors import GRID_FACTORS
from routes.auth import login_required
from calculations.uncertainty import propagate_uncertainty, Tier
from utils import get_current_user, get_allowed_facility_ids, require_facility_access
import datetime

scope2_bp = Blueprint("scope2", __name__)

# Default emission factor for natural-gas-fired boilers (indirect steam)
# Per EPA AP-42 / API Compendium: ~53.06 kg CO2/MMBtu for natural gas
_DEFAULT_BOILER_EF_KG_PER_MMBTU = 53.06


def _calc_indirect_steam(data):
    """Calculate tCO2e for indirect steam / heat entry."""
    amount = float(data.get("amount") or data.get("heat_mmbtu") or 0)
    unit = (data.get("unit") or "mmbtu").lower().replace(" ", "")
    ci = data.get("calc_inputs", {}).get("indirect_steam", {})
    boiler_eff = float(data.get("boiler_efficiency") or ci.get("boiler_eff", 0.80))
    trans_loss = float(ci.get("trans_loss", 0.0))
    ef_co2 = float(ci.get("ef_co2", _DEFAULT_BOILER_EF_KG_PER_MMBTU))
    if 0 < ef_co2 < 1.0:
        ef_co2 = ef_co2 * 1000.0

    # Normalise input to MMBtu
    # Conversion factors:
    #   1 BTU  = 1/1,000,000 MMBtu
    #   1 MJ   = 947.817 BTU  → 0.000947817 MMBtu
    #   1 GJ   = 1,000 MJ     → 0.947817 MMBtu  (= 1/1.05505585)
    #   1 kWh  = 3,412.142 BTU → 0.003412142 MMBtu
    #   1 MWh  = 3,412,142 BTU → 3.412142 MMBtu
    if unit in ["btu"]:
        energy_mmbtu = amount / 1_000_000.0
    elif unit in ["mj", "megajoule", "mega_joule"]:
        energy_mmbtu = amount * 0.000947817  # 1 MJ = 0.000947817 MMBtu
    elif unit in ["gj", "gigajoule"]:
        energy_mmbtu = amount * 0.947817  # 1 GJ = 0.947817 MMBtu
    elif unit in ["kwh", "kw-hr", "kilowatthour"]:
        energy_mmbtu = amount * 0.003412142
    elif unit in ["mwh", "mw-hr"]:
        energy_mmbtu = amount * 3.412142
    elif unit in ["ton", "us_ton", "short_ton"]:
        # Saturated steam: 1 US ton (~2000 lb) = 2.0 MMBtu (or specific enthalpy)
        enthalpy = float(ci.get("steam_enthalpy") or 2.0)
        energy_mmbtu = amount * enthalpy
    elif unit in ["tonne", "metric_ton", "mt"]:
        # 1 metric tonne = 2.20462 MMBtu (or specific enthalpy)
        enthalpy = float(ci.get("steam_enthalpy") or 2.20462)
        energy_mmbtu = amount * enthalpy
    elif unit in ["mlb", "klb", "thousand_lbs"]:
        # 1,000 lbs steam = 1.0 MMBtu
        energy_mmbtu = amount * 1.0
    elif unit in ["lb", "lbs", "pound", "pounds"]:
        energy_mmbtu = amount * 0.001
    elif unit in ["kg", "kilogram"]:
        energy_mmbtu = amount * 0.00220462
    else:  # assume already in MMBtu
        energy_mmbtu = amount

    net_eff = boiler_eff * (1.0 - trans_loss)
    if net_eff <= 0:
        raise ValueError(
            f"Net efficiency must be greater than 0 (got {net_eff:.4f}). "
            f"Check boiler efficiency ({boiler_eff}) and transmission loss ({trans_loss})."
        )
    co2_kg = (energy_mmbtu * ef_co2) / net_eff
    return co2_kg / 1000.0, energy_mmbtu, ef_co2


def _calc_cogen_allocation(data):
    """Calculate heat-allocated tCO2e for CHP / cogeneration entry."""
    val = float(data.get("amount", 0) or data.get("co2e", 0) or data.get("total_emissions", 0))
    ci = data.get("calc_inputs", {}).get("cogen_allocation", {})
    total_emissions = float(data.get("total_emissions") or ci.get("total_emissions", val))
    if total_emissions == 0 and data.get("fuel_consumed_mmbtu"):
        # Calculate facility emissions from fuel consumed (e.g. 53.06 kg CO2/MMBtu)
        total_emissions = (float(data["fuel_consumed_mmbtu"]) * _DEFAULT_BOILER_EF_KG_PER_MMBTU) / 1000.0
    heat_output = float(data.get("heat_output_mmbtu") or ci.get("heat_output", 0))
    power_output = float(data.get("power_output_mwh") or ci.get("power_output", 0))
    method = data.get("allocation_method") or ci.get("allocation_method", "wri_efficiency")

    if method == "wri_efficiency":
        e_h, e_p = 0.8, 0.33
        denom = (heat_output / e_h) + (power_output / e_p)
        allocated = ((heat_output / e_h) / denom) * total_emissions if denom else 0
    else:
        denom = heat_output + power_output
        allocated = (heat_output / denom) * total_emissions if denom else 0
    return allocated


@scope2_bp.route("", methods=["GET"])
@login_required
def get_scope2_emissions():
    """Get all Scope 2 emissions, scoped to the requesting user's allowed facilities."""
    try:
        user = get_current_user()
        if user and user.role in ["it_admin", "it_manager", "it"]:
            return jsonify({"error": "IT personnel do not have access to emission data"}), 403

        allowed_fids = get_allowed_facility_ids(user)

        query = Scope2Emission.query
        # Apply facility-based RLS (same pattern as Scope 1 / Dashboard)
        if allowed_fids is not None:
            query = query.filter(Scope2Emission.facility_id.in_(allowed_fids))

        # Optional query-string filters
        year_arg = request.args.get("year")
        facility_arg = request.args.get("facilityId") or request.args.get("facility_id")
        if year_arg and year_arg != "all":
            try:
                query = query.filter(Scope2Emission.year == int(year_arg))
            except ValueError:
                pass
        if facility_arg and facility_arg != "all":
            try:
                query = query.filter(Scope2Emission.facility_id == int(facility_arg))
            except ValueError:
                pass

        emissions = query.order_by(Scope2Emission.created_at.desc()).all()
        return jsonify(
            [
                {
                    "id": e.id,
                    "facility_id": e.facility_id,
                    "year": e.year,
                    "month": e.month,
                    "source_type": e.source_type,
                    "electricity_kwh": float(e.electricity_kwh or 0),
                    "steam_ton": float(e.steam_ton or 0),
                    "heat_mmbtu": float(e.heat_mmbtu or 0),
                    "cooling_ton": float(e.cooling_ton or 0),
                    "emission_factor": float(e.emission_factor or 0),
                    "co2e": float(e.co2e or 0),
                    "location": e.location,
                    "grid_region": e.grid_region,
                    "activity": e.activity,
                    "division": e.division,
                    "field": e.field,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in emissions
            ]
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@scope2_bp.route("", methods=["POST"])
@login_required
def create_scope2_emission():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["auditor", "it_admin", "it_manager", "it"]:
        return jsonify({"error": "Read-only or administrative role cannot create emission records"}), 403

    data = request.get_json() or {}
    facility_id = data.get("facility_id")
    if not facility_id:
        return jsonify({"error": "Missing facility_id"}), 422

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and int(facility_id) not in allowed_fids:
        return jsonify({"error": "Unauthorized for this facility"}), 403

    user_id = user.id
    source_type = data.get("source_type", "electricity")

    # --- Run calculation for source types ---
    co2e = float(data.get("co2e", 0))
    emission_factor = float(data.get("emission_factor", 0))
    electricity_kwh = float(data.get("electricity_kwh", 0))
    heat_mmbtu = 0.0

    if source_type == "electricity":
        # Authoritative server-side electricity calculation
        if electricity_kwh == 0 and data.get("amount"):
            raw_amt = float(data.get("amount", 0))
            raw_unit = str(data.get("unit") or "kwh").lower().strip()
            if raw_unit in ["mwh", "mw-hr", "megawatthour"]:
                electricity_kwh = raw_amt * 1000.0
            elif raw_unit in ["gwh", "gw-hr", "gigawatthour"]:
                electricity_kwh = raw_amt * 1_000_000.0
            else:
                electricity_kwh = raw_amt

        grid_region = data.get("grid_region") or data.get("location")
        grid_entry = GRID_FACTORS.get(grid_region, {})
        resolved_ef = grid_entry.get("factor") if grid_entry else None
        if resolved_ef is not None:
            emission_factor = float(resolved_ef)

        if emission_factor > 0 and (electricity_kwh > 0 or co2e == 0):
            co2e = (electricity_kwh * emission_factor) / 1000.0

    elif source_type == "indirect_steam":
        try:
            co2e, heat_mmbtu, emission_factor = _calc_indirect_steam(data)
        except Exception as exc:
            return jsonify({"error": f"Indirect steam calculation failed: {exc}"}), 422

    elif source_type == "cogen_allocation":
        try:
            co2e = _calc_cogen_allocation(data)
        except Exception as exc:
            return jsonify({"error": f"CHP allocation calculation failed: {exc}"}), 422

    # Calculate uncertainty
    provided_uncertainty = data.get("uncertainty")
    if provided_uncertainty is not None:
        final_uncertainty = float(provided_uncertainty)
    else:
        # Default Scope 2 uncertainty (5% EF, 2% AD -> ~5.4% combined)
        u_res = propagate_uncertainty(
            co2e,
            ef_uncertainty=0.05,
            activity_uncertainty=0.02,
            tier=Tier.T2,
            process_category="scope2",
            gas="co2",
        )
        final_uncertainty = u_res["relative_uncertainty"]

    user = get_current_user()
    req_status = data.get("status")
    if req_status == "Draft":
        initial_status = "Draft"
    else:
        # Maker-Checker (D-04): admin and superuser manual entries are auto-Verified
        initial_status = "Verified" if user and user.role in ["admin", "superuser"] else "Pending"

    # Map amount to steam_ton / cooling_ton if source_type or unit indicates steam or cooling
    steam_ton_val = float(data.get("steam_ton") or data.get("stream_ton", 0) or 0)
    cooling_ton_val = float(data.get("cooling_ton", 0) or 0)
    raw_amt = float(data.get("amount", 0) or 0)
    raw_unit = str(data.get("unit") or "").lower().strip()

    if steam_ton_val == 0 and ("steam" in source_type.lower() or raw_unit in ["ton", "tonne", "mt", "us_ton", "short_ton", "tons"]):
        if raw_amt > 0:
            steam_ton_val = raw_amt

    if cooling_ton_val == 0 and ("cooling" in source_type.lower() or raw_unit in ["cooling_ton", "ton_hour", "ton_cooling"]):
        if raw_amt > 0:
            cooling_ton_val = raw_amt

    emission = Scope2Emission(
        facility_id=data.get("facility_id"),
        year=data.get("year"),
        month=data.get("month"),
        source_type=source_type,
        electricity_kwh=electricity_kwh,
        steam_ton=steam_ton_val,
        heat_mmbtu=heat_mmbtu,
        cooling_ton=cooling_ton_val,
        emission_factor=emission_factor,
        co2e=co2e,
        uncertainty=final_uncertainty,
        location=data.get("location") or data.get("grid_region"),
        grid_region=data.get("grid_region") or data.get("location"),
        activity=data.get("activity"),
        division=data.get("division"),
        field=data.get("field"),
        created_by=user_id,
        status=initial_status,
        approved_by=user.id if initial_status == "Verified" and user else None,
        approved_at=datetime.datetime.now(datetime.timezone.utc) if initial_status == "Verified" else None,
    )

    try:
        db.session.add(emission)
        db.session.flush()
        emission_id_val = emission.id
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create Scope 2 emission: {str(e)}"}), 500

    if user:
        try:
            from utils import log_activity_and_notify
            log_activity_and_notify(
                action="CREATE",
                record_id=str(emission_id_val),
                user=user,
                request=request,
                entity="Scope2Emission",
                details=f"Created Scope 2 emission: {source_type} ({co2e:.2f} tCO2e, Status: {initial_status})",
            )
            from status import PENDING_STATUS_SET
            if initial_status in PENDING_STATUS_SET:
                from models import Notification, User
                admins = User.query.filter_by(role="admin", status="active").all()
                for admin in admins:
                    Notification.create(
                        user_id=admin.id,
                        type="audit",
                        title="New Scope 2 Emission Pending Review",
                        message=f"A new Scope 2 emission record ({source_type}) was submitted by {user.fullName} and is awaiting your approval.",
                    )
                db.session.commit()
        except Exception:
            db.session.rollback()

    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()

    return (
        jsonify(
            {
                "message": "Scope 2 emission created",
                "id": emission_id_val,
                "co2e": co2e,
                "status": initial_status,
                "emissions": {
                    "totalCo2e": co2e,
                    "co2": co2e,
                    "ch4": 0.0,
                    "n2o": 0.0,
                    "uncertainty": final_uncertainty,
                },
                "record": {
                    "id": emission_id_val,
                    "year": emission.year,
                    "month": emission.month,
                    "facility_id": emission.facility_id,
                    "source_type": emission.source_type,
                    "electricity_kwh": electricity_kwh,
                    "heat_mmbtu": heat_mmbtu,
                    "amount": electricity_kwh if source_type == "electricity" else (heat_mmbtu or emission.steam_ton or emission.cooling_ton),
                    "unit": "kWh" if source_type == "electricity" else (data.get("unit") or "MMBtu"),
                    "emission_factor": emission.emission_factor,
                    "co2e": co2e,
                    "uncertainty": final_uncertainty,
                    "location": emission.location or emission.grid_region,
                    "status": emission.status,
                },
                "calculation_method": f"Scope 2 {source_type.replace('_', ' ').title()}",
            }
        ),
        201,
    )


@scope2_bp.route("/<int:emission_id>", methods=["PUT"])
@login_required
def update_scope2_emission(emission_id):
    """Update a Scope 2 emission record"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["auditor", "it_admin", "it_manager", "it"]:
        return jsonify({"error": "Read-only or administrative role cannot modify emission records"}), 403

    emission = db.session.get(Scope2Emission, emission_id)
    if not emission:
        return jsonify({"error": "Emission not found"}), 404

    if not require_facility_access(user, emission.facility_id):
        return jsonify({"error": "Unauthorized: Outside your region"}), 403

    # Enforce creator ownership for standard user role
    if user.role == "user" and emission.created_by is not None and emission.created_by != user.id:
        return jsonify({"error": "Unauthorized: You may only modify records you created"}), 403

    # If non-admin modifies a verified record, reset status to Pending for maker-checker review
    if user.role not in ["admin", "superuser"] and emission.status == "Verified":
        emission.status = "Pending"
        emission.approved_by = None
        emission.approved_at = None

    data = request.get_json() or {}

    # Strip status and co2e from direct client overwrite
    data.pop("status", None)
    data.pop("approved_by", None)
    data.pop("approved_at", None)
    data.pop("co2e", None)

    if "facility_id" in data:
        new_fid = int(data["facility_id"])
        if not require_facility_access(user, new_fid):
            return jsonify({"error": "Unauthorized to reassign to this facility"}), 403
        emission.facility_id = new_fid
    if "year" in data:
        emission.year = int(data["year"])
    if "month" in data:
        emission.month = int(data["month"])
    if "source_type" in data:
        emission.source_type = data["source_type"]

    # Check for recalculation trigger (L9)
    activity_changed = any(
        k in data
        for k in [
            "electricity_kwh",
            "steam_ton",
            "heat_mmbtu",
            "cooling_ton",
            "emission_factor",
        ]
    )
    if "electricity_kwh" in data:
        emission.electricity_kwh = float(data["electricity_kwh"] or 0)
    if "steam_ton" in data:
        emission.steam_ton = float(data["steam_ton"] or 0)
    if "heat_mmbtu" in data:
        emission.heat_mmbtu = float(data["heat_mmbtu"] or 0)
    if "cooling_ton" in data:
        emission.cooling_ton = float(data["cooling_ton"] or 0)
    if "emission_factor" in data:
        emission.emission_factor = float(data["emission_factor"] or 0)

    if activity_changed:
        factor = emission.emission_factor or 0.0
        st = (emission.source_type or "").strip().lower()
        if st in ["electricity"] or "electric" in st:
            emission.co2e = round((emission.electricity_kwh * factor) / 1000.0, 4)
        elif st in ["steam", "indirect_steam"] or "steam" in st:
            # Authoritative thermodynamic indirect steam formula with enthalpy & efficiency
            steam_ton_val = emission.steam_ton if (emission.steam_ton and emission.steam_ton > 0) else 0.0
            is_ton = steam_ton_val > 0
            temp_data = {
                "amount": steam_ton_val if is_ton else emission.heat_mmbtu,
                "unit": "ton" if is_ton else "mmbtu",
                "calc_inputs": data.get("calc_inputs", {}),
            }
            if "indirect_steam" not in temp_data["calc_inputs"]:
                boiler_eff_val = float(data.get("boiler_eff") or data.get("boiler_efficiency") or 0.80)
                trans_loss_val = float(data.get("trans_loss") or 0.0)
                enthalpy_val = float(data.get("steam_enthalpy") or 2.0)
                temp_data["calc_inputs"]["indirect_steam"] = {
                    "boiler_eff": boiler_eff_val,
                    "trans_loss": trans_loss_val,
                    "ef_co2": factor or _DEFAULT_BOILER_EF_KG_PER_MMBTU,
                    "steam_enthalpy": enthalpy_val,
                }
            try:
                co2e_val, heat_mmbtu, _ = _calc_indirect_steam(temp_data)
                emission.co2e = round(co2e_val, 4)
                if heat_mmbtu:
                    emission.heat_mmbtu = round(heat_mmbtu, 4)
            except Exception:
                eff = float(data.get("boiler_eff") or data.get("boiler_efficiency") or 0.80)
                enth = float(data.get("steam_enthalpy") or 2.0)
                mmbtu = (emission.steam_ton * enth) if (emission.steam_ton and emission.steam_ton > 0) else (emission.heat_mmbtu or 0.0)
                ef_kg = (factor * 1000.0) if (0 < factor < 1.0) else factor
                emission.co2e = round((mmbtu * ef_kg) / (eff * 1000.0), 4)
        elif st in ["heat"] or "heat" in st:
            emission.co2e = round((emission.heat_mmbtu * factor) / 1000.0, 4)
        elif st in ["cooling"] or "cool" in st:
            emission.co2e = round((emission.cooling_ton * factor) / 1000.0, 4)

    if "uncertainty" in data:
        emission.uncertainty = float(data["uncertainty"] or 0)
    if "location" in data:
        emission.location = data["location"]
    if "grid_region" in data:
        emission.grid_region = data["grid_region"]

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update Scope 2 emission: {str(e)}"}), 500

    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()

    return jsonify({"message": "Scope 2 emission updated"})


@scope2_bp.route("/<int:emission_id>", methods=["DELETE"])
@login_required
def delete_scope2_emission(emission_id):
    """Delete a Scope 2 emission record"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT personnel do not have access to emission data"}), 403

    if user.role in ["auditor"]:
        return jsonify({"error": "Forbidden: Read-only accounts cannot delete emission records"}), 403

    emission = db.session.get(Scope2Emission, emission_id)
    if not emission:
        return jsonify({"error": "Emission not found"}), 404

    if user.role not in ["admin", "superuser"]:
        if emission.created_by != user.id:
            return (
                jsonify(
                    {"error": "Forbidden: You do not have permission to delete records created by another user"}
                ),
                403,
            )
    else:
        if not require_facility_access(user, emission.facility_id):
            return jsonify({"error": "Unauthorized: Outside your region"}), 403

    log_details = f"Deleted Scope 2 emission: {emission.source_type} ({emission.co2e:.2f} tCO2e, facility #{emission.facility_id})"

    db.session.delete(emission)
    try:
        from utils import log_activity_and_notify
        log_activity_and_notify(
            action="DELETE",
            record_id=str(emission_id),
            user=user,
            request=request,
            entity="Scope2Emission",
            details=log_details,
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete Scope 2 emission: {e}")
        return jsonify({"error": "Failed to delete Scope 2 record"}), 500

    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()

    return jsonify({"message": "Scope 2 emission deleted"})


@scope2_bp.route("/bulk-import", methods=["POST"])
@login_required
def bulk_import_scope2():
    """Import Scope 2 emissions from CSV data"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT personnel do not have access to upload emission data"}), 403

    allowed_fids = get_allowed_facility_ids(user)
    data = request.get_json() or {}
    records = data.get("records", [])
    if not records:
        return jsonify({"error": "No records provided"}), 400

    MAX_SYNCHRONOUS_IMPORT = 2500
    if len(records) > MAX_SYNCHRONOUS_IMPORT:
        return (
            jsonify(
                {
                    "error": f"Payload exceeds maximum synchronous limit of {MAX_SYNCHRONOUS_IMPORT} rows. Please split the batch."
                }
            ),
            413,
        )

    # Per Maker-Checker: admin/superuser imports are Verified, regular user imports are Pending
    bulk_status = "Verified" if user.role in ["admin", "superuser"] else "Pending"
    imported_count = 0
    errors = []
    facility_cache = {}

    for i, rec in enumerate(records):
        try:
            # 1. Resolve facility
            f_val = rec.get("facility_id")
            facility = None
            if isinstance(f_val, str) and not str(f_val).isdigit():
                f_name_clean = f_val.strip()
                if f_name_clean.lower() in facility_cache:
                    facility = facility_cache[f_name_clean.lower()]
                else:
                    facility = Facility.query.filter(
                        func.lower(Facility.name) == f_name_clean.lower()
                    ).first()
                    facility_cache[f_name_clean.lower()] = facility
            else:
                try:
                    fid = int(f_val) if f_val else None
                    if fid in facility_cache:
                        facility = facility_cache[fid]
                    else:
                        facility = db.session.get(Facility, fid)
                        facility_cache[fid] = facility
                except (ValueError, TypeError):
                    facility = None

            if not facility:
                errors.append(f"Row {i}: Facility '{f_val}' not found")
                continue

            if allowed_fids is not None and facility.id not in allowed_fids:
                errors.append(f"Row {i}: Unauthorized for facility '{facility.name}'")
                continue

            # 2. Get Factor and Calculate
            grid_region = rec.get("grid_region")
            factor_info = GRID_FACTORS.get(grid_region)
            if not factor_info:
                errors.append(f"Row {i}: Grid Region '{grid_region}' not found")
                continue

            ef = factor_info["factor"]
            # consumption in payload might be kwh, mwh, gwh. BulkImportModal uses 'consumption' and 'unit'
            val = float(rec.get("consumption") or 0)
            unit = str(rec.get("unit") or "kwh").lower().strip()

            kwh = val
            if unit in ["mwh", "mw-hr", "megawatthour"]:
                kwh = val * 1000.0
            elif unit in ["gwh", "gw-hr", "gigawatthour"]:
                kwh = val * 1_000_000.0
            else:
                kwh = val

            co2e_val = (kwh * ef) / 1000

            # Default Scope 2 uncertainty
            u_res = propagate_uncertainty(
                co2e_val,
                ef_uncertainty=0.05,
                activity_uncertainty=0.02,
                tier=Tier.T2,
                process_category="scope2",
                gas="co2",
            )
            final_uncertainty = u_res["relative_uncertainty"]

            emission = Scope2Emission(
                facility_id=facility.id,
                year=int(rec.get("year", 2024)),
                month=int(rec.get("month", 1)),
                source_type="electricity",
                electricity_kwh=kwh,
                emission_factor=ef,
                co2e=co2e_val,
                uncertainty=final_uncertainty,
                grid_region=grid_region,
                location=grid_region,
                activity=rec.get("activity") or facility.activity,
                division=rec.get("division") or facility.division,
                field=rec.get("field") or facility.field,
                created_by=user.id,
                status=bulk_status,
                approved_by=user.id if bulk_status == "Verified" else None,
                approved_at=datetime.datetime.now(datetime.timezone.utc) if bulk_status == "Verified" else None,
            )
            db.session.add(emission)
            imported_count += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to bulk import Scope 2 emissions: {str(e)}"}), 500

    try:
        log_activity_and_notify(
            "IMPORT",
            str(imported_count),
            f"Bulk imported {imported_count} Scope 2 records",
            user=user,
            request=request,
            entity="Scope2Emission",
        )
        db.session.commit()
    except Exception:
        db.session.rollback()

    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    return jsonify(
        {"message": f"Successfully imported {imported_count} records", "errors": errors}
    ), (200 if not errors else 207)


@scope2_bp.route("/emission-factors", methods=["GET"])
@login_required
def get_emission_factors():
    """Get emission factors by grid region"""
    factors = []
    for region, info in GRID_FACTORS.items():
        factors.append(
            {
                "region": region,
                "factor": info["factor"],
                "unit": info["unit"],
                "description": info["description"],
            }
        )

    return jsonify(factors)
