"""
Universal Master Publication Report Engine
==========================================
Generates high-resolution, publication-grade executive PDF reports:
1. Consolidated Demo Operator Corporate Master Report
2. Regional Asset Master Reports (Basin Alpha, Basin Beta, Coastal Terminal)
3. Multi-Region Cross-Basin Benchmark Report

Complies with ISO 14064-1:2018, Algerian Executive Decree 21-330, and Executive Decree 06-138.
Supports bilingual output (English and French).

The section builders live in master_report_engine_front (cover, scorecard, geology, glidepath, JV, benchmark,
sign-off, process architecture) and master_report_engine_chapters (chart chapters, projects, OGMP, Scope 3,
CBAM / MACC); they use the styles and palette defined here and are imported at the end of this module.
"""

import os
import io
import json
import tempfile
import hashlib
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Image, PageBreak, Flowable
)
from reportlab.pdfgen import canvas

from services.master_report_data import aggregate_master_report_data
from services.master_report_charts import (
    generate_production_chart,
    generate_emissions_sangea_panel_chart,
    generate_flaring_decree_chart,
    generate_intensities_pollutants_panel_chart,
    generate_2030_glidepath_chart,
    generate_glidepath_jv_panel_chart,
    generate_regional_benchmark_chart,
    generate_ogmp_reconciliation_chart,
    generate_scope3_category_chart,
    generate_cbam_embeddings_chart,
    generate_process_overview_diagram,
)
from services.master_report_i18n import (
    get_t, TRANSLATIONS_EN, TRANSLATIONS_FR
)
from services.master_report_appendices import (
    register_pdf_fonts,
    build_qaqc_uncertainty_elements,
    build_facility_appendix_elements,
    build_toc_and_glossary_elements,
    build_executive_narrative_elements,
    build_equipment_census_elements,
    build_gas_chromatography_elements,
    build_flaring_operational_elements,
    build_dynamic_quality_audit_elements,
    build_granular_source_ledger_elements,
    build_subannual_timeseries_elements,
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


COLOR_AMBER = colors.HexColor("#B45309")
COLOR_AMBER_BG = colors.HexColor("#FFFBEB")
COLOR_AMBER_BORDER = colors.HexColor("#D97706")
COLOR_SUCCESS_BG = colors.HexColor("#ECFDF5")


class _MasterDocTemplate(SimpleDocTemplate):
    """Custom DocTemplate collecting exact heading page numbers for 2-pass Table of Contents."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.toc_pages: Dict[str, int] = {}

    def afterFlowable(self, flowable):
        """Records the first page number for each flowable tagged with a `_toc_key` attribute."""
        toc_key = getattr(flowable, "_toc_key", None)
        if toc_key:
            self.toc_pages.setdefault(toc_key, self.page)


def _mark_toc(elems: List[Any], key: str) -> List[Any]:
    """Attaches a Pass-1 TOC lookup marker onto the first heading Paragraph without altering layout flow."""
    for item in elems:
        if isinstance(item, Paragraph):
            setattr(item, "_toc_key", key)
            break
    return elems


class _ImagePlaceholder(Flowable):
    """Exact-size Pass-1 placeholder avoiding redundant image decoding/compression during TOC discovery."""

    def __init__(self, width: float, height: float) -> None:
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, availWidth: float, availHeight: float):
        return self.width, self.height

    def draw(self) -> None:
        pass


def _chart_flowable(chart_path: Optional[str], width: float, height: float, for_toc_pass: bool = False) -> Optional[Flowable]:
    """Returns a size-matched placeholder during Pass 1 or the decoded Image during Pass 2."""
    if not chart_path or not os.path.exists(chart_path):
        return None
    if for_toc_pass:
        return _ImagePlaceholder(width, height)
    return Image(chart_path, width=width, height=height)


class MasterReportNumberedCanvas(canvas.Canvas):
    """Two-pass canvas generating dynamic 'Page X of Y' footers and period-lock-aware running headers."""
    def __init__(self, *args, language: str = "en", governance: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.language = language
        self.governance = governance or {}
        self._saved_page_states = []

    def showPage(self):
        """Buffers current canvas page state so total page count is known before final drawing."""
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Replays buffered pages with final headers/footers and persists the PDF stream."""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_decorations(self, total_pages: int):
        lang = self.language
        font_reg, font_bold, _ = register_pdf_fonts()
        is_locked = bool(self.governance.get("is_locked"))
        if self._pageNumber == 1:
            self.setFillColor(COLOR_ORANGE)
            self.rect(0, PAGE_HEIGHT - 6, PAGE_WIDTH, 6, fill=1, stroke=0)
            self.setFont(font_bold, 6.8)
            self.setFillColor(COLOR_SUCCESS if is_locked else COLOR_AMBER)
            cover_key = "canvas_cover_notice" if is_locked else "canvas_prelim_cover_notice"
            self.drawString(MARGIN, 22, get_t(cover_key, lang))
            self.setFillColor(COLOR_MUTED)
            self.drawRightString(PAGE_WIDTH - MARGIN, 22, get_t("canvas_page_of", lang, page=1, total=total_pages))
            return

        # Running header on inner pages (computed width avoids overlapping with DejaVuSans metrics)
        left_txt = get_t("canvas_inner_header_left", lang)
        self.setFont(font_bold, 7.5)
        self.setFillColor(COLOR_ORANGE)
        self.drawString(MARGIN, PAGE_HEIGHT - 24, left_txt)
        left_w = self.stringWidth(left_txt, font_bold, 7.5)

        self.setFont(font_reg, 7.0)
        self.setFillColor(COLOR_MUTED)
        self.drawString(MARGIN + left_w + 6, PAGE_HEIGHT - 24, get_t("canvas_inner_header_mid", lang))

        self.setFont(font_bold, 7.0)
        self.setFillColor(COLOR_SUCCESS if is_locked else COLOR_AMBER)
        right_key = "canvas_inner_header_right" if is_locked else "canvas_prelim_inner_right"
        self.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 24, get_t(right_key, lang))

        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.5)
        self.line(MARGIN, PAGE_HEIGHT - 28, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 28)

        # Running footer
        self.line(MARGIN, 30, PAGE_WIDTH - MARGIN, 30)
        self.setFont(font_reg, 6.8)
        self.setFillColor(COLOR_MUTED)
        self.drawString(MARGIN, 20, get_t("canvas_confidential", lang))
        self.drawRightString(PAGE_WIDTH - MARGIN, 20, get_t("canvas_page_of", lang, page=self._pageNumber, total=total_pages))


