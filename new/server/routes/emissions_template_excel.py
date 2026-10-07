"""Excel import template download.

Split out of routes/emissions.py unchanged (hardening plan, task 5.3). The route is
registered on the same ``emissions_bp`` blueprint, so URLs and endpoint names are the same.
"""
from flask import request, send_file

from . import emissions_bp


@emissions_bp.route("/template/excel", methods=["GET"])
def get_excel_template():
    tier = request.args.get("tier", "all")
    process = request.args.get("process", "all")

    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.comments import Comment
    from openpyxl.utils import get_column_letter
    import openpyxl.utils

    wb = openpyxl.Workbook()

    # ─── Colour palette (Modern Green Environmental Theme) ───
    GREEN_DARK = "1B5E20"  # dark forest green – headers
    GREEN_MID = "2E7D32"  # medium green – sub-headers / Tier-3 sheet headers
    GREEN_LIGHT = "C8E6C9"  # pale green – alternating data rows
    WHITE = "FFFFFF"
    GREY_LIGHT = "F5F5F5"
    YELLOW_HINT = "FFFDE7"  # required-field highlight
    BLUE_HINT = "E3F2FD"  # info / reference cells
    ORANGE_WARN = "FF6F00"  # warning accent

    def hdr_style(cell, bg=GREEN_DARK, fg=WHITE, sz=11, bold=True, wrap=True):
        cell.font = Font(bold=bold, color=fg, size=sz, name="Calibri")
        cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=wrap
        )

    def sub_hdr(cell, bg=GREEN_MID):
        hdr_style(cell, bg=bg, fg=WHITE, sz=10, bold=True)

    def info_cell(cell, bg=BLUE_HINT, fg="1A237E"):
        cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        cell.font = Font(color=fg, size=10, name="Calibri")
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    def req_cell(cell, bg=YELLOW_HINT):
        cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        cell.font = Font(color="B71C1C", size=10, bold=True, name="Calibri")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    thin = Side(style="thin", color="BDBDBD")
    thick = Side(style="medium", color=GREEN_DARK)
    std_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    thick_border = Border(left=thick, right=thick, top=thick, bottom=thick)

    def add_comment(cell, text, author="GHG Platform"):
        c = Comment(text, author)
        c.width = 300
        c.height = 120
        cell.comment = c

    # ═══════════════════════════════════════════════════════════
    # SHEET 1: INSTRUCTIONS
    # ═══════════════════════════════════════════════════════════
    ws_inst = wb.active
    ws_inst.title = "📋 Instructions"
    ws_inst.sheet_view.showGridLines = False

    # Title banner
    ws_inst.merge_cells("A1:H1")
    t = ws_inst["A1"]
    t.value = "GHG Emissions Data Entry Template – User Guide"
    t.font = Font(bold=True, size=16, color=WHITE, name="Calibri")
    t.fill = PatternFill(
        start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid"
    )
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws_inst.row_dimensions[1].height = 40

    ws_inst.merge_cells("A2:H2")
    sub = ws_inst["A2"]
    sub.value = (
        "API Compendium 2021 – Scope 1 Direct Emissions – Monthly Reporting Template"
    )
    sub.font = Font(bold=False, size=11, color=WHITE, name="Calibri", italic=True)
    sub.fill = PatternFill(
        start_color=GREEN_MID, end_color=GREEN_MID, fill_type="solid"
    )
    sub.alignment = Alignment(horizontal="center", vertical="center")
    ws_inst.row_dimensions[2].height = 22

    # Section: Quick Start
    ws_inst.merge_cells("A4:H4")
    sec = ws_inst["A4"]
    sec.value = "🚀  QUICK START"
    hdr_style(sec, bg=GREEN_MID, sz=12)
    ws_inst.row_dimensions[4].height = 28

    steps = [
        (
            "Step 1",
            "Fill in the '🏢 Facilities' sheet with your facility and equipment names. These will drive the dropdowns in the data sheet.",
        ),
        (
            "Step 2",
            "Go to the '📊 Data Entry' sheet. Each row = one piece of equipment for one calendar month.",
        ),
        (
            "Step 3",
            "Use the dropdowns in columns C (Process Type), D (Factor Type), and M (Unit) to select valid values.",
        ),
        (
            "Step 4",
            "For Tier 3 (Engineering) calculations, fill in the matching process tab (e.g. '⚙ Combustion', '⚙ Flaring').",
        ),
        (
            "Step 5",
            "Save the file and upload it using the 'Upload' button in the GHG Platform application.",
        ),
    ]
    for r, (s, d) in enumerate(steps, 5):
        ws_inst[f"A{r}"].value = s
        ws_inst[f"A{r}"].font = Font(
            bold=True, color=GREEN_DARK, name="Calibri", size=10
        )
        ws_inst[f"A{r}"].alignment = Alignment(vertical="top")
        ws_inst.merge_cells(f"B{r}:H{r}")
        ws_inst[f"B{r}"].value = d
        ws_inst[f"B{r}"].font = Font(name="Calibri", size=10)
        ws_inst[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws_inst.row_dimensions[r].height = 28

    # Section: Column Reference
    ws_inst.merge_cells(f"A{len(steps)+6}:H{len(steps)+6}")
    sec2 = ws_inst[f"A{len(steps)+6}"]
    sec2.value = "📑  DATA ENTRY COLUMN REFERENCE"
    hdr_style(sec2, bg=GREEN_MID, sz=12)
    ws_inst.row_dimensions[len(steps) + 6].height = 28

    col_ref = [
        (
            "A",
            "Date (YYYY-MM)",
            "Required",
            "Year and month: e.g. 2024-01 for January 2024. Must be in YYYY-MM format.",
        ),
        (
            "B",
            "Activity",
            "Required",
            "Business activity/segment: e.g. 'Exploration & Production', 'Midstream', 'Downstream'.",
        ),
        (
            "C",
            "Division",
            "Required",
            "Organizational unit/division: e.g. 'Production', 'Association'.",
        ),
        (
            "D",
            "Field",
            "Optional",
            "Field or project name: e.g. 'Hassi Messaoud', 'South Field'.",
        ),
        (
            "E",
            "Region / Facility",
            "Required",
            "Name of the facility as registered in the GHG Platform. Must match exactly.",
        ),
        (
            "F",
            "Emission Source (Group)",
            "Optional",
            "Functional grouping for the emission source (e.g. 'Compressor Station A').",
        ),
        (
            "G",
            "Equipment Name",
            "Required",
            "Descriptive name of the equipment (e.g. 'Caterpillar G3516 Engine #3').",
        ),
        (
            "H",
            "Equipment ID",
            "Optional",
            "Asset tag or unique ID (e.g. 'EQ-0042'). Used for deduplication checks.",
        ),
        (
            "I",
            "Process Type",
            "Required",
            "Select from dropdown. Options: Combustion, Flaring, Venting, Pneumatic Devices, etc.",
        ),
        (
            "J",
            "Activity / Fuel",
            "Required",
            "Fuel or gas type consumed/emitted. Must match supported factors (e.g. 'Natural Gas', 'Diesel').",
        ),
        (
            "K",
            "Factor Type",
            "Required",
            "Select 'default' (API Compendium factor) or 'custom' (user-defined factor saved in platform).",
        ),
        (
            "L",
            "Quantity",
            "Required",
            "Numeric value of the activity data for the month (volume, mass, or count).",
        ),
        (
            "M",
            "Unit",
            "Required",
            "Unit of the quantity. Must match the selected fuel factor unit (e.g. scf for gas, gal for liquid).",
        ),
    ]
    r_start = len(steps) + 7
    # Header row
    for c, (col, name, req, desc) in enumerate(col_ref, 0):
        ws_inst[f"A{r_start+c}"].value = col
        ws_inst[f"A{r_start+c}"].font = Font(
            bold=True, color=WHITE, name="Calibri", size=10
        )
        ws_inst[f"A{r_start+c}"].fill = PatternFill(
            start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid"
        )
        ws_inst[f"A{r_start+c}"].alignment = Alignment(
            horizontal="center", vertical="center"
        )
        ws_inst[f"B{r_start+c}"].value = name
        ws_inst[f"B{r_start+c}"].font = Font(bold=True, name="Calibri", size=10)
        req_color = "B71C1C" if req == "Required" else "37474F"
        ws_inst[f"C{r_start+c}"].value = req
        ws_inst[f"C{r_start+c}"].font = Font(
            color=req_color, bold=True, name="Calibri", size=10
        )
        ws_inst[f"C{r_start+c}"].alignment = Alignment(horizontal="center")
        ws_inst.merge_cells(f"D{r_start+c}:H{r_start+c}")
        ws_inst[f"D{r_start+c}"].value = desc
        ws_inst[f"D{r_start+c}"].font = Font(name="Calibri", size=10)
        ws_inst[f"D{r_start+c}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws_inst.row_dimensions[r_start + c].height = 30

    ws_inst.column_dimensions["A"].width = 8
    ws_inst.column_dimensions["B"].width = 30
    ws_inst.column_dimensions["C"].width = 12
    for c in "DEFGH":
        ws_inst.column_dimensions[c].width = 22

    # ═══════════════════════════════════════════════════════════
    # SHEET 2: FACILITIES REFERENCE
    # ═══════════════════════════════════════════════════════════
    ws_fac = wb.create_sheet("🏢 Facilities")
    ws_fac.sheet_view.showGridLines = False

    ws_fac.merge_cells("A1:E1")
    fac_title = ws_fac["A1"]
    fac_title.value = "Facility & Equipment Reference  ← Fill this sheet first"
    fac_title.font = Font(bold=True, size=13, color=WHITE, name="Calibri")
    fac_title.fill = PatternFill(
        start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid"
    )
    fac_title.alignment = Alignment(horizontal="center", vertical="center")
    ws_fac.row_dimensions[1].height = 35

    fac_cols = ["Facility Name", "Activity / Segment", "Division", "Field", "Notes"]
    for i, h in enumerate(fac_cols, 1):
        c = ws_fac.cell(row=2, column=i, value=h)
        hdr_style(c, bg=GREEN_MID)
        ws_fac.column_dimensions[get_column_letter(i)].width = 30

    sample_facs = [
        (
            "Field Alpha Processing Plant",
            "Exploration & Production",
            "Production",
            "Hassi Messaoud",
            "Main separation facility",
        ),
        (
            "Hassi R'mel Gas Hub",
            "Exploration & Production",
            "Production",
            "Hassi R'mel",
            "Gas injection + compression",
        ),
        (
            "South Field Compressor Stn",
            "Exploration & Production",
            "Production",
            "South Field",
            "4x Cat G3516 engines",
        ),
    ]
    for r, row in enumerate(sample_facs, 3):
        for c, val in enumerate(row, 1):
            cell = ws_fac.cell(row=r, column=c, value=val)
            cell.font = Font(name="Calibri", size=10, italic=True, color="546E7A")
            cell.fill = PatternFill(
                start_color=GREY_LIGHT, end_color=GREY_LIGHT, fill_type="solid"
            )
            cell.border = std_border
        ws_fac.row_dimensions[r].height = 20

    # Leave 97 blank editable rows
    for r in range(6, 103):
        for c in range(1, 6):
            cell = ws_fac.cell(row=r, column=c)
            cell.border = std_border
            cell.fill = PatternFill(
                start_color=WHITE, end_color=WHITE, fill_type="solid"
            )
        ws_fac.row_dimensions[r].height = 18

    ws_fac.freeze_panes = "A3"

    # Named range for facility names (col A rows 3–102) → used for dropdown in Data sheet
    # (openpyxl doesn't support dynamic named ranges well; we define a fixed range)
    wb.create_named_range("FacilityList", ws_fac, "$A$3:$A$102")

    # ═══════════════════════════════════════════════════════════
    # SHEET 3: MAIN DATA ENTRY
    # ═══════════════════════════════════════════════════════════
    ws_data = wb.create_sheet("📊 Data Entry")
    ws_data.sheet_view.showGridLines = False

    DATA_COLS = [
        # (header, width, required)
        ("Date\n(YYYY-MM)", 14, True),
        ("Activity", 22, True),
        ("Region", 20, True),
        ("Division", 20, True),
        ("Field", 20, False),
        ("Facility Name", 28, True),
        ("Emission Source\n(Group)", 24, False),
        ("Equipment Name", 28, True),
        ("Equipment ID", 18, False),
        ("Process Type", 24, True),
        ("Activity / Fuel", 24, True),
        ("Factor Type", 16, True),
        ("Quantity", 14, True),
        ("Unit", 14, True),
        ("Operating Hours", 14, False),
        ("Notes / Comments", 30, False),
    ]
    COL = {name: get_column_letter(i) for i, (name, _, _) in enumerate(DATA_COLS, 1)}

    # Freeze pane A2
    ws_data.freeze_panes = "A2"

    # Row 1 – Title banner
    ws_data.merge_cells(f"A1:{get_column_letter(len(DATA_COLS))}1")
    banner = ws_data["A1"]
    banner.value = "📊  GHG Emissions – Monthly Data Entry   |   One row = One equipment × One month   |   Columns in RED are required"
    banner.font = Font(bold=True, size=11, color=WHITE, name="Calibri")
    banner.fill = PatternFill(
        start_color=GREEN_DARK, end_color=GREEN_DARK, fill_type="solid"
    )
    banner.alignment = Alignment(horizontal="center", vertical="center")
    ws_data.row_dimensions[1].height = 30

    # Row 2 – Column headers
    for i, (col_name, col_w, req) in enumerate(DATA_COLS, 1):
        cell = ws_data.cell(row=2, column=i, value=col_name)
        bg = GREEN_MID if not req else "1B5E20"
        hdr_style(cell, bg=bg, sz=10)
        ws_data.column_dimensions[get_column_letter(i)].width = col_w
        ws_data.row_dimensions[2].height = 36

        # Header comments
        hints = {
            "Date\n(YYYY-MM)": "Format: YYYY-MM e.g. 2024-01",
            "Facility Name": "Must exactly match the name of a facility / region in the platform",
            "Equipment ID": "Links the row to its parameters on the Tier 3 sheet",
            "Process Type": "Select from the list: Combustion, Flaring, Venting, etc.",
            "Activity / Fuel": "Emission factor name as listed in the manual form, e.g. Natural Gas, Diesel (No. 2 Fuel Oil), Associated Gas (Flaring); for custom, the saved factor name",
            "Factor Type": "default = API Compendium factor | custom = your saved factor | specific = Tier 3 (parameters on the Tier 3 sheet)",
            "Quantity": "Activity of the month (e.g. 50000)",
            "Unit": "e.g. scf, Mscf, m3, gal, bbl, kg, tonne, days, devices",
            "Operating Hours": "Hours in the month for per-hour methods (pneumatic controllers, leaks), e.g. 744",
        }
        if col_name in hints:
            add_comment(cell, hints[col_name])

    # Data Validations

    dv_process = DataValidation(
        type="list",
        formula1='"Combustion,Flaring,Fugitive Emissions,Venting,Well Completions & Workovers,Liquids Unloading,Dehydrator,Pneumatic Device,Storage Tank - Flashing,Storage Tank - Working Losses,Storage Tank - Breathing,Drilling Operations,Acid Gas Removal (AGR),Mobile Combustion,Loading Losses,Wastewater / Separation"',
        allow_blank=True,
        showInputMessage=True,
        promptTitle="Process Type",
        prompt="Select the emission process type.",
        showErrorMessage=True,
        errorTitle="Invalid Value",
        error="Please select a value from the dropdown list.",
    )
    ws_data.add_data_validation(dv_process)
    dv_process.sqref = f"{COL['Process Type']}3:{COL['Process Type']}1048576"

    dv_factor = DataValidation(
        type="list",
        formula1='"default,custom,specific"',
        allow_blank=True,
        showInputMessage=True,
        promptTitle="Factor Type",
        prompt="'default' = API Compendium 2021 factor.\n'custom' = factor saved in your GHG Platform account.\n'specific' = Tier 3 (Tier 3 sheet).",
        showErrorMessage=True,
        errorTitle="Invalid Value",
        error="Please select 'default', 'custom' or 'specific'.",
    )
    ws_data.add_data_validation(dv_factor)
    dv_factor.sqref = f"{COL['Factor Type']}3:{COL['Factor Type']}1048576"

    dv_unit = DataValidation(
        type="list",
        formula1='"scf,Mscf,MMscf,m3,MMBtu,gal,bbl,kg,tonne,days,devices,components,events,km,miles"',
        allow_blank=True,
        showInputMessage=True,
        promptTitle="Unit",
        prompt="Select the unit that matches your quantity and fuel type.",
        showErrorMessage=False,  # allow custom units too
    )
    ws_data.add_data_validation(dv_unit)
    dv_unit.sqref = f"{COL['Unit']}3:{COL['Unit']}1048576"

    dv_date = DataValidation(
        type="textLength",
        operator="greaterThanOrEqual",
        formula1="7",
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Date Format",
        error="Please enter a date in YYYY-MM format (e.g. 2024-01).",
    )
    ws_data.add_data_validation(dv_date)
    date_col = COL["Date\n(YYYY-MM)"]
    dv_date.sqref = f"{date_col}3:{date_col}1048576"

    dv_qty = DataValidation(
        type="decimal",
        operator="greaterThanOrEqual",
        formula1="0",
        allow_blank=True,
        showErrorMessage=True,
        errorTitle="Invalid Quantity",
        error="Quantity must be a non-negative number.",
    )
    ws_data.add_data_validation(dv_qty)
    dv_qty.sqref = f"{COL['Quantity']}3:{COL['Quantity']}1048576"

    # ── Sample data rows ──
    # (date, activity, region, division, field, facility, group, equipment name, equipment ID, process,
    #  activity / fuel, factor type, quantity, unit, operating hours, notes); process key for the filter
    samples = [
        ("combustion", ["2024-01", "Exploration & Production", "Ouargla", "Production", "Hassi Messaoud",
                        "Field Alpha Processing Plant", "Compressor Station A", "Caterpillar G3516 #1", "EQ-001",
                        "Combustion", "Natural Gas", "default", 50000, "scf", None, "Tier 1 - catalog factor"]),
        ("flaring", ["2024-01", "Exploration & Production", "Ouargla", "Production", "Hassi Messaoud",
                     "Field Alpha Processing Plant", "Flare Stack", "HP Flare Stack - West", "EQ-002", "Flaring",
                     "Associated Gas (Flaring)", "specific", 120000, "scf", None,
                     "Tier 3 - gas composition on the Tier 3 sheet"]),
        ("venting", ["2024-01", "Exploration & Production", "Ouargla", "Production", "Hassi Messaoud",
                     "Field Alpha Processing Plant", "Production Separator", "3-Phase Separator #2", "EQ-003",
                     "Venting", "Natural Gas (Venting/Blowdown)", "default", 8000, "m3", None,
                     "Venting from separator depressuring"]),
        ("tank_flashing", ["2024-01", "Exploration & Production", "Ouargla", "Production", "Hassi Messaoud",
                           "Field Alpha Processing Plant", "Storage", "Crude Oil Storage Tank #5", "EQ-004",
                           "Storage Tank - Flashing", "Tank - Flash Emissions (Oil)", "default", 9500, "bbl", None,
                           "Monthly oil throughput"]),
        ("pneumatic", ["2024-01", "Exploration & Production", "South", "Production", "South Field",
                       "South Field Compressor Stn", "Pneumatics", "Control Valve Bank A", "EQ-005",
                       "Pneumatic Device", "Production high-bleed controller (API study)", "default", 12, "devices",
                       744, "12 high-bleed controllers, 744 h in January"]),
    ]

    from services.scope1_calc import normalize_process_type

    wanted = {normalize_process_type(q) or q for q in str(process or "all").split(",") if q.strip()} or {"all"}
    filtered_samples = [row for key, row in samples if "all" in wanted or key in wanted]
    if tier == "1":
        filtered_samples = [row for row in filtered_samples if row[11] != "specific"]
    if not filtered_samples:
        filtered_samples = [row for _, row in samples if row[11] != "specific"]  # fallback if no match

    for r, row in enumerate(filtered_samples, 3):
        for c, val in enumerate(row, 1):
            cell = ws_data.cell(row=r, column=c, value=val)
            cell.border = std_border
            cell.font = Font(name="Calibri", size=10, italic=True, color="37474F")
            bg = GREEN_LIGHT if r % 2 == 1 else WHITE
            cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
            cell.alignment = Alignment(vertical="center", wrap_text=False)
        ws_data.row_dimensions[r].height = 18

    # Empty rows with alternating shading and borders
    for r in range(8, 2003):
        for c in range(1, len(DATA_COLS) + 1):
            cell = ws_data.cell(row=r, column=c)
            cell.border = std_border
            bg = GREEN_LIGHT if r % 2 == 0 else WHITE
            cell.fill = PatternFill(start_color=bg, end_color=bg, fill_type="solid")
        ws_data.row_dimensions[r].height = 18

    # ═══════════════════════════════════════════════════════════
    # SHEET 4+: TIER 3 ENGINEERING SHEETS (one per process)
    # ═══════════════════════════════════════════════════════════
    if tier != "1":
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
        p_completion = ["all", "completions", "unloading"]
        p_bdn = ["all", "venting", "blowdown"]
        p_tank = ["all", "tank_flashing", "tank_working", "tank_breathing"]
        p_pneu = ["all", "pneumatic"]
        p_agr = ["all", "agr"]
        p_dehy = ["all", "dehydrator"]
        p_fug = ["all", "fugitive"]

        base_cols = [
            ("Equipment ID", 18, "Link to Equipment ID in Data Entry sheet"),
            ("Date (YYYY-MM)", 14, "Must match the date in Data Entry sheet"),
            ("Process Type", 18, "Optional Reference"),
            ("User Uncertainty CO2 (%)", 22, "Optional: Override CO2 Uncertainty"),
            ("User Uncertainty CH4 (%)", 22, "Optional: Override CH4 Uncertainty"),
            ("User Uncertainty N2O (%)", 22, "Optional: Override N2O Uncertainty"),
        ]

        p_unload = ["all", "unloading"]
        t3_params = [
            ("C1 (mol %)", 14, "Methane (CH4) mole %", p_comp),
            ("C2 (mol %)", 14, "Ethane mole %", p_comp),
            ("C3 (mol %)", 14, "Propane mole %", p_comp),
            ("C4 (mol %)", 14, "Butane mole %", p_comp),
            ("C5 (mol %)", 14, "Pentane mole %", p_comp),
            ("C6 (mol %)", 14, "Hexane mole %", p_comp),
            ("C7 (mol %)", 14, "Heptane mole %", p_comp),
            ("C8 (mol %)", 14, "Octane mole %", p_comp),
            ("C9 (mol %)", 14, "Nonane mole %", p_comp),
            ("C10 (mol %)", 14, "Decane+ mole %", p_comp),
            ("CO2 (mol %)", 14, "CO2 mole % of the gas", p_comp),
            ("N2 (mol %)", 14, "Nitrogen mole %", p_comp),
            ("Flare Type", 18, "elevated | enclosed_ground | air_assisted | steam_assisted", p_flare),
            ("Flare Control Efficiency (%)", 22, "Destruction efficiency (%)", p_flare),
            ("Tank GOR", 14, "Flash gas-to-oil ratio (scf/bbl)", p_tank),
            ("Tank CH4 Content (%)", 18, "CH4 mole % of the flash gas", p_tank),
            ("Tank Control Eff (%)", 18, "Vapour control efficiency (%)", p_tank),
            ("Pneumatic Count", 16, "Number of identical devices", p_pneu),
            ("Bleed Rate (scf/hr)", 20, "Measured bleed rate per device", p_pneu),
            ("Hours", 10, "Operating hours in the month", p_pneu),
            ("Well Depth (ft)", 16, "Liquids unloading: well depth", p_unload),
            ("Diameter (in)", 14, "Liquids unloading: casing diameter", p_unload),
            ("Pressure (psi)", 16, "Liquids unloading: shut-in pressure (psig)", p_unload),
            ("Events", 10, "Liquids unloading: events in the month", p_unload),
            ("Fugitive Method", 18, "screening | correlation | ogi | measurement", p_fug),
            ("Component Type", 16, "valve | connector | flange | open_ended_line | pump_seal | other", p_fug),
            ("Service", 12, "gas | light_oil | heavy_oil | water_oil", p_fug),
            ("M21 Below Count", 16, "Components screened below 10,000 ppmv", p_fug),
            ("M21 Above Count", 16, "Components screened at or above 10,000 ppmv", p_fug),
            ("CO2 In (%)", 14, "AGR: CO2 mole % in the feed", p_agr),
            ("CO2 Out (%)", 14, "AGR: CO2 mole % in the sweet gas", p_agr),
        ]

        filtered_cols = [c for c in base_cols]
        for col_def in t3_params:
            if "all" in wanted or wanted & set(col_def[3]):
                filtered_cols.append((col_def[0], col_def[1], col_def[2]))

        TIER3_SHEETS = {
            "⚙ Tier 3 Calculations": {
                "desc": "Engineering parameters for Tier 3 calculations and Gas Composition data.",
                "cols": filtered_cols,
            }
        }

        for sheet_name, cfg in TIER3_SHEETS.items():
            ws_t3 = wb.create_sheet(sheet_name)
            ws_t3.sheet_view.showGridLines = False
            ws_t3.freeze_panes = "A3"

            col_count = len(cfg["cols"])
            ws_t3.merge_cells(f"A1:{get_column_letter(col_count)}1")
            t3_title = ws_t3["A1"]
            t3_title.value = (
                f"{sheet_name.replace('⚙ ', '')} – Tier 3 Engineering Parameters"
            )
            t3_title.font = Font(bold=True, size=13, color=WHITE, name="Calibri")
            t3_title.fill = PatternFill(
                start_color=GREEN_MID, end_color=GREEN_MID, fill_type="solid"
            )
            t3_title.alignment = Alignment(horizontal="center", vertical="center")
            ws_t3.row_dimensions[1].height = 35

            ws_t3.merge_cells(f"A2:{get_column_letter(col_count)}2")
            desc_c = ws_t3["A2"]
            desc_c.value = cfg["desc"]
            desc_c.font = Font(italic=True, size=10, color="37474F", name="Calibri")
            desc_c.fill = PatternFill(
                start_color=GREEN_LIGHT, end_color=GREEN_LIGHT, fill_type="solid"
            )
            desc_c.alignment = Alignment(horizontal="center", vertical="center")
            ws_t3.row_dimensions[2].height = 22

            for i, (col_name, col_w, col_hint) in enumerate(cfg["cols"], 1):
                cell = ws_t3.cell(row=3, column=i, value=col_name)
                hdr_style(cell, bg=GREEN_DARK, sz=10)
                ws_t3.column_dimensions[get_column_letter(i)].width = col_w
                ws_t3.row_dimensions[3].height = 32
                add_comment(cell, col_hint)

            # Define samples for Tier 3
            t3_samples = [
                (
                    "EQ-002",
                    "2024-01",
                    "Flaring",
                    "flaring",
                    {
                        "Flare Type": "elevated",
                        "Flare Control Efficiency (%)": "98",
                        "C1 (mol %)": "83",
                        "C2 (mol %)": "6",
                        "C3 (mol %)": "3",
                        "C4 (mol %)": "2",
                        "C5 (mol %)": "1",
                        "CO2 (mol %)": "2",
                        "N2 (mol %)": "3",
                    },
                ),
            ]
            filtered_t3_samples = [t for t in t3_samples if "all" in wanted or t[3] in wanted]

            row_idx = 4
            for s in filtered_t3_samples:
                # Map s[4] dict to columns
                row_data = {
                    "Equipment ID": s[0],
                    "Date (YYYY-MM)": s[1],
                    "Process Type": s[2],
                    **s[4],
                }

                for c_idx, (col_name, _, _) in enumerate(cfg["cols"], 1):
                    val = row_data.get(col_name, "")
                    cell = ws_t3.cell(row=row_idx, column=c_idx, value=val)
                    cell.border = std_border
                    cell.font = Font(
                        name="Calibri", size=10, italic=True, color="37474F"
                    )
                    bg = GREEN_LIGHT if row_idx % 2 == 1 else WHITE
                    cell.fill = PatternFill(
                        start_color=bg, end_color=bg, fill_type="solid"
                    )
                    cell.alignment = Alignment(vertical="center", wrap_text=False)
                ws_t3.row_dimensions[row_idx].height = 18
                row_idx += 1

            # Empty data rows
            for r in range(row_idx, 1004):
                for c in range(1, col_count + 1):
                    cell = ws_t3.cell(row=r, column=c)
                    cell.border = std_border
                    bg = GREEN_LIGHT if r % 2 == 0 else WHITE
                    cell.fill = PatternFill(
                        start_color=bg, end_color=bg, fill_type="solid"
                    )
                ws_t3.row_dimensions[r].height = 18

    # ─── Save to in-memory buffer (no leaking temp files on disk, M2) ───
    # Ensure exactly 3 sheets as requested (remove instructions)
    if "📋 Instructions" in wb.sheetnames:
        del wb["📋 Instructions"]

    import io
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return send_file(
        bio,
        as_attachment=True,
        download_name="GHG_Emissions_Template_v2.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
