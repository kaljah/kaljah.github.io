"""EU CBAM communication template workbook (GET /api/reports/cbam-export?format=excel).

One function per sheet, split out of routes/reports_cbam.export_cbam_report on 2026-10-16; the workbook is
unchanged.
"""
import hashlib
import json

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from services.cbam_data import (RecordFigures, _get_facility_production_tonnes, _get_facility_scope1_split,
                                _get_facility_scope2_metrics, fingerprint_row, get_cbam_aggregated_category,
                                get_cbam_production_route, quarter_of)

# Official European Commission CBAM palette
EU_NAVY = "003399"     # EU Reflex Blue
BLUE_SUB = "1E40AF"    # sub header
BORDER = "CBD5E1"
ZEBRA = "F8FAFC"       # alternating rows

DIRECT_BOUNDARY = "Gate-to-gate installation boundary including combustion, reaction, flare, and on-site electricity"
# the declarant's statement, to be signed by them (the export certified it "under penalty of perjury" itself)
CERTIFICATION = (
    "To be signed by the declarant: the specific embedded direct and indirect emissions reported in this file were "
    "determined with the monitoring methodology of Implementing Regulation (EU) 2023/1773.")
NO_SCOPE2 = "No verified Scope 2 electricity data for this facility and year"


def _solid(color):
    return PatternFill(start_color=color, end_color=color, fill_type="solid")


class Styles:
    header_fill = _solid(EU_NAVY)
    sub_fill = _solid(BLUE_SUB)
    label_fill = _solid("F1F5F9")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color=EU_NAVY)
    subtitle_font = Font(name="Calibri", size=10, italic=True, color="475569")
    bold = Font(name="Calibri", size=11, bold=True)
    regular = Font(name="Calibri", size=11)
    mono = Font(name="Consolas", size=10)
    _side = Side(style="thin", color=BORDER)
    thin_border = Border(left=_side, right=_side, top=_side, bottom=_side)


def style_header_row(ws, row_idx, fill=Styles.header_fill, font=Styles.header_font):
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(row=row_idx, column=col)
        cell.fill = fill
        cell.font = font
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


def _sheet(wb, title, heading, subtitle, headers=None):
    ws = wb.create_sheet(title=title)
    ws.views.sheetView[0].showGridLines = True
    ws.cell(row=1, column=1, value=heading).font = Styles.title_font
    ws.cell(row=2, column=1, value=subtitle).font = Styles.subtitle_font
    if headers:
        for col, h in enumerate(headers, start=1):
            ws.cell(row=4, column=col, value=h)
        style_header_row(ws, 4)
    return ws


def _cell(ws, row, col, value, font=None, number_format=None):
    cell = ws.cell(row=row, column=col, value=value)
    if font is not None:
        cell.font = font
    if number_format is not None:
        cell.number_format = number_format
    return cell


def _finish_row(ws, row, ncols):
    """Borders on the row's cells, and the zebra fill on even rows."""
    for col in range(1, ncols + 1):
        ws.cell(row=row, column=col).border = Styles.thin_border
        if row % 2 == 0:
            ws.cell(row=row, column=col).fill = _solid(ZEBRA)


