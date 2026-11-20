"""Master report chapters: the chart-and-table chapter layout, decarbonization projects, OGMP 2.0, Scope 3 and
CBAM / MACC (split from master_report_engine.py, which holds the styles, palette and document assembly)."""

from typing import Any, Dict, List, Optional
from services.master_report_engine import (
    COLOR_AMBER_BG,
    COLOR_AMBER_BORDER,
    COLOR_BORDER,
    COLOR_CARD_BG,
    COLOR_DARK,
    COLOR_LIGHT_BG,
    COLOR_SLATE,
    _chart_flowable,
)
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from services.master_report_i18n import TRANSLATIONS_EN, TRANSLATIONS_FR, get_t, localize_status
from reportlab.lib import colors
from services.master_report_appendices import register_pdf_fonts
from services.pdf_escape import safe_pdf_text


def _build_chapter_with_chart(
    title: str,
    desc: str,
    chart_path: Optional[str],
    table_headers: List[str],
    table_rows: List[List[str]],
    col_widths: List[float],
    styles: Dict[str, ParagraphStyle],
    footnote: Optional[str] = None,
    img_height: float = 225,
    badge_text: Optional[str] = None,
    for_toc_pass: bool = False,
) -> List[Any]:
    """Helper to assemble an analytical chapter containing title, text, 150 DPI chart, and data table."""
    font_reg, font_bold, _ = register_pdf_fonts()
    elements = []
    elements.append(Paragraph(title, styles["H1"]))
    elements.append(Paragraph(desc, styles["Body"]))

    if badge_text:
        t_badge = Table([[Paragraph(badge_text, styles["BodySmall"])]], colWidths=[520])
        t_badge.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_AMBER_BG),
            ("BOX", (0, 0), (-1, -1), 0.8, COLOR_AMBER_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_badge)
        elements.append(Spacer(1, 6))

    img_flow = _chart_flowable(chart_path, width=520, height=img_height, for_toc_pass=for_toc_pass)
    if img_flow is not None:
        elements.append(img_flow)
        elements.append(Spacer(1, 6))

    if table_rows:
        ch_hdr_style = ParagraphStyle("ChapterTblHdr", fontName=font_bold, fontSize=6.6, leading=8.0, textColor=colors.white, alignment=1, spaceAfter=0)
        headers_fmt = [Paragraph(h, ch_hdr_style) for h in table_headers]
        t_data = [headers_fmt] + table_rows
        t = Table(t_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
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
    """Builds the database-sourced strategic decarbonization projects table or explicit empty-state notice."""
    font_reg, font_bold, _ = register_pdf_fonts()
    elements = []
    projects = data.get("decarbonization_projects") or []

    elements.append(Paragraph(get_t("decarb_title", lang), styles["H2"]))
    elements.append(Paragraph(get_t("decarb_desc", lang), styles["Body"]))

    if not projects:
        t_empty = Table([[Paragraph(get_t("decarb_empty_notice", lang), styles["BodySmall"])]], colWidths=[520])
        t_empty.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t_empty)
        elements.append(Spacer(1, 10))
        return elements

    p_headers = TRANSLATIONS_FR["decarb_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["decarb_headers"]
    p_hdr_left = ParagraphStyle("DecarbHdrL", fontName=font_bold, fontSize=6.8, leading=8.0, textColor=colors.white, alignment=0, spaceAfter=0)
    p_hdr_ctr = ParagraphStyle("DecarbHdrC", fontName=font_bold, fontSize=6.8, leading=8.0, textColor=colors.white, alignment=1, spaceAfter=0)
    p_headers_fmt = [
        Paragraph(p_headers[0], p_hdr_left),
        Paragraph(p_headers[1], p_hdr_ctr),
        Paragraph(p_headers[2], p_hdr_ctr),
    ]
    p_cell_style = ParagraphStyle("DecarbCell", parent=styles["BodySmall"], fontSize=7.2, leading=9.2, spaceAfter=0)
    p_rows = []
    for p in projects:
        raw_status = p.get("status", "Executing")
        p_rows.append([
            Paragraph(safe_pdf_text(p.get("title", "")), p_cell_style),
            f"{int(p.get('reduction_tco2e', 0)):,}",
            localize_status(raw_status, lang),
        ])

    t_p = Table([p_headers_fmt] + p_rows, colWidths=[270, 140, 110])
    t_p.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 1), (-1, -1), font_reg),
        ("FONTSIZE", (0, 1), (-1, -1), 7.5),
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


