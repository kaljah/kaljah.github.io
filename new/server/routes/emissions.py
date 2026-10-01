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


@emissions_bp.route("/bulk-upload", methods=["POST"])
@limiter.limit("20 per minute")
@login_required
def add_bulk_upload():
    from datetime import datetime

    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT personnel do not have access to upload emission data"}), 403

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
    from utils import build_name_map

    fac_name_map = build_name_map(all_facilities)

    # Pre-fetch user's custom factors
    custom_factors = CustomFactor.query.filter_by(created_by=user.id, is_archived=False).all()
    cf_name_map = build_name_map(custom_factors)

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

        proc_clean = str(process_type).strip().lower()
        factor_type_raw = str(row.get("factor_type", "")).lower()
        if global_factor_type and global_factor_type != "auto":
            factor_type = global_factor_type
        else:
            factor_type = factor_type_raw

        is_tier3_factor = factor_type in [
            "specific", "site_specific", "site-specific", "engineering", "tier3", "tier_3", "t3", "cems"
        ]
        is_non_comb = proc_clean in NON_COMBUSTION_PROCESSES or is_tier3_factor

        if not process_type:
            row_errors.append("Missing process type.")
        if not fuel and not is_non_comb:
            row_errors.append("Missing fuel/activity.")

        # 4. Resolve Factor (Standard vs Custom vs Sparse Engineering)
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
            cf = cf_name_map.get(fuel.strip().lower())
            if fuel.strip().lower() in cf_name_map.ambiguous:
                row_errors.append(f"Custom factor name '{fuel}' is not unique; rename the duplicates first.")
            elif not cf:
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
                    parent_factor = _lookup_api_factor(cf.parent_fuel)
                    if "uncertainty" in parent_factor:
                        factor_data["uncertainty"] = parent_factor["uncertainty"]
        elif is_non_comb or is_tier3_factor:
            factor_data = API_FACTORS.get(fuel, {})
        else:
            factor_data = API_FACTORS.get(fuel, {})
            if (
                not factor_data
                and not row_errors
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
            "destruction_efficiency",
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

        if is_tier3_factor or has_specific:
            calc_data["factor_source"] = "specific"
        elif factor_type in ["custom", "regional", "tier2", "tier_2", "t2"]:
            calc_data["factor_source"] = "custom"
        elif factor_type == "default":
            calc_data["factor_source"] = "default"


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

        # Prepare Record — all bulk upload paths queue as Pending per Decision D-04
        rec_id = str(uuid.uuid4())
        bulk_status = "Pending"
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
            status=bulk_status,
            approved_by=user.id if bulk_status == "Verified" else None,
            approved_at=datetime.datetime.now(datetime.timezone.utc) if bulk_status == "Verified" else None,
            factor_source=calc_data.get("factor_source", "default"),
        )
        emission_obj.ogmp_level = ogmp_level_for(emission_obj)


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
                # overwrite through the maker-checker (back to Pending, old and new values in the
                # audit trail), never by deleting the reviewed record
                from background_processor import _S1_RESULT_FIELDS, _bulk_overwrite

                _bulk_overwrite(duplicate, {f: getattr(emission_obj, f) for f in _S1_RESULT_FIELDS
                                            if f not in ("qa_flag",)}, user.id, "Scope 1")
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
                # If records are pending approval, notify all admins
                if bulk_status in ("Pending", "Pending Approval"):
                    admins = User.query.filter_by(role="admin", status="active").all()
                    for admin in admins:
                        Notification.create(
                            user_id=admin.id,
                            type="audit",
                            title="Scope 1 Bulk Upload Pending Review",
                            message=f"{len(new_emissions):,} new Scope 1 emission records were uploaded by {user.fullName} and are awaiting your approval.",
                        )
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                return internal_error(e, "Failed to save to database")

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


def _template_args():
    """(tier, processes, optional columns, facility names the user can upload to) of a template request."""
    from services.scope1_template import normalize_tier, wanted_processes
    from utils import get_allowed_facility_ids

    tier = normalize_tier(request.args.get("tier", "auto"))
    processes = wanted_processes(request.args.get("process", "all"))
    optional = str(request.args.get("optional", "")).lower() in ("1", "true", "yes")
    facilities = []
    user = get_current_user()
    if user:
        from models import Facility

        allowed = get_allowed_facility_ids(user)
        q = Facility.query if allowed is None else Facility.query.filter(Facility.id.in_(allowed))
        facilities = sorted({f.name for f in q.all() if f.name})
    return tier, processes, optional, facilities


@emissions_bp.route("/template/csv", methods=["GET"])
def get_csv_template():
    """Scope 1 CSV template built from services.scope1_template: column names are the import names,
    one short help row, example rows dated EXAMPLE (skipped on import). Only the columns of the chosen
    tier and processes are included (?tier=1|2|3|auto&process=a,b&optional=1)."""
    from services.scope1_template import build_csv, template_filename

    tier, processes, optional, facilities = _template_args()
    body = build_csv(tier, processes, optional, facilities[0] if facilities else "Your Facility")
    return Response(
        body,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={template_filename(tier, processes, 'csv')}"},
    )


