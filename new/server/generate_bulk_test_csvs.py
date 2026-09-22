"""
generate_bulk_test_csvs.py

Generates:
1. bulk_tier1_all_fuels.csv: Comprehensive Tier 1 catalog file across all fuel types and units.
2. bulk_tier3_360_per_region.csv: Exactly 360 distinct engineering scenarios for each of the
   3 database regions (West, Center, South) = 1,080 rows total, covering:
   - Combustion (Tier 3)
   - Flaring (Tier 3)
   - Storage Tanks Flashing (Tier 3)
   - Storage Tanks Working / Breathing (Tier 3)
   - Acid Gas Removal / AGR (Tier 3)
   - Glycol Dehydrators (Tier 3)
   - Pneumatics (Tier 3)
   - Liquids Unloading (Tier 3)
   - Completions Flowback (Tier 3)
   - Blowdowns & Venting (Tier 3)
"""

import csv
import os
import random

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))

# 3 Database Regions and their representative facility names
REGIONS_FACILITIES = [
    {"region": "West", "facility": "Complexe Sidérurgique DRI/EAF (Tosyali)", "activity": "Steel & Iron (Acier DRI)", "division": "Metallurgy"},
    {"region": "Center", "facility": "Cimenterie Industrielle de Chlef (GICA)", "activity": "Cement & Clinker", "division": "Building Materials"},
    {"region": "South", "facility": "Centre de Traitement Gazier Hassi Messaoud (Sonatrach)", "activity": "Upstream & Midstream Gas", "division": "Exploration & Production"}
]

# -------------------------------------------------------------
# 1. Tier 1 Test CSV: All Fuel Types and Standard Units
# -------------------------------------------------------------
TIER1_FUELS = [
    ("Natural Gas", ["scf", "m3", "Mcf", "MMscf"]),
    ("Diesel (No. 2 Fuel Oil)", ["gal", "L", "bbl", "m3"]),
    ("Motor Gasoline", ["gal", "L", "m3"]),
    ("Propane (Liquid/LPG)", ["gal", "L", "bbl"]),
    ("Kerosene", ["gal", "L", "bbl"]),
    ("Residual Fuel Oil (No. 6 Fuel Oil)", ["gal", "bbl", "m3"]),
    ("Crude Oil", ["bbl", "m3", "gal"]),
    ("Associated Gas (Flaring)", ["scf", "m3", "Mcf"]),
    ("Landfill Gas", ["scf", "m3"]),
    ("Coke Oven Gas", ["scf", "m3"]),
    ("Refinery Gas", ["scf", "m3"]),
    ("Coal (Bituminous)", ["ton", "tonne", "kg"]),
    ("Coal (Sub-bituminous)", ["ton", "tonne"]),
    ("Coal (Lignite)", ["ton", "tonne"]),
    ("Coal (Anthracite)", ["ton", "tonne"]),
]

def generate_tier1_csv():
    filepath = os.path.join(SERVER_DIR, "bulk_tier1_all_fuels.csv")
    headers = [
        "date", "facility_name", "activity", "division", "process", "fuel", "factor_type", "quantity", "unit"
    ]
    rows = []
    month_idx = 1

    for rf in REGIONS_FACILITIES:
        for fuel_name, units in TIER1_FUELS:
            for u in units:
                qty = random.randint(500, 50000)
                year = 2024 + (month_idx % 2)
                mo = (month_idx % 12) + 1
                month_idx += 1
                
                # Alternate between facility name and region name to test both lookups
                loc = rf["facility"]
                proc = "Flaring" if "Flaring" in fuel_name else "Combustion"

                rows.append([
                    f"{year}-{mo:02d}",
                    loc,
                    rf["activity"],
                    rf["division"],
                    proc,
                    fuel_name,
                    "Default",
                    qty,
                    u
                ])

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Generated {len(rows)} Tier 1 rows in: {filepath}")
    return filepath


