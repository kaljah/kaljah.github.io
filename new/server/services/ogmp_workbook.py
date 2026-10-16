"""The UNEP / IMEO OGMP 2.0 member disclosure workbook (GET /api/reports/ogmp-export).

One function per sheet, split out of routes/reports_ogmp.export_ogmp_excel (a 770-line function) on 2026-10-16;
the workbook is unchanged.
"""
from datetime import datetime, timezone

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from extensions import db
from models import BaseYearRecalculation, Emission, Facility, Goal, OgmpSurvey, ProductionData
from services.audit_chain import data_fingerprint
from services.dashboard_filters import production_gas_m3
from services.labels import process_label
from services.ogmp import compute_facility_ogmp_level, ogmp_level_for

# Official UNEP palette
UNEP_NAVY = "1E3A8A"
UNEP_BLUE = "2563EB"
UNEP_TEAL = "0D9488"
GOLD_AMBER = "D97706"

OGMP_SOURCE_MAP = {
    "combustion": "Combustion", "stationary_combustion": "Combustion", "mobile": "Combustion",
    "flaring": "Flaring",
    "fugitive": "Fugitive", "fugitive_component": "Fugitive", "equipment_fugitive": "Fugitive",
    "pneumatic": "Vented", "pneumatic_devices": "Vented", "venting": "Vented", "blowdown": "Vented",
    "completions": "Vented", "tank": "Vented", "tank_flashing": "Vented", "liquids_unloading": "Vented",
    "unloading": "Vented",
    "agr": "Process", "dehydrator": "Process",
}

LEVEL_NAMES = {
    1: "Level 1 (Asset-level estimate)",
    2: "Level 2 (Generic factors)",
    3: "Level 3 (Source-type factors)",
    4: "Level 4 (Source-specific / measured)",
    5: "Level 5 (Reconciled with site measurement)",
}

INVENTORY_ROW_LIMIT = 2500


def _solid(color):
    return PatternFill(start_color=color, end_color=color, fill_type="solid")


class Styles:
    header_fill = _solid(UNEP_NAVY)
    sub_fill = _solid(UNEP_BLUE)
    accent_fill = _solid(UNEP_TEAL)
    gold_fill = _solid(GOLD_AMBER)
    label_fill = _solid("E2E8F0")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=15, bold=True, color=UNEP_NAVY)
    sub_title_font = Font(name="Calibri", size=11, italic=True, color="475569")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)
    mono_font = Font(name="Consolas", size=10)
    _side = Side(style="thin", color="CBD5E1")
    thin_border = Border(left=_side, right=_side, top=_side, bottom=_side)


class Context:
    """What every sheet needs: the requesting user, the filters and the facilities in scope."""

    def __init__(self, user, year, year_filter, facility_filter, allowed_fids, facilities, safe):
        self.user = user
        self.year = year  # the request's text ("all" or a year)
        self.year_filter = year_filter
        self.facility_filter = facility_filter
        self.allowed_fids = allowed_fids
        self.facilities = facilities
        self.safe = safe  # routes.reports._safe_excel_value
        # the declaring account as it is: no invented organisation, name or address (review 2026-10-16)
        self.company_name = getattr(user, "orgName", None) or ""
        self.assessor_name = getattr(user, "fullName", None) or ""
        self.assessor_email = getattr(user, "email", None) or ""
        self._ch4 = {}
        self._td = {}

    def bottom_up_ch4(self, fac):
        """Verified Scope 1 CH4 (t) of a facility for the period."""
        if fac.id not in self._ch4:
            q = db.session.query(db.func.sum(Emission.ch4_emissions)).filter(
                Emission.facility_id == fac.id, Emission.status == "Verified")
            if self.year_filter:
                q = q.filter(Emission.year == self.year_filter)
            self._ch4[fac.id] = q.scalar() or 0.0
        return self._ch4[fac.id]

    def top_down_ch4(self, fac):
        """Mean of the facility's survey estimates (t CH4 / yr) for the period."""
        if fac.id not in self._td:
            q = db.session.query(db.func.avg(OgmpSurvey.estimated_annual_tch4)).filter(OgmpSurvey.facility_id == fac.id)
            if self.year_filter:
                q = q.filter(OgmpSurvey.year == self.year_filter)
            self._td[fac.id] = q.scalar() or 0.0
        return self._td[fac.id]


