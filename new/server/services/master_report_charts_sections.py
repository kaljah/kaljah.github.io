"""Master report charts: OGMP reconciliation, Scope 3 categories, CBAM embeddings and the facility process
overview diagram (split from master_report_charts.py, which holds the cache, palette and Matplotlib setup)."""

import io
import matplotlib.pyplot as plt
import numpy as np
import textwrap
from typing import Any, Dict, List, Optional
from services.master_report_charts import (
    CHART_DPI,
    COLOR_BLUE,
    COLOR_BORDER,
    COLOR_DARK,
    COLOR_LIGHT_BG,
    COLOR_MUTED,
    COLOR_ORANGE,
    COLOR_PURPLE,
    COLOR_SLATE,
    COLOR_SUCCESS,
    COLOR_TEAL,
    COLOR_WARNING,
    _MAX_PFD_BASE_CACHE_ENTRIES,
    _PFD_BASE_CACHE,
    _PLOT_LOCK,
    _cached_render,
    _finalize_figure,
)
from PIL import Image as PILImage, ImageDraw, ImageFont
from matplotlib import font_manager, patches
from services.master_report_i18n import get_t


_PFD_FONT_CACHE: dict[int, Any] = {}


_PFD_FONT_PATH: str | None = None


def _render_empty_state_chart(ax, title: str, headline: str, subline: str) -> None:
    """Draws an honest non-fabricated empty-state notice canvas when no DB records exist."""
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_facecolor(COLOR_LIGHT_BG)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(COLOR_BORDER)
        spine.set_linestyle("--")
    ax.set_xticks([])
    ax.set_yticks([])
    box = patches.FancyBboxPatch(
        (0.08, 0.22),
        0.84,
        0.56,
        boxstyle="round,pad=0.03",
        facecolor="white",
        edgecolor=COLOR_BORDER,
        linestyle="--",
        linewidth=1.1,
    )
    ax.add_patch(box)
    ax.text(0.5, 0.58, headline, ha="center", va="center", fontsize=10.0, fontweight="bold", color=COLOR_SLATE)
    ax.text(0.5, 0.39, subline, ha="center", va="center", fontsize=8.0, color=COLOR_MUTED, parse_math=False)
    ax.set_title(title, fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)


