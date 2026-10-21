"""
Universal Master Publication Report Engine
==========================================
Generates high-resolution, publication-grade executive PDF reports:
1. Consolidated Sonatrach Group Corporate Master Report
2. Regional Asset Master Reports (HMD, HRM, RNS, In Amenas, In Salah, TFT, Berkine, Skikda, Arzew)
3. Multi-Region Cross-Basin Benchmark Report

Complies with ISO 14064-1:2018, Algerian Executive Decree 21-330, and Executive Decree 06-138.
Supports bilingual output (English and French).
"""

import os
import io
import tempfile
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Image, Spacer, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

from services.master_report_data import aggregate_master_report_data
from services.master_report_charts import (
    generate_production_chart,
    generate_emissions_progression_chart,
    generate_sangea_breakdown_chart,
    generate_flaring_decree_chart,
    generate_intensities_chart,
    generate_criteria_pollutants_chart,
    generate_2030_glidepath_chart,
    generate_jv_equity_chart,
    generate_regional_benchmark_chart,
)
from services.master_report_i18n import (
    get_t, localize_status, localize_segment, TRANSLATIONS_EN, TRANSLATIONS_FR
)
from services.master_report_appendices import (
    build_qaqc_uncertainty_elements,
    build_facility_appendix_elements,
    build_toc_and_glossary_elements,
    build_executive_narrative_elements,
)

# Palette
COLOR_ORANGE = colors.HexColor("#EA580C")
COLOR_DARK = colors.HexColor("#0F172A")
COLOR_SLATE = colors.HexColor("#1E293B")
COLOR_MUTED = colors.HexColor("#64748B")
COLOR_LIGHT_BG = colors.HexColor("#F8FAFC")
COLOR_BORDER = colors.HexColor("#CBD5E1")
COLOR_SUCCESS = colors.HexColor("#10B981")
COLOR_DANGER = colors.HexColor("#EF4444")
COLOR_CARD_BG = colors.HexColor("#F1F5F9")

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 36


class MasterReportNumberedCanvas(canvas.Canvas):
    """Two-pass canvas generating dynamic 'Page X of Y' footers and running headers."""
    def __init__(self, *args, language: str = "en", **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_decorations(self, total_pages: int):
        lang = self.language
        if self._pageNumber == 1:
            self.setFillColor(COLOR_ORANGE)
            self.rect(0, PAGE_HEIGHT - 6, PAGE_WIDTH, 6, fill=1, stroke=0)
            self.setFont("Helvetica-Bold", 7)
            self.setFillColor(COLOR_MUTED)
            self.drawString(MARGIN, 22, get_t("canvas_cover_notice", lang))
            self.drawRightString(PAGE_WIDTH - MARGIN, 22, get_t("canvas_page_of", lang, page=1, total=total_pages))
            return

        # Running header on inner pages
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(COLOR_ORANGE)
        self.drawString(MARGIN, PAGE_HEIGHT - 24, get_t("canvas_inner_header_left", lang))
        self.setFont("Helvetica", 7.5)
        self.setFillColor(COLOR_MUTED)
        self.drawString(MARGIN + 182, PAGE_HEIGHT - 24, get_t("canvas_inner_header_mid", lang))
        self.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 24, get_t("canvas_inner_header_right", lang))

        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.5)
        self.line(MARGIN, PAGE_HEIGHT - 28, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 28)

        # Running footer
        self.line(MARGIN, 30, PAGE_WIDTH - MARGIN, 30)
        self.setFont("Helvetica", 7)
        self.setFillColor(COLOR_MUTED)
        self.drawString(MARGIN, 20, get_t("canvas_confidential", lang))
        self.drawRightString(PAGE_WIDTH - MARGIN, 20, get_t("canvas_page_of", lang, page=self._pageNumber, total=total_pages))


