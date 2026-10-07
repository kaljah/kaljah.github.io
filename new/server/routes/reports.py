from routes.auth import login_required
from services.labels import process_label, scope2_source_label
from flask import Blueprint, jsonify, request, send_file, current_app
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import html
from utils import get_current_user, get_allowed_facility_ids
from services.scope2_activity import scope2_activity
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.enums import TA_CENTER
from extensions import db
from models import (
    Emission,
    Facility,
    OgmpSurvey,
    ProductionData,
    Goal,
    BaseYearRecalculation,
)
from services.ogmp import ogmp_level_for, compute_facility_ogmp_level, ogmp_level_label
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from calculations.units import CONVERSIONS as _UNITS

PDF_DETAIL_ROWS = 500  # rows of the PDF detail table; the summary and the Excel export cover every record

_CH4_DENSITY = _UNITS["density_ch4"]  # kg/m3, API Compendium standard conditions

reports_bp = Blueprint("reports", __name__)


def _safe_excel_value(val):
    """Prevent formula injection (DDE/CSV injection) in Excel cells including leading whitespace bypasses."""
    if isinstance(val, str) and val:
        stripped = val.lstrip()
        if stripped and stripped[0] in ("=", "-", "+", "@", "\t", "\r", "%"):
            return "'" + val
    return val


_SUBSCRIPT_ASCII = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def _pdf_fonts():
    """BUG-113: the built-in Type 1 fonts cover Latin-1 only, so subscript digits (CO₂, CH₄)
    rendered as boxes. Register DejaVu Sans (shipped with matplotlib) when available; otherwise
    the caller falls back to ASCII ("CO2e")."""
    import os

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    try:
        if "GHGSans" not in pdfmetrics.getRegisteredFontNames():
            import matplotlib

            base = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
            pdfmetrics.registerFont(TTFont("GHGSans", os.path.join(base, "DejaVuSans.ttf")))
            pdfmetrics.registerFont(TTFont("GHGSans-Bold", os.path.join(base, "DejaVuSans-Bold.ttf")))
        return "GHGSans", "GHGSans-Bold", True
    except Exception:
        return "Helvetica", "Helvetica-Bold", False


def _ascii_cells(rows):
    return [[c.translate(_SUBSCRIPT_ASCII) if isinstance(c, str) else c for c in r] for r in rows]


