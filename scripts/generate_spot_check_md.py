import json
import random
import os

SEED = 42
random.seed(SEED)

with open('scripts/full_reconciled_sources.json') as f:
    sources = json.load(f)

# Sample 10 sources
sampled_indices = sorted(random.sample(range(len(sources)), 10))
sampled = [sources[i] for i in sampled_indices]

# Image files mapping
crop_map = {
    0: ("spot_01_hbns_heater4.png", "page_26.png", "page_27.png"),
    1: ("spot_02_hbns_turbine3.png", "page_26.png", "page_27.png"),
    2: ("spot_03_hbns_flare_purging.png", "page_26.png", "page_27.png"),
    3: ("spot_04_hbns_flare1_hp.png", "page_26.png", "page_27.png"),
    4: ("spot_05_hbns_venting_cpf.png", "page_26.png", "page_27.png"),
    5: ("spot_06_hbns_tank_liquid.png", "page_27.png", "page_28.png"),
    6: ("spot_07_elm_h01_ngl_heater.png", "page_32.png", "page_33.png"),
    7: ("spot_08_elm_flare_ap.png", "page_32.png", "page_33.png"),
    8: ("spot_09_elm_flare_ot1.png", "page_32.png", "page_33.png"),
    9: ("spot_10_elm_fire_suppressant.png", "page_32.png", "page_34.png"),
}

md_lines = [
    "# Independent Auditor Spot-Check Verification Sample (10 Sources)",
    "",
    "> **Audit Standard**: ISO 14064-3 / API Compendium (2021) Verification Protocol  ",
    f"> **Deterministic PRNG Sampling Seed**: `SEED = {SEED}` (Python `random.seed({SEED})`)  ",
    f"> **Total Source Population**: {len(sources)} individual emission sources across HBNS and El Merk  ",
    "> **Sample Size**: 10 random sources  ",
    "> **Objective**: Enable hands-on, third-party manual verification of activity data, reported emissions, stoichiometry, and AR4 GWP aggregations with direct high-resolution screenshot evidence.  ",
    "",
    "---",
    "",
    "## 1. Summary Table of Sampled Spot-Check Sources",
    "",
    "| Sample # | Entity | Source Name | SANGEA Module | Activity Data | Activity Unit | Reported CO₂ (t) | Reported CH₄ (t) | Reported N₂O (t) | Reported CO₂e (t) | Recalculated CO₂e (t) | Delta (t) | Status | Evidence Screenshot |",
    "| :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |"
]

for idx, s in enumerate(sampled):
    crop_file, p_act_file, p_em_file = crop_map[idx]
    crop_path = f"screenshots/spot_check/{crop_file}"
    md_lines.append(
        f"| **#{idx+1:02d}** | {s['entity']} | **{s['source_name']}** | {s['module']} | "
        f"{s['activity_data']:,.2f} | {s['activity_unit']} | "
        f"{s['rep_co2']:,.2f} | {s['rep_ch4']:,.3f} | {s['rep_n2o']:,.3f} | "
        f"**{s['rep_co2e']:,.2f}** | **{s['calc_co2e']:,.2f}** | "
        f"{s['diff_co2e']:+.2f} | `{s['status']}` | [`{crop_file}`](file:///c:/Users/samsung/Desktop/H2/{crop_path}) |"
    )

md_lines.extend([
    "",
    "---",
    "",
    "## 2. Granular Per-Source Verification Dossier",
    ""
])