@emissions_bp.route("/template/excel", methods=["GET"])
def get_excel_template():
    """Scope 1 Excel template from the same column spec: Data Entry with dropdowns (the fuel and unit
    lists follow the row's process), Examples, Reference and a hidden Lists sheet."""
    from services.scope1_template import build_xlsx, template_filename

    tier, processes, optional, facilities = _template_args()
    return send_file(
        build_xlsx(tier, processes, optional, facilities),
        as_attachment=True,
        download_name=template_filename(tier, processes, "xlsx"),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _read_upload_request():
    """The validated upload form (file saved to a temp path), or an error response. Shared by the import
    and by the "Check file" step so both refuse the same files."""
    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "Unauthorized"}), 401)

    if "file" not in request.files:
        return None, (jsonify({"error": "No file part"}), 400)
    file = request.files["file"]
    if file.filename == "":
        return None, (jsonify({"error": "No selected file"}), 400)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext == ".xls":
        # the reader handles Excel 2007+ workbooks only (a .xls file was read as text)
        return None, (jsonify({"error": "Excel 97-2003 (.xls) files are not supported: save the file as .xlsx or .csv"}), 400)
    if ext not in [".csv", ".xlsx"]:
        return None, (jsonify({"error": "Invalid file type. Only .csv and .xlsx files are allowed."}), 400)

    global_factor_type = request.form.get("global_factor_type", "auto")
    mapping_str = request.form.get("column_mapping") or request.form.get("mapping")
    scope = request.form.get("scope", "1")
    overwrite_duplicates = request.form.get("overwrite_duplicates") == "true"

    # BUG-001: the bulk job must enforce the same roles as the dedicated endpoints.
    if user.role in ["it_admin", "it_manager", "it"]:
        return None, (jsonify({"error": "IT accounts cannot upload business data"}), 403)
    if user.role == "auditor":
        return None, (jsonify({"error": "Read-only role cannot upload data"}), 403)
    if scope not in ("1", "2", "3", "3_eeio", "sources", "production", "mitigation", "custom_factors", "facilities"):
        return None, (jsonify({"error": f"Unknown import type '{scope}'"}), 400)
    if scope in ("facilities", "custom_factors") and user.role not in ["admin", "superuser"]:
        return None, (jsonify({"error": "Only admins and superusers can import facilities or custom factors"}), 403)

    import json

    provided_mapping = None
    if mapping_str:
        try:
            provided_mapping = json.loads(mapping_str)
        except json.JSONDecodeError:
            return None, (jsonify({"error": "column_mapping is not valid JSON"}), 400)
        if not isinstance(provided_mapping, dict):
            return None, (jsonify({"error": "column_mapping must be an object of field -> column"}), 400)

    fd, path = tempfile.mkstemp(suffix=ext)
    os.close(fd)  # H6: Close descriptor immediately to prevent leak
    file.save(path)

    # Content sniffing check for Excel
    if ext == ".xlsx":
        try:
            with open(path, "rb") as f_check:
                header = f_check.read(4)
                if header != b"PK\x03\x04":
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    return None, (jsonify({"error": "Invalid or corrupted XLSX file"}), 400)
        except Exception:
            pass

    return {"user": user, "path": path, "filename": file.filename, "global_factor_type": global_factor_type,
            "mapping": provided_mapping, "scope": scope, "overwrite": overwrite_duplicates}, None


@emissions_bp.route("/upload/start", methods=["POST"])
@login_required
def upload_start():
    req, err = _read_upload_request()
    if err:
        return err
    from flask import current_app

    job_id = start_background_upload(
        current_app._get_current_object(),
        req["path"],
        req["filename"],
        req["user"].id,
        req["global_factor_type"],
        provided_mapping=req["mapping"],
        scope=req["scope"],
        overwrite_duplicates=req["overwrite"],
    )

    return jsonify({"job_id": job_id})


@emissions_bp.route("/upload/check", methods=["POST"])
@login_required
def upload_check():
    """Check a file before importing it: the first `sample_rows` rows are calculated exactly as the import
    would, every row is counted (period, facilities, processes), and nothing is saved."""
    req, err = _read_upload_request()
    if err:
        return err
    from flask import current_app
    from background_processor import run_file_check

    try:
        sample = max(100, min(int(request.form.get("sample_rows") or 2000), 20000))
    except ValueError:
        sample = 2000
    status = run_file_check(current_app._get_current_object(), req["path"], req["filename"], req["user"].id,
                            req["global_factor_type"], provided_mapping=req["mapping"], scope=req["scope"],
                            overwrite_duplicates=req["overwrite"], sample_rows=sample)
    if not status or status.get("status") != "completed":
        errors = (status or {}).get("errors") or ["The file could not be checked."]
        return jsonify({"error": errors[0], "errors": errors}), 400
    return jsonify({"preview": status.get("preview"), "skipped_groups": status.get("skipped_groups", [])})


@emissions_bp.route("/upload/limits", methods=["GET"])
@login_required
def upload_limits():
    """Upload limits the wizard checks when a file is picked (no row limit; the request size is capped)."""
    from flask import current_app

    return jsonify({"max_bytes": current_app.config.get("MAX_CONTENT_LENGTH")})


# ── Saved column mappings (import wizard) ─────────────────────────────────────
_MAPPING_SCOPES = ("1", "2", "3", "3_eeio", "sources", "production", "mitigation", "custom_factors", "facilities")
MAX_SAVED_MAPPINGS = 50


@emissions_bp.route("/upload/mappings", methods=["GET"])
@login_required
def list_import_mappings():
    """The user's saved column mappings for an import type, most recently used first."""
    from models import ImportMapping

    user = get_current_user()
    scope = str(request.args.get("scope", "1"))
    rows = ImportMapping.query.filter_by(user_id=user.id, scope=scope).all()
    rows.sort(key=lambda m: (m.last_used_at or m.updated_at or m.created_at).isoformat() if (
        m.last_used_at or m.updated_at or m.created_at) else "", reverse=True)
    return jsonify([m.to_dict() for m in rows])


