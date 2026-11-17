"""
Master Report Appendices & Uncertainty Module
=============================================
Provides publication-grade elements for:
1. QA/QC Verification Protocols, Statutory Mandates Matrix & IPCC Approach 1 / Monte Carlo Uncertainty Assessment
   (master_report_appendices_qaqc).
2. Disaggregated Facility-Level Operational Ledgers (CPF Breakdown), table of contents, glossary and narrative.
3. Equipment census, gas chromatography, flaring operations, quality audit, Appendix A and B
   (master_report_appendices_operations).
The fonts, palette and activity checks the split modules share stay here.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer

from services.master_report_i18n import get_t
from services.pdf_escape import safe_pdf_text

COLOR_DARK = colors.HexColor("#0F172A")
COLOR_SLATE = colors.HexColor("#1E293B")
COLOR_MUTED = colors.HexColor("#64748B")
COLOR_BORDER = colors.HexColor("#CBD5E1")
COLOR_LIGHT_BG = colors.HexColor("#F8FAFC")
COLOR_CARD_BG = colors.HexColor("#F1F5F9")
COLOR_SUCCESS = colors.HexColor("#10B981")


def register_pdf_fonts() -> Tuple[str, str, bool]:
    """Register DejaVu Sans TrueType fonts (bundled with matplotlib) for Unicode glyphs & French accents."""
    try:
        if "GHGSans" not in pdfmetrics.getRegisteredFontNames():
            import matplotlib

            base = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
            reg_ttf = os.path.join(base, "DejaVuSans.ttf")
            bold_ttf = os.path.join(base, "DejaVuSans-Bold.ttf")
            obl_ttf = os.path.join(base, "DejaVuSans-Oblique.ttf")
            bobl_ttf = os.path.join(base, "DejaVuSans-BoldOblique.ttf")
            pdfmetrics.registerFont(TTFont("GHGSans", reg_ttf))
            pdfmetrics.registerFont(TTFont("GHGSans-Bold", bold_ttf))
            has_obl = os.path.exists(obl_ttf)
            has_bobl = os.path.exists(bobl_ttf)
            if has_obl:
                pdfmetrics.registerFont(TTFont("GHGSans-Italic", obl_ttf))
            if has_bobl:
                pdfmetrics.registerFont(TTFont("GHGSans-BoldItalic", bobl_ttf))
            pdfmetrics.registerFontFamily(
                "GHGSans",
                normal="GHGSans",
                bold="GHGSans-Bold",
                italic="GHGSans-Italic" if has_obl else "GHGSans",
                boldItalic="GHGSans-BoldItalic" if has_bobl else "GHGSans-Bold",
            )
        return "GHGSans", "GHGSans-Bold", True
    except Exception as exc:
        logger.warning("TrueType font registration failed (%s); falling back to Helvetica.", exc, exc_info=True)
        return "Helvetica", "Helvetica-Bold", False


def _facility_breakdown_has_activity(fac: dict[str, Any]) -> bool:
    timeline = fac.get("timeline") or []
    return any(
        (t.get("gross_gas_mmsm3") or 0) != 0
        or (t.get("liquid_mmbbl") or 0) != 0
        or (t.get("total_mmboe") or 0) != 0
        or (t.get("scope1_t") or 0) != 0
        or (t.get("scope2_t") or 0) != 0
        or (t.get("total_ghg_t") or 0) != 0
        or (t.get("flaring_mmsm3") or 0) != 0
        or (t.get("routine_mmsm3") or 0) != 0
        for t in timeline
    )


def build_facility_appendix_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the Appendix containing granular disaggregated operational ledgers per Central Processing Facility."""
    breakdowns = [
        fac for fac in data.get("facility_breakdowns", []) if _facility_breakdown_has_activity(fac)
    ]
    if not breakdowns:
        return []

    elements = []
    elements.append(Paragraph(get_t("app_fac_title", lang), styles["H1"]))
    elements.append(Paragraph(get_t("app_fac_desc", lang), styles["Body"]))

    headers = get_t("app_fac_headers", lang)

    font_reg, font_bold, _ = register_pdf_fonts()
    fac_hdr_style = ParagraphStyle(
        "FacHdr", fontName=font_bold, fontSize=6.2, leading=7.2, textColor=colors.white, alignment=1
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
                ("FONTNAME", (0, 1), (-1, -1), font_reg),
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


def _glossary_elements(styles: Dict[str, ParagraphStyle], lang: str, is_fr: bool, font_reg: str, font_bold: str) -> List[Any]:
    """Technical glossary of the acronyms used in the report."""
    elements = []
    # Technical Glossary
    elements.append(Paragraph(f"<b>{get_t('glossary_title', lang)}</b>", styles["H2"]))
    if is_fr:
        glossary_rows = [
            ["API", "American Petroleum Institute (Compendium 2021)", "AR5", "GIEC Cinquième Rapport d'Évaluation (PRG 100 ans)"],
            ["BEP", "Baril Équivalent Pétrole (5 800 scf/bbl)", "CEMS", "Système de Mesure Continue des Émissions"],
            ["CPF", "Centre de Traitement et de Production", "DRE", "Efficacité de Destruction et d'Élimination (%)"],
            ["LDAR", "Détection et Réparation des Fuites (Composants)", "NGSI", "Initiative de Durabilité du Gaz Naturel (Méthane %)"],
            ["OGMP", "Partenariat pour le Méthane Pétrole & Gaz (Niveaux 4/5)", "VISR", "Radiométrie Spectrale par Imagerie Vidéo (Torches)"],
        ]
    else:
        glossary_rows = [
            ["API", "American Petroleum Institute (2021 Compendium)", "AR5", "IPCC Fifth Assessment Report (100-yr GWP metric)"],
            ["BOE", "Barrel of Oil Equivalent (5,800 scf/bbl)", "CEMS", "Continuous Emission Monitoring System"],
            ["CPF", "Central Processing Facility (Production Hub)", "DRE", "Destruction & Removal Efficiency (Flame combustion %)"],
            ["LDAR", "Leak Detection & Repair (Component Monitoring)", "NGSI", "Natural Gas Sustainability Initiative (Methane %)"],
            ["OGMP", "Oil & Gas Methane Partnership (Level 4/5 Reporting)", "VISR", "Video Image Spectral Radiometry Optical Flare Telemetry"],
        ]

    t_glossary = Table(glossary_rows, colWidths=[55, 205, 55, 205])
    t_glossary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), COLOR_CARD_BG),
        ("BACKGROUND", (2, 0), (2, -1), COLOR_CARD_BG),
        ("FONTNAME", (0, 0), (-1, -1), font_reg),
        ("FONTNAME", (0, 0), (0, -1), font_bold),
        ("FONTNAME", (2, 0), (2, -1), font_bold),
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


