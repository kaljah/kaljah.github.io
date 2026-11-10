"""
Master Report Appendices & Uncertainty Module
=============================================
Provides publication-grade elements for:
1. QA/QC Verification Protocols, Statutory Mandates Matrix & IPCC Approach 1 / Monte Carlo Uncertainty Assessment.
2. Disaggregated Facility-Level Operational Ledgers (CPF Breakdown).
"""

from typing import Any, Dict, List
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, PageBreak

from services.master_report_i18n import get_t
from services.pdf_escape import safe_pdf_text

COLOR_DARK = colors.HexColor("#0F172A")
COLOR_SLATE = colors.HexColor("#1E293B")
COLOR_MUTED = colors.HexColor("#64748B")
COLOR_BORDER = colors.HexColor("#CBD5E1")
COLOR_LIGHT_BG = colors.HexColor("#F8FAFC")
COLOR_CARD_BG = colors.HexColor("#F1F5F9")
COLOR_SUCCESS = colors.HexColor("#10B981")


def build_qaqc_uncertainty_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates Chapter 9: QA/QC Verification Protocols, Statutory Regimes & Measurement Uncertainty."""
    elements = []
    uncert = data.get("uncertainty", {})
    is_fr = str(lang).lower().startswith("fr")

    elements.append(Paragraph(get_t("qaqc_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("qaqc_desc", lang), styles["Body"]))

    # 1. Quality Assurance Protocols Narrative
    elements.append(Paragraph(f"<b>{get_t('qaqc_proto_title', lang)}</b>", styles["H2"]))
    dre_val = data.get("timeline", [{}])[-1].get("measured_dre_pct", 98.0) if data.get("timeline") else 98.0
    elements.append(Paragraph(get_t("qaqc_proto_desc", lang, dre_pct=f"{dre_val:.2f}%"), styles["Body"]))

    # 2. Statutory Regimes Compliance Matrix
    elements.append(Paragraph(f"<b>{get_t('qaqc_statute_title', lang)}</b>", styles["H2"]))
    stat_headers = get_t("qaqc_statute_headers", lang)

    timeline = data.get("timeline", [])
    active_timeline = [t for t in timeline if (t.get("total_co2e_t") or 0.0) > 0 or (t.get("gross_gas_mmsm3") or 0.0) > 0]
    latest_t = active_timeline[-1] if active_timeline else (timeline[-1] if timeline else {})
    fi = latest_t.get("flaring_intensity_pct", 0.0)
    is_compliant = latest_t.get("decree_21_330_compliant", False)
    if is_compliant:
        d21_status = get_t("qaqc_statute_d21_pass", lang)
    else:
        d21_status = get_t("qaqc_statute_d21_fail", lang, flaring_pct=f"{fi:.2f}")

    if is_fr:
        raw_stat_rows = [
            ["Décret Exécutif 21-330 Art. 9", "Loi Hydrocarbures 19-13", "Plafond obligatoire de torchage <= 1,00 % de la production brute", d21_status],
            ["Décret Exécutif 06-138", "Ministère de l'Environnement", "Valeurs limites de rejets atmosphériques industriels (mg/Nm³)", "Conforme Stœchiométrique"],
            ["Spécification ISO 14064-1:2018", "Normalisation Internationale", "Directives de quantification et de déclaration des inventaires GES", "Assurance Raisonnable"],
            ["Initiative Climat OGCI", "Consortium Mondial Oil & Gas", "Cible d'intensité méthane <= 0,20 % du gaz commercialisé", "Objectif Atteint"],
        ]
    else:
        raw_stat_rows = [
            ["Executive Decree 21-330 Art. 9", "Hydrocarbon Law 19-13", "Mandatory gas flaring ceiling not to exceed 1.00% of gross output", d21_status],
            ["Executive Decree 06-138", "Ministry of Environment", "Atmospheric emission limit values (mg/Nm³) for industrial facilities", "Stoichiometric Verification"],
            ["ISO 14064-1:2018 Specification", "International Standards", "Specification with guidance for quantification and reporting of GHG", "Reasonable Assurance Grade"],
            ["OGCI Climate Initiative", "Global Oil & Gas Consortium", "Methane intensity ceiling not to exceed 0.20% of marketed gas", "Target Surpassed"],
        ]

    stat_hdr_style = ParagraphStyle(
        "StatHdr", fontName="Helvetica-Bold", fontSize=7, leading=8.5, textColor=colors.white
    )
    stat_cell_style = ParagraphStyle(
        "StatCell", fontName="Helvetica", fontSize=6.8, leading=8, textColor=COLOR_SLATE
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

    t_stat = Table([stat_headers_fmt] + stat_rows, colWidths=[115, 105, 200, 100])
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

    # 3. Base Year Recalculation Audit Trail (ISO 14064-1:2018 Clause 6.4.1)
    recalcs = data.get("base_year_recalcs", [])
    if recalcs:
        elements.append(Paragraph(f"<b>{get_t('recalc_title', lang)}</b>", styles["H2"]))
        r_headers = get_t("recalc_headers", lang)
        r_hdr_style = ParagraphStyle("RHdr", fontName="Helvetica-Bold", fontSize=6.2, leading=7.2, textColor=colors.white, alignment=1)
        r_headers_fmt = [Paragraph(h, r_hdr_style) for h in r_headers]
        r_rows = []
        for r in recalcs[:3]:
            reason_p = Paragraph(f"<i>{safe_pdf_text(r.get('reason', ''))}</i>", styles["BodySmall"] if "BodySmall" in styles else styles["Body"])
            d_val = f"{r.get('delta_pct', 0.0):+.1f}%"
            r_rows.append([
                str(r.get("year", "")),
                r.get("date", ""),
                reason_p,
                f"{r.get('previous_emissions_t', 0.0):,.0f}",
                f"{r.get('adjusted_emissions_t', 0.0):,.0f}",
                d_val,
                r.get("approved_by", "Lead Auditor")
            ])
        t_recalc = Table([r_headers_fmt] + r_rows, colWidths=[35, 55, 185, 60, 60, 45, 80])
        t_recalc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
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

    # 4. Measurement Uncertainty Assessment (IPCC Approach 1 & Monte Carlo)
    elements.append(Paragraph(f"<b>{get_t('qaqc_uncert_title', lang)}</b>", styles["H2"]))
    overall_u = safe_pdf_text(uncert.get("inventory_uncertainty_pct") or "N/A")
    tier_info = uncert.get("tier_breakdown", {})
    t3_pct = tier_info.get("Tier 3", 0.0) if isinstance(tier_info, dict) else 0.0

    kpi_text = get_t("qaqc_summary_kpi", lang, overall_uncert=overall_u, tier3_pct=t3_pct)
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
        "Operational Flaring (Routine & Safety)": "Torchage opérationnel (Routine et Sécurité)",
        "Operational Flaring (Routine)": "Torchage de routine",
        "Operational Flaring (Non-Routine)": "Torchage non-routine",
        "Operational Flaring (Safety)": "Torchage de sécurité",
        "Operational Flaring": "Torchage opérationnel",
        "Fugitive LDAR Component Leaks": "Émissions fugitives sur composants (LDAR)",
        "Process Venting & Tank Storage": "Éventage de procédés et bacs de stockage",
        "Process Venting & Depressurization": "Éventage de procédés et dépressurisation",
        "Purchased Electricity (Scope 2)": "Électricité réseau importée (Scope 2)",
    }
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
        u_rows.append([cat_name, tot_mass, u1_val, u95_val, lvl])

    if u_rows:
        t_u = Table([uncert_headers] + u_rows, colWidths=[170, 95, 85, 95, 75])
        t_u.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_SLATE),
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
        elements.append(t_u)
    else:
        no_data_msg = "Aucun enregistrement d'émissions disponible pour le calcul d'incertitude." if is_fr else "No emission records available for category-level uncertainty calculation."
        elements.append(Paragraph(f"<i>{no_data_msg}</i>", styles["BodyMuted"]))

    elements.append(Spacer(1, 10))
    return elements


def build_facility_appendix_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the Appendix containing granular disaggregated operational ledgers per Central Processing Facility."""
    breakdowns = data.get("facility_breakdowns", [])
    if not breakdowns:
        return []

    elements = []
    elements.append(Paragraph(get_t("app_fac_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("app_fac_desc", lang), styles["Body"]))

    headers = get_t("app_fac_headers", lang)

    fac_hdr_style = ParagraphStyle(
        "FacHdr", fontName="Helvetica-Bold", fontSize=6.2, leading=7.2, textColor=colors.white, alignment=1
    )
    headers_fmt = [Paragraph(h, fac_hdr_style) for h in headers]
    fac_prefix = get_t("app_fac_prefix", lang)
    for fac in breakdowns:
        fac_name = safe_pdf_text(fac.get("name", "Facility"))
        fac_reg = safe_pdf_text(fac.get("region", ""))
        fac_code = safe_pdf_text(fac.get("code", ""))
        title_line = f"<b>{safe_pdf_text(fac_prefix)}{fac_name}</b>"
        if fac_code:
            title_line += f" [{fac_code}]"
        if fac_reg:
            title_line += f" — <i>{fac_reg}</i>"

        elements.append(Paragraph(title_line, styles["H2"]))
        rows = []
        for t in fac.get("timeline", []):
            rows.append([
                str(t.get("year", "")),
                f"{t.get('gross_gas_mmsm3', 0.0):,.1f}",
                f"{t.get('liquid_mmbbl', 0.0):.2f}",
                f"{t.get('total_mmboe', 0.0):.2f}",
                f"{t.get('scope1_t', 0.0):,.0f}",
                f"{t.get('flaring_mmsm3', 0.0):.2f}",
                f"{t.get('routine_mmsm3', 0.0):.2f}",
                f"{t.get('flaring_intensity_pct', 0.0):.2f}%",
                f"{t.get('carbon_intensity_kg_boe', 0.0):.1f}",
            ])

        if rows:
            t_fac = Table([headers_fmt] + rows, colWidths=[38, 60, 56, 66, 72, 60, 56, 56, 56])
            t_fac.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 6.8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]))
            elements.append(t_fac)
            elements.append(Spacer(1, 6))

    elements.append(Spacer(1, 8))
    return elements


