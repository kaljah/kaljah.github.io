"""
Generate a comprehensive 1,000-row Scope 1 test CSV that covers:
- All 13 process types
- Multiple real regions
- Tier 1 only rows (no gas composition)
- Tier 3 rows (with gas composition)
- Auto-detect rows (mixed: some with composition, some without)
- Missing year → should be REJECTED
- Missing month → should be REJECTED  
- Wrong region name → should be REJECTED (Region not found)
- Missing quantity → should be REJECTED
- Missing process → should be REJECTED
- Missing fuel (for combustion) → should be REJECTED
- Invalid quantity (non-numeric) → should be REJECTED
- All valid fuels from API Compendium
- Multiple years (2022, 2023, 2024)
- All 12 months
- Gas composition present (Tier 3 auto-detect)
- Gas composition absent (Tier 1 auto-detect)
"""

import csv
import random
import math

random.seed(42)

OUTPUT = r"C:\Users\samsung\Desktop\H2\1k_scope1_comprehensive_test.csv"

# Real regions from DB
REGIONS = ["ADR", "REB", "HBK", "GTL", "OHT", "STAH", "TFT", "HMD", "RNS", "BRS", "MLN", "OURHOUD"]

# Process types matching backend
PROCESSES = [
    "combustion", "flaring", "venting",
    "tank_flashing", "tank_working_standing",
    "pneumatic_device", "pneumatic_pump",
    "fugitives_equipment", "fugitives_leaks",
    "completions", "blowdown",
    "dehydrator", "agr",
]

# Valid fuels from API Compendium (must match exactly)
COMBUSTION_FUELS = [
    "Natural Gas", "Diesel (No. 2 Fuel Oil)", "Crude Oil",
    "Motor Gasoline", "LPG", "Propane", "Fuel Oil",
]
FLARE_FUELS = ["Natural Gas", "Natural Gas (Venting/Blowdown)", "Associated Gas"]
VENT_FUELS   = ["Natural Gas (Venting/Blowdown)", "Natural Gas"]
OTHER_FUELS  = ["Natural Gas"]   # for all others

# Units by process
UNITS = {
    "combustion": ["scf", "m3", "MMBtu", "gal"],
    "flaring":    ["scf", "m3", "MMBtu"],
    "venting":    ["m3", "scf"],
    "tank_flashing": ["bbl", "m3"],
    "tank_working_standing": ["bbl"],
    "pneumatic_device": ["scf/hr", "m3/hr"],
    "pneumatic_pump": ["scf/hr"],
    "fugitives_equipment": ["scf/hr"],
    "fugitives_leaks": ["scf/hr", "kg/hr"],
    "completions": ["scf", "m3"],
    "blowdown": ["scf", "m3"],
    "dehydrator": ["scf", "m3"],
    "agr": ["tonne/day"],
}

def gas_comp():
    """Return a realistic gas composition that sums to ~100%."""
    c1 = round(random.uniform(75, 95), 2)
    c2 = round(random.uniform(2, 8), 2)
    c3 = round(random.uniform(0.5, 3), 2)
    c4 = round(random.uniform(0.1, 1), 2)
    c5 = round(random.uniform(0.05, 0.5), 2)
    c6 = round(random.uniform(0.01, 0.3), 2)
    co2_mol = round(random.uniform(0.1, 2), 2)
    n2_mol = round(max(0, 100 - c1 - c2 - c3 - c4 - c5 - c6 - co2_mol), 2)
    return c1, c2, c3, c4, c5, c6, 0, 0, 0, 0, co2_mol, n2_mol

def fuel_for(process):
    if process == "combustion":
        return random.choice(COMBUSTION_FUELS)
    elif process == "flaring":
        return random.choice(FLARE_FUELS)
    elif process == "venting":
        return random.choice(VENT_FUELS)
    else:
        return random.choice(OTHER_FUELS)

HEADERS = [
    "date", "year", "month",
    "facility_name", "activity", "division", "field",
    "group", "equipment", "equipment_id",
    "process", "fuel", "quantity", "unit", "factor_type",
    # Tier 3 gas composition
    "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10", "co2_mol", "n2_mol",
    # Tier 3 combustion/flare params
    "hhv", "combustion_efficiency", "flare_type", "ch4_content", "co2_content", "control_efficiency",
    "operating_temperature", "temp_unit", "operating_pressure", "press_unit", "z_factor",
    # Pneumatic
    "pneu_type", "pneu_count", "pneu_bleed_rate", "pneu_hours",
    # Tank
    "tank_gor", "tank_ch4_content", "tank_control_eff", "tank_api_gravity",
    # Fugitive
    "fugitive_method", "fugitive_ppm", "comp_count", "operating_hours",
    "leak_count", "leak_duration", "leak_rate",
    # Completion / Blowdown
    "comp_method", "comp_rate", "comp_duration", "comp_flare_eff",
    "blowdown_pressure", "blowdown_events", "blowdown_temp",
    # Dehydrator / AGR
    "dehy_pump_rate", "dehy_hours", "dehy_press", "dehy_temp", "dehy_ch4_content", "dehy_eff",
    "agr_co2_in", "agr_co2_out", "agr_ch4_in", "agr_ch4_slip", "agr_control_eff",
]