def _build_styles() -> Dict[str, ParagraphStyle]:
    """Prepares consistent Unicode-capable typography hierarchy for the publication document."""
    font_reg, font_bold, _ = register_pdf_fonts()
    styles = {}
    styles["Title"] = ParagraphStyle("CoverTitle", fontName=font_bold, fontSize=20, leading=24, textColor=COLOR_DARK, spaceAfter=6)
    styles["Subtitle"] = ParagraphStyle("CoverSubtitle", fontName=font_reg, fontSize=11, leading=15, textColor=COLOR_MUTED, spaceAfter=14)
    styles["H1"] = ParagraphStyle("Heading1", fontName=font_bold, fontSize=12, leading=16, textColor=COLOR_DARK, spaceBefore=12, spaceAfter=6, keepWithNext=True)
    styles["H2"] = ParagraphStyle("Heading2", fontName=font_bold, fontSize=10, leading=13, textColor=COLOR_ORANGE, spaceBefore=8, spaceAfter=4, keepWithNext=True)
    styles["Body"] = ParagraphStyle("BodyDark", fontName=font_reg, fontSize=8.5, leading=11.5, textColor=COLOR_SLATE, spaceAfter=6)
    styles["BodyMuted"] = ParagraphStyle("BodyMuted", fontName=font_reg, fontSize=7.5, leading=10, textColor=COLOR_MUTED, spaceAfter=4)
    styles["CardVal"] = ParagraphStyle("CardValue", fontName=font_bold, fontSize=13, leading=16, textColor=COLOR_DARK, alignment=1)
    styles["CardLbl"] = ParagraphStyle("CardLabel", fontName=font_bold, fontSize=7, leading=9, textColor=COLOR_MUTED, alignment=1)
    styles["H3"] = ParagraphStyle("Heading3", fontName=font_bold, fontSize=8.5, leading=11, textColor=COLOR_DARK, spaceBefore=6, spaceAfter=3, keepWithNext=True)
    styles["BodySmall"] = ParagraphStyle("BodySmall", fontName=font_reg, fontSize=7, leading=9, textColor=COLOR_SLATE, spaceAfter=3)
    return styles