def style_header_row(ws, row_idx, fill):
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(row=row_idx, column=col)
        cell.fill = fill
        cell.font = Styles.header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def autofit_columns(ws):
    for col in ws.columns:
        max_len = 0
        for cell in col:
            val_str = str(cell.value or "")
            if "\n" in val_str:
                val_str = max(val_str.split("\n"), key=len)
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 4, 12)


def _sheet(wb, title, heading, subtitle=None):
    ws = wb.create_sheet(title=title)
    ws.views.sheetView[0].showGridLines = True
    ws.cell(row=1, column=1, value=heading).font = Styles.title_font
    if subtitle:
        ws.cell(row=2, column=1, value=subtitle).font = Styles.sub_title_font
    return ws


def _headers(ws, row, labels, fill):
    for col, label in enumerate(labels, start=1):
        ws.cell(row=row, column=col, value=label)
    style_header_row(ws, row, fill)


def _data_row(ws, row, values):
    for col, value in enumerate(values, start=1):
        ws.cell(row=row, column=col, value=value)
    for col in range(1, len(values) + 1):
        ws.cell(row=row, column=col).border = Styles.thin_border


def _facility_name(obj):
    if obj.facility:
        return obj.facility.name
    fac = db.session.get(Facility, obj.facility_id) if obj.facility_id else None
    return fac.name if fac else "Unknown"


def _target_year(fac):
    op_st = fac.operator_status or "operated"
    b_yr = fac.ogmp_membership_year or 2023
    return op_st, b_yr, b_yr + (3 if op_st == "operated" else 5)


def sheet_profile(wb, ctx):
    ws = _sheet(wb, "0. Company Profile", "UNITED NATIONS ENVIRONMENT PROGRAMME (UNEP) — IMEO")
    ws.cell(row=2, column=1, value="Oil & Gas Methane Partnership 2.0 (OGMP 2.0) — Annual Member Reporting Template").font = Styles.sub_title_font
    ws.cell(row=3, column=1, value="Official Member Disclosure & Compliance Artifact (Revision 2024/2025)").font = Styles.regular_font
    for col, label in enumerate(("UNEP IMEO Reporting Attribute", "Member Entity Disclosure Value",
                                 "Official Guidance / Reference"), start=1):
        ws.cell(row=5, column=col, value=label).fill = Styles.header_fill
        ws.cell(row=5, column=col).font = Styles.header_font
    rows = [
        ("Reporting Member Company", ctx.company_name, "Registered UNEP OGMP 2.0 Signatory Entity"),
        ("UNEP Member Identifier", "", "Official Member Tracking Code (to be completed by the member)"),
        ("Lead Reporting Officer", f"{ctx.assessor_name} ({ctx.assessor_email})" if ctx.assessor_email
         else ctx.assessor_name, "Designated Company Focal Point"),
        ("Reporting Period (Year)", str(ctx.year if ctx.year != "all" else datetime.now().year), "Annual Measurement & Reporting Cycle"),
        ("Date of Disclosure", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), "Filing Generation Timestamp"),
        ("Reporting Framework Standard", "OGMP 2.0 Technical Guidance Document (TGD)", "Level 1 to Level 5 Measurement & Reconciliation"),
        ("Operational Boundary Scope", "Operational Control & Material Equity Stakes", "100% of Operated Assets, Equity Share for NOVs"),
        ("Operated Facilities Included", str(len(ctx.facilities)), "Assets actively operated within reporting scope"),
        ("Upstream Methane Target Intensity", "0.20% of marketed natural gas", "UNEP IMEO Gold Standard Upstream Benchmark"),
        ("Midstream Methane Target Intensity", "0.05% of natural gas throughput", "UNEP IMEO Gold Standard Midstream Benchmark"),
        ("Materiality Threshold", "5% of operated methane footprint", "Threshold for detailed source measurement"),
        ("Gold Standard Pathway Target", "3 Years (Operated) / 5 Years (Non-Operated)", "Deadline from base year to reach Level 4/5 Gold Standard"),
        ("GWP Standard Basis", "IPCC AR5 (100-Year CH4 GWP = 28.0)", "IPCC Assessment Report 100-year horizon"),
    ]
    for r_idx, (attr, val, ref) in enumerate(rows, start=6):
        ws.cell(row=r_idx, column=1, value=attr).font = Styles.bold_font
        ws.cell(row=r_idx, column=1).fill = Styles.label_fill
        ws.cell(row=r_idx, column=1).border = Styles.thin_border
        ws.cell(row=r_idx, column=2, value=ctx.safe(str(val))).font = Styles.regular_font
        ws.cell(row=r_idx, column=2).border = Styles.thin_border
        ws.cell(row=r_idx, column=3, value=ref).font = Styles.regular_font
        ws.cell(row=r_idx, column=3).border = Styles.thin_border
    autofit_columns(ws)


