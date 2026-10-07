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
        from sqlalchemy import or_

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

        # Scope filters for SQL
        y_int = None
        if year and year != "all":
            try:
                y_int = int(year)
            except:
                pass

        m_int = None
        if month and month != "all":
            try:
                m_int = int(month)
            except:
                pass

        f_int = None
        if facility_id and facility_id != "all":
            try:
                f_int = int(facility_id)
            except:
                pass

        if f_int is not None and allowed_fids is not None and f_int not in allowed_fids:
            return jsonify({"error": "Unauthorized facility"}), 403

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
            if division and division != "all":
                q1 = q1.filter(Emission.division.ilike(f"%{division.strip()}%"))
            if field and field != "all":
                q1 = q1.filter(Emission.field.ilike(f"%{field.strip()}%"))
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
        if scope in ["all", "2", "scope2"]:
            q2 = Scope2Emission.query
            if y_int:
                q2 = q2.filter_by(year=y_int)
            if m_int:
                q2 = q2.filter_by(month=m_int)
            if f_int:
                q2 = q2.filter_by(facility_id=f_int)
            elif allowed_fids is not None:
                q2 = q2.filter(Scope2Emission.facility_id.in_(allowed_fids))
            if division and division != "all":
                q2 = q2.filter(Scope2Emission.division.ilike(f"%{division.strip()}%"))
            if field and field != "all":
                q2 = q2.filter(Scope2Emission.field.ilike(f"%{field.strip()}%"))
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
        if scope in ["all", "3", "scope3"]:
            q3 = Scope3Emission.query
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
                        "process_type": e.category or "Value Chain",
                        "fuel_type": e.sub_category or "Scope 3",
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

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as e:
        current_app.logger.error(f"Error exporting emissions: {e}", exc_info=True)
        return (
            jsonify(
                {"error": "Report export failed. Please try again or contact support."}
            ),
            500,
        )