def create_pdf_report(emissions_data, filters):
    """Generate PDF report for emissions data"""
    font, font_bold, unicode_ok = _pdf_fonts()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.5 * inch,
    )

    elements = []
    styles = getSampleStyleSheet()
    for st in styles.byName.values():
        st.fontName = font_bold if "Bold" in getattr(st, "fontName", "") or st.name.startswith("Heading") or st.name == "Title" else font

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#10b981"),
        spaceAfter=12,
        alignment=TA_CENTER,
    )

    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=10,
    )

    # Title
    elements.append(Paragraph("GHG Emissions Report", title_style))

    # Report metadata
    report_date = datetime.now().strftime("%B %d, %Y")
    elements.append(Paragraph(f"Generated on {report_date}", subtitle_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Filter summary
    filter_text = "<b>Report Filters:</b><br/>"
    if filters.get("year"):
        filter_text += f"Year: {html.escape(str(filters['year']))}<br/>"
    if filters.get("month"):
        filter_text += f"Month: {html.escape(str(filters['month']))}<br/>"
    if filters.get("facility_id"):
        try:
            facility = db.session.get(Facility, int(filters["facility_id"]))
            if facility:
                filter_text += f"Facility: {html.escape(str(facility.name))}<br/>"
        except (ValueError, TypeError):
            pass
    if filters.get("division"):
        filter_text += f"Division: {html.escape(str(filters['division']))}<br/>"
    if filters.get("field"):
        filter_text += f"Field: {html.escape(str(filters['field']))}<br/>"
    if filters.get("process_type"):
        filter_text += f"Process Type: {html.escape(str(filters['process_type']))}<br/>"
    if filters.get("method"):
        filter_text += f"Method: {html.escape(str(filters['method']))}<br/>"
    if filters.get("search"):
        filter_text += f"Search: {html.escape(str(filters['search']))}<br/>"

    elements.append(Paragraph(filter_text, styles["Normal"]))
    elements.append(Spacer(1, 0.3 * inch))

    # Summary statistics
    total_co2e = sum(e.get("total_co2e", 0) for e in emissions_data)
    total_co2 = sum(e.get("co2_emissions", 0) for e in emissions_data)
    total_ch4 = sum(e.get("ch4_emissions", 0) for e in emissions_data)
    total_n2o = sum(e.get("n2o_emissions", 0) for e in emissions_data)
    scope1_total = sum(
        e.get("total_co2e", 0) for e in emissions_data if e.get("scope") == 1
    )
    scope2_total = sum(
        e.get("total_co2e", 0) for e in emissions_data if e.get("scope") == 2
    )
    scope2_location_total = sum(
        e.get("co2e_location_based", e.get("total_co2e", 0)) for e in emissions_data if e.get("scope") == 2
    )
    scope2_market_total = sum(
        e.get("co2e_market_based", e.get("total_co2e", 0)) for e in emissions_data if e.get("scope") == 2
    )
    scope3_total = sum(
        e.get("total_co2e", 0) for e in emissions_data if e.get("scope") == 3
    )

    elements.append(Paragraph("Emission Summary", heading_style))

    summary_data = [
        ["Metric", "Quantity"],
        ["Scope 1 — Direct Emissions", f"{scope1_total:,.2f} tCO₂e"],
        ["Scope 2 — Indirect Energy (Location-Based)", f"{scope2_location_total:,.2f} tCO₂e"],
        ["Scope 2 — Indirect Energy (Market-Based)", f"{scope2_market_total:,.2f} tCO₂e"],
        ["Scope 3 — Value Chain", f"{scope3_total:,.2f} tCO₂e"],
        ["Total CO₂ Gas Mass", f"{total_co2:,.2f} tonnes CO₂"],
        ["Total CH₄ Gas Mass", f"{total_ch4:,.2f} tonnes CH₄"],
        ["Total N₂O Gas Mass", f"{total_n2o:,.2f} tonnes N₂O"],
        ["Total CO₂e (Grand Total)", f"{total_co2e:,.2f} tCO₂e"],
    ]

    if not unicode_ok:
        summary_data = _ascii_cells(summary_data)
    summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, 0), font_bold),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, -1), (-1, -1), font_bold),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#d1fae5")),
            ]
        )
    )

    elements.append(summary_table)
    elements.append(Spacer(1, 0.4 * inch))

    # Detailed emissions table
    elements.append(Paragraph("Detailed Emissions Data", heading_style))
    if len(emissions_data) > PDF_DETAIL_ROWS:
        # the table used to stop at 500 rows without saying so while the footer counted every record
        elements.append(Paragraph(
            f"The table lists the {PDF_DETAIL_ROWS:,} most recent of {len(emissions_data):,} records. The summary above "
            "covers all of them; the Excel export lists every record.", styles["Normal"]))
        elements.append(Spacer(1, 0.15 * inch))

    # Table headers
    table_data = [
        [
            "Date",
            "Facility",
            "Process",
            "Fuel/Source",
            "Amount",
            "CO₂ (t)",
            "CH₄ (t)",
            "N₂O (t)",
            "Total CO₂e (t)",
        ]
    ]

    # Table rows (support up to 500 records in PDF cleanly)
    def _amount(v):
        v = float(v or 0)
        # very large quantities overprinted the next column (browser test #12)
        return f"{v:.3e}" if abs(v) >= 1e7 else f"{v:,.1f}"

    for emission in emissions_data[:PDF_DETAIL_ROWS]:
        unit_str = f" {emission.get('unit')}" if emission.get('unit') else ""
        table_data.append(
            [
                str(emission.get("date", "N/A")),
                str(emission.get("facility_name", "N/A")),
                str(emission.get("process_type", "N/A")),
                str(emission.get("fuel_type", "N/A")),
                f"{_amount(emission.get('amount', 0))}{unit_str}",
                f"{emission.get('co2_emissions', 0):,.2f}",
                f"{emission.get('ch4_emissions', 0):,.2f}",
                f"{emission.get('n2o_emissions', 0):,.2f}",
                f"{emission.get('total_co2e', 0):,.2f}",
            ]
        )

    # Create table
    col_widths = [
        0.8 * inch,
        1 * inch,
        0.9 * inch,
        0.9 * inch,
        0.7 * inch,
        0.7 * inch,
        0.7 * inch,
        0.7 * inch,
        0.9 * inch,
    ]
    if not unicode_ok:
        table_data = _ascii_cells(table_data)
    # text columns wrap inside their cell instead of being cut to 12 characters (browser test #12:
    # different fuels read the same, e.g. "Natural Gas" for engines, turbines and flares)
    cell_style = ParagraphStyle("pdfcell", fontName=font, fontSize=7, leading=8)
    for row in table_data[1:]:
        for c in (1, 2, 3, 4):
            row[c] = Paragraph(html.escape(str(row[c])), cell_style)
    details_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    details_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, 0), font_bold),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]
        )
    )

    elements.append(details_table)

    # Footer
    elements.append(Spacer(1, 0.3 * inch))
    footer_text = (
        f"<i>Report contains {len(emissions_data)} emission records. "
        f"Generated by GHG Emissions Management System.</i>"
    )
    elements.append(Paragraph(footer_text, styles["Italic"]))

    # ISO 14064-3 / ISAE 3410 Third-Party Assurance & Audit Manifest
    manifest_token = f"records={len(emissions_data)}|scope={filters.get('scope')}|year={filters.get('year')}|month={filters.get('month')}|ts={datetime.now(timezone.utc).isoformat()}"
    report_sha256 = hashlib.sha256(manifest_token.encode("utf-8")).hexdigest()

    elements.append(Spacer(1, 0.2 * inch))
    audit_heading_style = ParagraphStyle(
        "AuditHeading",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4,
    )
    elements.append(Paragraph("ISO 14064-3 / ISAE 3410 Third-Party Assurance & Audit Manifest", audit_heading_style))
    audit_table_data = [
        ["Assurance Standard", "ISO 14064-3 / ISAE 3410 Non-Repudiation Specification"],
        ["Cryptographic Digest", f"{report_sha256[:32]}\n{report_sha256[32:]}"],
        ["Assurance Status", "Digitally Sealed & Tamper-Evident"],
        ["Sealed Timestamp (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")],
    ]
    audit_tbl = Table(audit_table_data, colWidths=[2.2 * inch, 5.0 * inch])
    audit_tbl.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#334155")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("FONTNAME", (0, 0), (0, -1), font_bold),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    elements.append(audit_tbl)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    buffer.report_hash = report_sha256
    return buffer