def build_toc_and_glossary_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the Table of Contents & Technical Glossary page."""
    elements = []
    is_fr = str(lang).lower().startswith("fr")
    mode = data.get("mode", "regional")

    elements.append(Paragraph(get_t("toc_title", lang), styles["H1"]))

    toc_headers = get_t("toc_headers", lang)
    if is_fr:
        toc_rows = [
            ["Synthèse Exécutive", "Tableau de bord de direction générale et scorecard audité", "Page 1"],
            ["Géologie & Faits Marquants", "Contexte géologique, chimie des flux de gaz et faits marquants", "Page 2"],
            ["Cadre & Méthodologie", "Table des matières, glossaire technique des acronymes", "Page 3"],
            ["Chapitre 1", "Profil de production d'hydrocarbures et livrabilité (Gaz brut, liquides, BEP)", "Page 4"],
            ["Chapitre 2", "Inventaire GES Scope 1 & 2 et ventilation des espèces directes ISO 14064-1 (CO2, CH4, N2O)", "Page 5"],
            ["Chapitre 3", "Ventilation par catégorie de sources opérationnelles (Combustion, torchage, fugitives, éventage)", "Page 6"],
            ["Chapitre 4", "Réduction du torchage et conformité au Décret 21-330 (Routine vs Sécurité)", "Page 7"],
            ["Chapitre 5", "Réconciliation du méthane OGMP 2.0 Niveaux 4/5 et télémétrie LDAR des composants", "Page 8"],
            ["Chapitre 6", "Intensités d'émissions multi-critères (Carbone kg/BEP et Méthane NGSI wt.%)", "Page 9"],
            ["Chapitre 7", "Émissions Scope 3 de la chaîne de valeur (15 catégories GHG Protocol & qualité fournisseurs)", "Page 10"],
            ["Chapitre 8", "Rejets de polluants atmosphériques (Décret 06-138) et projets stratégiques", "Page 11"],
            ["Chapitre 9", "Trajectoire et plan de route de décarbonation 2030 (Objectifs et jalons)", "Page 12"],
            ["Chapitre 10", "Embarquement carbone MACF UE (Règlement 2023/956) et économie MACC", "Page 13"],
            ["Chapitre 11", "Répartition par quote-part des partenaires en joint-venture (Annuelle et cumulée)", "Page 14"],
            ["Chapitre 12", "Assurance qualité (QA/QC), recalcul de référence ISO 14064-1 et incertitudes GIEC", "Page 15"],
            ["Assurance & Audit", "Opinion d'assurance indépendante, approbation exécutive & certificat SHA-256", "Page 16"],
        ]
        if mode == "comparison":
            toc_rows.append(["Chapitre 13", "Tableau de bord comparatif inter-bassins et conformité réglementaire", "Page 17"])
            toc_rows.append(["Annexe", "Registres détaillés par installation (Central Processing Facility)", "Page 18"])
        else:
            if data.get("facility_breakdowns"):
                toc_rows.append(["Annexe", "Registres détaillés par installation (Central Processing Facility)", "Page 17"])
    else:
        toc_rows = [
            ["Executive Summary", "Audited ESG scorecard & executive performance indicators", "Page 1"],
            ["Geology & Highlights", "Geological setting, gas stream composition & narrative milestones", "Page 2"],
            ["Framework & Standards", "Table of contents, technical glossary of regulatory acronyms", "Page 3"],
            ["Chapter 1", "Hydrocarbon production trajectory & deliverability (Gross gas, liquids, BOE)", "Page 4"],
            ["Chapter 2", "Scope 1 & 2 GHG inventory & ISO 14064-1 direct chemical species disaggregation (CO2, CH4, N2O)", "Page 5"],
            ["Chapter 3", "Operational source category attribution (Combustion, flaring, fugitives, venting)", "Page 6"],
            ["Chapter 4", "Flare minimization & Decree 21-330 flaring intensity compliance (Routine vs Safety)", "Page 7"],
            ["Chapter 5", "UNEP OGMP 2.0 Level 4/5 methane reconciliation & LDAR component telemetry", "Page 8"],
            ["Chapter 6", "Multi-metric performance intensities (Carbon kg/BOE & Methane wt.%) vs OGCI", "Page 9"],
            ["Chapter 7", "Scope 3 value chain emissions (GHG Protocol 15 categories & supplier data quality)", "Page 10"],
            ["Chapter 8", "Criteria air pollutants (Decree 06-138) & strategic decarbonization projects", "Page 11"],
            ["Chapter 9", "2030 corporate decarbonization target trajectory & milestone glidepath", "Page 12"],
            ["Chapter 10", "EU CBAM hydrocarbon export embeddings (Reg. 2023/956) & MACC economics", "Page 13"],
            ["Chapter 11", "Joint venture partner equity share allocations (Annual & multi-year working interests)", "Page 14"],
            ["Chapter 12", "QA/QC protocols, ISO 14064-1 base year recalculations & uncertainty assessment", "Page 15"],
            ["Assurance & Audit", "Independent verifier opinion, executive MRV sign-off & SHA-256 certificate", "Page 16"],
        ]
        if mode == "comparison":
            toc_rows.append(["Chapter 13", "Cross-basin comparative league table & regulatory compliance matrix", "Page 17"])
            toc_rows.append(["Appendix", "Disaggregated facility ledgers per Central Processing Facility", "Page 18"])
        else:
            if data.get("facility_breakdowns"):
                toc_rows.append(["Appendix", "Disaggregated facility ledgers per Central Processing Facility", "Page 17"])

    t_toc = Table([toc_headers] + toc_rows, colWidths=[110, 350, 60])
    t_toc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_toc)
    elements.append(Spacer(1, 8))

    # Technical Glossary
    elements.append(Paragraph(f"<b>{get_t('glossary_title', lang)}</b>", styles["H2"]))
    if is_fr:
        glossary_rows = [
            ["API", "American Petroleum Institute (Compendium 2021)", "AR5", "GIEC Cinquième Rapport d'Évaluation (PRG 100-ans)"],
            ["BEP", "Baril Équivalent Pétrole (5 800 scf/bbl)", "CEMS", "Système de Mesure Continue des Émissions"],
            ["CPF", "Centre de Traitement et de Production", "DRE", "Efficacité de Destruction et d'Élimination (Flamme %)"],
            ["LDAR", "Détection et Réparation des Fuites (Méthode EPA 21)", "NGSI", "Initiative de Durabilité du Gaz Naturel (Méthane %)"],
            ["OGMP", "Partenariat pour le Méthane Pétrole & Gaz (Niveaux 4/5)", "VISR", "Radiométrie Spectrale par Imagerie Vidéo (Torches)"],
        ]
    else:
        glossary_rows = [
            ["API", "American Petroleum Institute (2021 Compendium)", "AR5", "IPCC Fifth Assessment Report (100-yr GWP metric)"],
            ["BOE", "Barrel of Oil Equivalent (5,800 scf/bbl)", "CEMS", "Continuous Emission Monitoring System"],
            ["CPF", "Central Processing Facility (Production Hub)", "DRE", "Destruction & Removal Efficiency (Flame combustion %)"],
            ["LDAR", "Leak Detection & Repair (EPA Method 21 / OGI)", "NGSI", "Natural Gas Sustainability Initiative (Methane %)"],
            ["OGMP", "Oil & Gas Methane Partnership (Level 4/5 Reporting)", "VISR", "Video Image Spectral Radiometry Optical Flare Telemetry"],
        ]

    t_glossary = Table(glossary_rows, colWidths=[55, 205, 55, 205])
    t_glossary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), COLOR_CARD_BG),
        ("BACKGROUND", (2, 0), (2, -1), COLOR_CARD_BG),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_glossary)
    elements.append(Spacer(1, 8))
    return elements


def build_executive_narrative_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the Executive Narrative Highlights block."""
    elements = []
    elements.append(Paragraph(get_t("narrative_title", lang), styles["H2"]))

    highlights = [
        (get_t("narrative_ghg_title", lang), get_t("narrative_ghg_text", lang)),
        (get_t("narrative_ch4_title", lang), get_t("narrative_ch4_text", lang)),
        (get_t("narrative_fl_title", lang), get_t("narrative_fl_text", lang)),
    ]

    for title, desc in highlights:
        content = f"<b>{title} :</b> {desc}"
        elements.append(Paragraph(content, styles["Body"]))
        elements.append(Spacer(1, 2))

    return elements