def sheet_installations(wb, ctx):
    """A_InstData: installation and operator data, and the register of installations."""
    ws = _sheet(wb, "A_InstData", "EUROPEAN COMMISSION — DIRECTORATE-GENERAL TAXATION AND CUSTOMS UNION",
                "CBAM Communication Template for Installations outside the EU (Regulation (EU) 2023/956 & "
                "Implementing Reg (EU) 2023/1773)")
    fields = [
        ("Reporting Period (Start Date)", f"{ctx.rep_year_str}-01-01"),
        ("Reporting Period (End Date)", f"{ctx.rep_year_str}-12-31"),
        ("Reporting Year", ctx.rep_year_str),
        ("Name of the Operator", ctx.company_name),
        ("Unique Operator Identifier", ctx.op_id),
        ("Country of Operator", f"{ctx.op_country} ({ctx.op_iso})"),
        ("Country Code (ISO 3166-1 alpha-2)", ctx.op_iso),
        ("Primary Contact Person", f"{ctx.assessor_name} ({ctx.assessor_email})"),
        ("Role of Declarant", "Non-EU Installation Operator / Direct Exporter"),
        ("EU ETS Benchmark Reference", "Commission Implementing Regulation (EU) 2021/447"),
        ("Applicable Methodology", "Annex III of Implementing Regulation (EU) 2023/1773 (Calculation-based / Activity-based)"),
        ("Accreditation Standard for Verifier", "ISO 14065 / ISO 14064-3 Reasonable Assurance"),
        ("Operating Facilities in Scope", len(ctx.facilities)),
        ("CBAM Export Records Count", len(ctx.records)),
    ]
    for col, label in enumerate(("Field Parameter", "Declared Value"), start=1):
        ws.cell(row=4, column=col, value=label).fill = Styles.header_fill
        ws.cell(row=4, column=col).font = Styles.header_font
    for idx, (prop, val) in enumerate(fields, start=5):
        _cell(ws, idx, 1, prop, Styles.bold).fill = Styles.label_fill
        ws.cell(row=idx, column=1).border = Styles.thin_border
        _cell(ws, idx, 2, ctx.safe(str(val)), Styles.regular).border = Styles.thin_border

    sub_row = len(fields) + 7
    _cell(ws, sub_row, 1, "REGISTERED PRODUCTION INSTALLATIONS & SITES", Styles.bold)
    for col, h in enumerate(["ID", "Installation Name", "Facility Code", "Segment", "Division / Region", "Country",
                             "Latitude", "Longitude", "Status"], start=1):
        ws.cell(row=sub_row + 1, column=col, value=h).fill = Styles.sub_fill
        ws.cell(row=sub_row + 1, column=col).font = Styles.header_font
        ws.cell(row=sub_row + 1, column=col).alignment = Alignment(horizontal="center", vertical="center")
    for idx, f in enumerate(ctx.facilities.values(), start=sub_row + 2):
        _cell(ws, idx, 1, f.id, Styles.regular)
        _cell(ws, idx, 2, ctx.safe(f.name), Styles.bold)
        _cell(ws, idx, 3, ctx.safe(f.code or f"{ctx.op_iso}-FAC-{f.id:03d}"), Styles.mono)
        _cell(ws, idx, 4, ctx.safe(f.segment or "Downstream"), Styles.regular)
        _cell(ws, idx, 5, ctx.safe(f"{f.division or ''} / {f.region or ''}"), Styles.regular)
        _cell(ws, idx, 6, ctx.safe(f.country or ctx.op_country), Styles.regular)
        _cell(ws, idx, 7, f.latitude if f.latitude is not None else "N/A", Styles.mono)
        _cell(ws, idx, 8, f.longitude if f.longitude is not None else "N/A", Styles.mono)
        _cell(ws, idx, 9, ctx.safe(f.operator_status or "Active Operational Control"), Styles.regular)
        _finish_row(ws, idx, 9)
    autofit_columns(ws)


def sheet_processes(wb, ctx):
    """B_Processes: aggregated goods categories and production routes."""
    ws = _sheet(wb, "B_Processes", "EU CBAM — AGGREGATED GOODS CATEGORIES & PRODUCTION PROCESSES",
                "Production routes, CN classifications and system boundaries under Annex II of Reg (EU) 2023/1773",
                ["Process ID", "Installation Name", "Facility Code", "Aggregated Goods Category", "CN Code (8-digit)",
                 "Commercial Product Name", "Production Route / Technology", "System Boundary Definition",
                 "Total Annual Production (t)", "EU Export Quantity (t)", "Share of EU Export (%)"])
    for idx, r in enumerate(ctx.records, start=5):
        qty = float(r.quantity_tonnes or 0.0)
        total_prod, _from_production = _get_facility_production_tonnes(r.facility_id, r.year, qty)
        _cell(ws, idx, 1, f"PROC-{r.id:04d}", Styles.mono)
        _cell(ws, idx, 2, ctx.safe(ctx.fac_name(r)), Styles.bold)
        _cell(ws, idx, 3, ctx.safe(ctx.fac_code(r)), Styles.mono)
        _cell(ws, idx, 4, get_cbam_aggregated_category(r.cn_code, r.product_name), Styles.bold)
        _cell(ws, idx, 5, ctx.safe(str(r.cn_code)), Styles.mono)
        _cell(ws, idx, 6, ctx.safe(r.product_name), Styles.regular)
        _cell(ws, idx, 7, get_cbam_production_route(r.cn_code, r.product_name), Styles.regular)
        _cell(ws, idx, 8, DIRECT_BOUNDARY, Styles.regular)
        _cell(ws, idx, 9, round(total_prod, 1), number_format="#,##0.0")
        _finish_row(ws, idx, 11)
    autofit_columns(ws)