def _build_styles() -> Dict[str, ParagraphStyle]:
    """Prepares consistent typography hierarchy for the publication document."""
    styles = {}
    styles["Title"] = ParagraphStyle("CoverTitle", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=COLOR_DARK, spaceAfter=6)
    styles["Subtitle"] = ParagraphStyle("CoverSubtitle", fontName="Helvetica", fontSize=11, leading=15, textColor=COLOR_MUTED, spaceAfter=14)
    styles["H1"] = ParagraphStyle("Heading1", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=COLOR_DARK, spaceBefore=12, spaceAfter=6, keepWithNext=True)
    styles["H2"] = ParagraphStyle("Heading2", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=COLOR_ORANGE, spaceBefore=8, spaceAfter=4, keepWithNext=True)
    styles["Body"] = ParagraphStyle("BodyDark", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=COLOR_SLATE, spaceAfter=6)
    styles["BodyMuted"] = ParagraphStyle("BodyMuted", fontName="Helvetica", fontSize=7.5, leading=10, textColor=COLOR_MUTED, spaceAfter=4)
    styles["CardVal"] = ParagraphStyle("CardValue", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=COLOR_DARK, alignment=1)
    styles["CardLbl"] = ParagraphStyle("CardLabel", fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=COLOR_MUTED, alignment=1)
    return styles


