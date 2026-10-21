"""
Executive Master Report & Intelligence Studio Endpoints
======================================================
Provides publication-grade reporting endpoints:
1. POST /api/reports/master-report (streams 300 DPI executive PDF report)
2. GET /api/reports/master-report/regions (available regions and assets)
3. POST /api/reports/master-report/benchmark-excel (executive cross-basin benchmark workbook)
"""

import io
import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask import request, send_file, jsonify, current_app
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from extensions import db
from models import Facility
from routes.auth import login_required
from routes.reports import reports_bp, _safe_excel_value
from utils import get_current_user, get_allowed_facility_ids
from services.audit_chain import record_report_fingerprint
from services.regional_profiles import list_available_regions, get_regional_profile
from services.master_report_data import aggregate_master_report_data
from services.master_report_engine import generate_master_publication_pdf


@reports_bp.route("/master-report/regions", methods=["GET"])
@login_required
def get_master_report_regions():
    """Returns available regions strictly present in the software database."""
    user = get_current_user()
    allowed_ids = get_allowed_facility_ids(user)
    all_profiles = list_available_regions()

    # Query facilities in scope
    fac_query = Facility.query
    if allowed_ids is not None:
        fac_query = fac_query.filter(Facility.id.in_(allowed_ids))
    facilities = fac_query.all()

    # If database has no facilities yet, return the default regional registry
    if not facilities:
        fallback_regions = []
        for r in all_profiles:
            rc = dict(r)
            rc["facility_count"] = 0
            fallback_regions.append(rc)
        return jsonify({"status": "success", "regions": fallback_regions})

    present_regions = []
    matched_fac_ids = set()

    # 1. Match known regional profiles that have monitored facilities in the software
    for r in all_profiles:
        rk = r["key"].lower()
        if rk == "national":
            continue
        p = get_regional_profile(rk)
        aliases = [a.lower() for a in p.get("aliases", [])]
        matched_facs = [
            f for f in facilities
            if rk in (f.region or "").lower() or rk in (f.name or "").lower()
            or any(alias in (f.region or "").lower() or alias in (f.name or "").lower() for alias in aliases)
        ]
        if matched_facs:
            r_copy = dict(r)
            r_copy["facility_count"] = len(matched_facs)
            r_copy["facility_names"] = [f.name for f in matched_facs]
            present_regions.append(r_copy)
            for f in matched_facs:
                matched_fac_ids.add(f.id)

    # 2. Dynamically include any custom facility regions present in the software
    unmatched_facs = [f for f in facilities if f.id not in matched_fac_ids]
    custom_map: Dict[str, List[Facility]] = {}
    for f in unmatched_facs:
        reg_name = f.region or f.location or f.name
        if not reg_name or reg_name.lower() in ("algeria", "global", "south", "none"):
            continue
        custom_map.setdefault(reg_name, []).append(f)

    for reg_name, fac_list in custom_map.items():
        clean_key = reg_name.lower().replace(" ", "_").replace("/", "_")
        present_regions.append({
            "key": clean_key,
            "name": f"{reg_name} Production Area",
            "segment": fac_list[0].segment or "Upstream",
            "facility_count": len(fac_list),
            "facility_names": [f.name for f in fac_list],
        })

    # 3. Add National (Consolidated Sonatrach Group) if facilities exist
    if facilities:
        national_entry = next((r for r in all_profiles if r["key"] == "national"), {
            "key": "national",
            "name": "Sonatrach Corporate Group (Consolidated National)",
            "segment": "Integrated",
        })
        nat_copy = dict(national_entry)
        nat_copy["facility_count"] = len(facilities)
        present_regions.insert(0, nat_copy)

    return jsonify({"status": "success", "regions": present_regions})


