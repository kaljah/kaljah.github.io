"""Master report Chapter 12: QA/QC protocols, statutory regimes, base year recalculations and uncertainty
(split from master_report_appendices.py)."""

from typing import Any, Dict, List
from services.master_report_appendices import (
    COLOR_BORDER,
    COLOR_CARD_BG,
    COLOR_DARK,
    COLOR_LIGHT_BG,
    COLOR_SLATE,
    register_pdf_fonts,
)
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from services.master_report_i18n import get_t
from services.pdf_escape import safe_pdf_text


def _qaqc_protocol_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str, is_fr: bool, latest_t: Dict[str, Any]) -> List[Any]:
    """QA/QC protocols narrative built from the records in the report."""
    elements = []
    # 1. Dynamic Database-Driven Quality Assurance Protocols Narrative
    elements.append(Paragraph(f"<b>{get_t('qaqc_proto_title', lang)}</b>", styles["H2"]))

    dre_val = latest_t.get("measured_dre_pct") if latest_t else None
    has_measured_dre = bool(latest_t.get("has_measured_dre")) or (dre_val is not None)
    streams = data.get("multistream_gas_chromatography") or []
    gc_cnt = len(streams)
    ogmp = data.get("ogmp") or {}
    survey_cnt = len(ogmp.get("surveys") or [])
    comp_cnt = int(ogmp.get("total_components_monitored") or 0)
    excl_tot = int((data.get("excluded_unverified") or {}).get("total_excluded", 0) or 0)

    if is_fr:
        dre_clause = (
            f"Les rendements de destruction en torchage s'appuient sur la télémétrie optique vérifiée ({float(dre_val):.2f} % DRE)."
            if (has_measured_dre and dre_val is not None) else
            "Aucune télémétrie optique VISR de torche n'étant enregistrée sur la période, le rendement par défaut EPA de 98,0 % est appliqué."
        )
        gc_clause = (
            f"La caractérisation du gaz repose sur {gc_cnt} analyse(s) chromatographique(s) de laboratoire approuvée(s) en base."
            if gc_cnt > 0 else
            "0 analyse chromatographique spécifique au site n'est enregistrée en base (spécifications gaz standard appliquées)."
        )
        ogmp_clause = (
            f"Le suivi des fuites intègre {comp_cnt:,} composant(s) LDAR et {survey_cnt} campagne(s) OGMP 2.0."
            if (survey_cnt > 0 or comp_cnt > 0) else
            "Aucune campagne descendante OGMP 2.0 ni inventaire composant LDAR n'est enregistré pour ce périmètre."
        )
        excl_clause = (
            f" Par filtrage QA/QC strict, {excl_tot} enregistrement(s) non vérifié(s) ou test ont été exclus."
            if excl_tot > 0 else
            " Seuls les enregistrements au statut « Verified » (hors lignes de test) sont inclus."
        )
        proto_text = (
            f"Les données d'émissions et de production proviennent exclusivement des enregistrements vérifiés de la base "
            f"accompagnés d'une empreinte d'intégrité SHA-256. {dre_clause} {gc_clause} {ogmp_clause}{excl_clause}"
        )
    else:
        dre_clause = (
            f"Flare destruction efficiency reflects verified field/optical telemetry ({float(dre_val):.2f}% DRE)."
            if (has_measured_dre and dre_val is not None) else
            "No verified optical VISR flare telemetry is logged for the period; the EPA 98.0% engineering default DRE applies."
        )
        gc_clause = (
            f"Fuel and flare gas properties draw from {gc_cnt} approved multi-stream gas chromatography assay(s) in the database."
            if gc_cnt > 0 else
            "0 site-specific laboratory gas chromatography assays are logged in the database (standard fuel gas defaults applied)."
        )
        ogmp_clause = (
            f"Fugitive management tracks {comp_cnt:,} LDAR component(s) and {survey_cnt} OGMP 2.0 survey campaign(s)."
            if (survey_cnt > 0 or comp_cnt > 0) else
            "0 OGMP 2.0 top-down campaigns or component-level LDAR logs are recorded for this perimeter."
        )
        excl_clause = (
            f" Strict QA/QC status gating excluded {excl_tot} unverified, pending, or test record(s) from official totals."
            if excl_tot > 0 else
            " Strict QA/QC status gating admits Verified production and emission records only (non-test)."
        )
        proto_text = (
            f"Emission and production ledgers are compiled directly from Verified software records anchored to a canonical "
            f"dataset SHA-256 checksum. {dre_clause} {gc_clause} {ogmp_clause}{excl_clause}"
        )
    elements.append(Paragraph(proto_text, styles["Body"]))
    return elements