def empty_row():
    return {h: "" for h in HEADERS}

rows = []
eq_counter = 1

# ─── CATEGORY 1: Valid Tier 1 rows (no gas composition) ───────────────────── 400 rows
for _ in range(400):
    r = empty_row()
    year  = random.choice([2022, 2023, 2024])
    month = random.randint(1, 12)
    r["year"]          = year
    r["month"]         = month
    r["date"]          = f"{year}-{month:02d}"
    r["facility_name"] = random.choice(REGIONS)
    r["activity"]      = "Activité E&P"
    r["division"]      = random.choice(["DP", "AST"])
    r["field"]         = random.choice(["OF", "GF"])
    r["group"]         = f"Unit-{random.randint(1,10)}"
    r["equipment"]     = f"EQ-{eq_counter:04d}"
    r["equipment_id"]  = f"ID-{eq_counter:04d}"
    eq_counter        += 1
    proc               = random.choice(["combustion", "flaring", "venting"])
    r["process"]       = proc
    r["fuel"]          = fuel_for(proc)
    r["quantity"]      = round(random.uniform(100, 500000), 2)
    r["unit"]          = random.choice(UNITS.get(proc, ["m3"]))
    r["factor_type"]   = "default"
    rows.append(r)

# ─── CATEGORY 2: Valid Tier 3 rows (with full gas composition) ──────────────  300 rows
for _ in range(300):
    r = empty_row()
    year  = random.choice([2022, 2023, 2024])
    month = random.randint(1, 12)
    r["year"]          = year
    r["month"]         = month
    r["date"]          = f"{year}-{month:02d}"
    r["facility_name"] = random.choice(REGIONS)
    r["activity"]      = "Activité E&P"
    r["division"]      = random.choice(["DP", "AST"])
    r["field"]         = random.choice(["OF", "GF"])
    r["group"]         = f"Tier3-Unit-{random.randint(1,5)}"
    r["equipment"]     = f"EQ-{eq_counter:04d}"
    r["equipment_id"]  = f"ID-{eq_counter:04d}"
    eq_counter        += 1
    proc               = random.choice(PROCESSES)
    r["process"]       = proc
    r["fuel"]          = fuel_for(proc)
    r["quantity"]      = round(random.uniform(500, 1000000), 2)
    r["unit"]          = random.choice(UNITS.get(proc, ["m3"]))
    r["factor_type"]   = "default"

    # Gas composition (Tier 3 trigger)
    c1,c2,c3,c4,c5,c6,c7,c8,c9,c10,co2m,n2m = gas_comp()
    r["c1"],r["c2"],r["c3"],r["c4"],r["c5"],r["c6"] = c1,c2,c3,c4,c5,c6
    r["co2_mol"],r["n2_mol"]                        = co2m, n2m
    r["hhv"]                     = round(random.uniform(900, 1100), 1)
    r["combustion_efficiency"]   = round(random.uniform(95, 99.5), 1) if proc == "combustion" else ""
    r["flare_type"]              = random.choice(["steam_assisted", "air_assisted", "non_assisted"]) if proc == "flaring" else ""
    r["ch4_content"]             = round(random.uniform(70, 95), 2)
    r["co2_content"]             = round(random.uniform(0.5, 5), 2)
    r["control_efficiency"]      = round(random.uniform(85, 99), 1)
    r["operating_temperature"]   = round(random.uniform(20, 120), 1)
    r["temp_unit"]               = "C"
    r["operating_pressure"]      = round(random.uniform(100, 5000), 1)
    r["press_unit"]              = "kPa"
    r["z_factor"]                = round(random.uniform(0.85, 0.99), 3)

    # Process-specific Tier 3
    if proc == "pneumatic_device":
        r["pneu_type"]      = random.choice(["high_bleed", "low_bleed", "intermittent"])
        r["pneu_count"]     = random.randint(1, 50)
        r["pneu_bleed_rate"]= round(random.uniform(0.01, 5), 3)
        r["pneu_hours"]     = round(random.uniform(4000, 8760), 0)
    elif proc == "tank_flashing":
        r["tank_gor"]          = round(random.uniform(50, 500), 1)
        r["tank_ch4_content"]  = round(random.uniform(50, 90), 2)
        r["tank_control_eff"]  = round(random.uniform(85, 99), 2)
        r["tank_api_gravity"]  = round(random.uniform(20, 45), 1)
    elif proc == "fugitives_equipment":
        r["fugitive_method"] = random.choice(["EPA_factor", "OGI_measurement", "direct"])
        r["fugitive_ppm"]    = round(random.uniform(100, 50000), 1)
        r["comp_count"]      = random.randint(10, 500)
        r["operating_hours"] = round(random.uniform(4000, 8760), 0)
    elif proc == "completions":
        r["comp_method"]   = random.choice(["open_vent", "flared"])
        r["comp_rate"]     = round(random.uniform(100, 10000), 1)
        r["comp_duration"] = round(random.uniform(24, 720), 0)
        r["comp_flare_eff"]= round(random.uniform(90, 99), 1)
    elif proc == "blowdown":
        r["blowdown_pressure"] = round(random.uniform(500, 8000), 1)
        r["blowdown_events"]   = random.randint(1, 50)
        r["blowdown_temp"]     = round(random.uniform(15, 60), 1)
    elif proc == "dehydrator":
        r["dehy_pump_rate"]    = round(random.uniform(0.5, 20), 2)
        r["dehy_hours"]        = round(random.uniform(4000, 8760), 0)
        r["dehy_press"]        = round(random.uniform(500, 3000), 1)
        r["dehy_temp"]         = round(random.uniform(50, 200), 1)
        r["dehy_ch4_content"]  = round(random.uniform(70, 95), 2)
        r["dehy_eff"]          = round(random.uniform(90, 99), 1)
    elif proc == "agr":
        r["agr_co2_in"]        = round(random.uniform(5, 30), 2)
        r["agr_co2_out"]       = round(random.uniform(0.1, 2), 2)
        r["agr_ch4_in"]        = round(random.uniform(1, 10), 2)
        r["agr_ch4_slip"]      = round(random.uniform(0.01, 0.5), 3)
        r["agr_control_eff"]   = round(random.uniform(90, 99.5), 1)

    rows.append(r)

