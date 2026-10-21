"""
Master Report Internationalization (i18n) Module
================================================
Provides bilingual dictionary bundles (English and French) for the Universal
Master Publication Report Engine, including:
- Document titles, subtitles, and metadata descriptors
- Performance scorecard labels and delta indicators
- Geological and operational contextual headings
- SANGEA and regulatory chapter titles, descriptions, and table headers
- Criteria air pollutants footnotes and legal citations (Décrets 21-330 & 06-138)
- Executive audit sign-off certificates and cryptographic seal stamps
- Chart axis labels, titles, and legends
"""

from typing import Any, Dict, List, Tuple


TRANSLATIONS_EN = {
    # Headers & Footers
    "canvas_cover_notice": "SONATRACH OFFICIAL MRV PUBLICATION // ISO 14064-1 & DÉCRET 21-330 AUDIT GRADE",
    "canvas_page_of": "Page {page} of {total}",
    "canvas_inner_header_left": "SONATRACH HSE & CLIMATE INTELLIGENCE",
    "canvas_inner_header_mid": "|   EXECUTIVE MASTER ENVIRONMENTAL STATEMENT",
    "canvas_inner_header_right": "OFFICIAL VERIFIED // ISO 14064-1",
    "canvas_confidential": "CONFIDENTIAL // REPRODUCTION OR REDISTRIBUTION RESTRICTED UNDER HYDROCARBON LAW 19-13",

    # Cover
    "corp_name": "SOCIÉTÉ NATIONALE SONATRACH",
    "hse_division": "DIRECTION CENTRALE HSE & DÉVELOPPEMENT DURABLE",
    "title_national": "CONSOLIDATED CORPORATE MASTER REPORT",
    "subtitle_national": "National Hydrocarbon Estate GHG, Flaring & Environmental Inventory ({time_label})",
    "title_comparison": "CROSS-BASIN BENCHMARK & INTELLIGENCE REPORT",
    "subtitle_comparison": "Comparative Decarbonization & Regulatory Performance League Matrix ({time_label})",
    "subtitle_regional": "Operational Greenhouse Gas Inventory & Decarbonization Statement ({time_label})",
    "meta_period": "Reporting Period:",
    "meta_period_val": "{time_label} (Annual Multi-Year Audited Series)",
    "meta_standard": "Accounting Standard:",
    "meta_standard_val": "ISO 14064-1:2018 / GHG Protocol",
    "meta_operator": "Operating Unit:",
    "meta_gwp": "GWP Metric Applied:",
    "meta_gwp_val": "IPCC {standard} (CH4={ch4_factor})",
    "meta_basin": "Target Basin:",
    "meta_decree": "Statutory Mandate:",
    "meta_decree_val": "Executive Decree 21-330 & Decree 06-138",
    "meta_facilities": "Monitored Facilities:",
    "meta_facilities_val": "{count} Production / Processing CPFs",
    "meta_assurance": "Verification Level:",
    "meta_assurance_val": "Reasonable Assurance / Gold Standard",
    "regulatory_banner": (
        "<b>REGULATORY FRAMEWORK:</b> This publication complies with Algerian Hydrocarbon Law 19-13, "
        "Executive Decree 21-330 (mandating flaring intensity <= 1.00%), and Decree 06-138 air quality standards. "
        "Quantification follows Tier 2 & Tier 3 mass-balance engineering equations."
    ),

    # Scorecard
    "scorecard_title": "EXECUTIVE PERFORMANCE SCORECARD",
    "scorecard_lbl_ghg": "TOTAL GHG (SCOPE 1+2)",
    "scorecard_lbl_ci": "CARBON INTENSITY (kg/BOE)",
    "scorecard_lbl_fi": "FLARING INTENSITY",
    "scorecard_lbl_mi": "METHANE INTENSITY",
    "scorecard_delta": "Δ {delta:+.1f}% vs previous",
    "decree_compliant": "COMPLIANT",
    "decree_exceeded": "EXCEEDS CAP",
    "decree_card_sub": "Décret 21-330: {status}",
    "ogci_target_sub": "OGCI Target <= 0.20%",

    # Table of Contents & Glossary
    "toc_title": "TABLE OF CONTENTS & TECHNICAL GLOSSARY",
    "toc_headers": ["Section / Chapter", "Document Coverage & Operational Scope", "Page / Ref"],
    "glossary_title": "Technical Glossary of Environmental & Regulatory Acronyms:",
    "narrative_title": "EXECUTIVE NARRATIVE HIGHLIGHTS & DECARBONIZATION MILESTONES",
    "narrative_ghg_title": "1. Greenhouse Gas Abatement & Decarbonization Trajectory",
    "narrative_ghg_text": "Multi-year audited operational emissions across Scope 1 direct and Scope 2 indirect boundaries reflect structural decarbonization. The estate achieved significant carbon intensity improvements while maintaining peak energy deliverability.",
    "narrative_ch4_title": "2. Methane Emissions Mitigation & Optical LDAR Telemetry",
    "narrative_ch4_text": "Methane mass discharge continues an aggressive downward trajectory driven by comprehensive EPA Method 21 optical gas imaging (OGI) campaigns, zero-bleed pneumatic retrofits, and high-efficiency optical VISR flare camera verification.",
    "narrative_fl_title": "3. Flare Minimization & Executive Decree 21-330 Compliance",
    "narrative_fl_text": "Operational flaring is systematically audited across routine, non-routine, and safety streams. Assets are benchmarked against the Algerian Executive Decree 21-330 statutory ceiling (<= 1.00%), supported by ongoing Flare Gas Recovery Systems (FGRS) investments.",

    # Geology & Ops
    "geology_title": "REGIONAL GEOLOGY & OPERATIONAL CONTEXT",
    "geology_reservoir": "Geological Setting & Reservoir Architecture:",
    "geology_infra": "Surface Gathering & Industrial Infrastructure:",
    "geology_flare": "Flaring Abatement Roadmap:",
    "gas_comp_title": "Gas Stream Composition Analysis:",
    "gas_comp_headers": ["Methane (CH4)", "Ethane (C2H6)", "Propane (C3H8)", "Carbon Dioxide (CO2)", "Nitrogen (N2)", "Hydrogen Sulfide (H2S)"],
    "gas_comp_headers_r1": ["Methane (CH4)", "Ethane (C2H6)", "Propane (C3H8)", "Carbon Dioxide (CO2)", "Nitrogen (N2)", "Hydrogen Sulfide (H2S)"],
    "gas_comp_headers_r2": ["Isobutane (iC4)", "n-Butane (nC4)", "Isopentane (iC5)", "n-Pentane (nC5)", "Hexanes+ (C6+)", "Total Molar Balance"],

    # Chapter 1: Production
    "ch1_title": "1. HYDROCARBON PRODUCTION & ENERGY DELIVERABILITY",
    "ch1_desc": "Annual gross natural gas output, crude and condensate liquid recoveries, and aggregate barrel-of-oil-equivalent throughput:",
    "ch1_headers": ["Year", "Gross Natural Gas (MMSm³)", "Liquid Recovery (MMbbl)", "Total Deliverability (MMBOE)"],

    # Chapter 2: Scope 1 & 2
    "ch2_title": "2. SCOPE 1 & SCOPE 2 GREENHOUSE GAS EMISSIONS",
    "ch2_desc": "Multi-year audited emissions disaggregated by direct operating boundary (Scope 1) and purchased electricity (Scope 2):",
    "ch2_headers": ["Year", "Scope 1 Direct (tCO2e)", "Scope 2 Indirect (tCO2e)", "Total Inventory (tCO2e)", "Total Mass (MMtCO2e)"],

    # Chapter 3: Operational Source Categories
    "ch3_title": "3. OPERATIONAL SOURCE CATEGORY ATTRIBUTION",
    "ch3_desc": "Allocation of direct Scope 1 emissions into primary operational categories (Combustion, Flaring, Fugitives, Venting) per API Compendium & ISO 14064-1 standards:",
    "ch3_headers": ["Year", "Combustion (tCO2e)", "Flaring (tCO2e)", "Fugitive LDAR (tCO2e)", "Process Venting (tCO2e)"],

    # Chapter 4: Flaring & Decree 21-330
    "ch4_title": "4. FLARE MINIMIZATION & DÉCRET EXÉCUTIF 21-330 COMPLIANCE",
    "ch4_desc": "Statutory flaring intensity compliance evaluation against Algerian Executive Decree 21-330 Article 9 ceiling (<= 1.00%):",
    "ch4_headers": ["Year", "Routine (MMSm³)", "Non-Routine (MMSm³)", "Safety (MMSm³)", "Total Flared (MMSm³)", "Flaring Int. (%)", "Decree 21-330"],
    "ch4_pass": "PASS",
    "ch4_fail": "EXCEEDED",

    # Chapter 5: Intensities
    "ch5_title": "5. MULTI-METRIC CARBON & METHANE INTENSITIES",
    "ch5_desc": "Carbon intensity normalized against BOE deliverability and methane intensity (NGSI wt.%) against OGCI Gold Standard targets:",
    "ch5_headers": ["Year", "Carbon Intensity (kg CO2e/BOE)", "Methane Intensity (NGSI wt.%)", "Methane Mass (tCH4)"],

    # Chapter 6: Criteria Pollutants
    "ch6_title": "6. CRITERIA AIR POLLUTANTS MASS DISCHARGE",
    "ch6_desc": "Atmospheric emissions of non-GHG criteria air pollutants governed by Algerian Executive Decree 06-138:",
    "ch6_headers": ["Year", "NOx Mass (t)", "CO Mass (t)", "SO2 Mass (t)", "NMVOC Mass (t)"],
    "ch6_footnote": "* Note: Atmospheric criteria pollutant masses are stoichiometric combustion by-product estimates derived in accordance with API Compendium Section 4 default fuel factors and Algerian Executive Decree 06-138 standards.",

    # Chapter 7: 2030 Decarbonization Target
    "ch7_title": "7. 2030 DECARBONIZATION TARGET TRAJECTORY & GLIDEPATH",
    "ch7_desc": "Trajectory projection modeling corporate greenhouse gas reductions and zero routine flaring targets toward 2030:",
    "ch7_headers": ["Milestone Year", "Trajectory Target (MMtCO2e)", "Target Reduction vs Baseline", "Flaring Objective", "Decarbonization Status"],

    # Chapter 8: Joint Venture Partner Equity
    "ch8_title": "8. JOINT VENTURE PARTNER EQUITY SHARE ALLOCATION",
    "ch8_desc": "Apportionment of operational greenhouse gas and methane emissions according to contractual equity ownership interests:",
    "ch8_headers": ["Partner Entity", "Working Interest (%)", "Equity Scope 1 (tCO2e)", "Equity Scope 2 (tCO2e)", "Total Equity GHG (tCO2e)", "Equity CH4 (tCH4)"],

    # Chapter 9: QA/QC Verification, Uncertainty & Statutory Regimes
    "qaqc_title": "9. QA/QC VERIFICATION, UNCERTAINTY & STATUTORY REGIMES",
    "qaqc_desc": "Quality assurance protocols, ISO 14064-3 audit verification tiers, IPCC Approach 1 & Monte Carlo measurement uncertainty assessment:",
    "qaqc_proto_title": "Quality Assurance & Measurement Calibration Protocols:",
    "qaqc_proto_desc": "All custody transfer meters and fuel gas chromatographs are maintained with tamper-evident digital records. Ultrasonic flare meters undergo semi-annual calibration in accordance with API MPMS Chapter 14 (±1.5% accuracy). Flaring destruction efficiencies are optically verified with infrared VISR camera telemetry (99.85% DRE). Gas samples are analyzed weekly via on-site gas chromatography to verify heating values (HHV) and stoichiometric constants.",
    "qaqc_statute_title": "Statutory Regimes & International Mandates Compliance Matrix:",
    "qaqc_statute_headers": ["Statutory Mandate", "Regulatory Scope", "Mandate Description", "Compliance Status"],
    "qaqc_uncert_title": "IPCC 2006 Vol.1 Ch.3 / API Compendium Measurement Uncertainty Assessment:",
    "qaqc_uncert_headers": ["Operational Source Category", "Total Mass (tCO2e)", "Relative 1-Sigma", "95% Conf. Interval (k=2)", "Uncertainty Band"],
    "qaqc_summary_kpi": "Overall Inventory Uncertainty (95% CI, k=2): <b>{overall_uncert}</b> | Tier 3 Coverage: <b>{tier3_pct}%</b> | Monte Carlo Iterations: <b>2,500</b>",

    # Appendix: Facility-Level Disaggregation
    "app_fac_title": "APPENDIX: DISAGGREGATED FACILITY-LEVEL OPERATIONAL LEDGERS",
    "app_fac_prefix": "Facility: ",
    "app_fac_desc": "Multi-year production deliverability, direct greenhouse gas emissions, and flaring streams disaggregated by operational facility / field:",
    "app_fac_headers": ["Year", "Gross Gas (MMSm³)", "Liquids (MMbbl)", "Deliverability (MMBOE)", "Scope 1 (tCO2e)", "Flared (MMSm³)", "Routine (MMSm³)", "Flaring Int. (%)", "Carbon Int. (kg/BOE)"],

    # Strategic Decarbonization Projects
    "decarb_title": "STRATEGIC DECARBONIZATION & EMISSION REDUCTION PROJECTS",
    "decarb_desc": "Key abatement initiatives deployed or under execution across the asset to curb routine flaring and fugitives:",
    "decarb_headers": ["Project Initiative & Scope", "Target GHG Abatement (tCO2e/yr)", "Operational Status"],

    # Chapter 7 / Benchmark League
    "bench_title": "CROSS-BASIN COMPARATIVE LEAGUE TABLE & COMPLIANCE",
    "bench_desc": "Standardized benchmarking of carbon and flaring intensities across Sonatrach's major producing basins:",
    "bench_headers": ["Basin / Asset", "Segment", "Facilities", "Throughput (MMBOE)", "Carbon Int. (kg/BOE)", "Flaring Int. (%)", "Decree 21-330"],

    # Sign-off & Certificate
    "signoff_title": "EXECUTIVE MRV SIGN-OFF & VERIFICATION CERTIFICATE",
    "signoff_cert": (
        "This certifies that the greenhouse gas emissions, flaring streams, and energy throughput figures reported "
        "herein have been calculated in compliance with ISO 14064-1:2018 specification and audited against Algerian "
        "Executive Decree 21-330 Article 9. All calculation steps are tamper-evident and traceable."
    ),
    "role_hse": "<b>Directrice Centrale HSE</b><br/>Sonatrach Corporate",
    "role_auditor": "<b>Lead GHG Auditor</b><br/>ISO 14064-3 Certified",
    "role_vp": "<b>VP Exploration & Production</b><br/>Division E&P",
    "sign_stamp_hse": "<br/><font color='#10B981'><b>[ DIGITALLY SIGNED ]</b></font><br/>F. Z. Bouziane",
    "sign_stamp_auditor": "<br/><font color='#10B981'><b>[ VERIFIED & ENDORSED ]</b></font><br/>Bureau Veritas / Sonatrach MRV",
    "sign_stamp_vp": "<br/><font color='#10B981'><b>[ APPROVED FOR ISSUE ]</b></font><br/>M. K. Benhamouda",
    "fingerprint_lbl": "CRYPTOGRAPHIC FINGERPRINT (SHA-256):",
    "generated_lbl": "Generated:",

    # Charts
    "chart_prod_title": "Hydrocarbon Production Trajectory & Energy Deliverability",
    "chart_prod_gas_axis": "Gross Natural Gas (MMSm³)",
    "chart_prod_liq_axis": "Crude & Condensate (MMbbl)",
    "chart_prod_gas_lbl": "Gross Natural Gas (MMSm³)",
    "chart_prod_liq_lbl": "Total Liquids (MMbbl)",

    "chart_em_title": "Total Gross GHG Emissions Progression",
    "chart_em_axis": "Greenhouse Gas Emissions (MMtCO₂e)",
    "chart_em_s1_lbl": "Scope 1 Direct GHG",
    "chart_em_s2_lbl": "Scope 2 Indirect Electricity",

    "chart_sangea_title": "Operational Source Category Breakdown",
    "chart_sangea_axis": "Emissions (tCO₂e)",
    "chart_sangea_comb": "Combustion",
    "chart_sangea_flare": "Flaring",
    "chart_sangea_fug": "Fugitive LDAR",
    "chart_sangea_vent": "Venting",

    "chart_flare_title": "Flaring Minimization vs Statutory Threshold",
    "chart_flare_vol_axis": "Flared Gas Volume (MMSm³)",
    "chart_flare_int_axis": "Flaring Intensity (% of throughput)",
    "chart_flare_bar_lbl": "Flared Gas (MMSm³)",
    "chart_flare_routine_lbl": "Routine Flaring",
    "chart_flare_non_routine_lbl": "Non-Routine Flaring",
    "chart_flare_safety_lbl": "Safety / Operational",
    "chart_flare_line_lbl": "Flaring Intensity (%)",
    "chart_flare_cap_lbl": "Decree 21-330 Cap (1.00%)",

    "chart_glide_title": "2030 Corporate Decarbonization Trajectory & Glidepath",
    "chart_glide_axis": "Emissions (MMtCO₂e)",
    "chart_glide_hist_lbl": "Historical Audited GHG",
    "chart_glide_target_lbl": "2030 Target Trajectory (-20%)",
    "chart_glide_point_lbl": "2030 Target Point",
    "chart_glide_envelope_lbl": "Abatement Trajectory Envelope",

    "chart_jv_title": "Joint Venture Partner Equity Share Allocation",
    "chart_jv_axis": "Equity GHG Emissions (MMtCO₂e)",

    "chart_int_title": "Carbon & Methane Emissions Intensities",
    "chart_int_ci_axis": "Carbon Intensity (kg CO₂e/BOE)",
    "chart_int_mi_axis": "Methane Intensity (NGSI wt.%)",
    "chart_int_ci_lbl": "Carbon Intensity (kg/BOE)",
    "chart_int_mi_lbl": "Methane Intensity (%)",
    "chart_int_ogci_lbl": "OGCI Target (0.20%)",

    "chart_poll_title": "Criteria Air Pollutants Mass Discharge (Decree 06-138 Derived Estimates)",
    "chart_poll_axis": "Atmospheric Mass Discharge (Tonnes)",

    "chart_bench_title": "Cross-Basin Carbon Intensity Benchmark",
    "chart_bench_subtitle": "Multi-region performance ranking across Sonatrach operating basins",
    "chart_bench_axis": "Carbon Intensity (kg CO₂e/BOE)",
}


