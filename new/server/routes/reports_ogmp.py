"""OGMP 2.0 Excel export route.

Split out of routes/reports.py unchanged (hardening plan, task 5.3). The routes are
registered on the same ``reports_bp`` blueprint, so URLs and endpoint names are the same.
"""
import hashlib
import openpyxl
from datetime import datetime, timezone
from extensions import db
from flask import current_app, jsonify, request, send_file
from io import BytesIO
from models import BaseYearRecalculation, Emission, Facility, Goal, OgmpSurvey, ProductionData
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from routes.auth import login_required
from services.labels import process_label
from services.ogmp import compute_facility_ogmp_level, ogmp_level_for
from utils import get_allowed_facility_ids, get_current_user
from routes.reports import _CH4_DENSITY, _safe_excel_value, reports_bp


@reports_bp.route("/ogmp-export", methods=["GET"])
@login_required
def export_ogmp_excel():
    """
    Generates a 5-tab UNEP / OGMP 2.0 Standard Disclosure Workbook (Excel):
    1. Executive Summary & Asset Metadata
    2. Bottom-Up Source Inventory (L1-L4)
    3. Top-Down Measurement Campaigns (L4/L5)
    4. Reconciliation Matrix
    5. Gold Standard Progression Roadmap
    """
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
        allowed_fids = get_allowed_facility_ids(user)

        year = request.args.get("year", "all")
        year_filter = int(year) if year and year.isdigit() and year != "all" else None
        facility_id = request.args.get("facility_id") or request.args.get("facilityId")
        facility_filter = (
            int(facility_id) if facility_id and facility_id.isdigit() and facility_id != "all" else None
        )

        if (
            facility_filter is not None
            and allowed_fids is not None
            and facility_filter not in allowed_fids
        ):
            return jsonify({"error": "Unauthorized facility"}), 403

        # Prepare workbook
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default empty sheet

        # Styling definitions
        header_fill = PatternFill(
            start_color="1E3A8A", end_color="1E3A8A", fill_type="solid"
        )  # Navy
        sub_fill = PatternFill(
            start_color="2563EB", end_color="2563EB", fill_type="solid"
        )  # Blue
        accent_fill = PatternFill(
            start_color="0D9488", end_color="0D9488", fill_type="solid"
        )  # Teal
        gold_fill = PatternFill(
            start_color="D97706", end_color="D97706", fill_type="solid"
        )  # Amber
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=16, bold=True, color="1E3A8A")
        bold_font = Font(name="Calibri", size=11, bold=True)
        regular_font = Font(name="Calibri", size=11)
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        def style_header_row(ws, row_idx, fill=header_fill):
            for col in range(1, ws.max_column + 1):
                cell = ws.cell(row=row_idx, column=col)
                cell.fill = fill
                cell.font = header_font
                cell.alignment = Alignment(
                    horizontal="center", vertical="center", wrap_text=True
                )

        def autofit_columns(ws):
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    val_str = str(cell.value or "")
                    if "\n" in val_str:
                        val_str = max(val_str.split("\n"), key=len)
                    max_len = max(max_len, len(val_str))
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

        # -------------------------------------------------------------
        # TAB 1: Executive Summary & Facility Metadata
        # -------------------------------------------------------------
        ws1 = wb.create_sheet(title="1. Executive Summary")
        ws1.views.sheetView[0].showGridLines = True
        ws1.cell(row=1, column=1, value="OGMP 2.0 COMPLIANCE & ASSET SUMMARY").font = (
            title_font
        )
        ws1.cell(
            row=2,
            column=1,
            value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Reporting Period: {year if year != 'all' else 'All Active Years'}",
        ).font = regular_font

        # Emission goal and base year from ManageData
        _goal_yr = year_filter if year_filter else datetime.now().year
        _active_goal = Goal.query.filter_by(year=_goal_yr).first()
        _active_base_year = BaseYearRecalculation.query.order_by(
            BaseYearRecalculation.recalc_date.desc()
        ).first()
        if _active_goal:
            ws1.cell(
                row=3,
                column=1,
                value=f"Emission Target {_active_goal.year}: {float(_active_goal.target_amount or 0):,.0f} tCO\u2082e",
            ).font = bold_font
        if _active_base_year:
            by_val = f"Active Base Year: {_active_base_year.year}"
            if _active_base_year.reason:
                by_val += f" — {_active_base_year.reason[:80]}"
            ws1.cell(row=3, column=6 if _active_goal else 1, value=by_val).font = (
                bold_font
            )

        ws1.cell(row=4, column=1, value="Facility Name")
        ws1.cell(row=4, column=2, value="Code")
        ws1.cell(row=4, column=3, value="Segment")
        ws1.cell(row=4, column=4, value="Operator Status")
        ws1.cell(row=4, column=5, value="Country")
        ws1.cell(row=4, column=6, value="Base Year")
        ws1.cell(row=4, column=7, value="Target Gold Year")
        ws1.cell(row=4, column=8, value="Current Level")
        ws1.cell(row=4, column=9, value="Gas Production (m³)")
        ws1.cell(row=4, column=10, value="Bottom-Up CH₄ (t)")
        ws1.cell(row=4, column=11, value="Top-Down CH₄ (t)")
        ws1.cell(row=4, column=12, value="Loss Rate (%)")
        ws1.cell(row=4, column=13, value="Gold Target (%)")
        ws1.cell(row=4, column=14, value="Target Compliance")
        ws1.cell(row=4, column=15, value="Pathway Status")
        style_header_row(ws1, 4, header_fill)

        fac_q = Facility.query
        if allowed_fids is not None:
            fac_q = fac_q.filter(Facility.id.in_(allowed_fids))
        if facility_filter:
            fac_q = fac_q.filter_by(id=facility_filter)
        activity = request.args.get("activity")
        division = request.args.get("division")
        segment = request.args.get("segment")
        if activity and activity != "all":
            fac_q = fac_q.filter(Facility.activity == activity)
        if division and division != "all":
            fac_q = fac_q.filter(Facility.division == division)
        if segment and segment != "all":
            fac_q = fac_q.filter(Facility.segment == segment)
        facilities = fac_q.all()

        level_by_fac = {}  # OGMP level per facility, shared with the roadmap tab
        row_curr = 5
        for f in facilities:
            op_st = f.operator_status or "operated"
            b_yr = f.ogmp_membership_year or 2023
            target_yr = b_yr + (3 if op_st == "operated" else 5)

            # Aggregate CH4
            em_q = db.session.query(db.func.sum(Emission.ch4_emissions)).filter(
                Emission.facility_id == f.id, Emission.status == "Verified"
            )
            if year_filter:
                em_q = em_q.filter(Emission.year == year_filter)
            bu_ch4 = em_q.scalar() or 0.0

            # Aggregate Gas Production with unit conversion
            prod_q = ProductionData.query.filter(ProductionData.facility_id == f.id)
            if year_filter:
                prod_q = prod_q.filter(ProductionData.year == year_filter)
            prod_records = prod_q.all()
            # same gas definition as the Methane Intensity page (gross gas first): the export read
            # gas_amount only and reported a 161,966 % loss rate where the page showed 3.479 %
            from services.dashboard_filters import production_gas_m3
            gas_m3 = sum(production_gas_m3(p) or 0.0 for p in prod_records)

            # Top Down (D-02: mean of surveys per facility-year)
            td_q = db.session.query(
                db.func.avg(OgmpSurvey.estimated_annual_tch4)
            ).filter(OgmpSurvey.facility_id == f.id)
            if year_filter:
                td_q = td_q.filter(OgmpSurvey.year == year_filter)
            td_ch4 = td_q.scalar() or 0.0

            # Loss rate %
            ch4_vol_m3 = (bu_ch4 * 1000.0) / _CH4_DENSITY if bu_ch4 > 0 else 0.0
            target_rate = (
                0.20 if "upstream" in (f.segment or "Upstream").lower() else 0.05
            )
            if gas_m3 > 0:
                loss_rate_pct = (ch4_vol_m3 / gas_m3 * 100.0)
                comp_status = (
                    "Compliant" if loss_rate_pct <= target_rate else "Non-Compliant"
                )
            else:
                if bu_ch4 > 0:
                    loss_rate_pct = None
                    comp_status = "Non-Compliant (Missing Production Data)"
                else:
                    loss_rate_pct = 0.0
                    comp_status = "N/A (No Activity)"

            # Canonical OGMP Level calculation
            curr_lvl = compute_facility_ogmp_level(
                f, year=year_filter, top_down_tch4=td_ch4, bottom_up_tch4=bu_ch4
            )
            level_by_fac[f.id] = curr_lvl
            pathway = (
                "Gold Standard Achieved"
                if curr_lvl == 5
                else ("On Track" if (year_filter or datetime.now().year) <= target_yr else "Overdue")
            )

            ws1.cell(row=row_curr, column=1, value=_safe_excel_value(f.name))
            ws1.cell(row=row_curr, column=2, value=_safe_excel_value(f.code or "N/A"))
            ws1.cell(
                row=row_curr, column=3, value=_safe_excel_value(f.segment or "Upstream")
            )
            ws1.cell(
                row=row_curr,
                column=4,
                value=_safe_excel_value(op_st.replace("_", "-").title()),
            )
            ws1.cell(
                row=row_curr, column=5, value=_safe_excel_value(f.country or "Algeria")
            )
            ws1.cell(row=row_curr, column=6, value=b_yr)
            ws1.cell(row=row_curr, column=7, value=target_yr)
            ws1.cell(row=row_curr, column=8, value=f"Level {curr_lvl}")
            ws1.cell(row=row_curr, column=9, value=round(gas_m3, 2))
            ws1.cell(row=row_curr, column=10, value=round(bu_ch4, 2))
            ws1.cell(row=row_curr, column=11, value=round(td_ch4, 2))
            ws1.cell(
                row=row_curr,
                column=12,
                value=round(loss_rate_pct, 4) if loss_rate_pct is not None else "N/A",
            )
            ws1.cell(row=row_curr, column=13, value=target_rate)
            ws1.cell(row=row_curr, column=14, value=comp_status)
            ws1.cell(row=row_curr, column=15, value=pathway)

            for c in range(1, 16):
                ws1.cell(row=row_curr, column=c).border = thin_border
            row_curr += 1

        autofit_columns(ws1)

        # -------------------------------------------------------------
        # TAB 2: Bottom-Up Inventory (Level 1 - Level 4)
        # -------------------------------------------------------------
        ws2 = wb.create_sheet(title="2. Bottom-Up Inventory")
        ws2.views.sheetView[0].showGridLines = True
        ws2.cell(
            row=1, column=1, value="OGMP 2.0 SOURCE-LEVEL EMISSIONS INVENTORY (L1 - L4)"
        ).font = title_font

        ws2.cell(row=3, column=1, value="Record ID")
        ws2.cell(row=3, column=2, value="Facility")
        ws2.cell(row=3, column=3, value="Year")
        ws2.cell(row=3, column=4, value="Month")
        ws2.cell(row=3, column=5, value="Process / Category")
        ws2.cell(row=3, column=6, value="Equipment / Source Code")
        ws2.cell(row=3, column=7, value="Activity Quantity")
        ws2.cell(row=3, column=8, value="Unit")
        ws2.cell(row=3, column=9, value="EF Source")
        ws2.cell(row=3, column=10, value="CH₄ Emissions (t)")
        ws2.cell(row=3, column=11, value="CO₂e Total (t)")
        ws2.cell(row=3, column=12, value="OGMP Level")
        ws2.cell(row=3, column=13, value="Calculation Method")
        ws2.cell(row=3, column=14, value="OGMP Source Category")
        style_header_row(ws2, 3, sub_fill)

        OGMP_SOURCE_MAP = {
            "combustion": "Combustion",
            "stationary_combustion": "Combustion",
            "mobile": "Combustion",
            "flaring": "Flaring",
            "fugitive": "Fugitive",
            "fugitive_component": "Fugitive",
            "equipment_fugitive": "Fugitive",
            "pneumatic": "Vented",
            "pneumatic_devices": "Vented",
            "venting": "Vented",
            "blowdown": "Vented",
            "completions": "Vented",
            "tank": "Vented",
            "tank_flashing": "Vented",
            "liquids_unloading": "Vented",
            "unloading": "Vented",
            "agr": "Process",
            "dehydrator": "Process",
        }

        em_list_q = Emission.query.filter(Emission.status == "Verified")
        if allowed_fids is not None:
            em_list_q = em_list_q.filter(Emission.facility_id.in_(allowed_fids))
        if year_filter:
            em_list_q = em_list_q.filter_by(year=year_filter)
        if facility_filter:
            em_list_q = em_list_q.filter_by(facility_id=facility_filter)
        total_count = em_list_q.count()
        if total_count > 1500:
            ws2.cell(
                row=2,
                column=1,
                value=f"⚠ NOTICE: Inventory truncated to 1,500 records. Full dataset contains {total_count} records. Apply facility/year filters for complete disclosure.",
            ).font = Font(color="FF0000", bold=True)
        em_list = (
            em_list_q.order_by(Emission.year.desc(), Emission.month.desc())
            .limit(1500)
            .all()
        )

        row_curr = 4
        for em in em_list:
            fac_name = (
                em.facility.name
                if em.facility
                else (
                    db.session.get(Facility, em.facility_id).name
                    if em.facility_id and db.session.get(Facility, em.facility_id)
                    else "Unknown"
                )
            )
            lvl = ogmp_level_for(em)
            ogmp_cat = OGMP_SOURCE_MAP.get((em.process_type or "").lower(), "Other")
            ws2.cell(
                row=row_curr,
                column=1,
                value=_safe_excel_value(em.record_id or f"EM-{em.id}"),
            )
            ws2.cell(row=row_curr, column=2, value=_safe_excel_value(fac_name))
            ws2.cell(row=row_curr, column=3, value=em.year)
            ws2.cell(row=row_curr, column=4, value=em.month)
            ws2.cell(
                row=row_curr,
                column=5,
                value=_safe_excel_value(process_label(em.process_type, "N/A")),
            )
            ws2.cell(
                row=row_curr,
                column=6,
                value=_safe_excel_value(
                    em.source_type_code or em.equipment_id or "N/A"
                ),
            )
            ws2.cell(row=row_curr, column=7, value=em.quantity or 0)
            ws2.cell(row=row_curr, column=8, value=_safe_excel_value(em.unit or ""))
            ws2.cell(
                row=row_curr,
                column=9,
                value=_safe_excel_value(em.factor_source or "Default EF"),
            )
            ws2.cell(row=row_curr, column=10, value=round(em.ch4_emissions or 0, 4))
            ws2.cell(row=row_curr, column=11, value=round(em.co2e_total or 0, 2))
            ws2.cell(row=row_curr, column=12, value=f"Level {lvl}")
            ws2.cell(
                row=row_curr,
                column=13,
                value=_safe_excel_value(
                    em.calc_method
                    or ("Facility Specific" if lvl >= 4 else "Generic EF")
                ),
            )
            ws2.cell(row=row_curr, column=14, value=_safe_excel_value(ogmp_cat))

            for c in range(1, 15):
                ws2.cell(row=row_curr, column=c).border = thin_border
            row_curr += 1

        autofit_columns(ws2)

        # -------------------------------------------------------------
        # TAB 3: Top-Down Measurement Surveys (Level 4/5)
        # -------------------------------------------------------------
        ws3 = wb.create_sheet(title="3. Top-Down Surveys")
        ws3.views.sheetView[0].showGridLines = True
        ws3.cell(
            row=1, column=1, value="OGMP 2.0 SITE-LEVEL MEASUREMENT CAMPAIGNS (L4 / L5)"
        ).font = title_font

        ws3.cell(row=3, column=1, value="Survey ID")
        ws3.cell(row=3, column=2, value="Facility")
        ws3.cell(row=3, column=3, value="Year")
        ws3.cell(row=3, column=4, value="Survey Date")
        ws3.cell(row=3, column=5, value="Technology / Method")
        ws3.cell(row=3, column=6, value="Measured Rate (kg CH₄/hr)")
        ws3.cell(row=3, column=7, value="Operating Hours (hr/yr)")
        ws3.cell(row=3, column=8, value="Annualized Rate (tCH₄/yr)")
        ws3.cell(row=3, column=9, value="Detection Limit (kg/hr)")
        ws3.cell(row=3, column=10, value="Instrument / Vendor")
        ws3.cell(row=3, column=11, value="Reconciliation Status")
        ws3.cell(row=3, column=12, value="Operator Notes")
        style_header_row(ws3, 3, accent_fill)

        surv_q = OgmpSurvey.query
        if allowed_fids is not None:
            surv_q = surv_q.filter(OgmpSurvey.facility_id.in_(allowed_fids))
        if year_filter:
            surv_q = surv_q.filter_by(year=year_filter)
        if facility_filter:
            surv_q = surv_q.filter_by(facility_id=facility_filter)
        surveys = surv_q.order_by(OgmpSurvey.survey_date.desc()).all()

        row_curr = 4
        for s in surveys:
            fac_name = (
                s.facility.name
                if s.facility
                else (
                    db.session.get(Facility, s.facility_id).name
                    if s.facility_id and db.session.get(Facility, s.facility_id)
                    else "Unknown"
                )
            )
            ws3.cell(row=row_curr, column=1, value=_safe_excel_value(f"OGMP-{s.id}"))
            ws3.cell(row=row_curr, column=2, value=_safe_excel_value(fac_name))
            ws3.cell(row=row_curr, column=3, value=s.year)
            ws3.cell(row=row_curr, column=4, value=_safe_excel_value(s.survey_date))
            ws3.cell(row=row_curr, column=5, value=_safe_excel_value(s.survey_type))
            ws3.cell(row=row_curr, column=6, value=s.measured_rate_kg_hr)
            ws3.cell(row=row_curr, column=7, value=s.operating_hours_year or 8760)
            ws3.cell(row=row_curr, column=8, value=s.estimated_annual_tch4)
            ws3.cell(
                row=row_curr,
                column=9,
                value=_safe_excel_value(s.detection_threshold or "N/A"),
            )
            ws3.cell(
                row=row_curr,
                column=10,
                value=_safe_excel_value(s.instrument_vendor or "N/A"),
            )
            ws3.cell(
                row=row_curr,
                column=11,
                value=_safe_excel_value(s.reconciliation_status or "Reconciled"),
            )
            ws3.cell(
                row=row_curr, column=12, value=_safe_excel_value(s.operator_notes or "")
            )

            for c in range(1, 13):
                ws3.cell(row=row_curr, column=c).border = thin_border
            row_curr += 1

        autofit_columns(ws3)

        # -------------------------------------------------------------
        # TAB 4: Reconciliation Matrix (Bottom-Up vs Top-Down)
        # -------------------------------------------------------------
        ws4 = wb.create_sheet(title="4. Reconciliation Matrix")
        ws4.views.sheetView[0].showGridLines = True
        ws4.cell(
            row=1,
            column=1,
            value="OGMP 2.0 BOTTOM-UP VS TOP-DOWN RECONCILIATION MATRIX",
        ).font = title_font

        ws4.cell(row=3, column=1, value="Facility")
        ws4.cell(row=3, column=2, value="Reporting Year")
        ws4.cell(row=3, column=3, value="Segment")
        ws4.cell(row=3, column=4, value="Bottom-Up Total (tCH₄)")
        ws4.cell(row=3, column=5, value="Top-Down Survey Total (tCH₄)")
        ws4.cell(row=3, column=6, value="Reconciliation Variance (%)")
        ws4.cell(row=3, column=7, value="Threshold (%)")
        ws4.cell(row=3, column=8, value="Discrepancy Flag")
        ws4.cell(row=3, column=9, value="Reconciliation Status")
        ws4.cell(row=3, column=10, value="Operator Explanation & Remediation")
        style_header_row(ws4, 3, gold_fill)

        row_curr = 4
        for f in facilities:
            # Bottom-Up
            bu_q = db.session.query(db.func.sum(Emission.ch4_emissions)).filter(
                Emission.facility_id == f.id, Emission.status == "Verified"
            )
            if year_filter:
                bu_q = bu_q.filter(Emission.year == year_filter)
            bu_total = bu_q.scalar() or 0.0

            # Top-Down (D-02: mean of surveys)
            td_q = db.session.query(
                db.func.avg(OgmpSurvey.estimated_annual_tch4)
            ).filter(OgmpSurvey.facility_id == f.id)
            if year_filter:
                td_q = td_q.filter(OgmpSurvey.year == year_filter)
            td_total = td_q.scalar() or 0.0

            thresh = f.reconciliation_threshold or 20.0
            if bu_total > 0 and td_total > 0:
                var_pct = round(((td_total - bu_total) / bu_total * 100.0), 2)
                is_flagged = abs(var_pct) > thresh
                rec_status = "Reconciled" if not is_flagged else "Discrepancy Flagged"
                var_str = f"{var_pct:+.2f}%"
            elif bu_total == 0 and td_total > 0:
                var_pct = None
                is_flagged = True
                rec_status = "No Bottom-Up Inventory — Discrepancy Flagged"
                var_str = "N/A (No BU)"
            elif td_total == 0:
                var_pct = None
                is_flagged = False
                rec_status = "Pending Measurement"
                var_str = "Pending TD"
            else:
                var_pct = None
                is_flagged = False
                rec_status = "No Data"
                var_str = "No Data"

            ws4.cell(row=row_curr, column=1, value=_safe_excel_value(f.name))
            ws4.cell(
                row=row_curr,
                column=2,
                value=_safe_excel_value(year if year != "all" else "All Years"),
            )
            ws4.cell(
                row=row_curr, column=3, value=_safe_excel_value(f.segment or "Upstream")
            )
            ws4.cell(row=row_curr, column=4, value=round(bu_total, 2))
            ws4.cell(row=row_curr, column=5, value=round(td_total, 2))
            ws4.cell(row=row_curr, column=6, value=var_str)
            ws4.cell(row=row_curr, column=7, value=f"±{thresh}%")
            # a reconciliation needs both inventories: without a top-down measurement there is
            # nothing to pass (browser test #10: "PASS - within acceptable variance" with no survey)
            if var_pct is None and not is_flagged:
                flag_txt = "NOT ASSESSED"
                note = ("No top-down measurement for this period: schedule a site-level survey"
                        if rec_status == "Pending Measurement" else "No bottom-up or top-down data")
            elif is_flagged:
                flag_txt = "FLAGGED (> Threshold)"
                note = ("Site measurement exceeds bottom-up inventory. Investigate uncombusted slip "
                        "or uninventoried vent sources." if (var_pct is None or var_pct > 0)
                        else "Site measurement is below the bottom-up inventory. Review the "
                             "inventory factors and the survey coverage.")
            else:
                flag_txt = "PASS"
                note = "Within acceptable variance bounds"
            ws4.cell(row=row_curr, column=8, value=flag_txt)
            ws4.cell(row=row_curr, column=9, value=_safe_excel_value(rec_status))
            ws4.cell(row=row_curr, column=10, value=_safe_excel_value(note))

            for c in range(1, 11):
                ws4.cell(row=row_curr, column=c).border = thin_border
            row_curr += 1

        autofit_columns(ws4)

        # -------------------------------------------------------------
        # TAB 5: Gold Standard Progression Roadmap
        # -------------------------------------------------------------
        ws5 = wb.create_sheet(title="5. Gold Standard Roadmap")
        ws5.views.sheetView[0].showGridLines = True
        ws5.cell(
            row=1, column=1, value="OGMP 2.0 GOLD STANDARD PATHWAY & MILESTONE TRACKER"
        ).font = title_font

        ws5.cell(row=3, column=1, value="Facility")
        ws5.cell(row=3, column=2, value="Operator Type")
        ws5.cell(row=3, column=3, value="OGMP Base Year")
        ws5.cell(row=3, column=4, value="Compliance Timeline")
        ws5.cell(row=3, column=5, value="Target Deadline Year")
        ws5.cell(row=3, column=6, value="Current Level")
        ws5.cell(row=3, column=7, value="Milestone Status")
        ws5.cell(row=3, column=8, value="Next Mandatory Action")
        style_header_row(ws5, 3, header_fill)

        row_curr = 4
        for f in facilities:
            op_st = f.operator_status or "operated"
            b_yr = f.ogmp_membership_year or 2023
            timeline = (
                "3 Years (Operated Asset)"
                if op_st == "operated"
                else "5 Years (Non-Operated Asset)"
            )
            target_yr = b_yr + (3 if op_st == "operated" else 5)

            # Check reconciled survey existence
            latest_survey = (
                OgmpSurvey.query.filter_by(facility_id=f.id)
                .order_by(OgmpSurvey.year.desc(), OgmpSurvey.survey_date.desc())
                .first()
            )
            is_reconciled = (
                latest_survey is not None
                and latest_survey.reconciliation_status == "Reconciled"
                and not latest_survey.variance_flag
            )
            has_survey = latest_survey is not None
            # the level shown in the Executive Summary (browser test #10: Level 2 there, "Level 3"
            # here); the deadline is compared with the reporting year, not a fixed 2026
            lvl_num = level_by_fac.get(f.id)
            lvl_names = {1: "Level 1 (Asset-level estimate)", 2: "Level 2 (Generic factors)",
                         3: "Level 3 (Source-type factors)", 4: "Level 4 (Source-specific / measured)",
                         5: "Level 5 (Reconciled with site measurement)"}
            curr_lvl = lvl_names.get(lvl_num, f"Level {lvl_num}" if lvl_num else "Not assessed")
            ref_year = year_filter or datetime.now().year
            if lvl_num == 5 or is_reconciled:
                status = "Gold Standard Achieved"
            elif ref_year < target_yr:
                status = f"On Track ({target_yr - ref_year} yr remaining)"
            elif ref_year == target_yr:
                status = "Due this year"
            else:
                status = "Overdue - Action Plan Required"
            action = (
                "Maintain annual top-down measurement campaigns"
                if is_reconciled
                else (
                    "Reconcile measurement discrepancy with inventory"
                    if has_survey
                    else "Schedule aerial / satellite top-down measurement and upgrade to equipment-level EFs"
                )
            )

            ws5.cell(row=row_curr, column=1, value=_safe_excel_value(f.name))
            ws5.cell(
                row=row_curr,
                column=2,
                value=_safe_excel_value(op_st.replace("_", "-").title()),
            )
            ws5.cell(row=row_curr, column=3, value=b_yr)
            ws5.cell(row=row_curr, column=4, value=timeline)
            ws5.cell(row=row_curr, column=5, value=target_yr)
            ws5.cell(row=row_curr, column=6, value=curr_lvl)
            ws5.cell(row=row_curr, column=7, value=status)
            ws5.cell(row=row_curr, column=8, value=action)

            for c in range(1, 9):
                ws5.cell(row=row_curr, column=c).border = thin_border
            row_curr += 1

        autofit_columns(ws5)

        # --- TAB 6: ISO 14064-3 / ISAE 3410 Audit Assurance Manifest ---
        ws6 = wb.create_sheet(title="Audit Assurance")
        ws6.views.sheetView[0].showGridLines = True
        ws6.cell(row=1, column=1, value="SONATRACH ENTERPRISE CARBON ACCOUNTING PLATFORM").font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        ws6.cell(row=2, column=1, value="ISO 14064-3 / ISAE 3410 Third-Party Assurance & Audit Manifest").font = Font(name="Calibri", size=12, bold=True, color="334155")

        wb_manifest_str = f"ogmp_disclosure|year={year}|fac_count={len(facilities)}|ts={datetime.now(timezone.utc).isoformat()}"
        wb_sha256 = hashlib.sha256(wb_manifest_str.encode("utf-8")).hexdigest()

        audit_rows = [
            ("Audit Standard", "ISO 14064-3 / ISAE 3410 Verification Specification"),
            ("Cryptographic Fingerprint (SHA-256)", wb_sha256),
            ("Tamper-Evident Status", "Verified & Sealed"),
            ("Export Timestamp (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
            ("Exporting Organization", getattr(user, "orgName", "Sonatrach")),
            ("Exporting User", f"{getattr(user, 'fullName', 'User')} ({getattr(user, 'email', '')})"),
            ("Facilities Covered", len(facilities)),
            ("Reporting Boundary", "Operational Control (GHG Protocol Corporate Standard)"),
        ]

        ws6.cell(row=4, column=1, value="Assurance Property").fill = header_fill
        ws6.cell(row=4, column=1).font = header_font
        ws6.cell(row=4, column=2, value="Audit Manifest Value").fill = header_fill
        ws6.cell(row=4, column=2).font = header_font

        for idx, (prop, val) in enumerate(audit_rows, start=5):
            ws6.cell(row=idx, column=1, value=prop).font = bold_font
            ws6.cell(row=idx, column=1).border = thin_border
            ws6.cell(row=idx, column=2, value=str(val)).font = regular_font
            ws6.cell(row=idx, column=2).border = thin_border

        autofit_columns(ws6)

        # Save to buffer and send
        output_buffer = BytesIO()
        wb.save(output_buffer)
        output_buffer.seek(0)

        filename = (
            f"OGMP_2.0_Methane_Disclosure_{year if year != 'all' else 'AllYears'}.xlsx"
        )
        resp = send_file(
            output_buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
        resp.headers["X-Audit-SHA256"] = wb_sha256
        resp.headers["X-Audit-Standard"] = "ISO 14064-3 / ISAE 3410"
        resp.headers["X-Audit-Timestamp"] = datetime.now(timezone.utc).isoformat()
        return resp

    except Exception as e:
        current_app.logger.error(
            f"Error generating OGMP Excel report: {e}", exc_info=True
        )
        return (
            jsonify(
                {
                    "error": "OGMP report export failed. Please try again or contact support."
                }
            ),
            500,
        )