def _build_ogmp_elements(
    data: Dict[str, Any],
    chart_path: str,
    styles: Dict[str, ParagraphStyle],
    lang: str = "en",
    for_toc_pass: bool = False,
) -> List[Any]:
    """Generates Chapter 5: OGMP 2.0 Methane Reconciliation & LDAR Telemetry."""
    elements = []
    ogmp = data.get("ogmp", {})
    is_fr = str(lang).lower().startswith("fr")

    elements.append(Paragraph(get_t("ch5_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("ch5_desc", lang), styles["Body"]))
    elements.append(Spacer(1, 4))

    font_reg, font_bold, _ = register_pdf_fonts()
    surveys = ogmp.get("surveys", [])
    comp_count = int(ogmp.get("total_components_monitored", 0) or 0)
    hdr_style = ParagraphStyle("OgmpHdr", fontName=font_bold, fontSize=6.4, leading=7.8, textColor=colors.white, alignment=1, spaceAfter=0)
    cell_left = ParagraphStyle("OgmpCellL", parent=styles["BodySmall"], leading=8.0, spaceAfter=0)
    cell_center = ParagraphStyle("OgmpCellC", parent=styles["BodySmall"], leading=8.0, spaceAfter=0, alignment=1)

    if surveys:
        gold_ok = ogmp.get("gold_standard_compliant")
        # the stored outcome: "Reconciled" surveys only (no Gold Standard claim; audit 2026-11 F-RPT-03)
        status_str = (
            ("Réconcilié (résultat enregistré)" if is_fr else "Reconciled (recorded outcome)")
            if gold_ok else
            ("Non réconcilié" if is_fr else "Not reconciled")
        )
        mv = ogmp.get("mean_variance_pct")
        kpi_p = get_t("ch5_kpi", lang, status=status_str, variance=(f"{float(mv):+.1f}" if mv is not None else "n/a"),
                      comp_count=comp_count)
    else:
        kpi_p = get_t("ch5_empty_kpi", lang, comp_count=comp_count)

    t_kpi = Table([[Paragraph(kpi_p, styles["Body"])]], colWidths=[520])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(t_kpi)
    elements.append(Spacer(1, 6))

    img_flow = _chart_flowable(chart_path, width=520, height=210, for_toc_pass=for_toc_pass)
    if img_flow is not None:
        elements.append(img_flow)
        elements.append(Spacer(1, 6))

    if surveys:
        headers = get_t("ch5_ogmp_headers", lang)
        headers_fmt = [Paragraph(h, hdr_style) for h in headers]
        rows = []
        for s in surveys[:6]:
            st_raw = s.get("status", "Reconciled")
            st_text = ("Réconcilié" if "reconcil" in st_raw.lower() else "Écart Détecté") if is_fr else ("Reconciled" if "reconcil" in st_raw.lower() else "Discrepancy Detected")
            rows.append([
                Paragraph(safe_pdf_text(s.get("survey_type", "Site Survey"), 45), cell_left),
                Paragraph(safe_pdf_text(s.get("vendor", "Not Specified"), 40), cell_left),
                s.get("survey_date", ""),
                f"{s.get('bottom_up_tch4', 0.0):,.1f}",
                f"{s.get('top_down_tch4', 0.0):,.1f}",
                f"{s['variance_pct']:+.1f}%" if s.get("variance_pct") is not None else "n/a",
                st_text
            ])
        t_ogmp = Table([headers_fmt] + rows, colWidths=[120, 105, 55, 65, 65, 55, 55])
        t_ogmp.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("FONTSIZE", (0, 1), (-1, -1), 6.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 1), (1, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_ogmp)
    else:
        t_empty = Table([[Paragraph(get_t("ch5_empty_notice", lang), styles["BodySmall"])]], colWidths=[520])
        t_empty.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t_empty)
    elements.append(Spacer(1, 6))

    comps = ogmp.get("components", [])
    if comps:
        ldar_hdrs = get_t("ch5_ldar_headers", lang)
        ldar_hdrs_fmt = [Paragraph(h, hdr_style) for h in ldar_hdrs]
        comp_rows = []
        for c in comps[:6]:
            comp_rows.append([
                Paragraph(safe_pdf_text(c.get("equipment_type", "Valves"), 45), cell_left),
                Paragraph(safe_pdf_text(c.get("component_type", "Gate"), 45), cell_left),
                Paragraph(safe_pdf_text(c.get("service_type", "Gas"), 30), cell_center),
                Paragraph(str(c.get("quantity", 1)), cell_center),
                Paragraph(safe_pdf_text(c.get("methodology", "Component Average"), 48), cell_left),
            ])
        t_ldar = Table([ldar_hdrs_fmt] + comp_rows, colWidths=[110, 110, 80, 70, 150])
        t_ldar.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("FONTSIZE", (0, 1), (-1, -1), 6.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(t_ldar)
        elements.append(Spacer(1, 4))

    pnote = ogmp.get("perimeter_note", "")
    if pnote:
        if is_fr:
            pnote = (
                "Réconciliation OGMP 2.0 Niveaux 4/5 et registre des composants LDAR issus directement de la base de données."
                if surveys else
                "Aucune campagne de mesure OGMP 2.0 Niveau 4/5 n'est enregistrée en base pour ce périmètre et cette période."
            )
        elements.append(Paragraph(f"<i>* {safe_pdf_text(pnote)}</i>", styles["BodyMuted"]))

    return elements


def _build_scope3_elements(
    data: Dict[str, Any],
    chart_path: str,
    styles: Dict[str, ParagraphStyle],
    lang: str = "en",
    for_toc_pass: bool = False,
) -> List[Any]:
    """Generates Chapter 7: Scope 3 Value Chain Emissions & Product Lifecycle."""
    elements = []
    s3 = data.get("scope3", {})
    is_fr = str(lang).lower().startswith("fr")

    elements.append(Paragraph(get_t("ch7_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("ch7_desc", lang), styles["Body"]))
    elements.append(Spacer(1, 4))

    font_reg, font_bold, _ = register_pdf_fonts()
    categories = s3.get("categories", [])
    tot_s3 = float(s3.get("total_period_co2e", 0.0) or 0.0)
    has_data = bool(s3.get("has_data")) or (bool(categories) and tot_s3 > 0)

    if has_data and categories:
        up_t = float(s3.get("upstream_t", 0.0) or 0.0)
        down_t = float(s3.get("downstream_t", 0.0) or 0.0)
        up_pct = float(s3.get("upstream_pct", 0.0) or 0.0)
        down_pct = float(s3.get("downstream_pct", 0.0) or 0.0)
        tier2_cov = float(s3.get("tier2_coverage_pct", 0.0) or 0.0)
        kpi_p = get_t(
            "ch7_kpi",
            lang,
            total_s3=tot_s3,
            up_pct=up_pct,
            up_t=up_t,
            down_pct=down_pct,
            down_t=down_t,
            tier2_pct=tier2_cov,
        )
    else:
        kpi_p = get_t("ch7_empty_kpi", lang)

    t_kpi = Table([[Paragraph(kpi_p, styles["Body"])]], colWidths=[520])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(t_kpi)
    elements.append(Spacer(1, 6))

    img_flow = _chart_flowable(chart_path, width=520, height=210, for_toc_pass=for_toc_pass)
    if img_flow is not None:
        elements.append(img_flow)
        elements.append(Spacer(1, 6))

    if has_data and categories:
        headers = get_t("ch7_headers", lang)
        hdr_style = ParagraphStyle("S3Hdr", fontName=font_bold, fontSize=6.4, leading=7.8, textColor=colors.white, alignment=1, spaceAfter=0)
        s3_left = ParagraphStyle("S3CellL", parent=styles["BodySmall"], leading=8.0, spaceAfter=0)
        s3_ctr = ParagraphStyle("S3CellC", parent=styles["BodySmall"], leading=8.0, spaceAfter=0, alignment=1)
        headers_fmt = [Paragraph(h, hdr_style) for h in headers]
        rows = []
        for c in categories[:8]:
            cname = c.get("category_name", "")
            sub = c.get("sub_category", "")
            act = f"{c.get('activity_data', 0.0):,.0f}" if c.get("activity_data") else "N/A"
            ef_val = c.get("emission_factor")
            if ef_val:
                fu = str(c.get("factor_unit") or "").strip()
                ef = f"{ef_val:.3f} {safe_pdf_text(fu, 24)}".strip() if fu else f"{ef_val:.3f}"
            else:
                ef = "N/A"
            rows.append([
                Paragraph(safe_pdf_text(cname, 55), s3_left),
                Paragraph(safe_pdf_text(sub, 50), s3_left),
                act,
                Paragraph(safe_pdf_text(c.get("unit", "tonnes"), 18), s3_ctr),
                Paragraph(ef, s3_ctr),
                f"{c.get('co2e_t', 0.0):,.1f}",
                f"{c.get('share_pct', 0.0):.1f}%",
                c.get("tier", "N/A")
            ])

        t_s3 = Table([headers_fmt] + rows, colWidths=[105, 100, 48, 37, 85, 55, 42, 48])
        t_s3.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("FONTSIZE", (0, 1), (-1, -1), 6.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 1), (1, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_s3)
    else:
        t_empty = Table([[Paragraph(get_t("ch7_empty_notice", lang), styles["BodySmall"])]], colWidths=[520])
        t_empty.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t_empty)
    elements.append(Spacer(1, 6))

    pnote = s3.get("perimeter_note", "")
    if pnote:
        if is_fr:
            pnote = (
                "Émissions Scope 3 de la chaîne de valeur comptabilisées selon les Catégories 3–6 de la norme ISO 14064-1:2018."
                if (has_data and categories) else
                "Aucune émission Scope 3 vérifiée n'est enregistrée en base pour ce périmètre et cette période."
            )
        elements.append(Paragraph(f"<i>* {safe_pdf_text(pnote)}</i>", styles["BodyMuted"]))

    return elements


def _macc_table_elements(macc_projects: List[Dict[str, Any]], hdr_style: ParagraphStyle, cb_left: ParagraphStyle, cb_ctr: ParagraphStyle, styles: Dict[str, ParagraphStyle], lang: str, is_fr: bool, font_reg: str) -> List[Any]:
    """Marginal abatement cost table of the mitigation projects, or its empty notice."""
    elements = []
    if macc_projects:
        macc_hdrs = get_t("ch10_macc_headers", lang)
        macc_hdrs_fmt = [Paragraph(h, hdr_style) for h in macc_hdrs]
        macc_rows = []
        _PT_EN = {
            "METHANE_ABATEMENT": "Methane Abatement",
            "FLARE_RECOVERY": "Flare Recovery",
            "METHANE_LDAR": "Methane LDAR",
            "RENEWABLE": "Renewable",
            "EFFICIENCY": "Energy Efficiency",
            "CCS": "Carbon Capture",
        }
        _PT_FR = {
            "METHANE_ABATEMENT": "Atténuation CH4",
            "FLARE_RECOVERY": "Récup. Torches",
            "METHANE_LDAR": "LDAR Méthane",
            "RENEWABLE": "Renouvelable",
            "EFFICIENCY": "Efficacité Énerg.",
            "CCS": "Captage Carbone",
        }
        for m in macc_projects[:6]:
            inv_val = m.get("investment_usd")
            inv_str = f"${float(inv_val):,.0f}" if inv_val is not None and float(inv_val) > 0 else "N/A"
            cpt_val = m.get("cost_per_tonne_usd")
            cpt_str = f"${float(cpt_val):,.1f}" if cpt_val is not None else "N/A"
            raw_pt = str(m.get("project_type", "DEC")).strip().upper()
            pt_disp = (_PT_FR if is_fr else _PT_EN).get(raw_pt, raw_pt.replace("_", " ").title())
            raw_m_st = " ".join(w.capitalize() for w in str(m.get("status", "Active")).strip().replace("_", " ").split())
            macc_rows.append([
                Paragraph(safe_pdf_text(m.get("name", ""), 55), cb_left),
                Paragraph(safe_pdf_text(pt_disp, 36), cb_ctr),
                f"{m.get('annual_abatement_tco2e', 0.0):,.0f}",
                inv_str,
                cpt_str,
                localize_status(raw_m_st, lang)
            ])
        t_macc = Table([macc_hdrs_fmt] + macc_rows, colWidths=[145, 85, 70, 75, 70, 75])
        t_macc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("FONTSIZE", (0, 1), (-1, -1), 6.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(t_macc)
        elements.append(Spacer(1, 4))
    else:
        t_empty_m = Table([[Paragraph(get_t("ch10_macc_empty_notice", lang), styles["BodySmall"])]], colWidths=[520])
        t_empty_m.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t_empty_m)
        elements.append(Spacer(1, 4))
    return elements


def _build_cbam_macc_elements(
    data: Dict[str, Any],
    chart_path: str,
    styles: Dict[str, ParagraphStyle],
    lang: str = "en",
    for_toc_pass: bool = False,
) -> List[Any]:
    """Generates Chapter 10: EU CBAM Hydrocarbon Export Embeddings & Decarbonization Economics."""
    elements = []
    cbam = data.get("cbam_macc", {})
    is_fr = str(lang).lower().startswith("fr")

    elements.append(Paragraph(get_t("ch10_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("ch10_desc", lang), styles["Body"]))
    elements.append(Spacer(1, 4))

    font_reg, font_bold, _ = register_pdf_fonts()
    products = cbam.get("products", [])
    macc_projects = cbam.get("macc_projects", [])
    exp_tonnes = float(cbam.get("total_export_tonnes", 0.0) or 0.0)
    exp_ghg = float(cbam.get("total_embedded_co2e", 0.0) or 0.0)
    macc_cap = float(cbam.get("total_abatement_capacity", 0.0) or 0.0)
    has_cbam = bool(cbam.get("has_cbam_data")) or bool(products)

    hdr_style = ParagraphStyle("CbamHdr", fontName=font_bold, fontSize=6.4, leading=7.8, textColor=colors.white, alignment=1, spaceAfter=0)
    cb_left = ParagraphStyle("CbamCellL", parent=styles["BodySmall"], leading=8.0, spaceAfter=0)
    cb_ctr = ParagraphStyle("CbamCellC", parent=styles["BodySmall"], leading=8.0, spaceAfter=0, alignment=1)
    if has_cbam:
        kpi_p = get_t("ch10_kpi", lang, exp_tonnes=exp_tonnes, exp_ghg=exp_ghg, macc_cap=macc_cap)
    else:
        macc_cap_str = (
            f"{macc_cap:,.0f} tCO2e/an" if (is_fr and macc_cap > 0)
            else (f"{macc_cap:,.0f} tCO2e/yr" if macc_cap > 0 else ("0 tCO2e/an" if is_fr else "0 tCO2e/yr"))
        )
        kpi_p = get_t("ch10_empty_kpi", lang, macc_cap_str=macc_cap_str)

    t_kpi = Table([[Paragraph(kpi_p, styles["Body"])]], colWidths=[520])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(t_kpi)
    elements.append(Spacer(1, 6))

    img_flow = _chart_flowable(chart_path, width=520, height=210, for_toc_pass=for_toc_pass)
    if img_flow is not None:
        elements.append(img_flow)
        elements.append(Spacer(1, 6))

    if has_cbam:
        headers = get_t("ch10_cbam_headers", lang)
        headers_fmt = [Paragraph(h, hdr_style) for h in headers]
        rows = []
        for p in products[:6]:
            rows.append([
                Paragraph(safe_pdf_text(p.get("product_name", ""), 45), cb_left),
                p.get("cn_code", ""),
                Paragraph(safe_pdf_text(p.get("destinations", "EU"), 36), cb_left),
                f"{p.get('quantity_tonnes', 0.0):,.0f}",
                f"{p.get('see_direct', 0.0):.3f}",
                f"{p.get('see_indirect', 0.0):.3f}",
                f"{p.get('total_embedded_ghg', 0.0):,.0f}"
            ])
        t_cbam = Table([headers_fmt] + rows, colWidths=[110, 60, 110, 60, 60, 60, 60])
        t_cbam.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("FONTSIZE", (0, 1), (-1, -1), 6.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("ALIGN", (2, 1), (2, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_cbam)
    else:
        t_empty_c = Table([[Paragraph(get_t("ch10_empty_cbam_notice", lang), styles["BodySmall"])]], colWidths=[520])
        t_empty_c.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.6, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t_empty_c)
    elements.append(Spacer(1, 6))

    elements.extend(_macc_table_elements(macc_projects, hdr_style, cb_left, cb_ctr, styles, lang, is_fr, font_reg))
    pnote = cbam.get("perimeter_note", "")
    if pnote:
        if is_fr:
            pnote = (
                "Registre d'exportation MACF UE (Règlement (UE) 2023/956) et économie d'abattement MACC issus directement de la base de données."
                if has_cbam else
                "Aucune exportation de produit soumise au MACF UE n'est enregistrée en base pour ce périmètre et cette période."
            )
        elements.append(Paragraph(f"<i>* {safe_pdf_text(pnote)}</i>", styles["BodyMuted"]))

    return elements