def sheet_direct(wb, ctx):
    """C_Emissions: direct emissions split by the facility's Scope 1 families, and SEE_dir."""
    ws = _sheet(wb, "C_Emissions", "EU CBAM — DIRECT EMISSIONS & SPECIFIC EMBEDDED DIRECT (SEE_dir)",
                "Activity data, combustion, process stoichiometry, flaring and heat attribution under Reg (EU) 2023/1773",
                ["Record ID", "Product Name", "CN Code", "Quantity Exported (t)", "Combustion Emissions (tCO2e)",
                 "Process Reaction Emissions (tCO2e)", "Flaring & Venting (tCO2e)", "Measurable Net Heat (GJ)",
                 "Heat Emission Factor (tCO2/GJ)", "Attributed Direct Emissions (tCO2e)",
                 "Specific Direct Embedded (SEE_dir) (tCO2e/t)", "EU ETS Benchmark Benchmark (tCO2e/t)",
                 "Benchmark Alignment"])
    for idx, r in enumerate(ctx.records, start=5):
        qty = float(r.quantity_tonnes or 0.0)
        direct_see = float(r.specific_embedded_direct or 0.0)
        attr_direct = qty * direct_see
        comb_pct, proc_pct, flare_pct, _has_split = _get_facility_scope1_split(r.facility_id, r.year, ctx.statuses)
        ets_bench = 1.30 if "ammonia" in r.product_name.lower() else (0.28 if "diesel" in r.product_name.lower() else 0.85)
        alignment = "Compliant (Within Expected Envelope)" if direct_see <= ets_bench * 1.5 else "Higher Than Benchmark"
        _cell(ws, idx, 1, r.id, Styles.mono)
        _cell(ws, idx, 2, ctx.safe(r.product_name), Styles.bold)
        _cell(ws, idx, 3, ctx.safe(str(r.cn_code)), Styles.mono)
        _cell(ws, idx, 4, round(qty, 1), number_format="#,##0.0")
        _cell(ws, idx, 5, round(attr_direct * comb_pct, 1), number_format="#,##0.0")
        _cell(ws, idx, 6, round(attr_direct * proc_pct, 1), number_format="#,##0.0")
        _cell(ws, idx, 7, round(attr_direct * flare_pct, 1), number_format="#,##0.0")
        _cell(ws, idx, 8, round(0.0, 1), number_format="#,##0.0")  # measurable net heat
        _cell(ws, idx, 9, 0.0561, number_format="0.0000")  # heat emission factor
        _cell(ws, idx, 10, round(attr_direct, 1), number_format="#,##0.0")
        _cell(ws, idx, 11, round(direct_see, 4), number_format="0.0000")
        _cell(ws, idx, 12, ets_bench, number_format="0.0000")
        _cell(ws, idx, 13, alignment, Styles.bold)
        _finish_row(ws, idx, 13)
    autofit_columns(ws)