def _front_matter_elements(data: Dict[str, Any], styles: Dict[str, ParagraphStyle], lang: str, pfd_elems: List[Any], census_elems: List[Any], narr_elems: List[Any], toc_pages: Optional[Dict[str, int]], section_flags: Dict[str, bool]) -> List[Any]:
    """Cover, scorecard, process diagrams, geology, census / narrative and the table of contents."""
    elements = []
    # 1. Executive Cover & Performance Scorecard (Page 1)
    elements.extend(_mark_toc(_build_cover_elements(data, styles, lang), "cover"))
    elements.extend(_build_scorecard_elements(data, styles, lang))
    elements.append(PageBreak())

    # 2. Process Architecture & PFD Flowcharts
    if pfd_elems:
        elements.extend(_mark_toc(pfd_elems, "pfd"))
        elements.append(PageBreak())

    # 3. Regional Geology & Stream-by-Stream Gas Chromatography
    elements.extend(_mark_toc(_build_geology_and_ops_elements(data, styles, lang), "geology"))
    gc_elems = build_gas_chromatography_elements(data, styles, lang=lang)
    if gc_elems:
        elements.extend(gc_elems)
    elements.append(PageBreak())

    # 4. Equipment Census & Narrative Highlights
    if census_elems:
        elements.extend(_mark_toc(census_elems, "census_narrative"))
        elements.extend(narr_elems)
    else:
        elements.extend(_mark_toc(narr_elems, "census_narrative"))
    elements.append(PageBreak())

    # 5. Table of Contents & Technical Glossary (exact 2-pass page numbers)
    elements.extend(
        _mark_toc(
            build_toc_and_glossary_elements(data, styles, lang=lang, toc_pages=toc_pages, section_flags=section_flags),
            "toc",
        )
    )
    elements.append(PageBreak())
    return elements