def build_toc_and_glossary_elements(
    data: Dict[str, Any],
    styles: Dict[str, ParagraphStyle],
    lang: str = "en",
    toc_pages: Optional[Dict[str, int]] = None,
    section_flags: Optional[Dict[str, bool]] = None,
) -> List[Any]:
    """Generates the Table of Contents (with 2-pass exact page numbers) & Technical Glossary page."""
    elements = []
    is_fr = str(lang).lower().startswith("fr")
    mode = data.get("mode", "regional")
    font_reg, font_bold, _ = register_pdf_fonts()
    flags = section_flags or {}

    def _pg(key: str) -> str:
        if toc_pages and key in toc_pages:
            return f"Page {toc_pages[key]}"
        return "—"

    elements.append(Paragraph(get_t("toc_title", lang), styles["H1"]))

    has_pfd = bool(flags.get("pfd", False))
    has_jv = bool(flags.get("jv", data.get("jv_equity", {}).get("partners")))
    has_ch13 = bool(flags.get("ch13", data.get("dynamic_quality_audit")))
    has_app_a = bool(flags.get("app_a", data.get("granular_source_ledger", {}).get("ledger_by_facility")))
    has_app_b = bool(flags.get("app_b", any(_subannual_has_activity(v) for v in data.get("subannual_time_series", {}).values())))
    has_app_c = bool(flags.get("app_c", any(_facility_breakdown_has_activity(f) for f in data.get("facility_breakdowns", []))))

    toc_headers = get_t("toc_headers", lang)
    if is_fr:
        toc_rows = [
            ["Synthèse Exécutive", "Tableau de bord de direction générale et scorecard", _pg("cover")],
        ]
        if has_pfd:
            toc_rows.append(["Schémas de Principe CPF", "Architecture des procédés et réseau de collecte", _pg("pfd")])
        toc_rows.extend([
            ["Géologie & Gaz", "Contexte géologique et chromatographie des flux de gaz", _pg("geology")],
            ["Recensement & Faits Marquants", "Inventaire des équipements sources et synthèse exécutive", _pg("census_narrative")],
            ["Cadre & Glossaire", "Table des matières et glossaire technique des acronymes", _pg("toc")],
            ["Chapitre 1", "Profil de production d'hydrocarbures et livrabilité (Gaz brut, liquides, BEP)", _pg("ch1")],
            ["Chapitre 2", "Inventaire GES Scope 1 & 2 et espèces directes ISO 14064-1 (CO₂, CH₄, N₂O)", _pg("ch2")],
            ["Chapitre 3", "Ventilation par catégorie de sources opérationnelles (Combustion, torchage, fugitives)", _pg("ch3")],
            ["Chapitre 4", "Réduction du torchage et conformité au Décret 21-330 (Routine vs Sécurité)", _pg("ch4")],
            ["Chapitre 5", "Réconciliation du méthane OGMP 2.0 Niveaux 4/5 et télémétrie LDAR", _pg("ch5")],
            ["Chapitre 6", "Intensités d'émissions multi-critères (Carbone kg/BEP et Méthane NGSI)", _pg("ch6")],
            ["Chapitre 7", "Émissions Scope 3 de la chaîne de valeur (GHG Protocol)", _pg("ch7")],
            ["Chapitre 8", "Polluants atmosphériques (dépistage API / Décret 06-138) et projets de décarbonation", _pg("ch8")],
            ["Chapitre 9", "Trajectoire et plan de route de décarbonation 2030", _pg("ch9")],
            ["Chapitre 10", "Embarquement carbone MACF UE (Règlement 2023/956) et économie MACC", _pg("ch10")],
        ])
        if has_jv:
            toc_rows.append(["Chapitre 11", "Répartition par quote-part des partenaires en joint-venture", _pg("ch11")])
        toc_rows.append(["Chapitre 12", "Assurance qualité (QA/QC), recalcul ISO 14064-1 et incertitudes GIEC", _pg("ch12")])
        if has_ch13:
            toc_rows.append(["Chapitre 13", "Audit qualité des données d'inventaire et feuille de route", _pg("ch13")])
        toc_rows.append(["Assurance & Audit", "Certificat d'approbation MRV et empreinte d'intégrité SHA-256", _pg("signoff")])
        if mode == "comparison":
            toc_rows.append(["Comparatif Inter-Bassins", "Tableau de bord comparatif inter-bassins et conformité", _pg("benchmark")])
        if has_app_a:
            toc_rows.append(["Annexe A", "Registre détaillé des sources d'émission et d'activité", _pg("app_a")])
        if has_app_b:
            toc_rows.append(["Annexe B", "Registres opérationnels trimestriels et mensuels", _pg("app_b")])
        if has_app_c:
            toc_rows.append(["Annexe C", "Registres désagrégés par installation (CPF)", _pg("app_c")])
    else:
        toc_rows = [
            ["Executive Summary", "Executive KPI scorecard & period governance summary", _pg("cover")],
        ]
        if has_pfd:
            toc_rows.append(["CPF Process Topology", "Illustrative block flow architecture and gathering network", _pg("pfd")])
        toc_rows.extend([
            ["Geology & Gas Streams", "Operational boundary context & laboratory gas chromatography", _pg("geology")],
            ["Equipment & Highlights", "Physical source inventory census & data-driven executive summary", _pg("census_narrative")],
            ["Framework & Glossary", "Table of contents & technical glossary of regulatory acronyms", _pg("toc")],
            ["Chapter 1", "Hydrocarbon production trajectory & deliverability (Gross gas, liquids, BOE)", _pg("ch1")],
            ["Chapter 2", "Scope 1 & 2 GHG inventory & ISO 14064-1 chemical species (CO₂, CH₄, N₂O)", _pg("ch2")],
            ["Chapter 3", "Operational source category attribution (Combustion, flaring, fugitives, venting)", _pg("ch3")],
            ["Chapter 4", "Flare minimization & Decree 21-330 flaring intensity compliance", _pg("ch4")],
            ["Chapter 5", "UNEP OGMP 2.0 Level 4/5 methane reconciliation & LDAR component telemetry", _pg("ch5")],
            ["Chapter 6", "Multi-metric performance intensities (Carbon kg/BOE & Methane wt.%) vs OGCI", _pg("ch6")],
            ["Chapter 7", "Scope 3 value chain emissions (GHG Protocol Categories 1–15)", _pg("ch7")],
            ["Chapter 8", "Criteria air pollutants screening (Decree 06-138) & decarbonization projects", _pg("ch8")],
            ["Chapter 9", "2030 corporate decarbonization target trajectory & milestone glidepath", _pg("ch9")],
            ["Chapter 10", "EU CBAM hydrocarbon export embeddings (Reg. 2023/956) & MACC economics", _pg("ch10")],
        ])
        if has_jv:
            toc_rows.append(["Chapter 11", "Joint venture partner equity share allocations", _pg("ch11")])
        toc_rows.append(["Chapter 12", "QA/QC protocols, ISO 14064-1 base year recalculations & uncertainty assessment", _pg("ch12")])
        if has_ch13:
            toc_rows.append(["Chapter 13", "Dynamic inventory data quality audit & field improvement roadmap", _pg("ch13")])
        toc_rows.append(["Assurance & Audit", "MRV sign-off status & canonical dataset SHA-256 certificate", _pg("signoff")])
        if mode == "comparison":
            toc_rows.append(["Cross-Basin Benchmark", "Cross-basin comparative league table & regulatory compliance matrix", _pg("benchmark")])
        if has_app_a:
            toc_rows.append(["Appendix A", "Granular source-by-source activity & emissions ledger", _pg("app_a")])
        if has_app_b:
            toc_rows.append(["Appendix B", "Sub-annual quarterly & monthly operational ledgers", _pg("app_b")])
        if has_app_c:
            toc_rows.append(["Appendix C", "Disaggregated facility ledgers per Central Processing Facility", _pg("app_c")])

    t_toc = Table([toc_headers] + toc_rows, colWidths=[115, 345, 60])
    t_toc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTNAME", (0, 1), (-1, -1), font_reg),
        ("FONTSIZE", (0, 0), (-1, -1), 6.6),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
    ]))
    elements.append(t_toc)
    elements.append(Spacer(1, 8))

    elements.extend(_glossary_elements(styles, lang, is_fr, font_reg, font_bold))

    return elements