def _summary_targets(ws, ctx):
    """Row 3: the emission goal and the active base year from Manage Data."""
    goal = Goal.query.filter_by(year=ctx.year_filter if ctx.year_filter else datetime.now().year).first()
    base_year = BaseYearRecalculation.query.order_by(BaseYearRecalculation.recalc_date.desc()).first()
    if goal:
        ws.cell(row=3, column=1,
                value=f"Emission Target {goal.year}: {float(goal.target_amount or 0):,.0f} tCO₂e").font = Styles.bold_font
    if base_year:
        text = f"Active Base Year: {base_year.year}"
        if base_year.reason:
            text += f" — {base_year.reason[:80]}"
        ws.cell(row=3, column=6 if goal else 1, value=ctx.safe(text)).font = Styles.bold_font


def _loss_rate(bu_ch4, gas_m3, segment, ch4_density):
    """(loss rate % or None, target %, compliance text)."""
    ch4_vol_m3 = (bu_ch4 * 1000.0) / ch4_density if bu_ch4 > 0 else 0.0
    target_rate = 0.20 if "upstream" in (segment or "Upstream").lower() else 0.05
    if gas_m3 > 0:
        rate = ch4_vol_m3 / gas_m3 * 100.0
        return rate, target_rate, "Compliant" if rate <= target_rate else "Non-Compliant"
    if bu_ch4 > 0:
        return None, target_rate, "Non-Compliant (Missing Production Data)"
    return 0.0, target_rate, "N/A (No Activity)"


def sheet_summary(wb, ctx, ch4_density):
    """Executive summary per facility; returns {facility id: OGMP level}."""
    ws = _sheet(wb, "1. Executive Summary", "OGMP 2.0 COMPLIANCE & ASSET SUMMARY")
    ws.cell(row=2, column=1, value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Reporting Period: "
                                   f"{ctx.year if ctx.year != 'all' else 'All Active Years'}").font = Styles.regular_font
    _summary_targets(ws, ctx)
    _headers(ws, 4, ["Facility Name", "Code", "Segment", "Operator Status", "Country", "Equity (%)", "Base Year",
                     "Target Gold Year", "Current Level", "Gas Production (m³)", "Bottom-Up CH₄ (t)",
                     "Top-Down CH₄ (t)", "Loss Rate (%)", "Gold Target (%)", "Target Compliance", "Pathway Status"],
             Styles.header_fill)
    levels = {}
    for row, f in enumerate(ctx.facilities, start=5):
        op_st, b_yr, target_yr = _target_year(f)
        bu_ch4, td_ch4 = ctx.bottom_up_ch4(f), ctx.top_down_ch4(f)
        prod_q = ProductionData.query.filter(ProductionData.facility_id == f.id)
        if ctx.year_filter:
            prod_q = prod_q.filter(ProductionData.year == ctx.year_filter)
        gas_m3 = sum(production_gas_m3(p) or 0.0 for p in prod_q.all())
        rate, target_rate, compliance = _loss_rate(bu_ch4, gas_m3, f.segment, ch4_density)
        level = compute_facility_ogmp_level(f, year=ctx.year_filter, top_down_tch4=td_ch4, bottom_up_tch4=bu_ch4)
        levels[f.id] = level
        pathway = ("Gold Standard Achieved" if level == 5
                   else ("On Track" if (ctx.year_filter or datetime.now().year) <= target_yr else "Overdue"))
        _data_row(ws, row, [
            ctx.safe(f.name), ctx.safe(f.code or "N/A"), ctx.safe(f.segment or "Upstream"),
            ctx.safe(op_st.replace("_", "-").title()), ctx.safe(f.country or "Algeria"),
            float(f.equity_share_pct or 100.0), b_yr, target_yr, f"Level {level}", round(gas_m3, 2),
            round(bu_ch4, 2), round(td_ch4, 2), round(rate, 4) if rate is not None else "N/A", target_rate,
            compliance, pathway])
    autofit_columns(ws)
    return levels