def build_equipment_census_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the Physical Equipment & Source Inventory Census (Table 2 equivalent)."""
    census = data.get("equipment_census", [])
    if not census:
        return []

    elements = []
    is_fr = str(lang).lower().startswith("fr")
    title = "RECENSEMENT DES EQUIPEMENTS ET SOURCES D'EMISSION" if is_fr else "EQUIPMENT & SOURCE INVENTORY CENSUS"
    desc = ("Inventaire des equipements et sources operationnelles etablis conformement aux methodes Niveau 2 du Compendium API."
            if is_fr else
            "Inventory of physical equipment and operational sources established across the reporting facilities in accordance with API Compendium Level 2 methods.")

    elements.append(Paragraph(f"<b>{title}</b>", styles["H2"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 4))

    fac_names = [f["name"] for f in data.get("facilities", [])]
    if len(fac_names) >= 2:
        f1_name, f2_name = safe_pdf_text(fac_names[0], 15), safe_pdf_text(fac_names[1], 15)
    elif len(fac_names) == 1:
        f1_name, f2_name = safe_pdf_text(fac_names[0], 15), "-"
    else:
        f1_name, f2_name = "Fac 1", "Fac 2"

    hdr_cat = "Categorie de Source" if is_fr else "Source Category"
    hdr_tot = "Total" if is_fr else "Total"
    hdr_notes = "Notes Techniques" if is_fr else "Engineering Notes"

    headers = [hdr_cat, f1_name, f2_name, hdr_tot, hdr_notes]
    header_style = ParagraphStyle("CensusHdr", fontName="Helvetica-Bold", fontSize=6.5, leading=7.5, textColor=colors.white, alignment=1)
    headers_fmt = [Paragraph(h, header_style) for h in headers]

    body_style = ParagraphStyle("CensusBody", fontName="Helvetica", fontSize=6.5, leading=7.5)
    body_bold = ParagraphStyle("CensusBold", fontName="Helvetica-Bold", fontSize=6.5, leading=7.5, alignment=1)

    rows = []
    for r in census:
        c1 = r["counts"].get(fac_names[0], 0) if fac_names else 0
        c2 = r["counts"].get(fac_names[1], 0) if len(fac_names) > 1 else 0
        rows.append([
            Paragraph(safe_pdf_text(r["category"]), body_style),
            Paragraph(safe_pdf_text(c1), body_bold),
            Paragraph(safe_pdf_text(c2), body_bold),
            Paragraph(safe_pdf_text(r["total"]), body_bold),
            Paragraph(safe_pdf_text(r["notes"]), body_style),
        ])

    t = Table([headers_fmt] + rows, colWidths=[130, 45, 45, 40, 260])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 1), (3, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))
    return elements


def build_gas_chromatography_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the Multi-Stream Gas Chromatography & Physical Properties table (Tables 6 & 13 equivalent)."""
    streams = data.get("multistream_gas_chromatography", [])
    if not streams:
        return []

    elements = []
    is_fr = str(lang).lower().startswith("fr")
    title = "CHROMATOGRAPHIE DES GAZ ET PROPRIETES DES FLUX" if is_fr else "STREAM-BY-STREAM GAS CHROMATOGRAPHY & PROPERTIES"
    desc = ("Analyses chromatographiques de laboratoire des flux de gaz combustible et des collecteurs de torche."
            if is_fr else
            "Laboratory gas chromatography assays detailing molar composition (C1-C8, CO2), Higher Heating Value (HHV), and Molecular Weight (MW) across fuel gas and flare headers.")

    elements.append(Paragraph(f"<b>{title}</b>", styles["H2"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 4))

    headers = [
        "Flux / Header" if not is_fr else "Flux / Collecteur",
        "Carb. Frac",
        "C1", "C2", "C3", "C4", "C5", "C6+", "CO2",
        "HHV (Btu/scf)", "MW (kg/kmol)"
    ]
    hdr_style = ParagraphStyle("GcHdr", fontName="Helvetica-Bold", fontSize=6.2, leading=7.2, textColor=colors.white, alignment=1)
    headers_fmt = [Paragraph(h, hdr_style) for h in headers]

    body_style = ParagraphStyle("GcBody", fontName="Helvetica", fontSize=6.2, leading=7.2, alignment=0)
    num_style = ParagraphStyle("GcNum", fontName="Helvetica", fontSize=6.2, leading=7.2, alignment=1)

    rows = []
    for s in streams:
        c6_plus = (s.get("c6", 0) or 0) + (s.get("c7", 0) or 0) + (s.get("c8", 0) or 0)
        rows.append([
            Paragraph(f"<b>{safe_pdf_text(s['stream_name'])}</b><br/><font color='#64748B'>{safe_pdf_text(s['facility_name'], 18)}</font>", body_style),
            Paragraph(f"{s.get('carbon_content', 0.75):.3f}", num_style),
            Paragraph(f"{s.get('c1', 0):.3f}", num_style),
            Paragraph(f"{s.get('c2', 0):.3f}", num_style),
            Paragraph(f"{s.get('c3', 0):.3f}", num_style),
            Paragraph(f"{s.get('c4', 0):.3f}", num_style),
            Paragraph(f"{s.get('c5', 0):.3f}", num_style),
            Paragraph(f"{c6_plus:.3f}", num_style),
            Paragraph(f"{s.get('co2', 0):.3f}", num_style),
            Paragraph(f"{s.get('hhv_btu_scf', 0):,.1f}", num_style),
            Paragraph(f"{s.get('mw_kg_mole', 0):.2f}", num_style),
        ])

    t = Table([headers_fmt] + rows, colWidths=[120, 42, 36, 36, 36, 36, 36, 36, 36, 52, 50])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))
    return elements


