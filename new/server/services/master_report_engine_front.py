"""Master report sections: cover, scorecard, geology and operations, 2030 glidepath, JV equity, cross-basin
benchmark, sign-off and process architecture (split from master_report_engine.py, which holds the styles,
palette and document assembly)."""

import os
from typing import Any, Dict, List, Optional
from services.master_report_engine import (
    COLOR_AMBER_BG,
    COLOR_AMBER_BORDER,
    COLOR_BORDER,
    COLOR_CARD_BG,
    COLOR_DANGER,
    COLOR_DARK,
    COLOR_LIGHT_BG,
    COLOR_MUTED,
    COLOR_ORANGE,
    COLOR_SLATE,
    COLOR_SUCCESS,
    COLOR_SUCCESS_BG,
    _chart_flowable,
)
from reportlab.platypus import HRFlowable, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from services.master_report_i18n import (
    TRANSLATIONS_EN,
    TRANSLATIONS_FR,
    get_t,
    localize_segment,
    localize_status,
)
from reportlab.lib import colors
from datetime import datetime, timezone
from services.tenant_config import get_tenant_config
from services.master_report_appendices import register_pdf_fonts
from services.pdf_escape import safe_pdf_text


def _build_cover_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the executive publication cover page elements."""
    elements = []
    profile = data["profile"]
    mode = data["mode"]
    start_y = data["start_year"]
    end_y = data["end_year"]
    time_label = f"{start_y}" if start_y == end_y else f"{start_y} – {end_y}"

    elements.append(Spacer(1, 15))
    tenant_cfg = data.get("tenant_config") or get_tenant_config(data.get("tenant_id"))
    org_name = str(profile.get("operator") or tenant_cfg.get("organization_name", "Operator"))
    elements.append(Paragraph(f"<b>{safe_pdf_text(org_name.upper())}</b>", styles["H2"]))
    is_fr = str(lang).lower().startswith("fr")
    jv_partners = data.get("jv_equity", {}).get("partners", [])
    if jv_partners and len(jv_partners) > 1:
        partner_str = " &amp; ".join(safe_pdf_text(p.get("partner_name", "")) for p in jv_partners)
        jv_lbl = "Partenariat Joint-Venture :" if is_fr else "Joint Venture Partnership:"
        elements.append(Paragraph(f"<b>{jv_lbl}</b> {partner_str}", styles["BodyMuted"]))
    gov = data.get("governance") or {}
    rm = gov.get("reporting_metadata") or {}
    is_locked = bool(gov.get("is_locked"))

    elements.append(Paragraph(get_t("hse_division", lang), styles["BodyMuted"]))
    elements.append(Spacer(1, 10))

    if mode == "national":
        doc_title = get_t("title_national", lang)
        sub_title = get_t("subtitle_national", lang, time_label=time_label)
    elif mode == "comparison":
        doc_title = get_t("title_comparison", lang)
        sub_title = get_t("subtitle_comparison", lang, time_label=time_label)
    else:
        doc_title = safe_pdf_text(str(profile.get("name", "REGIONAL ASSET")).upper())
        sub_title = get_t("subtitle_regional", lang, time_label=time_label)

    elements.append(Paragraph(doc_title, styles["Title"]))
    elements.append(Paragraph(sub_title, styles["Subtitle"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=COLOR_ORANGE, spaceBefore=4, spaceAfter=12))

    if rm.get("assurance_level"):
        assurance_val = safe_pdf_text(str(rm["assurance_level"]))
        if rm.get("assurance_provider"):
            prov_txt = safe_pdf_text(str(rm["assurance_provider"]))
            assurance_val += f" — {prov_txt}" if ("(" in prov_txt or ")" in prov_txt) else f" ({prov_txt})"
    else:
        assurance_val = get_t("meta_assurance_unspecified", lang)

    if start_y == end_y:
        period_val = f"{start_y} ({'Exercice Unique' if is_fr else 'Single-Year Series'})"
    else:
        period_val = get_t("meta_period_val", lang, time_label=time_label)

    meta_data = [
        [
            Paragraph(f"<b>{get_t('meta_period', lang)}</b>", styles["Body"]),
            Paragraph(period_val, styles["Body"]),
            Paragraph(f"<b>{get_t('meta_standard', lang)}</b>", styles["Body"]),
            Paragraph(get_t("meta_standard_val", lang), styles["Body"]),
        ],
        [
            Paragraph(f"<b>{get_t('meta_operator', lang)}</b>", styles["Body"]),
            Paragraph(safe_pdf_text(profile.get("operator") or tenant_cfg.get("organization_name", "Operator")), styles["Body"]),
            Paragraph(f"<b>{get_t('meta_gwp', lang)}</b>", styles["Body"]),
            Paragraph(get_t("meta_gwp_val", lang, standard=data["gwp_standard"], ch4_factor=data["gwp_factors"].get("CH4", 28)), styles["Body"]),
        ],
        [
            Paragraph(f"<b>{get_t('meta_basin', lang)}</b>", styles["Body"]),
            Paragraph(safe_pdf_text(profile.get("basin", "National Estate")), styles["Body"]),
            Paragraph(f"<b>{get_t('meta_decree', lang)}</b>", styles["Body"]),
            Paragraph(get_t("meta_decree_val", lang), styles["Body"]),
        ],
        [
            Paragraph(f"<b>{get_t('meta_facilities', lang)}</b>", styles["Body"]),
            Paragraph(
                ("1 CPF de Production / Traitement" if is_fr else "1 Production / Processing CPF")
                if len(data["facilities"]) == 1 else
                get_t("meta_facilities_val", lang, count=len(data["facilities"])),
                styles["Body"],
            ),
            Paragraph(f"<b>{get_t('meta_assurance', lang)}</b>", styles["Body"]),
            Paragraph(assurance_val, styles["Body"]),
        ],
    ]
    t_meta = Table(meta_data, colWidths=[134, 136, 115, 135])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 10))

    tier_info = (data.get("uncertainty") or {}).get("tier_breakdown") or {}
    tier_summary = f"Tier 1: {tier_info.get('Tier 1', 0.0)}%, Tier 2: {tier_info.get('Tier 2', 0.0)}%, Tier 3: {tier_info.get('Tier 3', 0.0)}%"
    raw_fw = tenant_cfg.get("regulatory_framework")
    if raw_fw == "Executive Decree 21-330 Article 9" and is_fr:
        framework_str = "Décret Exécutif 21-330 Article 9"
    else:
        framework_str = raw_fw or (
            "ISO 14064-1:2018 & Loi algérienne 19-13" if is_fr else "ISO 14064-1:2018 & Algerian Hydrocarbon Law 19-13"
        )
    elements.append(
        Paragraph(
            get_t("regulatory_banner", lang, framework=safe_pdf_text(framework_str), tier_summary=tier_summary),
            styles["BodyMuted"],
        )
    )
    elements.append(Spacer(1, 6))

    req_years = gov.get("required_lock_years") or list(range(start_y, end_y + 1))
    years_str = ", ".join(str(y) for y in req_years)
    if is_locked:
        gov_msg = get_t(
            "cover_locked_banner",
            lang,
            signatory=safe_pdf_text(gov.get("signoff_signatory") or gov.get("locked_by_name") or "Authorized Signatory"),
            locked_at=safe_pdf_text(gov.get("locked_at") or "Verified"),
        )
        gov_bg, gov_border = COLOR_SUCCESS_BG, COLOR_SUCCESS
    else:
        gov_msg = get_t("cover_prelim_banner", lang, years=years_str)
        gov_bg, gov_border = COLOR_AMBER_BG, COLOR_AMBER_BORDER

    t_gov = Table([[Paragraph(gov_msg, styles["BodySmall"])]], colWidths=[520])
    t_gov.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), gov_bg),
        ("BOX", (0, 0), (-1, -1), 0.8, gov_border),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_gov)
    elements.append(Spacer(1, 8))
    return elements


def _build_scorecard_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the executive KPI cards block."""
    elements = []
    timeline = data["timeline"]
    if not timeline:
        return elements

    active_entries = [t for t in timeline if (t.get("total_co2e_t") or 0.0) > 0 or (t.get("gross_gas_mmsm3") or 0.0) > 0]
    latest = active_entries[-1] if active_entries else timeline[-1]
    if active_entries and len(active_entries) > 1:
        prev = active_entries[-2]
    elif len(timeline) > 1:
        prev = timeline[-2]
    else:
        prev = latest

    co2e_delta = ((latest["total_co2e_t"] - prev["total_co2e_t"]) / prev["total_co2e_t"] * 100.0) if prev["total_co2e_t"] > 0 else 0.0
    ci_delta = ((latest["carbon_intensity_kg_boe"] - prev["carbon_intensity_kg_boe"]) / prev["carbon_intensity_kg_boe"] * 100.0) if prev["carbon_intensity_kg_boe"] > 0 else 0.0

    fi_val = latest["flaring_intensity_pct"]
    fi_status = get_t("decree_compliant", lang) if fi_val <= 1.00 else get_t("decree_exceeded", lang)
    fi_color = COLOR_SUCCESS if fi_val <= 1.00 else COLOR_DANGER

    is_single = (prev is latest) or (prev.get("year") == latest.get("year"))
    ghg_sub = get_t("scorecard_single_period", lang) if is_single else get_t("scorecard_delta", lang, delta=co2e_delta)
    ci_sub = get_t("scorecard_single_period", lang) if is_single else get_t("scorecard_delta", lang, delta=ci_delta)

    mi_val = float(latest.get("methane_intensity_pct", 0.0) or 0.0)
    mi_basis = latest.get("methane_intensity_basis", "net_gas")
    gas_out = float(latest.get("net_gas_mmsm3") or latest.get("gross_gas_mmsm3") or 0.0)
    if mi_basis == "no_gas_denominator" or gas_out <= 0:
        mi_sub = get_t("ogci_nogas_sub", lang)
        mi_color_hex = COLOR_MUTED.hexval()
    elif mi_val <= 0.20:
        mi_sub = get_t("ogci_target_sub", lang)
        mi_color_hex = "#0D9488"
    else:
        mi_sub = get_t("ogci_exceeded_sub", lang)
        mi_color_hex = COLOR_DANGER.hexval()

    cards_data = [
        [
            Paragraph(f"{latest['total_mmt']:.3f} MMt", styles["CardVal"]),
            Paragraph(f"{latest['carbon_intensity_kg_boe']:.1f}", styles["CardVal"]),
            Paragraph(f"{fi_val:.2f}%", styles["CardVal"]),
            Paragraph(f"{mi_val:.3f}%", styles["CardVal"]),
        ],
        [
            Paragraph(f"{get_t('scorecard_lbl_ghg', lang)}<br/><font size=6 color='#64748B'>{ghg_sub}</font>", styles["CardLbl"]),
            Paragraph(f"{get_t('scorecard_lbl_ci', lang)}<br/><font size=6 color='#64748B'>{ci_sub}</font>", styles["CardLbl"]),
            Paragraph(f"{get_t('scorecard_lbl_fi', lang)}<br/><font size=6 color='{fi_color.hexval()}'>{get_t('decree_card_sub', lang, status=fi_status)}</font>", styles["CardLbl"]),
            Paragraph(f"{get_t('scorecard_lbl_mi', lang)}<br/><font size=6 color='{mi_color_hex}'>{mi_sub}</font>", styles["CardLbl"]),
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

    db_badge = get_t("db_boundary_tag", lang)
    ref_badge = get_t("ref_profile_tag", lang)
    fac_notes = [
        f"<b>{safe_pdf_text(f['name'])}:</b> "
        + " — ".join(
            safe_pdf_text(str(x))
            for x in (f.get("description"), f.get("boundary_notes"))
            if x and str(x).strip()
        )
        for f in (data.get("facilities") or [])
        if (f.get("description") and str(f.get("description")).strip()) or (f.get("boundary_notes") and str(f.get("boundary_notes")).strip())
    ]

    elements.append(Paragraph(get_t("geology_title", lang), styles["H1"]))
    if fac_notes:
        elements.append(Paragraph(f"<font size=7 color='#64748B'>{safe_pdf_text(db_badge)}</font>", styles["BodyMuted"]))
        for fn in fac_notes:
            elements.append(Paragraph(fn, styles["Body"]))
    else:
        tag_html = f"<font size=7 color='#64748B'>{safe_pdf_text(ref_badge)}</font> "
        elements.append(Paragraph(f"<b>{get_t('geology_reservoir', lang)}</b> {tag_html}{safe_pdf_text(profile.get('geology', 'Hydrocarbon geological setting recorded in regional profile.'))}", styles["Body"]))
        elements.append(Paragraph(f"<b>{get_t('geology_infra', lang)}</b> {safe_pdf_text(profile.get('infrastructure', 'Gathering and processing facility network.'))}", styles["Body"]))
        elements.append(Paragraph(f"<b>{get_t('geology_flare', lang)}</b> {safe_pdf_text(profile.get('flaring_profile', 'Flare metering and reduction tracking boundary.'))}", styles["Body"]))

    gc = data.get("gas_composition")
    gc_name = data.get("gas_comp_name")
    has_custom_gc = bool(
        gc and isinstance(gc, dict) and any(float(gc.get(k, 0) or 0) > 0 for k in ("ch4_mol_pct", "c2h6_mol_pct", "co2_mol_pct"))
    )
    if has_custom_gc:
        title_prefix = f"{safe_pdf_text(gc_name)} — " if gc_name else ""
        section_title = f"{title_prefix}{get_t('gas_comp_title', lang)}"
        elements.append(Paragraph(f"<b>{section_title}</b>", styles["H2"]))
        is_fr = str(lang).lower().startswith("fr")
        h1 = TRANSLATIONS_FR.get("gas_comp_headers_r1") if is_fr else TRANSLATIONS_EN.get("gas_comp_headers_r1")
        h2 = TRANSLATIONS_FR.get("gas_comp_headers_r2") if is_fr else TRANSLATIONS_EN.get("gas_comp_headers_r2")
        r1 = [f"{gc.get('ch4_mol_pct', 0)} mol%", f"{gc.get('c2h6_mol_pct', 0)} mol%", f"{gc.get('c3h8_mol_pct', 0)} mol%", f"{gc.get('co2_mol_pct', 0)} mol%", f"{gc.get('n2_mol_pct', 0)} mol%", (f"{gc.get('h2s_mol_pct')} mol%" if gc.get('h2s_mol_pct') not in (None, "") else f"{gc.get('h2s_ppm', 0)} ppm")]
        m_keys = ("ch4_mol_pct", "c2h6_mol_pct", "c3h8_mol_pct", "ic4_mol_pct", "nc4_mol_pct", "ic5_mol_pct", "nc5_mol_pct", "c6_plus_mol_pct", "co2_mol_pct", "n2_mol_pct")
        tot = sum(float(gc.get(k, 0) or 0) for k in m_keys)
        r2 = [f"{gc.get('ic4_mol_pct', 0)} mol%", f"{gc.get('nc4_mol_pct', 0)} mol%", f"{gc.get('ic5_mol_pct', 0)} mol%", f"{gc.get('nc5_mol_pct', 0)} mol%", f"{gc.get('c6_plus_mol_pct', 0)} mol%", f"{tot:.2f} mol%"]
        font_reg_gc, font_bold_gc, _ = register_pdf_fonts()
        gc_hdr_style = ParagraphStyle("GasCompHdr", fontName=font_bold_gc, fontSize=6.4, leading=7.8, textColor=colors.white, alignment=1, spaceAfter=0)
        h1_fmt = [Paragraph(h, gc_hdr_style) for h in h1]
        h2_fmt = [Paragraph(h, gc_hdr_style) for h in h2]
        t_gc = Table([h1_fmt, r1, h2_fmt, r2], colWidths=[84, 84, 84, 92, 84, 92])
        t_gc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, 1), font_reg_gc),
            ("BACKGROUND", (0, 1), (-1, 1), COLOR_LIGHT_BG),
            ("BACKGROUND", (0, 2), (-1, 2), COLOR_SLATE),
            ("BACKGROUND", (0, 3), (-1, 3), COLOR_LIGHT_BG),
            ("FONTNAME", (0, 3), (-1, 3), font_reg_gc),
            ("FONTNAME", (-1, 3), (-1, 3), font_bold_gc),
            ("FONTSIZE", (0, 1), (-1, 1), 7.2),
            ("FONTSIZE", (0, 3), (-1, 3), 7.2),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t_gc)
    else:
        note_p = Paragraph(f"<b>{get_t('gas_comp_none_title', lang)}</b><br/>{get_t('gas_comp_none_desc', lang)}", styles["BodyMuted"])
        note_tbl = Table([[note_p]], colWidths=[520])
        note_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(note_tbl)

    elements.append(Spacer(1, 10))
    return elements