def _production_emissions_flaring_chapters(data: Dict[str, Any], timeline: List[Dict[str, Any]], charts: Dict[str, str], styles: Dict[str, ParagraphStyle], lang: str, for_toc_pass: bool) -> List[Any]:
    """Chapters 1 to 4: production, Scope 1 and 2 emissions, source categories and flaring."""
    elements = []
    # Chapter 1: Production
    prod_rows = [[str(t["year"]), f"{t['gross_gas_mmsm3']:,.1f}", f"{t['liquid_mmbbl']:.2f}", f"{t['total_mmboe']:.2f}"] for t in timeline]
    elements.extend(_mark_toc(_build_chapter_with_chart(
        get_t("ch1_title", lang),
        get_t("ch1_desc", lang),
        charts["prod"],
        TRANSLATIONS_FR["ch1_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch1_headers"],
        prod_rows,
        [70, 150, 150, 150],
        styles,
        for_toc_pass=for_toc_pass,
    ), "ch1"))
    elements.append(PageBreak())

    # Chapter 2: Scope 1 & 2 Emissions (paired 2-panel chart with Chapter 3 SANGEA attribution)
    em_rows = [
        [
            str(t["year"]),
            f"{t['scope1_co2e_t']:,.0f}",
            f"{t.get('co2_mass_t', 0.0):,.0f}",
            f"{t.get('ch4_mass_t', 0.0):,.0f}",
            f"{t.get('n2o_mass_t', 0.0):.1f}",
            f"{t['scope2_co2e_t']:,.0f}",
            f"{t['total_mmt']:.3f}"
        ]
        for t in timeline
    ]
    elements.extend(_mark_toc(_build_chapter_with_chart(
        get_t("ch2_title", lang),
        get_t("ch2_desc", lang),
        charts["em_sangea"],
        TRANSLATIONS_FR["ch2_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch2_headers"],
        em_rows,
        [42, 88, 78, 66, 60, 88, 98],
        styles,
        img_height=165,
        for_toc_pass=for_toc_pass,
    ), "ch2"))

    # Chapter 3: SANGEA Modules (tabular companion to paired Figure 2/3 above)
    sangea_rows = [[str(t["year"]), f"{t['combustion_t']:,.0f}", f"{t['flaring_t']:,.0f}", f"{t['fugitives_t']:,.0f}", f"{t['venting_t']:,.0f}"] for t in timeline]
    elements.extend(_mark_toc(_build_chapter_with_chart(
        get_t("ch3_title", lang),
        get_t("ch3_desc", lang),
        None,
        TRANSLATIONS_FR["ch3_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch3_headers"],
        sangea_rows,
        [60, 115, 115, 115, 115],
        styles,
    ), "ch3"))
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
    elements.extend(_mark_toc(_build_chapter_with_chart(
        get_t("ch4_title", lang),
        get_t("ch4_desc", lang),
        charts["flare"],
        TRANSLATIONS_FR["ch4_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch4_headers"],
        flare_rows,
        [42, 76, 86, 74, 80, 78, 84],
        styles,
        for_toc_pass=for_toc_pass,
    ), "ch4"))
    flare_op_elems = build_flaring_operational_elements(data, styles, lang=lang)
    if flare_op_elems:
        elements.extend(flare_op_elems)
    elements.append(PageBreak())
    return elements


