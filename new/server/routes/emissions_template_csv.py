"""CSV import template download.

Split out of routes/emissions.py unchanged (hardening plan, task 5.3). The route is
registered on the same ``emissions_bp`` blueprint, so URLs and endpoint names are the same.
"""
from flask import Response, request

from . import emissions_bp
from .emissions_template_columns import TEMPLATE_COLUMNS


@emissions_bp.route("/template/csv", methods=["GET"])
def get_csv_template():
    """
    Returns a comprehensive CSV template with all fields needed for
    Tier 1 (default/custom factor) and Tier 3 (specific engineering) calculations
    across all 18 supported process types.
    """
    import csv, io

    tier = request.args.get("tier", "3")
    process = request.args.get("process", "all")

    # -----------------------------------------------------------------------
    # COLUMN DEFINITIONS
    # Format: (header_label, internal_key, tier, description)
    # -----------------------------------------------------------------------
    COLUMNS = list(TEMPLATE_COLUMNS)

    filtered_columns = []

    # Process grouping maps
    p_comp = ["all", "combustion", "flaring", "completions", "blowdown", "agr"]
    p_flare = [
        "all",
        "flaring",
        "completions",
        "unloading",
        "blowdown",
        "tank_flashing",
        "tank_working",
        "tank_breathing",
    ]
    p_drill = ["all", "drilling"]
    p_completion = ["all", "completions"]
    p_unload = ["all", "unloading"]
    p_bdn = ["all", "venting", "blowdown"]
    p_tank = ["all", "tank_flashing", "tank_working", "tank_breathing"]
    p_pneu = ["all", "pneumatic"]
    p_agr = ["all", "agr"]
    p_dehy = ["all", "dehydrator"]
    p_stoich = ["all", "stoichiometry", "combustion"]
    p_fug = ["all", "fugitive"]
    p_vent = ["all", "dehydrator", "venting", "vented_gas", "well_testing", "workovers", "casing_gas",
              "compressor_venting", "non_routine_venting"]
    p_act = ["all", "pneumatic", "fugitive", "agr", "dehydrator", "loading", "separation", "well_testing", "workovers",
             "casing_gas", "compressor_venting", "non_routine_venting"]

    # the wizard sends one process, several ("flaring,venting") or its own names
    from services.scope1_calc import normalize_process_type

    wanted = {normalize_process_type(p) or p for p in str(process or "all").split(",") if p.strip()} or {"all"}
    if "all" in wanted:
        wanted = {"all"}

    def _for(group):
        return bool(wanted & set(group))

    for c in COLUMNS:
        t = c[2]
        header = c[0]
        if t in ["Core", "Meta"]:
            filtered_columns.append(c)
        elif tier in ("3", "auto"):
            if t == "Unc":
                filtered_columns.append(c)
            elif t == "T1":
                filtered_columns.append(c)
            elif header.startswith("[T3] ") and _for(p_comp):
                filtered_columns.append(c)
            elif header.startswith("[T3-Flare]") and _for(p_flare):
                filtered_columns.append(c)
            elif header.startswith("[T3-Drill]") and _for(p_drill):
                filtered_columns.append(c)
            elif header.startswith("[T3-Comp]") and _for(p_completion):
                filtered_columns.append(c)
            elif header.startswith("[T3-Unload]") and _for(p_unload):
                filtered_columns.append(c)
            elif header.startswith("[T3-BDN]") and _for(p_bdn):
                filtered_columns.append(c)
            elif header.startswith("[T3-Tank]") and _for(p_tank):
                filtered_columns.append(c)
            elif header.startswith("[T3-Pneu]") and _for(p_pneu):
                filtered_columns.append(c)
            elif header.startswith("[T3-AGR]") and _for(p_agr):
                filtered_columns.append(c)
            elif header.startswith("[T3-Dehy]") and _for(p_dehy):
                filtered_columns.append(c)
            elif header.startswith("[T3-Vent]") and _for(p_vent):
                filtered_columns.append(c)
            elif header.startswith("[T3-Stoich]") and _for(p_stoich):
                filtered_columns.append(c)
            elif header.startswith("[T3-Fug]") and _for(p_fug):
                filtered_columns.append(c)
        elif tier == "1":
            if t == "T1" and (header not in ("[T1] operating_hours", "[T1] activity_days") or _for(p_act)):
                filtered_columns.append(c)

    # Use filtered_columns instead of COLUMNS for mapping
    COLUMNS = filtered_columns

    headers = [c[0] for c in COLUMNS]
    descriptions = [c[3] for c in COLUMNS]

    # -----------------------------------------------------------------------
    # SAMPLE ROWS — one per major process type
    # -----------------------------------------------------------------------
    def _row(**kw):
        """Build a row dict keyed by column header labels, filling blanks with '-'."""
        inv = {c[0]: c[1] for c in COLUMNS}  # header → internal_key
        fwd = {c[1]: c[0] for c in COLUMNS}  # internal_key → header
        result = {h: "-" for h in headers}
        for k, v in kw.items():
            hdr = fwd.get(k, k)  # allow passing either internal key or header
            if hdr in result:
                result[hdr] = str(v)
        return [result[h] for h in headers]

    F1, F2 = "Hassi Messaoud Gas Plant", "Hassi R'Mel Hub"  # replace with your own facility names
    sample_rows = [
        # Tier 1 - catalog factors
        _row(date="2024-01", facility_name=F1, process_type="combustion", fuel="Natural Gas", quantity="50000",
             unit="scf", factor_type="default", group="Compressor Station A", equipment="EQ-001",
             equipment_name="CAT G3516 Generator", activity="Upstream & Midstream Gas", region="Ouargla",
             division="Production", field="Hassi Messaoud"),
        _row(date="2024-01", facility_name=F1, process_type="combustion", fuel="Diesel (No. 2 Fuel Oil)", quantity="1200",
             unit="gal", factor_type="default", group="Diesel Generators", equipment="EQ-003"),
        _row(date="2024-01", facility_name=F2, process_type="flaring", fuel="Associated Gas (Flaring)", quantity="80000",
             unit="scf", factor_type="default", group="LP Flare", equipment="EQ-011"),
        _row(date="2024-01", facility_name=F2, process_type="venting", fuel="Natural Gas (Venting/Blowdown)", quantity="200",
             unit="Mscf", factor_type="default", group="Separator depressuring", equipment="EQ-012"),
        _row(date="2024-01", facility_name=F1, process_type="drilling", fuel="Drilling - Mud Degassing (Water Based)",
             quantity="30", unit="days", factor_type="default", group="Well HMD-47", equipment="EQ-020"),
        _row(date="2024-01", facility_name=F2, process_type="pneumatic", fuel="Production high-bleed controller (API study)",
             quantity="12", unit="devices", factor_type="default", group="Control valves", equipment="EQ-071",
             operating_hours="744"),
        _row(date="2024-01", facility_name=F2, process_type="dehydrator", fuel="Glycol dehydrator vent, production (no gas pump)",
             quantity="100", unit="MMscf", factor_type="default", group="TEG Dehydrator D-401", equipment="EQ-091"),
        _row(date="2024-01", facility_name=F1, process_type="fugitive", fuel="Component - Valve (Gas Service)",
             quantity="350", unit="components", factor_type="default", group="Valve Packings", equipment="EQ-101",
             operating_hours="744"),
        # Tier 3 - site data and engineering methods
        _row(date="2024-01", facility_name=F1, process_type="combustion", fuel="Natural Gas", quantity="50000",
             unit="scf", factor_type="specific", group="Compressor Station B", equipment="EQ-002", hhv="1010",
             combustion_efficiency="99.5", c1="87.5", c2="5.2", c3="2.1", c4="1.0", c5="0.5", co2_mol="1.8", n2_mol="1.9"),
        _row(date="2024-01", facility_name=F2, process_type="flaring", fuel="Associated Gas (Flaring)", quantity="120000",
             unit="scf", factor_type="specific", group="HP Flare Stack", equipment="EQ-010", c1="83", c2="6", c3="3",
             c4="2", c5="1", co2_mol="2", n2_mol="3", flare_type="elevated", control_efficiency="98"),
        _row(date="2024-01", facility_name=F1, process_type="drilling", fuel="Drilling - Mud Degassing (Water Based)",
             quantity="30", unit="days", factor_type="specific", group="Well HMD-48", equipment="EQ-021",
             mud_type="water_based"),
        _row(date="2024-01", facility_name=F1, process_type="completions", quantity="25000", unit="scf",
             factor_type="specific", group="Well HMD-55 Completion", equipment="EQ-030", comp_method="metered_volume",
             ch4_content="82", co2_content="3", comp_flare_eff="90"),
        _row(date="2024-01", facility_name=F1, process_type="completions", factor_type="specific",
             group="Well HMD-56 Completion", equipment="EQ-031", comp_method="rate_duration", comp_rate="50",
             comp_rate_unit="Mcf/day", comp_duration="72", ch4_content="84", co2_content="2", comp_flare_eff="85"),
        _row(date="2024-01", facility_name=F1, process_type="unloading", quantity="12", unit="events",
             factor_type="specific", group="Well HMD-22", equipment="EQ-040", unload_depth="8500", unload_diam="4.5",
             unload_press="800", unload_freq="12", unload_flare_eff="0", ch4_content="87", co2_content="1.5"),
        _row(date="2024-01", facility_name=F2, process_type="blowdown", quantity="200", unit="m3", factor_type="specific",
             group="Separator S-101", equipment="EQ-050", blowdown_pressure="450", blowdown_events="8",
             ch4_content="85", co2_content="2", blowdown_temp="65", blowdown_temp_unit="F",
             blowdown_press_unit="psig", z_factor="0.93"),
        _row(date="2024-01", facility_name=F2, process_type="tank_flashing", quantity="5000", unit="bbl",
             factor_type="specific", group="Condensate Storage TK-201", equipment="EQ-060", tank_gor="85",
             tank_ch4_content="65", tank_control_eff="95", tank_unit="bbl", tank_api_gravity="62"),
        _row(date="2024-01", facility_name=F2, process_type="pneumatic", quantity="25", unit="devices",
             factor_type="specific", group="High-Bleed Controllers", equipment="EQ-070", pneu_count="25",
             pneu_bleed_rate="6.0", pneu_bleed_unit="scf", pneu_hours="744", pneu_ch4_content="85"),
        _row(date="2024-01", facility_name=F2, process_type="agr", quantity="15", unit="mmscf", factor_type="specific",
             group="Amine Unit K-301", equipment="EQ-080", agr_co2_in="8.5", agr_co2_out="0.5", agr_unit="mmscf",
             agr_ch4_in="85", agr_ch4_slip="0.001", agr_control_eff="0"),
        _row(date="2024-01", facility_name=F2, process_type="dehydrator", quantity="150", unit="Mscf",
             factor_type="specific", group="TEG Dehydrator D-401", equipment="EQ-090", vent_method="volume",
             ch4_content="87", co2_content="2"),
        _row(date="2024-01", facility_name=F1, process_type="fugitive", quantity="350", unit="components",
             factor_type="specific", group="Wellhead Valve Survey", equipment="EQ-100", fugitive_method="screening",
             component_type="valve", service="gas", m21_below_count="340", m21_above_count="10",
             operating_hours="744"),
        _row(date="2024-01", facility_name=F1, process_type="stoichiometry", quantity="45000", unit="kg",
             factor_type="specific", group="Process Furnace F-501", equipment="EQ-120", carbon_content="0.748"),
    ]

    # Filter sample rows based on requested process and tier
    filtered_rows = []
    for row in sample_rows:
        # Assuming index 2 is 'process_type' (since it is the 3rd column in COLUMNS)
        # We can find the process_type from the dictionary mapping if we constructed it dynamically,
        # but since _row returns a list matched to headers, we need to extract process_type value.
        process_type_idx = headers.index("[Required] process_type")
        factor_type_idx = headers.index("[Required] factor_type")

        row_process = row[process_type_idx]
        row_factor = row[factor_type_idx]

        # Check process match
        process_match = "all" in wanted or row_process in wanted

        # Check tier match
        tier_match = True
        if tier == "1":
            tier_match = row_factor == "default"
        elif tier == "3":
            tier_match = row_factor == "specific"

        if process_match and tier_match:
            filtered_rows.append(row)

    # If filtered_rows is empty (e.g. asking for Tier 1 of a process that only has Tier 3 samples),
    # just show whatever is available for that process.
    if not filtered_rows and "all" not in wanted:
        for row in sample_rows:
            if row[headers.index("[Required] process_type")] in wanted:
                filtered_rows.append(row)

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(headers)
    cw.writerow(descriptions)
    for row in filtered_rows:
        cw.writerow(row)

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=scope1_emissions_template.csv"
        },
    )