def _qaqc_statute_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str, is_fr: bool, latest_t: Dict[str, Any], font_reg: str, font_bold: str) -> List[Any]:
    """Statutory regimes compliance matrix."""
    elements = []
    # 2. Statutory Regimes Compliance Matrix
    elements.append(Paragraph(f"<b>{get_t('qaqc_statute_title', lang)}</b>", styles["H2"]))
    stat_headers = get_t("qaqc_statute_headers", lang)

    fi = latest_t.get("flaring_intensity_pct", 0.0)
    is_compliant = latest_t.get("decree_21_330_compliant", False)
    if is_compliant:
        d21_status = get_t("qaqc_statute_d21_pass", lang)
    else:
        d21_status = get_t("qaqc_statute_d21_fail", lang, flaring_pct=f"{fi:.2f}")

    gov = data.get("governance") or {}
    rm = gov.get("reporting_metadata") or {}
    is_locked = bool(gov.get("is_locked"))
    raw_assur = rm.get("assurance_level")
    if raw_assur:
        assur_txt = safe_pdf_text(str(raw_assur))
        if rm.get("assurance_provider"):
            prov_txt = safe_pdf_text(str(rm["assurance_provider"]))
            assur_txt += f" — {prov_txt}" if ("(" in prov_txt or ")" in prov_txt) else f" ({prov_txt})"
        iso_status = assur_txt if is_locked else (("Provisoire (Non verrouillé) — " if is_fr else "Provisional (Unlocked) — ") + assur_txt)
    else:
        if is_locked:
            iso_status = "Inventaire Verrouillé (Assurance externe non spécifiée)" if is_fr else "Locked Internal Inventory (External Assurance Unspecified)"
        else:
            iso_status = "Inventaire Provisoire Auto-Déclaré (Non verrouillé)" if is_fr else "Provisional Self-Declared Inventory (Unlocked)"

    mi_val = latest_t.get("methane_intensity_pct")
    mi_basis = latest_t.get("methane_intensity_basis")
    gas_denom = float(latest_t.get("net_gas_mmsm3") or latest_t.get("gross_gas_mmsm3") or 0.0)
    if mi_basis == "no_gas_denominator" or (mi_val is not None and gas_denom <= 0):
        ogci_status = "N/D — Aucun volume gaz sur la période" if is_fr else "N/A — No Gas Volume in Period"
    elif mi_val is not None and float(mi_val) <= 0.20:
        ogci_status = f"Objectif Atteint ({float(mi_val):.3f} % ≤ 0,20 %)" if is_fr else f"Target Achieved ({float(mi_val):.3f}% ≤ 0.20%)"
    elif mi_val is not None:
        ogci_status = f"Seuil Dépassé ({float(mi_val):.3f} % > 0,20 %)" if is_fr else f"Target Exceeded ({float(mi_val):.3f}% > 0.20%)"
    else:
        ogci_status = "N/D — Données intensité méthane absentes" if is_fr else "N/A — Methane intensity unavailable"

    if is_fr:
        raw_stat_rows = [
            ["Décret Exécutif 21-330 Art. 9", "Loi Hydrocarbures 19-13", "Plafond obligatoire de torchage ≤ 1,00 % de la production brute", d21_status],
            ["Décret Exécutif 06-138", "Ministère de l'Environnement", "Valeurs limites de rejets atmosphériques industriels (mg/Nm³)", "Non vérifié — Mesures cheminée requises"],
            ["Spécification ISO 14064-1:2018", "Normalisation Internationale", "Directives de quantification et de déclaration des inventaires GES", iso_status],
            ["Initiative Climat OGCI", "Consortium Mondial Oil &amp; Gas", "Cible d'intensité méthane ≤ 0,20 % du gaz commercialisé", ogci_status],
        ]
    else:
        raw_stat_rows = [
            ["Executive Decree 21-330 Art. 9", "Hydrocarbon Law 19-13", "Mandatory gas flaring ceiling not to exceed 1.00% of gross output", d21_status],
            ["Executive Decree 06-138", "Ministry of Environment", "Atmospheric emission limit values (mg/Nm³) for industrial facilities", "Not Verified — Stack Data Required"],
            ["ISO 14064-1:2018 Specification", "International Standards", "Specification with guidance for quantification and reporting of GHG", iso_status],
            ["OGCI Climate Initiative", "Global Oil &amp; Gas Consortium", "Methane intensity ceiling not to exceed 0.20% of marketed gas", ogci_status],
        ]

    stat_hdr_style = ParagraphStyle(
        "StatHdr", fontName=font_bold, fontSize=7, leading=8.5, textColor=colors.white
    )
    stat_cell_style = ParagraphStyle(
        "StatCell", fontName=font_reg, fontSize=6.8, leading=8, textColor=COLOR_SLATE
    )
    stat_headers_fmt = [Paragraph(h, stat_hdr_style) for h in stat_headers]
    stat_rows = [
        [
            Paragraph(r[0], stat_cell_style),
            Paragraph(r[1], stat_cell_style),
            Paragraph(r[2], stat_cell_style),
            Paragraph(f"<b>{r[3]}</b>", stat_cell_style),
        ]
        for r in raw_stat_rows
    ]

    t_stat = Table([stat_headers_fmt] + stat_rows, colWidths=[115, 105, 190, 110])
    t_stat.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_stat)
    elements.append(Spacer(1, 8))
    return elements