def sheet_inventory(wb, ctx):
    """Source-level inventory (Verified records); returns the Level 4+ records with their facility names."""
    ws = _sheet(wb, "2. Bottom-Up Inventory", "OGMP 2.0 SOURCE-LEVEL EMISSIONS INVENTORY (L1 - L4)")
    _headers(ws, 3, ["Record ID", "Facility", "Year", "Month", "Process / Category", "Equipment / Source Code",
                     "Activity Quantity", "Unit", "EF Source", "CH₄ Emissions (t)", "CO₂e Total (t)", "OGMP Level",
                     "Calculation Method", "OGMP Source Category"], Styles.sub_fill)
    q = Emission.query.filter(Emission.status == "Verified")
    if ctx.allowed_fids is not None:
        q = q.filter(Emission.facility_id.in_(ctx.allowed_fids))
    if ctx.year_filter:
        q = q.filter_by(year=ctx.year_filter)
    if ctx.facility_filter:
        q = q.filter_by(facility_id=ctx.facility_filter)
    total = q.count()
    if total > INVENTORY_ROW_LIMIT:
        ws.cell(row=2, column=1, value=f"⚠ NOTICE: Inventory truncated to 2,500 records. Full dataset contains {total} "
                                       "records. Apply facility/year filters for complete disclosure.").font = Font(color="FF0000", bold=True)
    level4 = []
    rows = q.order_by(Emission.year.desc(), Emission.month.desc()).limit(INVENTORY_ROW_LIMIT).all()
    for row, em in enumerate(rows, start=4):
        fac_name = _facility_name(em)
        lvl = ogmp_level_for(em)
        if lvl >= 4:
            level4.append((em, fac_name))
        _data_row(ws, row, [
            ctx.safe(em.record_id or f"EM-{em.id}"), ctx.safe(fac_name), em.year, em.month,
            ctx.safe(process_label(em.process_type, "N/A")), ctx.safe(em.source_type_code or em.equipment_id or "N/A"),
            em.quantity or 0, ctx.safe(em.unit or ""), ctx.safe(em.factor_source or "API Compendium 2021"),
            round(em.ch4_emissions or 0, 4), round(em.co2e_total or 0, 2), f"Level {lvl}",
            ctx.safe(em.calc_method or ("Facility Specific" if lvl >= 4 else "Generic EF")),
            ctx.safe(OGMP_SOURCE_MAP.get((em.process_type or "").lower(), "Other"))])
    autofit_columns(ws)
    return level4