@reports_bp.route("/master-report", methods=["POST"])
@login_required
def generate_master_report_endpoint():
    """Generates and streams the publication-grade Master Report PDF."""
    user = get_current_user()
    allowed_ids = get_allowed_facility_ids(user)
    payload = request.get_json() or {}

    mode = str(payload.get("mode", "regional")).lower()
    if mode not in ("regional", "national", "comparison"):
        mode = "regional"

    region_key = payload.get("region")
    if mode == "national":
        region_key = "national"

    try:
        start_year = int(payload.get("start_year", 2023))
        end_year = int(payload.get("end_year", 2025))
    except (ValueError, TypeError):
        start_year, end_year = 2023, 2025

    if start_year > end_year:
        start_year, end_year = end_year, start_year

    gwp_standard = str(payload.get("gwp_standard", "AR5")).upper()
    if gwp_standard not in ("AR4", "AR5", "AR6"):
        gwp_standard = "AR5"

    language = str(payload.get("language", "en")).lower()
    if language not in ("en", "fr"):
        language = "en"

    try:
        pdf_buffer = generate_master_publication_pdf(
            mode=mode,
            region_key=region_key,
            start_year=start_year,
            end_year=end_year,
            gwp_standard=gwp_standard,
            allowed_facility_ids=allowed_ids,
            language=language,
        )

        time_tag = f"{start_year}" if start_year == end_year else f"{start_year}_{end_year}"
        clean_name = (region_key.capitalize() if region_key else "National").replace(" ", "_").replace("/", "_")
        lang_tag = f"_{language.upper()}"
        filename = f"Sonatrach_{mode.capitalize()}_{clean_name}_Master_Report_{time_tag}{lang_tag}.pdf"

        report_sha256 = getattr(pdf_buffer, "report_hash", None) or hashlib.sha256(pdf_buffer.getvalue()).hexdigest()

        resp = send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
        resp.headers["X-Audit-Timestamp"] = datetime.now(timezone.utc).isoformat()
        resp.headers["X-Report-SHA256"] = report_sha256

        filters = {
            "mode": mode,
            "region": region_key,
            "start_year": start_year,
            "end_year": end_year,
            "gwp_standard": gwp_standard,
            "language": language,
        }
        return record_report_fingerprint(resp, user, f"Master Publication Report ({mode})", filters, 1, report_sha256)

    except Exception as e:
        current_app.logger.error(f"Error generating Master Report: {e}", exc_info=True)
        return jsonify({"error": f"Failed to generate Master Publication Report: {str(e)}"}), 500


def _style_excel_header(ws, col_count: int, title: str, subtitle: str):
    """Styles the corporate header block for benchmark Excel workbooks."""
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    sub_fill = PatternFill(start_color="EA580C", end_color="EA580C", fill_type="solid")
    white_bold = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    white_sub = Font(name="Calibri", size=10, bold=True, color="FFFFFF")

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=col_count)
    c1 = ws.cell(row=1, column=1, value=_safe_excel_value(f"SONATRACH // {title.upper()}"))
    c1.fill = header_fill
    c1.font = white_bold
    c1.alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=col_count)
    c2 = ws.cell(row=2, column=1, value=_safe_excel_value(subtitle))
    c2.fill = sub_fill
    c2.font = white_sub
    c2.alignment = Alignment(horizontal="center", vertical="center")


@reports_bp.route("/master-report/benchmark-excel", methods=["POST"])
@login_required
def export_benchmark_excel():
    """Generates an executive cross-basin benchmark Excel workbook."""
    user = get_current_user()
    allowed_ids = get_allowed_facility_ids(user)
    payload = request.get_json() or {}

    start_year = int(payload.get("start_year", 2023))
    end_year = int(payload.get("end_year", 2025))
    gwp_standard = str(payload.get("gwp_standard", "AR5")).upper()

    data = aggregate_master_report_data("comparison", None, start_year, end_year, gwp_standard, allowed_ids)
    benchmarks = data.get("regional_benchmarks", [])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cross-Basin Benchmark"

    cols = [
        "Basin / Regional Asset",
        "Operational Segment",
        "Facilities Monitored",
        "Aggregate Deliverability (MMBOE)",
        "Scope 1+2 GHG (tCO2e)",
        "Carbon Intensity (kg CO2e/BOE)",
        "Flaring Intensity (% Gas)",
        "Decree 21-330 Status (<= 1.00%)"
    ]
    _style_excel_header(ws, len(cols), "Cross-Basin Benchmark & Intelligence Matrix", f"Period: {start_year} - {end_year} | Standard: ISO 14064-1 & Décret 21-330")

    # Table Header
    th_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    th_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    border_thin = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    for col_idx, col_name in enumerate(cols, 1):
        cell = ws.cell(row=4, column=col_idx, value=_safe_excel_value(col_name))
        cell.fill = th_fill
        cell.font = th_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Populate rows
    for r_idx, b in enumerate(benchmarks, 5):
        row_vals = [
            b.get("name", ""),
            b.get("segment", "Upstream"),
            b.get("facility_count", 1),
            round(b.get("total_mmboe", 0.0), 3),
            round(b.get("total_co2e_t", 0.0), 1),
            round(b.get("carbon_intensity_kg_boe", 0.0), 2),
            f"{b.get('flaring_intensity_pct', 0.0):.2f}%",
            "COMPLIANT" if b.get("decree_compliant") else "EXCEEDED CAP",
        ]
        for c_idx, v in enumerate(row_vals, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=_safe_excel_value(v))
            cell.border = border_thin
            cell.font = Font(name="Calibri", size=9.5)
            if c_idx == 8:
                cell.font = Font(name="Calibri", size=9.5, bold=True, color="166534" if "COMPLIANT" in str(v) else "991B1B")

    # Auto-fit columns
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    hash_val = hashlib.sha256(buf.getvalue()).hexdigest()

    filename = f"Sonatrach_Cross_Basin_Benchmark_{start_year}_{end_year}.xlsx"
    resp = send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )
    resp.headers["X-Audit-Timestamp"] = datetime.now(timezone.utc).isoformat()
    resp.headers["X-Report-SHA256"] = hash_val
    return resp