def sheet_electricity(wb, ctx):
    """D_Electricity: electricity consumption and SEE_indir."""
    ws = _sheet(wb, "D_Electricity", "EU CBAM — ELECTRICITY CONSUMPTION & SPECIFIC INDIRECT EMBEDDED (SEE_indir)",
                "Grid emission factors, on-site power generation and indirect emissions under Annex III Reg (EU) 2023/1773",
                ["Record ID", "Product Name", "CN Code", "Quantity Exported (t)", "Electricity Source",
                 "Process Electricity Consumed (MWh)", "Specific Electricity Consumption (MWh/t)",
                 "Electricity Emission Factor (tCO2/MWh)", "Attributed Indirect Emissions (tCO2e)",
                 "Specific Indirect Embedded (SEE_indir) (tCO2e/t)", "Accounting Basis"])
    for idx, r in enumerate(ctx.records, start=5):
        qty = float(r.quantity_tonnes or 0.0)
        indirect_see = float(r.specific_embedded_indirect or 0.0)
        country = ctx.fac_country(r)
        _mwh, grid_ef, supplier, has_s2 = _get_facility_scope2_metrics(r.facility_id, r.year, country, ctx.statuses)
        # without verified Scope 2 data there is no grid factor, so no electricity quantity to derive
        spec_mwh = (indirect_see / grid_ef) if grid_ef else None
        basis = "Verified Scope 2 Invoiced Metering + Grid EF" if has_s2 else NO_SCOPE2
        _cell(ws, idx, 1, r.id, Styles.mono)
        _cell(ws, idx, 2, ctx.safe(r.product_name), Styles.bold)
        _cell(ws, idx, 3, ctx.safe(str(r.cn_code)), Styles.mono)
        _cell(ws, idx, 4, round(qty, 1), number_format="#,##0.0")
        _cell(ws, idx, 5, ctx.safe(supplier), Styles.regular)
        _cell(ws, idx, 6, round(qty * spec_mwh, 1) if spec_mwh is not None else "N/A", number_format="#,##0.0")
        _cell(ws, idx, 7, round(spec_mwh, 4) if spec_mwh is not None else "N/A", number_format="0.0000")
        _cell(ws, idx, 8, grid_ef if grid_ef else "N/A", number_format="0.0000")
        _cell(ws, idx, 9, round(qty * indirect_see, 1), number_format="#,##0.0")
        _cell(ws, idx, 10, round(indirect_see, 4), number_format="0.0000")
        _cell(ws, idx, 11, basis, Styles.regular)
        _finish_row(ws, idx, 11)
    autofit_columns(ws)


def sheet_precursors(wb, ctx):
    """E_Precursors: Article 7 complex goods and their precursors."""
    ws = _sheet(wb, "E_Precursors", "EU CBAM — COMPLEX GOODS PRECURSORS & EMBEDDED ACCOUNTING",
                "Precursor consumption ratios and embedded emissions for complex goods under Article 7 Reg (EU) 2023/956",
                ["Complex Good Name", "CN Code", "Relevant Precursor Name", "Precursor CN Code",
                 "Precursor Country of Origin", "Precursor Consumption Ratio (t/t)", "Precursor SEE_dir (tCO2e/t)",
                 "Precursor SEE_indir (tCO2e/t)", "Precursor Total SEE (tCO2e/t)",
                 "Contribution to Complex Good (tCO2e/t)"])
    rows = []
    for r in ctx.records:
        if r.is_complex_good and r.precursor_name:
            ratio, p_dir, p_indir = (float(r.precursor_ratio or 0.0), float(r.precursor_see_dir or 0.0),
                                     float(r.precursor_see_indir or 0.0))
            p_tot = p_dir + p_indir
            rows.append((ctx.safe(r.product_name), ctx.safe(r.cn_code), ctx.safe(r.precursor_name),
                         ctx.safe(r.precursor_cn_code or "2814 10 00"),
                         ctx.safe(f"{ctx.fac_country(r)} (In-House / Attributed)"), ratio, p_dir, p_indir, p_tot,
                         ratio * p_tot))
    if not rows:
        _cell(ws, 5, 1, "No complex goods with upstream precursors declared for this reporting period under Article 7",
              Styles.subtitle_font)
        for col in range(1, 11):
            ws.cell(row=5, column=col).border = Styles.thin_border
    fonts = (Styles.bold, Styles.mono, Styles.regular, Styles.mono, Styles.regular)
    for idx, p in enumerate(rows, start=5):
        for col, value in enumerate(p, start=1):
            if col <= 5:
                _cell(ws, idx, col, value, fonts[col - 1])
            else:
                _cell(ws, idx, col, value, number_format="0.0000")
        _finish_row(ws, idx, 10)
    autofit_columns(ws)


def _totals_row(ws, row, label, sums, ncols):
    """A labelled totals row of SUM formulas over rows 5 .. row - 1 ({column: number format})."""
    _cell(ws, row, 1, label, Styles.bold)
    for col, fmt in sums.items():
        letter = get_column_letter(col)
        _cell(ws, row, col, f"=SUM({letter}5:{letter}{row - 1})", number_format=fmt).font = Styles.bold
    for col in range(1, ncols + 1):
        ws.cell(row=row, column=col).fill = Styles.label_fill
        ws.cell(row=row, column=col).border = Styles.thin_border


