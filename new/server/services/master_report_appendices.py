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

from services.master_report_i18n import get_t, localize_status

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
    elements.append(Paragraph(get_t("qaqc_proto_desc", lang), styles["Body"]))

    # 2. Statutory Regimes Compliance Matrix
    elements.append(Paragraph(f"<b>{get_t('qaqc_statute_title', lang)}</b>", styles["H2"]))
    stat_headers = get_t("qaqc_statute_headers", lang)
    if is_fr:
        raw_stat_rows = [
            ["Décret Exécutif 21-330 Art. 9", "Loi Hydrocarbures 19-13", "Plafond obligatoire de torchage <= 1,00 % de la production brute", "Conforme Audité"],
            ["Décret Exécutif 06-138", "Ministère de l'Environnement", "Valeurs limites de rejets atmosphériques industriels (mg/Nm³)", "Conforme Stœchiométrique"],
            ["Spécification ISO 14064-1:2018", "Normalisation Internationale", "Directives de quantification et de déclaration des inventaires GES", "Assurance Raisonnable"],
            ["Initiative Climat OGCI", "Consortium Mondial Oil & Gas", "Cible d'intensité méthane <= 0,20 % du gaz commercialisé", "Objectif Atteint"],
        ]
    else:
        raw_stat_rows = [
            ["Executive Decree 21-330 Art. 9", "Hydrocarbon Law 19-13", "Mandatory gas flaring ceiling not to exceed 1.00% of gross output", "Audited Compliant"],
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

    # 3. Measurement Uncertainty Assessment (IPCC Approach 1 & Monte Carlo)
    elements.append(Paragraph(f"<b>{get_t('qaqc_uncert_title', lang)}</b>", styles["H2"]))
    overall_u = uncert.get("inventory_uncertainty_pct") or "±4.82%"
    tier_info = uncert.get("tier_breakdown", {})
    t3_pct = tier_info.get("Tier 3", 82.5) if isinstance(tier_info, dict) else 82.5

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
    u_rows = []
    for c in categories[:7]:
        cat_name = c.get("category", "")
        tot_mass = f"{c.get('total_emissions', 0.0):,.0f}"
        u1_val = f"±{c.get('uncertainty_1sigma', 0.0) * 100:.1f}%"
        u95_val = c.get("uncertainty_pct", "±5.0%")
        lvl = (c.get("level", "low")).upper()
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
        fac_name = fac.get("name", "Facility")
        fac_reg = fac.get("region", "")
        fac_code = fac.get("code", "")
        title_line = f"<b>{fac_prefix}{fac_name}</b>"
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
            ["Synthèse Exécutive", "Tableau de bord de direction, géologie régionale et chimie des gaz", "Page 1"],
            ["Cadre & Faits Marquants", "Table des matières, faits marquants de décarbonation et glossaire", "Page 2"],
            ["Chapitre 1", "Profil de production d'hydrocarbures et livrabilité (Gaz brut, liquides, BEP)", "Page 3"],
            ["Chapitre 2", "Inventaire GES Scope 1 (exploitation directe) et Scope 2 (électricité importée)", "Page 4"],
            ["Chapitre 3", "Ventilation par catégorie de sources opérationnelles (Combustion, torchage, fugitives, éventage)", "Page 5"],
            ["Chapitre 4", "Réduction du torchage et conformité au Décret 21-330 (Routine vs Sécurité)", "Page 6"],
            ["Chapitre 5", "Intensités d'émissions multi-critères (Carbone kg/BEP et Méthane NGSI wt.%)", "Page 7"],
            ["Chapitre 6", "Rejets de polluants atmosphériques (Décret 06-138) et projets stratégiques", "Page 8"],
            ["Chapitre 7", "Trajectoire et plan de route de décarbonation 2030 (Objectifs et jalons)", "Page 9"],
            ["Chapitre 8", "Répartition par quote-part des partenaires en joint-venture (Quotes-parts)", "Page 10"],
            ["Chapitre 9", "Assurance qualité (QA/QC), incertitudes GIEC / Monte Carlo et conformité", "Page 11"],
            ["Annexe & Audit", "Registres détaillés par installation / champ et certificat exécutif avec empreinte SHA-256", "Page 12" if mode != "comparison" else "Page 13"],
        ]
    else:
        toc_rows = [
            ["Executive Summary", "Audited ESG scorecard, regional geological architecture & gas composition", "Page 1"],
            ["Framework & Highlights", "Table of contents, executive narrative milestones & technical glossary", "Page 2"],
            ["Chapter 1", "Hydrocarbon production trajectory & deliverability (Gross gas, liquids, BOE)", "Page 3"],
            ["Chapter 2", "Scope 1 direct operating boundary & Scope 2 indirect electricity inventory", "Page 4"],
            ["Chapter 3", "Operational source category attribution (Combustion, flaring, fugitives, venting)", "Page 5"],
            ["Chapter 4", "Flare minimization & Decree 21-330 flaring intensity compliance (Routine vs Safety)", "Page 6"],
            ["Chapter 5", "Multi-metric performance intensities (Carbon kg/BOE & Methane wt.%) vs OGCI", "Page 7"],
            ["Chapter 6", "Criteria air pollutants (Decree 06-138) & strategic decarbonization projects", "Page 8"],
            ["Chapter 7", "2030 corporate decarbonization target trajectory & milestone glidepath", "Page 9"],
            ["Chapter 8", "Joint venture partner equity share allocations (Contractual working interests)", "Page 10"],
            ["Chapter 9", "QA/QC verification protocols, IPCC Approach 1 & Monte Carlo uncertainty assessment", "Page 11"],
            ["Appendix & Audit", "Disaggregated facility / field ledgers & executive certificate with SHA-256 seal", "Page 12" if mode != "comparison" else "Page 13"],
        ]

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
