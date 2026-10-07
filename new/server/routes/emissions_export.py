"""Export route for emission records (CSV and Excel).

Split out of routes/emissions.py unchanged (hardening plan, task 5.3). The routes are
registered on the same ``emissions_bp`` blueprint, so URLs and endpoint names are the same.
"""
import datetime
from flask import jsonify, request
from models import Emission, Facility, Scope2Emission, Scope3Emission
from routes.auth import login_required
from services.labels import process_label, scope2_source_label
from services.scope2_activity import scope2_activity
from sqlalchemy import or_
from utils import get_allowed_facility_ids, get_current_user
from . import emissions_bp
from routes.emissions import _escape_like


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
                    "process": process_label(r.process_type, "N/A"),
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
                    "process": f"Scope 2: {scope2_source_label(r.source_type)}",
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