# -------------------------------------------------------------
# 2. Tier 3 Test CSV: 360 Distinct Scenarios per Region (1,080 rows)
# -------------------------------------------------------------
def generate_tier3_csv():
    filepath = os.path.join(SERVER_DIR, "bulk_tier3_360_per_region.csv")
    headers = [
        "date", "facility_name", "activity", "division", "process", "fuel", "factor_type", "quantity", "unit",
        "combustion_efficiency", "flare_type", "ch4_content", "co2_content", "hhv",
        "tank_gor", "tank_control_eff", "tank_api_gravity",
        "agr_throughput", "agr_co2_in", "agr_co2_out",
        "dehy_throughput", "dehy_pump_rate", "dehy_hours", "dehy_ch4_content",
        "pneu_count", "pneu_bleed_rate", "pneu_hours",
        "unload_freq", "unload_diam", "unload_depth", "unload_press",
        "comp_duration", "comp_rate", "comp_flare_eff",
        "blowdown_volume", "blowdown_pressure", "blowdown_events",
        "user_unc_co2", "user_unc_ch4", "user_unc_n2o"
    ]
    rows = []

    for rf in REGIONS_FACILITIES:
        region_rows = []
        loc = rf["facility"]

        # 1. Combustion (40 scenarios)
        for i in range(40):
            year = 2025
            mo = (i % 12) + 1
            qty = 10000 + i * 5000
            eff = round(95.0 + (i % 50) * 0.1, 1) # 95.0 - 99.9%
            hhv = 950 + (i % 25) * 10 # 950 - 1200 BTU/scf
            row = {h: "" for h in headers}
            row.update({
                "date": f"{year}-{mo:02d}", "facility_name": loc, "activity": rf["activity"], "division": rf["division"],
                "process": "Combustion", "fuel": "Natural Gas", "factor_type": "Specific", "quantity": qty, "unit": "scf",
                "combustion_efficiency": eff, "hhv": hhv, "user_unc_co2": "2.5", "user_unc_ch4": "3.0", "user_unc_n2o": "5.0"
            })
            region_rows.append([row[h] for h in headers])

        # 2. Flaring (40 scenarios)
        flare_types = ["elevated", "open", "ground", "enclosed"]
        for i in range(40):
            year = 2025
            mo = (i % 12) + 1
            qty = 5000 + i * 2500
            ftype = flare_types[i % len(flare_types)]
            ch4_pct = round(70.0 + (i % 28) * 1.0, 1) # 70% - 98%
            row = {h: "" for h in headers}
            row.update({
                "date": f"{year}-{mo:02d}", "facility_name": loc, "activity": rf["activity"], "division": rf["division"],
                "process": "Flaring", "fuel": "Associated Gas (Flaring)", "factor_type": "Specific", "quantity": qty, "unit": "m3",
                "flare_type": ftype, "ch4_content": ch4_pct, "hhv": 1020,
                "user_unc_co2": "3.0", "user_unc_ch4": "4.0", "user_unc_n2o": "6.0"
            })
            region_rows.append([row[h] for h in headers])

        # 3. Tanks Flashing (40 scenarios)
        for i in range(40):
            year = 2024
            mo = (i % 12) + 1
            throughput = 1000 + i * 1200
            gor = 50 + i * 10
            ch4_pct = round(65.0 + (i % 25) * 1.0, 1)
            row = {h: "" for h in headers}
            row.update({
                "date": f"{year}-{mo:02d}", "facility_name": loc, "activity": rf["activity"], "division": rf["division"],
                "process": "Storage Tanks", "fuel": "Crude Oil", "factor_type": "Specific", "quantity": throughput, "unit": "bbl",
                "tank_gor": gor, "tank_control_eff": 95, "tank_api_gravity": 35 + (i % 10), "ch4_content": ch4_pct,
                "user_unc_ch4": "5.0"
            })
            region_rows.append([row[h] for h in headers])

        # 4. Tanks Working / Breathing (35 scenarios)
        for i in range(35):
            year = 2024
            mo = (i % 12) + 1
            throughput = 500 + i * 800
            row = {h: "" for h in headers}
            row.update({
                "date": f"{year}-{mo:02d}", "facility_name": loc, "activity": rf["activity"], "division": rf["division"],
                "process": "Storage Tanks", "fuel": "Condensate", "factor_type": "Specific", "quantity": throughput, "unit": "bbl",
                "tank_control_eff": 90, "ch4_content": 80.0, "user_unc_ch4": "6.0"
            })
            region_rows.append([row[h] for h in headers])

        # 5. Acid Gas Removal / AGR (35 scenarios)
        for i in range(35):
            year = 2025
            mo = (i % 12) + 1
            throughput = round(5.0 + i * 1.5, 1) # MMscf/day
            co2_in = round(3.0 + (i % 12) * 1.0, 1) # 3% - 15%
            co2_out = 0.05
            row = {h: "" for h in headers}
            row.update({
                "date": f"{year}-{mo:02d}", "facility_name": loc, "activity": rf["activity"], "division": rf["division"],
                "process": "Acid Gas Removal (AGR)", "fuel": "Natural Gas", "factor_type": "Specific", "quantity": throughput, "unit": "MMscf/day",
                "agr_throughput": throughput, "agr_co2_in": co2_in, "agr_co2_out": co2_out,
                "user_unc_co2": "2.0", "user_unc_ch4": "4.0"
            })
            region_rows.append([row[h] for h in headers])

        # 6. Glycol Dehydrators (35 scenarios)
        for i in range(35):
            year = 2025
            mo = (i % 12) + 1
            throughput = 15 + i * 2 # MMscfd
            pump_rate = round(2.0 + (i % 15) * 0.4, 1)
            row = {h: "" for h in headers}
            row.update({
                "date": f"{year}-{mo:02d}", "facility_name": loc, "activity": rf["activity"], "division": rf["division"],
                "process": "Dehydrator", "fuel": "Natural Gas", "factor_type": "Specific", "quantity": throughput, "unit": "MMscf/day",
                "dehy_throughput": throughput, "dehy_pump_rate": pump_rate, "dehy_hours": 8760, "dehy_ch4_content": 85.0,
                "user_unc_ch4": "4.5"
            })
            region_rows.append([row[h] for h in headers])

        # 7. Pneumatics (35 scenarios)
        for i in range(35):
            year = 2025
            mo = (i % 12) + 1
            count = 5 + i * 2
            bleed = round(2.5 + (i % 20) * 1.2, 1) # scf/hr
            row = {h: "" for h in headers}
            row.update({
                "date": f"{year}-{mo:02d}", "facility_name": loc, "activity": rf["activity"], "division": rf["division"],
                "process": "Pneumatic Device", "fuel": "Natural Gas", "factor_type": "Specific", "quantity": count, "unit": "devices",
                "pneu_count": count, "pneu_bleed_rate": bleed, "pneu_hours": 8760, "ch4_content": 86.0,
                "user_unc_ch4": "5.0"
            })
            region_rows.append([row[h] for h in headers])

        # 8. Liquids Unloading (35 scenarios)
        for i in range(35):
            year = 2024
            mo = (i % 12) + 1
            events = 2 + (i % 24)
            depth = 3000 + i * 200
            diam = round(1.5 + (i % 8) * 0.35, 3)
            press = 100 + i * 20
            row = {h: "" for h in headers}
            row.update({
                "date": f"{year}-{mo:02d}", "facility_name": loc, "activity": rf["activity"], "division": rf["division"],
                "process": "Liquids Unloading", "fuel": "Natural Gas", "factor_type": "Specific", "quantity": events, "unit": "events",
                "unload_freq": events, "unload_diam": diam, "unload_depth": depth, "unload_press": press,
                "user_unc_ch4": "5.5"
            })
            region_rows.append([row[h] for h in headers])

        # 9. Well Completions Flowback (35 scenarios)
        for i in range(35):
            year = 2024
            mo = (i % 12) + 1
            dur = 24 + i * 4
            rate = 50 + i * 15
            row = {h: "" for h in headers}
            row.update({
                "date": f"{year}-{mo:02d}", "facility_name": loc, "activity": rf["activity"], "division": rf["division"],
                "process": "Well Completions & Workovers", "fuel": "Natural Gas", "factor_type": "Specific", "quantity": dur, "unit": "hours",
                "comp_duration": dur, "comp_rate": rate, "comp_flare_eff": 98.0,
                "user_unc_ch4": "5.0"
            })
            region_rows.append([row[h] for h in headers])

        # 10. Blowdowns & Venting (30 scenarios)
        for i in range(30):
            year = 2025
            mo = (i % 12) + 1
            vol = 50 + i * 30 # m3
            press = 200 + i * 40
            events = 1 + (i % 12)
            row = {h: "" for h in headers}
            row.update({
                "date": f"{year}-{mo:02d}", "facility_name": loc, "activity": rf["activity"], "division": rf["division"],
                "process": "Venting (Blowdown)", "fuel": "Natural Gas", "factor_type": "Specific", "quantity": vol, "unit": "m3",
                "blowdown_volume": vol, "blowdown_pressure": press, "blowdown_events": events,
                "user_unc_ch4": "4.0"
            })
            region_rows.append([row[h] for h in headers])

        assert len(region_rows) == 360, f"Expected 360 rows for region {rf['region']}, got {len(region_rows)}"
        print(f"Region {rf['region']} ({rf['facility']}): Exactly {len(region_rows)} distinct Tier 3 scenarios generated.")
        rows.extend(region_rows)

    assert len(rows) == 1080, f"Expected 1080 total rows, got {len(rows)}"

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"Generated {len(rows)} Total Tier 3 rows (360 per region) in: {filepath}")
    return filepath


if __name__ == "__main__":
    generate_tier1_csv()
    generate_tier3_csv()