for idx, s in enumerate(sampled):
    crop_file, p_act_file, p_em_file = crop_map[idx]
    crop_path = f"screenshots/spot_check/{crop_file}"
    p_act_path = f"screenshots/spot_check/{p_act_file}"
    p_em_path = f"screenshots/spot_check/{p_em_file}"
    
    gwp_calc = s['rep_co2'] * 1.0 + s['rep_ch4'] * 25.0 + s['rep_n2o'] * 298.0
    
    md_lines.extend([
        f"### Sample #{idx+1:02d}: {s['entity']} — {s['source_name']}",
        "",
        f"- **Facility / Entity**: {s['entity']} (Groupement Berkine)",
        f"- **Module**: {s['module']}",
        f"- **Reporting Scope**: {s['scope']}",
        f"- **Activity Level**: `{s['activity_data']:,.2f} {s['activity_unit']}` (Extracted from {s['table_activity']}, Page {s['page_activity']})",
        f"- **Reported Emissions**: ",
        f"  - $\\text{{CO}}_2$: `{s['rep_co2']:,.2f}` tonnes",
        f"  - $\\text{{CH}}_4$: `{s['rep_ch4']:,.3f}` tonnes",
        f"  - $\\text{{N}}_2\\text{{O}}$: `{s['rep_n2o']:,.3f}` tonnes",
        f"  - $\\text{{Total CO}}_2\\text{{e}}$: `{s['rep_co2e']:,.2f}` tonnes (Extracted from {s['table_emissions']}, Page {s['page_emissions']})",
        f"- **AR4 GWP Verification**: $1.0 \\times {s['rep_co2']:,.2f} + 25.0 \\times {s['rep_ch4']:,.3f} + 298.0 \\times {s['rep_n2o']:,.3f} = {gwp_calc:,.2f}\\ \\text{{t CO}}_2\\text{{e}}$ (Reported: `{s['rep_co2e']:,.2f}`, $\\Delta = {gwp_calc - s['rep_co2e']:+.2f}$ t)",
        f"- **Independent Recalculated Value**: `{s['calc_co2e']:,.2f}\\ \\text{{t CO}}_2\\text{{e}}$",
        f"- **Discrepancy / Variance**: `{s['diff_co2e']:+.2f}\\ \\text{{t CO}}_2\\text{{e}}`",
        f"- **Reconciliation Status**: `{s['status']}`",
        f"- **Auditor Engineering Notes**: {s['notes']}",
        "",
        "#### Primary Evidence Screenshot Crop:",
        f"![{s['source_name']} Table Crop](file:///c:/Users/samsung/Desktop/H2/{crop_path})",
        "",
        f"> **Full Page Context**:  ",
        f"> - Activity Source: [{s['table_activity']} (Page {s['page_activity']})](file:///c:/Users/samsung/Desktop/H2/{p_act_path})  ",
        f"> - Emissions Source: [{s['table_emissions']} (Page {s['page_emissions']})](file:///c:/Users/samsung/Desktop/H2/{p_em_path})  ",
        "",
        "---",
        ""
    ])

md_lines.extend([
    "## 3. Step-by-Step Manual Hand-Verification Protocol",
    "",
    "Auditors and reviewers can execute independent manual verification following this exact procedure:",
    "",
    "1. **Click the evidence links above** or inspect the saved high-resolution images in `screenshots/spot_check/`.",
    "2. **Verify the Activity Volume**: Confirm the activity number in the cropped table against the Activity Table ({Table 7 for HBNS, Table 14 for El Merk}).",
    "3. **Verify Reported Greenhouse Gases**: Read the individual gas columns ($\\text{CO}_2$, $\\text{CH}_4$, $\\text{N}_2\\text{O}$) in the Emissions Table ({Table 8 for HBNS, Table 15 for El Merk}).",
    "4. **Recompute AR4 $\\text{CO}_2\\text{e}$**: Manually evaluate $\\text{CO}_2\\text{e} = \\text{CO}_2 + 25 \\times \\text{CH}_4 + 298 \\times \\text{N}_2\\text{O}$ using standard calculator precision.",
    "5. **Check Tolerances**: Confirm whether difference is strictly within intermediate floating point / table display rounding ($< 0.10\\ \\text{t}$ or $< 1.5\\ \\text{t}$ for high-tonnage sources) or represents an identified structural anomaly.",
    ""
])

with open('spot_check.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(md_lines))

print("spot_check.md written successfully.")
