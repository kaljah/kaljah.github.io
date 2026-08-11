import csv
import random
from datetime import datetime, timedelta


def generate_1m_csv(filepath, num_rows=1000000):
    headers = [
        "Date (YYYY-MM)",
        "Activity",
        "Division",
        "Field",
        "Region / Facility",
        "Emission Source (Group)",
        "Equipment Name",
        "Equipment ID",
        "Process Type",
        "Activity / Fuel",
        "Factor Type",
        "Quantity",
        "Unit",
        "CH4 Content (%)",
        "CO2 Content (%)",
        "HHV (Btu/scf)",
        "C1 Mol%",
        "C2 Mol%",
        "C3 Mol%",
        "C4 Mol%",
        "C5 Mol%",
        "C6 Mol%",
        "C7 Mol%",
        "C8 Mol%",
        "C9 Mol%",
        "C10 Mol%",
        "N2 Mol%",
        "CO2 Mol% (Gas Comp)",
        "Flare Type",
        "Flare Control Efficiency (%)",
        "Mud Type",
        "GOR (scf/bbl)",
        "Flowback Days",
        "Completions Flare Efficiency (%)",
        "Well Depth (ft)",
        "Casing Diameter (in)",
        "Well Pressure (psia)",
        "Unloading Events",
        "Unloading Flare Efficiency (%)",
        "Tank GOR (scf/bbl)",
        "Tank API Gravity",
        "Tank Control Efficiency (%)",
        "Blowdown Volume (scf)",
        "Blowdown Pressure (psia)",
        "Blowdown Events",
        "Pneumatic Device Count",
        "Pneumatic Bleed Rate (scf/hr/device)",
        "Pneumatic Hours",
        "Fugitive Method",
        "Leak Concentration (ppm)",
        "Pipeline Length (km)",
        "AGR Unit Type",
        "AGR Flow Rate",
        "AGR Flow Unit",
    ]

    activities = ["Upstream", "Midstream", "Downstream", "Production", "Processing"]
    regions = ["ADR", "REB", "HBK", "GTL", "OHT", "STAH", "TFT", "HMD", "RNS", "HRM"]
    divisions = ["Div A", "Div B", "Div C", "Exploration", "Refining", "Distribution"]
    fields = [
        "Field Alpha",
        "Field Beta",
        "Field Gamma",
        "Eagle Ford",
        "Ghawar",
        "Troll",
    ]

    processes = [
        {
            "process": "Combustion",
            "fuels": ["Natural Gas", "Diesel", "Propane"],
            "units": ["scf", "m3", "gal"],
        },
        {
            "process": "Flaring",
            "fuels": ["Associated Gas", "Natural Gas"],
            "units": ["scf", "m3"],
        },
        {"process": "Venting", "fuels": ["Natural Gas"], "units": ["scf", "m3"]},
        {
            "process": "Storage Tank - Flashing",
            "fuels": ["Crude Oil"],
            "units": ["bbl", "gal"],
        },
        {
            "process": "Fugitive Emissions",
            "fuels": ["Natural Gas"],
            "units": ["kg", "scf"],
        },
        {"process": "Pneumatic Device", "fuels": ["Natural Gas"], "units": ["scf"]},
        {"process": "Dehydrator", "fuels": ["Natural Gas"], "units": ["scf", "MMscf"]},
        {
            "process": "Well Completions & Workovers",
            "fuels": ["Natural Gas"],
            "units": ["scf", "bbl"],
        },
        {
            "process": "Liquids Unloading",
            "fuels": ["Natural Gas"],
            "units": ["scf", "bbl"],
        },
        {
            "process": "Acid Gas Removal (AGR)",
            "fuels": ["Natural Gas"],
            "units": ["scf", "MMscf"],
        },
    ]

    start_date = datetime(2022, 1, 1)

    print(f"Generating {num_rows} unique rows for CSV. This will be very fast...")

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for i in range(1, num_rows + 1):
            if i % 100000 == 0:
                print(f"  ... {i} rows generated")

            dt = start_date + timedelta(days=random.randint(0, 1000))
            date_str = dt.strftime("%Y-%m")

            proc = random.choice(processes)
            process_name = proc["process"]
            fuel = random.choice(proc["fuels"])
            unit = random.choice(proc["units"])

            # Truly unique randoms for every row to ensure no two rows are identically calculated
            quantity = round(random.uniform(10.0, 500000.0) + (i * 0.001), 3)
            eq_id = f"EQ-CSV-{i:07d}"

            # C1-C10 and other params
            c1 = round(random.uniform(50, 95), 2)
            c2 = round(random.uniform(1, 15), 2)
            c3 = round(random.uniform(0.1, 5), 2)
            c4 = round(random.uniform(0.1, 3), 2)
            c5 = round(random.uniform(0.1, 2), 2)
            c6 = round(random.uniform(0.1, 1), 2)
            c7 = round(random.uniform(0.1, 0.5), 2)
            c8 = round(random.uniform(0.01, 0.2), 2)
            c9 = round(random.uniform(0.01, 0.1), 2)
            c10 = round(random.uniform(0.01, 0.05), 2)
            n2 = round(random.uniform(0.1, 5), 2)

            ctrl_eff = round(random.uniform(90, 99.9), 1)
            flare_type = random.choice(
                ["elevated", "enclosed_ground", "air_assisted", "steam_assisted"]
            )
            tank_gor = round(random.uniform(10, 500), 2)
            pneumatic_count = random.randint(1, 100)
            pneumatic_bleed = round(random.uniform(1, 50), 2)
            hours = random.randint(100, 720)
            well_depth = round(random.uniform(1000, 15000), 1)
            diameter = round(random.uniform(2, 12), 1)
            pressure = round(random.uniform(50, 5000), 1)
            events = random.randint(1, 20)
            blowdown_vol = round(random.uniform(1, 1000), 2)
            fugitive = random.choice(["screening", "pipeline", "average"])
            ppm = round(random.uniform(100, 10000), 1)
            agr_rate = round(random.uniform(1, 100), 2)
            round(random.uniform(5, 20), 2)
            round(random.uniform(0.1, 2), 2)
            ch4_content = round(random.uniform(70, 95), 2)
            co2_content = round(random.uniform(1, 5), 2)

            row = [
                date_str,
                random.choice(activities),
                random.choice(divisions),
                random.choice(fields),
                random.choice(regions),
                f"Source Group {random.randint(1,500)}",
                f"EQP-{process_name[:3]}-{random.randint(10,999)}",
                eq_id,
                process_name,
                fuel,
                "default",
                quantity,
                unit,
                ch4_content,
                co2_content,
                1000,  # HHV
                c1,
                c2,
                c3,
                c4,
                c5,
                c6,
                c7,
                c8,
                c9,
                c10,
                n2,
                co2_content,
                flare_type,
                ctrl_eff,  # Flare
                "Water-based",
                0,
                0,
                0,  # Mud, GOR, flowback, compl flare
                well_depth,
                diameter,
                pressure,
                events,
                0,  # Unloading
                tank_gor,
                40,
                ctrl_eff,  # Tank
                blowdown_vol,
                pressure,
                events,  # Blowdown
                pneumatic_count,
                pneumatic_bleed,
                hours,  # Pneumatics
                fugitive,
                ppm,
                100,  # Fugitive
                "Amine",
                agr_rate,
                "MMscf",  # AGR
            ]

            writer.writerow(row)

    print(f"Saving file to {filepath}.")
    print("Done!")


if __name__ == "__main__":
    generate_1m_csv("C:\\Users\\samsung\\Desktop\\h\\1m_exhaustive_test.csv", 1000000)