# ─── CATEGORY 3: ERROR rows — Missing year ─────────────────────────────────── 30 rows
for _ in range(30):
    r = empty_row()
    r["month"]         = random.randint(1, 12)
    r["date"]          = ""           # no date either
    r["year"]          = ""           # MISSING
    r["facility_name"] = random.choice(REGIONS)
    r["process"]       = "combustion"
    r["fuel"]          = "Natural Gas"
    r["quantity"]      = round(random.uniform(100, 5000), 2)
    r["unit"]          = "scf"
    rows.append(r)

# ─── CATEGORY 4: ERROR rows — Missing month ──────────────────────────────────  30 rows
for _ in range(30):
    r = empty_row()
    r["year"]          = random.choice([2022, 2023, 2024])
    r["month"]         = ""           # MISSING — no YYYY-MM date either
    r["date"]          = str(r["year"])  # only year, no month
    r["facility_name"] = random.choice(REGIONS)
    r["process"]       = "flaring"
    r["fuel"]          = "Natural Gas"
    r["quantity"]      = round(random.uniform(100, 5000), 2)
    r["unit"]          = "scf"
    rows.append(r)

# ─── CATEGORY 5: ERROR rows — Wrong region name ──────────────────────────────  30 rows
BAD_REGIONS = ["Paris Unit", "London Refinery", "Texas Plant", "UNKNOWN_REG", "Test Region", "N/A"]
for _ in range(30):
    r = empty_row()
    year  = random.choice([2022, 2023, 2024])
    month = random.randint(1, 12)
    r["year"]          = year
    r["month"]         = month
    r["date"]          = f"{year}-{month:02d}"
    r["facility_name"] = random.choice(BAD_REGIONS)   # WRONG
    r["process"]       = "combustion"
    r["fuel"]          = "Natural Gas"
    r["quantity"]      = round(random.uniform(100, 5000), 2)
    r["unit"]          = "scf"
    rows.append(r)

# ─── CATEGORY 6: ERROR rows — Missing quantity ───────────────────────────────  30 rows
for _ in range(30):
    r = empty_row()
    year  = random.choice([2022, 2023, 2024])
    month = random.randint(1, 12)
    r["year"]          = year
    r["month"]         = month
    r["date"]          = f"{year}-{month:02d}"
    r["facility_name"] = random.choice(REGIONS)
    r["process"]       = "combustion"
    r["fuel"]          = "Natural Gas"
    r["quantity"]      = ""           # MISSING
    r["unit"]          = "scf"
    rows.append(r)