def generate_ogmp_reconciliation_chart(
    ogmp_data: dict,
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Renders OGMP 2.0 Level 4 vs Level 5 Methane Reconciliation Chart (tCH4), or empty-state notice if unrecorded."""
    payload = {"ogmp": ogmp_data, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        is_fr = str(language).lower().startswith("fr")
        surveys = ogmp_data.get("surveys", [])

        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=dpi)
            try:
                if not surveys:
                    headline = (
                        "AUCUN RELEVÉ OGMP 2.0 DESCENDANT ENREGISTRÉ"
                        if is_fr else
                        "NO OGMP 2.0 TOP-DOWN SURVEYS RECORDED"
                    )
                    subline = (
                        "Aucune campagne aérienne, satellite ou OGI Niveau 4/5 trouvée\ndans la base de données pour ce périmètre et cette période."
                        if is_fr else
                        "No Level 4/5 aerial, satellite, or OGI reconciliation campaigns\nfound in database for this perimeter and reporting cycle."
                    )
                    _render_empty_state_chart(ax, get_t("chart_ogmp_title", language), headline, subline)
                else:
                    pts = surveys[:5]
                    labels = [f"{s.get('survey_type', 'Survey').split('(')[0].strip()}\n{s.get('year', '')}" for s in pts]
                    bu_vals = [s.get("bottom_up_tch4", 0.0) for s in pts]
                    td_vals = [s.get("top_down_tch4", 0.0) for s in pts]
                    x = np.arange(len(pts))
                    width = 0.35

                    lbl_bu = "Source Bottom-Up L4" if not is_fr else "Source Ascendante N4"
                    lbl_td = "Site Top-Down L5" if not is_fr else "Site Descendante N5"

                    ax.bar(x - width / 2, bu_vals, width, label=lbl_bu, color=COLOR_SLATE, alpha=0.9)
                    ax.bar(x + width / 2, td_vals, width, label=lbl_td, color=COLOR_TEAL, alpha=0.9)

                    ax.set_xticks(x)
                    ax.set_xticklabels(labels, fontsize=7.2, fontweight="bold", parse_math=False)

                    max_v = max(max(bu_vals + td_vals + [1.0]), 10.0)
                    ax.set_ylim(0, max_v * 1.35)

                    for i, s in enumerate(pts):
                        var = s.get("variance_pct", 0.0)
                        higher = max(bu_vals[i], td_vals[i])
                        var_color = COLOR_SUCCESS if abs(var) <= 20.0 else COLOR_WARNING
                        ax.text(x[i], higher + max_v * 0.03, f"Δ {var:+.1f}%", ha="center", va="bottom", fontsize=6.8, fontweight="bold", color=var_color)

                    ax.set_ylabel(get_t("chart_ogmp_axis", language), fontsize=8.5, fontweight="bold", color=COLOR_DARK)
                    ax.tick_params(axis="both", labelsize=7.5)
                    ax.grid(axis="y", linestyle="--", alpha=0.5)
                    ax.set_title(get_t("chart_ogmp_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)
                    ax.legend(loc="upper right", frameon=True, fontsize=7.2)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("ogmp", payload, out_path, _render, use_cache=use_cache)


def generate_scope3_category_chart(
    scope3_data: dict,
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Renders Scope 3 Category Breakdown Donut Chart, or empty-state notice if unrecorded."""
    payload = {"s3": scope3_data, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        is_fr = str(language).lower().startswith("fr")
        categories = scope3_data.get("categories", [])

        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=dpi)
            try:
                if not categories or scope3_data.get("total_period_co2e", 0.0) <= 0:
                    headline = (
                        "AUCUNE DONNÉE VÉRIFIÉE SCOPE 3 ENREGISTRÉE"
                        if is_fr else
                        "NO VERIFIED SCOPE 3 VALUE CHAIN RECORDS"
                    )
                    subline = (
                        "Aucune émission vérifiée Scope 3 (Catégories GHG Protocol 1–15)\nn'est enregistrée dans la base de données pour ce périmètre."
                        if is_fr else
                        "No Verified Scope 3 emissions (GHG Protocol Categories 1–15)\nrecorded in database for this reporting perimeter and period."
                    )
                    _render_empty_state_chart(ax, get_t("chart_scope3_title", language), headline, subline)
                else:
                    top_cats = categories[:5]
                    sizes = [c["co2e_t"] for c in top_cats]
                    other_sum = sum(c["co2e_t"] for c in categories[5:])
                    labels = [c["category_name"].split(":")[0] if ":" in c["category_name"] else c["category_name"][:18] for c in top_cats]
                    if other_sum > 0:
                        labels.append("Other Categories" if not is_fr else "Autres Catégories")
                        sizes.append(other_sum)
                    palette = [COLOR_BLUE, COLOR_TEAL, COLOR_ORANGE, COLOR_PURPLE, COLOR_WARNING, COLOR_SLATE][:len(sizes)]

                    wedges, texts, autotexts = ax.pie(
                        sizes,
                        labels=labels,
                        autopct="%1.1f%%",
                        startangle=140,
                        colors=palette,
                        pctdistance=0.75,
                        textprops=dict(color=COLOR_DARK, fontsize=7.2, fontweight="bold", parse_math=False),
                        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=1.5),
                    )
                    for at in autotexts:
                        at.set_fontsize(6.8)
                        at.set_color(COLOR_DARK)

                    total_val = scope3_data.get("total_period_co2e", sum(sizes))
                    center_text = f"Total Scope 3\n{total_val:,.0f} tCO2e" if not is_fr else f"Scope 3 Total\n{total_val:,.0f} tCO2e"
                    ax.text(0, 0, center_text, ha="center", va="center", fontsize=7.5, fontweight="bold", color=COLOR_DARK)
                    ax.set_title(get_t("chart_scope3_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("scope3", payload, out_path, _render, use_cache=use_cache)


def _wrap_cbam_product_name(raw_name: str) -> str:
    """Wraps long CBAM product labels onto two balanced lines without mid-word breaks."""
    clean = str(raw_name or "").strip()
    if "(" in clean and clean.index("(") > 4:
        idx = clean.index("(")
        first = clean[:idx].strip()
        rest = clean[idx:].strip()
        if len(first) <= 22 and len(rest) <= 24:
            return f"{first}\n{rest}"
    return textwrap.fill(clean, width=20)


def _plot_cbam_axes(ax, products: List[Dict[str, Any]], language: str) -> None:
    """Draws CBAM Direct vs Indirect specific embedded emissions bars or honest empty state."""
    is_fr = str(language).lower().startswith("fr")
    if not products:
        headline = (
            "AUCUN FLUX D'EXPORTATION MACF UE ENREGISTRÉ"
            if is_fr else
            "NO EU CBAM EXPORT STREAMS RECORDED"
        )
        subline = (
            "Aucune déclaration d'exportation soumise au Règlement (UE) 2023/956\nn'est enregistrée dans la base pour ce périmètre."
            if is_fr else
            "No EU CBAM (Regulation 2023/956) covered hydrocarbon exports\nrecorded in database for this perimeter and reporting cycle."
        )
        _render_empty_state_chart(ax, get_t("chart_cbam_title", language), headline, subline)
        return

    pts = products[:5]
    names = [_wrap_cbam_product_name(p["product_name"]) for p in pts]
    see_dir = [p["see_direct"] for p in pts]
    see_indir = [p["see_indirect"] for p in pts]

    x = np.arange(len(names))
    width = 0.45
    lbl_dir = "Direct Embedded (SEE Direct)" if not is_fr else "Émissions Spécifiques Directes"
    lbl_indir = "Indirect Electricity (SEE Indirect)" if not is_fr else "Électricité Indirecte"

    ax.bar(x, see_dir, width, label=lbl_dir, color=COLOR_BLUE, alpha=0.9)
    ax.bar(x, see_indir, width, bottom=see_dir, label=lbl_indir, color=COLOR_ORANGE, alpha=0.9)

    ax.set_ylabel(get_t("chart_cbam_axis", language), fontsize=8.0, fontweight="bold", color=COLOR_DARK)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=6.8, fontweight="bold", rotation=0, parse_math=False)
    ax.tick_params(axis="both", labelsize=7.5)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    totals = [d + i for d, i in zip(see_dir, see_indir)]
    max_tot = max(totals) if totals else 1.0
    ax.set_ylim(0, max(max_tot * 1.35, 0.1))

    for i, tot in enumerate(totals):
        if tot > 0:
            ax.text(x[i], tot + max(max_tot * 0.03, 0.005), f"{tot:.3f}", ha="center", va="bottom", fontsize=6.8, fontweight="bold", color=COLOR_DARK)

    ax.set_title(get_t("chart_cbam_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)
    ax.legend(loc="upper right", frameon=True, fontsize=7.2)


def generate_cbam_embeddings_chart(
    cbam_data: dict,
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Renders EU CBAM Specific Embedded Emissions (SEE Direct vs Indirect), or empty-state notice if unrecorded."""
    payload = {"cbam": cbam_data, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        products = cbam_data.get("products", [])
        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=dpi)
            try:
                _plot_cbam_axes(ax, products, language)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("cbam", payload, out_path, _render, use_cache=use_cache)


def _get_pfd_font(size_px: int) -> Any:
    global _PFD_FONT_PATH
    with _PLOT_LOCK:
        if size_px in _PFD_FONT_CACHE:
            return _PFD_FONT_CACHE[size_px]
        if _PFD_FONT_PATH is None:
            _PFD_FONT_PATH = font_manager.findfont(
                font_manager.FontProperties(family="DejaVu Sans", weight="bold")
            )
        font = ImageFont.truetype(_PFD_FONT_PATH, size_px)
        _PFD_FONT_CACHE[size_px] = font
        return font


def _get_pfd_base_template(
    lang_key: str,
    dpi: int,
    active_tuple: tuple[str, ...] = (),
    has_filter: Optional[bool] = None,
) -> tuple[PILImage.Image, float, float]:
    """Renders the CPF PFD diagram template once per (language, dpi, filter-state, active_tuple) using a bounded LRU."""
    eff_filter = bool(active_tuple) if has_filter is None else bool(has_filter)
    cache_key = (lang_key, dpi, eff_filter, active_tuple)
    with _PLOT_LOCK:
        cached = _PFD_BASE_CACHE.get(cache_key)
        if cached is not None:
            _PFD_BASE_CACHE.move_to_end(cache_key)
            return cached[0].copy(), cached[1], cached[2]

        fig, ax = plt.subplots(figsize=(8.5, 4.2), dpi=dpi)
        try:
            ax.set_xlim(0, 100)
            ax.set_ylim(0, 50)
            ax.axis("off")

            is_fr = lang_key.startswith("fr")
            active_set = set(active_tuple)
            has_filter = eff_filter
            ax.text(50, 47, "X", ha="center", va="center", fontsize=10.5, fontweight="bold", alpha=0.0)

            fence = patches.Rectangle((3, 3), 94, 41, fill=False, edgecolor=COLOR_MUTED, linestyle="--", linewidth=0.8)
            ax.add_patch(fence)
            ax.text(5, 42, "CPF FENCE LINE" if not is_fr else "LIMITE DE L'INSTALLATION CPF", fontsize=6.5, fontweight="bold", color=COLOR_MUTED)
            illus_lbl = (
                "Schéma de Principe Illustratif (Blocs grisés = non déclarés en base)"
                if (is_fr and has_filter) else
                ("Schéma de Principe Illustratif" if is_fr else
                 ("Illustrative Block Flow Diagram (Grey = not logged in DB)" if has_filter else "Illustrative Block Flow Diagram"))
            )
            ax.text(95, 42, illus_lbl, ha="right", fontsize=5.8, style="italic", color=COLOR_MUTED)

            blocks = [
                (5, 18, 14, 11, "Wellhead Gathering\n& FGS Manifolds" if not is_fr else "Collecte Puits\n& Manifolds FGS", "#0284C7", None),
                (23, 18, 15, 11, "Inlet Separation\n(HP / IP Trains)" if not is_fr else "Séparation Entrée\n(Trains HP / MP)", "#0D9488", None),
                (42, 18, 16, 11, "Oil Desalting &\nStabilization Tower" if not is_fr else "Dessalage & Colonne\nde Stabilisation", "#059669", ("tank", "combustion", "flare")),
                (62, 18, 15, 11, "Crude / Condensate\nStorage Tanks" if not is_fr else "Stockage Brut &\nCondensats", "#10B981", ("tank",)),
                (81, 18, 15, 11, "LACT Custody &\nExport Pipeline" if not is_fr else "Comptage LACT &\nExport Pipeline", "#047857", None),
                (23, 32, 15, 9, "Gas Compression\n(BGC / AGC / RGC)" if not is_fr else "Compression Gaz\n(BGC / AGC / RGC)", "#D97706", ("compression", "combustion", "flare")),
                (42, 32, 16, 9, "Glycol / Mole Sieve\nDehydration Unit" if not is_fr else "Unité Déshydratation\n(Glycol / Tamis)", "#B45309", ("dehydration",)),
                (62, 32, 15, 9, "High-Pressure Gas\nReinjection Network" if not is_fr else "Réseau Réinjection\nGaz Haute Pression", "#92400E", ("reinjection",)),
                (42, 5, 16, 9, "Produced Water\nTreatment System" if not is_fr else "Traitement des\nEaux de Production", "#64748B", ("water",)),
                (62, 5, 15, 9, "Water Injection\nWells & Pumps" if not is_fr else "Puits & Pompes\nInjection d'Eau", "#475569", ("water",)),
                (81, 5, 15, 9, "Flaring System\n(HP/LP Smokeless)" if not is_fr else "Système Torches\n(HP/MP Sans Fumée)", "#DC2626", ("flare",)),
                (81, 32, 15, 9, "Gas Turbines &\nPower Generation" if not is_fr else "Turbines à Gaz &\nProduction Élec.", "#7C3AED", ("combustion", "scope2")),
            ]

            for x, y, w, h, label, bg, req_mods in blocks:
                is_active = (not has_filter) or (req_mods is None) or any(m in active_set for m in req_mods)
                face_c = bg if is_active else "#E2E8F0"
                edge_c = COLOR_DARK if is_active else "#94A3B8"
                ls = "-" if is_active else "--"
                txt_c = "white" if is_active else "#475569"
                disp_lbl = label if is_active else f"{label}\n[N/D]" if is_fr else f"{label}\n[Not Logged]"
                rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3", facecolor=face_c, edgecolor=edge_c, linestyle=ls, linewidth=0.8, zorder=2)
                ax.add_patch(rect)
                ax.text(x + w / 2, y + h / 2, disp_lbl, ha="center", va="center", color=txt_c, fontsize=5.9 if not is_active else 6.2, fontweight="bold", zorder=4)

            arrows = [
                ((19, 23.5), (23, 23.5)),
                ((38, 23.5), (42, 23.5)),
                ((58, 23.5), (62, 23.5)),
                ((77, 23.5), (81, 23.5)),
                ((30.5, 29), (30.5, 32)),
                ((38, 36.5), (42, 36.5)),
                ((58, 36.5), (62, 36.5)),
                ((77, 36.5), (81, 36.5)),
                ((50, 18), (50, 14)),
                ((58, 9.5), (62, 9.5)),
                ((77, 9.5), (81, 9.5)),
            ]
            for start, end in arrows:
                ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="->", color=COLOR_DARK, lw=1.2), zorder=1)

            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=dpi)
            img_w, img_h = fig.canvas.get_width_height()
            disp_x, disp_y = ax.transData.transform((50, 47))
            title_x = float(disp_x)
            title_y = float(img_h - disp_y)
            buf.seek(0)
            with PILImage.open(buf) as loaded:
                base_img = loaded.convert("RGB")
            _PFD_BASE_CACHE[cache_key] = (base_img, title_x, title_y)
            while len(_PFD_BASE_CACHE) > _MAX_PFD_BASE_CACHE_ENTRIES:
                _PFD_BASE_CACHE.popitem(last=False)
            return base_img.copy(), title_x, title_y
        finally:
            fig.clear()
            plt.close(fig)


def generate_process_overview_diagram(
    facility_name: str,
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
    active_modules: Optional[List[str]] = None,
):
    """Renders a 150-DPI Process Flow Diagram (PFD) for a facility."""
    has_filter = active_modules is not None
    active_tuple = tuple(sorted({str(m).strip().lower() for m in (active_modules or []) if m}))
    payload = {
        "facility_name": facility_name,
        "lang": language,
        "dpi": dpi,
        "has_filter": has_filter,
        "active": active_tuple,
    }

    def _render(target_path: str) -> None:
        lang_norm = str(language or "en").lower()
        lang_key = "fr" if lang_norm.startswith("fr") else "en"
        is_fr = lang_key == "fr"
        title_suffix = "Architecture des Procédés CPF (Schéma Illustratif)" if is_fr else "CPF Process Architecture (Illustrative Block Flow)"
        title_text = f"{facility_name} - {title_suffix}"

        base_img, title_x, title_y = _get_pfd_base_template(
            lang_key,
            dpi,
            active_tuple=active_tuple,
            has_filter=has_filter,
        )
        base_px = max(10, round(10.5 * dpi / 72.0))
        font = _get_pfd_font(base_px)
        draw = ImageDraw.Draw(base_img)
        bbox = draw.textbbox((0, 0), title_text, font=font)
        text_w = bbox[2] - bbox[0]
        max_w = max(200, base_img.width - 36)
        if text_w > max_w and text_w > 0:
            scaled_px = max(9, int(base_px * (max_w / text_w)))
            font = _get_pfd_font(scaled_px)
        draw.text((title_x, title_y), title_text, fill=COLOR_DARK, font=font, anchor="mm")
        base_img.save(target_path, format="PNG", compress_level=1)

    _cached_render("pfd", payload, out_path, _render, use_cache=use_cache)