def build_executive_narrative_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates dynamic, data-driven Executive Narrative Highlights derived strictly from live metrics."""
    elements = []
    is_fr = str(lang).lower().startswith("fr")
    elements.append(Paragraph(get_t("narrative_title", lang), styles["H2"]))

    timeline = data.get("timeline", [])
    active_entries = [t for t in timeline if (t.get("total_co2e_t") or 0.0) > 0 or (t.get("gross_gas_mmsm3") or 0.0) > 0]
    latest = active_entries[-1] if active_entries else (timeline[-1] if timeline else {})
    first = active_entries[0] if active_entries else (timeline[0] if timeline else {})
    multi_period = len(active_entries) > 1 and latest.get("year") != first.get("year")

    tot_mmt = float(latest.get("total_mmt", (latest.get("total_co2e_t", 0.0) or 0.0) / 1e6) or 0.0)
    ci_val = float(latest.get("carbon_intensity_kg_boe", 0.0) or 0.0)
    yr_latest = latest.get("year", data.get("end_year", ""))
    yr_first = first.get("year", data.get("start_year", ""))
    decarb_cnt = len(data.get("decarbonization_projects") or [])

    if multi_period:
        f_co2e = float(first.get("total_co2e_t", 0.0) or 0.0)
        l_co2e = float(latest.get("total_co2e_t", 0.0) or 0.0)
        co2e_delta = ((l_co2e - f_co2e) / f_co2e * 100.0) if f_co2e > 0 else 0.0
        f_ci = float(first.get("carbon_intensity_kg_boe", 0.0) or 0.0)
        ci_delta = ((ci_val - f_ci) / f_ci * 100.0) if f_ci > 0 else 0.0
        if is_fr:
            ghg_txt = (
                f"Entre {yr_first} et {yr_latest}, les émissions totales vérifiées (Scope 1+2) ont évolué de "
                f"{co2e_delta:+.1f} % pour atteindre {tot_mmt:.3f} MMtCO2e, avec une intensité carbone de "
                f"{ci_val:.1f} kg CO2e/BEP ({ci_delta:+.1f} % sur la période). {decarb_cnt} projet(s) actif(s) "
                f"de décarbonation enregistré(s) en base."
            )
        else:
            ghg_txt = (
                f"Across {yr_first}–{yr_latest}, Verified Scope 1+2 emissions changed by {co2e_delta:+.1f}% to "
                f"{tot_mmt:.3f} MMtCO2e, with carbon intensity at {ci_val:.1f} kg CO2e/BOE ({ci_delta:+.1f}% over "
                f"the period). {decarb_cnt} database-registered mitigation project(s) apply to this scope."
            )
    else:
        if is_fr:
            ghg_txt = (
                f"Pour l'exercice unique {yr_latest}, l'inventaire vérifié (Scope 1+2) s'élève à {tot_mmt:.3f} MMtCO2e "
                f"pour une intensité carbone de {ci_val:.1f} kg CO2e/BEP (sans comparaison pluriannuelle sur un exercice isolé). "
                f"{decarb_cnt} projet(s) de décarbonation enregistré(s) en base pour ce périmètre."
            )
        else:
            ghg_txt = (
                f"For the single-year {yr_latest} baseline, Verified Scope 1+2 emissions stand at {tot_mmt:.3f} MMtCO2e "
                f"with carbon intensity of {ci_val:.1f} kg CO2e/BOE (no multi-year trend inferred for a single period). "
                f"{decarb_cnt} decarbonization project(s) logged in the database for this perimeter."
            )

    ogmp = data.get("ogmp") or {}
    survey_cnt = len(ogmp.get("surveys") or [])
    comp_cnt = int(ogmp.get("total_components_monitored") or 0)
    ch4_t = float(latest.get("ch4_mass_t", 0.0) or 0.0)
    mi_val = float(latest.get("methane_intensity_pct", 0.0) or 0.0)
    mi_basis = latest.get("methane_intensity_basis", "net_gas")
    _ngsi = latest.get("methane_intensity_ngsi_pct")
    ngsi_txt = (f"; NGSI {_ngsi:.3f} %" if _ngsi is not None else "")
    if is_fr:
        mi_basis_disp = {
            "marketed_net_gas": "gaz commercialisé net",
            "marketed_gas": "gaz commercialisé (OGCI / OGMP)",
            "net_gas": "gaz net",
            "gross_gas_fallback": "gaz brut (repli)",
            "no_gas_denominator": "aucun volume gaz",
            "no_gas_production": "aucune production de gaz",
        }.get(mi_basis, str(mi_basis))
        ldar_note = (
            f"{survey_cnt} campagne(s) OGMP 2.0 et {comp_cnt:,} composant(s) LDAR sont enregistrés en base."
            if (survey_cnt > 0 or comp_cnt > 0) else
            "Aucune campagne OGMP 2.0 (LiDAR/OGI/EPA Méthode 21) ni inventaire composant LDAR n'est enregistré en base pour ce périmètre."
        )
        ch4_txt = (
            f"Les rejets directs de méthane atteignent {ch4_t:,.1f} tCH4 (intensité méthane {mi_val:.3f} %, "
            f"base : {mi_basis_disp}{ngsi_txt}). {ldar_note}"
        )
    else:
        mi_basis_disp = {
            "marketed_net_gas": "marketed net gas",
            "marketed_gas": "marketed gas (OGCI / OGMP)",
            "net_gas": "net gas",
            "gross_gas_fallback": "gross gas (fallback)",
            "no_gas_denominator": "no gas volume",
            "no_gas_production": "no gas production",
        }.get(mi_basis, str(mi_basis))
        ldar_note = (
            f"{survey_cnt} OGMP 2.0 survey campaign(s) and {comp_cnt:,} LDAR component(s) are logged in database."
            if (survey_cnt > 0 or comp_cnt > 0) else
            "0 OGMP 2.0 top-down survey campaigns (LiDAR/OGI/Method 21) and 0 LDAR component records are logged in the database for this perimeter."
        )
        ch4_txt = (
            f"Verified direct methane mass stands at {ch4_t:,.1f} tCH4 (methane intensity {mi_val:.3f}%, "
            f"basis: {mi_basis_disp}{ngsi_txt}). {ldar_note}"
        )

    fl_vol = float(latest.get("flaring_mmsm3", 0.0) or 0.0)
    fi_pct = float(latest.get("flaring_intensity_pct", 0.0) or 0.0)
    dre_val = latest.get("measured_dre_pct")
    has_dre = bool(latest.get("has_measured_dre")) or (dre_val is not None)
    d21_ok = bool(latest.get("decree_21_330_compliant", fi_pct <= 1.0))
    if is_fr:
        dre_note = f"DRE mesuré en base : {float(dre_val):.2f} %" if (has_dre and dre_val is not None) else "télémétrie VISR non mesurée en base (facteur défaut EPA 98,0 % appliqué)"
        stat_word = "conforme au seuil Décret 21-330 : ≤ 1,00 %" if d21_ok else "au-dessus du seuil Décret 21-330 : > 1,00 %"
        fl_txt = f"Le volume torché totalise {fl_vol:.3f} MMSm³ soit une intensité de {fi_pct:.2f} % ({stat_word}) ; {dre_note}."
    else:
        dre_note = f"database-logged DRE = {float(dre_val):.2f}%" if (has_dre and dre_val is not None) else "no VISR flare telemetry logged (EPA 98.0% default DRE applied)"
        stat_word = "compliant with Decree 21-330: ≤ 1.00%" if d21_ok else "exceeds Decree 21-330 threshold: > 1.00%"
        fl_txt = f"Flared gas totals {fl_vol:.3f} MMSm³ representing {fi_pct:.2f}% flaring intensity ({stat_word}); {dre_note}."

    highlights = [
        (get_t("narrative_ghg_title", lang), ghg_txt),
        (get_t("narrative_ch4_title", lang), ch4_txt),
        (get_t("narrative_fl_title", lang), fl_txt),
    ]

    for title, desc in highlights:
        content = f"<b>{title} :</b> {desc}"
        elements.append(Paragraph(content, styles["Body"]))
        elements.append(Spacer(1, 2))

    return elements


def _subannual_has_activity(f_data: dict[str, Any]) -> bool:
    q_rows = f_data.get("quarterly_rows", [])
    m_rows = f_data.get("monthly_rows", [])
    tot_co2e = sum((q.get("co2e") or 0) for q in q_rows)
    tot_boe = sum((q.get("total_boe") or 0) for q in q_rows)
    has_nonzero_monthly = any(
        (m.get("co2e") or 0) != 0 or (m.get("total_boe") or 0) != 0
        for m in m_rows
    )
    return not (tot_co2e == 0 and tot_boe == 0 and not has_nonzero_monthly)


# Split modules (they import from this one, so they come last)
from services.master_report_appendices_operations import (  # noqa: F401,E402
    build_dynamic_quality_audit_elements,
    build_equipment_census_elements,
    build_flaring_operational_elements,
    build_gas_chromatography_elements,
    build_granular_source_ledger_elements,
    build_subannual_timeseries_elements,
)
from services.master_report_appendices_qaqc import build_qaqc_uncertainty_elements  # noqa: F401,E402
