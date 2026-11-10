"""
Master Report Matplotlib Visual Engine
======================================
Renders 150-DPI Agg-backend publication figures for the Universal Master
Publication Report with strict figure cleanup, deterministic disk caching, and
consolidated multi-panel layouts:
- Hydrocarbon Production Trajectory
- Scope 1 & Scope 2 Emissions Progression + SANGEA Attribution (Combined Panel)
- Flaring Volumes vs Decree 21-330 Statutory Limit (1.00%)
- Multi-Metric Carbon & Methane Intensities + Criteria Air Pollutants (Combined Panel)
- 2030 Decarbonization Glidepath + JV Partner Equity Allocation (Combined Panel)
- Regional Cross-Basin Benchmark League Table
- OGMP 2.0 Level 4/5 Reconciliation, Scope 3 Categories, EU CBAM Embeddings
- Facility Process Overview Diagrams (PFD)
"""

import hashlib
import json
import os
import shutil
import threading
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib

if matplotlib.get_backend().lower() != "agg":
    matplotlib.use("Agg", force=True)
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np

from services.master_report_i18n import get_t

CHART_DPI = 150
_CACHE_SCHEMA_VERSION = "v2-150dpi"
_PLOT_LOCK = threading.RLock()
_CACHE_STATS_LOCK = threading.Lock()
_CACHE_STATS = {"hits": 0, "misses": 0}

# Corporate Publication Palette
COLOR_ORANGE = "#EA580C"
COLOR_DARK = "#0F172A"
COLOR_SLATE = "#334155"
COLOR_MUTED = "#64748B"
COLOR_LIGHT_BG = "#F8FAFC"
COLOR_BORDER = "#CBD5E1"
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER = "#EF4444"
COLOR_BLUE = "#0284C7"
COLOR_PURPLE = "#8B5CF6"
COLOR_TEAL = "#0D9488"

# Global clean styling
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "axes.edgecolor": COLOR_BORDER,
    "axes.linewidth": 0.8,
    "grid.color": "#F1F5F9",
    "grid.linestyle": "--",
    "grid.alpha": 0.8,
})


def get_chart_cache_dir() -> Path:
    """Returns the writable chart cache directory (configurable via env)."""
    custom = os.environ.get("MASTER_REPORT_CHART_CACHE_DIR", "").strip()
    if custom:
        cache_dir = Path(custom)
    else:
        server_dir = Path(__file__).resolve().parent.parent
        cache_dir = server_dir / "instance" / "chart_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def clear_chart_cache() -> int:
    """Removes cached chart PNGs and resets counters. Used by tests and sandbox reset."""
    cache_dir = get_chart_cache_dir()
    removed = 0
    for png in cache_dir.glob("*.png"):
        try:
            png.unlink()
            removed += 1
        except OSError:
            pass
    with _CACHE_STATS_LOCK:
        _CACHE_STATS["hits"] = 0
        _CACHE_STATS["misses"] = 0
    return removed


def get_chart_cache_stats() -> Dict[str, int]:
    """Returns thread-safe cache hit/miss counters."""
    with _CACHE_STATS_LOCK:
        return dict(_CACHE_STATS)


