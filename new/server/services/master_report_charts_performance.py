"""Master report charts: carbon / methane intensities, criteria pollutants, the 2030 glidepath and JV equity
(split from master_report_charts.py, which holds the cache, palette and Matplotlib setup)."""

import matplotlib.pyplot as plt
import numpy as np
from typing import Any, Dict, List
from services.master_report_charts import (
    CHART_DPI,
    COLOR_BLUE,
    COLOR_DANGER,
    COLOR_DARK,
    COLOR_ORANGE,
    COLOR_PURPLE,
    COLOR_SLATE,
    COLOR_TEAL,
    COLOR_WARNING,
    _PLOT_LOCK,
    _cached_render,
    _finalize_figure,
)
from services.master_report_i18n import get_t


def _plot_intensities_axes(
    ax1,
    years: List[int],
    carbon_intensity_kg_boe: List[float],
    methane_intensity_pct: List[float],
    language: str = "en",
) -> None:
    x = np.arange(len(years))

    lbl_ci = get_t("chart_int_ci_lbl", language)
    lbl_mi = get_t("chart_int_mi_lbl", language)
    ax1.plot(x, carbon_intensity_kg_boe, color=COLOR_ORANGE, marker="o", linewidth=2.2, markersize=5.5, label=lbl_ci)
    ax1.set_ylabel(get_t("chart_int_ci_axis", language), color=COLOR_ORANGE, fontsize=8.5, fontweight="bold")
    ax1.tick_params(axis="y", labelcolor=COLOR_ORANGE, labelsize=8)
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(y) for y in years], fontsize=8.5, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.5)

    if len(years) == 1:
        ax1.set_xlim(-0.6, 0.6)
    max_ci = max(carbon_intensity_kg_boe) if carbon_intensity_kg_boe else 0.0
    ax1.set_ylim(bottom=0, top=max(max_ci * 1.38, 5.0))

    for i, v in enumerate(carbon_intensity_kg_boe):
        ax1.text(x[i], v + max(max_ci * 0.025, 0.2), f"{v:.1f}", ha="center", va="bottom", fontsize=7, color=COLOR_ORANGE, fontweight="bold")

    ax2 = ax1.twinx()
    ax2.plot(x, methane_intensity_pct, color=COLOR_TEAL, marker="^", linewidth=2.2, markersize=5.5, label=lbl_mi)
    ax2.axhline(0.20, color="#0F766E", linestyle="--", linewidth=1.2, label=get_t("chart_int_ogci_lbl", language))
    ax2.set_ylabel(get_t("chart_int_mi_axis", language), color=COLOR_TEAL, fontsize=8.5, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=COLOR_TEAL, labelsize=8)

    max_mi = max(methane_intensity_pct) if methane_intensity_pct else 0.0
    ax2.set_ylim(bottom=0, top=max(max_mi * 1.42, 0.35))

    for i, v in enumerate(methane_intensity_pct):
        ax2.text(x[i], v + max(max_mi * 0.03, 0.005), f"{v:.3f}%", ha="center", va="bottom", fontsize=7, color=COLOR_TEAL, fontweight="bold")

    ax1.set_title(get_t("chart_int_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=6.6, frameon=True)


def _plot_criteria_pollutants_axes(
    ax,
    years: List[int],
    nox_t: List[float],
    co_t: List[float],
    so2_t: List[float],
    voc_t: List[float],
    language: str = "en",
) -> None:
    x = np.arange(len(years))
    width = 0.2

    is_fr = str(language).lower().startswith("fr")
    lbl_nox = "Oxydes d'azote (NOx)" if is_fr else "Nitrogen Oxides (NOx)"
    lbl_co = "Monoxyde de carbone (CO)" if is_fr else "Carbon Monoxide (CO)"
    lbl_so2 = "Dioxyde de soufre (SO₂)" if is_fr else "Sulfur Dioxide (SO₂)"
    lbl_voc = "Composés organiques volatils (COVNM)" if is_fr else "Volatile Organics (VOC)"

    ax.bar(x - 1.5 * width, nox_t, width, label=lbl_nox, color="#2563EB", alpha=0.9)
    ax.bar(x - 0.5 * width, co_t, width, label=lbl_co, color="#D97706", alpha=0.9)
    ax.bar(x + 0.5 * width, so2_t, width, label=lbl_so2, color="#DC2626", alpha=0.9)
    ax.bar(x + 1.5 * width, voc_t, width, label=lbl_voc, color="#059669", alpha=0.9)

    ax.set_ylabel(get_t("chart_poll_axis", language), fontsize=8.5, fontweight="bold", color=COLOR_DARK)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years], fontsize=8.5, fontweight="bold")
    ax.tick_params(axis="both", labelsize=8)
    ax.legend(loc="upper right", frameon=True, fontsize=7.0)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    if len(years) == 1:
        ax.set_xlim(-0.65, 0.65)
    max_p = max(max(nox_t, default=0), max(co_t, default=0), max(so2_t, default=0), max(voc_t, default=0))
    ax.set_ylim(bottom=0, top=max(max_p * 1.38, 1.0))
    ax.set_title(get_t("chart_poll_title", language), fontsize=9.0, fontweight="bold", pad=10, color=COLOR_DARK)


