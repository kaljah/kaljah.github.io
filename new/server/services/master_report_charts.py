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

Intensity / pollutant / glidepath / JV charts live in master_report_charts_performance, and the OGMP, Scope 3,
CBAM and process diagram charts in master_report_charts_sections; both use the cache, palette and Matplotlib
setup defined here and are re-exported at the end of this module.
"""

from collections import OrderedDict
import hashlib
import json
import logging
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
import matplotlib.pyplot as plt
import numpy as np

from services.master_report_i18n import get_t

CHART_DPI = 150
_CACHE_SCHEMA_VERSION = "v4-150dpi"
_PLOT_LOCK = threading.RLock()
_CACHE_STATS_LOCK = threading.Lock()
_CACHE_STATS = {"hits": 0, "misses": 0}
logger = logging.getLogger(__name__)

_MAX_PFD_BASE_CACHE_ENTRIES = 32
_PFD_BASE_CACHE: OrderedDict[tuple[str, int, bool, tuple[str, ...]], tuple[Any, float, float]] = OrderedDict()

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
    "text.parse_math": False,
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
        except OSError as exc:
            logger.warning("Failed removing cached chart %s: %s", png, exc)
    with _PLOT_LOCK:
        _PFD_BASE_CACHE.clear()
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
            except OSError as exc:
                logger.warning("Failed removing temp chart artifact %s: %s", tmp_path, exc)


def _finalize_figure(fig: plt.Figure, out_path: str, dpi: int = CHART_DPI, w_pad: Optional[float] = None) -> None:
    """Saves and always closes a Matplotlib figure cleanly."""
    if w_pad is not None:
        fig.tight_layout(w_pad=w_pad)
    else:
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
                _finalize_figure(fig, target_path, dpi=dpi, w_pad=3.2)
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
                ax2.set_ylim(bottom=0, top=max(max_int * 1.40, 1.5))

                pass_label = "Conforme" if str(language).lower().startswith("fr") else "Pass"
                for i, v in enumerate(flaring_intensity_pct):
                    col = COLOR_SUCCESS if v <= 1.00 else COLOR_DANGER
                    tag = f"{v:.2f}% ({pass_label})" if v <= 1.00 else f"{v:.2f}% (!)"
                    ax2.annotate(
                        tag,
                        xy=(x[i], v),
                        xytext=(0, 9),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=6.8,
                        color=col,
                        fontweight="bold",
                        bbox=dict(
                            boxstyle="round,pad=0.18",
                            facecolor="white",
                            edgecolor="#CBD5E1",
                            linewidth=0.5,
                            alpha=0.92,
                        ),
                        zorder=7,
                    )

                ax1.set_title(get_t("chart_flare_title", language), fontsize=9.5, fontweight="bold", pad=12, color=COLOR_DARK)
                lines1, labels1 = ax1.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=7, frameon=True)
                _finalize_figure(fig, target_path, dpi=dpi)
            finally:
                fig.clear()
                plt.close(fig)

    _cached_render("flaring", payload, out_path, _render, use_cache=use_cache)


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
                ax.set_yticklabels(names, fontsize=8, fontweight="bold", color=COLOR_DARK, parse_math=False)
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


# Split modules (they import from this one, so they come last)
from services.master_report_charts_performance import (  # noqa: F401,E402
    generate_2030_glidepath_chart,
    generate_criteria_pollutants_chart,
    generate_glidepath_jv_panel_chart,
    generate_intensities_chart,
    generate_intensities_pollutants_panel_chart,
    generate_jv_equity_chart,
)
from services.master_report_charts_sections import (  # noqa: F401,E402
    _get_pfd_base_template,
    generate_cbam_embeddings_chart,
    generate_ogmp_reconciliation_chart,
    generate_process_overview_diagram,
    generate_scope3_category_chart,
)