def _build_cover_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the executive publication cover page elements."""
    elements = []
    profile = data["profile"]
    mode = data["mode"]
    start_y = data["start_year"]
    end_y = data["end_year"]
    time_label = f"{start_y}" if start_y == end_y else f"{start_y} – {end_y}"

    elements.append(Spacer(1, 15))
    elements.append(Paragraph(get_t("corp_name", lang), styles["H2"]))
    elements.append(Paragraph(get_t("hse_division", lang), styles["BodyMuted"]))
    elements.append(Spacer(1, 12))

    if mode == "national":
        doc_title = get_t("title_national", lang)
        sub_title = get_t("subtitle_national", lang, time_label=time_label)
    elif mode == "comparison":
        doc_title = get_t("title_comparison", lang)
        sub_title = get_t("subtitle_comparison", lang, time_label=time_label)
    else:
        doc_title = profile.get("name", "REGIONAL ASSET").upper()
        sub_title = get_t("subtitle_regional", lang, time_label=time_label)

    elements.append(Paragraph(doc_title, styles["Title"]))
    elements.append(Paragraph(sub_title, styles["Subtitle"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=COLOR_ORANGE, spaceBefore=4, spaceAfter=14))

    meta_data = [
        [
            Paragraph(f"<b>{get_t('meta_period', lang)}</b>", styles["Body"]),
            Paragraph(get_t("meta_period_val", lang, time_label=time_label), styles["Body"]),
            Paragraph(f"<b>{get_t('meta_standard', lang)}</b>", styles["Body"]),
            Paragraph(get_t("meta_standard_val", lang), styles["Body"]),
        ],
        [
            Paragraph(f"<b>{get_t('meta_operator', lang)}</b>", styles["Body"]),
            Paragraph(str(profile.get("operator", "Sonatrach")), styles["Body"]),
            Paragraph(f"<b>{get_t('meta_gwp', lang)}</b>", styles["Body"]),
            Paragraph(get_t("meta_gwp_val", lang, standard=data["gwp_standard"], ch4_factor=data["gwp_factors"].get("CH4", 28)), styles["Body"]),
        ],
        [
            Paragraph(f"<b>{get_t('meta_basin', lang)}</b>", styles["Body"]),
            Paragraph(str(profile.get("basin", "National Estate")), styles["Body"]),
            Paragraph(f"<b>{get_t('meta_decree', lang)}</b>", styles["Body"]),
            Paragraph(get_t("meta_decree_val", lang), styles["Body"]),
        ],
        [
            Paragraph(f"<b>{get_t('meta_facilities', lang)}</b>", styles["Body"]),
            Paragraph(get_t("meta_facilities_val", lang, count=len(data["facilities"])), styles["Body"]),
            Paragraph(f"<b>{get_t('meta_assurance', lang)}</b>", styles["Body"]),
            Paragraph(get_t("meta_assurance_val", lang), styles["Body"]),
        ],
    ]
    t_meta = Table(meta_data, colWidths=[115, 155, 115, 135])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph(get_t("regulatory_banner", lang), styles["BodyMuted"]))
    elements.append(Spacer(1, 10))
    return elements


def _build_scorecard_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the executive KPI cards block."""
    elements = []
    timeline = data["timeline"]
    if not timeline:
        return elements

    latest = timeline[-1]
    prev = timeline[-2] if len(timeline) > 1 else latest

    co2e_delta = ((latest["total_co2e_t"] - prev["total_co2e_t"]) / prev["total_co2e_t"] * 100.0) if prev["total_co2e_t"] > 0 else 0.0
    ci_delta = ((latest["carbon_intensity_kg_boe"] - prev["carbon_intensity_kg_boe"]) / prev["carbon_intensity_kg_boe"] * 100.0) if prev["carbon_intensity_kg_boe"] > 0 else 0.0

    fi_val = latest["flaring_intensity_pct"]
    fi_status = get_t("decree_compliant", lang) if fi_val <= 1.00 else get_t("decree_exceeded", lang)
    fi_color = COLOR_SUCCESS if fi_val <= 1.00 else COLOR_DANGER

    cards_data = [
        [
            Paragraph(f"{latest['total_mmt']:.3f} MMt", styles["CardVal"]),
            Paragraph(f"{latest['carbon_intensity_kg_boe']:.1f}", styles["CardVal"]),
            Paragraph(f"{fi_val:.2f}%", styles["CardVal"]),
            Paragraph(f"{latest['methane_intensity_pct']:.3f}%", styles["CardVal"]),
        ],
        [
            Paragraph(f"{get_t('scorecard_lbl_ghg', lang)}<br/><font size=6 color='#64748B'>{get_t('scorecard_delta', lang, delta=co2e_delta)}</font>", styles["CardLbl"]),
            Paragraph(f"{get_t('scorecard_lbl_ci', lang)}<br/><font size=6 color='#64748B'>{get_t('scorecard_delta', lang, delta=ci_delta)}</font>", styles["CardLbl"]),
            Paragraph(f"{get_t('scorecard_lbl_fi', lang)}<br/><font size=6 color='{fi_color.hexval()}'>{get_t('decree_card_sub', lang, status=fi_status)}</font>", styles["CardLbl"]),
            Paragraph(f"{get_t('scorecard_lbl_mi', lang)}<br/><font size=6 color='#0D9488'>{get_t('ogci_target_sub', lang)}</font>", styles["CardLbl"]),
        ],
    ]
    t_cards = Table(cards_data, colWidths=[130, 130, 130, 130])
    t_cards.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD_BG),
        ("BOX", (0, 0), (-1, -1), 1, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    elements.append(Paragraph(get_t("scorecard_title", lang), styles["H1"]))
    elements.append(t_cards)
    elements.append(Spacer(1, 12))
    return elements


def _build_geology_and_ops_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the geological and operational context section."""
    elements = []
    profile = data["profile"]

    elements.append(Paragraph(get_t("geology_title", lang), styles["H1"]))
    elements.append(Paragraph(f"<b>{get_t('geology_reservoir', lang)}</b> {profile.get('geology', 'Authentic geological setting spanning the Saharan platform.')}", styles["Body"]))
    elements.append(Paragraph(f"<b>{get_t('geology_infra', lang)}</b> {profile.get('infrastructure', 'Integrated gathering and processing network.')}", styles["Body"]))
    elements.append(Paragraph(f"<b>{get_t('geology_flare', lang)}</b> {profile.get('flaring_profile', 'Flare minimization aligned with Zero Routine Flaring.')}", styles["Body"]))

    gc = data.get("gas_composition") or profile.get("gas_composition", {})
    gc_name = data.get("gas_comp_name") or profile.get("name")
    if gc:
        title_prefix = f"{gc_name} — " if gc_name else ""
        section_title = f"{title_prefix}{get_t('gas_comp_title', lang)}"
        elements.append(Paragraph(f"<b>{section_title}</b>", styles["H2"]))
        is_fr = str(lang).lower().startswith("fr")
        h1 = TRANSLATIONS_FR.get("gas_comp_headers_r1") if is_fr else TRANSLATIONS_EN.get("gas_comp_headers_r1")
        h2 = TRANSLATIONS_FR.get("gas_comp_headers_r2") if is_fr else TRANSLATIONS_EN.get("gas_comp_headers_r2")
        r1 = [f"{gc.get('ch4_mol_pct', 0)} mol%", f"{gc.get('c2h6_mol_pct', 0)} mol%", f"{gc.get('c3h8_mol_pct', 0)} mol%", f"{gc.get('co2_mol_pct', 0)} mol%", f"{gc.get('n2_mol_pct', 0)} mol%", f"{gc.get('h2s_ppm', 0)} ppm"]
        m_keys = ("ch4_mol_pct", "c2h6_mol_pct", "c3h8_mol_pct", "ic4_mol_pct", "nc4_mol_pct", "ic5_mol_pct", "nc5_mol_pct", "c6_plus_mol_pct", "co2_mol_pct", "n2_mol_pct")
        tot = sum(float(gc.get(k, 0) or 0) for k in m_keys)
        r2 = [f"{gc.get('ic4_mol_pct', 0)} mol%", f"{gc.get('nc4_mol_pct', 0)} mol%", f"{gc.get('ic5_mol_pct', 0)} mol%", f"{gc.get('nc5_mol_pct', 0)} mol%", f"{gc.get('c6_plus_mol_pct', 0)} mol%", f"{tot:.2f} mol%"]
        t_gc = Table([h1, r1, h2, r2], colWidths=[86, 86, 86, 88, 86, 88])
        t_gc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 1), (-1, 1), COLOR_LIGHT_BG),
            ("BACKGROUND", (0, 2), (-1, 2), COLOR_SLATE),
            ("TEXTCOLOR", (0, 2), (-1, 2), colors.white),
            ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
            ("BACKGROUND", (0, 3), (-1, 3), COLOR_LIGHT_BG),
            ("FONTNAME", (-1, 3), (-1, 3), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.2),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_gc)

    elements.append(Spacer(1, 10))
    return elements


def _build_chapter_with_chart(
    title: str,
    desc: str,
    chart_path: str,
    table_headers: List[str],
    table_rows: List[List[str]],
    col_widths: List[float],
    styles: Dict[str, ParagraphStyle],
    footnote: Optional[str] = None
) -> List[Any]:
    """Helper to assemble an analytical chapter containing title, text, 300 DPI chart, and data table."""
    elements = []
    elements.append(Paragraph(title, styles["H1"]))
    elements.append(Paragraph(desc, styles["Body"]))

    if os.path.exists(chart_path):
        elements.append(Image(chart_path, width=520, height=230))
        elements.append(Spacer(1, 6))

    if table_rows:
        t_data = [table_headers] + table_rows
        t = Table(t_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]))
        elements.append(t)

    if footnote:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(footnote, styles["BodyMuted"]))

    elements.append(Spacer(1, 12))
    return elements


def _build_decarbonization_projects_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Builds the strategic decarbonization projects table."""
    elements = []
    projects = data.get("decarbonization_projects") or data["profile"].get("decarbonization_projects", [])
    if not projects:
        return elements

    elements.append(Paragraph(get_t("decarb_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("decarb_desc", lang), styles["Body"]))

    p_headers = TRANSLATIONS_FR["decarb_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["decarb_headers"]
    p_rows = []
    for p in projects:
        raw_status = p.get("status", "Executing")
        p_rows.append([
            Paragraph(p.get("title", ""), styles["Body"]),
            f"{int(p.get('reduction_tco2e', 0)):,}",
            localize_status(raw_status, lang),
        ])

    t_p = Table([p_headers] + p_rows, colWidths=[280, 130, 110])
    t_p.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (1, 0), (2, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_p)
    elements.append(Spacer(1, 12))
    return elements


def _build_glidepath_elements(data: Dict[str, Any], chart_path: str, styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates Chapter 7: 2030 Corporate Decarbonization Target Glidepath and milestone table."""
    target_proj = data.get("target_projection", {})
    if not target_proj:
        return []
    elements = []
    elements.append(Paragraph(get_t("ch7_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("ch7_desc", lang), styles["Body"]))
    if os.path.exists(chart_path):
        elements.append(Image(chart_path, width=520, height=230))
        elements.append(Spacer(1, 6))

    headers = TRANSLATIONS_FR["ch7_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch7_headers"]
    milestones = target_proj.get("milestones", [])
    rows = []
    for m in milestones:
        stat = localize_status(m.get("status", "Planned"), lang)
        rows.append([
            str(m.get("year", "")),
            f"{m.get('target_ghg_mmt', 0.0):.3f}",
            str(m.get("reduction_str", "0.0%")),
            str(m.get("flaring_objective", "Zero Routine Flaring")),
            stat,
        ])
    if rows:
        t_m = Table([headers] + rows, colWidths=[70, 110, 110, 130, 100])
        t_m.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]))
        elements.append(t_m)
    elements.append(Spacer(1, 12))
    return elements


def _build_jv_equity_elements(data: Dict[str, Any], chart_path: str, styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates Chapter 8: Joint Venture Partner Equity Share Allocation and partner breakdown table."""
    jv_equity = data.get("jv_equity", {})
    if not jv_equity or not jv_equity.get("partners"):
        return []
    elements = []
    elements.append(Paragraph(get_t("ch8_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("ch8_desc", lang), styles["Body"]))
    if os.path.exists(chart_path):
        elements.append(Image(chart_path, width=520, height=230))
        elements.append(Spacer(1, 6))

    headers = TRANSLATIONS_FR["ch8_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch8_headers"]
    hdr_style = ParagraphStyle(
        "JVHdr",
        fontName="Helvetica-Bold",
        fontSize=6.8,
        leading=8,
        textColor=colors.white,
        alignment=1,
    )
    formatted_headers = [Paragraph(h, hdr_style) for h in headers]
    partners = jv_equity.get("partners", [])
    rows = []
    for p in partners:
        rows.append([
            p.get("partner_name", ""),
            f"{p.get('equity_share_pct', 0.0):.1f}%",
            f"{p.get('equity_s1_tco2e', 0.0):,.0f}",
            f"{p.get('equity_s2_tco2e', 0.0):,.0f}",
            f"{p.get('equity_total_ghg_tco2e', 0.0):,.0f}",
            f"{p.get('equity_ch4_t', 0.0):,.0f}",
        ])
    if rows:
        t_jv = Table([formatted_headers] + rows, colWidths=[130, 65, 80, 80, 85, 80])
        t_jv.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]))
        elements.append(t_jv)
    elements.append(Spacer(1, 12))
    return elements


def _build_benchmark_league_elements(data: Dict[str, Any], chart_path: str, styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Builds the multi-region league table and comparative chart for comparison mode."""
    elements = []
    elements.append(Paragraph(get_t("bench_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("bench_desc", lang), styles["Body"]))

    if os.path.exists(chart_path):
        elements.append(Image(chart_path, width=520, height=240))
        elements.append(Spacer(1, 6))

    benchmarks = data.get("regional_benchmarks", [])
    if benchmarks:
        b_headers = TRANSLATIONS_FR["bench_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["bench_headers"]
        b_rows = []
        for b in sorted(benchmarks, key=lambda x: x.get("carbon_intensity_kg_boe", 0.0)):
            stat = get_t("decree_compliant", lang) if b.get("decree_compliant") else get_t("decree_exceeded", lang)
            b_rows.append([
                b.get("name", "").split("(")[0].strip()[:24],
                localize_segment(b.get("segment", "Upstream"), lang),
                str(b.get("facility_count", 1)),
                f"{b.get('total_mmboe', 0.0):.2f}",
                f"{b.get('carbon_intensity_kg_boe', 0.0):.1f}",
                f"{b.get('flaring_intensity_pct', 0.0):.2f}%",
                stat,
            ])
        t_b = Table([b_headers] + b_rows, colWidths=[120, 65, 45, 75, 75, 70, 70])
        t_b.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(t_b)
    elements.append(Spacer(1, 12))
    return elements


def _build_signoff_elements(data: Dict[str, Any], sha256_hash: str, styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the official MRV verification certificate and cryptographic seal."""
    elements = []
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(get_t("signoff_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("signoff_cert", lang), styles["Body"]))

    sign_data = [
        [
            Paragraph(get_t("role_hse", lang), styles["Body"]),
            Paragraph(get_t("role_auditor", lang), styles["Body"]),
            Paragraph(get_t("role_vp", lang), styles["Body"]),
        ],
        [
            Paragraph(get_t("sign_stamp_hse", lang), styles["Body"]),
            Paragraph(get_t("sign_stamp_auditor", lang), styles["Body"]),
            Paragraph(get_t("sign_stamp_vp", lang), styles["Body"]),
        ],
    ]
    t_sign = Table(sign_data, colWidths=[173, 173, 174])
    t_sign.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_sign)
    elements.append(Spacer(1, 8))

    hash_p = f"<b>{get_t('fingerprint_lbl', lang)}</b> <code>{sha256_hash}</code><br/>{get_t('generated_lbl', lang)} {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    elements.append(Paragraph(hash_p, styles["BodyMuted"]))
    return elements


def _assemble_document_story(
    data: Dict[str, Any],
    charts: Dict[str, str],
    styles: Dict[str, ParagraphStyle],
    lang: str = "en"
) -> List[Any]:
    """Assembles all sections, scorecards, chapters, charts, and appendices into a cohesive flow."""
    elements = []
    mode = data["mode"]
    timeline = data["timeline"]

    # 1. Cover, Scorecard & Geology
    elements.extend(_build_cover_elements(data, styles, lang))
    elements.extend(_build_scorecard_elements(data, styles, lang))
    elements.extend(_build_geology_and_ops_elements(data, styles, lang))
    elements.append(PageBreak())

    # 2. Table of Contents, Technical Glossary & Executive Narrative Highlights (Page 2)
    elements.extend(build_toc_and_glossary_elements(data, styles, lang=lang))
    elements.extend(build_executive_narrative_elements(data, styles, lang=lang))
    elements.append(PageBreak())

    # Chapter 1: Production
    prod_rows = [[str(t["year"]), f"{t['gross_gas_mmsm3']:,.1f}", f"{t['liquid_mmbbl']:.2f}", f"{t['total_mmboe']:.2f}"] for t in timeline]
    elements.extend(_build_chapter_with_chart(
        get_t("ch1_title", lang),
        get_t("ch1_desc", lang),
        charts["prod"],
        TRANSLATIONS_FR["ch1_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch1_headers"],
        prod_rows,
        [70, 150, 150, 150],
        styles
    ))
    elements.append(PageBreak())

    # Chapter 2: Scope 1 & 2 Emissions
    em_rows = [[str(t["year"]), f"{t['scope1_co2e_t']:,.0f}", f"{t['scope2_co2e_t']:,.0f}", f"{t['total_co2e_t']:,.0f}", f"{t['total_mmt']:.3f}"] for t in timeline]
    elements.extend(_build_chapter_with_chart(
        get_t("ch2_title", lang),
        get_t("ch2_desc", lang),
        charts["em"],
        TRANSLATIONS_FR["ch2_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch2_headers"],
        em_rows,
        [60, 115, 115, 115, 115],
        styles
    ))
    elements.append(PageBreak())

    # Chapter 3: SANGEA Modules
    sangea_rows = [[str(t["year"]), f"{t['combustion_t']:,.0f}", f"{t['flaring_t']:,.0f}", f"{t['fugitives_t']:,.0f}", f"{t['venting_t']:,.0f}"] for t in timeline]
    elements.extend(_build_chapter_with_chart(
        get_t("ch3_title", lang),
        get_t("ch3_desc", lang),
        charts["sangea"],
        TRANSLATIONS_FR["ch3_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch3_headers"],
        sangea_rows,
        [60, 115, 115, 115, 115],
        styles
    ))
    elements.append(PageBreak())

    # Chapter 4: Flaring & Decree 21-330
    pass_txt = get_t("ch4_pass", lang)
    fail_txt = get_t("ch4_fail", lang)
    flare_rows = [
        [
            str(t["year"]),
            f"{t.get('routine_mmsm3', 0.0):.2f}",
            f"{t.get('non_routine_mmsm3', 0.0):.2f}",
            f"{t.get('safety_mmsm3', 0.0):.2f}",
            f"{t['flaring_mmsm3']:.2f}",
            f"{t['flaring_intensity_pct']:.2f}%",
            pass_txt if t["decree_21_330_compliant"] else fail_txt
        ]
        for t in timeline
    ]
    elements.extend(_build_chapter_with_chart(
        get_t("ch4_title", lang),
        get_t("ch4_desc", lang),
        charts["flare"],
        TRANSLATIONS_FR["ch4_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch4_headers"],
        flare_rows,
        [50, 75, 85, 75, 75, 80, 80],
        styles
    ))
    elements.append(PageBreak())

    # Chapter 5: Intensities
    int_rows = [[str(t["year"]), f"{t['carbon_intensity_kg_boe']:.1f}", f"{t['methane_intensity_pct']:.3f}%", f"{t['ch4_mass_t']:,.0f}"] for t in timeline]
    elements.extend(_build_chapter_with_chart(
        get_t("ch5_title", lang),
        get_t("ch5_desc", lang),
        charts["int"],
        TRANSLATIONS_FR["ch5_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch5_headers"],
        int_rows,
        [70, 160, 150, 140],
        styles
    ))
    elements.append(PageBreak())

    # Chapter 6: Criteria Pollutants
    poll_rows = [[str(t["year"]), f"{t['nox_t']:.1f}", f"{t['co_t']:.1f}", f"{t['so2_t']:.1f}", f"{t['voc_t']:.1f}"] for t in timeline]
    elements.extend(_build_chapter_with_chart(
        get_t("ch6_title", lang),
        get_t("ch6_desc", lang),
        charts["poll"],
        TRANSLATIONS_FR["ch6_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch6_headers"],
        poll_rows,
        [70, 110, 110, 110, 120],
        styles,
        footnote=get_t("ch6_footnote", lang)
    ))

    # Strategic Decarbonization Projects
    elements.extend(_build_decarbonization_projects_elements(data, styles, lang))

    # Chapter 7: 2030 Decarbonization Target Trajectory & Glidepath
    elements.append(PageBreak())
    elements.extend(_build_glidepath_elements(data, charts["glide"], styles, lang))

    # Chapter 8: Joint Venture Partner Equity Share Allocation
    elements.append(PageBreak())
    elements.extend(_build_jv_equity_elements(data, charts["jv"], styles, lang))

    # Chapter 9: QA/QC Verification, Uncertainty & Statutory Regimes
    elements.append(PageBreak())
    elements.extend(build_qaqc_uncertainty_elements(data, styles, lang=lang))

    # If Comparison Mode: Cross-Basin Benchmark
    if mode == "comparison":
        elements.append(PageBreak())
        elements.extend(_build_benchmark_league_elements(data, charts["bench"], styles, lang))

    # Appendix: Disaggregated Facility Ledgers (if multi-facility)
    if data.get("facility_breakdowns"):
        elements.append(PageBreak())
        elements.extend(build_facility_appendix_elements(data, styles, lang=lang))

    # Sign-off & Fingerprint Certificate
    simulated_hash = hashlib.sha256(f"{mode}-{data.get('region_key')}-{data['start_year']}-{data['end_year']}-{len(timeline)}-{lang}".encode()).hexdigest()
    elements.extend(_build_signoff_elements(data, simulated_hash, styles, lang))

    return elements


def generate_master_publication_pdf(
    mode: str,
    region_key: Optional[str],
    start_year: int,
    end_year: int,
    gwp_standard: str = "AR5",
    allowed_facility_ids: Optional[List[int]] = None,
    language: str = "en"
) -> io.BytesIO:
    """
    Main orchestration routine. Compiles the publication PDF and returns an in-memory BytesIO buffer.
    """
    data = aggregate_master_report_data(mode, region_key, start_year, end_year, gwp_standard, allowed_facility_ids)
    timeline = data["timeline"]
    years = [t["year"] for t in timeline]
    styles = _build_styles()

    with tempfile.TemporaryDirectory() as tmp_dir:
        charts = {
            "prod": os.path.join(tmp_dir, "prod.png"),
            "em": os.path.join(tmp_dir, "em.png"),
            "sangea": os.path.join(tmp_dir, "sangea.png"),
            "flare": os.path.join(tmp_dir, "flare.png"),
            "int": os.path.join(tmp_dir, "int.png"),
            "poll": os.path.join(tmp_dir, "poll.png"),
            "glide": os.path.join(tmp_dir, "glide.png"),
            "jv": os.path.join(tmp_dir, "jv.png"),
            "bench": os.path.join(tmp_dir, "bench.png"),
        }

        generate_production_chart(years, [t["gross_gas_mmsm3"] for t in timeline], [t["liquid_mmbbl"] for t in timeline], charts["prod"], language=language)
        generate_emissions_progression_chart(years, [t["scope1_mmt"] for t in timeline], [t["scope2_mmt"] for t in timeline], charts["em"], language=language)
        generate_sangea_breakdown_chart(
            years,
            [t["combustion_t"] for t in timeline],
            [t["flaring_t"] for t in timeline],
            [t["fugitives_t"] for t in timeline],
            [t["venting_t"] for t in timeline],
            charts["sangea"],
            language=language
        )
        generate_flaring_decree_chart(
            years,
            [t["flaring_mmsm3"] for t in timeline],
            [t["flaring_intensity_pct"] for t in timeline],
            charts["flare"],
            language=language,
            routine_mmsm3=[t.get("routine_mmsm3", 0.0) for t in timeline],
            non_routine_mmsm3=[t.get("non_routine_mmsm3", 0.0) for t in timeline],
            safety_mmsm3=[t.get("safety_mmsm3", 0.0) for t in timeline],
        )
        generate_intensities_chart(years, [t["carbon_intensity_kg_boe"] for t in timeline], [t["methane_intensity_pct"] for t in timeline], charts["int"], language=language)
        generate_criteria_pollutants_chart(
            years,
            [t["nox_t"] for t in timeline],
            [t["co_t"] for t in timeline],
            [t["so2_t"] for t in timeline],
            [t["voc_t"] for t in timeline],
            charts["poll"],
            language=language
        )
        generate_2030_glidepath_chart(data["target_projection"], charts["glide"], language=language)
        generate_jv_equity_chart(data["jv_equity"], charts["jv"], language=language)
        if mode == "comparison":
            generate_regional_benchmark_chart(data.get("regional_benchmarks", []), charts["bench"], language=language)

        elements = _assemble_document_story(data, charts, styles, lang=language)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
        )
        doc.build(elements, canvasmaker=lambda *args, **kwargs: MasterReportNumberedCanvas(*args, language=language, **kwargs))

        pdf_bytes = buffer.getvalue()
        real_hash = hashlib.sha256(pdf_bytes).hexdigest()
        buffer.seek(0)
        buffer.report_hash = real_hash
        return buffer
