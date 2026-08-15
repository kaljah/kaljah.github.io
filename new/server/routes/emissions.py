from flask import request, jsonify, session
from sqlalchemy import func
from . import emissions_bp
from utils import get_current_user, get_allowed_facility_ids
from models import (
    User,
    Emission,
    Scope2Emission,
    Scope3Emission,
    Goal,
    Notification,
    CustomFactor,
    Facility,
)
from extensions import db
from utils import log_activity_and_notify
from calculations import (
    compute_emissions,
    calculate_co2e,
)
from emission_factors import API_FACTORS
from routes.auth import login_required
import datetime
import uuid
import json
from sqlalchemy import cast, String, literal, Float, union_all


def get_current_user():
    user_id = session.get("user_id")
    return (
        db.session.get(User, user_id) if user_id else None
    )  # EXTRA-02 FIX: replaced deprecated query.get


def _escape_like(val: str) -> str:
    """NEW-07 FIX: Escape SQL LIKE wildcards in user-supplied search strings."""
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@emissions_bp.route("/", methods=["GET"])
@login_required  # SEC-01 FIX: was missing, route was unauthenticated
def get_emissions():
    from flask import current_app

    user = get_current_user()
    if user:
        current_app.logger.info(f"[Emissions] Fetch requested by user_id: {user.id}")
    else:
        current_app.logger.info("[Emissions] Fetch requested by anonymous user")

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    # Parameters from request
    limit_arg = request.args.get("limit", "50")
    offset_arg = request.args.get("offset", "0")

    # Handle both 'page' and 'limit/offset' pagination
    if "limit" in request.args and "offset" in request.args:
        try:
            per_page = int(limit_arg)
            offset = int(offset_arg)
            page = (offset // per_page) + 1
        except (ValueError, TypeError, ZeroDivisionError):
            per_page = 50
            page = 1
    else:
        page = request.args.get("page", 1, type=int)
        if limit_arg == "all":
            per_page = 5000  # SEC-10 FIX: hard cap — was 1,000,000 (DoS vector)
        else:
            try:
                per_page = int(limit_arg)
            except ValueError:
                per_page = 50

    scope = request.args.get("scope", "all")
    year = request.args.get("year")
    month = request.args.get("month")
    facility_id = request.args.get("facilityId") or request.args.get("facility_id")
    process_type = request.args.get("process") or request.args.get("process_type")
    division_arg = request.args.get("division")
    field_arg = request.args.get("field")
    search_term = request.args.get("search")
    method_arg = request.args.get("method")

    results = []

    # helper to apply common filters
    def apply_filters(q, model, filter_model=None):
        fm = filter_model or model
        allowed_fids = get_allowed_facility_ids(user)
        if allowed_fids is not None:
            if hasattr(model, "facility_id"):
                q = q.filter(model.facility_id.in_(allowed_fids))
            elif model == Facility:
                q = q.filter(Facility.id.in_(allowed_fids))
            else:
                q = q.filter(model.id == -1)  # Restrict fully if unknown model

        nonlocal year
        if year == "baseline":
            from models import BaseYear

            base = BaseYear.query.first()
            year = str(base.year) if base else "2020"

        if year and year != "all":
            try:
                q = q.filter(model.year == int(year))
            except ValueError:
                pass
        if month and month != "all":
            try:
                q = q.filter(model.month == int(month))
            except ValueError:
                pass
        if facility_id and facility_id != "all":
            try:
                q = q.filter(model.facility_id == int(facility_id))
            except ValueError:
                pass
        # NEW-07 FIX: escape LIKE wildcards before filtering
        if division_arg and division_arg != "all":
            q = q.filter(
                fm.division.ilike(
                    f"%{_escape_like(division_arg.strip())}%", escape="\\"
                )
            )
        if field_arg and field_arg != "all":
            q = q.filter(
                fm.field.ilike(f"%{_escape_like(field_arg.strip())}%", escape="\\")
            )

        if method_arg and method_arg != "all":
            if hasattr(model, "calc_method"):
                q = q.filter(
                    model.calc_method.ilike(
                        f"%{_escape_like(method_arg)}%", escape="\\"
                    )
                )
            elif hasattr(model, "calculation_method"):
                q = q.filter(
                    model.calculation_method.ilike(
                        f"%{_escape_like(method_arg)}%", escape="\\"
                    )
                )

        if search_term:
            from sqlalchemy import or_

            safe_term = _escape_like(search_term)
            search_filters = []
            if hasattr(model, "process_type"):
                search_filters.append(
                    model.process_type.ilike(f"%{safe_term}%", escape="\\")
                )
            if hasattr(model, "fuel_type"):
                search_filters.append(
                    model.fuel_type.ilike(f"%{safe_term}%", escape="\\")
                )
            if hasattr(model, "activity"):
                search_filters.append(
                    model.activity.ilike(f"%{safe_term}%", escape="\\")
                )
            if hasattr(model, "group_name"):
                search_filters.append(
                    model.group_name.ilike(f"%{safe_term}%", escape="\\")
                )
            if hasattr(model, "equipment_id"):
                search_filters.append(
                    model.equipment_id.ilike(f"%{safe_term}%", escape="\\")
                )
            if hasattr(model, "division"):
                search_filters.append(
                    model.division.ilike(f"%{safe_term}%", escape="\\")
                )
            if hasattr(model, "field"):
                search_filters.append(model.field.ilike(f"%{safe_term}%", escape="\\"))
            if hasattr(model, "category"):
                search_filters.append(
                    model.category.ilike(f"%{safe_term}%", escape="\\")
                )
            if hasattr(model, "sub_category"):
                search_filters.append(
                    model.sub_category.ilike(f"%{safe_term}%", escape="\\")
                )

            if search_filters:
                q = q.filter(or_(*search_filters))

        return q

    queries = []

    # 1. SCOPE 1
    if scope in ["all", "1", "scope1"]:
        s1_query = apply_filters(Emission.query, Emission)
        if process_type and process_type != "all":
            s1_query = s1_query.filter(Emission.process_type == process_type)

        # Outer join to avoid losing records if facility link is missing
        s1_query = s1_query.outerjoin(Facility, Emission.facility_id == Facility.id)

        sel1 = s1_query.with_entities(
            (literal("s1_") + cast(Emission.id, String)).label("id"),
            literal(1).label("scope"),
            Emission.year.label("year"),
            Emission.month.label("month"),
            Emission.facility_id.label("facility_id"),
            Facility.name.label("facility_name"),  # Joined name
            Emission.group_name.label("group_name"),
            Emission.activity.label("activity"),
            Emission.process_type.label("process_type"),
            Emission.fuel_type.label("fuel"),
            Emission.quantity.label("amount"),
            Emission.unit.label("unit"),
            Emission.co2_emissions.label("co2_emissions"),
            Emission.ch4_emissions.label("ch4_emissions"),
            Emission.n2o_emissions.label("n2o_emissions"),
            Emission.co2e_total.label("co2e_total"),
            Emission.status.label("status"),
            Emission.timestamp.label("timestamp"),
            Emission.division.label("division"),
            Emission.field.label("field"),
            Emission.equipment_id.label("equipment_id"),
            Emission.calc_method.label("factor_type"),
            Facility.region.label("region"),
            Emission.source_payload.label("source_payload"),
            Emission.uncertainty.label("uncertainty_co2"),
            Emission.uncertainty_ch4.label("uncertainty_ch4"),
            Emission.uncertainty_n2o.label("uncertainty_n2o"),
        )
        current_app.logger.info(f"[Emissions] Scope 1 count: {sel1.count()}")
        queries.append(sel1)

    # 2. SCOPE 2
    if scope in ["all", "2", "scope2"]:
        s2_query = apply_filters(Scope2Emission.query, Scope2Emission)

        # Outer join
        s2_query = s2_query.outerjoin(
            Facility, Scope2Emission.facility_id == Facility.id
        )

        sel2 = s2_query.with_entities(
            (literal("s2_") + cast(Scope2Emission.id, String)).label("id"),
            literal(2).label("scope"),
            Scope2Emission.year.label("year"),
            Scope2Emission.month.label("month"),
            Scope2Emission.facility_id.label("facility_id"),
            Facility.name.label("facility_name"),  # Joined name
            literal("N/A").label("group_name"),
            Scope2Emission.activity.label("activity"),
            literal("Scope 2").label("process_type"),
            Scope2Emission.grid_region.label("fuel"),
            Scope2Emission.electricity_kwh.label("amount"),
            literal("kWh").label("unit"),
            cast(literal(0), Float).label("co2_emissions"),
            cast(literal(0), Float).label("ch4_emissions"),
            cast(literal(0), Float).label("n2o_emissions"),
            Scope2Emission.co2e.label("co2e_total"),
            Scope2Emission.status.label("status"),
            Scope2Emission.created_at.label("timestamp"),
            Scope2Emission.division.label("division"),
            Scope2Emission.field.label("field"),
            literal("N/A").label("equipment_id"),
            literal("Location-based").label("factor_type"),
            Facility.region.label("region"),
            literal(None).label("source_payload"),
            cast(literal(None), Float).label("uncertainty_co2"),
            cast(literal(None), Float).label("uncertainty_ch4"),
            cast(literal(None), Float).label("uncertainty_n2o"),
        )
        current_app.logger.info(f"[Emissions] Scope 2 count: {sel2.count()}")
        queries.append(sel2)

    # 3. SCOPE 3
    if scope in ["all", "3", "scope3"]:
        # Outer join
        s3_base_query = Scope3Emission.query.outerjoin(
            Facility, Scope3Emission.facility_id == Facility.id
        )
        s3_query = apply_filters(s3_base_query, Scope3Emission, Facility)

        sel3 = s3_query.with_entities(
            (literal("s3_") + cast(Scope3Emission.id, String)).label("id"),
            literal(3).label("scope"),
            Scope3Emission.year.label("year"),
            Scope3Emission.month.label("month"),
            Scope3Emission.facility_id.label("facility_id"),
            Facility.name.label("facility_name"),  # Joined name
            literal("N/A").label("group_name"),
            literal("Value Chain").label("activity"),
            Scope3Emission.category.label("process_type"),
            Scope3Emission.sub_category.label("fuel"),
            Scope3Emission.activity_data.label("amount"),
            Scope3Emission.unit.label("unit"),
            cast(literal(0), Float).label("co2_emissions"),
            cast(literal(0), Float).label("ch4_emissions"),
            cast(literal(0), Float).label("n2o_emissions"),
            Scope3Emission.co2e.label("co2e_total"),
            Scope3Emission.status.label("status"),
            Scope3Emission.created_at.label("timestamp"),
            Facility.division.label("division"),
            Facility.field.label("field"),
            literal("N/A").label("equipment_id"),
            Scope3Emission.calculation_method.label("factor_type"),
            Facility.region.label("region"),
            literal(None).label("source_payload"),
            cast(literal(None), Float).label("uncertainty_co2"),
            cast(literal(None), Float).label("uncertainty_ch4"),
            cast(literal(None), Float).label("uncertainty_n2o"),
        )
        print(f"[Emissions] Scope 3 count: {sel3.count()}")
        queries.append(sel3)

    # Combine queries
    if len(queries) == 1:
        u = queries[0].subquery()
    else:
        u = union_all(*queries).subquery()

    # Get total count safely with detailed logging
    try:
        total = db.session.query(func.count()).select_from(u).scalar() or 0
    except Exception as count_err:
        current_app.logger.error(f"[Emissions] Count Query failed: {count_err}")
        total = 0

    # Paginate and sort
    stmt = db.session.query(u).order_by(u.c.timestamp.desc().nullslast())

    if limit_arg != "all":
        start = (page - 1) * per_page
        stmt = stmt.offset(start).limit(per_page)

    records = stmt.all()

    # Resolve facility names
    facility_ids = set(r.facility_id for r in records if r.facility_id)
    facilities = (
        {
            f.id: f.name
            for f in Facility.query.filter(Facility.id.in_(facility_ids)).all()
        }
        if facility_ids
        else {}
    )

    paginated_results = []
    for r in records:
        f_name = r.facility_name
        if not f_name or f_name == "Unknown":
            f_name = facilities.get(r.facility_id, "Unknown")

        d = {
            "id": r.id,
            "scope": r.scope,
            "year": r.year,
            "month": r.month,
            "facility_id": r.facility_id,
            "facility_name": f_name,
            "activity": r.activity,
            "process_type": r.process_type,
            "fuel": r.fuel,
            "amount": r.amount,
            "unit": r.unit,
            "co2_emissions": r.co2_emissions,
            "ch4_emissions": r.ch4_emissions,
            "n2o_emissions": r.n2o_emissions,
            "co2e_total": r.co2e_total,
            "status": getattr(r, "status", "Verified"),
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "division": r.division,
            "field": r.field,
            "group_name": r.group_name,
            "equipment_id": r.equipment_id,
            "factor_type": r.factor_type,
            "region": getattr(r, "region", None),
            "uncertainty_co2": getattr(r, "uncertainty_co2", None),
            "uncertainty_ch4": getattr(r, "uncertainty_ch4", None),
            "uncertainty_n2o": getattr(r, "uncertainty_n2o", None),
        }
        if (
            r.scope == 1
            and hasattr(r, "source_payload")
            and getattr(r, "source_payload", None)
        ):
            import json

            try:
                payload = json.loads(r.source_payload)
                d["factor_source"] = payload.get("factor_source")
            except Exception:
                pass
        paginated_results.append(d)

    return jsonify(
        {
            "data": paginated_results,
            "emissions": paginated_results,
            "total": total,
            "pages": (
                (total // per_page) + (1 if total % per_page > 0 else 0)
                if limit_arg != "all"
                else 1
            ),
            "current_page": page,
        }
    )


# Helper: Get GWP based on user prefs and global settings
def resolve_gwp_dict(user=None):
    import json
    from calculations.constants import get_active_gwp

    try:
        prefs = (
            json.loads(user.preferences or "{}") if user and user.preferences else {}
        )
        model = prefs.get("gwp_standard") or prefs.get("gwpModel")
        if model in ["AR4", "AR5", "AR6"]:
            return get_active_gwp(standard=model)
    except Exception:
        pass
    return get_active_gwp()


def resolve_gwp_standard(user=None):
    import json

    try:
        prefs = (
            json.loads(user.preferences or "{}") if user and user.preferences else {}
        )
        model = prefs.get("gwp_standard") or prefs.get("gwpModel")
        if model in ["AR4", "AR5", "AR6"]:
            return model
    except Exception:
        pass
    try:
        from routes.auth import _app_settings

        return _app_settings.get("gwp_standard", "AR5")
    except Exception:
        return "AR5"


@emissions_bp.route("/bulk-upload", methods=["POST"])
@login_required
def add_bulk_upload():
    from datetime import datetime

    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    records = data.get("records", [])
    date_format = data.get("date_format", "YYYY-MM-DD")
    global_factor_type = data.get("global_factor_type", "auto")
    confirm = data.get("confirm", False)

    allowed_facilities = get_allowed_facility_ids(user)

    # Map frontend date format strings to strptime formats
    fmt_map = {
        "YYYY-MM-DD": "%Y-%m-%d",
        "MM/DD/YYYY": "%m/%d/%Y",
        "DD/MM/YYYY": "%d/%m/%Y",
        "YYYY-MM": "%Y-%m",
        "MM/YYYY": "%m/%Y",
        "YYYY": "%Y",
    }
    py_fmt = fmt_map.get(date_format, "%Y-%m-%d")

    # Pre-fetch facilities and custom factors for resolution
    all_facilities = Facility.query.all()
    fac_name_map = {f.name.lower(): f for f in all_facilities}

    # Pre-fetch user's custom factors
    custom_factors = CustomFactor.query.filter_by(created_by=user.id).all()
    cf_name_map = {cf.name.lower(): cf for cf in custom_factors}

    valid_records = []
    errors = []
    duplicates = []
    new_emissions = []

    for idx, row in enumerate(records):
        row_num = idx + 1
        row_errors = []

        # 1. Parse Date
        date_str = row.get("date")
        if date_str:
            try:
                dt = datetime.strptime(str(date_str).strip(), py_fmt)
                year = dt.year
                month = dt.month
            except ValueError:
                row_errors.append(
                    f"Invalid date format: {date_str} does not match {date_format}."
                )
                year, month = None, None
        else:
            year_val = row.get("year")
            month_val = row.get("month")
            if year_val and month_val:
                try:
                    year = int(year_val)
                    month = int(month_val)
                except ValueError:
                    row_errors.append(f"Invalid year/month: {year_val}/{month_val}")
                    year, month = None, None
            else:
                row_errors.append("Missing date or year/month.")
                year, month = None, None

        # 2. Resolve Facility
        fac_name = row.get("facility_name", row.get("facility_id", "")).strip()
        facility = None
        if fac_name:
            # Check ID match first if they provided a number
            if fac_name.isdigit():
                facility = next(
                    (f for f in all_facilities if str(f.id) == fac_name), None
                )
            # If not ID or not found, try name match
            if not facility:
                facility = fac_name_map.get(fac_name.lower())

            if not facility:
                row_errors.append(f"Facility not found: '{fac_name}'")
            elif (
                allowed_facilities is not None and facility.id not in allowed_facilities
            ):
                row_errors.append(
                    f"You do not have permission to add data for facility: '{fac_name}'"
                )
        else:
            row_errors.append("Missing facility.")

        # 3. Handle Quantity/Amount
        amount_raw = row.get("quantity", row.get("amount"))
        try:
            amount = float(amount_raw)
        except (ValueError, TypeError):
            row_errors.append(f"Invalid quantity: {amount_raw}")
            amount = 0

        process_type = row.get("process", row.get("process_type", row.get("type", "")))
        fuel = row.get("fuel", row.get("fuel_type", ""))
        unit = row.get("unit", "")

        if not process_type:
            row_errors.append("Missing process type.")
        if not fuel and process_type not in [
            "Well Completions",
            "Fugitive",
        ]:  # Some processes might not need fuel
            row_errors.append("Missing fuel/activity.")

        # 4. Resolve Factor (Standard vs Custom vs Sparse Engineering)
        factor_type_raw = str(row.get("factor_type", "")).lower()
        if global_factor_type and global_factor_type != "auto":
            factor_type = global_factor_type
        else:
            factor_type = factor_type_raw

        factor_data = {}

        if process_type == "Flaring":
            # Option B: Sparse columns
            try:
                factor_data = {
                    "c1": float(row.get("c1", 0)),
                    "c2": float(row.get("c2", 0)),
                    "c3": float(row.get("c3", 0)),
                    "c4": float(row.get("c4", 0)),
                    "c5": float(row.get("c5", 0)),
                    "c6": float(row.get("c6", 0)),
                    "co2": float(row.get("co2_mol", 0)),
                    "n2": float(row.get("n2_mol", 0)),
                }
            except ValueError:
                row_errors.append("Invalid engineering calculation inputs for Flaring.")
        elif factor_type == "custom":
            cf = cf_name_map.get(fuel.lower())
            if not cf:
                row_errors.append(
                    f"Custom factor not found for fuel: '{fuel}'. Please save it in the app first."
                )
            else:
                factor_data = {
                    "co2": cf.co2_factor,
                    "ch4": cf.ch4_factor,
                    "n2o": cf.n2o_factor,
                    "co": cf.co_factor,
                    "unit": cf.unit,
                    "hhv": cf.hhv_factor,
                    "type": "custom",
                    "name": cf.name,
                }
                if cf.co2_uncertainty or cf.ch4_uncertainty or cf.n2o_uncertainty:
                    factor_data["uncertainty"] = {
                        "co2": float(
                            getattr(cf, "co2_uncertainty", None)
                            or getattr(cf, "uncertainty", 0)
                            or 0
                        )
                        / 100.0,
                        "ch4": float(
                            getattr(cf, "ch4_uncertainty", None)
                            or getattr(cf, "uncertainty", 0)
                            or 0
                        )
                        / 100.0,
                        "n2o": float(
                            getattr(cf, "n2o_uncertainty", None)
                            or getattr(cf, "uncertainty", 0)
                            or 0
                        )
                        / 100.0,
                    }
                elif cf.uncertainty and cf.uncertainty > 0:
                    factor_data["uncertainty"] = {
                        "co2": float(cf.uncertainty or 0) / 100.0,
                        "ch4": float(cf.uncertainty or 0) / 100.0,
                        "n2o": float(cf.uncertainty or 0) / 100.0,
                    }
                elif cf.parent_fuel:
                    parent_factor = API_FACTORS.get(cf.parent_fuel, {})
                    if "uncertainty" in parent_factor:
                        factor_data["uncertainty"] = parent_factor["uncertainty"]
        else:
            factor_data = API_FACTORS.get(fuel, {})
            if (
                not factor_data
                and not row_errors
                and process_type not in ["Well Completions"]
            ):
                row_errors.append(f"Standard emission factor not found for: '{fuel}'")

        # 5. Check if row is clean to compute
        if row_errors:
            errors.append({"row": row_num, "reasons": row_errors, "original": row})
            continue

        # Base calc_data
        calc_data = {
            "year": year,
            "month": month,
            "facility_id": facility.id,
            "process_type": process_type,
            "fuel": fuel,
            "amount": amount,
            "unit": unit,
        }

        # Inject all other optional variables dynamically
        has_specific = False
        specific_keys = {
            "c1",
            "c2",
            "c3",
            "c4",
            "c5",
            "c6",
            "c7",
            "c8",
            "c9",
            "c10",
            "n2_mol",
            "co2_mol",
            "n2",
            "co2_comp",
            "h2s",
            "flare_type",
            "control_efficiency",
            "ch4_content",
            "co2_content",
            "combustion_efficiency",
            "operating_temperature",
            "temp_unit",
            "operating_pressure",
            "press_unit",
            "z_factor",
            "mud_type",
            "mud_unit",
            "comp_method",
            "comp_rate",
            "comp_duration",
            "comp_liquid_bbl",
            "comp_gor",
            "comp_flare_eff",
            "comp_choke_size",
            "comp_whp",
            "gor",
            "flowback_days",
            "unload_depth",
            "unload_diam",
            "unload_press",
            "unload_freq",
            "unload_flare_eff",
            "unload_temp",
            "blowdown_volume",
            "blowdown_pressure",
            "blowdown_events",
            "blowdown_unit",
            "blowdown_temp",
            "blowdown_temp_unit",
            "blowdown_press_unit",
            "blowdown_ch4",
            "tank_gor",
            "tank_press",
            "tank_temp",
            "tank_flare_eff",
            "tank_ch4_content",
            "tank_control_eff",
            "tank_unit",
            "tank_api_gravity",
            "pneumatic_type",
            "pneumatic_count",
            "pneumatic_hours",
            "pneu_count",
            "pneu_bleed_rate",
            "pneu_bleed_unit",
            "pneu_hours",
            "pneu_ch4_content",
            "agr_co2_in",
            "agr_co2_out",
            "agr_ch4_in",
            "agr_unit",
            "agr_ch4_slip",
            "agr_control_eff",
            "dehy_pump_rate",
            "dehy_pump_unit",
            "dehy_hours",
            "dehy_eff",
            "dehy_ch4_content",
            "dehy_press",
            "dehy_press_unit",
            "dehy_temp",
            "dehy_temp_unit",
            "dehy_has_flash",
            "dehy_flash_eff",
            "dehy_still_type",
            "hhv",
            "ef_unit",
            "fuel_type",
            "boiler_eff",
            "trans_loss",
            "heat_unit",
            "total_emissions",
            "heat_output",
            "power_output",
            "allocation_method",
            "carbon_content",
            "molecular_weight",
            "fugitive_method",
            "fugitive_ppm",
        }

        for k, v in row.items():
            if k not in calc_data and v is not None:
                val = str(v).strip()
                if val:  # only include non-empty values
                    calc_data[k] = val
                    if k in specific_keys:
                        has_specific = True

        if has_specific:
            calc_data["factor_source"] = "specific"

        # Ensure factor source is recorded cleanly if forced globally or provided in column
        if factor_type in ["default", "custom", "specific"]:
            calc_data["factor_source"] = factor_type

        # 6. Compute
        gwp_dict = resolve_gwp_dict(user)
        gwp_std = resolve_gwp_standard(user)
        try:
            em_result, method = compute_emissions(
                calc_data, factor_data, gwp_dict=gwp_dict
            )
        except Exception as e:
            errors.append(
                {
                    "row": row_num,
                    "reasons": [f"Calculation failed: {str(e)}"],
                    "original": row,
                }
            )
            continue

        # Fallback GWP CO2e if missing
        if not em_result.get("totalCo2e") or em_result.get("totalCo2e") == 0:
            co2_val = em_result.get("co2", 0)
            ch4_val = em_result.get("ch4", 0)
            n2o_val = em_result.get("n2o", 0)
            em_result["totalCo2e"] = calculate_co2e(
                co2_val, ch4_val, n2o_val, gwp_dict=gwp_dict
            )

        # Uncertainty
        api_res = em_result.get("_full_api_res")
        if api_res:
            uncertainty = {
                "co2": (
                    api_res["results"]["co2"].get("uncertainty")
                    if isinstance(api_res["results"]["co2"], dict)
                    else 0.05
                ),
                "ch4": (
                    api_res["results"]["ch4"].get("uncertainty")
                    if isinstance(api_res["results"]["ch4"], dict)
                    else 0.15
                ),
                "n2o": (
                    api_res["results"]["n2o"].get("uncertainty")
                    if isinstance(api_res["results"]["n2o"], dict)
                    else 0.15
                ),
            }
        else:
            uncertainty = factor_data.get("uncertainty", {})

        # Prepare Record
        rec_id = str(uuid.uuid4())
        emission_obj = Emission(
            record_id=rec_id,
            year=year,
            month=month,
            facility_id=facility.id,
            group_name=row.get("group", ""),
            activity=row.get("activity", facility.activity),
            division=row.get("division", facility.division),
            field=row.get("field", facility.field),
            process_type=process_type,
            fuel_type=fuel,
            quantity=amount,
            unit=unit,
            equipment_id=row.get("equipment", ""),
            co2_emissions=em_result["co2"],
            ch4_emissions=em_result["ch4"],
            n2o_emissions=em_result["n2o"],
            co_emissions=em_result.get("co", 0),
            co2e_total=em_result["totalCo2e"],
            calc_method=method,
            gwp_version=gwp_std,
            source_payload=json.dumps(calc_data),
            created_by=user.id,
            uncertainty=(
                uncertainty.get("co2", None)
                if isinstance(uncertainty, dict)
                else (uncertainty or None)
            ),
            uncertainty_ch4=(
                uncertainty.get("ch4", None)
                if isinstance(uncertainty, dict)
                else (uncertainty or None)
            ),
            uncertainty_n2o=(
                uncertainty.get("n2o", None)
                if isinstance(uncertainty, dict)
                else (uncertainty or None)
            ),
            status="Verified",
        )

        # 7. Check for Duplicates
        duplicate = Emission.query.filter_by(
            year=year,
            month=month,
            facility_id=facility.id,
            process_type=process_type,
            equipment_id=row.get("equipment", ""),
        ).first()

        preview_data = {
            "row": row_num,
            "year": year,
            "month": month,
            "facility": facility.name,
            "process": process_type,
            "fuel": fuel,
            "amount": amount,
            "unit": unit,
            "co2e": round(em_result["totalCo2e"], 2),
        }

        if duplicate:
            duplicates.append(preview_data)
            # If confirm=True and they chose to overwrite, we'd update.
            # For simplicity, if we are confirming and hit a duplicate, we can delete the old one and insert new.
            if confirm:
                db.session.delete(duplicate)
                new_emissions.append(emission_obj)
        else:
            valid_records.append(preview_data)
            if confirm:
                new_emissions.append(emission_obj)

    # 8. Finalize Database changes if confirming
    if confirm:
        if new_emissions:
            db.session.add_all(new_emissions)
            try:
                db.session.commit()
                # Create a single bulk audit log
                log_activity_and_notify(
                    action="CREATE",
                    record_id="bulk",
                    user=user,
                    request=request,
                    entity="Emission",
                    details=f"Bulk imported {len(new_emissions)} emissions via CSV",
                )
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return (
                    jsonify({"error": "Failed to save to database", "details": str(e)}),
                    500,
                )

        return jsonify(
            {"status": "success", "imported": len(new_emissions), "errors": errors}
        )

    # If preview
    return jsonify(
        {
            "status": "preview",
            "valid_count": len(valid_records),
            "valid_records": valid_records,
            "duplicate_count": len(duplicates),
            "duplicates": duplicates,
            "errors": errors,
        }
    )


import os
import tempfile
from flask import send_file, Response
from background_processor import start_background_upload, get_job_status


@emissions_bp.route("/template/csv", methods=["GET"])
def get_csv_template():
    """
    Returns a comprehensive CSV template with all fields needed for
    Tier 1 (default/custom factor) and Tier 3 (specific engineering) calculations
    across all 18 supported process types.
    """
    import csv, io

    tier = request.args.get("tier", "3")
    process = request.args.get("process", "all")

    # -----------------------------------------------------------------------
    # COLUMN DEFINITIONS
    # Format: (header_label, internal_key, tier, description)
    # -----------------------------------------------------------------------
    COLUMNS = [
        # ── REQUIRED CORE FIELDS ─────────────────────────────────────────
        (
            "[Required] date",
            "date",
            "Core",
            "Date as YYYY-MM (e.g. 2024-03). Required.",
        ),
        (
            "[Required] facility_name",
            "facility_name",
            "Core",
            "Exact facility/region name from Manage Data → Regions. Required.",
        ),
        (
            "[Required] process_type",
            "process_type",
            "Core",
            "combustion | flaring | venting | blowdown | pneumatic | tank_flashing | tank_working | tank_breathing | drilling | completions | unloading | agr | dehydrator | fugitive | mobile | indirect_steam | stoichiometry | separation",
        ),
        (
            "[Required] fuel",
            "fuel",
            "Core",
            "Fuel or activity type exactly as in API factors catalog (e.g. Natural Gas, Diesel, Associated Gas). Required for Tier 1.",
        ),
        (
            "[Required] quantity",
            "quantity",
            "Core",
            "Numeric activity quantity (volume, mass, count, etc.). Required.",
        ),
        (
            "[Required] unit",
            "unit",
            "Core",
            "Unit of quantity: m3 | scf | mscf | mmscf | bbl | gal | l | kg | tonne | lb | kWh. Required.",
        ),
        (
            "[Required] factor_type",
            "factor_type",
            "Core",
            "default = API standard factors (Tier 1) | custom = user-saved factor | specific = engineering/Tier 3 calculation",
        ),
        # ── OPTIONAL METADATA ─────────────────────────────────────────────
        (
            "[Optional] activity",
            "activity",
            "Meta",
            "Activity label (e.g. Exploration & Production). Defaults to facility activity if blank.",
        ),
        (
            "[Optional] region",
            "region",
            "Meta",
            "Region label. Defaults to facility region if blank.",
        ),
        (
            "[Optional] division",
            "division",
            "Meta",
            "Division label. Defaults to facility division if blank.",
        ),
        (
            "[Optional] field",
            "field",
            "Meta",
            "Field/sub-unit name. Defaults to facility field if blank.",
        ),
        (
            "[Optional] group",
            "group",
            "Meta",
            "Emission source group (e.g. Compressor Station A). For reporting grouping only.",
        ),
        (
            "[Optional] equipment",
            "equipment",
            "Meta",
            "Equipment tag/ID (e.g. EQ-001). Used for duplicate detection.",
        ),
        (
            "[Optional] equipment_name",
            "equipment_name",
            "Meta",
            "Human-readable equipment name (e.g. Caterpillar G3516).",
        ),
        # ── TIER 1 COMBUSTION ─────────────────────────────────────────────
        (
            "[T1/T3] hhv",
            "hhv",
            "T1",
            "Higher Heating Value in Btu/scf (gas) or Btu/gal (liquid). Defaults from API catalog if blank. e.g. 1020 for Natural Gas.",
        ),
        (
            "[T1] ef_unit",
            "ef_unit",
            "T1",
            "Emission factor unit override. Usually kg/MMBtu or kg/m3. Leave blank to use catalog default.",
        ),
        (
            "[T1] combustion_efficiency",
            "combustion_efficiency",
            "T1",
            "Combustion efficiency 0-1 or 0-100%. Default 0.995 (99.5%). Required for Tier 3 combustion.",
        ),
        (
            "[T1] fuel_type",
            "fuel_type",
            "T1",
            "Broad fuel category: gases | liquids | solids. Needed for unit normalization.",
        ),
        # ── T1/T3 TEMPERATURE & PRESSURE NORMALIZATION (all gas processes) ─
        (
            "[T1/T3] operating_temperature",
            "operating_temperature",
            "T1",
            "Measured gas temperature at operating conditions. Enables API §4.2.1 thermodynamic correction.",
        ),
        (
            "[T1/T3] temp_unit",
            "temp_unit",
            "T1",
            "Temperature unit: C | F | K. Default C.",
        ),
        (
            "[T1/T3] operating_pressure",
            "operating_pressure",
            "T1",
            "Measured gas pressure at operating conditions (gauge or absolute depending on press_unit).",
        ),
        (
            "[T1/T3] press_unit",
            "press_unit",
            "T1",
            "Pressure unit: psig | psia | kPa | barg | bara. Default psig.",
        ),
        (
            "[T1/T3] z_factor",
            "z_factor",
            "T1",
            "Gas compressibility factor Z. Default 1.0 (ideal gas). Use 0.85–0.99 for real gas conditions.",
        ),
        # ── TIER 3 GAS COMPOSITION (combustion, flaring, completions, blowdown, agr) ──
        (
            "[T3] c1",
            "c1",
            "T3-GasComp",
            "Methane (CH4) mole fraction 0–100 mol%. Required for Tier 3 combustion/flaring.",
        ),
        ("[T3] c2", "c2", "T3-GasComp", "Ethane (C2H6) mole fraction 0–100 mol%."),
        ("[T3] c3", "c3", "T3-GasComp", "Propane (C3H8) mole fraction 0–100 mol%."),
        ("[T3] c4", "c4", "T3-GasComp", "Butane (C4H10) mole fraction 0–100 mol%."),
        ("[T3] c5", "c5", "T3-GasComp", "Pentane (C5H12) mole fraction 0–100 mol%."),
        ("[T3] c6", "c6", "T3-GasComp", "Hexane (C6H14) mole fraction 0–100 mol%."),
        ("[T3] c7", "c7", "T3-GasComp", "Heptane (C7H16) mole fraction 0–100 mol%."),
        ("[T3] c8", "c8", "T3-GasComp", "Octane (C8H18) mole fraction 0–100 mol%."),
        ("[T3] c9", "c9", "T3-GasComp", "Nonane (C9H20) mole fraction 0–100 mol%."),
        ("[T3] c10", "c10", "T3-GasComp", "Decane+ (C10+) mole fraction 0–100 mol%."),
        (
            "[T3] n2_mol",
            "n2_mol",
            "T3-GasComp",
            "Nitrogen (N2) mole fraction 0–100 mol%.",
        ),
        (
            "[T3] co2_mol",
            "co2_mol",
            "T3-GasComp",
            "CO2 mole fraction in gas stream 0–100 mol% (distinct from emitted CO2).",
        ),
        # ── T3 FLARING ────────────────────────────────────────────────────
        (
            "[T3-Flare] flare_type",
            "flare_type",
            "T3",
            "Flare design type: elevated | enclosed_ground | offshore_boom | air_assisted | steam_assisted. Default elevated.",
        ),
        (
            "[T3-Flare] ch4_content",
            "ch4_content",
            "T3",
            "Gas stream CH4 content % (0–100). Alias for c1 for flaring/completions/unloading.",
        ),
        (
            "[T3-Flare] co2_content",
            "co2_content",
            "T3",
            "Gas stream CO2 content % (0–100). Used by completions, blowdown, unloading.",
        ),
        (
            "[T3-Flare] control_efficiency",
            "control_efficiency",
            "T3",
            "Flare/control device destruction efficiency 0–100%. Used by flaring, completions, blowdown, unloading, tanks.",
        ),
        # ── T3 DRILLING / MUD DEGASSING ───────────────────────────────────
        (
            "[T3-Drill] mud_type",
            "mud_type",
            "T3",
            "Drilling mud type: water_based | oil_based | synthetic. Default water_based.",
        ),
        (
            "[T3-Drill] mud_unit",
            "mud_unit",
            "T3",
            "Unit of mud volume: m3 | bbl. Defaults to quantity unit if blank.",
        ),
        # ── T3 WELL COMPLETIONS / WORKOVERS ───────────────────────────────
        (
            "[T3-Comp] comp_method",
            "comp_method",
            "T3-Completion",
            "Completions calculation method: metered_volume (default) | rate_duration | gor_liquid.",
        ),
        (
            "[T3-Comp] comp_rate",
            "comp_rate",
            "T3-Completion",
            "Flowback rate (Mscf/day). Required when comp_method=rate_duration.",
        ),
        (
            "[T3-Comp] comp_duration",
            "comp_duration",
            "T3-Completion",
            "Flowback duration (hours). Required when comp_method=rate_duration.",
        ),
        (
            "[T3-Comp] comp_liquid_bbl",
            "comp_liquid_bbl",
            "T3-Completion",
            "Liquid flowback volume (bbl). Required when comp_method=gor_liquid.",
        ),
        (
            "[T3-Comp] comp_gor",
            "comp_gor",
            "T3-Completion",
            "Gas-Oil Ratio scf/bbl. Required when comp_method=gor_liquid.",
        ),
        (
            "[T3-Comp] comp_flare_eff",
            "comp_flare_eff",
            "T3-Completion",
            "Completions flare/combustion control efficiency 0–100%.",
        ),
        (
            "[T3-Comp] comp_choke_size",
            "comp_choke_size",
            "T3-Completion",
            "Choke size in inches (optional, for engineering documentation).",
        ),
        (
            "[T3-Comp] comp_whp",
            "comp_whp",
            "T3-Completion",
            "Wellhead pressure (psia) during completions (optional).",
        ),
        # ── T3 LIQUIDS UNLOADING ──────────────────────────────────────────
        (
            "[T3-Unload] unload_depth",
            "unload_depth",
            "T3",
            "Well depth (ft). REQUIRED for liquids unloading Tier 3.",
        ),
        (
            "[T3-Unload] unload_diam",
            "unload_diam",
            "T3",
            "Casing inner diameter (inches). REQUIRED for liquids unloading Tier 3.",
        ),
        (
            "[T3-Unload] unload_press",
            "unload_press",
            "T3",
            "Shut-in surface pressure (psig). REQUIRED for liquids unloading Tier 3.",
        ),
        (
            "[T3-Unload] unload_freq",
            "unload_freq",
            "T3",
            "Number of unloading events per year. REQUIRED for liquids unloading Tier 3. (quantity can be used if blank)",
        ),
        (
            "[T3-Unload] unload_flare_eff",
            "unload_flare_eff",
            "T3",
            "Unloading vented gas flare efficiency 0–100%.",
        ),
        (
            "[T3-Unload] unload_temp",
            "unload_temp",
            "T3",
            "Well temperature at unloading conditions. Default 60°F.",
        ),
        # ── T3 VENTING / BLOWDOWN ─────────────────────────────────────────
        (
            "[T3-BDN] blowdown_pressure",
            "blowdown_pressure",
            "T3",
            "Vessel/pipeline pressure before blowdown (psig). REQUIRED for blowdown Tier 3.",
        ),
        (
            "[T3-BDN] blowdown_events",
            "blowdown_events",
            "T3",
            "Number of blowdown events per year. REQUIRED for blowdown Tier 3.",
        ),
        (
            "[T3-BDN] blowdown_unit",
            "blowdown_unit",
            "T3",
            "Unit for blowdown volume: m3 | scf | bbl. Defaults to quantity unit if blank.",
        ),
        (
            "[T3-BDN] blowdown_temp",
            "blowdown_temp",
            "T3",
            "Gas temperature in vessel before blowdown. Default 60°F.",
        ),
        (
            "[T3-BDN] blowdown_temp_unit",
            "blowdown_temp_unit",
            "T3",
            "Temperature unit for blowdown: F | C | K. Default F.",
        ),
        (
            "[T3-BDN] blowdown_press_unit",
            "blowdown_press_unit",
            "T3",
            "Pressure unit for blowdown: psig | psia | kPa. Default psig.",
        ),
        # ── T3 STORAGE TANKS ──────────────────────────────────────────────
        (
            "[T3-Tank] tank_gor",
            "tank_gor",
            "T3",
            "Tank flash gas-to-oil ratio (scf/bbl). REQUIRED for storage tank Tier 3.",
        ),
        (
            "[T3-Tank] tank_ch4_content",
            "tank_ch4_content",
            "T3",
            "Tank flash gas CH4 content % (0–100). REQUIRED for storage tank Tier 3.",
        ),
        (
            "[T3-Tank] tank_control_eff",
            "tank_control_eff",
            "T3",
            "Tank vapor control efficiency 0–100%.",
        ),
        (
            "[T3-Tank] tank_unit",
            "tank_unit",
            "T3",
            "Unit of liquid throughput: bbl | m3 | gal | l. Default bbl.",
        ),
        (
            "[T3-Tank] tank_api_gravity",
            "tank_api_gravity",
            "T3",
            "Crude API gravity (degrees). Optional, used for documentation.",
        ),
        # ── T3 PNEUMATIC DEVICES ──────────────────────────────────────────
        (
            "[T3-Pneu] pneu_count",
            "pneu_count",
            "T3",
            "Number of pneumatic devices (controllers/pumps). REQUIRED for pneumatic Tier 3.",
        ),
        (
            "[T3-Pneu] pneu_bleed_rate",
            "pneu_bleed_rate",
            "T3",
            "Measured bleed rate per device (scf/hr or m3/hr). REQUIRED for pneumatic Tier 3.",
        ),
        (
            "[T3-Pneu] pneu_bleed_unit",
            "pneu_bleed_unit",
            "T3",
            "Unit of bleed rate: scf | m3. Default scf.",
        ),
        (
            "[T3-Pneu] pneu_hours",
            "pneu_hours",
            "T3",
            "Annual operating hours per device. REQUIRED for pneumatic Tier 3 (e.g. 8760).",
        ),
        (
            "[T3-Pneu] pneu_ch4_content",
            "pneu_ch4_content",
            "T3",
            "Supply gas CH4 content % (0–100). Default 85%.",
        ),
        # ── T3 ACID GAS REMOVAL (AGR / Amine / Selexol) ──────────────────
        (
            "[T3-AGR] agr_co2_in",
            "agr_co2_in",
            "T3",
            "Inlet CO2 mole % in raw gas. REQUIRED for AGR Tier 3.",
        ),
        (
            "[T3-AGR] agr_co2_out",
            "agr_co2_out",
            "T3",
            "Outlet CO2 mole % after sweetening. REQUIRED for AGR Tier 3.",
        ),
        (
            "[T3-AGR] agr_unit",
            "agr_unit",
            "T3",
            "Unit for AGR gas throughput: mmscf | m3 | scf. Default mmscf.",
        ),
        (
            "[T3-AGR] agr_ch4_in",
            "agr_ch4_in",
            "T3",
            "Inlet CH4 mole fraction or % (0–1 or 0–100). Default 0.85.",
        ),
        (
            "[T3-AGR] agr_ch4_slip",
            "agr_ch4_slip",
            "T3",
            "CH4 slip fraction through solvent (0–1). Default 0.001 (0.1%).",
        ),
        (
            "[T3-AGR] agr_control_eff",
            "agr_control_eff",
            "T3",
            "Acid gas control/destruction efficiency 0–100%. Default 0.",
        ),
        # ── T3 DEHYDRATOR ─────────────────────────────────────────────────
        (
            "[T3-Dehy] dehy_pump_rate",
            "dehy_pump_rate",
            "T3",
            "TEG/glycol circulation rate (gal/hr or liters/hr). Required when no throughput.",
        ),
        (
            "[T3-Dehy] dehy_pump_unit",
            "dehy_pump_unit",
            "T3",
            "Unit for pump rate: gph | lph. Default gph.",
        ),
        (
            "[T3-Dehy] dehy_hours",
            "dehy_hours",
            "T3",
            "Dehydrator annual operating hours. Default 8760.",
        ),
        (
            "[T3-Dehy] dehy_press",
            "dehy_press",
            "T3",
            "Contactor pressure (psig). Default 800.",
        ),
        (
            "[T3-Dehy] dehy_press_unit",
            "dehy_press_unit",
            "T3",
            "Pressure unit for dehydrator: psig | kPa. Default psig.",
        ),
        (
            "[T3-Dehy] dehy_temp",
            "dehy_temp",
            "T3",
            "Contactor temperature (°F). Default 100.",
        ),
        (
            "[T3-Dehy] dehy_temp_unit",
            "dehy_temp_unit",
            "T3",
            "Temperature unit for dehydrator: F | C. Default F.",
        ),
        (
            "[T3-Dehy] dehy_has_flash",
            "dehy_has_flash",
            "T3",
            "Has flash tank? true | false. Default true.",
        ),
        (
            "[T3-Dehy] dehy_flash_eff",
            "dehy_flash_eff",
            "T3",
            "Flash tank vapor recovery efficiency 0–100%. Default 0.",
        ),
        (
            "[T3-Dehy] dehy_still_type",
            "dehy_still_type",
            "T3",
            "Still column type: none | condenser | fired_reboiler. Default none.",
        ),
        (
            "[T3-Dehy] dehy_ch4_content",
            "dehy_ch4_content",
            "T3",
            "Feed gas CH4 content % (0–100). Default 85%.",
        ),
        (
            "[T3-Dehy] dehy_eff",
            "dehy_eff",
            "T3",
            "Overall glycol dehydrator emission control efficiency 0–100%. Default 0.",
        ),
        # ── T3 INDIRECT STEAM / HEAT (Section 8) ─────────────────────────
        (
            "[T3-Steam] boiler_eff",
            "boiler_eff",
            "T3",
            "Boiler thermal efficiency fraction (e.g. 0.80 = 80%). REQUIRED for indirect_steam.",
        ),
        (
            "[T3-Steam] trans_loss",
            "trans_loss",
            "T3",
            "Steam distribution transmission loss fraction 0–1. Default 0.",
        ),
        (
            "[T3-Steam] heat_unit",
            "heat_unit",
            "T3",
            "Heat energy unit: btu | mmbtu | mj | gj | kwh. Default btu.",
        ),
        # ── T3 STOICHIOMETRY (Carbon Mass Balance) ────────────────────────
        (
            "[T3-Stoich] carbon_content",
            "carbon_content",
            "T3",
            "Fuel carbon mass fraction 0–1 (e.g. 0.85 for natural gas). REQUIRED for stoichiometry.",
        ),
        # ── T3 FUGITIVE ───────────────────────────────────────────────────
        (
            "[T3-Fug] fugitive_method",
            "fugitive_method",
            "T3",
            "Fugitive calculation method: average (Tier 1) | screening (OGI/EPA Method 21). Default average.",
        ),
        (
            "[T3-Fug] fugitive_ppm",
            "fugitive_ppm",
            "T3",
            "Leak concentration in ppm. Required when fugitive_method=screening.",
        ),
        # ── UNCERTAINTY OVERRIDES ─────────────────────────────────────────
        (
            "[Unc] meter_uncertainty_pct",
            "meter_uncertainty_pct",
            "Unc",
            "Flow meter measurement uncertainty % (overrides Tier default). e.g. 2.5",
        ),
        (
            "[Unc] gc_uncertainty_pct",
            "gc_uncertainty_pct",
            "Unc",
            "Gas chromatograph composition uncertainty %. e.g. 1.0",
        ),
        (
            "[Unc] user_unc_co2",
            "user_unc_co2",
            "Unc",
            "Custom CO2 emission factor uncertainty % override.",
        ),
        (
            "[Unc] user_unc_ch4",
            "user_unc_ch4",
            "Unc",
            "Custom CH4 emission factor uncertainty % override.",
        ),
        (
            "[Unc] user_unc_n2o",
            "user_unc_n2o",
            "Unc",
            "Custom N2O emission factor uncertainty % override.",
        ),
    ]

    filtered_columns = []

    # Process grouping maps
    p_comp = ["all", "combustion", "flaring", "completions", "blowdown", "agr"]
    p_flare = [
        "all",
        "flaring",
        "completions",
        "unloading",
        "blowdown",
        "tank_flashing",
        "tank_working",
        "tank_breathing",
    ]
    p_drill = ["all", "drilling"]
    p_completion = ["all", "completions"]
    p_unload = ["all", "unloading"]
    p_bdn = ["all", "venting", "blowdown"]
    p_tank = ["all", "tank_flashing", "tank_working", "tank_breathing"]
    p_pneu = ["all", "pneumatic"]
    p_agr = ["all", "agr"]
    p_dehy = ["all", "dehydrator"]
    p_steam = ["all", "indirect_steam"]
    p_stoich = ["all", "stoichiometry", "combustion"]
    p_fug = ["all", "fugitive"]

    for c in COLUMNS:
        t = c[2]
        header = c[0]
        if t in ["Core", "Meta"]:
            filtered_columns.append(c)
        elif tier == "3":
            if t == "Unc":
                filtered_columns.append(c)
            elif t == "T1":
                filtered_columns.append(c)
            elif header.startswith("[T3] ") and process in p_comp:
                filtered_columns.append(c)
            elif header.startswith("[T3-Flare]") and process in p_flare:
                filtered_columns.append(c)
            elif header.startswith("[T3-Drill]") and process in p_drill:
                filtered_columns.append(c)
            elif header.startswith("[T3-Comp]") and process in p_completion:
                filtered_columns.append(c)
            elif header.startswith("[T3-Unload]") and process in p_unload:
                filtered_columns.append(c)
            elif header.startswith("[T3-BDN]") and process in p_bdn:
                filtered_columns.append(c)
            elif header.startswith("[T3-Tank]") and process in p_tank:
                filtered_columns.append(c)
            elif header.startswith("[T3-Pneu]") and process in p_pneu:
                filtered_columns.append(c)
            elif header.startswith("[T3-AGR]") and process in p_agr:
                filtered_columns.append(c)
            elif header.startswith("[T3-Dehy]") and process in p_dehy:
                filtered_columns.append(c)
            elif header.startswith("[T3-Steam]") and process in p_steam:
                filtered_columns.append(c)
            elif header.startswith("[T3-Stoich]") and process in p_stoich:
                filtered_columns.append(c)
            elif header.startswith("[T3-Fug]") and process in p_fug:
                filtered_columns.append(c)
        elif tier == "1":
            if t == "T1":
                filtered_columns.append(c)

    # Use filtered_columns instead of COLUMNS for mapping
    COLUMNS = filtered_columns

    headers = [c[0] for c in COLUMNS]
    descriptions = [c[3] for c in COLUMNS]

    # -----------------------------------------------------------------------
    # SAMPLE ROWS — one per major process type
    # -----------------------------------------------------------------------
    def _row(**kw):
        """Build a row dict keyed by column header labels, filling blanks with '-'."""
        inv = {c[0]: c[1] for c in COLUMNS}  # header → internal_key
        fwd = {c[1]: c[0] for c in COLUMNS}  # internal_key → header
        result = {h: "-" for h in headers}
        for k, v in kw.items():
            hdr = fwd.get(k, k)  # allow passing either internal key or header
            if hdr in result:
                result[hdr] = str(v)
        return [result[h] for h in headers]

    sample_rows = [
        # 1. Tier 1 – Natural Gas Combustion
        _row(
            date="2024-01",
            facility_name="Hassi Messaoud Gas Plant",
            process_type="combustion",
            fuel="Natural Gas",
            quantity="50000",
            unit="scf",
            factor_type="default",
            group="Compressor Station A",
            equipment="EQ-001",
            equipment_name="CAT G3516 Generator",
            activity="Upstream & Midstream Gas",
            region="Ouargla",
            division="Production",
            field="Hassi Messaoud",
            hhv="1020",
            combustion_efficiency="0.995",
            fuel_type="gases",
        ),
        # 2. Tier 3 – Combustion (Gas Composition Carbon Mass Balance)
        _row(
            date="2024-01",
            facility_name="Hassi Messaoud Gas Plant",
            process_type="combustion",
            fuel="Natural Gas",
            quantity="50000",
            unit="scf",
            factor_type="specific",
            group="Compressor Station B",
            equipment="EQ-002",
            activity="Upstream & Midstream Gas",
            region="Ouargla",
            division="Production",
            field="Hassi Messaoud",
            hhv="1010",
            combustion_efficiency="0.993",
            c1="87.5",
            c2="5.2",
            c3="2.1",
            c4="1.0",
            c5="0.5",
            co2_mol="1.8",
            n2_mol="1.9",
            operating_temperature="45",
            temp_unit="C",
            operating_pressure="300",
            press_unit="psig",
            z_factor="0.92",
        ),
        # 3. Tier 1 – Diesel Combustion
        _row(
            date="2024-01",
            facility_name="Hassi Messaoud Gas Plant",
            process_type="combustion",
            fuel="Diesel (No. 2 Fuel Oil)",
            quantity="1200",
            unit="gal",
            factor_type="default",
            group="Diesel Generators",
            equipment="EQ-003",
            activity="Upstream & Midstream Gas",
            region="Ouargla",
            division="Production",
            field="Hassi Messaoud",
            fuel_type="liquids",
            hhv="138700",
        ),
        # 4. Tier 3 – Flaring (Engineering Mode)
        _row(
            date="2024-01",
            facility_name="Hassi R'Mel Hub",
            process_type="flaring",
            fuel="Associated Gas",
            quantity="120000",
            unit="scf",
            factor_type="specific",
            group="HP Flare Stack",
            equipment="EQ-010",
            c1="83",
            c2="6",
            c3="3",
            c4="2",
            c5="1",
            co2_mol="2",
            n2_mol="3",
            flare_type="elevated",
            control_efficiency="98",
            operating_temperature="60",
            temp_unit="F",
            operating_pressure="150",
            press_unit="psig",
            z_factor="0.95",
        ),
        # 5. Tier 1 – Flaring (Default Factor)
        _row(
            date="2024-01",
            facility_name="Hassi R'Mel Hub",
            process_type="flaring",
            fuel="Associated Gas",
            quantity="80000",
            unit="scf",
            factor_type="default",
            group="LP Flare",
            equipment="EQ-011",
        ),
        # 6. Tier 3 – Drilling (Mud Degassing)
        _row(
            date="2024-01",
            facility_name="Hassi Messaoud Gas Plant",
            process_type="drilling",
            fuel="Drilling Operations",
            quantity="500",
            unit="m3",
            factor_type="specific",
            group="Well HMD-47",
            equipment="EQ-020",
            mud_type="water_based",
            mud_unit="m3",
        ),
        # 7. Tier 3 – Well Completions (Metered Volume)
        _row(
            date="2024-01",
            facility_name="Hassi Messaoud Gas Plant",
            process_type="completions",
            fuel="Associated Gas",
            quantity="25000",
            unit="scf",
            factor_type="specific",
            group="Well HMD-55 Completion",
            equipment="EQ-030",
            comp_method="metered_volume",
            ch4_content="82",
            co2_content="3",
            comp_flare_eff="90",
        ),
        # 8. Tier 3 – Well Completions (Rate × Duration)
        _row(
            date="2024-01",
            facility_name="Hassi Messaoud Gas Plant",
            process_type="completions",
            fuel="Associated Gas",
            quantity="-",
            unit="scf",
            factor_type="specific",
            group="Well HMD-56 Workover",
            equipment="EQ-031",
            comp_method="rate_duration",
            comp_rate="50",
            comp_duration="72",
            ch4_content="84",
            co2_content="2",
            comp_flare_eff="85",
        ),
        # 9. Tier 3 – Liquids Unloading
        _row(
            date="2024-01",
            facility_name="Hassi Messaoud Gas Plant",
            process_type="unloading",
            fuel="Natural Gas",
            quantity="12",
            unit="events",
            factor_type="specific",
            group="Well HMD-22",
            equipment="EQ-040",
            unload_depth="8500",
            unload_diam="4.5",
            unload_press="800",
            unload_freq="12",
            unload_flare_eff="0",
            ch4_content="87",
            co2_content="1.5",
            unload_temp="75",
            temp_unit="F",
        ),
        # 10. Tier 3 – Venting / Blowdown
        _row(
            date="2024-01",
            facility_name="Rhourde Nouss Gas Plant",
            process_type="blowdown",
            fuel="Natural Gas (Venting/Blowdown)",
            quantity="200",
            unit="m3",
            factor_type="specific",
            group="Separator S-101",
            equipment="EQ-050",
            blowdown_pressure="450",
            blowdown_events="8",
            ch4_content="85",
            co2_content="2",
            control_efficiency="0",
            blowdown_temp="65",
            blowdown_temp_unit="F",
            blowdown_press_unit="psig",
            z_factor="0.93",
        ),
        # 11. Tier 3 – Storage Tanks (Flashing)
        _row(
            date="2024-01",
            facility_name="Rhourde Nouss Gas Plant",
            process_type="tank_flashing",
            fuel="Condensate",
            quantity="5000",
            unit="bbl",
            factor_type="specific",
            group="Condensate Storage TK-201",
            equipment="EQ-060",
            tank_gor="85",
            tank_ch4_content="65",
            tank_control_eff="95",
            tank_unit="bbl",
            tank_api_gravity="62",
        ),
        # 12. Tier 3 – Pneumatic Devices
        _row(
            date="2024-01",
            facility_name="Hassi R'Mel Hub",
            process_type="pneumatic",
            fuel="Natural Gas",
            quantity="25",
            unit="devices",
            factor_type="specific",
            group="High-Bleed Controllers",
            equipment="EQ-070",
            pneu_count="25",
            pneu_bleed_rate="6.0",
            pneu_bleed_unit="scf",
            pneu_hours="8760",
            pneu_ch4_content="85",
        ),
        # 13. Tier 3 – AGR (Amine / CO2 Removal)
        _row(
            date="2024-01",
            facility_name="In Salah CCS Plant",
            process_type="agr",
            fuel="Natural Gas",
            quantity="15",
            unit="mmscf",
            factor_type="specific",
            group="Amine Unit K-301",
            equipment="EQ-080",
            agr_co2_in="8.5",
            agr_co2_out="0.5",
            agr_unit="mmscf",
            agr_ch4_in="85",
            agr_ch4_slip="0.1",
            agr_control_eff="0",
        ),
        # 14. Tier 3 – Dehydrator (TEG)
        _row(
            date="2024-01",
            facility_name="Hassi R'Mel Hub",
            process_type="dehydrator",
            fuel="Natural Gas",
            quantity="100",
            unit="mmscf",
            factor_type="specific",
            group="TEG Dehydrator D-401",
            equipment="EQ-090",
            dehy_pump_rate="5.0",
            dehy_pump_unit="gph",
            dehy_hours="8760",
            dehy_press="800",
            dehy_press_unit="psig",
            dehy_temp="100",
            dehy_temp_unit="F",
            dehy_has_flash="true",
            dehy_flash_eff="90",
            dehy_still_type="none",
            dehy_ch4_content="87",
            dehy_eff="0",
        ),
        # 15. Tier 3 – Fugitive (Screening / OGI)
        _row(
            date="2024-01",
            facility_name="Hassi Messaoud Gas Plant",
            process_type="fugitive",
            fuel="Natural Gas",
            quantity="350",
            unit="components",
            factor_type="specific",
            group="Wellhead Valve Leaks",
            equipment="EQ-100",
            fugitive_method="screening",
            fugitive_ppm="12500",
        ),
        # 16. Tier 1 – Fugitive (Average Factor)
        _row(
            date="2024-01",
            facility_name="Hassi Messaoud Gas Plant",
            process_type="fugitive",
            fuel="Natural Gas",
            quantity="350",
            unit="components",
            factor_type="default",
            group="Valve Packings",
            equipment="EQ-101",
        ),
        # 17. Tier 3 – Indirect Steam (Section 8)
        _row(
            date="2024-01",
            facility_name="Hassi R'Mel Hub",
            process_type="indirect_steam",
            fuel="Natural Gas",
            quantity="500000000",
            unit="btu",
            factor_type="specific",
            group="Central Boiler House",
            equipment="EQ-110",
            boiler_eff="0.82",
            trans_loss="0.05",
            heat_unit="btu",
        ),
        # 18. Tier 3 – Stoichiometry (Carbon Mass Balance)
        _row(
            date="2024-01",
            facility_name="Hassi Messaoud Gas Plant",
            process_type="stoichiometry",
            fuel="Natural Gas",
            quantity="45000",
            unit="kg",
            factor_type="specific",
            group="Process Furnace F-501",
            equipment="EQ-120",
            carbon_content="0.748",
        ),
    ]

    # Filter sample rows based on requested process and tier
    filtered_rows = []
    for row in sample_rows:
        # Assuming index 2 is 'process_type' (since it is the 3rd column in COLUMNS)
        # We can find the process_type from the dictionary mapping if we constructed it dynamically,
        # but since _row returns a list matched to headers, we need to extract process_type value.
        process_type_idx = headers.index("[Required] process_type")
        factor_type_idx = headers.index("[Required] factor_type")

        row_process = row[process_type_idx]
        row_factor = row[factor_type_idx]

        # Check process match
        process_match = (process == "all") or (row_process == process)

        # Check tier match
        tier_match = True
        if tier == "1":
            tier_match = row_factor == "default"
        elif tier == "3":
            # Tier 3 can include both specific and default for demonstration, but let's keep all if tier 3,
            # or just specific. Let's say if tier == 3, we show 'specific' mostly.
            tier_match = row_factor == "specific"

        if process_match and tier_match:
            filtered_rows.append(row)

    # If filtered_rows is empty (e.g. asking for Tier 1 of a process that only has Tier 3 samples),
    # just show whatever is available for that process.
    if not filtered_rows and process != "all":
        for row in sample_rows:
            if row[headers.index("[Required] process_type")] == process:
                filtered_rows.append(row)

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(headers)
    cw.writerow(descriptions)
    for row in filtered_rows:
        cw.writerow(row)

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=scope1_emissions_template.csv"
        },
    )