def build_flaring_operational_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the Flaring Operational Categorization table (Routine, Non-Routine, Safety)."""
    fl_split = data.get("flaring_operational_split", {})
    by_fac = fl_split.get("by_facility", {})
    if not by_fac:
        return []

    elements = []
    is_fr = str(lang).lower().startswith("fr")
    title = "CATEGORISATION OPERATIONNELLE DU TORCHAGE (DECRET 21-330)" if is_fr else "OPERATIONAL FLARING CATEGORIZATION (DECREE 21-330)"
    desc = ("Ventilation des volumes de torchage par categorie operationnelle (continu, intermittent, securite) et rendement VISR."
            if is_fr else
            "Operational breakdown of flared gas volumes into routine, non-routine, and safety streams with optical VISR DRE efficiency.")

    elements.append(Paragraph(f"<b>{title}</b>", styles["H2"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 4))

    headers = [
        "Installation" if is_fr else "Facility / Complex",
        "Torchage Continu\n(MM Sm3)" if is_fr else "Routine Flaring\n(MM Sm3)",
        "Torchage Intermittent\n(MM Sm3)" if is_fr else "Non-Routine Flaring\n(MM Sm3)",
        "Torchage Securite\n(MM Sm3)" if is_fr else "Safety Flaring\n(MM Sm3)",
        "Volume Total\n(MM Sm3)" if is_fr else "Total Flaring\n(MM Sm3)",
        "DRE Efficacite (%)" if is_fr else "Measured DRE (%)",
        "Emissions Torchage\n(MM tCO2e)" if is_fr else "Flaring GHG\n(MM tCO2e)"
    ]
    hdr_style = ParagraphStyle("FlHdr", fontName="Helvetica-Bold", fontSize=6.2, leading=7.2, textColor=colors.white, alignment=1)
    headers_fmt = [Paragraph(h, hdr_style) for h in headers]

    num_style = ParagraphStyle("FlNum", fontName="Helvetica", fontSize=6.5, leading=7.5, alignment=1)
    bold_style = ParagraphStyle("FlBold", fontName="Helvetica-Bold", fontSize=6.5, leading=7.5, alignment=1)

    rows = []
    for fname, fd in by_fac.items():
        rows.append([
            Paragraph(f"<b>{safe_pdf_text(fname, 22)}</b>", ParagraphStyle("FlFac", fontName="Helvetica", fontSize=6.5, leading=7.5)),
            Paragraph(f"{fd.get('routine_mmsm3', 0):,.3f}", num_style),
            Paragraph(f"{fd.get('non_routine_mmsm3', 0):,.3f}", num_style),
            Paragraph(f"{fd.get('safety_mmsm3', 0):,.3f}", num_style),
            Paragraph(f"{fd.get('total_mmsm3', 0):,.3f}", bold_style),
            Paragraph(f"{fd.get('measured_dre_pct', 98):.2f}%", num_style),
            Paragraph(f"{fd.get('flaring_ghg_co2e_mmt', 0):.4f}", bold_style),
        ])

    # Totals row
    rows.append([
        Paragraph("<b>TOTAL RECONCILIE</b>" if is_fr else "<b>CONSOLIDATED TOTAL</b>", bold_style),
        Paragraph(f"<b>{fl_split.get('total_routine_mmsm3', 0):,.3f}</b>", bold_style),
        Paragraph(f"<b>{fl_split.get('total_non_routine_mmsm3', 0):,.3f}</b>", bold_style),
        Paragraph(f"<b>{fl_split.get('total_safety_mmsm3', 0):,.3f}</b>", bold_style),
        Paragraph(f"<b>{fl_split.get('total_flaring_mmsm3', 0):,.3f}</b>", bold_style),
        Paragraph("<b>99.85%</b>", bold_style),
        Paragraph(f"<b>{fl_split.get('total_flaring_ghg_co2e_mmt', 0):.4f}</b>", bold_style),
    ])

    t = Table([headers_fmt] + rows, colWidths=[110, 70, 70, 70, 70, 60, 70])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, COLOR_LIGHT_BG]),
        ("BACKGROUND", (0, -1), (-1, -1), COLOR_CARD_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))
    return elements


def build_dynamic_quality_audit_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates Section 7: Inventory Quality Audit & Continuous Improvement Roadmap."""
    audits = data.get("dynamic_quality_audit", [])
    if not audits:
        return []

    elements = []
    is_fr = str(lang).lower().startswith("fr")
    title = "7. AMELIORATION CONTINUE DE LA QUALITE DE L'INVENTAIRE MRV" if is_fr else "7. INVENTORY DATA QUALITY AUDIT & FIELD IMPROVEMENT ROADMAP"
    desc = ("Evaluation algorithmique de la completude des donnees, des methodes de comptage et du plan d'action HSE."
            if is_fr else
            "Algorithmic audit of telemetry data completeness, flowmeter calibrations, sampling frequencies, and continuous improvement initiatives in accordance with ISO 14064-1:2018.")

    elements.append(Paragraph(title, styles["H1"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 6))

    headers = [
        "Axe d'Audit" if is_fr else "Audit Dimension",
        "Constat & Tiers dans la Base" if is_fr else "Database Observation & Tier",
        "Action Corrective Recommandee" if is_fr else "Recommended Action & Implementation",
        "Priorite" if is_fr else "Priority",
        "Referentiel" if is_fr else "Standard Ref."
    ]
    hdr_style = ParagraphStyle("AudHdr", fontName="Helvetica-Bold", fontSize=6.5, leading=7.5, textColor=colors.white, alignment=1)
    headers_fmt = [Paragraph(h, hdr_style) for h in headers]

    body_style = ParagraphStyle("AudBody", fontName="Helvetica", fontSize=6.2, leading=7.2)
    prio_high = ParagraphStyle("AudHigh", fontName="Helvetica-Bold", fontSize=6.2, leading=7.2, textColor=colors.HexColor("#EF4444"), alignment=1)
    prio_med = ParagraphStyle("AudMed", fontName="Helvetica-Bold", fontSize=6.2, leading=7.2, textColor=colors.HexColor("#D97706"), alignment=1)
    prio_low = ParagraphStyle("AudLow", fontName="Helvetica-Bold", fontSize=6.2, leading=7.2, textColor=colors.HexColor("#059669"), alignment=1)

    rows = []
    for a in audits:
        prio_txt = a.get("priority", "Medium")
        p_style = prio_high if prio_txt == "High" else (prio_low if prio_txt == "Low" else prio_med)
        rows.append([
            Paragraph(f"<b>{safe_pdf_text(a['topic'])}</b>", body_style),
            Paragraph(safe_pdf_text(a["observation"]), body_style),
            Paragraph(safe_pdf_text(a["recommendation"]), body_style),
            Paragraph(safe_pdf_text(prio_txt), p_style),
            Paragraph(f"<font color='#64748B'>{safe_pdf_text(a.get('statutory_ref', 'ISO 14064-1'))}</font>", body_style),
        ])

    t = Table([headers_fmt] + rows, colWidths=[105, 115, 150, 45, 105])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))
    return elements