def sheet_surveys(wb, ctx):
    ws = _sheet(wb, "3. Top-Down Surveys", "OGMP 2.0 SITE-LEVEL MEASUREMENT CAMPAIGNS (L4 / L5)")
    _headers(ws, 3, ["Survey ID", "Facility", "Year", "Survey Date", "Technology / Method",
                     "Measured Rate (kg CH₄/hr)", "Operating Hours (hr/yr)", "Annualized Rate (tCH₄/yr)",
                     "Detection Limit (kg/hr)", "Instrument / Vendor", "Reconciliation Status", "Operator Notes"],
             Styles.accent_fill)
    q = OgmpSurvey.query
    if ctx.allowed_fids is not None:
        q = q.filter(OgmpSurvey.facility_id.in_(ctx.allowed_fids))
    if ctx.year_filter:
        q = q.filter_by(year=ctx.year_filter)
    if ctx.facility_filter:
        q = q.filter_by(facility_id=ctx.facility_filter)
    for row, s in enumerate(q.order_by(OgmpSurvey.survey_date.desc()).all(), start=4):
        _data_row(ws, row, [
            ctx.safe(f"OGMP-{s.id}"), ctx.safe(_facility_name(s)), s.year, ctx.safe(s.survey_date),
            ctx.safe(s.survey_type), s.measured_rate_kg_hr, s.operating_hours_year or 8760, s.estimated_annual_tch4,
            ctx.safe(s.detection_threshold or "N/A"), ctx.safe(s.instrument_vendor or "N/A"),
            ctx.safe(s.reconciliation_status or "Reconciled"), ctx.safe(s.operator_notes or "")])
    autofit_columns(ws)


def _reconciliation(bu_total, td_total, thresh):
    """(variance text, flag text, status, explanation) of bottom-up against top-down."""
    var_pct = None
    if bu_total > 0 and td_total > 0:
        var_pct = round(((td_total - bu_total) / bu_total * 100.0), 2)
        is_flagged = abs(var_pct) > thresh
        status, var_str = ("Discrepancy Flagged" if is_flagged else "Reconciled"), f"{var_pct:+.2f}%"
    elif bu_total == 0 and td_total > 0:
        is_flagged, status, var_str = True, "No Bottom-Up Inventory — Discrepancy Flagged", "N/A (No BU)"
    elif td_total == 0:
        is_flagged, status, var_str = False, "Pending Measurement", "Pending TD"
    else:
        is_flagged, status, var_str = False, "No Data", "No Data"
    if var_pct is None and not is_flagged:
        flag = "NOT ASSESSED"
        note = ("No top-down measurement for this period: schedule a site-level survey"
                if status == "Pending Measurement" else "No bottom-up or top-down data")
    elif is_flagged:
        flag = "FLAGGED (> Threshold)"
        note = ("Site measurement exceeds bottom-up inventory. Investigate uncombusted slip "
                "or uninventoried vent sources." if (var_pct is None or var_pct > 0)
                else "Site measurement is below the bottom-up inventory. Review the "
                     "inventory factors and the survey coverage.")
    else:
        flag, note = "PASS", "Within acceptable variance bounds"
    return var_str, flag, status, note


def sheet_reconciliation(wb, ctx):
    ws = _sheet(wb, "4. Reconciliation Matrix", "OGMP 2.0 BOTTOM-UP VS TOP-DOWN RECONCILIATION MATRIX")
    _headers(ws, 3, ["Facility", "Reporting Year", "Segment", "Bottom-Up Total (tCH₄)", "Top-Down Survey Total (tCH₄)",
                     "Reconciliation Variance (%)", "Threshold (%)", "Discrepancy Flag", "Reconciliation Status",
                     "Operator Explanation & Remediation"], Styles.gold_fill)
    for row, f in enumerate(ctx.facilities, start=4):
        bu_total, td_total = ctx.bottom_up_ch4(f), ctx.top_down_ch4(f)
        thresh = f.reconciliation_threshold or 20.0
        var_str, flag, status, note = _reconciliation(bu_total, td_total, thresh)
        _data_row(ws, row, [
            ctx.safe(f.name), ctx.safe(ctx.year if ctx.year != "all" else "All Years"), ctx.safe(f.segment or "Upstream"),
            round(bu_total, 2), round(td_total, 2), var_str, f"±{thresh}%", flag, ctx.safe(status), ctx.safe(note)])
    autofit_columns(ws)