@emissions_bp.route("/template/excel", methods=["GET"])
def get_excel_template():
    tier = request.args.get("tier", "all")
    process = request.args.get("process", "all")

    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.comments import Comment
    from openpyxl.utils import get_column_letter
    import openpyxl.utils

    wb = openpyxl.Workbook()

    # ─── Colour palette (Modern Green Environmental Theme) ───
    GREEN_DARK = "1B5E20"  # dark forest green – headers
    GREEN_MID = "2E7D32"  # medium green – sub-headers / Tier-3 sheet headers
    GREEN_LIGHT = "C8E6C9"  # pale green – alternating data rows
    WHITE = "FFFFFF"
    GREY_LIGHT = "F5F5F5"
    YELLOW_HINT = "FFFDE7"  # required-field highlight
    BLUE_HINT = "E3F2FD"  # info / reference cells
    ORANGE_WARN = "FF6F00"  # warning accent

    def hdr_style(cell, bg=GREEN_DARK, fg=WHITE, sz=11, bold=True, wrap=True):
        cell.font = Font(bold=bold, color=fg, size=sz, name="Calibri")
        cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=wrap
        )

    def sub_hdr(cell, bg=GREEN_MID):
        hdr_style(cell, bg=bg, fg=WHITE, sz=10, bold=True)

    def info_cell(cell, bg=BLUE_HINT, fg="1A237E"):
        cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        cell.font = Font(color=fg, size=10, name="Calibri")
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    def req_cell(cell, bg=YELLOW_HINT):
        cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        cell.font = Font(color="B71C1C", size=10, bold=True, name="Calibri")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    thin = Side(style="thin", color="BDBDBD")
    thick = Side(style="medium", color=GREEN_DARK)
    std_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    thick_border = Border(left=thick, right=thick, top=thick, bottom=thick)

    def add_comment(cell, text, author="GHG Platform"):
        c = Comment(text, author)
        c.width = 300
        c.height = 120
        cell.comment = c

    # ═══════════════════════════════════════════════════════════
    # SHEET 1: INSTRUCTIONS
    # ═══════════════════════════════════════════════════════════
    ws_inst = wb.active
    ws_inst.title = "📋 Instructions"
    ws_inst.sheet_view.showGridLines = False

    # Title banner
    ws_inst.merge_cells("A1:H1")
    t = ws_inst["A1"]
    t.value = "GHG Emissions Data Entry Template – User Guide"
    t.font = Font(bold=True, size=16, color=WHITE, name="Calibri")
    t.fill = PatternFill(
        start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid"
    )
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws_inst.row_dimensions[1].height = 40

    ws_inst.merge_cells("A2:H2")
    sub = ws_inst["A2"]
    sub.value = (
        "API Compendium 2021 – Scope 1 Direct Emissions – Monthly Reporting Template"
    )
    sub.font = Font(bold=False, size=11, color=WHITE, name="Calibri", italic=True)
    sub.fill = PatternFill(
        start_color=GREEN_MID, end_color=GREEN_MID, fill_type="solid"
    )
    sub.alignment = Alignment(horizontal="center", vertical="center")
    ws_inst.row_dimensions[2].height = 22

    # Section: Quick Start
    ws_inst.merge_cells("A4:H4")
    sec = ws_inst["A4"]
    sec.value = "🚀  QUICK START"
    hdr_style(sec, bg=GREEN_MID, sz=12)
    ws_inst.row_dimensions[4].height = 28

    steps = [
        (
            "Step 1",
            "Fill in the '🏢 Facilities' sheet with your facility and equipment names. These will drive the dropdowns in the data sheet.",
        ),
        (
            "Step 2",
            "Go to the '📊 Data Entry' sheet. Each row = one piece of equipment for one calendar month.",
        ),
        (
            "Step 3",
            "Use the dropdowns in columns C (Process Type), D (Factor Type), and M (Unit) to select valid values.",
        ),
        (
            "Step 4",
            "For Tier 3 (Engineering) calculations, fill in the matching process tab (e.g. '⚙ Combustion', '⚙ Flaring').",
        ),
        (
            "Step 5",
            "Save the file and upload it using the 'Upload' button in the GHG Platform application.",
        ),
    ]
    for r, (s, d) in enumerate(steps, 5):
        ws_inst[f"A{r}"].value = s
        ws_inst[f"A{r}"].font = Font(
            bold=True, color=GREEN_DARK, name="Calibri", size=10
        )
        ws_inst[f"A{r}"].alignment = Alignment(vertical="top")
        ws_inst.merge_cells(f"B{r}:H{r}")
        ws_inst[f"B{r}"].value = d
        ws_inst[f"B{r}"].font = Font(name="Calibri", size=10)
        ws_inst[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws_inst.row_dimensions[r].height = 28

    # Section: Column Reference
    ws_inst.merge_cells(f"A{len(steps)+6}:H{len(steps)+6}")
    sec2 = ws_inst[f"A{len(steps)+6}"]
    sec2.value = "📑  DATA ENTRY COLUMN REFERENCE"
    hdr_style(sec2, bg=GREEN_MID, sz=12)
    ws_inst.row_dimensions[len(steps) + 6].height = 28

    col_ref = [
        (
            "A",
            "Date (YYYY-MM)",
            "Required",
            "Year and month: e.g. 2024-01 for January 2024. Must be in YYYY-MM format.",
        ),
        (
            "B",
            "Activity",
            "Required",
            "Business activity/segment: e.g. 'Exploration & Production', 'Midstream', 'Downstream'.",
        ),
        (
            "C",
            "Division",
            "Required",
            "Organizational unit/division: e.g. 'Production', 'Association'.",
        ),
        (
            "D",
            "Field",
            "Optional",
            "Field or project name: e.g. 'Hassi Messaoud', 'South Field'.",
        ),
        (
            "E",
            "Region / Facility",
            "Required",
            "Name of the facility as registered in the GHG Platform. Must match exactly.",
        ),
        (
            "F",
            "Emission Source (Group)",
            "Optional",
            "Functional grouping for the emission source (e.g. 'Compressor Station A').",
        ),
        (
            "G",
            "Equipment Name",
            "Required",
            "Descriptive name of the equipment (e.g. 'Caterpillar G3516 Engine #3').",
        ),
        (
            "H",
            "Equipment ID",
            "Optional",
            "Asset tag or unique ID (e.g. 'EQ-0042'). Used for deduplication checks.",
        ),
        (
            "I",
            "Process Type",
            "Required",
            "Select from dropdown. Options: Combustion, Flaring, Venting, Pneumatic Devices, etc.",
        ),
        (
            "J",
            "Activity / Fuel",
            "Required",
            "Fuel or gas type consumed/emitted. Must match supported factors (e.g. 'Natural Gas', 'Diesel').",
        ),
        (
            "K",
            "Factor Type",
            "Required",
            "Select 'default' (API Compendium factor) or 'custom' (user-defined factor saved in platform).",
        ),
        (
            "L",
            "Quantity",
            "Required",
            "Numeric value of the activity data for the month (volume, mass, or count).",
        ),
        (
            "M",
            "Unit",
            "Required",
            "Unit of the quantity. Must match the selected fuel factor unit (e.g. scf for gas, gal for liquid).",
        ),
    ]
    r_start = len(steps) + 7
    # Header row
    for c, (col, name, req, desc) in enumerate(col_ref, 0):
        ws_inst[f"A{r_start+c}"].value = col
        ws_inst[f"A{r_start+c}"].font = Font(
            bold=True, color=WHITE, name="Calibri", size=10
        )
        ws_inst[f"A{r_start+c}"].fill = PatternFill(
            start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid"
        )
        ws_inst[f"A{r_start+c}"].alignment = Alignment(
            horizontal="center", vertical="center"
        )
        ws_inst[f"B{r_start+c}"].value = name
        ws_inst[f"B{r_start+c}"].font = Font(bold=True, name="Calibri", size=10)
        req_color = "B71C1C" if req == "Required" else "37474F"
        ws_inst[f"C{r_start+c}"].value = req
        ws_inst[f"C{r_start+c}"].font = Font(
            color=req_color, bold=True, name="Calibri", size=10
        )
        ws_inst[f"C{r_start+c}"].alignment = Alignment(horizontal="center")
        ws_inst.merge_cells(f"D{r_start+c}:H{r_start+c}")
        ws_inst[f"D{r_start+c}"].value = desc
        ws_inst[f"D{r_start+c}"].font = Font(name="Calibri", size=10)
        ws_inst[f"D{r_start+c}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws_inst.row_dimensions[r_start + c].height = 30

    ws_inst.column_dimensions["A"].width = 8
    ws_inst.column_dimensions["B"].width = 30
    ws_inst.column_dimensions["C"].width = 12
    for c in "DEFGH":
        ws_inst.column_dimensions[c].width = 22

    # ═══════════════════════════════════════════════════════════
    # SHEET 2: FACILITIES REFERENCE
    # ═══════════════════════════════════════════════════════════
    ws_fac = wb.create_sheet("🏢 Facilities")
    ws_fac.sheet_view.showGridLines = False

    ws_fac.merge_cells("A1:E1")
    fac_title = ws_fac["A1"]
    fac_title.value = "Facility & Equipment Reference  ← Fill this sheet first"
    fac_title.font = Font(bold=True, size=13, color=WHITE, name="Calibri")
    fac_title.fill = PatternFill(
        start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid"
    )
    fac_title.alignment = Alignment(horizontal="center", vertical="center")
    ws_fac.row_dimensions[1].height = 35

    fac_cols = ["Facility Name", "Activity / Segment", "Division", "Field", "Notes"]
    for i, h in enumerate(fac_cols, 1):
        c = ws_fac.cell(row=2, column=i, value=h)
        hdr_style(c, bg=GREEN_MID)
        ws_fac.column_dimensions[get_column_letter(i)].width = 30

    sample_facs = [
        (
            "Field Alpha Processing Plant",
            "Exploration & Production",
            "Production",
            "Hassi Messaoud",
            "Main separation facility",
        ),
        (
            "Hassi R'mel Gas Hub",
            "Exploration & Production",
            "Production",
            "Hassi R'mel",
            "Gas injection + compression",
        ),
        (
            "South Field Compressor Stn",
            "Exploration & Production",
            "Production",
            "South Field",
            "4x Cat G3516 engines",
        ),
    ]
    for r, row in enumerate(sample_facs, 3):
        for c, val in enumerate(row, 1):
            cell = ws_fac.cell(row=r, column=c, value=val)
            cell.font = Font(name="Calibri", size=10, italic=True, color="546E7A")
            cell.fill = PatternFill(
                start_color=GREY_LIGHT, end_color=GREY_LIGHT, fill_type="solid"
            )
            cell.border = std_border
        ws_fac.row_dimensions[r].height = 20

    # Leave 97 blank editable rows
    for r in range(6, 103):
        for c in range(1, 6):
            cell = ws_fac.cell(row=r, column=c)
            cell.border = std_border
            cell.fill = PatternFill(
                start_color=WHITE, end_color=WHITE, fill_type="solid"
            )
        ws_fac.row_dimensions[r].height = 18

    ws_fac.freeze_panes = "A3"

    # Named range for facility names (col A rows 3–102) → used for dropdown in Data sheet
    # (openpyxl doesn't support dynamic named ranges well; we define a fixed range)
    wb.create_named_range("FacilityList", ws_fac, "$A$3:$A$102")

    # ═══════════════════════════════════════════════════════════
    # SHEET 3: MAIN DATA ENTRY
    # ═══════════════════════════════════════════════════════════
    ws_data = wb.create_sheet("📊 Data Entry")
    ws_data.sheet_view.showGridLines = False

    DATA_COLS = [
        # (header, width, required)
        ("Date\n(YYYY-MM)", 14, True),
        ("Activity", 22, True),
        ("Region", 20, True),
        ("Division", 20, True),
        ("Field", 20, False),
        ("Facility Name", 28, True),
        ("Emission Source\n(Group)", 24, False),
        ("Equipment Name", 28, True),
        ("Equipment ID", 18, False),
        ("Process Type", 24, True),
        ("Activity / Fuel", 24, True),
        ("Factor Type", 16, True),
        ("Quantity", 14, True),
        ("Unit", 14, True),
        ("Notes / Comments", 30, False),
    ]

    # Freeze pane A2
    ws_data.freeze_panes = "A2"

    # Row 1 – Title banner
    ws_data.merge_cells(f"A1:{get_column_letter(len(DATA_COLS))}1")
    banner = ws_data["A1"]
    banner.value = "📊  GHG Emissions – Monthly Data Entry   |   One row = One equipment × One month   |   Columns in RED are required"
    banner.font = Font(bold=True, size=11, color=WHITE, name="Calibri")
    banner.fill = PatternFill(
        start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid"
    )
    banner.alignment = Alignment(horizontal="center", vertical="center")
    ws_data.row_dimensions[1].height = 30

    # Row 2 – Column headers
    for i, (col_name, col_w, req) in enumerate(DATA_COLS, 1):
        cell = ws_data.cell(row=2, column=i, value=col_name)
        bg = GREEN_MID if not req else "1B5E20"
        hdr_style(cell, bg=bg, sz=10)
        ws_data.column_dimensions[get_column_letter(i)].width = col_w
        ws_data.row_dimensions[2].height = 36

        # Header comments
        hints = {
            1: "Format: YYYY-MM e.g. 2024-01",
            5: "Must exactly match a name from the 🏢 Facilities sheet",
            9: "Select from list: Combustion, Flaring, Venting, etc.",
            10: "Gas/fuel type e.g. Natural Gas, Diesel, Associated Gas",
            11: "default = API Compendium standard factor | specific = factor for specific setup | custom = your saved factor",
            12: "Numeric quantity for the month (e.g. 50000)",
            13: "e.g. scf, m3, gal, bbl, kg, tonne",
        }
        if i in hints:
            add_comment(cell, hints[i])

    # Data Validations

    dv_process = DataValidation(
        type="list",
        formula1='"Combustion,Flaring,Fugitive Emissions,Venting,Well Completions & Workovers,Liquids Unloading,Dehydrator,Pneumatic Device,Storage Tank - Flashing,Storage Tank - Working Losses,Storage Tank - Breathing,Drilling Operations,Acid Gas Removal (AGR),Mobile Combustion,Loading Losses,Wastewater / Separation"',
        allow_blank=True,
        showInputMessage=True,
        promptTitle="Process Type",
        prompt="Select the emission process type.",
        showErrorMessage=True,
        errorTitle="Invalid Value",
        error="Please select a value from the dropdown list.",
    )
    ws_data.add_data_validation(dv_process)
    dv_process.sqref = "I3:I1048576"

    dv_factor = DataValidation(
        type="list",
        formula1='"default,custom"',
        allow_blank=True,
        showInputMessage=True,
        promptTitle="Factor Type",
        prompt="'default' = API Compendium 2021 standard factor.\n'custom' = factor saved in your GHG Platform account.",
        showErrorMessage=True,
        errorTitle="Invalid Value",
        error="Please select 'default' or 'custom'.",
    )
    ws_data.add_data_validation(dv_factor)
    dv_factor.sqref = "K3:K1048576"

    dv_unit = DataValidation(
        type="list",
        formula1='"scf,Mscf,MMscf,m3,gal,bbl,kg,tonne,tonnes/yr,kWh,MWh,km,miles,hours"',
        allow_blank=True,
        showInputMessage=True,
        promptTitle="Unit",
        prompt="Select the unit that matches your quantity and fuel type.",
        showErrorMessage=False,  # allow custom units too
    )
    ws_data.add_data_validation(dv_unit)
    dv_unit.sqref = "M3:M1048576"

    dv_date = DataValidation(
        type="textLength",
        operator="greaterThanOrEqual",
        formula1="7",
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Date Format",
        error="Please enter a date in YYYY-MM format (e.g. 2024-01).",
    )
    ws_data.add_data_validation(dv_date)
    dv_date.sqref = "A3:A1048576"

    dv_qty = DataValidation(
        type="decimal",
        operator="greaterThanOrEqual",
        formula1="0",
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Invalid Quantity",
        error="Quantity must be a non-negative number.",
    )
    ws_data.add_data_validation(dv_qty)
    dv_qty.sqref = "L3:L1048576"

    # ── Sample data rows ──
    samples = [
        [
            "2024-01",
            "Exploration & Production",
            "Ouargla",
            "Production",
            "Hassi Messaoud",
            "Field Alpha Processing Plant",
            "Compressor Station A",
            "Caterpillar G3516 #1",
            "EQ-001",
            "Combustion",
            "Natural Gas",
            "default",
            50000,
            "scf",
            "Tier 1 – standard factor",
        ],
        [
            "2024-01",
            "Exploration & Production",
            "Ouargla",
            "Production",
            "Hassi Messaoud",
            "Field Alpha Processing Plant",
            "Flare Stack",
            "HP Flare Stack - West",
            "EQ-002",
            "Flaring",
            "Associated Gas",
            "default",
            120000,
            "scf",
            "Tier 3 – see Flaring sheet",
        ],
        [
            "2024-01",
            "Exploration & Production",
            "Ouargla",
            "Production",
            "Hassi Messaoud",
            "Field Alpha Processing Plant",
            "Production Separator",
            "3-Phase Separator #2",
            "EQ-003",
            "Venting",
            "Natural Gas (Venting/Blowdown)",
            "default",
            8000,
            "m3",
            "Venting from separator depressuring",
        ],
        [
            "2024-01",
            "Exploration & Production",
            "Ouargla",
            "Production",
            "Hassi Messaoud",
            "Field Alpha Processing Plant",
            "Storage",
            "Crude Oil Storage Tank #5",
            "EQ-004",
            "Storage Tank - Flashing",
            "Tank - Flash Emissions (Gas Well)",
            "default",
            9500,
            "bbl",
            "Monthly oil throughput",
        ],
        [
            "2024-01",
            "Exploration & Production",
            "South",
            "Production",
            "South Field",
            "South Field Compressor Stn",
            "Pneumatics",
            "Control Valve Bank A",
            "EQ-005",
            "Pneumatic Device",
            "Pneumatic High-Bleed Device",
            "default",
            12,
            "units",
            "Count of high-bleed controllers",
        ],
    ]

    filtered_samples = []
    for s in samples:
        row_process = s[9]  # Index 9 is 'Process Type' now (was 8)
        if process == "all" or process.lower() == row_process.lower().replace(" ", "_"):
            filtered_samples.append(s)

    # Simple direct string match, wait 'Storage Tank - Flashing' to 'tank_flashing' is complex.
    # Better to just use a custom mapping for the samples:
    sample_process_map = {
        0: "combustion",
        1: "flaring",
        2: "venting",
        3: "tank_flashing",
        4: "pneumatic",
    }

    filtered_samples = []
    for i, s in enumerate(samples):
        if process == "all" or sample_process_map.get(i) == process:
            filtered_samples.append(s)

    if not filtered_samples:
        filtered_samples = samples  # fallback if no match

    for r, row in enumerate(filtered_samples, 3):
        for c, val in enumerate(row, 1):
            cell = ws_data.cell(row=r, column=c, value=val)
            cell.border = std_border
            cell.font = Font(name="Calibri", size=10, italic=True, color="37474F")
            bg = GREEN_LIGHT if r % 2 == 1 else WHITE
            cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
            cell.alignment = Alignment(vertical="center", wrap_text=False)
        ws_data.row_dimensions[r].height = 18

    # Empty rows with alternating shading and borders
    for r in range(8, 2003):
        for c in range(1, len(DATA_COLS) + 1):
            cell = ws_data.cell(row=r, column=c)
            cell.border = std_border
            bg = GREEN_LIGHT if r % 2 == 0 else WHITE
            cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        ws_data.row_dimensions[r].height = 18

    # ═══════════════════════════════════════════════════════════
    # SHEET 4+: TIER 3 ENGINEERING SHEETS (one per process)
    # ═══════════════════════════════════════════════════════════
    if tier != "1":
        p_comp = ["all", "combustion", "flaring", "completions", "blowdown", "agr"]
        p_flare = [
            "all",
            "flaring",
            "completions",
            "unloading",
            "blowdown",
            "tank_flashing",
            "tank_working",
            "tank_breathing",
        ]
        p_completion = ["all", "completions", "unloading"]
        p_bdn = ["all", "venting", "blowdown"]
        p_tank = ["all", "tank_flashing", "tank_working", "tank_breathing"]
        p_pneu = ["all", "pneumatic"]
        p_agr = ["all", "agr"]
        p_dehy = ["all", "dehydrator"]
        p_fug = ["all", "fugitive"]

        base_cols = [
            ("Equipment ID", 18, "Link to Equipment ID in Data Entry sheet"),
            ("Date (YYYY-MM)", 14, "Must match the date in Data Entry sheet"),
            ("Process Type", 18, "Optional Reference"),
            ("User Uncertainty CO2 (%)", 22, "Optional: Override CO2 Uncertainty"),
            ("User Uncertainty CH4 (%)", 22, "Optional: Override CH4 Uncertainty"),
            ("User Uncertainty N2O (%)", 22, "Optional: Override N2O Uncertainty"),
        ]

        t3_params = [
            ("C1 (mol %)", 14, "Methane (CH4) fraction", p_comp),
            ("C2 (mol %)", 14, "Ethane fraction", p_comp),
            ("C3 (mol %)", 14, "Propane fraction", p_comp),
            ("C4 (mol %)", 14, "Butane fraction", p_comp),
            ("C5 (mol %)", 14, "Pentane fraction", p_comp),
            ("C6 (mol %)", 14, "Hexane fraction", p_comp),
            ("C7 (mol %)", 14, "Heptane fraction", p_comp),
            ("C8 (mol %)", 14, "Octane fraction", p_comp),
            ("C9 (mol %)", 14, "Nonane fraction", p_comp),
            ("C10 (mol %)", 14, "Decane+ fraction", p_comp),
            ("N2 (mol %)", 14, "Nitrogen fraction", p_comp),
            ("Flare Type", 18, "e.g., elevated, enclosed_ground", p_flare),
            ("Flare Control Efficiency (%)", 22, "Combustion efficiency (%)", p_flare),
            ("Tank GOR", 14, "Gas-to-Oil Ratio (scf/bbl)", p_tank),
            ("Pneumatic Count", 16, "Number of identical devices", p_pneu),
            ("Bleed Rate (scf/hr)", 20, "Bleed rate per device", p_pneu),
            ("Hours", 10, "Hours of operation in month", p_pneu),
            ("Well Depth (ft)", 16, "Depth of the well", p_completion),
            ("Diameter (in)", 14, "Casing or tubing diameter", p_completion),
            ("Pressure (psi)", 16, "Surface or bottom-hole pressure", p_completion),
            ("Events", 10, "Number of unloading/completion events", p_completion),
            ("Blowdown Volume (Mscf)", 22, "Total volume of gas blown down", p_bdn),
            ("Fugitive Method", 18, "Component count or leak survey method", p_fug),
            ("PPM", 10, "Leak concentration in PPM", p_fug),
            ("Dehydrator Throughput (Mscf/day)", 28, "Monthly gas throughput", p_dehy),
            ("Dehy CH4 (%)", 16, "Methane slip from Dehy", p_dehy),
            ("AGR Throughput (Mscf/day)", 24, "Monthly gas feed rate to AGR", p_agr),
            ("CO2 In (%)", 14, "CO2 in feed", p_agr),
            ("CO2 Out (%)", 14, "CO2 in sweet gas", p_agr),
        ]

        filtered_cols = [c for c in base_cols]
        for col_def in t3_params:
            if process in col_def[3]:
                filtered_cols.append((col_def[0], col_def[1], col_def[2]))

        TIER3_SHEETS = {
            "⚙ Tier 3 Calculations": {
                "desc": "Engineering parameters for Tier 3 calculations and Gas Composition data.",
                "cols": filtered_cols,
            }
        }

        for sheet_name, cfg in TIER3_SHEETS.items():
            ws_t3 = wb.create_sheet(sheet_name)
            ws_t3.sheet_view.showGridLines = False
            ws_t3.freeze_panes = "A3"

            col_count = len(cfg["cols"])
            ws_t3.merge_cells(f"A1:{get_column_letter(col_count)}1")
            t3_title = ws_t3["A1"]
            t3_title.value = (
                f"{sheet_name.replace('⚙ ', '')} – Tier 3 Engineering Parameters"
            )
            t3_title.font = Font(bold=True, size=13, color=WHITE, name="Calibri")
            t3_title.fill = PatternFill(
                start_color=GREEN_MID, end_color=GREEN_MID, fill_type="solid"
            )
            t3_title.alignment = Alignment(horizontal="center", vertical="center")
            ws_t3.row_dimensions[1].height = 35

            ws_t3.merge_cells(f"A2:{get_column_letter(col_count)}2")
            desc_c = ws_t3["A2"]
            desc_c.value = cfg["desc"]
            desc_c.font = Font(italic=True, size=10, color="37474F", name="Calibri")
            desc_c.fill = PatternFill(
                start_color=GREEN_LIGHT, end_color=GREEN_LIGHT, fill_type="solid"
            )
            desc_c.alignment = Alignment(horizontal="center", vertical="center")
            ws_t3.row_dimensions[2].height = 22

            for i, (col_name, col_w, col_hint) in enumerate(cfg["cols"], 1):
                cell = ws_t3.cell(row=3, column=i, value=col_name)
                hdr_style(cell, bg=GREEN_DARK, sz=10)
                ws_t3.column_dimensions[get_column_letter(i)].width = col_w
                ws_t3.row_dimensions[3].height = 32
                add_comment(cell, col_hint)

            # Define samples for Tier 3
            t3_samples = [
                (
                    "EQ-002",
                    "2024-01",
                    "Flaring",
                    "flaring",
                    {
                        "Flare Type": "elevated",
                        "Flare Control Efficiency (%)": "98",
                        "C1 (mol %)": "83",
                        "C2 (mol %)": "6",
                    },
                ),
                (
                    "EQ-030",
                    "2024-01",
                    "Well Completions & Workovers",
                    "completions",
                    {"Well Depth (ft)": "8500", "Events": "1"},
                ),
                (
                    "EQ-040",
                    "2024-01",
                    "Liquids Unloading",
                    "unloading",
                    {
                        "Well Depth (ft)": "8500",
                        "Diameter (in)": "4.5",
                        "Pressure (psi)": "800",
                        "Events": "12",
                    },
                ),
                (
                    "EQ-050",
                    "2024-01",
                    "Venting",
                    "venting",
                    {"Blowdown Volume (Mscf)": "200"},
                ),
                (
                    "EQ-060",
                    "2024-01",
                    "Storage Tank - Flashing",
                    "tank_flashing",
                    {"Tank GOR": "85"},
                ),
                (
                    "EQ-070",
                    "2024-01",
                    "Pneumatic Device",
                    "pneumatic",
                    {
                        "Pneumatic Count": "25",
                        "Bleed Rate (scf/hr)": "6.0",
                        "Hours": "8760",
                    },
                ),
                (
                    "EQ-080",
                    "2024-01",
                    "Acid Gas Removal (AGR)",
                    "agr",
                    {
                        "AGR Throughput (Mscf/day)": "15",
                        "CO2 In (%)": "8.5",
                        "CO2 Out (%)": "0.5",
                    },
                ),
                (
                    "EQ-090",
                    "2024-01",
                    "Dehydrator",
                    "dehydrator",
                    {"Dehydrator Throughput (Mscf/day)": "100", "Dehy CH4 (%)": "87"},
                ),
                (
                    "EQ-100",
                    "2024-01",
                    "Fugitive Emissions",
                    "fugitive",
                    {"Fugitive Method": "screening", "PPM": "12500"},
                ),
                (
                    "EQ-110",
                    "2024-01",
                    "Stationary Combustion",
                    "combustion",
                    {"C1 (mol %)": "87.5", "C2 (mol %)": "5.2", "C3 (mol %)": "2.1"},
                ),
            ]

            filtered_t3_samples = []
            for s in t3_samples:
                if process == "all" or s[3] == process:
                    filtered_t3_samples.append(s)

            row_idx = 4
            for s in filtered_t3_samples:
                # Map s[4] dict to columns
                row_data = {
                    "Equipment ID": s[0],
                    "Date (YYYY-MM)": s[1],
                    "Process Type": s[2],
                    **s[4],
                }

                for c_idx, (col_name, _, _) in enumerate(cfg["cols"], 1):
                    val = row_data.get(col_name, "")
                    cell = ws_t3.cell(row=row_idx, column=c_idx, value=val)
                    cell.border = std_border
                    cell.font = Font(
                        name="Calibri", size=10, italic=True, color="37474F"
                    )
                    bg = GREEN_LIGHT if row_idx % 2 == 1 else WHITE
                    cell.fill = PatternFill(
                        start_color=bg, end_color=bg, fill_type="solid"
                    )
                    cell.alignment = Alignment(vertical="center", wrap_text=False)
                ws_t3.row_dimensions[row_idx].height = 18
                row_idx += 1

            # Empty data rows
            for r in range(row_idx, 1004):
                for c in range(1, col_count + 1):
                    cell = ws_t3.cell(row=r, column=c)
                    cell.border = std_border
                    bg = GREEN_LIGHT if r % 2 == 0 else WHITE
                    cell.fill = PatternFill(
                        start_color=bg, end_color=bg, fill_type="solid"
                    )
                ws_t3.row_dimensions[r].height = 18

    # ─── Save ──────────────────────────────────────────────────
    # Ensure exactly 3 sheets as requested (remove instructions)
    if "📋 Instructions" in wb.sheetnames:
        del wb["📋 Instructions"]

    fd, path = tempfile.mkstemp(suffix=".xlsx")
    with os.fdopen(fd, "w"):
        pass
    wb.save(path)
    return send_file(
        path,
        as_attachment=True,
        download_name="GHG_Emissions_Template_v2.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@emissions_bp.route("/upload/start", methods=["POST"])
@login_required
def upload_start():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    global_factor_type = request.form.get("global_factor_type", "auto")
    mapping_str = request.form.get("column_mapping")
    scope = request.form.get("scope", "1")
    overwrite_duplicates = request.form.get("overwrite_duplicates") == "true"

    import json

    provided_mapping = None
    if mapping_str:
        try:
            provided_mapping = json.loads(mapping_str)
        except json.JSONDecodeError:
            pass

    fd, path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
    file.save(path)

    from flask import current_app

    job_id = start_background_upload(
        current_app._get_current_object(),
        path,
        file.filename,
        user.id,
        global_factor_type,
        provided_mapping=provided_mapping,
        scope=scope,
        overwrite_duplicates=overwrite_duplicates,
    )

    return jsonify({"job_id": job_id})


@emissions_bp.route("/upload/status/<job_id>", methods=["GET"])
@login_required
def upload_status(job_id):
    status = get_job_status(job_id)
    if not status:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(status)


@emissions_bp.route("/upload/errors/<job_id>", methods=["GET"])
@login_required
def upload_errors(job_id):
    status = get_job_status(job_id)
    if not status or not status.get("error_csv_path"):
        return jsonify({"error": "No errors file found"}), 404
    path = status["error_csv_path"]
    return send_file(
        path,
        as_attachment=True,
        download_name=f"errors_{job_id}.csv",
        mimetype="text/csv",
    )


@emissions_bp.route("/", methods=["POST"])
@login_required
def add_emission():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    # Validation
    required = ["year", "month", "facility_id", "process_type"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 422

    allowed_ids = get_allowed_facility_ids(user)
    if allowed_ids is not None and int(data["facility_id"]) not in allowed_ids:
        return jsonify({"error": "Unauthorized for this facility"}), 403

    # Calculate Emissions
    # We need to fetch factor data if not specific
    # For now, using a simplified factor data placeholder or letting calculate handle it
    # In a real scenario, we'd query the factor database here.
    # Passing empty factor_data relies on hardcoded defaults in calculations.py if any

    # Fetch real factor data from Constants based on fuel_type
    factor_data = API_FACTORS.get(data.get("fuel"), {})

    # Custom Factor Override
    custom_factor_id = data.get("custom_factor_id")
    if custom_factor_id:
        cf = CustomFactor.query.get(custom_factor_id)
        if cf:
            # Map CustomFactor to factor_data structure
            # API_FACTORS usually has: { 'co2': val, 'ch4': val, 'n2o': val, 'unit': '...', 'hhv': ... }
            factor_data = {
                "co2": cf.co2_factor,
                "ch4": cf.ch4_factor,
                "n2o": cf.n2o_factor,
                "co": cf.co_factor,
                "unit": cf.unit,
                "hhv": cf.hhv_factor,
                "type": "custom",  # Helper to know source
                "name": cf.name,
            }

            # Uncertainty Handling
            if cf.co2_uncertainty or cf.ch4_uncertainty or cf.n2o_uncertainty:
                factor_data["uncertainty"] = {
                    "co2": float(
                        getattr(cf, "co2_uncertainty", None)
                        or getattr(cf, "uncertainty", 0)
                        or 0
                    )
                    / 100.0,
                    "ch4": float(
                        getattr(cf, "ch4_uncertainty", None)
                        or getattr(cf, "uncertainty", 0)
                        or 0
                    )
                    / 100.0,
                    "n2o": float(
                        getattr(cf, "n2o_uncertainty", None)
                        or getattr(cf, "uncertainty", 0)
                        or 0
                    )
                    / 100.0,
                }
            elif cf.uncertainty and cf.uncertainty > 0:
                # Use saved custom uncertainty
                factor_data["uncertainty"] = {
                    "co2": cf.uncertainty,
                    "ch4": cf.uncertainty,
                    "n2o": cf.uncertainty,
                }
            elif cf.parent_fuel:
                # Fallback to parent fuel uncertainty
                parent_factor = API_FACTORS.get(cf.parent_fuel, {})
                if "uncertainty" in parent_factor:
                    factor_data["uncertainty"] = parent_factor["uncertainty"]

    # Call compute_emissions to calculate the actual emissions
    gwp_dict = resolve_gwp_dict(user)
    gwp_std = resolve_gwp_standard(user)
    try:
        em_result, method = compute_emissions(data, factor_data, gwp_dict=gwp_dict)
    except ValueError as e:
        # Extract missing field name from error message
        import re

        match = re.search(r"Missing required field: (\w+)", str(e))
        field = match.group(1) if match else "unknown"
        return jsonify({"error": "Missing required field", "field": field}), 422

    # Fallback: Calculate totalCo2e if it's missing or zero
    if not em_result.get("totalCo2e") or em_result.get("totalCo2e") == 0:
        co2_val = em_result.get("co2", 0)
        ch4_val = em_result.get("ch4", 0)
        n2o_val = em_result.get("n2o", 0)
        em_result["totalCo2e"] = calculate_co2e(
            co2_val, ch4_val, n2o_val, gwp_dict=gwp_dict
        )

    # Extract uncertainty from rich API result if available, otherwise fallback to factor data
    api_res = em_result.get("_full_api_res")
    if api_res:
        # Use uncertainties calculated by the new engine, or None if not provided
        uncertainty = {
            "co2": (
                api_res["results"]["co2"].get("uncertainty", None)
                if isinstance(api_res["results"]["co2"], dict)
                else None
            ),
            "ch4": (
                api_res["results"]["ch4"].get("uncertainty", None)
                if isinstance(api_res["results"]["ch4"], dict)
                else None
            ),
            "n2o": (
                api_res["results"]["n2o"].get("uncertainty", None)
                if isinstance(api_res["results"]["n2o"], dict)
                else None
            ),
        }
    else:
        uncertainty = factor_data.get("uncertainty", {})

    # NOTE: user_uncertainty is now handled inside dispatcher.py and propagated via SRSS

    record = Emission(
        record_id=str(uuid.uuid4()),
        year=data["year"],
        month=data["month"],
        facility_id=data["facility_id"],
        group_name=data.get("group_name"),
        activity=data.get("activity"),
        division=data.get("division"),
        field=data.get("field"),
        process_type=data["process_type"],
        fuel_type=data.get("fuel"),
        quantity=data.get("amount"),
        unit=data.get("unit"),
        equipment_id=data.get("equipment_id"),
        co2_emissions=em_result["co2"],
        ch4_emissions=em_result["ch4"],
        n2o_emissions=em_result["n2o"],
        co_emissions=em_result.get("co", 0),
        co2e_total=em_result["totalCo2e"],
        calc_method=method,
        gwp_version=gwp_std,
        source_payload=json.dumps(data),
        created_by=user.id,
        uncertainty=(
            uncertainty.get("co2", None)
            if isinstance(uncertainty, dict)
            else (uncertainty or None)
        ),
        uncertainty_ch4=(
            uncertainty.get("ch4", None)
            if isinstance(uncertainty, dict)
            else (uncertainty or None)
        ),
        uncertainty_n2o=(
            uncertainty.get("n2o", None)
            if isinstance(uncertainty, dict)
            else (uncertainty or None)
        ),
        status=data.get("status", "Verified"),
    )

    db.session.add(record)
    db.session.flush()

    # --- Audit Log ---
    try:
        # Fetch facility name for better description
        facility = Facility.query.get(data["facility_id"])
        facility_name = facility.name if facility else "Unknown"

        log_details = f"Added {record.process_type} emission: {record.quantity} {record.unit} of {record.fuel_type} for {facility_name} ({record.month}/{record.year})"
        log_activity_and_notify(
            action="CREATE",
            record_id=str(record.id),
            user=user,
            request=request,
            entity="Emission",
            details=log_details,
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Audit Log Error: {e}")
        # Not raising here to not block notifications, but we committed atomically if no error

    # --- Notification Logic: Check Goal ---
    try:
        # Check user preference first
        prefs = json.loads(user.preferences or "{}")
        if prefs.get("notifTargets", True):  # Default to True
            current_year = data.get("year")
            if current_year:
                # Get Total Emissions for Year
                total_emissions = (
                    db.session.query(func.sum(Emission.co2e_total))
                    .filter(Emission.year == current_year)
                    .scalar()
                    or 0
                )

                # Get Goal
                goal = Goal.query.get(current_year)

                if goal and goal.target_amount > 0:
                    percent = total_emissions / goal.target_amount

                    title = None
                    msg = None
                    n_type = None

                    if percent >= 1.0:
                        title = f"Goal Exceeded for {current_year}"
                        msg = f"Emissions ({total_emissions:.1f}t) have exceeded the goal of {goal.target_amount}t."
                        n_type = "critical"
                    elif percent >= 0.8:
                        title = f"Goal Warning for {current_year}"
                        msg = f"You have reached {percent*100:.0f}% of your emission goal ({total_emissions:.1f} / {goal.target_amount}t)."
                        n_type = "warning"

                    if title:
                        # EXTRA-08 FIX: Deduplicate — only create a new notification if
                        # an unread notification of the same type and year doesn't exist.
                        from datetime import timedelta

                        cutoff = datetime.datetime.utcnow() - timedelta(hours=24)
                        existing = Notification.query.filter(
                            Notification.user_id == user.id,
                            Notification.type == n_type,
                            Notification.title == title,
                            Notification.is_read == False,
                            Notification.created_at >= cutoff,
                        ).first()
                        if not existing:
                            Notification.create(
                                title=title, message=msg, type=n_type, user_id=user.id
                            )
    except Exception as e:
        from flask import current_app

        current_app.logger.warning(f"Notification check error: {e}")

    # Return emission result with uncertainty
    return (
        jsonify(
            {
                "message": "Record added",
                "id": record.id,
                "emissions": {
                    "co2": em_result["co2"],
                    "ch4": em_result["ch4"],
                    "n2o": em_result["n2o"],
                    "totalCo2e": em_result["totalCo2e"],
                    "uncertainty": uncertainty,
                },
                "record": {
                    "process_type": data["process_type"],
                    # BUG-04 FIX: safe facility name lookup
                    "facility_name": (
                        Facility.query.get(data["facility_id"]).name
                        if data.get("facility_id")
                        and Facility.query.get(data["facility_id"])
                        else "Unknown"
                    ),
                    "month": data["month"],
                    "year": data["year"],
                    "fuel": data.get("fuel"),
                    "amount": data.get("amount"),
                    "unit": data.get("unit"),
                },
                "calculation_method": method,
            }
        ),
        201,
    )


@emissions_bp.route("/<id>", methods=["DELETE"])
@login_required  # SEC-01 FIX: was missing
def delete_emission(id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    record = Emission.query.filter_by(record_id=id).first() or db.session.get(
        Emission, int(id) if str(id).isdigit() else -1
    )
    if not record:
        return jsonify({"error": "Record not found"}), 404
    # SEC-03 FIX: IDOR — enforce ownership; admins may delete any record, users can delete own records
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and record.facility_id not in allowed_fids:
        if record.created_by != user.id:
            return jsonify({"error": "Forbidden: Outside your region"}), 403

    # BUG-05 FIX: capture audit data before deletion, then commit everything atomically
    log_details = f"Deleted {record.process_type} record: {record.quantity} {record.unit} of {record.fuel_type} ({record.month}/{record.year})"

    db.session.delete(record)

    try:
        log_activity_and_notify(
            action="DELETE",
            record_id=str(id),
            user=user,
            request=request,
            entity="Emission",
            details=log_details,
        )
        db.session.commit()  # single atomic commit for delete + audit
    except Exception as e:
        db.session.rollback()
        raise e

    return jsonify({"message": "Record deleted"})


@emissions_bp.route("/<id>", methods=["PUT"])
@login_required  # EXTRA-06 FIX: decorator was present but get_current_user() could return None causing 500
def update_emission(id):
    user = get_current_user()
    data = request.get_json()  # EXTRA-03 FIX: removed duplicate call below
    record = Emission.query.filter_by(record_id=id).first() or db.session.get(
        Emission, int(id) if str(id).isdigit() else -1
    )  # EXTRA-02 FIX

    if not record:
        return jsonify({"error": "Not found"}), 404
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and record.facility_id not in allowed_fids:
        return jsonify({"error": "Unauthorized: Outside your region"}), 403
        # EXTRA-03 FIX: removed second data = request.get_json() (double-read, second returns None)

    # Update fields
    if "year" in data:
        record.year = data["year"]
    if "month" in data:
        record.month = data["month"]
    if "facility_id" in data:
        new_fid = int(data["facility_id"])
        if allowed_fids is not None and new_fid not in allowed_fids:
            return jsonify({"error": "Unauthorized to reassign to this facility"}), 403
        record.facility_id = new_fid
    if "process_type" in data:
        record.process_type = data["process_type"]
    if "fuel_type" in data:
        record.fuel_type = data["fuel_type"]
    if "quantity" in data:
        record.quantity = data["quantity"]
    if "unit" in data:
        record.unit = data["unit"]
    if "status" in data:
        record.status = data["status"]

    # Only recalculate emissions if explicitly requested
    if data.get("recalculate"):
        # BUG-18 FIX: initialize factor_data before the custom factor block
        factor_data = API_FACTORS.get(data.get("fuel") or data.get("fuel_type"), {})
        # Handle Custom Factor in update
        cf_id = data.get("custom_factor_id")
        if cf_id:
            cf = CustomFactor.query.get(cf_id)
            if cf:
                factor_data = {
                    "co2": cf.co2_factor,
                    "ch4": cf.ch4_factor,
                    "n2o": cf.n2o_factor,
                    "co": cf.co_factor,
                    "unit": cf.unit,
                    "hhv": cf.hhv_factor,
                    "type": "custom",
                    "name": cf.name,
                }
                # Uncertainty Handle (Update)
                if cf.co2_uncertainty or cf.ch4_uncertainty or cf.n2o_uncertainty:
                    factor_data["uncertainty"] = {
                        "co2": float(
                            getattr(cf, "co2_uncertainty", None)
                            or getattr(cf, "uncertainty", 0)
                            or 0
                        )
                        / 100.0,
                        "ch4": float(
                            getattr(cf, "ch4_uncertainty", None)
                            or getattr(cf, "uncertainty", 0)
                            or 0
                        )
                        / 100.0,
                        "n2o": float(
                            getattr(cf, "n2o_uncertainty", None)
                            or getattr(cf, "uncertainty", 0)
                            or 0
                        )
                        / 100.0,
                    }
                elif cf.uncertainty and cf.uncertainty > 0:
                    factor_data["uncertainty"] = {
                        "co2": float(cf.uncertainty or 0) / 100.0,
                        "ch4": float(cf.uncertainty or 0) / 100.0,
                        "n2o": float(cf.uncertainty or 0) / 100.0,
                    }
                elif cf.parent_fuel:
                    parent_factor = API_FACTORS.get(cf.parent_fuel, {})
                    if "uncertainty" in parent_factor:
                        factor_data["uncertainty"] = parent_factor["uncertainty"]

        gwp_dict = resolve_gwp_dict(user)
        gwp_std = resolve_gwp_standard(user)
        try:
            calculated_em, method = compute_emissions(
                data, factor_data, gwp_dict=gwp_dict
            )
            record.co2_emissions = calculated_em["co2"]
            record.ch4_emissions = calculated_em["ch4"]
            record.n2o_emissions = calculated_em["n2o"]
            record.co_emissions = calculated_em.get("co", 0)
            record.co2e_total = calculated_em["totalCo2e"]
            record.calc_method = method
            record.gwp_version = gwp_std

            # Update record uncertainty
            u_dict = factor_data.get("uncertainty", {})
            record.uncertainty = (
                u_dict.get("co2", None)
                if isinstance(u_dict, dict)
                else (u_dict or None)
            )
            record.uncertainty_ch4 = (
                u_dict.get("ch4", None)
                if isinstance(u_dict, dict)
                else (u_dict or None)
            )
            record.uncertainty_n2o = (
                u_dict.get("n2o", None)
                if isinstance(u_dict, dict)
                else (u_dict or None)
            )

            # Override with user-provided uncertainties if they exist
            user_unc = data.get("user_uncertainty")
            if user_unc and isinstance(user_unc, dict):
                if "co2" in user_unc and user_unc["co2"] not in [None, ""]:
                    record.uncertainty = float(user_unc["co2"]) / 100.0
                if "ch4" in user_unc and user_unc["ch4"] not in [None, ""]:
                    record.uncertainty_ch4 = float(user_unc["ch4"]) / 100.0
                if "n2o" in user_unc and user_unc["n2o"] not in [None, ""]:
                    record.uncertainty_n2o = float(user_unc["n2o"]) / 100.0

        except Exception as e:
            print(f"Error during emission recalculation: {e}")

    record.updated_by = user.id
    record.updated_at = datetime.datetime.utcnow()

    db.session.flush()

    # --- Audit Log ---
    try:
        # For updates, we could track exactly what changed
        changes = []
        for key in data:
            if key in [
                "year",
                "month",
                "facility_id",
                "process_type",
                "fuel_type",
                "quantity",
                "unit",
            ]:
                changes.append(key)

        log_details = (
            f"Updated emission record {id}. Changed fields: {', '.join(changes)}"
        )

        log_activity_and_notify(
            action="UPDATE",
            record_id=str(id),
            user=user,
            request=request,
            entity="Emission",
            details=log_details,
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    return jsonify({"message": "Record updated"})


@emissions_bp.route("/bulk-delete", methods=["POST"])
@login_required  # SEC-01 FIX: was missing
def bulk_delete_emissions():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    ids = data.get("ids", [])

    if not ids:
        return jsonify({"error": "No IDs provided"}), 400

    # SEC-03 FIX: IDOR — non-admins can only bulk-delete their own records
    query = Emission.query.filter(Emission.id.in_(ids))
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None:
        query = query.filter(Emission.facility_id.in_(allowed_fids))
    deleted_count = query.delete(synchronize_session=False)
    db.session.flush()

    # --- Audit Log ---
    try:
        log_activity_and_notify(
            action="DELETE",
            record_id="BULK",
            user=user,
            request=request,
            entity="Emission",
            details=f"Bulk deleted {deleted_count} emission records",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    return jsonify({"message": f"{deleted_count} records deleted"})


@emissions_bp.route("/import", methods=["POST"])
@login_required  # SEC-01 FIX: was missing
def import_emissions():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    records_data = data.get("records", [])

    if not records_data:
        return jsonify({"error": "No records provided"}), 400

    imported_count = 0
    errors = []

    allowed_ids = get_allowed_facility_ids(user)

    # Cache for facility lookups to avoid redundant queries
    facility_cache = {}

    for i, rec_data in enumerate(records_data):
        try:
            # 1. Resolve facility_id (could be a name string from CSV)
            f_val = rec_data.get("facility_id")
            facility = None

            if isinstance(f_val, str) and not f_val.isdigit():
                # Provided value is a facility name - make it case insensitive and strip whitespace
                f_name_clean = f_val.strip()
                if f_name_clean.lower() in facility_cache:
                    facility = facility_cache[f_name_clean.lower()]
                else:
                    facility = Facility.query.filter(
                        func.lower(Facility.name) == f_name_clean.lower()
                    ).first()
                    facility_cache[f_name_clean.lower()] = facility
            else:
                # Provided value is potentially an ID
                try:
                    fid = int(f_val) if f_val else None
                    if fid is not None:
                        if fid in facility_cache:
                            facility = facility_cache[fid]
                        else:
                            facility = db.session.get(Facility, fid)
                            facility_cache[fid] = facility
                    else:
                        facility = None
                except (ValueError, TypeError):
                    facility = None

            if not facility:
                errors.append(f"Row {i}: Facility/Region '{f_val}' not found")
                continue
            elif allowed_ids is not None and facility.id not in allowed_ids:
                errors.append(f"Row {i}: Unauthorized for facility '{f_val}'")
                continue

            # Update rec_data with resolved ID and ensure group_name is set for calculation context
            rec_data["facility_id"] = facility.id
            if not rec_data.get("group_name"):
                rec_data["group_name"] = facility.name

            # Fill in hierarchy if missing
            rec_data["activity"] = rec_data.get("activity") or facility.activity
            rec_data["division"] = rec_data.get("division") or facility.division
            rec_data["field"] = rec_data.get("field") or facility.field

            # CRITICAL: Sanitize CSV placeholders ('-') to prevent float conversion errors
            # CSV templates use '-' for empty optional fields
            for key in [
                "ch4_content",
                "hhv",
                "comp_flare_eff",
                "tank_gor",
                "tank_api_gravity",
                "flare_type",
                "pneu_bleed_rate",
                "pneu_hours",
                "dehy_pump_rate",
                "unload_diam",
                "unload_depth",
                "unload_press",
                "comp_duration",
                "comp_rate",
                "amount",
            ]:
                if rec_data.get(key) in ["-", "", None]:
                    rec_data[key] = None

            # Safe float conversion for amount
            if rec_data.get("amount") is not None:
                try:
                    rec_data["amount"] = float(rec_data["amount"])
                except (ValueError, TypeError):
                    errors.append(
                        f"Row {i}: Invalid numeric amount '{rec_data['amount']}'"
                    )
                    continue

            # 2. Fetch factor data
            fuel_key = rec_data.get("fuel") or rec_data.get("fuel_type")

            # CRITICAL: Fuel name aliasing - handle common variations
            FUEL_ALIASES = {
                "Diesel": "Diesel (No. 2 Fuel Oil)",
                "No. 2 Diesel": "Diesel (No. 2 Fuel Oil)",
                "Gasoline": "Motor Gasoline",
                "Petrol": "Motor Gasoline",
            }

            # Try alias first, then original
            canonical_fuel = FUEL_ALIASES.get(fuel_key, fuel_key)
            rec_data["fuel"] = canonical_fuel  # Update to canonical name

            factor_data = API_FACTORS.get(canonical_fuel, {})
            if not factor_data and fuel_key != canonical_fuel:
                # Fallback to original if alias didn't work
                factor_data = API_FACTORS.get(fuel_key, {})
                rec_data["fuel"] = fuel_key

            # CRITICAL: If no HHV provided in CSV, use factor's HHV or standard defaults
            if not rec_data.get("hhv"):
                # Try to get HHV from the emission factor
                if factor_data.get("hhv"):
                    rec_data["hhv"] = factor_data.get("hhv")
                else:
                    # Hardcoded defaults for common fuels (BTU/unit)
                    FUEL_HHV_DEFAULTS = {
                        "Natural Gas": 1020,  # BTU/scf
                        "Diesel": 138700,  # BTU/gal
                        "Gasoline": 125000,  # BTU/gal
                        "Fuel Oil": 138000,  # BTU/gal
                        "Propane": 91500,  # BTU/gal
                        "Butane": 103000,  # BTU/gal
                    }
                    default_hhv = FUEL_HHV_DEFAULTS.get(fuel_key)
                    if default_hhv:
                        rec_data["hhv"] = default_hhv

            # Check for custom factor if provided
            cf_id = rec_data.get("custom_factor_id")
            if cf_id:
                cf = CustomFactor.query.get(cf_id)
                if cf:
                    factor_data = {
                        "co2": cf.co2_factor,
                        "ch4": cf.ch4_factor,
                        "n2o": cf.n2o_factor,
                        "co": cf.co_factor,
                        "unit": cf.unit,
                        "hhv": cf.hhv_factor,
                        "type": "custom",
                        "name": cf.name,
                    }
                    # Uncertainty Handling (Import)
                    if cf.co2_uncertainty or cf.ch4_uncertainty or cf.n2o_uncertainty:
                        factor_data["uncertainty"] = {
                            "co2": float(
                                getattr(cf, "co2_uncertainty", None)
                                or getattr(cf, "uncertainty", 0)
                                or 0
                            )
                            / 100.0,
                            "ch4": float(
                                getattr(cf, "ch4_uncertainty", None)
                                or getattr(cf, "uncertainty", 0)
                                or 0
                            )
                            / 100.0,
                            "n2o": float(
                                getattr(cf, "n2o_uncertainty", None)
                                or getattr(cf, "uncertainty", 0)
                                or 0
                            )
                            / 100.0,
                        }
                    elif cf.uncertainty and cf.uncertainty > 0:
                        factor_data["uncertainty"] = {
                            "co2": float(cf.uncertainty or 0) / 100.0,
                            "ch4": float(cf.uncertainty or 0) / 100.0,
                            "n2o": float(cf.uncertainty or 0) / 100.0,
                        }
                    elif cf.parent_fuel:
                        parent_factor = API_FACTORS.get(cf.parent_fuel, {})
                        if "uncertainty" in parent_factor:
                            factor_data["uncertainty"] = parent_factor["uncertainty"]

            # 3. Compute emissions
            gwp_dict = resolve_gwp_dict(user)
            gwp_std = resolve_gwp_standard(user)
            em_result, method = compute_emissions(
                rec_data, factor_data, gwp_dict=gwp_dict
            )

            # Fallback for totalCo2e
            if not em_result.get("totalCo2e") or em_result.get("totalCo2e") == 0:
                co2_val = em_result.get("co2", 0)
                ch4_val = em_result.get("ch4", 0)
                n2o_val = em_result.get("n2o", 0)
                em_result["totalCo2e"] = calculate_co2e(
                    co2_val, ch4_val, n2o_val, gwp_dict=gwp_dict
                )

            # 4. Create record
            record = Emission(
                record_id=f"IMP-{uuid.uuid4().hex[:8]}-{i}",
                year=rec_data.get("year"),
                month=rec_data.get("month"),
                facility_id=facility.id,
                group_name=rec_data["group_name"],
                activity=rec_data["activity"],
                division=rec_data["division"],
                field=rec_data["field"],
                process_type=rec_data.get("process_type") or rec_data.get("type"),
                fuel_type=fuel_key,
                quantity=rec_data.get("amount"),
                unit=rec_data.get("unit"),
                equipment_id=rec_data.get("equipment_id"),
                co2_emissions=(
                    em_result.get("co2") if em_result.get("co2") is not None else 0
                ),
                ch4_emissions=(
                    em_result.get("ch4") if em_result.get("ch4") is not None else 0
                ),
                n2o_emissions=(
                    em_result.get("n2o") if em_result.get("n2o") is not None else 0
                ),
                co_emissions=(
                    em_result.get("co") if em_result.get("co") is not None else 0
                ),
                co2e_total=(
                    em_result.get("totalCo2e")
                    if em_result.get("totalCo2e") is not None
                    else 0
                ),
                calc_method=method,
                gwp_version=gwp_std,
                source_payload=json.dumps(rec_data),
                created_by=user.id,
                uncertainty=(
                    factor_data.get("uncertainty", {}).get("co2", 0)
                    if isinstance(factor_data.get("uncertainty"), dict)
                    else (factor_data.get("uncertainty") or 0)
                ),
                status=rec_data.get("status", "Verified"),
            )
            db.session.add(record)
            imported_count += 1
        except Exception as e:
            import traceback

            traceback.print_exc()
            errors.append(f"Row {i}: {str(e)}")

    from flask import current_app

    current_app.logger.info(
        f"Import summary: imported={imported_count}, errors={len(errors)}"
    )
    if errors and imported_count == 0:
        return jsonify({"error": "Import failed", "details": errors}), 400

    db.session.commit()

    return jsonify({"message": f"{imported_count} records imported"})


@emissions_bp.route("/export", methods=["GET"])
@login_required  # SEC-01 FIX: was missing
def export_emissions():
    """Export emissions to JSON format"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    query = Emission.query

    # BUG-09 FIX: cast query params to int before filtering integer columns
    if request.args.get("facilityId"):
        try:
            query = query.filter(
                Emission.facility_id == int(request.args.get("facilityId"))
            )
        except (ValueError, TypeError):
            pass
    if request.args.get("year"):
        try:
            query = query.filter(Emission.year == int(request.args.get("year")))
        except (ValueError, TypeError):
            pass
    if request.args.get("process"):
        query = query.filter(Emission.process_type == request.args.get("process"))

    emissions = query.all()

    export_data = []
    for r in emissions:
        export_data.append(
            {
                "record_id": r.record_id,
                "year": r.year,
                "month": r.month,
                "facility": r.facility.name if r.facility else "",
                "group": r.group_name,
                "process": r.process_type,
                "fuel": r.fuel_type,
                "quantity": r.quantity,
                "unit": r.unit,
                "co2": r.co2_emissions,
                "ch4": r.ch4_emissions,
                "n2o": r.n2o_emissions,
                "co2e_total": r.co2e_total,
                "status": r.status,
            }
        )

    return jsonify({"data": export_data, "count": len(export_data)})
