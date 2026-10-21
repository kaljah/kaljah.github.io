"""
Master Report Matplotlib Visual Engine
======================================
Renders 300-DPI publication-grade vector/raster figures for the
Universal Master Publication Report:
- Hydrocarbon Production Trajectory
- Scope 1 & Scope 2 Emissions Progression
- SANGEA Source Attribution
- Flaring Volumes vs Decree 21-330 Statutory Limit (1.00%)
- Multi-Metric Carbon & Methane Intensities
- Criteria Air Pollutants Mass
- Regional Cross-Basin Benchmark League Table
"""

import os
from typing import Any, Dict, List, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from services.master_report_i18n import get_t

# Corporate Sonatrach & Publication Palette
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


def generate_production_chart(
    years: List[int],
    gas_mmsm3: List[float],
    liquid_mmbbl: List[float],
    out_path: str,
    language: str = "en"
):
    """Dual-axis production trajectory: Gross Natural Gas (MMSm³) vs Total Liquids (MMbbl)."""
    fig, ax1 = plt.subplots(figsize=(7.2, 3.2), dpi=300)
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
            ax1.text(b.get_x() + b.get_width() / 2., h + max(max_gas * 0.02, 0.02), f"{h:,.1f}", ha="center", va="bottom", fontsize=7, color=COLOR_DARK)

    ax2 = ax1.twinx()
    ax2.plot(x + width / 2, liquid_mmbbl, label=lbl_liq, color=COLOR_ORANGE, marker="o", linewidth=2.2, markersize=5)
    ax2.set_ylabel(get_t("chart_prod_liq_axis", language), color=COLOR_ORANGE, fontsize=8.5, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=COLOR_ORANGE, labelsize=8)

    max_liq = max(liquid_mmbbl) if liquid_mmbbl else 0.0
    ax2.set_ylim(bottom=0, top=max(max_liq * 1.25, 0.1))

    for i, v in enumerate(liquid_mmbbl):
        if v > 0:
            ax2.text(x[i] + width / 2, v + max(max_liq * 0.03, 0.005), f"{v:,.2f}", ha="center", va="bottom", fontsize=7, color=COLOR_ORANGE, fontweight="bold")

    plt.title(get_t("chart_prod_title", language), fontsize=10, fontweight="bold", pad=12, color=COLOR_DARK)
    fig.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)


def generate_emissions_progression_chart(
    years: List[int],
    s1_mmt: List[float],
    s2_mmt: List[float],
    out_path: str,
    language: str = "en"
):
    """Stacked bar chart of Scope 1 Direct and Scope 2 Indirect GHG emissions (MMtCO2e)."""
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=300)
    x = np.arange(len(years))
    width = 0.45

    p1 = ax.bar(x, s1_mmt, width, label=get_t("chart_em_s1_lbl", language), color=COLOR_ORANGE, alpha=0.9)
    p2 = ax.bar(x, s2_mmt, width, bottom=s1_mmt, label=get_t("chart_em_s2_lbl", language), color=COLOR_TEAL, alpha=0.85)

    ax.set_ylabel(get_t("chart_em_axis", language), fontsize=8.5, fontweight="bold", color=COLOR_DARK)
    ax.set_xticks(x)
    ax.set_xticklabels([str(y) for y in years], fontsize=8.5, fontweight="bold")
    ax.tick_params(axis="both", labelsize=8)
    ax.legend(loc="upper right", frameon=True, fontsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    totals = [s1 + s2 for s1, s2 in zip(s1_mmt, s2_mmt)]
    max_tot = max(totals) if totals else 0.0
    ax.set_ylim(bottom=0, top=max(max_tot * 1.25, 0.01))

    for i in range(len(years)):
        tot = totals[i]
        if tot > 0:
            ax.text(x[i], tot + max(max_tot * 0.02, 0.0002), f"{tot:,.3f} MMt", ha="center", va="bottom", fontsize=7.5, fontweight="bold", color=COLOR_DARK)

    plt.title(get_t("chart_em_title", language), fontsize=10, fontweight="bold", pad=12, color=COLOR_DARK)
    fig.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)


def generate_sangea_breakdown_chart(
    years: List[int],
    combustion_t: List[float],
    flaring_t: List[float],
    fugitives_t: List[float],
    venting_t: List[float],
    out_path: str,
    language: str = "en"
):
    """Stacked bar chart displaying SANGEA operational categories."""
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=300)
    x = np.arange(len(years))
    width = 0.45

    # Convert to ktCO2e
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
    ax.legend(loc="upper left", frameon=True, fontsize=7.5, ncol=2)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    plt.title(get_t("chart_sangea_title", language), fontsize=10, fontweight="bold", pad=12, color=COLOR_DARK)
    fig.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)