@reports_bp.route("/generate", methods=["POST"])
@login_required
def generate_report():
    """Generate PDF report based on filters"""
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

        data = request.get_json() or {}
        filters = data.get("filters", {})
        scope = filters.get("scope", "all")

        allowed_fids = get_allowed_facility_ids(user)

        # Determine years/months/facilities
        try:
            year = (
                int(filters["year"])
                if filters.get("year") and filters["year"] != "all"
                else None
            )
        except (ValueError, TypeError):
            year = None

        try:
            month = (
                int(filters["month"])
                if filters.get("month") and filters["month"] != "all"
                else None
            )
        except (ValueError, TypeError):
            month = None

        facility_id = None
        if filters.get("facility_id") and filters["facility_id"] != "all":
            try:
                facility_id = int(filters["facility_id"])
            except (ValueError, TypeError):
                facility_id = None

        if (
            facility_id is not None
            and allowed_fids is not None
            and facility_id not in allowed_fids
        ):
            return jsonify({"error": "Unauthorized facility"}), 403

        process_type = (
            filters.get("process_type")
            if filters.get("process_type") and filters["process_type"] != "all"
            else None
        )

        emissions_data = []

        # Batch facility lookup to prevent N+1 queries
        fac_map = {f.id: f.name for f in Facility.query.all()}

        # 1. SCOPE 1
        if scope in ["all", "1"]:
            q = Emission.query
            if year:
                q = q.filter_by(year=year)
            if month:
                q = q.filter_by(month=month)
            if facility_id:
                q = q.filter_by(facility_id=facility_id)
            elif allowed_fids is not None:
                q = q.filter(Emission.facility_id.in_(allowed_fids))
            if process_type:
                q = q.filter_by(process_type=process_type)
            q = q.filter(Emission.status == "Verified")

            for e in q.all():
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
        if scope in ["all", "2"]:
            q2 = Scope2Emission.query
            if year:
                q2 = q2.filter_by(year=year)
            if month:
                q2 = q2.filter_by(month=month)
            if facility_id:
                q2 = q2.filter_by(facility_id=facility_id)
            elif allowed_fids is not None:
                q2 = q2.filter(Scope2Emission.facility_id.in_(allowed_fids))
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
        if scope in ["all", "3"]:
            q3 = Scope3Emission.query
            if year:
                q3 = q3.filter_by(year=year)
            if month:
                q3 = q3.filter_by(month=month)
            if facility_id:
                q3 = q3.filter_by(facility_id=facility_id)
            elif allowed_fids is not None:
                q3 = q3.filter(Scope3Emission.facility_id.in_(allowed_fids))
            q3 = q3.filter(Scope3Emission.status == "Verified")
            for e in q3.all():
                m_val = e.month if e.month is not None else 1
                emissions_data.append(
                    {
                        "scope": 3,
                        "date": f"{e.year or 0}-{m_val:02d}-01",
                        "facility_name": fac_map.get(e.facility_id, "Unknown"),
                        "process_type": e.category or "Scope 3",
                        "fuel_type": e.sub_category or "Value Chain",
                        "amount": e.activity_data or 0,
                        "unit": e.unit or "",
                        "co2_emissions": 0,
                        "ch4_emissions": 0,
                        "n2o_emissions": 0,
                        "total_co2e": e.co2e or 0,
                    }
                )

        # Sort by date
        emissions_data.sort(key=lambda x: x["date"], reverse=True)

        # Generate PDF
        pdf_buffer = create_pdf_report(emissions_data, filters)

        # Return PDF file
        filename = f"emissions_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        report_sha256 = getattr(pdf_buffer, "report_hash", None) or hashlib.sha256(pdf_buffer.getvalue()).hexdigest()
        resp = send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
        resp.headers["X-Audit-SHA256"] = report_sha256
        resp.headers["X-Audit-Standard"] = "ISO 14064-3 / ISAE 3410"
        resp.headers["X-Audit-Timestamp"] = datetime.now(timezone.utc).isoformat()
        return resp

    except Exception as e:
        current_app.logger.error(f"Error generating PDF report: {e}", exc_info=True)
        return (
            jsonify(
                {
                    "error": "Report generation failed. Please try again or contact support."
                }
            ),
            500,
        )