@emissions_bp.route("/upload/mappings", methods=["POST"])
@login_required
def save_import_mapping():
    """Save (or replace, by name) a column mapping: {scope, name, headers: [...], mapping: {field: column}}."""
    import json

    from models import ImportMapping

    user = get_current_user()
    data = request.get_json(silent=True) or {}
    scope = str(data.get("scope", "1"))
    name = str(data.get("name") or "").strip()
    headers = data.get("headers")
    mapping = data.get("mapping")
    if scope not in _MAPPING_SCOPES:
        return jsonify({"error": f"Unknown import type '{scope}'"}), 400
    if not name or len(name) > 80:
        return jsonify({"error": "Give the mapping a name (80 characters at most)"}), 400
    if not isinstance(headers, list) or not headers or len(headers) > 500 or not all(
            isinstance(h, str) and len(h) <= 200 for h in headers):
        return jsonify({"error": "headers must be the file's column names"}), 400
    if not isinstance(mapping, dict) or not mapping or len(mapping) > 500:
        return jsonify({"error": "mapping must be an object of field -> column"}), 400
    clean = {}
    for k, v in mapping.items():
        if not (isinstance(k, str) and isinstance(v, str) and len(k) <= 100):
            return jsonify({"error": "mapping must be an object of field -> column"}), 400
        if v:
            if v not in headers:
                return jsonify({"error": f"Column '{v}' is not one of the file's columns"}), 400
            clean[k] = v
    if not clean:
        return jsonify({"error": "The mapping has no matched column"}), 400

    row = ImportMapping.query.filter_by(user_id=user.id, scope=scope, name=name).first()
    if row is None:
        if ImportMapping.query.filter_by(user_id=user.id).count() >= MAX_SAVED_MAPPINGS:
            return jsonify({"error": f"You have {MAX_SAVED_MAPPINGS} saved mappings: delete one first"}), 400
        row = ImportMapping(user_id=user.id, scope=scope, name=name)
        db.session.add(row)
    row.headers = json.dumps(headers)
    row.mapping = json.dumps(clean)
    from models import utc_now

    row.updated_at = utc_now()
    db.session.commit()
    return jsonify(row.to_dict()), 201


@emissions_bp.route("/upload/mappings/<int:mapping_id>/used", methods=["POST"])
@login_required
def touch_import_mapping(mapping_id):
    """Mark a saved mapping as used (it is then offered first)."""
    from models import ImportMapping, utc_now

    row = ImportMapping.query.filter_by(id=mapping_id, user_id=get_current_user().id).first()
    if row is None:
        return jsonify({"error": "Not found"}), 404
    row.last_used_at = utc_now()
    db.session.commit()
    return jsonify(row.to_dict())


@emissions_bp.route("/upload/mappings/<int:mapping_id>", methods=["DELETE"])
@login_required
def delete_import_mapping(mapping_id):
    from models import ImportMapping

    row = ImportMapping.query.filter_by(id=mapping_id, user_id=get_current_user().id).first()
    if row is None:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"deleted": mapping_id})


def _job_visible(job_id):
    """BUG-076: a bulk job is readable by its uploader, or by an admin; others get 404."""
    from background_processor import get_job_owner

    user = get_current_user()
    owner = get_job_owner(job_id)
    return user is not None and owner is not None and (owner == user.id or user.role == "admin")


@emissions_bp.route("/upload/status/<job_id>", methods=["GET"])
@login_required
def upload_status(job_id):
    status = get_job_status(job_id) if _job_visible(job_id) else None
    if not status:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(status)