def generate_flaring_decree_chart(
    years: List[int],
    flaring_mmsm3: List[float],
    flaring_intensity_pct: List[float],
    out_path: str,
    language: str = "en",
    routine_mmsm3: Optional[List[float]] = None,
    non_routine_mmsm3: Optional[List[float]] = None,
    safety_mmsm3: Optional[List[float]] = None
):
    """Flaring volume with tripartite breakdown and Algerian Executive Decree 21-330 statutory cap (1.00%)."""
    fig, ax1 = plt.subplots(figsize=(7.2, 3.2), dpi=300)
    x = np.arange(len(years))
    width = 0.40

    has_tripartite = bool(
        routine_mmsm3 and non_routine_mmsm3 and safety_mmsm3 and
        any(v > 0 for v in routine_mmsm3)
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

    plt.title(get_t("chart_flare_title", language), fontsize=10, fontweight="bold", pad=12, color=COLOR_DARK)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=7, frameon=True)

    fig.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)


def generate_intensities_chart(
    years: List[int],
    carbon_intensity_kg_boe: List[float],
    methane_intensity_pct: List[float],
    out_path: str,
    language: str = "en"
):
    """Dual-axis trajectory of Carbon Intensity (kg CO2e/BOE) & Methane Intensity (NGSI wt.%)."""
    fig, ax1 = plt.subplots(figsize=(7.2, 3.2), dpi=300)
    x = np.arange(len(years))

    lbl_ci = get_t("chart_int_ci_lbl", language)
    lbl_mi = get_t("chart_int_mi_lbl", language)
    ax1.plot(x, carbon_intensity_kg_boe, color=COLOR_ORANGE, marker="o", linewidth=2.2, markersize=6, label=lbl_ci)
    ax1.set_ylabel(get_t("chart_int_ci_axis", language), color=COLOR_ORANGE, fontsize=8.5, fontweight="bold")
    ax1.tick_params(axis="y", labelcolor=COLOR_ORANGE, labelsize=8)
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(y) for y in years], fontsize=8.5, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.5)

    max_ci = max(carbon_intensity_kg_boe) if carbon_intensity_kg_boe else 0.0
    ax1.set_ylim(bottom=0, top=max(max_ci * 1.25, 5.0))

    for i, v in enumerate(carbon_intensity_kg_boe):
        ax1.text(x[i], v + max(max_ci * 0.02, 0.2), f"{v:.1f}", ha="center", va="bottom", fontsize=7.5, color=COLOR_ORANGE, fontweight="bold")

    ax2 = ax1.twinx()
    ax2.plot(x, methane_intensity_pct, color=COLOR_TEAL, marker="^", linewidth=2.2, markersize=6, label=lbl_mi)
    ax2.axhline(0.20, color="#0F766E", linestyle="--", linewidth=1.2, label=get_t("chart_int_ogci_lbl", language))
    ax2.set_ylabel(get_t("chart_int_mi_axis", language), color=COLOR_TEAL, fontsize=8.5, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=COLOR_TEAL, labelsize=8)

    max_mi = max(methane_intensity_pct) if methane_intensity_pct else 0.0
    ax2.set_ylim(bottom=0, top=max(max_mi * 1.35, 0.3))

    for i, v in enumerate(methane_intensity_pct):
        ax2.text(x[i], v + max(max_mi * 0.03, 0.005), f"{v:.3f}%", ha="center", va="bottom", fontsize=7.5, color=COLOR_TEAL, fontweight="bold")

    plt.title(get_t("chart_int_title", language), fontsize=10, fontweight="bold", pad=12, color=COLOR_DARK)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=7.5, frameon=True)

    fig.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)


def generate_criteria_pollutants_chart(
    years: List[int],
    nox_t: List[float],
    co_t: List[float],
    so2_t: List[float],
    voc_t: List[float],
    out_path: str,
    language: str = "en"
):
    """Grouped bar chart for Criteria Air Pollutants mass (NOx, CO, SO2, VOC)."""
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=300)
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
    ax.legend(loc="upper right", frameon=True, fontsize=7.5)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    max_p = max(max(nox_t, default=0), max(co_t, default=0), max(so2_t, default=0), max(voc_t, default=0))
    ax.set_ylim(bottom=0, top=max(max_p * 1.25, 1.0))

    plt.title(get_t("chart_poll_title", language), fontsize=9.5, fontweight="bold", pad=10, color=COLOR_DARK)
    fig.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)


def generate_regional_benchmark_chart(benchmarks: List[Dict[str, Any]], out_path: str, language: str = "en"):
    """Horizontal bar chart comparing Carbon Intensities (kg CO2e/BOE) across Sonatrach basins."""
    if not benchmarks:
        return
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=300)

    # Sort descending
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
    fig.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)