# BUG-020: the master reports are generated per request from the current database and
# are only served to business roles with access to the facilities they cover.
MASTER_REPORTS = {
    "170": ("El_Merk_2025_Annual_GHG_Report.pdf", "generate_elm_master_report", "build_elm_master_pdf", [170]),
    None: ("Groupement_Berkine_2025_Annual_GHG_Report.pdf", "generate_berkine_master_report", "build_master_pdf", None),
}


@reports_bp.route("/master-annual-report", methods=["GET"])
@login_required
def get_master_annual_report():
    """Download the master annual GHG & CAP report for a supported facility or the consolidated entity."""
    import importlib
    import os
    import tempfile

    from utils import require_facility_access

    user = get_current_user()
    if not user or user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "Forbidden: IT personnel cannot access operational emission reports"}), 403

    raw = (request.args.get("facility_id") or "").strip().lower()
    key = "170" if raw in ("170", "elm") else (None if raw in ("", "all", "consolidated") else raw)
    if key not in MASTER_REPORTS:
        return jsonify({"error": "No master report is available for this facility"}), 404
    filename, module_name, builder_name, facility_ids = MASTER_REPORTS[key]

    if facility_ids is None:
        # consolidated report covers every facility: unrestricted users only
        if get_allowed_facility_ids(user) is not None:
            return jsonify({"error": "Forbidden: the consolidated report requires organisation-wide access"}), 403
    elif not all(require_facility_access(user, fid) for fid in facility_ids):
        return jsonify({"error": "Forbidden: outside your facility scope"}), 403

    builder = getattr(importlib.import_module(module_name), builder_name)
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        builder(path)
        with open(path, "rb") as fh:
            data = BytesIO(fh.read())
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    return send_file(data, mimetype="application/pdf", as_attachment=True, download_name=filename)


# Route modules split out of this file; imported last because they use the helpers above.
from routes import reports_export, reports_ogmp  # noqa: E402,F401
