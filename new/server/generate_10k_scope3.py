import csv
import random
from datetime import datetime, timedelta

def generate_scope3_csv(filepath, num_rows=10000):
    headers = [
        "date",
        "facility_name",
        "category",
        "sub_category",
        "amount",
        "emission_factor",
        "unit"
    ]

    facilities = ["ADR", "REB", "HBK", "GTL", "OHT", "STAH", "TFT", "HMD", "RNS", "HRM"]
    categories = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"]
    units = ["kg", "tonne", "lbs", "gal"]

    start_date = datetime(2023, 1, 1)

    print(f"Generating {num_rows} unique rows for Scope 3 CSV...")

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for i in range(num_rows):
            dt = start_date + timedelta(days=random.randint(0, 700))
            date_str = dt.strftime("%Y-%m-%d")

            # Unique amounts and EFs to ensure unique variations
            amount = round(random.uniform(10.0, 10000.0) + (i * 0.01), 2)
            ef = round(random.uniform(0.1, 5.0) + (i * 0.0001), 4)

            row = [
                date_str,
                random.choice(facilities),
                random.choice(categories),
                f"Subcategory {random.randint(1, 5)}",
                amount,
                ef,
                random.choice(units)
            ]
            writer.writerow(row)

    print(f"Generated {num_rows} Scope 3 rows at {filepath}")

if __name__ == "__main__":
    generate_scope3_csv("C:\\Users\\samsung\\Desktop\\H2\\new\\server\\10k_scope3_test.csv", 10000)
