import csv
import random
from datetime import datetime, timedelta

def generate_scope2_csv(filepath, num_rows=10000):
    headers = [
        "date",
        "facility_name",
        "grid_region",
        "consumption",
        "unit",
        "activity",
        "division",
        "field"
    ]

    facilities = ["ADR", "REB", "HBK", "GTL", "OHT", "STAH", "TFT", "HMD", "RNS", "HRM"]
    grid_regions = ["North", "South", "East", "West", "Central"]
    units = ["kWh", "MWh", "GWh"]
    activities = ["Upstream", "Midstream", "Downstream"]
    divisions = ["Div A", "Div B", "Div C"]
    fields = ["Field Alpha", "Field Beta", "Eagle Ford"]

    start_date = datetime(2023, 1, 1)

    print(f"Generating {num_rows} unique rows for Scope 2 CSV...")

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for i in range(num_rows):
            dt = start_date + timedelta(days=random.randint(0, 700))
            date_str = dt.strftime("%Y-%m-%d")

            # Unique consumption value to ensure rows don't look identical
            consumption = round(random.uniform(100.0, 50000.0) + (i * 0.01), 2)

            row = [
                date_str,
                random.choice(facilities),
                random.choice(grid_regions),
                consumption,
                random.choice(units),
                random.choice(activities),
                random.choice(divisions),
                random.choice(fields)
            ]
            writer.writerow(row)

    print(f"Generated {num_rows} Scope 2 rows at {filepath}")

if __name__ == "__main__":
    generate_scope2_csv("C:\\Users\\samsung\\Desktop\\H2\\new\\server\\10k_scope2_test.csv", 10000)