@emissions_bp.route("/upload/errors/<job_id>", methods=["GET"])
@login_required
def upload_errors(job_id):
    from background_processor import get_job_error_csv_path

    path = get_job_error_csv_path(job_id) if _job_visible(job_id) else None
    if not path:
        return jsonify({"error": "No errors file found"}), 404
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
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to record emission")
        return jsonify({"error": "Failed to record emission"}), 500
    try:
        from routes.dashboard import clear_dashboard_cache

        clear_dashboard_cache()  # BUG-071: flushed rows are invisible to the before_commit hook
    except Exception:
        pass

    facility = db.session.get(Facility, data.get("facility_id"))
    facility_name = facility.name if facility else "Unknown"

    # --- Audit Log ---
    try:
        log_details = f"Added {record.process_type} emission: {record.quantity} {record.unit} of {record.fuel_type} for {facility_name} ({record.month}/{record.year})"
        log_activity_and_notify(
            action="CREATE",
            record_id=str(record_id_val),
            user=user,
            request=request,
            entity="Emission",
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
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.warning(f"Audit Log Error: {e}")

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
                        # EXTRA-08 FIX: Deduplicate — only create a new notification if
                        # an unread notification of the same type and year doesn't exist.
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
                            db.session.commit()
                        elif existing.message != msg:
                            # keep the unread notice current: it quoted the total at the time it was
                            # first raised (browser test: 660,945 t while the year stood at 891,521 t)
                            existing.message = msg
                            db.session.commit()
    except Exception as e:
        current_app.logger.warning(f"Notification check error: {e}")

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

    record = Emission.query.filter_by(record_id=id).first() or db.session.get(
        Emission, int(id) if str(id).isdigit() else -1
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

    data = request.get_json()  # EXTRA-03 FIX: removed duplicate call below
    record = Emission.query.filter_by(record_id=id).first() or db.session.get(
        Emission, int(id) if str(id).isdigit() else -1
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


@emissions_bp.route("/import", methods=["POST"])
@login_required  # SEC-01 FIX: was missing
def import_emissions():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return (
            jsonify(
                {"error": "Forbidden: IT personnel cannot access operational emission data"}
            ),
            403,
        )

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

            # CSV templates use '-' for empty optional fields
            for key in list(rec_data.keys()):
                if rec_data.get(key) == "-":
                    rec_data[key] = None

            # RC-6: same validation, factor resolution and persistence as the manual form
            from calculations.anomaly import plausibility_check
            from input_validation import ValidationError, parse_month, parse_year
            from services.scope1_calc import apply_result, canonicalize, resolve_factor, validate_activity
            from utils import user_label

            FUEL_ALIASES = {
                "Diesel": "Diesel (No. 2 Fuel Oil)",
                "No. 2 Diesel": "Diesel (No. 2 Fuel Oil)",
                "Gasoline": "Motor Gasoline",
                "Petrol": "Motor Gasoline",
            }
            try:
                rec_data["year"] = parse_year(rec_data.get("year"))
                rec_data["month"] = parse_month(rec_data.get("month"), required=True)
                rec_data["process_type"] = rec_data.get("process_type") or rec_data.get("type")
                fuel_key = rec_data.get("fuel") or rec_data.get("fuel_type")
                if fuel_key in FUEL_ALIASES:
                    rec_data["fuel"] = rec_data["fuel_type"] = FUEL_ALIASES[fuel_key]
                rec_data = canonicalize(rec_data)
                validate_activity(rec_data, require_unit=str(rec_data.get("factor_source") or "default").lower() in ("default", "custom"))
                factor_data = resolve_factor(rec_data)
                if factor_data.get("hhv") and not rec_data.get("hhv"):
                    rec_data["hhv"] = factor_data["hhv"]
                gwp_dict = resolve_gwp_dict(user)
                gwp_std = resolve_gwp_standard(user)
                em_result, method = compute_emissions(rec_data, factor_data, gwp_dict=gwp_dict)
            except ValueError as err:
                errors.append(f"Row {i}: {getattr(err, 'message', None) or err}")
                continue
            verdict, qa_msg = plausibility_check(em_result["totalCo2e"])
            if verdict == "reject":
                errors.append(f"Row {i}: {qa_msg}")
                continue

            record = Emission(
                record_id=f"IMP-{uuid.uuid4().hex[:8]}-{i}",
                year=rec_data["year"],
                month=rec_data["month"],
                facility_id=facility.id,
                group_name=rec_data["group_name"],
                activity=rec_data["activity"],
                division=rec_data["division"],
                field=rec_data["field"],
                equipment_id=rec_data.get("equipment_id"),
                created_by=user.id,
                created_by_name=user_label(user),
                factor_source=rec_data.get("factor_source") or "default",
                qa_flag=qa_msg[:255] if qa_msg else None,
                status="Pending",  # D-04: all bulk imports queue as Pending
                approved_by=None,
                approved_at=None,
            )
            apply_result(record, rec_data, em_result, method, factor_data, gwp_std)
            record.ogmp_level = ogmp_level_for(record)
            db.session.add(record)
            imported_count += 1
        except Exception:
            current_app.logger.exception("Import row %s failed", i)
            errors.append(f"Row {i}: could not be processed")  # BUG-087: no raw exception text

    current_app.logger.info(
        f"Import summary: imported={imported_count}, errors={len(errors)}"
    )
    if errors and imported_count == 0:
        db.session.rollback()
        return jsonify({"error": "Import failed", "details": errors}), 400

    if imported_count > 0:
        # audit entry + reviewer notifications commit atomically with the data (project convention)
        log_activity_and_notify(
            action="IMPORT",
            record_id=f"BATCH-{imported_count}",
            user=user,
            request=request,
            entity="Emission",
            details=f"Bulk imported {imported_count} emission records (status: Pending)",
        )
        for admin in User.query.filter_by(role="admin", status="active").all():
            if admin.id == user.id:
                continue
            Notification.create(
                user_id=admin.id,
                type="warning",
                title="Bulk Emission Records Awaiting Approval",
                message=f"{user.fullName or user.email} imported {imported_count} emission records that require verification.",
                metadata={"imported_count": imported_count, "uploader_id": user.id},
            )
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()

    return jsonify(
        {
            "message": f"{imported_count} records imported",
            "imported": imported_count,
            "status": "Pending",
            "errors": errors,
        }
    )


def _safe_excel_value(val):
    """Prevent formula injection (DDE/CSV injection) in Excel cells."""
    if isinstance(val, str) and val and val[0] in ("=", "-", "+", "@", "\t", "\r"):
        return "'" + val
    return val


@emissions_bp.route("/export", methods=["GET"])
@login_required  # SEC-01 FIX: was missing
def export_emissions():
    """Export emissions data as Excel (.xlsx) or JSON format with full filter support."""
    from flask import send_file
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return (
            jsonify(
                {"error": "Forbidden: IT personnel cannot access operational emission data"}
            ),
            403,
        )

    allowed_ids = get_allowed_facility_ids(user)

    # Extract query parameters
    scope = request.args.get("scope", "all")
    year_arg = request.args.get("year")
    month_arg = request.args.get("month")
    facility_arg = request.args.get("facilityId") or request.args.get("facility_id")
    process_arg = request.args.get("process") or request.args.get("process_type")
    division_arg = request.args.get("division")
    field_arg = request.args.get("field")
    method_arg = request.args.get("method")
    search_arg = request.args.get("search")
    export_format = request.args.get("format", "json").lower()

    # Parse numeric filters safely
    year_int = None
    if year_arg and year_arg != "all":
        try:
            year_int = int(year_arg)
        except (ValueError, TypeError):
            pass

    month_int = None
    if month_arg and month_arg != "all":
        try:
            month_int = int(month_arg)
        except (ValueError, TypeError):
            pass

    facility_int = None
    if facility_arg and facility_arg != "all":
        try:
            facility_int = int(facility_arg)
        except (ValueError, TypeError):
            pass

    if facility_int is not None and allowed_ids is not None and facility_int not in allowed_ids:
        return jsonify({"error": "Unauthorized facility"}), 403

    # Batch facility lookup to prevent N+1 queries
    all_facs = {f.id: f for f in Facility.query.all()}

    export_data = []

    # 1. SCOPE 1
    if scope in ["all", "1", "scope1"]:
        q1 = Emission.query.filter(Emission.status == "Verified")
        if allowed_ids is not None:
            q1 = q1.filter(Emission.facility_id.in_(allowed_ids))
        if year_int:
            q1 = q1.filter(Emission.year == year_int)
        if month_int:
            q1 = q1.filter(Emission.month == month_int)
        if facility_int:
            q1 = q1.filter(Emission.facility_id == facility_int)
        if process_arg and process_arg != "all":
            q1 = q1.filter(Emission.process_type == process_arg)
        if division_arg and division_arg != "all":
            q1 = q1.filter(Emission.division.ilike(f"%{_escape_like(division_arg.strip())}%", escape="\\"))
        if field_arg and field_arg != "all":
            q1 = q1.filter(Emission.field.ilike(f"%{_escape_like(field_arg.strip())}%", escape="\\"))
        if method_arg and method_arg != "all":
            q1 = q1.filter(Emission.calc_method.ilike(f"%{_escape_like(method_arg.strip())}%", escape="\\"))
        if search_arg:
            safe_s = _escape_like(search_arg.strip())
            q1 = q1.filter(
                or_(
                    Emission.process_type.ilike(f"%{safe_s}%", escape="\\"),
                    Emission.fuel_type.ilike(f"%{safe_s}%", escape="\\"),
                    Emission.equipment_id.ilike(f"%{safe_s}%", escape="\\"),
                    Emission.group_name.ilike(f"%{safe_s}%", escape="\\"),
                )
            )

        for r in q1.order_by(Emission.year.desc(), Emission.month.desc()).all():
            fac = all_facs.get(r.facility_id)
            export_data.append(
                {
                    "record_id": r.record_id or f"S1-{r.id}",
                    "scope": 1,
                    "year": r.year,
                    "month": r.month,
                    "facility": fac.name if fac else (r.facility.name if r.facility else "Unknown"),
                    "division": r.division or (fac.division if fac else ""),
                    "field": r.field or (fac.field if fac else ""),
                    "group": r.group_name or "N/A",
                    "process": r.process_type or "N/A",
                    "fuel": r.fuel_type or "N/A",
                    "quantity": float(r.quantity or 0),
                    "unit": r.unit or "",
                    "co2": float(r.co2_emissions or 0),
                    "ch4": float(r.ch4_emissions or 0),
                    "n2o": float(r.n2o_emissions or 0),
                    "co2e_total": float(r.co2e_total or 0),
                    "status": r.status or "Verified",
                }
            )

    # 2. SCOPE 2
    if scope in ["all", "2", "scope2"]:
        q2 = Scope2Emission.query.filter(Scope2Emission.status == "Verified")
        if allowed_ids is not None:
            q2 = q2.filter(Scope2Emission.facility_id.in_(allowed_ids))
        if year_int:
            q2 = q2.filter(Scope2Emission.year == year_int)
        if month_int:
            q2 = q2.filter(Scope2Emission.month == month_int)
        if facility_int:
            q2 = q2.filter(Scope2Emission.facility_id == facility_int)
        if division_arg and division_arg != "all":
            q2 = q2.filter(Scope2Emission.division.ilike(f"%{_escape_like(division_arg.strip())}%", escape="\\"))
        if field_arg and field_arg != "all":
            q2 = q2.filter(Scope2Emission.field.ilike(f"%{_escape_like(field_arg.strip())}%", escape="\\"))
        if search_arg:
            safe_s = _escape_like(search_arg.strip())
            q2 = q2.filter(
                or_(
                    Scope2Emission.activity.ilike(f"%{safe_s}%", escape="\\"),
                    Scope2Emission.grid_region.ilike(f"%{safe_s}%", escape="\\"),
                )
            )

        for r in q2.order_by(Scope2Emission.year.desc(), Scope2Emission.month.desc()).all():
            fac = all_facs.get(r.facility_id)
            export_data.append(
                {
                    "record_id": f"S2-{r.id}",
                    "scope": 2,
                    "year": r.year,
                    "month": r.month,
                    "facility": fac.name if fac else "Unknown",
                    "division": r.division or (fac.division if fac else ""),
                    "field": r.field or (fac.field if fac else ""),
                    "group": "N/A",
                    "process": f"Scope 2: {r.source_type or 'Electricity'}",
                    "fuel": scope2_activity(r)[2],
                    "quantity": scope2_activity(r)[0],
                    "unit": scope2_activity(r)[1],
                    "co2": 0.0,
                    "ch4": 0.0,
                    "n2o": 0.0,
                    "co2e_total": float(r.co2e or 0),
                    "status": r.status or "Verified",
                }
            )

    # 3. SCOPE 3
    if scope in ["all", "3", "scope3"]:
        q3 = Scope3Emission.query.filter(Scope3Emission.status == "Verified")
        if allowed_ids is not None:
            q3 = q3.filter(Scope3Emission.facility_id.in_(allowed_ids))
        if year_int:
            q3 = q3.filter(Scope3Emission.year == year_int)
        if month_int:
            q3 = q3.filter(Scope3Emission.month == month_int)
        if facility_int:
            q3 = q3.filter(Scope3Emission.facility_id == facility_int)
        if search_arg:
            safe_s = _escape_like(search_arg.strip())
            q3 = q3.filter(
                or_(
                    Scope3Emission.category.ilike(f"%{safe_s}%", escape="\\"),
                    Scope3Emission.sub_category.ilike(f"%{safe_s}%", escape="\\"),
                )
            )

        for r in q3.order_by(Scope3Emission.year.desc(), Scope3Emission.month.desc()).all():
            fac = all_facs.get(r.facility_id)
            export_data.append(
                {
                    "record_id": f"S3-{r.id}",
                    "scope": 3,
                    "year": r.year,
                    "month": r.month,
                    "facility": fac.name if fac else "Unknown",
                    "division": fac.division if fac else "",
                    "field": fac.field if fac else "",
                    "group": "N/A",
                    "process": r.category or "Value Chain",
                    "fuel": r.sub_category or "Scope 3",
                    "quantity": float(r.activity_data or 0),
                    "unit": r.unit or "",
                    "co2": 0.0,
                    "ch4": 0.0,
                    "n2o": 0.0,
                    "co2e_total": float(r.co2e or 0),
                    "status": r.status or "Verified",
                }
            )

    # Return Excel workbook if requested
    if export_format == "excel":
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove initial blank sheet

        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        summary_hdr_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid")
        total_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=15, bold=True, color="1E293B")
        bold_font = Font(name="Calibri", size=11, bold=True)
        regular_font = Font(name="Calibri", size=11)
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0"),
        )
        double_bottom_border = Border(
            top=Side(style="thin", color="94A3B8"),
            bottom=Side(style="double", color="1E293B"),
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
        )

        # ─── Sheet 1: Detailed Inventory ───
        ws1 = wb.create_sheet(title="Emissions Inventory")
        ws1.views.sheetView[0].showGridLines = True

        ws1.cell(row=1, column=1, value="GHG EMISSIONS INVENTORY DISCLOSURE").font = title_font
        subtitle = (
            f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
            f"Scope: {scope.upper()} | Year: {year_arg or 'All'} | Month: {month_arg or 'All'} | "
            f"Facility: {all_facs.get(facility_int).name if facility_int and facility_int in all_facs else 'All'}"
        )
        ws1.cell(row=2, column=1, value=subtitle).font = regular_font

        headers = [
            "Record ID",
            "Scope",
            "Year",
            "Month",
            "Facility",
            "Division",
            "Field",
            "Group",
            "Category / Process",
            "Fuel / Source",
            "Quantity",
            "Unit",
            "CO₂ (t)",
            "CH₄ (t)",
            "N₂O (t)",
            "Total CO₂e (t)",
            "Status",
        ]

        for col_idx, h in enumerate(headers, 1):
            cell = ws1.cell(row=4, column=col_idx, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        row_num = 5
        total_qty = 0.0
        total_co2 = 0.0
        total_ch4 = 0.0
        total_n2o = 0.0
        total_co2e = 0.0

        for item in export_data:
            total_qty += item["quantity"]
            total_co2 += item["co2"]
            total_ch4 += item["ch4"]
            total_n2o += item["n2o"]
            total_co2e += item["co2e_total"]

            ws1.cell(row=row_num, column=1, value=_safe_excel_value(item["record_id"]))
            ws1.cell(row=row_num, column=2, value=f"Scope {item['scope']}")
            ws1.cell(row=row_num, column=3, value=item["year"])
            ws1.cell(row=row_num, column=4, value=item["month"])
            ws1.cell(row=row_num, column=5, value=_safe_excel_value(item["facility"]))
            ws1.cell(row=row_num, column=6, value=_safe_excel_value(item["division"]))
            ws1.cell(row=row_num, column=7, value=_safe_excel_value(item["field"]))
            ws1.cell(row=row_num, column=8, value=_safe_excel_value(item["group"]))
            ws1.cell(row=row_num, column=9, value=_safe_excel_value(item["process"]))
            ws1.cell(row=row_num, column=10, value=_safe_excel_value(item["fuel"]))

            c_qty = ws1.cell(row=row_num, column=11, value=round(item["quantity"], 2))
            c_qty.number_format = "#,##0.00"
            c_qty.alignment = Alignment(horizontal="right")

            ws1.cell(row=row_num, column=12, value=_safe_excel_value(item["unit"]))

            c_co2 = ws1.cell(row=row_num, column=13, value=round(item["co2"], 2))
            c_co2.number_format = "#,##0.00"
            c_co2.alignment = Alignment(horizontal="right")

            c_ch4 = ws1.cell(row=row_num, column=14, value=round(item["ch4"], 2))
            c_ch4.number_format = "#,##0.00"
            c_ch4.alignment = Alignment(horizontal="right")

            c_n2o = ws1.cell(row=row_num, column=15, value=round(item["n2o"], 2))
            c_n2o.number_format = "#,##0.00"
            c_n2o.alignment = Alignment(horizontal="right")

            c_tot = ws1.cell(row=row_num, column=16, value=round(item["co2e_total"], 2))
            c_tot.number_format = "#,##0.00"
            c_tot.alignment = Alignment(horizontal="right")
            c_tot.font = bold_font

            ws1.cell(row=row_num, column=17, value=_safe_excel_value(item["status"]))

            for c in range(1, len(headers) + 1):
                ws1.cell(row=row_num, column=c).border = thin_border
            row_num += 1

        # Totals row
        ws1.cell(row=row_num, column=1, value="TOTALS").font = bold_font
        for c in range(1, len(headers) + 1):
            cell = ws1.cell(row=row_num, column=c)
            cell.fill = total_fill
            cell.border = double_bottom_border

        # quantities are in different units (kWh, m3, bbl, devices...): they are not summed
        ws1.cell(row=row_num, column=11, value="—").alignment = Alignment(horizontal="right")

        cell_t_co2 = ws1.cell(row=row_num, column=13, value=round(total_co2, 2))
        cell_t_co2.number_format = "#,##0.00"
        cell_t_co2.font = bold_font

        cell_t_ch4 = ws1.cell(row=row_num, column=14, value=round(total_ch4, 2))
        cell_t_ch4.number_format = "#,##0.00"
        cell_t_ch4.font = bold_font

        cell_t_n2o = ws1.cell(row=row_num, column=15, value=round(total_n2o, 2))
        cell_t_n2o.number_format = "#,##0.00"
        cell_t_n2o.font = bold_font

        cell_t_co2e = ws1.cell(row=row_num, column=16, value=round(total_co2e, 2))
        cell_t_co2e.number_format = "#,##0.00"
        cell_t_co2e.font = bold_font

        # Autofit columns
        for col in ws1.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if "\n" in val_str:
                    val_str = max(val_str.split("\n"), key=len)
                max_len = max(max_len, len(val_str))
            ws1.column_dimensions[col_letter].width = max(max_len + 4, 11)

        # ─── Sheet 2: Executive Summary ───
        ws2 = wb.create_sheet(title="Executive Summary")
        ws2.views.sheetView[0].showGridLines = True
        ws2.cell(row=1, column=1, value="EMISSION SCOPE BREAKDOWN & SUMMARY").font = title_font

        s1_sum = sum(i["co2e_total"] for i in export_data if i["scope"] == 1)
        s2_sum = sum(i["co2e_total"] for i in export_data if i["scope"] == 2)
        s3_sum = sum(i["co2e_total"] for i in export_data if i["scope"] == 3)

        sum_headers = ["Metric / Scope", "Value", "Unit"]
        for col_idx, h in enumerate(sum_headers, 1):
            cell = ws2.cell(row=3, column=col_idx, value=h)
            cell.fill = summary_hdr_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        summary_rows = [
            ("Scope 1 — Direct Operational Emissions", s1_sum, "tCO₂e"),
            ("Scope 2 — Indirect Energy (electricity, steam, heat, cooling)", s2_sum, "tCO₂e"),
            ("Scope 3 — Value Chain Emissions", s3_sum, "tCO₂e"),
            ("Grand Total CO₂e Footprint", total_co2e, "tCO₂e"),
            ("Total CO₂ Gas Mass", total_co2, "tonnes CO₂"),
            ("Total CH₄ Gas Mass", total_ch4, "tonnes CH₄"),
            ("Total N₂O Gas Mass", total_n2o, "tonnes N₂O"),
            ("Total Record Count", len(export_data), "records"),
        ]

        for s_idx, (label, val, unit) in enumerate(summary_rows, 4):
            ws2.cell(row=s_idx, column=1, value=label).font = (
                bold_font if "Grand Total" in label or "Scope" in label else regular_font
            )
            val_cell = ws2.cell(row=s_idx, column=2, value=round(val, 2) if isinstance(val, float) else val)
            if isinstance(val, (int, float)):
                val_cell.number_format = "#,##0.00" if isinstance(val, float) else "#,##0"
            val_cell.font = bold_font if "Grand Total" in label else regular_font
            val_cell.alignment = Alignment(horizontal="right")
            ws2.cell(row=s_idx, column=3, value=unit).font = regular_font

            for c in range(1, 4):
                ws2.cell(row=s_idx, column=c).border = thin_border
            if "Grand Total" in label:
                for c in range(1, 4):
                    ws2.cell(row=s_idx, column=c).fill = total_fill

        for col in ws2.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                max_len = max(max_len, len(str(cell.value or "")))
            ws2.column_dimensions[col_letter].width = max(max_len + 4, 15)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        year_lbl = year_arg if year_arg and year_arg != "all" else "all"
        month_lbl = month_arg if month_arg and month_arg != "all" else "all"
        fname = f"emissions_{year_lbl}_{month_lbl}.xlsx"
        return send_file(
            buf,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=fname,
        )

    return jsonify({"data": export_data, "count": len(export_data)})


# ─── Maker-Checker Approval ───────────────────────────────────────────────────

@emissions_bp.route("/approve/<int:emission_id>", methods=["POST"])
@login_required
def approve_emission(emission_id):
    """Approve a single record awaiting review (Scope 1, 2, 3 or CAP) — RC-2 state machine."""
    from services.maker_checker import DecisionError, decide_single

    req_data = request.get_json(silent=True) or {}
    scope = str(req_data.get("scope") or request.args.get("scope") or "1")
    try:
        decide_single(get_current_user(), scope, emission_id, "approve", request=request)
    except DecisionError as err:
        db.session.rollback()
        return jsonify({"error": err.message}), err.status
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    return jsonify({"success": True, "id": emission_id, "scope": scope, "status": "Verified"})


@emissions_bp.route("/reject/<int:emission_id>", methods=["POST"])
@login_required
def reject_emission(emission_id):
    """Reject a single record awaiting review; decided records cannot be flipped (BUG-070)."""
    from services.maker_checker import DecisionError, decide_single

    req_data = request.get_json(silent=True) or {}
    scope = str(req_data.get("scope") or request.args.get("scope") or "1")
    reason = str(req_data.get("reason") or "Rejected by reviewer")
    try:
        decide_single(get_current_user(), scope, emission_id, "reject", reason=reason, request=request)
    except DecisionError as err:
        db.session.rollback()
        return jsonify({"error": err.message}), err.status
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    return jsonify({"success": True, "id": emission_id, "scope": scope, "status": "Rejected", "reason": reason})


def _batch_targets(data, all_flag):
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


def _batch_decide(decision):
    from services.maker_checker import DecisionError, decide

    user = get_current_user()
    data = request.get_json(silent=True) or {}
    all_flag = bool(data.get("approve_all") if decision == "approve" else data.get("reject_all"))
    targets = _batch_targets(data, all_flag)
    if not targets:
        return jsonify({"error": "Provide by_scope ids, a single scope with ids, or scope='all' with the all flag"}), 400
    reason = str(data.get("reason") or "Batch rejected by reviewer")
    done = []
    try:
        for scope, ids in targets.items():
            if ids is not None and not ids:
                continue
            done += decide(user, scope, ids, decision, reason=reason, request=request)
    except DecisionError as err:
        db.session.rollback()
        return jsonify({"error": err.message}), err.status
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    return done


@emissions_bp.route("/approve/batch", methods=["POST"])
@login_required
def approve_batch_emissions():
    """Approve records awaiting review. Body: {by_scope: {"1": [...], ...}} or {scope, ids} or {scope: "all", approve_all: true}.
    Records the caller created or last modified are skipped (segregation of duties)."""
    done = _batch_decide("approve")
    if not isinstance(done, list):
        return done
    return jsonify({"success": True, "approved_count": len(done), "approved_ids": done})


@emissions_bp.route("/reject/batch", methods=["POST"])
@login_required
def reject_batch_emissions():
    """Reject records awaiting review (soft: status Rejected, excluded from totals)."""
    done = _batch_decide("reject")
    if not isinstance(done, list):
        return done
    return jsonify({"success": True, "deleted_count": len(done), "rejected_count": len(done), "rejected_ids": done})


@emissions_bp.route("/erp/sync", methods=["POST"])
@login_required
def trigger_erp_sync():
    """ERP integration endpoint. No ERP connector is implemented: the former "mock" sync inserted three
    invented Scope 3 records (fixed spend, factors and co2e, "SAP Ariba Inv #9921") into the inventory
    when ENABLE_MOCK_ERP was set; it is removed and the endpoint says so."""
    user = get_current_user()
    if not user or user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Admin privileges required for ERP sync"}), 403
    return jsonify({"error": "No ERP connector is configured. Import ERP spend or activity data with the "
                             "Scope 3 file upload."}), 501


@emissions_bp.route("/pending", methods=["GET"])
@login_required
def get_pending_emissions():
    """Get all pending emissions across Scope 1, 2, 3 for the reviewer dashboard.
    Query params: ?all=true (unlimited) or ?limit=200
    """
    user = get_current_user()
    if not user or user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Insufficient permissions"}), 403

    allowed_fids = get_allowed_facility_ids(user)
    # drafts are the maker's unsubmitted work: they enter review only when submitted (browser test)
    pending_statuses = ["Pending", "Pending Approval", "Pending Review"]
    fetch_all = request.args.get("all", "").lower() == "true"
    limit_val = None if fetch_all else int(request.args.get("limit", 200))

    def q_scope1():
        q = Emission.query.filter(Emission.status.in_(pending_statuses))
        if allowed_fids is not None:
            q = q.filter(Emission.facility_id.in_(allowed_fids))
        q = q.order_by(Emission.timestamp.desc())
        if limit_val:
            q = q.limit(limit_val)
        return [
            {
                "id": e.id, "scope": "1", "facility_id": e.facility_id,
                "facility_name": e.facility.name if getattr(e, "facility", None) else None,
                "year": e.year, "month": e.month, "process_type": e.process_type,
                "fuel_type": e.fuel_type, "quantity": e.quantity, "unit": e.unit,
                "co2e_total": e.co2e_total, "status": e.status, 
                "qa_flag": getattr(e, "qa_flag", None),
                "emission_factor": getattr(e, "emission_factor", None),
                "created_by": getattr(e, "created_by", None),
                "created_at": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in q.all()
        ]

    def q_scope2():
        q = Scope2Emission.query.filter(Scope2Emission.status.in_(pending_statuses))
        if allowed_fids is not None:
            q = q.filter(Scope2Emission.facility_id.in_(allowed_fids))
        q = q.order_by(Scope2Emission.created_at.desc())
        if limit_val:
            q = q.limit(limit_val)
        return [
            {
                "id": e.id, "scope": "2", "facility_id": e.facility_id,
                "facility_name": e.facility.name if getattr(e, "facility", None) else None,
                "year": e.year, "month": e.month, "source_type": e.source_type,
                "electricity_kwh": e.electricity_kwh, "heat_mmbtu": getattr(e, "heat_mmbtu", None),
                "co2e": e.co2e, "status": e.status,
                "qa_flag": getattr(e, "qa_flag", None),
                "emission_factor": getattr(e, "emission_factor", None),
                "created_by": getattr(e, "created_by", None),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in q.all()
        ]

    def q_scope3():
        q = Scope3Emission.query.filter(Scope3Emission.status.in_(pending_statuses))
        if allowed_fids is not None:
            q = q.filter(Scope3Emission.facility_id.in_(allowed_fids))
        q = q.order_by(Scope3Emission.created_at.desc())
        if limit_val:
            q = q.limit(limit_val)
        return [
            {
                "id": e.id, "scope": "3", "facility_id": e.facility_id,
                "facility_name": e.facility.name if getattr(e, "facility", None) else None,
                "year": e.year, "month": e.month, "category": e.category,
                "sub_category": getattr(e, "sub_category", None),
                "activity_data": getattr(e, "activity_data", None),
                "unit": getattr(e, "unit", None),
                "co2e": e.co2e, "status": e.status,
                "qa_flag": getattr(e, "qa_flag", None),
                "emission_factor": getattr(e, "emission_factor", None),
                "created_by": getattr(e, "created_by", None),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in q.all()
        ]

    def count_pending(model):
        q = model.query.filter(model.status.in_(pending_statuses))
        if allowed_fids is not None:
            q = q.filter(model.facility_id.in_(allowed_fids))
        return q.count()

    counts = {"1": count_pending(Emission), "2": count_pending(Scope2Emission), "3": count_pending(Scope3Emission)}

    def sum_pending(model, col):
        q = db.session.query(db.func.coalesce(db.func.sum(col), 0.0)).filter(model.status.in_(pending_statuses))
        if allowed_fids is not None:
            q = q.filter(model.facility_id.in_(allowed_fids))
        return float(q.scalar() or 0.0)

    pending_co2e = (sum_pending(Emission, Emission.co2e_total) + sum_pending(Scope2Emission, Scope2Emission.co2e)
                    + sum_pending(Scope3Emission, Scope3Emission.co2e))
    return jsonify({
        "scope1": q_scope1(),
        "scope2": q_scope2(),
        "scope3": q_scope3(),
        # the lists hold at most `limit` rows per scope; the counts are the whole queue
        "pending_counts": counts,
        "pending_co2e": pending_co2e,
        "limit": limit_val,
        "total_pending": sum(counts.values()),
    })

