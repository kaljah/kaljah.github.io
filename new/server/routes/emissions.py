from flask import request, jsonify, session, current_app
from sqlalchemy import func
from . import emissions_bp
from utils import get_current_user, get_allowed_facility_ids, require_facility_access
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
from extensions import db, limiter
from utils import log_activity_and_notify
from services.labels import process_label, scope2_source_label
from services.scope2_activity import scope2_activity
from calculations import (
    compute_emissions,
    calculate_co2e,
)
from emission_factors import API_FACTORS, ALL_EMISSION_FACTORS
from routes.auth import login_required
import datetime
import uuid
import json
from sqlalchemy import cast, String, literal, Float, union_all, or_
from services.ogmp import ogmp_level_for
from process_categories import NON_COMBUSTION_PROCESSES
from utils import internal_error
from routes.emissions_template_csv import get_csv_template  # noqa: F401  (registers the CSV template route)
from routes.emissions_template_excel import get_excel_template  # noqa: F401  (registers the Excel template route)



def _escape_like(val: str) -> str:
    """NEW-07 FIX: Escape SQL LIKE wildcards in user-supplied search strings."""
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _canonical_api_factor_name(fuel_name: str):
    """The catalog name a fuel / factor name resolves to (exact, alias, case- and punctuation-
    insensitive, or factor code), or None."""
    if not fuel_name:
        return None
    factor_catalog = {**API_FACTORS, **ALL_EMISSION_FACTORS}
    if fuel_name in factor_catalog:
        return fuel_name
    norm = str(fuel_name).lower().replace("_", " ").replace("-", " ").strip()
    aliases = {
        "natural gas": "Natural Gas",
        "gas": "Natural Gas",
        "diesel": "Diesel (No. 2 Fuel Oil)",
        "crude oil": "Crude Oil",
        "lpg": "Propane (Liquid)",
        "propane": "Propane (Gas)",
        "gasoline": "Motor Gasoline",
        "kerosene": "Kerosene",
        "coal": "Bituminous Coal",
        "tank flash emissions oil": "Tank - Flash Emissions (Oil)",
        "tank flash oil": "Tank - Flash Emissions (Oil)",
        "tank flash": "Tank - Flash Emissions (Oil)",
        "asphalt": "Asphalt",
        "asphalt blowing": "Asphalt",
    }
    canonical = aliases.get(norm)
    if canonical and canonical in factor_catalog:
        return canonical
    def _n(x):
        return str(x).lower().replace("_", " ").replace("-", " ").strip()

    for k in factor_catalog:
        if _n(k) == norm:
            return k
    # a factor code only when it names one factor: several factors share a code (e.g. CB_Prod is
    # Carbon Black with and without thermal abatement, CH4 478x apart) and the first one used to win
    by_code = [k for k, v in factor_catalog.items() if v.get("code") and _n(v["code"]) == norm]
    distinct = {repr(sorted((kk, str(vv)) for kk, vv in factor_catalog[k].items() if kk in ("co2", "ch4", "n2o", "unit", "hhv")))
                for k in by_code}
    return by_code[0] if by_code and len(distinct) == 1 else None


def _lookup_api_factor(fuel_name: str) -> dict:
    """Look up an emission factor from ALL_EMISSION_FACTORS / API_FACTORS supporting exact, normalized, and alias matches."""
    name = _canonical_api_factor_name(fuel_name)
    return {**API_FACTORS, **ALL_EMISSION_FACTORS}[name] if name else {}