def _plot_glidepath_axes(ax, target_projection: Dict[str, Any], language: str = "en") -> None:
    hist_years = target_projection.get("historical_years", [])
    hist_ghg = target_projection.get("historical_ghg_mmt", [])
    proj_years = target_projection.get("proj_years", [])
    glidepath = target_projection.get("glidepath_mmt", [])
    target_2030 = target_projection.get("target_2030_ghg_mmt", 0.0)

    if hist_years and hist_ghg:
        lbl_hist = get_t("chart_glide_hist_lbl", language)
        ax.plot(hist_years, hist_ghg, color=COLOR_BLUE, marker="o", linewidth=2.4, markersize=5.0, label=lbl_hist)
        for y, val in zip(hist_years, hist_ghg):
            ax.text(y, val + max(max(hist_ghg) * 0.025, 0.01), f"{val:.2f}", ha="center", va="bottom", fontsize=6.8, fontweight="bold", color=COLOR_BLUE)

    if proj_years and glidepath:
        pct_val = f"{float(target_projection.get('target_reduction_pct', 20.0)):.1f}"
        lbl_target = get_t("chart_glide_target_lbl", language, pct=pct_val)
        ax.plot(proj_years, glidepath, color=COLOR_ORANGE, marker="s", linestyle="--", linewidth=2.2, markersize=4.8, label=lbl_target)
        ax.fill_between(proj_years, glidepath, alpha=0.12, color=COLOR_ORANGE, label=get_t("chart_glide_envelope_lbl", language))
        for y, val in zip(proj_years[1:], glidepath[1:]):
            ax.text(y, val - max(max(glidepath) * 0.04, 0.02), f"{val:.2f}", ha="center", va="top", fontsize=6.5, color=COLOR_ORANGE, fontweight="bold")

    lbl_point = get_t("chart_glide_point_lbl", language)
    ax.scatter([2030], [target_2030], color=COLOR_DANGER, s=65, zorder=6, label=lbl_point)

    all_years = sorted(list(set(hist_years + proj_years)))
    ax.set_xticks(all_years)
    ax.set_xticklabels([str(y) for y in all_years], fontsize=7.5, fontweight="bold")
    ax.set_ylabel(get_t("chart_glide_axis", language), fontsize=8.5, fontweight="bold", color=COLOR_DARK)
    ax.grid(True, linestyle="--", alpha=0.5)

    all_vals = (hist_ghg or []) + (glidepath or [])
    max_val = max(all_vals) if all_vals else 1.0
    ax.set_ylim(bottom=0, top=max(max_val * 1.3, 0.1))

    ax.set_title(get_t("chart_glide_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)
    ax.legend(loc="upper right", fontsize=6.8, frameon=True)


def _plot_jv_equity_axes(ax, jv_equity: Any, language: str = "en") -> None:
    if isinstance(jv_equity, dict):
        annual = jv_equity.get("annual_equity_timeline", [])
        partners = jv_equity.get("partners", [])
    elif isinstance(jv_equity, list):
        partners = jv_equity
        annual = []
    else:
        annual, partners = [], []

    if not annual or not partners:
        ax.set_title(get_t("chart_jv_title", language), fontsize=9.5, fontweight="bold", color=COLOR_DARK)
        return

    years = [a["year"] for a in annual]
    x = np.arange(len(years))
    width = 0.42

    palette = [COLOR_ORANGE, COLOR_BLUE, COLOR_TEAL, COLOR_PURPLE, COLOR_WARNING, COLOR_SLATE]
    bottom = np.zeros(len(years))

    for idx, p in enumerate(partners):
        p_code = p.get("partner_code", p.get("code", "SH"))
        p_name = p.get("partner_name", p.get("partner", "Operator"))
        pct = p.get("equity_share_pct", p.get("share_pct", 100.0))
        c = palette[idx % len(palette)]
        vals_mmt = []
        for a in annual:
            p_data = a.get("partner_emissions", {}).get(p_code, {})
            tot_ghg = p_data.get("total_ghg_tco2e", p_data.get("total_ghg", 0.0))
            vals_mmt.append(tot_ghg / 1_000_000.0)
        vals_arr = np.array(vals_mmt)
        label = f"{p_name} ({pct:.1f}%)"
        ax.bar(x, vals_arr, width, bottom=bottom, label=label, color=c, alpha=0.9)
        bottom += vals_arr

    ax.set_ylabel(get_t("chart_jv_axis", language), fontsize=8.5, fontweight="bold", color=COLOR_DARK)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years], fontsize=8.0, fontweight="bold")
    ax.tick_params(axis="both", labelsize=7.5)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    max_tot = max(bottom) if len(bottom) > 0 else 0.0
    ax.set_ylim(bottom=0, top=max(max_tot * 1.42, 0.01))

    for i in range(len(years)):
        tot = bottom[i]
        if tot > 0:
            ax.text(x[i], tot + max(max_tot * 0.02, 0.001), f"{tot:,.3f} MMt", ha="center", va="bottom", fontsize=7.0, fontweight="bold", color=COLOR_DARK)

    ax.set_title(get_t("chart_jv_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)
    ax.legend(loc="upper right", frameon=True, fontsize=6.8, ncol=min(len(partners), 2))


def generate_intensities_chart(
    years: List[int],
    carbon_intensity_kg_boe: List[float],
    methane_intensity_pct: List[float],
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Dual-axis trajectory of Carbon Intensity (kg CO2e/BOE) & Methane Intensity (NGSI wt.%)."""
    payload = {"years": years, "ci": carbon_intensity_kg_boe, "mi": methane_intensity_pct, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, ax1 = plt.subplots(figsize=(7.2, 3.2), dpi=dpi)
            try:
                _plot_intensities_axes(ax1, years, carbon_intensity_kg_boe, methane_intensity_pct, language)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("intensities", payload, out_path, _render, use_cache=use_cache)


def generate_criteria_pollutants_chart(
    years: List[int],
    nox_t: List[float],
    co_t: List[float],
    so2_t: List[float],
    voc_t: List[float],
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Grouped bar chart for Criteria Air Pollutants mass (NOx, CO, SO2, VOC)."""
    payload = {"years": years, "nox": nox_t, "co": co_t, "so2": so2_t, "voc": voc_t, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=dpi)
            try:
                _plot_criteria_pollutants_axes(ax, years, nox_t, co_t, so2_t, voc_t, language)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("pollutants", payload, out_path, _render, use_cache=use_cache)


def generate_intensities_pollutants_panel_chart(
    years: List[int],
    carbon_intensity_kg_boe: List[float],
    methane_intensity_pct: List[float],
    nox_t: List[float],
    co_t: List[float],
    so2_t: List[float],
    voc_t: List[float],
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Consolidated 2-panel figure merging Intensities and Criteria Air Pollutants."""
    payload = {
        "years": years,
        "ci": carbon_intensity_kg_boe,
        "mi": methane_intensity_pct,
        "nox": nox_t,
        "co": co_t,
        "so2": so2_t,
        "voc": voc_t,
        "lang": language,
        "dpi": dpi,
    }

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.2, 3.2), dpi=dpi)
            try:
                _plot_intensities_axes(ax1, years, carbon_intensity_kg_boe, methane_intensity_pct, language)
                _plot_criteria_pollutants_axes(ax2, years, nox_t, co_t, so2_t, voc_t, language)
                _finalize_figure(fig, target_path, dpi=dpi, w_pad=3.4)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("int_poll_panel", payload, out_path, _render, use_cache=use_cache)


def generate_2030_glidepath_chart(
    target_projection: Dict[str, Any],
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Visualizes the 2030 corporate decarbonization trajectory, historical emissions, and milestone glidepath."""
    payload = {"target": target_projection, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=dpi)
            try:
                _plot_glidepath_axes(ax, target_projection, language)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("glidepath", payload, out_path, _render, use_cache=use_cache)


def generate_jv_equity_chart(
    jv_equity: Any,
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Visualizes JV Partner Equity Share allocation across the multi-year reporting timeline."""
    payload = {"jv": jv_equity, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=dpi)
            try:
                _plot_jv_equity_axes(ax, jv_equity, language)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("jv_equity", payload, out_path, _render, use_cache=use_cache)


def generate_glidepath_jv_panel_chart(
    target_projection: Dict[str, Any],
    jv_equity: Any,
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Consolidated 2-panel figure merging 2030 Decarbonization Glidepath and JV Partner Equity."""
    payload = {"target": target_projection, "jv": jv_equity, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.2, 3.2), dpi=dpi)
            try:
                _plot_glidepath_axes(ax1, target_projection, language)
                _plot_jv_equity_axes(ax2, jv_equity, language)
                _finalize_figure(fig, target_path, dpi=dpi, w_pad=3.2)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("glide_jv_panel", payload, out_path, _render, use_cache=use_cache)
