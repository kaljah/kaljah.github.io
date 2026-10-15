"""Emission record export route for the reports page.

Split out of routes/reports.py unchanged (hardening plan, task 5.3). The routes are
registered on the same ``reports_bp`` blueprint, so URLs and endpoint names are the same.
"""
from flask import current_app, jsonify, request, send_file
from models import Emission, Facility
from routes.auth import login_required
from services.labels import process_label, scope2_source_label
from services.scope2_activity import scope2_activity
from utils import get_allowed_facility_ids, get_current_user
from routes.reports import create_pdf_report, reports_bp
from services.audit_chain import record_report_fingerprint


@reports_bp.route("/export", methods=["GET"])
@login_required
def export_emissions():
    """Export emissions data as PDF - GET version for frontend integration"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return (
            jsonify(
                {"error": "Forbidden: IT personnel cannot access operational emission reports"}
            ),
            403,
        )

    try:
        from models import Scope2Emission, Scope3Emission
        from sqlalchemy import func, or_

        allowed_fids = get_allowed_facility_ids(user)

        # Get query parameters
        year = request.args.get("year")
        month = request.args.get("month")
        facility_id = request.args.get("facility_id") or request.args.get("facilityId")
        process_type = request.args.get("process_type") or request.args.get("process")
        division = request.args.get("division")
        field = request.args.get("field")
        method = request.args.get("method")
        search = request.args.get("search")
        scope = request.args.get("scope", "all")

        filters = {
            "year": year,
            "month": month,
            "facility_id": facility_id,
            "process_type": process_type,
            "division": division,
            "field": field,
            "method": method,
            "search": search,
            "scope": scope,
        }

        emissions_data = []

        # Scope filters for SQL. Audit 2026-10-14 BUG-0034: a malformed filter is refused (it was ignored
        # and the PDF silently covered every year / facility).
        def _filter(value, name, low, high):
            if not value or value == "all":
                return None
            text = str(value).strip()
            if not text.isdigit() or not low <= int(text) <= high:
                raise ValueError(f"Invalid {name} filter: '{value}'")
            return int(text)

        try:
            y_int = _filter(year, "year", 1900, 2200)
            m_int = _filter(month, "month", 1, 12)
            f_int = _filter(facility_id, "facility_id", 1, 2**31 - 1)
        except ValueError as err:
            return jsonify({"error": str(err)}), 400

        if f_int is not None and allowed_fids is not None and f_int not in allowed_fids:
            return jsonify({"error": "Unauthorized facility"}), 403
        division_f = division.strip().lower() if division and division.strip().lower() != "all" else None
        field_f = field.strip().lower() if field and field.strip().lower() != "all" else None

        # Batch facility lookup to prevent N+1 queries
        fac_map = {f.id: f.name for f in Facility.query.all()}

        # 1. SCOPE 1
        if scope in ["all", "1", "scope1"]:
            q1 = Emission.query
            if y_int:
                q1 = q1.filter_by(year=y_int)
            if m_int:
                q1 = q1.filter_by(month=m_int)
            if f_int:
                q1 = q1.filter_by(facility_id=f_int)
            elif allowed_fids is not None:
                q1 = q1.filter(Emission.facility_id.in_(allowed_fids))
            if process_type and process_type != "all":
                q1 = q1.filter_by(process_type=process_type)
            # bug hunt 2026-10-15 #37: division / field match exactly (case-insensitive); "Sud" matched "Sud-Est"
            if division_f:
                q1 = q1.filter(func.lower(Emission.division) == division_f)
            if field_f:
                q1 = q1.filter(func.lower(Emission.field) == field_f)
            if method and method != "all":
                q1 = q1.filter(Emission.calc_method.ilike(f"%{method.strip()}%"))
            if search:
                s_term = search.strip()
                q1 = q1.filter(
                    or_(
                        Emission.process_type.ilike(f"%{s_term}%"),
                        Emission.fuel_type.ilike(f"%{s_term}%"),
                        Emission.equipment_id.ilike(f"%{s_term}%"),
                        Emission.group_name.ilike(f"%{s_term}%"),
                    )
                )
            q1 = q1.filter(Emission.status == "Verified")
            for e in q1.all():
                m_val = e.month if e.month is not None else 1
                emissions_data.append(
                    {
                        "scope": 1,
                        "date": f"{e.year or 0}-{m_val:02d}-01",
                        "facility_name": fac_map.get(e.facility_id, "Unknown"),
                        "process_type": process_label(e.process_type, "N/A"),
                        "fuel_type": e.fuel_type or "N/A",
                        "amount": e.quantity or 0,
                        "unit": e.unit or "",
                        "co2_emissions": e.co2_emissions or 0,
                        "ch4_emissions": e.ch4_emissions or 0,
                        "n2o_emissions": e.n2o_emissions or 0,
                        "total_co2e": e.co2e_total or 0,
                    }
                )

        # 2. SCOPE 2
        # a process or calculation-method filter selects Scope 1 records: Scope 2 / 3 have neither (#37)
        scope1_only = bool((process_type and process_type != "all") or (method and method != "all"))
        if scope in ["all", "2", "scope2"] and not scope1_only:
            q2 = Scope2Emission.query
            if y_int:
                q2 = q2.filter_by(year=y_int)
            if m_int:
                q2 = q2.filter_by(month=m_int)
            if f_int:
                q2 = q2.filter_by(facility_id=f_int)
            elif allowed_fids is not None:
                q2 = q2.filter(Scope2Emission.facility_id.in_(allowed_fids))
            if division_f:
                q2 = q2.filter(func.lower(Scope2Emission.division) == division_f)
            if field_f:
                q2 = q2.filter(func.lower(Scope2Emission.field) == field_f)
            if search:
                s_term = search.strip()
                q2 = q2.filter(
                    or_(
                        Scope2Emission.activity.ilike(f"%{s_term}%"),
                        Scope2Emission.grid_region.ilike(f"%{s_term}%"),
                    )
                )
            q2 = q2.filter(Scope2Emission.status == "Verified")
            for e in q2.all():
                m_val = e.month if e.month is not None else 1
                s2_amount, s2_unit, _s2_label = scope2_activity(e)
                emissions_data.append(
                    {
                        "scope": 2,
                        "date": f"{e.year or 0}-{m_val:02d}-01",
                        "facility_name": fac_map.get(e.facility_id, "Unknown"),
                        "process_type": f"Scope 2: {scope2_source_label(e.source_type)}",
                        "fuel_type": _s2_label,
                        "amount": s2_amount,
                        "unit": s2_unit,
                        "co2_emissions": 0,
                        "ch4_emissions": 0,
                        "n2o_emissions": 0,
                        "total_co2e": e.co2e or 0,
                        "co2e_location_based": e.co2e_location_based if e.co2e_location_based is not None else (e.co2e or 0),
                        "co2e_market_based": e.co2e_market_based if e.co2e_market_based is not None else (e.co2e or 0),
                        "market_instrument_type": e.market_instrument_type,
                    }
                )

        # 3. SCOPE 3
        if scope in ["all", "3", "scope3"] and not scope1_only:
            q3 = Scope3Emission.query
            # Scope 3 records carry no division / field: those of their facility (they were ignored)
            if division_f or field_f:
                fq = Facility.query
                if division_f:
                    fq = fq.filter(func.lower(Facility.division) == division_f)
                if field_f:
                    fq = fq.filter(func.lower(Facility.field) == field_f)
                q3 = q3.filter(Scope3Emission.facility_id.in_([f.id for f in fq.all()] or [-1]))
            if y_int:
                q3 = q3.filter_by(year=y_int)
            if m_int:
                q3 = q3.filter_by(month=m_int)
            if f_int:
                q3 = q3.filter_by(facility_id=f_int)
            elif allowed_fids is not None:
                q3 = q3.filter(Scope3Emission.facility_id.in_(allowed_fids))
            if search:
                s_term = search.strip()
                q3 = q3.filter(
                    or_(
                        Scope3Emission.category.ilike(f"%{s_term}%"),
                        Scope3Emission.sub_category.ilike(f"%{s_term}%"),
                    )
                )
            q3 = q3.filter(Scope3Emission.status == "Verified")
            for e in q3.all():
                m_val = e.month if e.month is not None else 1
                emissions_data.append(
                    {
                        "scope": 3,
                        "date": f"{e.year or 0}-{m_val:02d}-01",
                        "facility_name": fac_map.get(e.facility_id, "Unknown"),
                        "process_type": str(getattr(e, "category", None) or "Scope 3"),
                        "fuel_type": str(getattr(e, "sub_category", None) or "Value Chain"),
                        "amount": e.activity_data or 0,
                        "unit": e.unit or "",
                        "co2_emissions": 0,
                        "ch4_emissions": 0,
                        "n2o_emissions": 0,
                        "total_co2e": e.co2e or 0,
                    }
                )

        emissions_data.sort(key=lambda x: x["date"], reverse=True)

        # Generate PDF
        pdf_buffer = create_pdf_report(emissions_data, filters)

        # Return PDF file
        year_str = year if year and year != "all" else "all"
        month_str = month if month and month != "all" else "all"
        filename = f"emissions_{year_str}_{month_str}.pdf"

        resp = send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)
        return record_report_fingerprint(resp, user, "PDF export", filters, len(emissions_data), pdf_buffer.report_hash)

    except Exception as e:
        current_app.logger.error(f"Error exporting emissions: {e}", exc_info=True)
        return (
            jsonify(
                {"error": "Report export failed. Please try again or contact support."}
            ),
            500,
        )