def generate_2030_glidepath_chart(
    target_projection: Dict[str, Any],
    out_path: str,
    language: str = "en"
):
    """Visualizes the 2030 corporate decarbonization trajectory, historical emissions, and milestone glidepath."""
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=300)

    hist_years = target_projection.get("historical_years", [])
    hist_ghg = target_projection.get("historical_ghg_mmt", [])
    proj_years = target_projection.get("proj_years", [])
    glidepath = target_projection.get("glidepath_mmt", [])
    target_2030 = target_projection.get("target_2030_ghg_mmt", 0.0)

    if hist_years and hist_ghg:
        lbl_hist = get_t("chart_glide_hist_lbl", language)
        ax.plot(hist_years, hist_ghg, color=COLOR_BLUE, marker="o", linewidth=2.4, markersize=5.5, label=lbl_hist)
        for y, val in zip(hist_years, hist_ghg):
            ax.text(y, val + max(max(hist_ghg) * 0.025, 0.01), f"{val:.2f}", ha="center", va="bottom", fontsize=7, fontweight="bold", color=COLOR_BLUE)

    if proj_years and glidepath:
        lbl_target = get_t("chart_glide_target_lbl", language)
        ax.plot(proj_years, glidepath, color=COLOR_ORANGE, marker="s", linestyle="--", linewidth=2.2, markersize=5, label=lbl_target)
        ax.fill_between(proj_years, glidepath, alpha=0.12, color=COLOR_ORANGE, label=get_t("chart_glide_envelope_lbl", language))
        for y, val in zip(proj_years[1:], glidepath[1:]):
            ax.text(y, val - max(max(glidepath) * 0.04, 0.02), f"{val:.2f}", ha="center", va="top", fontsize=6.8, color=COLOR_ORANGE, fontweight="bold")

    lbl_point = get_t("chart_glide_point_lbl", language)
    ax.scatter([2030], [target_2030], color=COLOR_DANGER, s=75, zorder=6, label=lbl_point)

    all_years = sorted(list(set(hist_years + proj_years)))
    ax.set_xticks(all_years)
    ax.set_xticklabels([str(y) for y in all_years], fontsize=8, fontweight="bold")
    ax.set_ylabel(get_t("chart_glide_axis", language), fontsize=8.5, fontweight="bold", color=COLOR_DARK)
    ax.grid(True, linestyle="--", alpha=0.5)

    all_vals = (hist_ghg or []) + (glidepath or [])
    max_val = max(all_vals) if all_vals else 1.0
    ax.set_ylim(bottom=0, top=max(max_val * 1.3, 0.1))

    plt.title(get_t("chart_glide_title", language), fontsize=10, fontweight="bold", pad=12, color=COLOR_DARK)
    ax.legend(loc="upper right", fontsize=7, frameon=True)

    fig.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)


def generate_jv_equity_chart(
    jv_equity: Any,
    out_path: str,
    language: str = "en"
):
    """Visualizes JV Partner Equity Share allocation across the multi-year reporting timeline."""
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=300)
    if isinstance(jv_equity, dict):
        annual = jv_equity.get("annual_equity_timeline", [])
        partners = jv_equity.get("partners", [])
    elif isinstance(jv_equity, list):
        partners = jv_equity
        annual = []
    else:
        annual, partners = [], []

    if not annual or not partners:
        plt.title(get_t("chart_jv_title", language), fontsize=10, fontweight="bold", color=COLOR_DARK)
        fig.tight_layout()
        plt.savefig(out_path, dpi=300)
        plt.close(fig)
        return

    years = [a["year"] for a in annual]
    x = np.arange(len(years))
    width = 0.42

    palette = [COLOR_ORANGE, COLOR_BLUE, COLOR_TEAL, COLOR_PURPLE, COLOR_WARNING, COLOR_SLATE]
    bottom = np.zeros(len(years))

    for idx, p in enumerate(partners):
        p_code = p.get("partner_code", p.get("code", "SH"))
        p_name = p.get("partner_name", p.get("partner", "Sonatrach"))
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
    ax.set_xticklabels([str(y) for y in years], fontsize=8.5, fontweight="bold")
    ax.tick_params(axis="both", labelsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    max_tot = max(bottom) if len(bottom) > 0 else 0.0
    ax.set_ylim(bottom=0, top=max(max_tot * 1.25, 0.01))

    for i in range(len(years)):
        tot = bottom[i]
        if tot > 0:
            ax.text(x[i], tot + max(max_tot * 0.02, 0.001), f"{tot:,.3f} MMt", ha="center", va="bottom", fontsize=7.5, fontweight="bold", color=COLOR_DARK)

    plt.title(get_t("chart_jv_title", language), fontsize=10, fontweight="bold", pad=12, color=COLOR_DARK)
    ax.legend(loc="upper right", frameon=True, fontsize=7.2, ncol=min(len(partners), 2))

    fig.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close(fig)