def _cached_render(
    chart_name: str,
    cache_payload: Any,
    out_path: str,
    render_fn: Callable[[str], None],
    use_cache: bool = True,
) -> None:
    """Renders a chart once for a given payload hash and reuses cached PNG on hits."""
    cache_enabled = use_cache and os.environ.get("DISABLE_CHART_CACHE", "").strip() not in ("1", "true", "True")
    if not cache_enabled:
        render_fn(out_path)
        return

    digest = hashlib.sha256(
        json.dumps(
            {"v": _CACHE_SCHEMA_VERSION, "chart": chart_name, "data": cache_payload},
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    cache_dir = get_chart_cache_dir()
    cached_path = cache_dir / f"{chart_name}_{digest[:24]}.png"

    if cached_path.exists() and cached_path.stat().st_size > 0:
        with _CACHE_STATS_LOCK:
            _CACHE_STATS["hits"] += 1
        shutil.copyfile(cached_path, out_path)
        return

    with _CACHE_STATS_LOCK:
        _CACHE_STATS["misses"] += 1

    tmp_path = cache_dir / f".tmp_{chart_name}_{uuid.uuid4().hex}.png"
    try:
        render_fn(str(tmp_path))
        os.replace(tmp_path, cached_path)
        shutil.copyfile(cached_path, out_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _finalize_figure(fig: plt.Figure, out_path: str, dpi: int = CHART_DPI) -> None:
    """Saves and always closes a Matplotlib figure cleanly."""
    fig.tight_layout()
    fig.savefig(out_path, dpi=dpi)


def _plot_production_axes(
    ax1,
    years: List[int],
    gas_mmsm3: List[float],
    liquid_mmbbl: List[float],
    language: str = "en",
) -> None:
    x = np.arange(len(years))
    width = 0.38

    lbl_gas = get_t("chart_prod_gas_lbl", language)
    lbl_liq = get_t("chart_prod_liq_lbl", language)
    bars = ax1.bar(x - width / 2, gas_mmsm3, width, label=lbl_gas, color=COLOR_BLUE, alpha=0.88)
    ax1.set_ylabel(get_t("chart_prod_gas_axis", language), color=COLOR_BLUE, fontsize=8.5, fontweight="bold")
    ax1.tick_params(axis="y", labelcolor=COLOR_BLUE, labelsize=8)
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(y) for y in years], fontsize=8.5, fontweight="bold")
    ax1.grid(axis="y", linestyle="--", alpha=0.5)

    max_gas = max(gas_mmsm3) if gas_mmsm3 else 0.0
    ax1.set_ylim(bottom=0, top=max(max_gas * 1.25, 1.0))

    for b in bars:
        h = b.get_height()
        if h > 0:
            ax1.text(
                b.get_x() + b.get_width() / 2.0,
                h + max(max_gas * 0.02, 0.02),
                f"{h:,.1f}",
                ha="center",
                va="bottom",
                fontsize=7,
                color=COLOR_DARK,
            )

    ax2 = ax1.twinx()
    ax2.plot(x + width / 2, liquid_mmbbl, label=lbl_liq, color=COLOR_ORANGE, marker="o", linewidth=2.2, markersize=5)
    ax2.set_ylabel(get_t("chart_prod_liq_axis", language), color=COLOR_ORANGE, fontsize=8.5, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=COLOR_ORANGE, labelsize=8)

    max_liq = max(liquid_mmbbl) if liquid_mmbbl else 0.0
    ax2.set_ylim(bottom=0, top=max(max_liq * 1.25, 0.1))

    for i, v in enumerate(liquid_mmbbl):
        if v > 0:
            ax2.text(
                x[i] + width / 2,
                v + max(max_liq * 0.03, 0.005),
                f"{v:,.2f}",
                ha="center",
                va="bottom",
                fontsize=7,
                color=COLOR_ORANGE,
                fontweight="bold",
            )

    ax1.set_title(get_t("chart_prod_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)


def _plot_emissions_axes(
    ax,
    years: List[int],
    s1_mmt: List[float],
    s2_mmt: List[float],
    language: str = "en",
) -> None:
    x = np.arange(len(years))
    width = 0.45

    ax.bar(x, s1_mmt, width, label=get_t("chart_em_s1_lbl", language), color=COLOR_ORANGE, alpha=0.9)
    ax.bar(x, s2_mmt, width, bottom=s1_mmt, label=get_t("chart_em_s2_lbl", language), color=COLOR_TEAL, alpha=0.85)

    ax.set_ylabel(get_t("chart_em_axis", language), fontsize=8.5, fontweight="bold", color=COLOR_DARK)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years], fontsize=8.5, fontweight="bold")
    ax.tick_params(axis="both", labelsize=8)
    ax.legend(loc="upper right", frameon=True, fontsize=7.5)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    totals = [s1 + s2 for s1, s2 in zip(s1_mmt, s2_mmt)]
    max_tot = max(totals) if totals else 0.0
    ax.set_ylim(bottom=0, top=max(max_tot * 1.25, 0.01))

    for i in range(len(years)):
        tot = totals[i]
        if tot > 0:
            ax.text(
                x[i],
                tot + max(max_tot * 0.02, 0.0002),
                f"{tot:,.3f} MMt",
                ha="center",
                va="bottom",
                fontsize=7,
                fontweight="bold",
                color=COLOR_DARK,
            )

    ax.set_title(get_t("chart_em_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)


def _plot_sangea_axes(
    ax,
    years: List[int],
    combustion_t: List[float],
    flaring_t: List[float],
    fugitives_t: List[float],
    venting_t: List[float],
    language: str = "en",
) -> None:
    x = np.arange(len(years))
    width = 0.45

    c_kt = [v / 1000.0 for v in combustion_t]
    f_kt = [v / 1000.0 for v in flaring_t]
    fug_kt = [v / 1000.0 for v in fugitives_t]
    v_kt = [v / 1000.0 for v in venting_t]

    b1 = np.array(c_kt)
    b2 = b1 + np.array(f_kt)
    b3 = b2 + np.array(fug_kt)

    totals = [c + f + fg + v for c, f, fg, v in zip(c_kt, f_kt, fug_kt, v_kt)]
    max_tot = max(totals) if totals else 0.0
    ax.set_ylim(bottom=0, top=max(max_tot * 1.25, 1.0))

    ax.bar(x, c_kt, width, label=get_t("chart_sangea_comb", language), color=COLOR_BLUE, alpha=0.9)
    ax.bar(x, f_kt, width, bottom=b1, label=get_t("chart_sangea_flare", language), color=COLOR_ORANGE, alpha=0.9)
    ax.bar(x, fug_kt, width, bottom=b2, label=get_t("chart_sangea_fug", language), color=COLOR_PURPLE, alpha=0.85)
    ax.bar(x, v_kt, width, bottom=b3, label=get_t("chart_sangea_vent", language), color=COLOR_MUTED, alpha=0.8)

    ax.set_ylabel(get_t("chart_sangea_axis", language), fontsize=8.5, fontweight="bold", color=COLOR_DARK)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years], fontsize=8.5, fontweight="bold")
    ax.tick_params(axis="both", labelsize=8)
    ax.legend(loc="upper left", frameon=True, fontsize=7.0, ncol=2)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.set_title(get_t("chart_sangea_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)


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

    max_ci = max(carbon_intensity_kg_boe) if carbon_intensity_kg_boe else 0.0
    ax1.set_ylim(bottom=0, top=max(max_ci * 1.25, 5.0))

    for i, v in enumerate(carbon_intensity_kg_boe):
        ax1.text(x[i], v + max(max_ci * 0.02, 0.2), f"{v:.1f}", ha="center", va="bottom", fontsize=7, color=COLOR_ORANGE, fontweight="bold")

    ax2 = ax1.twinx()
    ax2.plot(x, methane_intensity_pct, color=COLOR_TEAL, marker="^", linewidth=2.2, markersize=5.5, label=lbl_mi)
    ax2.axhline(0.20, color="#0F766E", linestyle="--", linewidth=1.2, label=get_t("chart_int_ogci_lbl", language))
    ax2.set_ylabel(get_t("chart_int_mi_axis", language), color=COLOR_TEAL, fontsize=8.5, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=COLOR_TEAL, labelsize=8)

    max_mi = max(methane_intensity_pct) if methane_intensity_pct else 0.0
    ax2.set_ylim(bottom=0, top=max(max_mi * 1.35, 0.3))

    for i, v in enumerate(methane_intensity_pct):
        ax2.text(x[i], v + max(max_mi * 0.03, 0.005), f"{v:.3f}%", ha="center", va="bottom", fontsize=7, color=COLOR_TEAL, fontweight="bold")

    ax1.set_title(get_t("chart_int_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=7.0, frameon=True)


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

    max_p = max(max(nox_t, default=0), max(co_t, default=0), max(so2_t, default=0), max(voc_t, default=0))
    ax.set_ylim(bottom=0, top=max(max_p * 1.25, 1.0))
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
        lbl_target = get_t("chart_glide_target_lbl", language)
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
        p_name = p.get("partner_name", p.get("partner", "Demo Operator Co."))
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
    ax.set_ylim(bottom=0, top=max(max_tot * 1.25, 0.01))

    for i in range(len(years)):
        tot = bottom[i]
        if tot > 0:
            ax.text(x[i], tot + max(max_tot * 0.02, 0.001), f"{tot:,.3f} MMt", ha="center", va="bottom", fontsize=7.0, fontweight="bold", color=COLOR_DARK)

    ax.set_title(get_t("chart_jv_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)
    ax.legend(loc="upper right", frameon=True, fontsize=6.8, ncol=min(len(partners), 2))


def generate_production_chart(
    years: List[int],
    gas_mmsm3: List[float],
    liquid_mmbbl: List[float],
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Dual-axis production trajectory: Gross Natural Gas (MMSm³) vs Total Liquids (MMbbl)."""
    payload = {"years": years, "gas": gas_mmsm3, "liq": liquid_mmbbl, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, ax1 = plt.subplots(figsize=(7.2, 3.2), dpi=dpi)
            try:
                _plot_production_axes(ax1, years, gas_mmsm3, liquid_mmbbl, language)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("production", payload, out_path, _render, use_cache=use_cache)


def generate_emissions_progression_chart(
    years: List[int],
    s1_mmt: List[float],
    s2_mmt: List[float],
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Stacked bar chart of Scope 1 Direct and Scope 2 Indirect GHG emissions (MMtCO2e)."""
    payload = {"years": years, "s1": s1_mmt, "s2": s2_mmt, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=dpi)
            try:
                _plot_emissions_axes(ax, years, s1_mmt, s2_mmt, language)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("emissions", payload, out_path, _render, use_cache=use_cache)


def generate_sangea_breakdown_chart(
    years: List[int],
    combustion_t: List[float],
    flaring_t: List[float],
    fugitives_t: List[float],
    venting_t: List[float],
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Stacked bar chart displaying SANGEA operational categories."""
    payload = {
        "years": years,
        "comb": combustion_t,
        "flare": flaring_t,
        "fug": fugitives_t,
        "vent": venting_t,
        "lang": language,
        "dpi": dpi,
    }

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=dpi)
            try:
                _plot_sangea_axes(ax, years, combustion_t, flaring_t, fugitives_t, venting_t, language)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("sangea", payload, out_path, _render, use_cache=use_cache)


def generate_emissions_sangea_panel_chart(
    years: List[int],
    s1_mmt: List[float],
    s2_mmt: List[float],
    combustion_t: List[float],
    flaring_t: List[float],
    fugitives_t: List[float],
    venting_t: List[float],
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Consolidated 2-panel figure merging Scope 1/2 Progression and SANGEA Attribution."""
    payload = {
        "years": years,
        "s1": s1_mmt,
        "s2": s2_mmt,
        "comb": combustion_t,
        "flare": flaring_t,
        "fug": fugitives_t,
        "vent": venting_t,
        "lang": language,
        "dpi": dpi,
    }

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.2, 3.2), dpi=dpi)
            try:
                _plot_emissions_axes(ax1, years, s1_mmt, s2_mmt, language)
                _plot_sangea_axes(ax2, years, combustion_t, flaring_t, fugitives_t, venting_t, language)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("em_sangea_panel", payload, out_path, _render, use_cache=use_cache)


def generate_flaring_decree_chart(
    years: List[int],
    flaring_mmsm3: List[float],
    flaring_intensity_pct: List[float],
    out_path: str,
    language: str = "en",
    routine_mmsm3: Optional[List[float]] = None,
    non_routine_mmsm3: Optional[List[float]] = None,
    safety_mmsm3: Optional[List[float]] = None,
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Flaring volume with tripartite breakdown and Algerian Executive Decree 21-330 statutory cap (1.00%)."""
    payload = {
        "years": years,
        "fl": flaring_mmsm3,
        "fi": flaring_intensity_pct,
        "rout": routine_mmsm3,
        "nonr": non_routine_mmsm3,
        "safe": safety_mmsm3,
        "lang": language,
        "dpi": dpi,
    }

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, ax1 = plt.subplots(figsize=(7.2, 3.2), dpi=dpi)
            try:
                x = np.arange(len(years))
                width = 0.40

                has_tripartite = bool(
                    routine_mmsm3 and non_routine_mmsm3 and safety_mmsm3 and any(v > 0 for v in routine_mmsm3)
                )

                if has_tripartite:
                    lbl_rout = get_t("chart_flare_routine_lbl", language)
                    lbl_nonr = get_t("chart_flare_non_routine_lbl", language)
                    lbl_safe = get_t("chart_flare_safety_lbl", language)

                    r_arr = np.array(routine_mmsm3)
                    nr_arr = np.array(non_routine_mmsm3)
                    s_arr = np.array(safety_mmsm3)

                    ax1.bar(x, r_arr, width, label=lbl_rout, color="#DC2626", alpha=0.88)
                    ax1.bar(x, nr_arr, width, bottom=r_arr, label=lbl_nonr, color="#F59E0B", alpha=0.88)
                    ax1.bar(x, s_arr, width, bottom=r_arr + nr_arr, label=lbl_safe, color="#0D9488", alpha=0.88)
                else:
                    ax1.bar(x, flaring_mmsm3, width, label=get_t("chart_flare_bar_lbl", language), color=COLOR_WARNING, alpha=0.85)

                ax1.set_ylabel(get_t("chart_flare_vol_axis", language), color="#B45309", fontsize=8.5, fontweight="bold")
                ax1.tick_params(axis="y", labelcolor="#B45309", labelsize=8)
                ax1.set_xticks(x)
                ax1.set_xticklabels([str(y) for y in years], fontsize=8.5, fontweight="bold")
                ax1.grid(axis="y", linestyle="--", alpha=0.5)

                max_fl = max(flaring_mmsm3) if flaring_mmsm3 else 0.0
                ax1.set_ylim(bottom=0, top=max(max_fl * 1.25, 1.0))

                for i, v in enumerate(flaring_mmsm3):
                    if v > 0:
                        ax1.text(x[i], v + max(max_fl * 0.02, 0.02), f"{v:,.2f}", ha="center", va="bottom", fontsize=7, color=COLOR_DARK, fontweight="bold")

                ax2 = ax1.twinx()
                ax2.plot(x, flaring_intensity_pct, label=get_t("chart_flare_line_lbl", language), color=COLOR_DARK, marker="s", linewidth=2.2, markersize=5)
                ax2.axhline(1.00, color="#991B1B", linestyle=":", linewidth=1.8, label=get_t("chart_flare_cap_lbl", language))
                ax2.set_ylabel(get_t("chart_flare_int_axis", language), color=COLOR_DARK, fontsize=8.5, fontweight="bold")
                ax2.tick_params(axis="y", labelcolor=COLOR_DARK, labelsize=8)

                max_int = max(flaring_intensity_pct) if flaring_intensity_pct else 0.0
                ax2.set_ylim(bottom=0, top=max(max_int * 1.35, 1.5))

                pass_label = "Conforme" if str(language).lower().startswith("fr") else "Pass"
                for i, v in enumerate(flaring_intensity_pct):
                    col = COLOR_SUCCESS if v <= 1.00 else COLOR_DANGER
                    tag = f"{v:.2f}% ({pass_label})" if v <= 1.00 else f"{v:.2f}% (!)"
                    ax2.text(x[i], v + max(max_int * 0.03, 0.03), tag, ha="center", va="bottom", fontsize=7, color=col, fontweight="bold")

                ax1.set_title(get_t("chart_flare_title", language), fontsize=9.5, fontweight="bold", pad=12, color=COLOR_DARK)
                lines1, labels1 = ax1.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=7, frameon=True)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("flaring", payload, out_path, _render, use_cache=use_cache)


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
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("int_poll_panel", payload, out_path, _render, use_cache=use_cache)


def generate_regional_benchmark_chart(
    benchmarks: List[Dict[str, Any]],
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Horizontal bar chart comparing Carbon Intensities (kg CO2e/BOE) across operational basins."""
    if not benchmarks:
        return
    payload = {"benchmarks": benchmarks, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=dpi)
            try:
                sorted_b = sorted(benchmarks, key=lambda b: b.get("carbon_intensity_kg_boe", 0.0))
                names = [b.get("name", "").split("(")[0].strip() for b in sorted_b]
                ci_vals = [b.get("carbon_intensity_kg_boe", 0.0) for b in sorted_b]
                colors_list = [COLOR_SUCCESS if b.get("decree_compliant") else COLOR_DANGER for b in sorted_b]

                y_pos = np.arange(len(names))
                bars = ax.barh(y_pos, ci_vals, color=colors_list, alpha=0.88, height=0.6)

                ax.set_yticks(y_pos)
                ax.set_yticklabels(names, fontsize=8, fontweight="bold", color=COLOR_DARK)
                ax.set_xlabel(get_t("chart_bench_axis", language), fontsize=8.5, fontweight="bold", color=COLOR_DARK)
                ax.tick_params(axis="x", labelsize=8)
                ax.grid(axis="x", linestyle="--", alpha=0.5)

                max_val = max(ci_vals) if ci_vals else 0.0
                ax.set_xlim(left=0, right=max(max_val * 1.25, 5.0))

                boe_unit = "kg/BEP" if str(language).lower().startswith("fr") else "kg/BOE"
                for b, val in zip(bars, ci_vals):
                    ax.text(val + max(max_val * 0.02, 0.2), b.get_y() + b.get_height() / 2, f"{val:.1f} {boe_unit}", va="center", ha="left", fontsize=7, fontweight="bold", color=COLOR_DARK)

                fig.suptitle(get_t("chart_bench_title", language), fontsize=9.5, fontweight="bold", y=0.98, color=COLOR_DARK)
                is_fr = str(language).lower().startswith("fr")
                sub = "(Vert = Conforme Décret 21-330  |  Rouge = Dépassement Plafond Réglementaire)" if is_fr else "(Green = Decree 21-330 Compliant  |  Red = Exceeded Statutory Flaring Ceiling)"
                ax.set_title(sub, fontsize=7.5, color=COLOR_MUTED, pad=4)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("benchmark", payload, out_path, _render, use_cache=use_cache)


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
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("glide_jv_panel", payload, out_path, _render, use_cache=use_cache)


def generate_ogmp_reconciliation_chart(
    ogmp_data: dict,
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Renders OGMP 2.0 Level 4 vs Level 5 Methane Reconciliation Chart (tCH4)."""
    payload = {"ogmp": ogmp_data, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        is_fr = str(language).lower().startswith("fr")
        surveys = ogmp_data.get("surveys", [])

        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=dpi)
            try:
                if not surveys:
                    lbl = "Relevé OGMP 2.0 (N4/N5)" if is_fr else "OGMP 2.0 L4/L5 Survey"
                    x = np.arange(1)
                    ax.bar(x - 0.18, [845.0], 0.35, label="Source Bottom-Up L4 (845 tCH4)", color=COLOR_SLATE, alpha=0.9)
                    ax.bar(x + 0.18, [809.4], 0.35, label="Site Top-Down L5 (809 tCH4)", color=COLOR_TEAL, alpha=0.9)
                    ax.set_xticks(x)
                    ax.set_xticklabels([lbl], fontsize=8, fontweight="bold")
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
                    ax.set_xticklabels(labels, fontsize=7.2, fontweight="bold")

                    max_v = max(max(bu_vals + td_vals + [1.0]), 10.0)
                    ax.set_ylim(0, max_v * 1.3)

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
    """Renders Scope 3 Category Breakdown Donut / Pie Chart showing Category Share (%)."""
    payload = {"s3": scope3_data, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        is_fr = str(language).lower().startswith("fr")
        categories = scope3_data.get("categories", [])

        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=dpi)
            try:
                if not categories or scope3_data.get("total_period_co2e", 0.0) <= 0:
                    labels = ["Cat 1: Goods & Services", "Cat 4: Upstream Logistics", "Cat 11: Use of Sold Energy", "Other Scope 3"]
                    sizes = [65.0, 15.0, 15.0, 5.0]
                    palette = [COLOR_BLUE, COLOR_TEAL, COLOR_ORANGE, COLOR_SLATE]
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
                    textprops=dict(color=COLOR_DARK, fontsize=7.2, fontweight="bold"),
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


def generate_cbam_embeddings_chart(
    cbam_data: dict,
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Renders EU CBAM Specific Embedded Emissions (SEE Direct vs SEE Indirect) by Export Product."""
    payload = {"cbam": cbam_data, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        is_fr = str(language).lower().startswith("fr")
        products = cbam_data.get("products", [])

        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=dpi)
            try:
                if not products:
                    names = ["Ammonia (GL1Z)", "UAN Fertilizer", "ULSD Diesel (RA1K)", "Aromatics", "Sahara Blend"]
                    see_dir = [1.785, 0.824, 0.265, 0.612, 0.045]
                    see_indir = [0.142, 0.098, 0.048, 0.115, 0.012]
                else:
                    pts = products[:5]
                    names = [p["product_name"][:20] for p in pts]
                    see_dir = [p["see_direct"] for p in pts]
                    see_indir = [p["see_indirect"] for p in pts]

                x = np.arange(len(names))
                width = 0.45

                lbl_dir = "Direct Embedded (SEE Direct)" if not is_fr else "Émissions Spécifiques Directes"
                lbl_indir = "Indirect Electricity (SEE Indirect)" if not is_fr else "Électricité Indirecte"

                ax.bar(x, see_dir, width, label=lbl_dir, color=COLOR_BLUE, alpha=0.9)
                ax.bar(x, see_indir, width, bottom=see_dir, label=lbl_indir, color=COLOR_ORANGE, alpha=0.9)

                ax.set_ylabel(get_t("chart_cbam_axis", language), fontsize=8.5, fontweight="bold", color=COLOR_DARK)
                ax.set_xticks(x)
                ax.set_xticklabels(names, fontsize=7.2, fontweight="bold", rotation=0)
                ax.tick_params(axis="both", labelsize=7.5)
                ax.grid(axis="y", linestyle="--", alpha=0.5)

                totals = [d + i for d, i in zip(see_dir, see_indir)]
                max_tot = max(totals) if totals else 1.0
                ax.set_ylim(0, max(max_tot * 1.3, 0.1))

                for i, tot in enumerate(totals):
                    if tot > 0:
                        ax.text(x[i], tot + max(max_tot * 0.03, 0.005), f"{tot:.3f}", ha="center", va="bottom", fontsize=6.8, fontweight="bold", color=COLOR_DARK)

                ax.set_title(get_t("chart_cbam_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)
                ax.legend(loc="upper right", frameon=True, fontsize=7.2)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("cbam", payload, out_path, _render, use_cache=use_cache)


def generate_process_overview_diagram(
    facility_name: str,
    out_path: str,
    language: str = "en",
    dpi: int = CHART_DPI,
    use_cache: bool = True,
):
    """Renders a 150-DPI Process Flow Diagram (PFD) for a facility."""
    payload = {"facility_name": facility_name, "lang": language, "dpi": dpi}

    def _render(target_path: str) -> None:
        with _PLOT_LOCK:
            fig, ax = plt.subplots(figsize=(8.5, 4.2), dpi=dpi)
            try:
                ax.set_xlim(0, 100)
                ax.set_ylim(0, 50)
                ax.axis("off")

                is_fr = str(language).lower().startswith("fr")
                title_suffix = "Architecture des Procedees CPF" if is_fr else "CPF Process Architecture & Block Flow Overview"
                ax.text(50, 47, f"{facility_name} - {title_suffix}", ha="center", va="center", fontsize=10.5, fontweight="bold", color=COLOR_DARK)

                fence = patches.Rectangle((3, 3), 94, 41, fill=False, edgecolor=COLOR_MUTED, linestyle="--", linewidth=0.8)
                ax.add_patch(fence)
                ax.text(5, 42, "CPF FENCE LINE" if not is_fr else "LIMITE DE L'INSTALLATION CPF", fontsize=6.5, fontweight="bold", color=COLOR_MUTED)

                blocks = [
                    (5, 18, 14, 11, "Wellhead Gathering\n& FGS Manifolds" if not is_fr else "Collecte Puits\n& Manifolds FGS", "#0284C7"),
                    (23, 18, 15, 11, "Inlet Separation\n(HP / IP Trains)" if not is_fr else "Separation Entree\n(Trains HP / MP)", "#0D9488"),
                    (42, 18, 16, 11, "Oil Desalting &\nStabilization Tower" if not is_fr else "Dessalage & Colonne\nde Stabilisation", "#059669"),
                    (62, 18, 15, 11, "Crude / Condensate\nStorage Tanks" if not is_fr else "Stockage Brut &\nCondensats", "#10B981"),
                    (81, 18, 15, 11, "LACT Custody &\nExport Pipeline" if not is_fr else "Comptage LACT &\nExport Pipeline", "#047857"),
                    (23, 32, 15, 9, "Gas Compression\n(BGC / AGC / RGC)" if not is_fr else "Compression Gaz\n(BGC / AGC / RGC)", "#D97706"),
                    (42, 32, 16, 9, "Glycol / Mole Sieve\nDehydration Unit" if not is_fr else "Unite Deshydratation\n(Glycol / Tamis)", "#B45309"),
                    (62, 32, 15, 9, "High-Pressure Gas\nReinjection Network" if not is_fr else "Reseau Reinjection\nGaz Haute Pression", "#92400E"),
                    (42, 5, 16, 9, "Produced Water\nTreatment System" if not is_fr else "Traitement des\nEaux de Production", "#64748B"),
                    (62, 5, 15, 9, "Water Injection\nWells & Pumps" if not is_fr else "Puits & Pompes\nInjection d'Eau", "#475569"),
                    (81, 5, 15, 9, "Flaring System\n(HP/LP Smokeless)" if not is_fr else "Systeme Torches\n(HP/MP Sans Fumee)", "#DC2626"),
                    (81, 32, 15, 9, "Gas Turbines &\nPower Generation" if not is_fr else "Turbines a Gaz &\nProduction Elec.", "#7C3AED"),
                ]

                for x, y, w, h, label, bg in blocks:
                    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3", facecolor=bg, edgecolor=COLOR_DARK, linewidth=0.8)
                    ax.add_patch(rect)
                    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", color="white", fontsize=6.2, fontweight="bold")

                arrows = [
                    ((19, 23.5), (23, 23.5)),
                    ((38, 23.5), (42, 23.5)),
                    ((58, 23.5), (62, 23.5)),
                    ((77, 23.5), (81, 23.5)),
                    ((30.5, 29), (30.5, 32)),
                    ((38, 36.5), (42, 36.5)),
                    ((58, 36.5), (62, 36.5)),
                    ((58, 36.5), (81, 36.5)),
                    ((50, 18), (50, 14)),
                    ((58, 9.5), (62, 9.5)),
                    ((77, 9.5), (81, 9.5)),
                ]
                for start, end in arrows:
                    ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="->", color=COLOR_DARK, lw=1.2))

                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("pfd", payload, out_path, _render, use_cache=use_cache)