def sheet_summary(wb, ctx):
    """F_Summary: the communication summary for EU importers; returns the fingerprint rows."""
    ws = _sheet(wb, "F_Summary", "EU CBAM — OFFICIAL COMMUNICATION SUMMARY FOR EU IMPORTERS & DECLARANTS",
                "Core declaration dataset required for submission to the EU CBAM Transitional Registry (DG TAXUD)",
                ["Installation Name", "Installation Code", "Country of Origin", "Commercial Product Name",
                 "CN Code (8-digit)", "Aggregated Category", "Reporting Period", "Quantity Exported to EU (t)",
                 "Captured CO2 (t)", "Specific Direct Embedded (tCO2e/t)", "Specific Indirect Embedded (tCO2e/t)",
                 "Precursor Embedded (tCO2e/t)", "Total Specific Embedded (tCO2e/t)",
                 "Total Embedded Emissions (tCO2e)", "Origin Carbon Price Paid (EUR/t)",
                 "Net CBAM Embedded Emissions (tCO2e)"])
    fingerprint = []
    for idx, r in enumerate(ctx.records, start=5):
        fig = RecordFigures(r)
        _cell(ws, idx, 1, ctx.safe(ctx.fac_name(r)), Styles.bold)
        _cell(ws, idx, 2, ctx.safe(ctx.fac_code(r)), Styles.mono)
        _cell(ws, idx, 3, ctx.safe(f"{ctx.fac_country(r)} ({ctx.op_iso})"), Styles.regular)
        _cell(ws, idx, 4, ctx.safe(r.product_name), Styles.bold)
        _cell(ws, idx, 5, ctx.safe(str(r.cn_code)), Styles.mono)
        _cell(ws, idx, 6, ctx.safe(get_cbam_aggregated_category(r.cn_code, r.product_name)), Styles.bold)
        _cell(ws, idx, 7, ctx.safe(f"{r.year} - {quarter_of(r)}"), Styles.regular)
        _cell(ws, idx, 8, round(fig.qty, 1), number_format="#,##0.0")
        _cell(ws, idx, 9, round(float(r.captured_co2_tonnes or 0.0), 1), number_format="#,##0.0")
        _cell(ws, idx, 10, round(fig.direct, 4), number_format="0.0000")
        _cell(ws, idx, 11, round(fig.indirect, 4), number_format="0.0000")
        _cell(ws, idx, 12, round(fig.precursor, 4), number_format="0.0000")
        _cell(ws, idx, 13, round(fig.total_see, 4), number_format="0.0000")
        _cell(ws, idx, 14, round(fig.total_emissions, 1), number_format="#,##0.0")
        _cell(ws, idx, 15, float(r.carbon_price_paid_eur or 0.0), number_format="€#,##0.00")
        _cell(ws, idx, 16, round(fig.total_emissions, 1), number_format="#,##0.0")  # net = total embedded
        fingerprint.append(fingerprint_row(ctx, r, fig))
        _finish_row(ws, idx, 16)
    _totals_row(ws, len(ctx.records) + 5, "TOTAL DECLARED EXPORTS & EMBEDDED EMISSIONS",
                {8: "#,##0.0", 9: "#,##0.0", 14: "#,##0.0", 16: "#,##0.0"}, 16)
    autofit_columns(ws)
    return fingerprint


def _receipt_id(r, rate):
    if rate <= 0:
        return "N/A"
    notes_val = str(r.notes or "").strip()
    if notes_val and any(term in notes_val.lower() for term in ("receipt", "tax", "cert", "ref", "doc")):
        return notes_val
    return "Self-Declared / Pending Fiscal Proof"