def _qaqc_recalculation_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str, font_reg: str, font_bold: str) -> List[Any]:
    """Base year recalculation audit trail (ISO 14064-1:2018 Clause 6.4.1)."""
    elements = []
    # 3. Base Year Recalculation Audit Trail (ISO 14064-1:2018 Clause 6.4.1)
    recalcs = data.get("base_year_recalcs", [])
    recalc_heading = get_t("recalc_title", lang)
    if data.get("mode") == "regional":
        recalc_heading = f"{recalc_heading} <font size=7 color='#64748B'>{safe_pdf_text(get_t('corp_boundary_badge', lang))}</font>"
    elements.append(Paragraph(f"<b>{recalc_heading}</b>", styles["H2"]))
    if recalcs:
        r_headers = get_t("recalc_headers", lang)
        r_hdr_style = ParagraphStyle("RHdr", fontName=font_bold, fontSize=6.2, leading=7.2, textColor=colors.white, alignment=1)
        r_headers_fmt = [Paragraph(h, r_hdr_style) for h in r_headers]
        pending_lbl = get_t("pending_approval_lbl", lang)
        r_rows = []
        for r in recalcs[:5]:
            reason_p = Paragraph(f"<i>{safe_pdf_text(r.get('reason', ''))}</i>", styles["BodySmall"] if "BodySmall" in styles else styles["Body"])
            d_val = f"{r.get('delta_pct', 0.0):+.1f}%"
            approver_val = r.get("approved_by") or pending_lbl
            r_rows.append([
                str(r.get("year", "")),
                r.get("date", ""),
                reason_p,
                f"{r.get('previous_emissions_t', 0.0):,.0f}",
                f"{r.get('adjusted_emissions_t', 0.0):,.0f}",
                d_val,
                str(approver_val),
            ])
        t_recalc = Table([r_headers_fmt] + r_rows, colWidths=[42, 55, 178, 60, 60, 45, 80])
        t_recalc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("FONTSIZE", (0, 1), (-1, -1), 6.5),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (2, 1), (2, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(t_recalc)
        elements.append(Spacer(1, 6))
    else:
        empty_r = Table([[Paragraph(get_t("recalc_empty_notice", lang), styles["BodyMuted"])]], colWidths=[520])
        empty_r.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(empty_r)
        elements.append(Spacer(1, 6))
    return elements


def _qaqc_uncertainty_elements(uncert: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str, is_fr: bool, font_reg: str, font_bold: str) -> List[Any]:
    """Uncertainty summary and per-category table (IPCC Approach 1 / Monte Carlo)."""
    elements = []
    # 4. Measurement Uncertainty Assessment (IPCC Approach 1 & Monte Carlo)
    elements.append(Paragraph(f"<b>{get_t('qaqc_uncert_title', lang)}</b>", styles["H2"]))
    overall_u = safe_pdf_text(uncert.get("inventory_uncertainty_pct") or "N/A")
    tier_info = uncert.get("tier_breakdown") or {}
    t1_pct = tier_info.get("Tier 1", 0.0) if isinstance(tier_info, dict) else 0.0
    t2_pct = tier_info.get("Tier 2", 0.0) if isinstance(tier_info, dict) else 0.0
    t3_pct = tier_info.get("Tier 3", 0.0) if isinstance(tier_info, dict) else 0.0
    has_mc = bool(uncert.get("monte_carlo"))
    mc_label = (
        ("Itérations Monte Carlo : <b>2 500</b>" if has_mc else "Méthode : <b>GIEC Approche 1 (IC 95 %, k=2)</b>")
        if is_fr else
        ("Monte Carlo Iterations: <b>2,500</b>" if has_mc else "Method: <b>IPCC Approach 1 (95% CI, k=2)</b>")
    )

    kpi_text = get_t(
        "qaqc_summary_kpi",
        lang,
        overall_uncert=overall_u,
        tier1_pct=t1_pct,
        tier2_pct=t2_pct,
        tier3_pct=t3_pct,
        mc_label=mc_label,
    )
    t_kpi = Table([[Paragraph(kpi_text, styles["Body"])]], colWidths=[520])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD_BG),
        ("BOX", (0, 0), (-1, -1), 0.8, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements.append(t_kpi)
    elements.append(Spacer(1, 6))

    uncert_headers = get_t("qaqc_uncert_headers", lang)
    categories = uncert.get("categories", [])
    FR_CATEGORY_MAP = {
        "Stationary Fuel Gas Combustion": "Combustion stationnaire de gaz combustible",
        "Stationary Combustion": "Combustion stationnaire",
        "Flaring": "Torchage",
        "Routine Flaring": "Torchage de routine",
        "Non-Routine Flaring": "Torchage non-routine",
        "Safety Flaring": "Torchage de sécurité",
        "Operational Flaring (Routine & Safety)": "Torchage opérationnel (Routine et Sécurité)",
        "Operational Flaring (Routine)": "Torchage de routine",
        "Operational Flaring (Non-Routine)": "Torchage non-routine",
        "Operational Flaring (Safety)": "Torchage de sécurité",
        "Operational Flaring": "Torchage opérationnel",
        "Venting (Blowdown)": "Éventage (Dépressurisation)",
        "Oil and Gas Venting": "Éventage pétrole et gaz",
        "Associated Gas Venting": "Éventage de gaz associé",
        "Process Venting & Tank Storage": "Éventage de procédés et bacs de stockage",
        "Process Venting & Depressurization": "Éventage de procédés et dépressurisation",
        "Onshore Equipment Leaks / Fugitives": "Fuites d'équipements terrestres / Fugitives",
        "Fugitive LDAR Component Leaks": "Émissions fugitives sur composants (LDAR)",
        "Mobile Combustion": "Combustion mobile",
        "Storage Tanks": "Bacs de stockage",
        "Storage Tank - Flashing/Events": "Bacs de stockage (Flashing / Événements)",
        "Storage Tank - Working Losses": "Bacs de stockage (Pertes d'exploitation)",
        "Storage Tank - Breathing Losses": "Bacs de stockage (Pertes par respiration)",
        "Purchased Electricity (Scope 2)": "Électricité réseau importée (Scope 2)",
        "Scope 2 (Indirect)": "Scope 2 (Électricité indirecte)",
        "Scope 3 (Value Chain)": "Scope 3 (Chaîne de valeur)",
    }
    u_hdr_style = ParagraphStyle("UHdr", fontName=font_bold, fontSize=6.4, leading=7.8, textColor=colors.white, alignment=1)
    u_cell_style = ParagraphStyle("UCell", fontName=font_reg, fontSize=6.8, leading=8.0, textColor=COLOR_SLATE)
    uncert_headers_fmt = [Paragraph(h, u_hdr_style) for h in uncert_headers]
    u_rows = []
    for c in categories[:7]:
        cat_name = c.get("category", "")
        if is_fr:
            cat_name = FR_CATEGORY_MAP.get(cat_name, cat_name)
        tot_mass = f"{c.get('total_emissions', 0.0):,.0f}"
        u1_val = f"±{c.get('uncertainty_1sigma', 0.0) * 100:.1f}%"
        u95_val = c.get("uncertainty_pct", "±0.0%")
        lvl_raw = (c.get("level", "low")).upper()
        if is_fr:
            lvl = "FAIBLE" if lvl_raw == "LOW" else ("MOYEN" if lvl_raw == "MEDIUM" else "ÉLEVÉ")
        else:
            lvl = lvl_raw
        u_rows.append([Paragraph(safe_pdf_text(cat_name), u_cell_style), tot_mass, u1_val, u95_val, lvl])

    if u_rows:
        t_u = Table([uncert_headers_fmt] + u_rows, colWidths=[160, 85, 80, 110, 85])
        t_u.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
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
        elements.append(t_u)
    else:
        no_data_msg = "Aucun enregistrement d'émissions disponible pour le calcul d'incertitude." if is_fr else "No emission records available for category-level uncertainty calculation."
        elements.append(Paragraph(f"<i>{no_data_msg}</i>", styles["BodyMuted"]))

    elements.append(Spacer(1, 10))
    return elements


def build_qaqc_uncertainty_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates Chapter 9: QA/QC Verification Protocols, Statutory Regimes & Measurement Uncertainty."""
    elements = []
    uncert = data.get("uncertainty", {})
    is_fr = str(lang).lower().startswith("fr")
    font_reg, font_bold, _ = register_pdf_fonts()

    elements.append(Paragraph(get_t("qaqc_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("qaqc_desc", lang), styles["Body"]))
    timeline = data.get("timeline", [])
    active_timeline = [t for t in timeline if (t.get("total_co2e_t") or 0.0) > 0 or (t.get("gross_gas_mmsm3") or 0.0) > 0]
    latest_t = active_timeline[-1] if active_timeline else (timeline[-1] if timeline else {})

    elements.extend(_qaqc_protocol_elements(data, styles, lang, is_fr, latest_t))
    elements.extend(_qaqc_statute_elements(data, styles, lang, is_fr, latest_t, font_reg, font_bold))
    elements.extend(_qaqc_recalculation_elements(data, styles, lang, font_reg, font_bold))
    elements.extend(_qaqc_uncertainty_elements(uncert, styles, lang, is_fr, font_reg, font_bold))

    return elements