def _assemble_document_story(
    data: Dict[str, Any],
    charts: Dict[str, str],
    styles: Dict[str, ParagraphStyle],
    pfd_charts: Optional[Dict[str, str]] = None,
    lang: str = "en",
    toc_pages: Optional[Dict[str, int]] = None,
    for_toc_pass: bool = False,
) -> List[Any]:
    """Assembles all sections, scorecards, chapters, charts, and appendices into a cohesive flow."""
    elements = []
    mode = data["mode"]
    timeline = data["timeline"]

    # Pre-build dynamic optional appendices & sections so TOC lists only included sections
    pfd_elems = _build_process_architecture_elements(data, pfd_charts, styles, lang, for_toc_pass=for_toc_pass)
    census_elems = build_equipment_census_elements(data, styles, lang=lang)
    narr_elems = build_executive_narrative_elements(data, styles, lang=lang)
    audit_elems = build_dynamic_quality_audit_elements(data, styles, lang=lang)
    jv_elems = _build_jv_equity_elements(data, None, styles, lang)
    ledger_elems = build_granular_source_ledger_elements(data, styles, lang=lang)
    subannual_elems = build_subannual_timeseries_elements(data, styles, lang=lang)
    fac_app_elems = build_facility_appendix_elements(data, styles, lang=lang) if data.get("facility_breakdowns") else []

    section_flags = {
        "pfd": bool(pfd_elems),
        "jv": bool(jv_elems),
        "ch13": bool(audit_elems),
        "app_a": bool(ledger_elems),
        "app_b": bool(subannual_elems),
        "app_c": bool(fac_app_elems),
    }

    elements.extend(_front_matter_elements(data, styles, lang, pfd_elems, census_elems, narr_elems, toc_pages, section_flags))
    elements.extend(_production_emissions_flaring_chapters(data, timeline, charts, styles, lang, for_toc_pass))

    # Chapter 5: OGMP 2.0 Methane Reconciliation & LDAR Telemetry
    elements.extend(_mark_toc(_build_ogmp_elements(data, charts["ogmp"], styles, lang, for_toc_pass=for_toc_pass), "ch5"))
    elements.append(PageBreak())

    # Chapter 6: Operational Efficiency & Multi-Metric Intensities (paired 2-panel chart with Ch 8 Pollutants)
    int_rows = [[str(t["year"]), f"{t['carbon_intensity_kg_boe']:.1f}", f"{t['methane_intensity_pct']:.3f}%",
                 (f"{t['methane_intensity_ngsi_pct']:.3f}%" if t.get("methane_intensity_ngsi_pct") is not None else "N/A"),
                 f"{t['ch4_mass_t']:,.0f}"] for t in timeline]
    elements.extend(_mark_toc(_build_chapter_with_chart(
        get_t("ch6_title", lang),
        get_t("ch6_desc", lang),
        charts["int_poll"],
        TRANSLATIONS_FR["ch6_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch6_headers"],
        int_rows,
        [55, 120, 135, 95, 115],
        styles,
        img_height=165,
        for_toc_pass=for_toc_pass,
    ), "ch6"))
    elements.append(PageBreak())

    # Chapter 7: Scope 3 Value Chain Emissions & Product Lifecycle
    elements.extend(_mark_toc(_build_scope3_elements(data, charts["s3"], styles, lang, for_toc_pass=for_toc_pass), "ch7"))
    elements.append(PageBreak())

    # Chapter 8: Criteria Pollutants Mass Discharge & DB Decarbonization Projects
    poll_rows = [[str(t["year"]), f"{t['nox_t']:.1f}", f"{t['co_t']:.1f}", f"{t['so2_t']:.1f}", f"{t['voc_t']:.1f}"] for t in timeline]
    elements.extend(_mark_toc(_build_chapter_with_chart(
        get_t("ch8_title", lang),
        get_t("ch8_desc", lang),
        None,
        TRANSLATIONS_FR["ch8_headers"] if str(lang).lower().startswith("fr") else TRANSLATIONS_EN["ch8_headers"],
        poll_rows,
        [70, 110, 110, 110, 120],
        styles,
        footnote=get_t("ch8_footnote", lang),
        badge_text=get_t("ch8_screening_badge", lang),
    ), "ch8"))
    elements.extend(_build_decarbonization_projects_elements(data, styles, lang))
    elements.append(PageBreak())

    # Chapter 9: 2030 Corporate Decarbonization Target Trajectory & Glidepath
    elements.extend(_mark_toc(_build_glidepath_elements(data, charts["glide_jv"], styles, lang, img_height=charts.get("glide_jv_height", 165), for_toc_pass=for_toc_pass), "ch9"))
    elements.append(PageBreak())

    # Chapter 10: EU CBAM Hydrocarbon Export Embeddings & Decarbonization Economics
    elements.extend(_mark_toc(_build_cbam_macc_elements(data, charts["cbam"], styles, lang, for_toc_pass=for_toc_pass), "ch10"))
    elements.append(PageBreak())

    # Chapter 11: Joint Venture Partner Equity Share Allocation (when JV partners exist)
    if jv_elems:
        elements.extend(_mark_toc(jv_elems, "ch11"))
        elements.append(PageBreak())

    # Chapter 12: QA/QC Verification, Base Year Recalculations & Statutory Regimes
    elements.extend(_mark_toc(build_qaqc_uncertainty_elements(data, styles, lang=lang), "ch12"))
    elements.append(PageBreak())

    # Chapter 13: Dynamic Inventory Data Quality Audit & Improvement Roadmap
    if audit_elems:
        elements.extend(_mark_toc(audit_elems, "ch13"))
        elements.append(PageBreak())

    # Executive MRV Sign-off & Canonical Dataset Integrity SHA-256 Certificate
    dataset_hash = data.get("dataset_sha256")
    if not dataset_hash:
        canonical_bytes = json.dumps(data, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
        dataset_hash = hashlib.sha256(canonical_bytes).hexdigest()
    elements.extend(_mark_toc(_build_signoff_elements(data, dataset_hash, styles, lang), "signoff"))

    # Cross-Basin Comparative League Table (if comparison mode)
    if mode == "comparison":
        elements.append(PageBreak())
        elements.extend(_mark_toc(_build_benchmark_league_elements(data, charts["bench"], styles, lang, for_toc_pass=for_toc_pass), "benchmark"))

    # Appendix A: Full Granular Source-by-Source Activity & Emissions Ledger
    if ledger_elems:
        elements.extend(_mark_toc(ledger_elems, "app_a"))

    # Appendix B: Sub-Annual Quarterly & Monthly Time-Series Ledgers
    if subannual_elems:
        elements.extend(_mark_toc(subannual_elems, "app_b"))

    # Appendix C: Disaggregated Facility Ledgers
    if fac_app_elems:
        elements.append(PageBreak())
        elements.extend(_mark_toc(fac_app_elems, "app_c"))

    return elements


class MasterReportPdfBuffer(io.BytesIO):
    """Typed BytesIO PDF buffer carrying cryptographic report and dataset SHA-256 digests."""

    def __init__(
        self,
        initial_bytes: bytes = b"",
        *,
        report_hash: str = "",
        dataset_hash: Optional[str] = None,
    ) -> None:
        super().__init__(initial_bytes)
        self.report_hash: str = report_hash
        self.dataset_hash: Optional[str] = dataset_hash


def generate_master_publication_pdf(
    mode: str,
    region_key: Optional[str],
    start_year: int,
    end_year: int,
    gwp_standard: str = "AR5",
    allowed_facility_ids: Optional[List[int]] = None,
    language: str = "en",
    tenant_id: str = "default",
) -> MasterReportPdfBuffer:
    """
    Main orchestration routine. Compiles the publication PDF and returns an in-memory BytesIO buffer.
    """
    data = aggregate_master_report_data(
        mode,
        region_key,
        start_year,
        end_year,
        gwp_standard,
        allowed_facility_ids,
        tenant_id=tenant_id,
    )
    timeline = data["timeline"]
    years = [t["year"] for t in timeline]
    styles = _build_styles()

    with tempfile.TemporaryDirectory() as tmp_dir:
        jv_eq = data.get("jv_equity") or {}
        has_jv_partners = bool(
            isinstance(jv_eq, dict) and jv_eq.get("partners") and jv_eq.get("annual_equity_timeline")
        )
        charts = {
            "prod": os.path.join(tmp_dir, "prod.png"),
            "em_sangea": os.path.join(tmp_dir, "em_sangea.png"),
            "flare": os.path.join(tmp_dir, "flare.png"),
            "int_poll": os.path.join(tmp_dir, "int_poll.png"),
            "glide_jv": os.path.join(tmp_dir, "glide_jv.png"),
            "glide_jv_height": 165 if has_jv_partners else 225,
            "bench": os.path.join(tmp_dir, "bench.png"),
            "ogmp": os.path.join(tmp_dir, "ogmp.png"),
            "s3": os.path.join(tmp_dir, "s3.png"),
            "cbam": os.path.join(tmp_dir, "cbam.png"),
        }

        generate_production_chart(years, [t["gross_gas_mmsm3"] for t in timeline], [t["liquid_mmbbl"] for t in timeline], charts["prod"], language=language)
        generate_emissions_sangea_panel_chart(
            years,
            [t["scope1_mmt"] for t in timeline],
            [t["scope2_mmt"] for t in timeline],
            [t["combustion_t"] for t in timeline],
            [t["flaring_t"] for t in timeline],
            [t["fugitives_t"] for t in timeline],
            [t["venting_t"] for t in timeline],
            charts["em_sangea"],
            language=language,
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
        generate_intensities_pollutants_panel_chart(
            years,
            [t["carbon_intensity_kg_boe"] for t in timeline],
            [t["methane_intensity_pct"] for t in timeline],
            [t["nox_t"] for t in timeline],
            [t["co_t"] for t in timeline],
            [t["so2_t"] for t in timeline],
            [t["voc_t"] for t in timeline],
            charts["int_poll"],
            language=language,
        )
        if has_jv_partners:
            generate_glidepath_jv_panel_chart(data["target_projection"], jv_eq, charts["glide_jv"], language=language)
        else:
            generate_2030_glidepath_chart(data["target_projection"], charts["glide_jv"], language=language)
        generate_ogmp_reconciliation_chart(data.get("ogmp", {}), charts["ogmp"], language=language)
        generate_scope3_category_chart(data.get("scope3", {}), charts["s3"], language=language)
        generate_cbam_embeddings_chart(data.get("cbam_macc", {}), charts["cbam"], language=language)
        if mode == "comparison":
            generate_regional_benchmark_chart(data.get("regional_benchmarks", []), charts["bench"], language=language)

        ledger_by_fac = data.get("granular_source_ledger", {}).get("ledger_by_facility", {})
        active_mods = data.get("active_modules")
        active_by_fac = data.get("active_modules_by_facility") or {}
        pfd_charts = {}
        for fac in data.get("facilities", []):
            fname = fac["name"]
            if ledger_by_fac and not ledger_by_fac.get(fname):
                continue
            fac_mods = active_by_fac[fname] if fname in active_by_fac else active_mods
            pfd_path = os.path.join(tmp_dir, f"pfd_{fac['id']}.png")
            generate_process_overview_diagram(fname, pfd_path, language=language, active_modules=fac_mods)
            pfd_charts[fname] = pfd_path

        # Pass 1: compute exact heading page numbers for the Table of Contents
        pass1_elements = _assemble_document_story(
            data, charts, styles, pfd_charts=pfd_charts, lang=language, toc_pages=None, for_toc_pass=True
        )
        pass1_buf = io.BytesIO()
        pass1_doc = _MasterDocTemplate(
            pass1_buf,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
        )
        pass1_doc.build(pass1_elements)
        toc_map = dict(pass1_doc.toc_pages)

        # Pass 2: assemble fresh flowables with real TOC page numbers and period-lock-aware canvas
        elements = _assemble_document_story(
            data, charts, styles, pfd_charts=pfd_charts, lang=language, toc_pages=toc_map
        )
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
        )
        gov_ctx = data.get("governance") or {}
        doc.build(
            elements,
            canvasmaker=lambda *args, **kwargs: MasterReportNumberedCanvas(
                *args, language=language, governance=gov_ctx, **kwargs
            ),
        )

        pdf_bytes = buffer.getvalue()
        real_hash = hashlib.sha256(pdf_bytes).hexdigest()
        return MasterReportPdfBuffer(
            pdf_bytes,
            report_hash=real_hash,
            dataset_hash=data.get("dataset_sha256"),
        )


# Split modules (they import from this one, so they come last)
from services.master_report_engine_front import (  # noqa: F401,E402
    _build_benchmark_league_elements,
    _build_cover_elements,
    _build_geology_and_ops_elements,
    _build_glidepath_elements,
    _build_jv_equity_elements,
    _build_process_architecture_elements,
    _build_scorecard_elements,
    _build_signoff_elements,
)
from services.master_report_engine_chapters import (  # noqa: F401,E402
    _build_cbam_macc_elements,
    _build_chapter_with_chart,
    _build_decarbonization_projects_elements,
    _build_ogmp_elements,
    _build_scope3_elements,
)