def sheet_carbon_price(wb, ctx):
    """H_CarbonPrice: Article 9 carbon price paid in the country of origin."""
    ws = _sheet(wb, "H_CarbonPrice", "EU CBAM — ARTICLE 9 CARBON PRICE & FLARING FISCALITY PAID IN COUNTRY OF ORIGIN",
                "Details of carbon price and flaring penalties effectively paid under Article 9 of Regulation (EU) 2023/956",
                ["Record ID", "Installation Name", "Facility Code", "Commercial Product Name", "CN Code (8-digit)",
                 "Export Quantity (t)", "Applicable Legal Reference", "Carbon Tax / Flaring Rate (€/t)",
                 "Total Origin Price Paid (€)", "Eligible CBAM Deduction Status", "Treasury / Fiscal Receipt ID"])
    for idx, r in enumerate(ctx.records, start=5):
        qty = float(r.quantity_tonnes or 0.0)
        rate = float(r.carbon_price_paid_eur or 0.0)
        legal_ref = r.carbon_price_legal_ref or (
            f"{ctx.fac_country(r)} Environmental / Carbon Fiscality" if rate > 0 else "N/A - No origin price claimed")
        _cell(ws, idx, 1, r.id, Styles.mono)
        _cell(ws, idx, 2, ctx.safe(ctx.fac_name(r)), Styles.bold)
        _cell(ws, idx, 3, ctx.safe(ctx.fac_code(r)), Styles.mono)
        _cell(ws, idx, 4, ctx.safe(r.product_name), Styles.regular)
        _cell(ws, idx, 5, ctx.safe(str(r.cn_code)), Styles.mono)
        _cell(ws, idx, 6, round(qty, 1), number_format="#,##0.0")
        _cell(ws, idx, 7, ctx.safe(legal_ref), Styles.regular)
        _cell(ws, idx, 8, rate, number_format="€#,##0.00")
        _cell(ws, idx, 9, round(qty * rate, 2), number_format="€#,##0.00")
        _cell(ws, idx, 10, "Eligible for Full Article 9 Deduction" if rate > 0 else "No Origin Price Claimed", Styles.bold)
        _cell(ws, idx, 11, ctx.safe(_receipt_id(r, rate)), Styles.mono)
        _finish_row(ws, idx, 11)
    _totals_row(ws, len(ctx.records) + 5, "TOTAL CARBON PRICE PAID IN COUNTRY OF ORIGIN",
                {6: "#,##0.0", 9: "€#,##0.00"}, 11)
    autofit_columns(ws)


def sheet_assurance(wb, ctx, sha256):
    ws = _sheet(wb, "Audit_Assurance", "EU CBAM — REGULATORY ASSURANCE & CRYPTOGRAPHIC VERIFICATION",
                "Official operator declaration and immutable SHA-256 seal under Regulation (EU) 2023/956 Art. 8")
    rows = [
        ("Assurance Standard", "ISO 14064-3 / Commission Implementing Regulation (EU) 2023/1773 Article 18"),
        ("Cryptographic Data Fingerprint (SHA-256)", sha256),
        ("Audit Log Record", "The fingerprint is recorded in the platform audit log (REPORT entry) when exported"),
        ("Export Timestamp (UTC)", ctx.now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")),
        ("Exporting Organization", ctx.safe(ctx.company_name)),
        ("Lead Environmental Assessor", f"{ctx.assessor_name} ({ctx.assessor_email}) - Role: {ctx.user.role}"),
        ("Declared Installation Sites", len(ctx.facilities)),
        ("Declared CBAM Export Records", len(ctx.records)),
        ("Legal Certification Clause", CERTIFICATION),
    ]
    for col, label in enumerate(("Assurance Parameter", "Audit Manifest Value"), start=1):
        ws.cell(row=4, column=col, value=label).fill = Styles.header_fill
        ws.cell(row=4, column=col).font = Styles.header_font
    for idx, (prop, val) in enumerate(rows, start=5):
        _cell(ws, idx, 1, prop, Styles.bold).border = Styles.thin_border
        ws.cell(row=idx, column=1).fill = Styles.label_fill
        mono = "SHA-256" in prop
        _cell(ws, idx, 2, str(val), Styles.mono if mono else Styles.regular).border = Styles.thin_border
    autofit_columns(ws)


def build_workbook(ctx):
    """(workbook, SHA-256 fingerprint of the declared values on the summary sheet)."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    sheet_installations(wb, ctx)
    sheet_processes(wb, ctx)
    sheet_direct(wb, ctx)
    sheet_electricity(wb, ctx)
    sheet_precursors(wb, ctx)
    fingerprint = sheet_summary(wb, ctx)
    sheet_carbon_price(wb, ctx)
    sha256 = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode("utf-8")).hexdigest()
    sheet_assurance(wb, ctx, sha256)
    return wb, sha256