@emissions_bp.route("/", methods=["GET"])
@login_required  # SEC-01 FIX: was missing, route was unauthenticated
def get_emissions():
    from flask import current_app

    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT personnel do not have access to emission data"}), 403

    current_app.logger.info(f"[Emissions] Fetch requested by user_id: {user.id}")

    # Parameters from request
    limit_arg = request.args.get("limit", "50")
    offset_arg = request.args.get("offset", "0")

    # Handle both 'page' and 'limit/offset' pagination with strict bounds
    if "limit" in request.args and "offset" in request.args:
        try:
            per_page = int(limit_arg)
            offset = max(0, int(offset_arg))
            per_page = max(1, min(5000, per_page))
            page = (offset // per_page) + 1
            start = offset  # honour non page-aligned offsets exactly
        except (ValueError, TypeError, ZeroDivisionError):
            per_page = 50
            page = 1
            start = 0
    else:
        try:
            page = max(1, request.args.get("page", 1, type=int))
        except (ValueError, TypeError):
            page = 1
        if limit_arg == "all":
            per_page = 5000  # SEC-10 FIX: hard cap
        else:
            try:
                per_page = max(1, min(5000, int(limit_arg)))
            except (ValueError, TypeError):
                per_page = 50
        start = (page - 1) * per_page

    scope = request.args.get("scope", "all")
    year = request.args.get("year")
    month = request.args.get("month")
    facility_id = request.args.get("facilityId") or request.args.get("facility_id")
    process_type = request.args.get("process") or request.args.get("process_type")
    division_arg = request.args.get("division")
    field_arg = request.args.get("field")
    search_term = request.args.get("search")
    method_arg = request.args.get("method")
    status_arg = request.args.get("status")  # BUG-077: inventory consumers request Verified only

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
            # same base year as /dashboard/base-year (latest recalculation, else the official baseline);
            # with none configured there is no baseline (it used to fall back to an invented 2020)
            from models import BaseYear, BaseYearRecalculation

            rec = BaseYearRecalculation.query.order_by(BaseYearRecalculation.recalc_date.desc()).first()
            base = rec or BaseYear.query.first()
            if not base:
                return q.filter(model.id == -1)
            year = str(base.year)

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
        if status_arg and status_arg != "all" and hasattr(model, "status"):
            q = q.filter(model.status.in_([x.strip() for x in status_arg.split(",") if x.strip()]))
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

    # H5: always bounded, including limit=all (capped at 5000 above)
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
                if payload.get("custom_factor_id") not in (None, ""):
                    d["custom_factor_id"] = payload.get("custom_factor_id")
            except Exception:
                pass
        paginated_results.append(d)

    # Records saved with a library / custom factor before the factor name was stored show the
    # factor id as their fuel (browser test #13): show the factor's name instead
    cf_ids = {int(d["custom_factor_id"]) for d in paginated_results
              if str(d.get("custom_factor_id") or "").isdigit() and str(d.get("fuel") or "").isdigit()}
    if cf_ids:
        from models import CustomFactor
        names = {cf.id: cf.name for cf in CustomFactor.query.filter(CustomFactor.id.in_(cf_ids)).all()}
        for d in paginated_results:
            if str(d.get("fuel") or "").isdigit() and str(d.get("custom_factor_id") or "").isdigit():
                d["fuel"] = names.get(int(d["custom_factor_id"]), d["fuel"])

    return jsonify(
        {
            "data": paginated_results,
            "emissions": paginated_results,
            "total": total,
            "pages": (total // per_page) + (1 if total % per_page > 0 else 0),
            "current_page": page,
        }
    )


def resolve_gwp_standard(user=None):
    """Returns the organization-wide GWP standard (AR4, AR5, AR6) per D-09."""
    try:
        from routes.auth import _app_settings, load_settings_from_db
        load_settings_from_db()
        return _app_settings.get("gwp_standard", "AR5")
    except Exception:
        return "AR5"


def resolve_gwp_dict(user=None):
    """Returns active GWP dictionary using global org-wide standard per D-09."""
    from calculations.constants import get_active_gwp
    std = resolve_gwp_standard()
    return get_active_gwp(standard=std)



import os
import tempfile
from flask import send_file, Response
from background_processor import start_background_upload, get_job_status



@emissions_bp.route("/", methods=["POST"])
@login_required
def add_emission():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ("auditor", "it_admin", "it_manager", "it"):
        return jsonify({"error": "Forbidden: Read-only or administrative role cannot create emission records"}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON: payload must be a JSON object"}), 400

    # Map source_type to process_type if missing, and vice versa
    if not data.get("process_type") and data.get("source_type"):
        data["process_type"] = data["source_type"]
    if not data.get("source_type") and data.get("process_type"):
        data["source_type"] = data["process_type"]

    # Validation
    required = ["year", "month", "facility_id", "process_type"]
    for field in required:
        if field not in data or data[field] is None:
            return jsonify({"error": f"Missing field: {field}"}), 422

    # Numeric & bounds validation (shared validators: year 1900..current+1, month 1..12)
    from input_validation import ValidationError, parse_month, parse_year
    from services.scope1_calc import canonicalize, resolve_factor, validate_activity

    try:
        data["year"] = parse_year(data["year"])
        data["month"] = parse_month(data["month"], required=True)
        # RC-6: amount/quantity and fuel/fuel_type are one value each (BUG-030)
        data = canonicalize(data)
        validate_activity(data, require_unit=str(data.get("factor_source") or "default").lower() in ("default", "custom"))
    except ValidationError as err:
        return jsonify({"error": err.message, "field": err.field}), 422

    for str_field in ["fuel", "fuel_type", "source_type", "sub_type", "process_type"]:
        val = data.get(str_field)
        if val and len(str(val)) > 200:
            return jsonify({"error": f"Invalid {str_field}: exceeds maximum length of 200 characters"}), 422

    try:
        fac_id = int(data["facility_id"])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid facility_id: must be an integer"}), 422

    allowed_ids = get_allowed_facility_ids(user)
    if allowed_ids is not None and fac_id not in allowed_ids:
        return jsonify({"error": "Unauthorized for this facility"}), 403

    facility = db.session.get(Facility, fac_id)

    # Process-specific input validation for associated_gas_venting
    p_type = (data.get("process_type") or "").lower().strip()
    if p_type in ["associated_gas_venting", "associated_venting", "associated_gas"]:
        ch4_in = data.get("ch4_content")
        co2_in = data.get("co2_content")
        c_ch4_val = None
        c_co2_val = None

        if ch4_in not in [None, "", "-"]:
            try:
                c_ch4_val = float(str(ch4_in).replace("%", "").strip())
                if c_ch4_val > 1.0:
                    c_ch4_val /= 100.0
                if c_ch4_val < 0.0 or c_ch4_val > 1.0:
                    return jsonify({"error": f"Invalid CH4 content: must be between 0% and 100% (got {c_ch4_val*100:.1f}%)", "field": "ch4_content"}), 422
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid CH4 content: must be a number", "field": "ch4_content"}), 422

        if co2_in not in [None, "", "-"]:
            try:
                c_co2_val = float(str(co2_in).replace("%", "").strip())
                if c_co2_val > 1.0:
                    c_co2_val /= 100.0
                if c_co2_val < 0.0 or c_co2_val > 1.0:
                    return jsonify({"error": f"Invalid CO2 content: must be between 0% and 100% (got {c_co2_val*100:.1f}%)", "field": "co2_content"}), 422
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid CO2 content: must be a number", "field": "co2_content"}), 422

        if c_ch4_val is not None and c_co2_val is not None:
            if (c_ch4_val + c_co2_val) > 1.0001:
                return jsonify({
                    "error": f"Gas composition error: Sum of CH4 ({c_ch4_val*100:.1f}%) and CO2 ({c_co2_val*100:.1f}%) exceeds 100%",
                    "field": "ch4_content",
                }), 422

        v_dur = data.get("venting_duration")
        if v_dur not in [None, "", "-"]:
            try:
                dur_float = float(v_dur)
                if dur_float < 0:
                    return jsonify({"error": "Venting duration cannot be negative", "field": "venting_duration"}), 422
                d_unit = str(data.get("duration_unit") or "days").lower()
                dur_days = dur_float if "day" in d_unit else dur_float / 24.0
                if dur_days > 366.0:
                    return jsonify({"error": f"Venting duration ({dur_days:.1f} days) exceeds maximum annual limit of 366 days", "field": "venting_duration"}), 422
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid venting duration: must be a number", "field": "venting_duration"}), 422

        gor_in = data.get("gor")
        if gor_in not in [None, "", "-"]:
            try:
                gor_float = float(gor_in)
                if gor_float < 0:
                    return jsonify({"error": "Gas-to-Oil Ratio (GOR) cannot be negative", "field": "gor"}), 422
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid GOR: must be a number", "field": "gor"}), 422

        for gas_f in ["recovered_gas_volume", "flared_gas_volume"]:
            val_in = data.get(gas_f)
            if val_in not in [None, "", "-"]:
                try:
                    vf = float(val_in)
                    if vf < 0:
                        return jsonify({"error": f"{gas_f.replace('_', ' ').capitalize()} cannot be negative", "field": gas_f}), 422
                except (ValueError, TypeError):
                    return jsonify({"error": f"Invalid {gas_f}: must be a number", "field": gas_f}), 422

    # Calculate Emissions
    # We need to fetch factor data if not specific
    # For now, using a simplified factor data placeholder or letting calculate handle it
    # In a real scenario, we'd query the factor database here.
    # Passing empty factor_data relies on hardcoded defaults in calculations.py if any

    # RC-4 / RC-6: one factor resolution (catalog or custom), never a silent zero factor
    try:
        factor_data = resolve_factor(data)
    except ValidationError as err:
        return jsonify({"error": err.message, "field": err.field}), 422
    if factor_data.get("hhv") and not data.get("hhv"):
        data["hhv"] = factor_data["hhv"]

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
        return jsonify({"error": str(e), "field": field, "detail": str(e)}), 422

    # Fallback: Calculate totalCo2e if it's missing or zero
    if not em_result.get("totalCo2e") or em_result.get("totalCo2e") == 0:
        co2_val = em_result.get("co2", 0)
        ch4_val = em_result.get("ch4", 0)
        n2o_val = em_result.get("n2o", 0)
        em_result["totalCo2e"] = calculate_co2e(
            co2_val, ch4_val, n2o_val, gwp_dict=gwp_dict
        )

    # BUG-007: plausibility bounds and statistical anomaly check on the manual path too
    from calculations.anomaly import AnomalyDetector, plausibility_check, scope1_source
    from services.scope1_calc import apply_result
    from utils import initial_record_status, user_label

    # the statistical check runs once the record carries its final source (equipment / fuel), below
    verdict, qa_msg = plausibility_check(em_result["totalCo2e"], None)
    if verdict == "reject":
        return jsonify({"error": qa_msg, "field": "amount"}), 422

    status = initial_record_status(user, data.get("status"))
    if verdict == "flag" and status == "Verified":
        status = "Pending"  # flagged values always need a reviewer, even for admins

    record = Emission(
        record_id=str(uuid.uuid4()),
        year=data["year"],
        month=data["month"],
        facility_id=data["facility_id"],
        group_name=data.get("group_name"),
        activity=data.get("activity") or (facility.activity if facility else None),
        division=data.get("division") or (facility.division if facility else None),
        region=data.get("region") or (facility.region if facility and facility.region else (facility.name if facility else None)),
        field=data.get("field") or (facility.field if facility else None),
        equipment_id=data.get("equipment_id"),
        created_by=user.id,
        created_by_name=user_label(user),
        status=status,
        approved_by=user.id if status == "Verified" else None,
        approved_by_name=user_label(user) if status == "Verified" else None,
        approved_at=datetime.datetime.now(datetime.timezone.utc) if status == "Verified" else None,
        qa_flag=qa_msg[:255] if qa_msg else None,
        factor_source=(
            data.get("factor_source")
            or ("custom" if data.get("factor_type") == "custom" else ("specific" if data.get("calc_method") in ("direct_measurement", "engineering", "specific", "tier3") else "default"))
        ),
        data_source_ref=(
            str(data.get("data_source_ref") or data.get("ticket_ref") or data.get("bulletin_ref") or "")[:120]
            or None
        ),
    )
    apply_result(record, data, em_result, method, factor_data, gwp_std)
    uncertainty = {"co2": record.uncertainty, "ch4": record.uncertainty_ch4, "n2o": record.uncertainty_n2o}
    record.ogmp_level = ogmp_level_for(record)

    facility = db.session.get(Facility, data.get("facility_id"))
    facility_name = facility.name if facility else "Unknown"

    # statistical anomaly against the same source's previous 12 months (flagged values need a reviewer)
    if not qa_msg:
        try:
            z = AnomalyDetector().check_scope1(int(data["facility_id"]), record.process_type, em_result["totalCo2e"],
                                               data["year"], data["month"],
                                               source=scope1_source(record.equipment_id, record.fuel_type))
            if z.get("flagged") and z.get("message"):
                record.qa_flag = z["message"][:255]
                if record.status == "Verified":
                    record.status = "Pending"
                    record.approved_by = record.approved_by_name = record.approved_at = None
        except Exception:
            pass

    db.session.add(record)
    try:
        db.session.flush()
        record_id_val = record.id

        # --- Audit Log ---
        log_details = f"Added {record.process_type} emission: {record.quantity} {record.unit} of {record.fuel_type} for {facility_name} ({record.month}/{record.year})"
        log_activity_and_notify(
            action="CREATE",
            record_id=str(record_id_val),
            user=user,
            request=request,
            entity="Emission",
            entity_id=str(record_id_val),
            facility_id=record.facility_id,
            details=log_details,
        )
        if record.status in ("Pending", "Pending Approval"):
            admins = User.query.filter_by(role="admin", status="active").all()
            for admin in admins:
                Notification.create(
                    user_id=admin.id,
                    type="audit",
                    title="New Scope 1 Emission Pending Review",
                    message=f"A new Scope 1 emission record ({record.process_type}, {facility_name}) was submitted by {user.fullName} and is awaiting your approval.",
                )

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
                        .filter(Emission.year == current_year, Emission.status == "Verified")
                        .scalar()
                        or 0
                    ) + (
                        db.session.query(func.sum(Scope2Emission.co2e))
                        .filter(Scope2Emission.year == current_year, Scope2Emission.status == "Verified")
                        .scalar()
                        or 0
                    )

                    # Get Goal
                    goal = db.session.get(Goal, current_year)

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
                            from datetime import timedelta

                            cutoff = datetime.datetime.now(datetime.timezone.utc) - timedelta(hours=24)
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
                            elif existing.message != msg:
                                existing.message = msg
        except Exception as e:
            current_app.logger.warning(f"Notification check error: {e}")

        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to record emission and audit trail")
        return jsonify({"error": "Failed to record emission"}), 500

    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()

    # Return emission result with uncertainty
    return (
        jsonify(
            {
                "message": "Record added",
                "id": record_id_val,
                "emissions": {
                    "co2": em_result["co2"],
                    "ch4": em_result["ch4"],
                    "n2o": em_result["n2o"],
                    "totalCo2e": em_result["totalCo2e"],
                    "uncertainty": uncertainty,
                },
                "record": {
                    "process_type": data["process_type"],
                    "facility_name": facility_name,
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

    clean_id = str(id)[3:] if str(id).startswith("s1_") else str(id)
    record = (
        Emission.query.filter_by(record_id=id).first()
        or Emission.query.filter_by(record_id=clean_id).first()
        or db.session.get(Emission, int(clean_id) if clean_id.isdigit() else -1)
    )
    if not record:
        return jsonify({"error": "Record not found"}), 404
    # BUG-067: approved records are not deletable by makers; region and ownership enforced
    from services.maker_checker import delete_denied_reason

    denied = delete_denied_reason(user, record)
    if denied:
        return jsonify({"error": denied}), 403
    fac_id_for_log = record.facility_id

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
            facility_id=fac_id_for_log,
        )
        db.session.commit()  # single atomic commit for delete + audit
        from routes.dashboard import clear_dashboard_cache

        clear_dashboard_cache()
    except Exception as e:
        db.session.rollback()
        raise e

    return jsonify({"message": "Record deleted"})


@emissions_bp.route("/<id>", methods=["PUT"])
@login_required  # EXTRA-06 FIX: decorator was present but get_current_user() could return None causing 500
def update_emission(id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if user.role in ["auditor", "it_admin", "it_manager", "it"]:
        return jsonify({"error": "Read-only or administrative role cannot modify emission records"}), 403

    data = request.get_json()
    clean_id = str(id)[3:] if str(id).startswith("s1_") else str(id)
    record = (
        Emission.query.filter_by(record_id=id).first()
        or Emission.query.filter_by(record_id=clean_id).first()
        or db.session.get(Emission, int(clean_id) if clean_id.isdigit() else -1)
    )  # EXTRA-02 FIX

    if not record:
        return jsonify({"error": "Not found"}), 404
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and record.facility_id not in allowed_fids:
        return jsonify({"error": "Unauthorized: Outside your region"}), 403

    # Enforce creator ownership for standard user role
    if user.role == "user" and record.created_by is not None and record.created_by != user.id:
        return jsonify({"error": "Unauthorized: You may only modify records you created"}), 403

    import json

    data = data or {}
    
    before_state = {
        "year": record.year,
        "month": record.month,
        "facility_id": record.facility_id,
        "process_type": record.process_type,
        "fuel_type": record.fuel_type,
        "quantity": record.quantity,
        "unit": record.unit,
        "status": record.status,
        "co2e_total": record.co2e_total,
    }

    # Strip status from client update payload (H2: prevent maker-checker bypass)
    data.pop("status", None)
    data.pop("approved_by", None)
    data.pop("approved_at", None)

    # Disallow direct client overwrite of calculated totals without recalculation
    data.pop("co2e_total", None)
    data.pop("co2_emissions", None)
    data.pop("ch4_emissions", None)
    data.pop("n2o_emissions", None)

    # Update fields (validated: BUG-073 / BUG-083 on the edit path too)
    from input_validation import parse_year, parse_month
    from services.maker_checker import on_edit

    if "year" in data:
        record.year = parse_year(data["year"])
    if "month" in data:
        record.month = parse_month(data["month"], required=True)
    if "facility_id" in data:
        new_fid = int(data["facility_id"])
        if not require_facility_access(user, new_fid):
            return jsonify({"error": "Unauthorized to reassign to this facility"}), 403
        record.facility_id = new_fid
    # BUG-067: every edit records the last maker; non-admin edits of decided records go back to review
    on_edit(record, user)
    # Recalculate whenever physical activity or factor inputs are modified (L9)
    recalc_keys = {"quantity", "amount", "fuel", "fuel_type", "unit", "custom_factor_id", "calc_method",
                   "process_type", "factor_source", "calc_inputs", "hhv", "user_uncertainty"}
    should_recalc = data.get("recalculate") or any(k in data for k in recalc_keys)

    if should_recalc:
        # RC-6: rebuild the calculation from the stored payload + record + this edit, with aliases
        # synchronised (BUG-003), the custom factor carried over (BUG-042), and the result
        # persisted exactly like a create (BUG-030 / BUG-037).
        from services.scope1_calc import apply_result, canonicalize, resolve_factor, validate_activity

        stored = {}
        if record.source_payload:
            try:
                stored = json.loads(record.source_payload)
            except Exception:
                stored = {}
        base = {
            "process_type": record.process_type, "process": record.process_type, "fuel_type": record.fuel_type,
            "fuel": record.fuel_type, "unit": record.unit, "quantity": record.quantity, "amount": record.quantity,
            # record.calc_method is the calculator's result label, not a method input
            "factor_source": record.factor_source,
            "custom_factor_id": record.custom_factor_id or stored.get("custom_factor_id"),
        }
        calc_payload = canonicalize({**base, **{k: v for k, v in stored.items() if v is not None}})
        calc_payload = canonicalize(calc_payload, delta={k: v for k, v in data.items() if k != "recalculate"})
        calc_payload["year"], calc_payload["month"] = record.year, record.month
        calc_payload["facility_id"] = record.facility_id
        if "fuel" in data or "fuel_type" in data:
            # a changed fuel on a Tier 2 record means the user picked another factor
            if "custom_factor_id" not in data and str(calc_payload.get("factor_source")).lower() != "custom":
                calc_payload.pop("custom_factor_id", None)
        try:
            validate_activity(calc_payload, require_unit=str(calc_payload.get("factor_source") or "default").lower() in ("default", "custom"))
            factor_data = resolve_factor(calc_payload, stored_payload=stored, allow_archived=True)
            if factor_data.get("hhv") and "hhv" not in data:
                calc_payload["hhv"] = factor_data["hhv"]
            gwp_dict = resolve_gwp_dict(user)
            gwp_std = resolve_gwp_standard(user)
            calculated_em, method = compute_emissions(calc_payload, factor_data, gwp_dict=gwp_dict)
        except ValueError as err:  # ValidationError, MissingFactorError, calculator input errors
            db.session.rollback()
            return jsonify({"error": getattr(err, "message", None) or str(err),
                            "field": getattr(err, "field", None)}), 422

        from calculations.anomaly import plausibility_check

        verdict, qa_msg = plausibility_check(calculated_em["totalCo2e"])
        if verdict == "reject":
            db.session.rollback()
            return jsonify({"error": qa_msg, "field": "amount"}), 422
        apply_result(record, calc_payload, calculated_em, method, factor_data, gwp_std)
        if verdict == "flag":
            record.qa_flag = qa_msg[:255]
            if record.status == "Verified":
                record.status, record.approved_by, record.approved_at = "Pending", None, None
                record.approved_by_name = None
    else:
        if "process_type" in data:
            record.process_type = data["process_type"]
        if "unit" in data:
            record.unit = data["unit"]

    record.updated_by = user.id
    record.updated_at = datetime.datetime.now(datetime.timezone.utc)

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

        after_state = {
            "year": record.year,
            "month": record.month,
            "facility_id": record.facility_id,
            "process_type": record.process_type,
            "fuel_type": record.fuel_type,
            "quantity": record.quantity,
            "unit": record.unit,
            "status": record.status,
            "co2e_total": record.co2e_total,
        }

        log_activity_and_notify(
            action="UPDATE",
            record_id=str(id),
            user=user,
            request=request,
            entity="Emission",
            details=log_details,
            metadata_json=json.dumps({"before": before_state, "after": after_state})
        )
        db.session.commit()
        from routes.dashboard import clear_dashboard_cache

        clear_dashboard_cache()
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

    # BUG-067 (alternative endpoint): the same per-record rules as DELETE /api/emissions/<id>
    from services.maker_checker import delete_denied_reason

    deleted_count, denied = 0, []
    for rec in Emission.query.filter(Emission.id.in_(ids)).all():
        reason = delete_denied_reason(user, rec)
        if reason:
            denied.append({"id": rec.id, "error": reason})
            continue
        db.session.delete(rec)
        deleted_count += 1
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
        from routes.dashboard import clear_dashboard_cache

        clear_dashboard_cache()
    except Exception as e:
        db.session.rollback()
        raise e

    return jsonify({"message": f"{deleted_count} records deleted", "deleted": deleted_count, "denied": denied})



# ─── Maker-Checker Approval ───────────────────────────────────────────────────


# Route modules split out of this file; imported last because they use the helpers above.
from routes import emissions_bulk_upload, emissions_export, emissions_import, emissions_mappings, emissions_review  # noqa: E402,F401