def _milestone(fac, level, target_yr, ref_year):
    """(milestone status, next action) from the latest survey and the facility's level."""
    latest = (OgmpSurvey.query.filter_by(facility_id=fac.id)
              .order_by(OgmpSurvey.year.desc(), OgmpSurvey.survey_date.desc()).first())
    reconciled = latest is not None and latest.reconciliation_status == "Reconciled" and not latest.variance_flag
    if level == 5 or reconciled:
        status = "Gold Standard Achieved"
    elif ref_year < target_yr:
        status = f"On Track ({target_yr - ref_year} yr remaining)"
    elif ref_year == target_yr:
        status = "Due this year"
    else:
        status = "Overdue - Action Plan Required"
    if reconciled:
        action = "Maintain annual top-down measurement campaigns"
    elif latest is not None:
        action = "Reconcile measurement discrepancy with inventory"
    else:
        action = "Schedule aerial / satellite top-down measurement and upgrade to equipment-level EFs"
    return status, action


def sheet_roadmap(wb, ctx, levels):
    ws = _sheet(wb, "5. Gold Standard Roadmap", "OGMP 2.0 GOLD STANDARD PATHWAY & MILESTONE TRACKER")
    _headers(ws, 3, ["Facility", "Operator Type", "OGMP Base Year", "Compliance Timeline", "Target Deadline Year",
                     "Current Level", "Milestone Status", "Next Mandatory Action"], Styles.header_fill)
    for row, f in enumerate(ctx.facilities, start=4):
        op_st, b_yr, target_yr = _target_year(f)
        timeline = "3 Years (Operated Asset)" if op_st == "operated" else "5 Years (Non-Operated Asset)"
        level = levels.get(f.id)
        level_text = LEVEL_NAMES.get(level, f"Level {level}" if level else "Not assessed")
        status, action = _milestone(f, level, target_yr, ctx.year_filter or datetime.now().year)
        _data_row(ws, row, [ctx.safe(f.name), ctx.safe(op_st.replace("_", "-").title()), b_yr, timeline, target_yr,
                            level_text, status, action])
    autofit_columns(ws)


def sheet_level4(wb, ctx, level4):
    ws = _sheet(wb, "6. Level 4 Direct Measurements", "OGMP 2.0 LEVEL 4 DIRECT SOURCE MEASUREMENTS",
                "Component-level empirical measurements & calibrated specific factors per UNEP TGD")
    _headers(ws, 4, ["Record ID", "Facility Name", "Reporting Year", "Process / Category", "Equipment Tag",
                     "Measurement Technology", "Activity Qty", "Unit", "Component CH₄ (t)", "Uncertainty (95% CI ±%)",
                     "Measurement Protocol"], Styles.accent_fill)
    if not level4:
        ws.cell(row=5, column=1, value="No direct Level 4 empirical measurements logged for this scope.").font = Styles.sub_title_font
        ws.cell(row=5, column=11, value="Upgrade Level 1-3 sources to Level 4 via OGI/Hi-Flow campaigns.").font = Styles.sub_title_font
    for row, (em, fac_name) in enumerate(level4, start=5):
        u_pct = em.uncertainty_pct if getattr(em, "uncertainty_pct", None) is not None else 15.0
        _data_row(ws, row, [
            ctx.safe(em.record_id or f"EM-{em.id}"), ctx.safe(fac_name), em.year,
            ctx.safe(process_label(em.process_type, "N/A")),
            ctx.safe(em.source_type_code or em.equipment_id or "Direct Component"),
            ctx.safe(em.calc_method or "Optical Gas Imaging (OGI) + High-Flow"), em.quantity or 0,
            ctx.safe(em.unit or ""), round(em.ch4_emissions or 0, 4), f"±{float(u_pct):.1f}%",
            "EPA Method 21 / OGI EN 15446"])
    autofit_columns(ws)