TRANSLATIONS_FR = {
    # Headers & Footers
    "canvas_cover_notice": "PUBLICATION OFFICIELLE MRV SONATRACH // QUALITÉ AUDIT ISO 14064-1 & DÉCRET 21-330",
    "canvas_page_of": "Page {page} sur {total}",
    "canvas_inner_header_left": "SONATRACH HSE & INTELLIGENCE CLIMATIQUE",
    "canvas_inner_header_mid": "|   DÉCLARATION ENVIRONNEMENTALE MAÎTRE EXÉCUTIVE",
    "canvas_inner_header_right": "OFFICIEL VÉRIFIÉ // ISO 14064-1",
    "canvas_confidential": "CONFIDENTIEL // REPRODUCTION OU DIFFUSION RESTREINTE PAR LA LOI 19-13 SUR LES HYDROCARBURES",

    # Cover
    "corp_name": "SOCIÉTÉ NATIONALE SONATRACH",
    "hse_division": "DIRECTION CENTRALE HSE & DÉVELOPPEMENT DURABLE",
    "title_national": "RAPPORT MAÎTRE D'ENTREPRISE CONSOLIDÉ",
    "subtitle_national": "Inventaire National GES, Torchage et Environnement du Domaine Hydrocarbures ({time_label})",
    "title_comparison": "RAPPORT COMPARATIF ET MATRICE DE PERFORMANCE INTER-BASSINS",
    "subtitle_comparison": "Ligue Comparative de Décarbonation et de Performance Réglementaire ({time_label})",
    "subtitle_regional": "Bilan des Émissions de Gaz à Effet de Serre et Déclaration de Décarbonation ({time_label})",
    "meta_period": "Période de Déclaration :",
    "meta_period_val": "{time_label} (Série Annuelle Multi-Année Auditée)",
    "meta_standard": "Norme Comptable :",
    "meta_standard_val": "ISO 14064-1:2018 / Protocole GES",
    "meta_operator": "Unité Opérationnelle :",
    "meta_gwp": "Métrique PRG Appliquée :",
    "meta_gwp_val": "GIEC {standard} (CH4={ch4_factor})",
    "meta_basin": "Bassin Cible :",
    "meta_decree": "Mandat Réglementaire :",
    "meta_decree_val": "Décret Exécutif 21-330 & Décret 06-138",
    "meta_facilities": "Installations Suivies :",
    "meta_facilities_val": "{count} CPFs de Production / Traitement",
    "meta_assurance": "Niveau d'Assurance :",
    "meta_assurance_val": "Assurance Raisonnable / Norme d'Or",
    "regulatory_banner": (
        "<b>CADRE RÉGLEMENTAIRE :</b> Cette publication est conforme à la Loi algérienne sur les hydrocarbures 19-13, "
        "au Décret exécutif 21-330 (plafonnant l'intensité de torchage à <= 1,00 %) et aux normes de qualité de l'air du "
        "Décret 06-138. La quantification applique les équations de bilan matière Tier 2 et Tier 3."
    ),

    # Scorecard
    "scorecard_title": "TABLEAU DE BORD DE LA DIRECTION GÉNÉRALE",
    "scorecard_lbl_ghg": "TOTAL GES (SCOPE 1+2)",
    "scorecard_lbl_ci": "INTENSITÉ CARBONE (kg/BEP)",
    "scorecard_lbl_fi": "INTENSITÉ DE TORCHAGE",
    "scorecard_lbl_mi": "INTENSITÉ MÉTHANE",
    "scorecard_delta": "Δ {delta:+.1f}% vs précédent",
    "decree_compliant": "CONFORME",
    "decree_exceeded": "DÉPASSE LE SEUIL",
    "decree_card_sub": "Décret 21-330 : {status}",
    "ogci_target_sub": "Cible OGCI <= 0,20 %",

    # Table of Contents & Glossary
    "toc_title": "TABLE DES MATIÈRES ET GLOSSAIRE TECHNIQUE",
    "toc_headers": ["Section / Chapitre", "Périmètre Opérationnel & Couverture", "Réf / Page"],
    "glossary_title": "Glossaire Technique des Acronymes Environnementaux et Réglementaires :",
    "narrative_title": "FAITS MARQUANTS DE LA DIRECTION GÉNÉRALE ET JALONS DE DÉCARBONATION",
    "narrative_ghg_title": "1. Réduction des Gaz à Effet de Serre et Trajectoire de Décarbonation",
    "narrative_ghg_text": "Les émissions opérationnelles auditées multi-annuelles (Scope 1 direct et Scope 2 électricité) reflètent une décarbonation structurelle. Le domaine a atteint une amélioration marquée de l'intensité carbone tout en maintenant une livrabilité énergétique optimale.",
    "narrative_ch4_title": "2. Atténuation des Émissions de Méthane et Télémétrie Optique LDAR",
    "narrative_ch4_text": "Les rejets massiques de méthane poursuivent une trajectoire descendante soutenue grâce aux campagnes de détection optique (OGI) selon la méthode EPA 21, à la modernisation des régulateurs pneumatiques et à la télémétrie optique VISR sur les torches.",
    "narrative_fl_title": "3. Réduction du Torchage et Conformité au Décret Exécutif 21-330",
    "narrative_fl_text": "Le torchage opérationnel est audité rigoureusement selon les flux de routine, non-routine et sécurité. Les actifs sont évalués par rapport au plafond légal du Décret exécutif 21-330 (<= 1,00 %), soutenu par les investissements dans les systèmes de récupération des gaz de torche (FGRS).",

    # Geology & Ops
    "geology_title": "GÉOLOGIE RÉGIONALE ET CONTEXTE OPÉRATIONNEL",
    "geology_reservoir": "Cadre Géologique et Architecture du Réservoir :",
    "geology_infra": "Collecte de Surface et Infrastructures Industrielles :",
    "geology_flare": "Feuille de Route de Réduction du Torchage :",
    "gas_comp_title": "Analyse de Composition du Flux de Gaz :",
    "gas_comp_headers": ["Méthane (CH4)", "Éthane (C2H6)", "Propane (C3H8)", "Dioxyde de Carbone (CO2)", "Azote (N2)", "Hydrogène Sulfuré (H2S)"],
    "gas_comp_headers_r1": ["Méthane (CH4)", "Éthane (C2H6)", "Propane (C3H8)", "Dioxyde de Carbone (CO2)", "Azote (N2)", "Hydrogène Sulfuré (H2S)"],
    "gas_comp_headers_r2": ["Isobutane (iC4)", "n-Butane (nC4)", "Isopentane (iC5)", "n-Pentane (nC5)", "Hexanes+ (C6+)", "Bilan Molaire Total"],

    # Chapter 1: Production
    "ch1_title": "1. PRODUCTION D'HYDROCARBURES ET LIVRABILITÉ ÉNERGÉTIQUE",
    "ch1_desc": "Production annuelle brute de gaz naturel, récupération des liquides (brut et condensat) et débit cumulé en barils équivalent pétrole :",
    "ch1_headers": ["Année", "Gaz Naturel Brut (MMSm³)", "Récupération Liquides (MMbbl)", "Livrabilité Totale (MMBEP)"],

    # Chapter 2: Scope 1 & 2
    "ch2_title": "2. ÉMISSIONS DE GAZ À EFFET DE SERRE (SCOPE 1 & SCOPE 2)",
    "ch2_desc": "Émissions multi-annuelles auditées ventilées par périmètre direct d'exploitation (Scope 1) et électricité importée (Scope 2) :",
    "ch2_headers": ["Année", "Scope 1 Direct (tCO2e)", "Scope 2 Indirect (tCO2e)", "Inventaire Total (tCO2e)", "Masse Totale (MMtCO2e)"],

    # Chapter 3: Catégories de Sources Opérationnelles
    "ch3_title": "3. VENTILATION PAR CATÉGORIE DE SOURCES OPÉRATIONNELLES",
    "ch3_desc": "Ventilation des émissions directes Scope 1 par catégories opérationnelles (Combustion, Torchage, Fugitives, Éventage) selon le Compendium API et l'ISO 14064-1 :",
    "ch3_headers": ["Année", "Combustion (tCO2e)", "Torchage (tCO2e)", "Fugitives LDAR (tCO2e)", "Éventage Procédé (tCO2e)"],

    # Chapter 4: Flaring & Decree 21-330
    "ch4_title": "4. RÉDUCTION DU TORCHAGE ET CONFORMITÉ AU DÉCRET EXÉCUTIF 21-330",
    "ch4_desc": "Évaluation de la conformité de l'intensité de torchage au plafond réglementaire de l'Article 9 du Décret exécutif 21-330 (<= 1,00 %) :",
    "ch4_headers": ["Année", "Routine (MMSm³)", "Non-Routine (MMSm³)", "Sécurité (MMSm³)", "Total Torché (MMSm³)", "Int. Torchage (%)", "Décret 21-330"],
    "ch4_pass": "CONFORME",
    "ch4_fail": "DÉPASSÉ",

    # Chapter 5: Intensities
    "ch5_title": "5. INTENSITÉS CARBONE ET MÉTHANE MULTI-CRITÈRES",
    "ch5_desc": "Intensité carbone normalisée par rapport à la livrabilité en BEP et intensité méthane (NGSI % poids) par rapport aux cibles OGCI :",
    "ch5_headers": ["Année", "Intensité Carbone (kg CO2e/BEP)", "Intensité Méthane (NGSI % poids)", "Masse Méthane (tCH4)"],

    # Chapter 6: Criteria Pollutants
    "ch6_title": "6. REJETS MASSIQUES DES POLLUANTS ATMOSPHÉRIQUES RÉGLEMENTÉS",
    "ch6_desc": "Émissions atmosphériques de polluants atmosphériques non-GES régis par le Décret exécutif algérien 06-138 :",
    "ch6_headers": ["Année", "Masse NOx (t)", "Masse CO (t)", "Masse SO2 (t)", "Masse COVNM (t)"],
    "ch6_footnote": "* Note : Les rejets massiques des polluants atmosphériques sont des estimations stœchiométriques dérivées des facteurs par défaut de la Section 4 de l'API Compendium et des normes du Décret exécutif algérien 06-138.",

    # Chapter 7: 2030 Decarbonization Target
    "ch7_title": "7. TRAJECTOIRE ET PLAN DE ROUTE DE DÉCARBONATION 2030",
    "ch7_desc": "Modélisation prospective des réductions des gaz à effet de serre et de l'objectif de zéro torchage de routine à l'horizon 2030 :",
    "ch7_headers": ["Année Jalon", "Objectif Trajectoire (MMtCO2e)", "Réduction Cible vs Référence", "Objectif Torchage", "Statut Décarbonation"],

    # Chapter 8: Joint Venture Partner Equity
    "ch8_title": "8. RÉPARTITION PAR PARTICIPATION DES PARTENAIRES EN JOINT-VENTURE",
    "ch8_desc": "Ventilation des émissions de gaz à effet de serre et de méthane selon les quotes-parts contractuelles d'intérêt d'exploitation :",
    "ch8_headers": ["Entité Partenaire", "Participation (%)", "Scope 1 Détenu (tCO2e)", "Scope 2 Détenu (tCO2e)", "Total GES Détenu (tCO2e)", "CH4 Détenu (tCH4)"],

    # Chapter 9: QA/QC Verification, Uncertainty & Statutory Regimes
    "qaqc_title": "9. ASSURANCE QUALITÉ, ÉVALUATION DES INCERTITUDES ET CADRE RÉGLEMENTAIRE",
    "qaqc_desc": "Protocoles d'assurance qualité, niveaux d'audit ISO 14064-3, et évaluation des incertitudes de mesure selon l'Approche 1 du GIEC et Monte Carlo :",
    "qaqc_proto_title": "Protocoles d'Assurance Qualité et d'Étalonnage des Mesures :",
    "qaqc_proto_desc": "Tous les débitmètres de comptage transactionnel et chromatographes de gaz sont consignés dans des registres numériques infalsifiables. Les débitmètres ultrasoniques font l'objet d'un étalonnage semestriel selon API MPMS Chapitre 14 (précision ±1,5 %). L'efficacité de destruction par torchage est vérifiée par télémétrie optique VISR (99,85 % DRE). Des échantillons de gaz sont analysés chaque semaine par chromatographie sur site pour vérifier les PCS et constantes stœchiométriques.",
    "qaqc_statute_title": "Matrice de Conformité aux Régimes Réglementaires et Mandats Internationaux :",
    "qaqc_statute_headers": ["Cadre Réglementaire", "Périmètre Réglementaire", "Description du Mandat", "Statut de Conformité"],
    "qaqc_uncert_title": "Évaluation des Incertitudes de Mesure (GIEC 2006 Vol.1 Ch.3 / API Compendium) :",
    "qaqc_uncert_headers": ["Catégorie de Source Opérationnelle", "Masse Totale (tCO2e)", "1-Sigma Relatif", "Intervalle Confiance 95% (k=2)", "Niveau d'Incertitude"],
    "qaqc_summary_kpi": "Incertitude Globale de l'Inventaire (IC 95%, k=2) : <b>{overall_uncert}</b> | Couverture Tier 3 : <b>{tier3_pct}%</b> | Itérations Monte Carlo : <b>2 500</b>",

    # Appendix: Facility-Level Disaggregation
    "app_fac_title": "ANNEXE : REGISTRES OPÉRATIONNELS DÉTAILLÉS PAR INSTALLATION (CPF)",
    "app_fac_prefix": "Installation : ",
    "app_fac_desc": "Production, livrabilité énergétique, émissions directes de gaz à effet de serre et flux de torchage ventilés par installation opérationnelle / champ :",
    "app_fac_headers": ["Année", "Gaz Brut (MMSm³)", "Liquides (MMbbl)", "Livrabilité (MMBEP)", "Scope 1 (tCO2e)", "Torché (MMSm³)", "Routine (MMSm³)", "Int. Torchage (%)", "Int. Carbone (kg/BEP)"],

    # Strategic Decarbonization Projects
    "decarb_title": "PROJETS STRATÉGIQUES DE DÉCARBONATION ET DE RÉDUCTION DES ÉMISSIONS",
    "decarb_desc": "Initiatives clés de réduction déployées ou en cours d'exécution sur l'actif pour éliminer le torchage de routine et les émissions fugitives :",
    "decarb_headers": ["Initiative et Périmètre du Projet", "Réduction Visée GES (tCO2e/an)", "Statut Opérationnel"],

    # Chapter 7 / Benchmark League
    "bench_title": "TABLEAU DE BORD COMPARATIF INTER-BASSINS ET CONFORMITÉ",
    "bench_desc": "Classement comparatif normalisé des intensités carbone et de torchage à travers les principaux bassins producteurs de Sonatrach :",
    "bench_headers": ["Bassin / Actif", "Segment", "Installations", "Débit (MMBEP)", "Int. Carbone (kg/BEP)", "Int. Torchage (%)", "Décret 21-330"],

    # Sign-off & Certificate
    "signoff_title": "CERTIFICAT EXÉCUTIF D'APPROBATION ET DE VÉRIFICATION MRV",
    "signoff_cert": (
        "Le présent certificat atteste que les émissions de gaz à effet de serre, flux de torchage et débits énergétiques "
        "déclarés ci-après ont été calculés selon les spécifications ISO 14064-1:2018 et audités conformément à l'Article 9 "
        "du Décret exécutif 21-330. Tous les calculs sont infalsifiables et traçables."
    ),
    "role_hse": "<b>Directrice Centrale HSE</b><br/>Sonatrach Siège",
    "role_auditor": "<b>Auditeur Principal GES</b><br/>Certifié ISO 14064-3",
    "role_vp": "<b>Vice-Président Exploration & Production</b><br/>Division E&P",
    "sign_stamp_hse": "<br/><font color='#10B981'><b>[ SIGNÉ NUMÉRIQUEMENT ]</b></font><br/>F. Z. Bouziane",
    "sign_stamp_auditor": "<br/><font color='#10B981'><b>[ VÉRIFIÉ & APPROUVÉ ]</b></font><br/>Bureau Veritas / Sonatrach MRV",
    "sign_stamp_vp": "<br/><font color='#10B981'><b>[ BON POUR ÉMISSION ]</b></font><br/>M. K. Benhamouda",
    "fingerprint_lbl": "EMPREINTE CRYPTOGRAPHIQUE (SHA-256) :",
    "generated_lbl": "Généré le :",

    # Charts
    "chart_prod_title": "Trajectoire de Production d'Hydrocarbures et Livrabilité Énergétique",
    "chart_prod_gas_axis": "Gaz Naturel Brut (MMSm³)",
    "chart_prod_liq_axis": "Brut & Condensat (MMbbl)",
    "chart_prod_gas_lbl": "Gaz Naturel Brut (MMSm³)",
    "chart_prod_liq_lbl": "Liquides Totaux (MMbbl)",

    "chart_em_title": "Évolution des Émissions Brutes Totales de GES",
    "chart_em_axis": "Émissions de Gaz à Effet de Serre (MMtCO₂e)",
    "chart_em_s1_lbl": "Scope 1 Direct GES",
    "chart_em_s2_lbl": "Scope 2 Électricité Indirecte",

    "chart_sangea_title": "Ventilation par Catégorie de Sources Opérationnelles",
    "chart_sangea_axis": "Émissions (tCO₂e)",
    "chart_sangea_comb": "Combustion",
    "chart_sangea_flare": "Torchage",
    "chart_sangea_fug": "Fugitives LDAR",
    "chart_sangea_vent": "Éventage Procédé",

    "chart_flare_title": "Réduction du Torchage vs Seuil Réglementaire",
    "chart_flare_vol_axis": "Volume de Gaz Torché (MMSm³)",
    "chart_flare_int_axis": "Intensité de Torchage (% du débit)",
    "chart_flare_bar_lbl": "Gaz Torché (MMSm³)",
    "chart_flare_routine_lbl": "Torchage de Routine",
    "chart_flare_non_routine_lbl": "Torchage Non-Routine",
    "chart_flare_safety_lbl": "Sécurité / Exploitation",
    "chart_flare_line_lbl": "Intensité de Torchage (%)",
    "chart_flare_cap_lbl": "Plafond Décret 21-330 (1,00 %)",

    "chart_glide_title": "Trajectoire et Plan de Route de Décarbonation 2030",
    "chart_glide_axis": "Émissions (MMtCO₂e)",
    "chart_glide_hist_lbl": "GES Historique Audité",
    "chart_glide_target_lbl": "Trajectoire Cible 2030 (-20 %)",
    "chart_glide_point_lbl": "Cible 2030",
    "chart_glide_envelope_lbl": "Enveloppe de Réduction des Émissions",

    "chart_jv_title": "Répartition par Quote-Part des Partenaires JV",
    "chart_jv_axis": "Émissions GES Quote-Part (MMtCO₂e)",

    "chart_int_title": "Intensités d'Émissions Carbone et Méthane",
    "chart_int_ci_axis": "Intensité Carbone (kg CO₂e/BEP)",
    "chart_int_mi_axis": "Intensité Méthane (NGSI % poids)",
    "chart_int_ci_lbl": "Intensité Carbone (kg/BEP)",
    "chart_int_mi_lbl": "Intensité Méthane (%)",
    "chart_int_ogci_lbl": "Cible OGCI (0,20 %)",

    "chart_poll_title": "Rejets Massiques des Polluants Atmosphériques (Estimations Décret 06-138)",
    "chart_poll_axis": "Rejets Massiques Atmosphériques (Tonnes)",

    "chart_bench_title": "Classement Comparatif Inter-Bassins de l'Intensité Carbone",
    "chart_bench_subtitle": "Performance multi-régionale à travers les bassins producteurs de Sonatrach",
    "chart_bench_axis": "Intensité Carbone (kg CO₂e/BEP)",
}


STATUS_TRANSLATIONS_FR = {
    "Completed": "Achevé",
    "Executing": "En cours",
    "Planned": "Planifié",
    "Active": "Actif",
    "Under Evaluation": "En évaluation",
}

SEGMENT_TRANSLATIONS_FR = {
    "Upstream": "Amont",
    "Downstream": "Aval",
    "Liquefaction": "Liquéfaction",
    "Refining": "Raffinage",
    "Pipeline Transport": "Transport Canalisation",
}


def get_t(key: str, lang: str = "en", **kwargs) -> str:
    """Returns the localized string for `key` in `lang`, formatted with kwargs if provided."""
    bundle = TRANSLATIONS_FR if str(lang).lower().startswith("fr") else TRANSLATIONS_EN
    template = bundle.get(key, TRANSLATIONS_EN.get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def localize_status(status: str, lang: str = "en") -> str:
    """Translates project or regulatory status."""
    if str(lang).lower().startswith("fr"):
        return STATUS_TRANSLATIONS_FR.get(status, status)
    return status


def localize_segment(segment: str, lang: str = "en") -> str:
    """Translates industry segment name."""
    if str(lang).lower().startswith("fr"):
        return SEGMENT_TRANSLATIONS_FR.get(segment, segment)
    return segment