def _build_glidepath_elements(
    data: Dict[str, Any],
    chart_path: Optional[str],
    styles: Dict[str, ParagraphStyle],
    lang: str = "en",
    img_height: float = 165,
    for_toc_pass: bool = False,
) -> List[Any]:
    """Generates Chapter 9: 2030 Corporate Decarbonization Target Glidepath and milestone table."""
    target_proj = data.get("target_projection", {})
    if not target_proj:
        return []
    elements = []
    font_reg, font_bold, _ = register_pdf_fonts()
    elements.append(Paragraph(get_t("ch9_title", lang), styles["H1"]))
    ch9_desc = get_t("ch9_desc", lang)
    if data.get("mode") == "regional":
        ch9_desc = f"{ch9_desc} <font size=7.5 color='#64748B'>{safe_pdf_text(get_t('corp_boundary_badge', lang))}</font>"
    elements.append(Paragraph(ch9_desc, styles["Body"]))
    img_flow = _chart_flowable(chart_path, width=520, height=img_height, for_toc_pass=for_toc_pass)
    if img_flow is not None:
        elements.append(img_flow)
        elements.append(Spacer(1, 6))

    is_fr = str(lang).lower().startswith("fr")
    headers = TRANSLATIONS_FR["ch9_headers"] if is_fr else TRANSLATIONS_EN["ch9_headers"]
    ch9_hdr_style = ParagraphStyle("Ch9Hdr", fontName=font_bold, fontSize=6.6, leading=8.0, textColor=colors.white, alignment=1, spaceAfter=0)
    ch9_cell_ctr = ParagraphStyle("Ch9CellCtr", fontName=font_reg, fontSize=7.2, leading=8.8, textColor=COLOR_DARK, alignment=1, spaceAfter=0)
    headers_fmt = [Paragraph(h, ch9_hdr_style) for h in headers]
    milestones = target_proj.get("milestones", [])
    _FLARE_OBJ_FR = {
        "Audited Baseline Level": "Niveau de Référence Audité",
        "Current Operating Flaring": "Torchage Opérationnel Actuel",
        "Eliminate Routine Flaring (<0.8%)": "Éliminer Torchage Routine (<0,8%)",
        "World Bank Zero Routine Flaring": "Zéro Torchage Routine (Banque Mondiale)",
    }
    rows = []
    for m in milestones:
        stat = localize_status(m.get("status", "Planned"), lang)
        red_raw = str(m.get("reduction_str", "0.0%"))
        fobj_raw = str(m.get("flaring_objective", "Zero Routine Flaring"))
        if is_fr:
            red_disp = "Point de Référence" if red_raw == "Reference Point" else red_raw.replace("GHG vs Baseline", "GES vs Référence").replace("vs Baseline", "vs Référence")
            fobj_disp = _FLARE_OBJ_FR.get(fobj_raw, fobj_raw)
        else:
            red_disp = red_raw
            fobj_disp = fobj_raw
        rows.append([
            str(m.get("year", "")),
            f"{m.get('target_ghg_mmt', 0.0):.3f}",
            Paragraph(safe_pdf_text(red_disp), ch9_cell_ctr),
            Paragraph(safe_pdf_text(fobj_disp), ch9_cell_ctr),
            stat,
        ])
    if rows:
        t_m = Table([headers_fmt] + rows, colWidths=[60, 100, 110, 155, 95])
        t_m.setStyle(TableStyle([
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
        elements.append(t_m)
    elements.append(Spacer(1, 12))
    return elements


def _build_jv_equity_elements(
    data: Dict[str, Any],
    chart_path: Optional[str],
    styles: Dict[str, ParagraphStyle],
    lang: str = "en",
    for_toc_pass: bool = False,
) -> List[Any]:
    """Generates Chapter 11: Joint Venture Partner Equity Share Allocation and partner breakdown table."""
    jv_equity = data.get("jv_equity", {})
    if not jv_equity or not jv_equity.get("partners"):
        return []
    elements = []
    elements.append(Paragraph(get_t("ch11_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("ch11_desc", lang), styles["Body"]))
    img_flow = _chart_flowable(chart_path, width=520, height=225, for_toc_pass=for_toc_pass)
    if img_flow is not None:
        elements.append(img_flow)
        elements.append(Spacer(1, 6))

    raw_headers = TRANSLATIONS_FR["ch11_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch11_headers"]
    partners = jv_equity.get("partners", [])
    timeline = data.get("timeline") or []
    active_timeline = [t for t in timeline if (t.get("total_co2e_t") or 0.0) > 0]
    fallback_latest = (
        active_timeline[-1].get("year")
        if active_timeline
        else (timeline[-1].get("year", 2025) if timeline else 2025)
    )
    latest_year = (
        partners[0].get("latest_year")
        if (partners and partners[0].get("latest_year") is not None)
        else fallback_latest
    )
    start_year = data.get("start_year", 2021)
    end_year = data.get("end_year", 2025)
    num_years = end_year - start_year + 1
    headers = [h.format(latest_year=latest_year, num_years=num_years) for h in raw_headers]

    font_reg, font_bold, _ = register_pdf_fonts()
    hdr_style = ParagraphStyle(
        "JVHdr",
        fontName=font_bold,
        fontSize=6.8,
        leading=8,
        textColor=colors.white,
        alignment=1,
    )
    formatted_headers = [Paragraph(h, hdr_style) for h in headers]
    rows = []
    for p in partners:
        rows.append([
            p.get("partner_name", ""),
            f"{p.get('equity_share_pct', 0.0):.1f}%",
            f"{p.get('latest_year_co2e', 0.0):,.0f}",
            f"{p.get('equity_total_ghg_tco2e', 0.0):,.0f}",
            f"{p.get('equity_s1_tco2e', 0.0):,.0f}",
            f"{p.get('equity_ch4_t', 0.0):,.0f}",
        ])
    if rows:
        t_jv = Table([formatted_headers] + rows, colWidths=[100, 70, 85, 95, 85, 85])
        t_jv.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
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


def _build_benchmark_league_elements(data: Dict[str, Any], chart_path: str, styles: Dict[str, ParagraphStyle], lang: str = "en", for_toc_pass: bool = False) -> List[Any]:
    """Builds the multi-region league table and comparative chart for comparison mode."""
    elements = []
    elements.append(Paragraph(get_t("bench_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("bench_desc", lang), styles["Body"]))

    img_flow = _chart_flowable(chart_path, width=520, height=240, for_toc_pass=for_toc_pass)
    if img_flow is not None:
        elements.append(img_flow)
        elements.append(Spacer(1, 6))

    benchmarks = data.get("regional_benchmarks", [])
    if benchmarks:
        b_headers = TRANSLATIONS_FR["bench_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["bench_headers"]
        font_reg, font_bold, _ = register_pdf_fonts()
        b_hdr_style = ParagraphStyle("BenchHdr", fontName=font_bold, fontSize=6.6, leading=8.0, textColor=colors.white, alignment=1, spaceAfter=0)
        b_cell_l = ParagraphStyle("BenchCellL", fontName=font_reg, fontSize=7.0, leading=8.5, textColor=COLOR_DARK, alignment=0, spaceAfter=0)
        b_headers_fmt = [Paragraph(h, b_hdr_style) for h in b_headers]
        b_rows = []
        for b in sorted(benchmarks, key=lambda x: x.get("carbon_intensity_kg_boe") or 0.0):
            stat = (get_t("decree_compliant", lang) if b.get("decree_compliant") else get_t("decree_exceeded", lang))                 if b.get("decree_compliant") is not None else "n/a"
            b_rows.append([
                Paragraph(safe_pdf_text(str(b.get("name", "")).split("(")[0].strip()), b_cell_l),
                localize_segment(b.get("segment", "Upstream"), lang),
                str(b.get("facility_count", 1)),
                f"{b.get('total_mmboe', 0.0):.2f}",
                f"{b['carbon_intensity_kg_boe']:.1f}" if b.get("carbon_intensity_kg_boe") is not None else "n/a",
                f"{b['flaring_intensity_pct']:.2f}%" if b.get("flaring_intensity_pct") is not None else "n/a",
                stat,
            ])
        t_b = Table([b_headers_fmt] + b_rows, colWidths=[140, 56, 62, 62, 66, 66, 68])
        t_b.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
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
    """Generates the official MRV verification certificate and canonical SHA-256 fingerprint, gated by PeriodLock."""
    is_fr = str(lang).lower().startswith("fr")
    gov = data.get("governance") or {}
    is_locked = bool(gov.get("is_locked"))

    elements = []
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(get_t("signoff_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("signoff_cert", lang), styles["Body"]))

    tenant_cfg = data.get("tenant_config") or get_tenant_config(data.get("tenant_id"))
    org = safe_pdf_text(data.get("profile", {}).get("operator") or tenant_cfg.get("organization_name", "Operator"))
    hse_signer = safe_pdf_text(tenant_cfg.get("hse_director_name", "HSE Director (Demo)"))
    auditor_signer = safe_pdf_text(tenant_cfg.get("lead_auditor_name", "Lead Verifier (Demo)"))
    vp_signer = safe_pdf_text(tenant_cfg.get("vp_upstream_name", "VP Operations (Demo)"))

    if is_locked:
        stamp_hse = get_t("sign_stamp_hse", lang, hse_signer=hse_signer, org=org)
        stamp_aud = get_t("sign_stamp_auditor", lang, auditor_signer=auditor_signer)
        stamp_vp = get_t("sign_stamp_vp", lang, vp_signer=safe_pdf_text(gov.get("signoff_signatory") or vp_signer), org=org)
    else:
        stamp_hse = get_t("sign_stamp_pending_hse", lang, hse_signer=hse_signer, org=org)
        stamp_aud = get_t("sign_stamp_pending_auditor", lang, auditor_signer=auditor_signer)
        stamp_vp = get_t("sign_stamp_pending_vp", lang, vp_signer=vp_signer, org=org)

    sign_data = [
        [
            Paragraph(get_t("role_hse", lang, org=org), styles["Body"]),
            Paragraph(get_t("role_auditor", lang), styles["Body"]),
            Paragraph(get_t("role_vp", lang, org=org), styles["Body"]),
        ],
        [
            Paragraph(stamp_hse, styles["Body"]),
            Paragraph(stamp_aud, styles["Body"]),
            Paragraph(stamp_vp, styles["Body"]),
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
    elements.append(Spacer(1, 6))

    if is_locked:
        signatory = safe_pdf_text(gov.get("signoff_signatory") or gov.get("locked_by_name") or "Authorized Signatory")
        locked_at = safe_pdf_text(gov.get("locked_at") or "Locked")
        notes = safe_pdf_text(gov.get("signoff_notes") or "—")
        lock_banner = (
            f"<b>PÉRIODE VERROUILLÉE &amp; APPROUVÉE :</b> Clôture par {signatory} le {locked_at} | Notes : {notes}"
            if is_fr else
            f"<b>PERIOD LOCK VERIFIED &amp; SEALED:</b> Locked by {signatory} on {locked_at} | Sign-off Notes: {notes}"
        )
        t_lock = Table([[Paragraph(lock_banner, styles["BodySmall"])]], colWidths=[520])
        t_lock.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_SUCCESS_BG),
            ("BOX", (0, 0), (-1, -1), 0.8, COLOR_SUCCESS),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_lock)
    else:
        req_years = gov.get("required_lock_years") or list(range(data.get("start_year", 2023), data.get("end_year", 2023) + 1))
        years_str = ", ".join(str(y) for y in req_years)
        t_lock = Table([[Paragraph(get_t("signoff_pending_notice", lang, years=years_str), styles["BodySmall"])]], colWidths=[520])
        t_lock.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_AMBER_BG),
            ("BOX", (0, 0), (-1, -1), 0.8, COLOR_AMBER_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t_lock)
    elements.append(Spacer(1, 6))

    hash_p = f"<b>{get_t('fingerprint_lbl', lang)}</b> <code>{sha256_hash}</code><br/>{get_t('generated_lbl', lang)} {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    elements.append(Paragraph(hash_p, styles["BodyMuted"]))
    return elements


def _build_process_architecture_elements(
    data: Dict[str, Any],
    pfd_charts: Optional[Dict[str, str]],
    styles: Dict[str, ParagraphStyle],
    lang: str = "en",
    for_toc_pass: bool = False,
) -> List[Any]:
    """Generates the Process Architecture & PFD Flowchart section for facilities in scope."""
    elements = []
    facilities = data.get("facilities", [])
    if not facilities or not pfd_charts:
        return []

    is_fr = str(lang).lower().startswith("fr")
    ill_tag = get_t("pfd_illustrative_tag", lang)
    title = ("ARCHITECTURE DES INSTALLATIONS & PROCÉDÉS CPF " if is_fr else "CPF PROCESS ARCHITECTURE & GATHERING NETWORK ") + f"<font size=8 color='#64748B'>{safe_pdf_text(ill_tag)}</font>"
    desc = (
        "Schémas de principe illustratifs des centres de traitement (CPF) ; les modules colorés reflètent les catégories de sources d'émissions enregistrées en base."
        if is_fr else
        "Illustrative process block flow topology across reporting production complexes; highlighted blocks correspond to emission source modules logged in the database."
    )
    elements.append(Paragraph(title, styles["H1"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 4))

    ledger_by_fac = data.get("granular_source_ledger", {}).get("ledger_by_facility", {})
    active_mods = data.get("active_modules") or []
    active_by_fac = data.get("active_modules_by_facility") or {}
    for fac in facilities:
        fname = fac["name"]
        if ledger_by_fac and not ledger_by_fac.get(fname):
            continue
        chart_path = pfd_charts.get(fname)
        if chart_path and os.path.exists(chart_path):
            fac_mods = active_by_fac[fname] if fname in active_by_fac else active_mods
            fac_mods_str = ", ".join(fac_mods) if fac_mods else ("aucun" if is_fr else "none logged")
            fname_esc = safe_pdf_text(fname)
            sub_title = f"{fname_esc} — {'Architecture des Procédés CPF' if is_fr else 'Process Flow &amp; Block Overview'} {safe_pdf_text(ill_tag)}"
            elements.append(Paragraph(f"<b>{sub_title}</b>", styles["H2"]))
            pfd_img = _chart_flowable(chart_path, width=520, height=255, for_toc_pass=for_toc_pass)
            if pfd_img is not None:
                elements.append(pfd_img)
            elements.append(Spacer(1, 4))
            db_desc = fac.get("description")
            if db_desc and str(db_desc).strip():
                narrative = f"{safe_pdf_text(str(db_desc).strip())} ({'Modules actifs en base' if is_fr else 'Active DB modules'}: {safe_pdf_text(fac_mods_str)})."
            else:
                narrative = (
                    f"Schéma de principe illustratif de l'installation {fname_esc} — modules actifs détectés dans la base : {safe_pdf_text(fac_mods_str)}."
                    if is_fr else
                    f"Illustrative block flow diagram for {fname_esc} — active modules detected from logged database sources: {safe_pdf_text(fac_mods_str)}."
                )
            elements.append(Paragraph(narrative, styles["BodyMuted"]))
            elements.append(Spacer(1, 6))

    return elements