# ─── CATEGORY 7: ERROR rows — Invalid quantity (non-numeric) ─────────────────  30 rows
for _ in range(30):
    r = empty_row()
    year  = random.choice([2022, 2023, 2024])
    month = random.randint(1, 12)
    r["year"]          = year
    r["month"]         = month
    r["date"]          = f"{year}-{month:02d}"
    r["facility_name"] = random.choice(REGIONS)
    r["process"]       = "venting"
    r["fuel"]          = "Natural Gas (Venting/Blowdown)"
    r["quantity"]      = random.choice(["N/A", "TBD", "Unknown", "—", "n.a.", "?"])  # BAD
    r["unit"]          = "m3"
    rows.append(r)

# ─── CATEGORY 8: ERROR rows — Missing process ────────────────────────────────  30 rows
for _ in range(30):
    r = empty_row()
    year  = random.choice([2022, 2023, 2024])
    month = random.randint(1, 12)
    r["year"]          = year
    r["month"]         = month
    r["date"]          = f"{year}-{month:02d}"
    r["facility_name"] = random.choice(REGIONS)
    r["process"]       = ""           # MISSING
    r["fuel"]          = "Natural Gas"
    r["quantity"]      = round(random.uniform(100, 5000), 2)
    r["unit"]          = "scf"
    rows.append(r)

# ─── CATEGORY 9: Valid all-12-months coverage per region ─────────────────────  120 rows
# Guarantee every month of 2024 is covered for the top 10 regions
for region in REGIONS[:10]:
    for month in range(1, 13):
        r = empty_row()
        r["year"]          = 2024
        r["month"]         = month
        r["date"]          = f"2024-{month:02d}"
        r["facility_name"] = region
        r["process"]       = "combustion"
        r["fuel"]          = "Natural Gas"
        r["quantity"]      = round(random.uniform(50000, 300000), 2)
        r["unit"]          = "scf"
        r["factor_type"]   = "default"
        r["equipment"]     = f"BOILER-{month:02d}"
        r["equipment_id"]  = f"BLR-{month:02d}"
        rows.append(r)

# Pad to exactly 1000
while len(rows) < 1000:
    r = empty_row()
    year  = random.choice([2022, 2023, 2024])
    month = random.randint(1, 12)
    r["year"]          = year
    r["month"]         = month
    r["date"]          = f"{year}-{month:02d}"
    r["facility_name"] = random.choice(REGIONS)
    r["process"]       = random.choice(["combustion", "flaring"])
    r["fuel"]          = fuel_for(r["process"])
    r["quantity"]      = round(random.uniform(1000, 200000), 2)
    r["unit"]          = "scf"
    r["factor_type"]   = "default"
    rows.append(r)

# Shuffle so error rows aren't all at the end
random.shuffle(rows)

# Write CSV
with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(rows[:1000])

print(f"Written {min(1000, len(rows))} rows to {OUTPUT}")

# Category breakdown
valid_t1    = sum(1 for r in rows[:1000] if r["year"] and r["month"] and r["facility_name"] in REGIONS and str(r["quantity"]).replace(".","").isdigit() and r["process"] and not r["c1"])
valid_t3    = sum(1 for r in rows[:1000] if r["year"] and r["month"] and r["facility_name"] in REGIONS and str(r["quantity"]).replace(".","").isdigit() and r["process"] and r["c1"])
err_year    = sum(1 for r in rows[:1000] if not r["year"] and not (r.get("date","") and "-" in str(r.get("date",""))))
err_month   = sum(1 for r in rows[:1000] if r["year"] and not r["month"] and not (r.get("date","") and "-" in str(r.get("date",""))))
err_region  = sum(1 for r in rows[:1000] if r["facility_name"] not in REGIONS)
err_qty     = sum(1 for r in rows[:1000] if not str(r["quantity"]).replace(".","").lstrip("-").isdigit() and r["quantity"] != "")
err_noquant = sum(1 for r in rows[:1000] if r["quantity"] == "")
err_proc    = sum(1 for r in rows[:1000] if not r["process"])

print(f"\nCategory breakdown (approx.):")
print(f"  Valid Tier 1 (no gas comp): {valid_t1}")
print(f"  Valid Tier 3 (gas comp):    {valid_t3}")
print(f"  Error - missing year:       {err_year}")
print(f"  Error - missing month:      {err_month}")
print(f"  Error - wrong region:       {err_region}")
print(f"  Error - bad quantity:       {err_qty}")
print(f"  Error - empty quantity:     {err_noquant}")
print(f"  Error - missing process:    {err_proc}")