def sheet_joint_ventures(wb, ctx):
    ws = _sheet(wb, "7. Non-Operated Assets (JV)", "OGMP 2.0 NON-OPERATED ASSETS & JOINT VENTURE DISCLOSURES",
                "Working interest equity stakes & non-operated partner reporting under UNEP IMEO rules")
    _headers(ws, 4, ["Asset Name", "Country", "Basin / Field", "Segment", "Operating Partner", "Equity Share (%)",
                     "Base Year", "Target Gold Year (5-Yr)", "Equity Share CH₄ (t)", "Reporting Source"], Styles.sub_fill)
    jvs = [f for f in ctx.facilities
           if (f.operator_status or "operated") == "non_operated" or float(f.equity_share_pct or 100.0) < 100.0]
    if not jvs:
        ws.cell(row=5, column=1, value="No non-operated minority joint venture assets found in active filter scope.").font = Styles.sub_title_font
        ws.cell(row=5, column=10, value="All assets currently declared under 100% operational control.").font = Styles.sub_title_font
    for row, f in enumerate(jvs, start=5):
        b_yr = f.ogmp_membership_year or 2023
        # an unrecorded equity share is said so (it was shown as 50 %); review 2026-10-16
        eq_pct = float(f.equity_share_pct) if f.equity_share_pct is not None else None
        _data_row(ws, row, [
            ctx.safe(f.name), ctx.safe(f.country or "Algeria"), ctx.safe(f.region or f.field or ""),
            ctx.safe(f.segment or "Upstream"), ctx.safe(f.boundary_detail or "Partner Joint Venture"),
            f"{eq_pct:.1f}%" if eq_pct is not None else "Equity share not recorded", b_yr, b_yr + 5,
            round(ctx.bottom_up_ch4(f) * (eq_pct / 100.0), 3) if eq_pct is not None else "N/A",
            "Partner Operator Data Exchange / Equity Model"])
    autofit_columns(ws)


def sheet_audit(wb, ctx, sha256):
    ws = wb.create_sheet(title="Audit Assurance")
    ws.views.sheetView[0].showGridLines = True
    title = f"{ctx.company_name.upper()} ENTERPRISE CARBON ACCOUNTING PLATFORM".strip()
    ws.cell(row=1, column=1, value=ctx.safe(title)).font = Font(
        name="Calibri", size=14, bold=True, color=UNEP_NAVY)
    ws.cell(row=2, column=1, value="Cryptographic Audit Assurance Manifest & Integrity Seal").font = Font(
        name="Calibri", size=12, bold=True, color="334155")
    rows = [
        ("Data Fingerprint (SHA-256)", sha256),
        ("Covers", "Every cell of all official sheets of this UNEP OGMP 2.0 filing workbook"),
        ("Check", "Matches the REPORT entry of the immutable audit log written when exported"),
        ("Export Timestamp (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
        ("Exporting Organization", ctx.safe(ctx.company_name)),
        ("Exporting User & Role", f"{ctx.assessor_name} ({getattr(ctx.user, 'email', '')}) - Role: {ctx.user.role}"),
        ("Facilities Covered", len(ctx.facilities)),
        ("UNEP IMEO Template Spec", "OGMP 2.0 Member Submission Format (TGD 2024/2025)"),
    ]  # no "digital seal" row: the platform has no HMAC or ledger seal, only the fingerprint in the audit log
    for col, label in enumerate(("Assurance Property", "Audit Manifest Value"), start=1):
        ws.cell(row=4, column=col, value=label).fill = Styles.header_fill
        ws.cell(row=4, column=col).font = Styles.header_font
    for idx, (prop, val) in enumerate(rows, start=5):
        ws.cell(row=idx, column=1, value=prop).font = Styles.bold_font
        ws.cell(row=idx, column=1).border = Styles.thin_border
        mono = "SHA-256" in prop
        ws.cell(row=idx, column=2, value=str(val)).font = Styles.mono_font if mono else Styles.regular_font
        ws.cell(row=idx, column=2).border = Styles.thin_border
    autofit_columns(ws)


def build_workbook(ctx, ch4_density):
    """(workbook, SHA-256 fingerprint of its official sheets)."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    sheet_profile(wb, ctx)
    levels = sheet_summary(wb, ctx, ch4_density)
    level4 = sheet_inventory(wb, ctx)
    sheet_surveys(wb, ctx)
    sheet_reconciliation(wb, ctx)
    sheet_roadmap(wb, ctx, levels)
    sheet_level4(wb, ctx, level4)
    sheet_joint_ventures(wb, ctx)
    sha256 = data_fingerprint([[ws.title, [list(r) for r in ws.iter_rows(values_only=True)]] for ws in wb.worksheets])
    sheet_audit(wb, ctx, sha256)
    return wb, sha256