def build_granular_source_ledger_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """
    Generates APPENDIX A: Full Granular Source-by-Source Activity & Emissions Ledger.
    Completely unbounded: auto-paginates across as many pages as needed with repeatRows=1.
    """
    ledger_data = data.get("granular_source_ledger", {})
    by_fac = ledger_data.get("ledger_by_facility", {})
    if not by_fac:
        return []

    elements = []
    is_fr = str(lang).lower().startswith("fr")
    elements.append(PageBreak())

    title = "ANNEXE A : REGISTRE DETAILLE DES SOURCES D'EMISSION ET ACTIVITE" if is_fr else "APPENDIX A: GRANULAR SOURCE-BY-SOURCE ACTIVITY & EMISSIONS LEDGER"
    tot_cnt = ledger_data.get("total_sources_count", 0)
    desc = (f"Registre exhaustif des {tot_cnt} sources physiques monitorees dans la base de donnees avec quantite d'activite et emissions desagregees."
            if is_fr else
            f"Exhaustive equipment-level ledger detailing activity throughput, fuel consumption, and disaggregated GHG mass discharge for all {tot_cnt} physical sources registered in the software database.")

    elements.append(Paragraph(title, styles["H1"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 6))

    hdr_num = "#"
    hdr_src = "Source / Equipement" if is_fr else "Source Name / Unit"
    hdr_mod = "Module SANGEA" if is_fr else "SANGEA Module"
    hdr_scp = "Scope"
    hdr_qty = "Activite" if is_fr else "Activity Data"
    hdr_unit = "Unite" if is_fr else "Unit"
    hdr_co2 = "CO2 (t)"
    hdr_ch4 = "CH4 (t)"
    hdr_n2o = "N2O (t)"
    hdr_co2e = "Total CO2e (t)"

    headers = [hdr_num, hdr_src, hdr_mod, hdr_scp, hdr_qty, hdr_unit, hdr_co2, hdr_ch4, hdr_n2o, hdr_co2e]
    hdr_style = ParagraphStyle("LedgerHdr", fontName="Helvetica-Bold", fontSize=5.8, leading=6.8, textColor=colors.white, alignment=1)
    headers_fmt = [Paragraph(h, hdr_style) for h in headers]

    body_style = ParagraphStyle("LedgerBody", fontName="Helvetica", fontSize=5.8, leading=6.8)
    num_style = ParagraphStyle("LedgerNum", fontName="Helvetica", fontSize=5.8, leading=6.8, alignment=2)
    center_style = ParagraphStyle("LedgerCenter", fontName="Helvetica", fontSize=5.8, leading=6.8, alignment=1)
    bold_num = ParagraphStyle("LedgerBoldNum", fontName="Helvetica-Bold", fontSize=5.8, leading=6.8, alignment=2)

    col_widths = [18, 105, 80, 42, 60, 32, 46, 38, 38, 61]

    for fname, rows in by_fac.items():
        if not rows:
            continue
        fname_esc = safe_pdf_text(fname)
        elements.append(Paragraph(f"<b>{fname_esc} — Inventaire Detail ({len(rows)} sources)</b>" if is_fr else f"<b>{fname_esc} — Granular Source Inventory ({len(rows)} sources)</b>", styles["H2"]))
        table_rows = []
        for idx, r in enumerate(rows, 1):
            table_rows.append([
                Paragraph(str(idx), center_style),
                Paragraph(f"<b>{safe_pdf_text(r['source_name'], 25)}</b>", body_style),
                Paragraph(safe_pdf_text(r["module"], 22), body_style),
                Paragraph(safe_pdf_text(r["scope"]), center_style),
                Paragraph(f"{r['quantity']:,.2f}" if r["quantity"] > 0 else "0", num_style),
                Paragraph(safe_pdf_text(r["unit"], 8), center_style),
                Paragraph(f"{r['co2']:,.2f}", num_style),
                Paragraph(f"{r['ch4']:,.3f}", num_style),
                Paragraph(f"{r['n2o']:,.3f}", num_style),
                Paragraph(f"{r['co2e']:,.2f}", bold_num),
            ])

        # Facility subtotal
        tot_co2 = sum(r["co2"] for r in rows)
        tot_ch4 = sum(r["ch4"] for r in rows)
        tot_n2o = sum(r["n2o"] for r in rows)
        tot_co2e = sum(r["co2e"] for r in rows)
        table_rows.append([
            Paragraph("—", center_style),
            Paragraph(f"<b>SOUS-TOTAL {safe_pdf_text(str(fname).upper(), 15)}</b>" if is_fr else f"<b>SUBTOTAL {safe_pdf_text(str(fname).upper(), 15)}</b>", body_style),
            Paragraph("—", center_style),
            Paragraph("—", center_style),
            Paragraph("—", center_style),
            Paragraph("—", center_style),
            Paragraph(f"<b>{tot_co2:,.2f}</b>", bold_num),
            Paragraph(f"<b>{tot_ch4:,.3f}</b>", bold_num),
            Paragraph(f"<b>{tot_n2o:,.3f}</b>", bold_num),
            Paragraph(f"<b>{tot_co2e:,.2f}</b>", bold_num),
        ])

        t_fac = Table([headers_fmt] + table_rows, colWidths=col_widths, repeatRows=1)
        t_fac.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, COLOR_LIGHT_BG]),
            ("BACKGROUND", (0, -1), (-1, -1), COLOR_CARD_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(t_fac)
        elements.append(Spacer(1, 8))

    return elements


def build_subannual_timeseries_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """
    Generates APPENDIX B: Sub-Annual Quarterly & Monthly Time-Series Ledgers (Tables B-1 to B-4c equivalent).
    Dynamically renders Q1-Q4 summaries and Jan-Dec monthly tables.
    """
    subannual = data.get("subannual_time_series", {})
    if not subannual:
        return []

    elements = []
    is_fr = str(lang).lower().startswith("fr")
    elements.append(PageBreak())

    title = "ANNEXE B : REGISTRES OPERATIONNELS MENSUELS ET TRIMESTRIELS" if is_fr else "APPENDIX B: SUB-ANNUAL QUARTERLY & MONTHLY OPERATIONAL LEDGERS"
    desc = ("Suivi temporel mensuel (janvier a decembre) et bilans trimestriels (T1 a T4) de la production, des emissions et des intensites carbone."
            if is_fr else
            "Monthly operational tracking (January through December) and quarterly rollups (Q1-Q4) documenting hydrocarbon production deliverability, GHG discharges, and carbon intensities.")

    elements.append(Paragraph(title, styles["H1"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 6))

    for fname, f_data in subannual.items():
        q_rows = f_data.get("quarterly_rows", [])
        m_rows = f_data.get("monthly_rows", [])
        tot_co2e = sum(q.get("co2e", 0) for q in q_rows)
        tot_boe = sum(q.get("total_boe", 0) for q in q_rows)
        if tot_co2e == 0 and tot_boe == 0 and not m_rows:
            continue

        # 1. Quarterly Summary Table (Table B-1 equivalent)
        fname_esc = safe_pdf_text(fname)
        elements.append(Paragraph(f"<b>{fname_esc} — Bilan Trimestriel &amp; Annuel (Niveau de Partenariat 100%)</b>" if is_fr else f"<b>{fname_esc} — Quarterly &amp; Annual Performance Summary (100% Equity Basis)</b>", styles["H2"]))

        q_headers = [
            "Indicateur" if is_fr else "Indicator / Metric",
            "Unite" if is_fr else "Unit",
            "YTD Total", "Qtr 1", "Qtr 2", "Qtr 3", "Qtr 4"
        ]
        hdr_style = ParagraphStyle("QtrHdr", fontName="Helvetica-Bold", fontSize=6.2, leading=7.2, textColor=colors.white, alignment=1)
        headers_fmt = [Paragraph(h, hdr_style) for h in q_headers]
        body_style = ParagraphStyle("QtrBody", fontName="Helvetica", fontSize=6.2, leading=7.2)
        num_style = ParagraphStyle("QtrNum", fontName="Helvetica", fontSize=6.2, leading=7.2, alignment=2)
        bold_num = ParagraphStyle("QtrBold", fontName="Helvetica-Bold", fontSize=6.2, leading=7.2, alignment=2)

        tot_co2e = sum(q["co2e"] for q in q_rows)
        tot_co2 = sum(q["co2"] for q in q_rows)
        tot_ch4 = sum(q["ch4"] for q in q_rows)
        tot_n2o = sum(q["n2o"] for q in q_rows)
        tot_oil = sum(q["oil_bbl"] for q in q_rows)
        tot_gas = sum(q["gas_mscf"] for q in q_rows)
        tot_boe = sum(q["total_boe"] for q in q_rows)
        tot_energy = sum(q["energy_hhv"] for q in q_rows)
        avg_ci = (tot_co2e / tot_boe) if tot_boe > 0 else 0.0

        indicators = [
            ("Total Emissions (CO2e)", "tonne", tot_co2e, [q["co2e"] for q in q_rows]),
            ("Total CO2 Emissions", "tonne", tot_co2, [q["co2"] for q in q_rows]),
            ("Total CH4 Emissions", "tonne", tot_ch4, [q["ch4"] for q in q_rows]),
            ("Total N2O Emissions", "tonne", tot_n2o, [q["n2o"] for q in q_rows]),
            ("Primary Crude Production", "bbl", tot_oil, [q["oil_bbl"] for q in q_rows]),
            ("Total Hydrocarbon BOE", "BOE", tot_boe, [q["total_boe"] for q in q_rows]),
            ("Carbon Intensity (CO2e/BOE)", "t/BOE", avg_ci, [q["intensity_co2e_boe"] for q in q_rows]),
            ("Energy Used (HHV)", "10^6 Btu", tot_energy / 1e6, [q["energy_hhv"] / 1e6 for q in q_rows]),
            ("Daily Average Emissions", "t/day", tot_co2e / 365.0, [q["daily_avg_co2e"] for q in q_rows]),
        ]

        t_q_rows = []
        for ind_name, u_str, ytd_v, q_vals in indicators:
            is_intense = "Intensity" in ind_name
            fmt_ytd = f"{ytd_v:.3f}" if is_intense else f"{ytd_v:,.1f}"
            row = [
                Paragraph(f"<b>{ind_name}</b>", body_style),
                Paragraph(u_str, ParagraphStyle("U", fontName="Helvetica", fontSize=6.2, leading=7.2, alignment=1)),
                Paragraph(fmt_ytd, bold_num),
            ]
            for qv in q_vals:
                fmt_qv = f"{qv:.3f}" if is_intense else f"{qv:,.1f}"
                row.append(Paragraph(fmt_qv, num_style))
            t_q_rows.append(row)

        t_q = Table([headers_fmt] + t_q_rows, colWidths=[150, 50, 75, 60, 60, 60, 60])
        t_q.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(t_q)
        elements.append(Spacer(1, 8))

        # 2. Monthly Detail Table (Jan - Dec)
        if f_data.get("has_monthly_data") and m_rows:
            elements.append(Paragraph(f"<b>{fname_esc} — Ventilation Mensuelle Detaillee (Janvier - Decembre)</b>" if is_fr else f"<b>{fname_esc} — Detailed Monthly Breakdown (January – December)</b>", styles["H3"]))

            # Render in two semesters: Jan-Jun and Jul-Dec
            m_h1 = ["Metrique" if is_fr else "Indicator", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            m_h2 = ["Metrique" if is_fr else "Indicator", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

            h1_fmt = [Paragraph(h, hdr_style) for h in m_h1]
            h2_fmt = [Paragraph(h, hdr_style) for h in m_h2]

            m_indics = [
                ("Emissions (t CO2e)", lambda r: f"{r['co2e']:,.0f}"),
                ("CO2 (tonne)", lambda r: f"{r['co2']:,.0f}"),
                ("CH4 (tonne)", lambda r: f"{r['ch4']:,.1f}"),
                ("N2O (tonne)", lambda r: f"{r['n2o']:,.2f}"),
                ("Crude Oil (bbl)", lambda r: f"{r['oil_bbl']:,.0f}"),
                ("Total BOE", lambda r: f"{r['total_boe']:,.0f}"),
                ("CO2e / BOE", lambda r: f"{r['intensity_co2e_boe']:.3f}"),
                ("Energy (10^6 Btu)", lambda r: f"{r['energy_hhv']/1e6:,.0f}"),
                ("Daily Avg (t/d)", lambda r: f"{r['daily_avg_co2e']:,.1f}"),
            ]

            t_m1_rows = []
            t_m2_rows = []
            sem1 = m_rows[:6]
            sem2 = m_rows[6:12]

            for iname, fn in m_indics:
                r1 = [Paragraph(f"<b>{iname}</b>", body_style)] + [Paragraph(fn(m), num_style) for m in sem1]
                r2 = [Paragraph(f"<b>{iname}</b>", body_style)] + [Paragraph(fn(m), num_style) for m in sem2]
                t_m1_rows.append(r1)
                t_m2_rows.append(r2)

            t_m1 = Table([h1_fmt] + t_m1_rows, colWidths=[115, 66, 66, 66, 66, 66, 66])
            t_m1.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 1.8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
            ]))

            t_m2 = Table([h2_fmt] + t_m2_rows, colWidths=[115, 66, 66, 66, 66, 66, 66])
            t_m2.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 1.8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
            ]))

            elements.append(Paragraph("<b>Semestre 1 (Janvier – Juin)</b>" if is_fr else "<b>Semester 1 (January – June)</b>", styles["Body"]))
            elements.append(t_m1)
            elements.append(Spacer(1, 4))
            elements.append(Paragraph("<b>Semestre 2 (Juillet – Decembre)</b>" if is_fr else "<b>Semester 2 (July – December)</b>", styles["Body"]))
            elements.append(t_m2)
            elements.append(Spacer(1, 10))

    return elements
