"""Master report: equipment census, gas chromatography, flaring operations, data quality audit, Appendix A
(source ledger) and Appendix B (sub-annual ledgers) elements (split from master_report_appendices.py)."""

from typing import Any, Dict, List, Optional
from services.master_report_appendices import (
    COLOR_BORDER,
    COLOR_CARD_BG,
    COLOR_DARK,
    COLOR_LIGHT_BG,
    _subannual_has_activity,
    register_pdf_fonts,
)
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from services.master_report_i18n import get_t
from services.pdf_escape import safe_pdf_text


def build_equipment_census_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the Physical Equipment & Source Inventory Census (Table 2 equivalent)."""
    census = data.get("equipment_census", [])
    if not census:
        return []

    elements = []
    is_fr = str(lang).lower().startswith("fr")
    font_reg, font_bold, _ = register_pdf_fonts()
    title = "RECENSEMENT DES ÉQUIPEMENTS ET SOURCES D'ÉMISSION" if is_fr else "EQUIPMENT & SOURCE INVENTORY CENSUS"
    desc = ("Inventaire des équipements et sources opérationnelles établis conformément aux méthodes Niveau 2 du Compendium API."
            if is_fr else
            "Inventory of physical equipment and operational sources established across the reporting facilities in accordance with API Compendium Level 2 methods.")

    elements.append(Paragraph(f"<b>{title}</b>", styles["H2"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 4))

    fac_names = [f["name"] for f in data.get("facilities", [])]
    hdr_cat = "Catégorie de Source" if is_fr else "Source Category"
    hdr_tot = "Total"
    hdr_notes = "Notes Techniques" if is_fr else "Engineering Notes"
    header_style = ParagraphStyle("CensusHdr", fontName=font_bold, fontSize=6.5, leading=7.5, textColor=colors.white, alignment=1)

    body_style = ParagraphStyle("CensusBody", fontName=font_reg, fontSize=6.5, leading=7.5)
    body_bold = ParagraphStyle("CensusBold", fontName=font_bold, fontSize=6.5, leading=7.5, alignment=1)

    FR_CENSUS_CAT = {
        "Combustion – Heaters": "Combustion – Fours & Réchauffeurs",
        "Combustion – Turbines / Generators": "Combustion – Turbines / Générateurs",
        "Combustion – Diesel fired engines": "Combustion – Moteurs Diesel",
        "Flares": "Torches",
        "Equipment Leaks – Gas production": "Fuites d'équipements – Production gaz",
        "Equipment Leaks – Oil production": "Fuites d'équipements – Production huile",
        "Equipment Leaks – CPF Gas processing": "Fuites d'équipements – Traitement gaz CPF",
        "Oil and Gas Venting Activities": "Activités d'éventage pétrole et gaz",
        "Mobile & Transportation – On-road vehicles": "Mobile & Transport – Véhicules routiers",
        "Mobile & Transportation – Aviation": "Mobile & Transport – Aviation",
        "Storage Tanks – Produced Water Tanks": "Bacs de stockage – Eaux de production",
        "Miscellaneous – Wastewater Treatment": "Divers – Traitement des eaux usées",
        "Miscellaneous – Fire Suppressant": "Divers – Agents d'extinction incendie",
        "Indirect – Purchased Electricity": "Indirect – Électricité réseau achetée",
    }
    FR_CENSUS_NOTES = {
        "Fuel gas combustion sources": "Sources de combustion au gaz combustible",
        "Fuel gas power generation & compression drivers": "Production électrique et entraînement compresseurs au gaz",
        "Emergency generators and utility diesel units": "Groupes électrogènes de secours et utilités diesel",
        "Smokeless high/low pressure flare networks": "Réseaux de torches HP/BP sans fumée",
        "No production leak sources logged in this sub-category": "Aucune source de fuite production enregistrée dans cette sous-catégorie",
        "Level 2 facility-level fugitive estimates (no component inventory logged)": "Estimations fugitives Niveau 2 au niveau installation (sans inventaire composants)",
        "Maintenance, blowdown and non-routine events": "Maintenance, dépressurisation et événements non-routine",
        "Fixed-wing/rotary logistics aircraft (if registered)": "Aéronefs logistiques à voilure fixe/tournante (si enregistrés)",
        "Separator / produced water atmospheric storage tanks": "Bacs atmosphériques de séparation / eaux de production",
        "Scope 2 grid import power supply": "Alimentation électrique réseau importée (Scope 2)",
        "Operational support systems": "Systèmes de support opérationnel",
    }

    def _loc_census_notes(raw_note: str) -> str:
        if not is_fr:
            return raw_note
        if raw_note in FR_CENSUS_NOTES:
            return FR_CENSUS_NOTES[raw_note]
        if raw_note.startswith("EPA Method 21 LDAR ("):
            return raw_note.replace("EPA Method 21 LDAR (", "LDAR EPA Méthode 21 (").replace("components logged", "composants enregistrés")
        if raw_note.startswith("Component-level LDAR inventory ("):
            return raw_note.replace("Component-level LDAR inventory (", "Inventaire LDAR par composants (").replace("components; no Method 21 surveys", "composants ; sans relevé Méthode 21")
        return raw_note

    fac_chunks: List[List[Optional[str]]] = (
        [fac_names[i : i + 4] for i in range(0, len(fac_names), 4)]
        if fac_names
        else [[None, None]]
    )
    multi_group = len(fac_chunks) > 1

    for chunk_idx, chunk in enumerate(fac_chunks, start=1):
        if chunk == [None, None]:
            fac_headers = ["Fac 1", "Fac 2"]
        else:
            fac_headers = [safe_pdf_text(fname, 15) for fname in chunk if fname is not None]

        n_fac = len(fac_headers)
        if multi_group:
            shown_names = ", ".join(safe_pdf_text(fn) for fn in chunk if fn is not None)
            grp_label = (
                f"<b>Groupe d'Installations {chunk_idx}/{len(fac_chunks)}</b> : {shown_names} "
                f"(la colonne Total reflète le périmètre complet de {len(fac_names)} installations)."
                if is_fr else
                f"<b>Facility Group {chunk_idx}/{len(fac_chunks)}</b>: {shown_names} "
                f"(Total column reflects full {len(fac_names)}-facility reporting scope)."
            )
            elements.append(Paragraph(grp_label, styles["BodyMuted"]))
            elements.append(Spacer(1, 2))

        headers_fmt = [Paragraph(h, header_style) for h in ([hdr_cat] + fac_headers + [hdr_tot, hdr_notes])]
        if n_fac == 1:
            cat_w, fac_w, tot_w, notes_w = 135, 75, 40, 270
        elif n_fac == 2:
            cat_w, fac_w, tot_w, notes_w = 125, 60, 38, 237
        elif n_fac == 3:
            cat_w, fac_w, tot_w, notes_w = 118, 54, 36, 204
        else:
            cat_w, fac_w, tot_w, notes_w = 110, 50, 36, 174
        col_widths = [cat_w] + ([fac_w] * n_fac) + [tot_w, notes_w]

        rows = []
        for r in census:
            if chunk == [None, None]:
                fac_cells = ["0", "0"]
            else:
                fac_cells = [
                    str(r["counts"].get(fn, 0))
                    for fn in chunk
                    if fn is not None
                ]
            cat_disp = FR_CENSUS_CAT.get(r["category"], r["category"]) if is_fr else r["category"]
            notes_disp = _loc_census_notes(r["notes"])
            rows.append(
                [Paragraph(safe_pdf_text(cat_disp), body_style)]
                + fac_cells
                + [str(r["total"]), Paragraph(safe_pdf_text(notes_disp), body_style)]
            )

        t = Table([headers_fmt] + rows, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (1, 1), (-2, -1), font_bold),
            ("FONTSIZE", (1, 1), (-2, -1), 6.5),
            ("ALIGN", (1, 1), (-2, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 8 if multi_group else 10))
    return elements


def build_gas_chromatography_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """Generates the Multi-Stream Gas Chromatography & Physical Properties table (Tables 6 & 13 equivalent)."""
    streams = data.get("multistream_gas_chromatography", [])
    if not streams:
        return []

    elements = []
    is_fr = str(lang).lower().startswith("fr")
    font_reg, font_bold, _ = register_pdf_fonts()
    title = "CHROMATOGRAPHIE DES GAZ ET PROPRIÉTÉS DES FLUX" if is_fr else "STREAM-BY-STREAM GAS CHROMATOGRAPHY & PROPERTIES"
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
    hdr_style = ParagraphStyle("GcHdr", fontName=font_bold, fontSize=6.2, leading=7.2, textColor=colors.white, alignment=1)
    headers_fmt = [Paragraph(h, hdr_style) for h in headers]

    body_style = ParagraphStyle("GcBody", fontName=font_reg, fontSize=6.2, leading=7.2, alignment=0)
    num_style = ParagraphStyle("GcNum", fontName=font_reg, fontSize=6.2, leading=7.2, alignment=1)

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
    font_reg, font_bold, _ = register_pdf_fonts()
    title = "CATÉGORISATION OPÉRATIONNELLE DU TORCHAGE (DÉCRET 21-330)" if is_fr else "OPERATIONAL FLARING CATEGORIZATION (DECREE 21-330)"
    desc = ("Ventilation des volumes de torchage par catégorie opérationnelle (continu, intermittent, sécurité) et rendement de destruction (DRE mesuré en base ou défaut EPA 98,0 %)."
            if is_fr else
            "Operational breakdown of flared gas volumes into routine, non-routine, and safety streams with database-measured DRE or EPA 98.0% engineering default.")

    elements.append(Paragraph(f"<b>{title}</b>", styles["H2"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 4))

    headers = [
        "Installation" if is_fr else "Facility / Complex",
        "Torchage Continu\n(MMSm³)" if is_fr else "Routine Flaring\n(MMSm³)",
        "Torchage Intermittent\n(MMSm³)" if is_fr else "Non-Routine Flaring\n(MMSm³)",
        "Torchage Sécurité\n(MMSm³)" if is_fr else "Safety Flaring\n(MMSm³)",
        "Volume Total\n(MMSm³)" if is_fr else "Total Flaring\n(MMSm³)",
        "DRE Efficacité (%)" if is_fr else "Flare DRE (%)",
        "Émissions Torchage\n(MM tCO₂e)" if is_fr else "Flaring GHG\n(MM tCO₂e)"
    ]
    hdr_style = ParagraphStyle("FlHdr", fontName=font_bold, fontSize=6.2, leading=7.2, textColor=colors.white, alignment=1)
    headers_fmt = [Paragraph(h, hdr_style) for h in headers]

    num_style = ParagraphStyle("FlNum", fontName=font_reg, fontSize=6.5, leading=7.5, alignment=1)
    bold_style = ParagraphStyle("FlBold", fontName=font_bold, fontSize=6.5, leading=7.5, alignment=1)
    fac_style = ParagraphStyle("FlFac", fontName=font_reg, fontSize=6.5, leading=7.5)
    default_dre_str = "Défaut 98,0 %" if is_fr else "Default 98.0%"

    rows = []
    measured_nums = []
    measured_vols = []
    for fname, fd in by_fac.items():
        fd_dre = fd.get("measured_dre_pct")
        fd_vol = float(fd.get("total_mmsm3", 0.0) or 0.0)
        if fd_dre is not None:
            measured_nums.append(float(fd_dre))
            measured_vols.append(max(fd_vol, 0.0))
        dre_cell = f"{float(fd_dre):.2f}%" if fd_dre is not None else default_dre_str
        rows.append([
            Paragraph(f"<b>{safe_pdf_text(fname, 22)}</b>", fac_style),
            Paragraph(f"{fd.get('routine_mmsm3', 0):,.3f}", num_style),
            Paragraph(f"{fd.get('non_routine_mmsm3', 0):,.3f}", num_style),
            Paragraph(f"{fd.get('safety_mmsm3', 0):,.3f}", num_style),
            Paragraph(f"{fd_vol:,.3f}", bold_style),
            Paragraph(dre_cell, num_style),
            Paragraph(f"{fd.get('flaring_ghg_co2e_mmt', 0):.4f}", bold_style),
        ])

    w_dre = fl_split.get("weighted_dre_pct")
    if w_dre is None and measured_nums:
        tot_v = sum(measured_vols)
        if tot_v > 0:
            w_dre = sum(d * v for d, v in zip(measured_nums, measured_vols)) / tot_v
        else:
            w_dre = sum(measured_nums) / len(measured_nums)
    tot_dre_str = f"<b>{float(w_dre):.2f}%</b>" if w_dre is not None else f"<b>{default_dre_str}</b>"

    # Totals row
    rows.append([
        Paragraph("<b>TOTAL RÉCONCILIÉ</b>" if is_fr else "<b>CONSOLIDATED TOTAL</b>", bold_style),
        Paragraph(f"<b>{fl_split.get('total_routine_mmsm3', 0):,.3f}</b>", bold_style),
        Paragraph(f"<b>{fl_split.get('total_non_routine_mmsm3', 0):,.3f}</b>", bold_style),
        Paragraph(f"<b>{fl_split.get('total_safety_mmsm3', 0):,.3f}</b>", bold_style),
        Paragraph(f"<b>{fl_split.get('total_flaring_mmsm3', 0):,.3f}</b>", bold_style),
        Paragraph(tot_dre_str, bold_style),
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
    font_reg, font_bold, _ = register_pdf_fonts()
    title = "13. AMÉLIORATION CONTINUE DE LA QUALITÉ DE L'INVENTAIRE MRV" if is_fr else "13. INVENTORY DATA QUALITY AUDIT & FIELD IMPROVEMENT ROADMAP"
    desc = ("Évaluation algorithmique de la complétude des données, des méthodes de comptage et du plan d'action HSE."
            if is_fr else
            "Algorithmic audit of telemetry data completeness, flowmeter calibrations, sampling frequencies, and continuous improvement initiatives in accordance with ISO 14064-1:2018.")

    elements.append(Paragraph(title, styles["H1"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 6))

    headers = [
        "Axe d'Audit" if is_fr else "Audit Dimension",
        "Constat & Tiers dans la Base" if is_fr else "Database Observation & Tier",
        "Action Corrective Recommandée" if is_fr else "Recommended Action & Implementation",
        "Priorité" if is_fr else "Priority",
        "Référentiel" if is_fr else "Standard Ref."
    ]
    hdr_style = ParagraphStyle("AudHdr", fontName=font_bold, fontSize=6.5, leading=7.5, textColor=colors.white, alignment=1)
    headers_fmt = [Paragraph(h, hdr_style) for h in headers]

    body_style = ParagraphStyle("AudBody", fontName=font_reg, fontSize=6.2, leading=7.2)
    prio_high = ParagraphStyle("AudHigh", fontName=font_bold, fontSize=6.2, leading=7.2, textColor=colors.HexColor("#EF4444"), alignment=1)
    prio_med = ParagraphStyle("AudMed", fontName=font_bold, fontSize=6.2, leading=7.2, textColor=colors.HexColor("#D97706"), alignment=1)
    prio_low = ParagraphStyle("AudLow", fontName=font_bold, fontSize=6.2, leading=7.2, textColor=colors.HexColor("#059669"), alignment=1)

    _PRIO_FR = {"High": "Élevée", "Medium": "Moyenne", "Low": "Faible"}
    rows = []
    for a in audits:
        prio_en = a.get("priority", "Medium")
        p_style = prio_high if prio_en == "High" else (prio_low if prio_en == "Low" else prio_med)
        topic_txt = a.get("topic_fr") if (is_fr and a.get("topic_fr")) else a["topic"]
        obs_txt = a.get("observation_fr") if (is_fr and a.get("observation_fr")) else a["observation"]
        rec_txt = a.get("recommendation_fr") if (is_fr and a.get("recommendation_fr")) else a["recommendation"]
        ref_txt = a.get("statutory_ref_fr") if (is_fr and a.get("statutory_ref_fr")) else a.get("statutory_ref", "ISO 14064-1")
        prio_disp = (a.get("priority_fr") or _PRIO_FR.get(prio_en, prio_en)) if is_fr else prio_en
        rows.append([
            Paragraph(f"<b>{safe_pdf_text(topic_txt)}</b>", body_style),
            Paragraph(safe_pdf_text(obs_txt), body_style),
            Paragraph(safe_pdf_text(rec_txt), body_style),
            Paragraph(safe_pdf_text(prio_disp), p_style),
            Paragraph(f"<font color='#64748B'>{safe_pdf_text(ref_txt)}</font>", body_style),
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
    font_reg, font_bold, _ = register_pdf_fonts()
    elements.append(PageBreak())

    title = "ANNEXE A : REGISTRE DÉTAILLÉ DES SOURCES D'ÉMISSION ET ACTIVITÉ" if is_fr else "APPENDIX A: GRANULAR SOURCE-BY-SOURCE ACTIVITY & EMISSIONS LEDGER"
    tot_cnt = ledger_data.get("total_sources_count", 0)
    desc = (f"Registre exhaustif des {tot_cnt} sources physiques suivies dans la base de données avec quantités d'activité et émissions désagrégées."
            if is_fr else
            f"Exhaustive equipment-level ledger detailing activity throughput, fuel consumption, and disaggregated GHG mass discharge for all {tot_cnt} physical sources registered in the software database.")

    elements.append(Paragraph(title, styles["H1"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 6))

    hdr_num = "#"
    hdr_src = "Source / Équipement" if is_fr else "Source Name / Unit"
    hdr_mod = "Module SANGEA" if is_fr else "SANGEA Module"
    hdr_scp = "Scope"
    hdr_qty = "Activité" if is_fr else "Activity Data"
    hdr_unit = "Unité" if is_fr else "Unit"
    hdr_co2 = "CO₂ (t)"
    hdr_ch4 = "CH₄ (t)"
    hdr_n2o = "N₂O (t)"
    hdr_co2e = "Total CO₂e (t)"

    headers = [hdr_num, hdr_src, hdr_mod, hdr_scp, hdr_qty, hdr_unit, hdr_co2, hdr_ch4, hdr_n2o, hdr_co2e]
    hdr_style = ParagraphStyle("LedgerHdr", fontName=font_bold, fontSize=5.8, leading=6.8, textColor=colors.white, alignment=1)
    headers_fmt = [Paragraph(h, hdr_style) for h in headers]

    body_style = ParagraphStyle("LedgerBody", fontName=font_reg, fontSize=5.8, leading=6.8)
    center_style = ParagraphStyle("LedgerCenter", fontName=font_reg, fontSize=5.8, leading=6.8, alignment=1)

    col_widths = [18, 115, 86, 40, 56, 30, 46, 38, 36, 55]
    _MOD_FR = {
        "Stationary Combustion": "Combustion Stationnaire",
        "Flare": "Torches",
        "Equipment Leaks": "Fuites d'Équipements",
        "Oil and Gas Venting": "Éventage Pétrole & Gaz",
        "Storage Tank": "Bacs de Stockage",
        "Mobile and Transportation": "Transport & Mobile",
        "Miscellaneous": "Divers",
        "Indirect Emissions (Scope 2)": "Émissions Indirectes (Scope 2)",
    }

    for fname, rows in by_fac.items():
        if not rows:
            continue
        fname_esc = safe_pdf_text(fname)
        elements.append(Paragraph(f"<b>{fname_esc} — Inventaire Détaillé ({len(rows)} sources)</b>" if is_fr else f"<b>{fname_esc} — Granular Source Inventory ({len(rows)} sources)</b>", styles["H2"]))
        table_rows = []
        for idx, r in enumerate(rows, 1):
            src_raw = r['source_name']
            if is_fr and src_raw == 'Purchased Electricity (Grid)':
                src_raw = 'Électricité Réseau Importée'
            mod_raw = _MOD_FR.get(r['module'], r['module']) if is_fr else r['module']
            src_str = str(src_raw or "")
            mod_str = str(mod_raw or "")
            src_cell = (
                src_str
                if (len(src_str) <= 18 and "\n" not in src_str)
                else Paragraph(f"<b>{safe_pdf_text(src_raw, 45)}</b>", body_style)
            )
            mod_cell = (
                mod_str
                if (len(mod_str) <= 15 and "\n" not in mod_str)
                else Paragraph(safe_pdf_text(mod_raw, 36), body_style)
            )
            table_rows.append([
                str(idx),
                src_cell,
                mod_cell,
                str(r["scope"] or "")[:12],
                f"{r['quantity']:,.2f}" if r["quantity"] > 0 else "0",
                str(r["unit"] or "")[:10],
                f"{r['co2']:,.2f}",
                f"{r['ch4']:,.3f}",
                f"{r['n2o']:,.3f}",
                f"{r['co2e']:,.2f}",
            ])

        # Facility subtotal
        tot_co2 = sum(r["co2"] for r in rows)
        tot_ch4 = sum(r["ch4"] for r in rows)
        tot_n2o = sum(r["n2o"] for r in rows)
        tot_co2e = sum(r["co2e"] for r in rows)
        table_rows.append([
            "—",
            Paragraph(f"<b>SOUS-TOTAL {safe_pdf_text(str(fname).upper(), 15)}</b>" if is_fr else f"<b>SUBTOTAL {safe_pdf_text(str(fname).upper(), 15)}</b>", body_style),
            "—",
            "—",
            "—",
            "—",
            f"{tot_co2:,.2f}",
            f"{tot_ch4:,.3f}",
            f"{tot_n2o:,.3f}",
            f"{tot_co2e:,.2f}",
        ])

        t_fac = Table([headers_fmt] + table_rows, colWidths=col_widths, repeatRows=1)
        t_fac.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -2), font_reg),
            ("FONTNAME", (1, 1), (1, -2), font_bold),
            ("FONTNAME", (9, 1), (9, -1), font_bold),
            ("FONTNAME", (0, -1), (-1, -1), font_bold),
            ("FONTSIZE", (0, 1), (-1, -1), 5.8),
            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            ("ALIGN", (1, 1), (2, -2), "LEFT"),
            ("ALIGN", (3, 1), (3, -2), "CENTER"),
            ("ALIGN", (5, 1), (5, -2), "CENTER"),
            ("ALIGN", (2, -1), (5, -1), "CENTER"),
            ("ALIGN", (4, 1), (4, -2), "RIGHT"),
            ("ALIGN", (6, 1), (9, -1), "RIGHT"),
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


def _subannual_quarter_elements(fname_esc: str, q_rows: List[Dict[str, Any]], styles: Dict[str, ParagraphStyle],
                                is_fr: bool, font_reg: str, font_bold: str) -> List[Any]:
    """Table B-1 equivalent: YTD and Q1-Q4 totals of one facility."""
    elements = []
    # 1. Quarterly Summary Table (Table B-1 equivalent)
    elements.append(Paragraph(f"<b>{fname_esc} — Bilan Trimestriel &amp; Annuel (Périmètre Opérateur 100 %)</b>" if is_fr else f"<b>{fname_esc} — Quarterly &amp; Annual Performance Summary (100% Operated Basis)</b>", styles["H2"]))

    q_headers = [
        "Indicateur" if is_fr else "Indicator / Metric",
        "Unité" if is_fr else "Unit",
        "YTD Total", "T1 / Q1", "T2 / Q2", "T3 / Q3", "T4 / Q4"
    ]
    hdr_style = ParagraphStyle("QtrHdr", fontName=font_bold, fontSize=6.2, leading=7.2, textColor=colors.white, alignment=1)
    headers_fmt = [Paragraph(h, hdr_style) for h in q_headers]

    tot_co2e = sum(q["co2e"] for q in q_rows)
    tot_co2 = sum(q["co2"] for q in q_rows)
    tot_ch4 = sum(q["ch4"] for q in q_rows)
    tot_n2o = sum(q["n2o"] for q in q_rows)
    tot_oil = sum(q["oil_bbl"] for q in q_rows)
    tot_boe = sum(q["total_boe"] for q in q_rows)
    tot_energy = sum(q["energy_hhv"] for q in q_rows)
    # the days the quarters cover (366 in a leap year, fewer for a partial year); it was always 365 (BA-050)
    tot_days = sum(float(q.get("days") or 0) for q in q_rows) or 365.0
    avg_ci = (tot_co2e / tot_boe) if tot_boe > 0 else 0.0

    if is_fr:
        indicators = [
            ("Émissions Totales (CO2e)", "tonne", tot_co2e, [q["co2e"] for q in q_rows], False),
            ("Émissions Totales de CO2", "tonne", tot_co2, [q["co2"] for q in q_rows], False),
            ("Émissions Totales de CH4", "tonne", tot_ch4, [q["ch4"] for q in q_rows], False),
            ("Émissions Totales de N2O", "tonne", tot_n2o, [q["n2o"] for q in q_rows], False),
            ("Production Primaire de Brut", "bbl", tot_oil, [q["oil_bbl"] for q in q_rows], False),
            ("Volume Total Hydrocarbures (BEP)", "BEP", tot_boe, [q["total_boe"] for q in q_rows], False),
            ("Intensité Carbone (CO2e/BEP)", "t/BEP", avg_ci, [q["intensity_co2e_boe"] for q in q_rows], True),
            ("Énergie Consommée (PCS / HHV)", "10^6 Btu", tot_energy / 1e6, [q["energy_hhv"] / 1e6 for q in q_rows], False),
            ("Moyenne Journalière d'Émissions", "t/jour", tot_co2e / tot_days, [q["daily_avg_co2e"] for q in q_rows], False),
        ]
    else:
        indicators = [
            ("Total Emissions (CO2e)", "tonne", tot_co2e, [q["co2e"] for q in q_rows], False),
            ("Total CO2 Emissions", "tonne", tot_co2, [q["co2"] for q in q_rows], False),
            ("Total CH4 Emissions", "tonne", tot_ch4, [q["ch4"] for q in q_rows], False),
            ("Total N2O Emissions", "tonne", tot_n2o, [q["n2o"] for q in q_rows], False),
            ("Primary Crude Production", "bbl", tot_oil, [q["oil_bbl"] for q in q_rows], False),
            ("Total Hydrocarbon BOE", "BOE", tot_boe, [q["total_boe"] for q in q_rows], False),
            ("Carbon Intensity (CO2e/BOE)", "t/BOE", avg_ci, [q["intensity_co2e_boe"] for q in q_rows], True),
            ("Energy Used (HHV)", "10^6 Btu", tot_energy / 1e6, [q["energy_hhv"] / 1e6 for q in q_rows], False),
            ("Daily Average Emissions", "t/day", tot_co2e / tot_days, [q["daily_avg_co2e"] for q in q_rows], False),
        ]

    t_q_rows = []
    for ind_name, u_str, ytd_v, q_vals, is_intense in indicators:
        fmt_ytd = f"{ytd_v:.3f}" if is_intense else f"{ytd_v:,.1f}"
        row = [ind_name, u_str, fmt_ytd]
        for qv in q_vals:
            row.append(f"{qv:.3f}" if is_intense else f"{qv:,.1f}")
        t_q_rows.append(row)

    t_q = Table([headers_fmt] + t_q_rows, colWidths=[150, 50, 75, 60, 60, 60, 60])
    t_q.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 1), (-1, -1), font_reg),
        ("FONTNAME", (0, 1), (0, -1), font_bold),
        ("FONTNAME", (2, 1), (2, -1), font_bold),
        ("FONTSIZE", (0, 1), (-1, -1), 6.2),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("ALIGN", (1, 1), (1, -1), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_q)
    elements.append(Spacer(1, 6))
    return elements


def _subannual_month_elements(fname_esc: str, f_data: Dict[str, Any], m_rows: List[Dict[str, Any]],
                              styles: Dict[str, ParagraphStyle], lang: str, is_fr: bool, font_reg: str,
                              font_bold: str) -> List[Any]:
    """Jan-Jun and Jul-Dec tables of one facility, or the quarterly-only notice."""
    elements = []
    hdr_style = ParagraphStyle("QtrHdr", fontName=font_bold, fontSize=6.2, leading=7.2, textColor=colors.white, alignment=1)
    # 2. Monthly Detail Table (Jan - Dec) OR honest Quarterly-Only disclosure Paragraph
    if f_data.get("has_monthly_data") and m_rows:
        elements.append(Paragraph(f"<b>{fname_esc} — Ventilation Mensuelle Détaillée (Janvier – Décembre)</b>" if is_fr else f"<b>{fname_esc} — Detailed Monthly Breakdown (January – December)</b>", styles["H3"]))

        # Render in two semesters: Jan-Jun and Jul-Dec
        m_h1 = ["Indicateur", "Jan", "Fév", "Mar", "Avr", "Mai", "Juin"] if is_fr else ["Indicator", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        m_h2 = ["Indicateur", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"] if is_fr else ["Indicator", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        h1_fmt = [Paragraph(h, hdr_style) for h in m_h1]
        h2_fmt = [Paragraph(h, hdr_style) for h in m_h2]

        if is_fr:
            m_indics = [
                ("Émissions (t CO2e)", lambda r: f"{r['co2e']:,.0f}"),
                ("CO2 (tonne)", lambda r: f"{r['co2']:,.0f}"),
                ("CH4 (tonne)", lambda r: f"{r['ch4']:,.1f}"),
                ("N2O (tonne)", lambda r: f"{r['n2o']:,.2f}"),
                ("Pétrole Brut (bbl)", lambda r: f"{r['oil_bbl']:,.0f}"),
                ("Total BEP", lambda r: f"{r['total_boe']:,.0f}"),
                ("CO2e / BEP", lambda r: f"{r['intensity_co2e_boe']:.3f}"),
                ("Énergie (10^6 Btu)", lambda r: f"{r['energy_hhv']/1e6:,.0f}"),
                ("Moy. Jour (t/j)", lambda r: f"{r['daily_avg_co2e']:,.1f}"),
            ]
        else:
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
            r1 = [iname] + [fn(m) for m in sem1]
            r2 = [iname] + [fn(m) for m in sem2]
            t_m1_rows.append(r1)
            t_m2_rows.append(r2)

        t_m1 = Table([h1_fmt] + t_m1_rows, colWidths=[115, 66, 66, 66, 66, 66, 66])
        t_m1.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_DARK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("FONTNAME", (0, 1), (0, -1), font_bold),
            ("FONTSIZE", (0, 1), (-1, -1), 6.2),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
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
            ("FONTNAME", (0, 1), (-1, -1), font_reg),
            ("FONTNAME", (0, 1), (0, -1), font_bold),
            ("FONTSIZE", (0, 1), (-1, -1), 6.2),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 1.8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8),
        ]))

        elements.append(Paragraph("<b>Semestre 1 (Janvier – Juin)</b>" if is_fr else "<b>Semester 1 (January – June)</b>", styles["Body"]))
        elements.append(t_m1)
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("<b>Semestre 2 (Juillet – Décembre)</b>" if is_fr else "<b>Semester 2 (July – December)</b>", styles["Body"]))
        elements.append(t_m2)
        elements.append(Spacer(1, 10))
    else:
        elements.append(Paragraph(get_t("subannual_quarterly_only", lang), styles["BodyMuted"]))
        elements.append(Spacer(1, 8))
    return elements


def build_subannual_timeseries_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str = "en") -> List[Any]:
    """
    Generates APPENDIX B: Sub-Annual Quarterly & Monthly Time-Series Ledgers (Tables B-1 to B-4c equivalent).
    Dynamically renders Q1-Q4 summaries and Jan-Dec monthly tables.
    """
    subannual = {
        fname: f_data
        for fname, f_data in data.get("subannual_time_series", {}).items()
        if _subannual_has_activity(f_data)
    }
    if not subannual:
        return []

    elements = []
    is_fr = str(lang).lower().startswith("fr")
    font_reg, font_bold, _ = register_pdf_fonts()
    elements.append(PageBreak())

    title = "ANNEXE B : REGISTRES OPÉRATIONNELS MENSUELS ET TRIMESTRIELS" if is_fr else "APPENDIX B: SUB-ANNUAL QUARTERLY & MONTHLY OPERATIONAL LEDGERS"
    desc = ("Bilans trimestriels (T1 à T4) et, lorsque disponibles dans la base, ventilations mensuelles (janvier à décembre) de la production, des émissions et des intensités carbone."
            if is_fr else
            "Quarterly rollups (Q1–Q4) and, where monthly disaggregation exists in the database, January–December tracking of hydrocarbon production, GHG discharges, and carbon intensities.")

    elements.append(Paragraph(title, styles["H1"]))
    elements.append(Paragraph(desc, styles["Body"]))
    elements.append(Spacer(1, 6))

    for fname, f_data in subannual.items():
        q_rows = f_data.get("quarterly_rows", [])
        m_rows = f_data.get("monthly_rows", [])

        fname_esc = safe_pdf_text(fname)
        elements.extend(_subannual_quarter_elements(fname_esc, q_rows, styles, is_fr, font_reg, font_bold))
        elements.extend(_subannual_month_elements(fname_esc, f_data, m_rows, styles, lang, is_fr, font_reg, font_bold))

    return elements
