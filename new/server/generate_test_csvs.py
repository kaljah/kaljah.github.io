import csv

# Scope 2 Test CSV
# Fields expected by wizard: facility_name, year, month, source_type, grid_region, consumption, unit
s2_headers = ["facility_name", "year", "month", "source_type", "grid_region", "consumption", "unit"]
s2_rows = [
    # Normal Electricity
    ["ADR", 2024, 1, "electricity", "Algerian National Grid", 50000, "kWh"],
    ["REB", 2024, 2, "electricity", "Captive Power Plant", 2500, "MWh"],
    # Indirect Steam
    ["HBK", 2024, 3, "indirect_steam", "Algerian National Grid", 1500, "MMBtu"],
    # Cogen Allocation
    ["GTL", 2024, 4, "cogen_allocation", "Algerian National Grid", 800, "tCO2e"],
    # Bad Data - should fail gracefully
    ["ADR", 2024, 5, "electricity", "NON_EXISTENT_GRID", 1000, "kWh"],
    ["NON_EXISTENT_FACILITY", 2024, 6, "electricity", "Algerian National Grid", 1000, "kWh"],
]

with open("test_scope2.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(s2_headers)
    writer.writerows(s2_rows)


# Scope 3 Test CSV
# Fields expected by wizard: facility_name, year, month, category, sub_category, notes, amount, unit, emission_factor, ef_unit, co2e
s3_headers = ["facility_name", "year", "month", "category", "sub_category", "notes", "amount", "unit", "emission_factor", "ef_unit", "co2e"]
s3_rows = [
    # Cat 1 - Purchased Goods
    ["ADR", 2024, 1, "1", "Steel Pipes", "Imported from Italy", 15000, "kg", 1.5, "kgCO2e/kg", ""],
    # Cat 6 - Business Travel
    ["REB", 2024, 2, "6", "Air Travel", "Algiers to Paris", 1000, "miles", 0.15, "kgCO2e/mile", ""],
    # Cat 11 - Use of Sold Products (Direct CO2e provided)
    ["HBK", 2024, 3, "11", "Crude Oil", "Burned by customer", 100000, "bbl", "", "", 45000],
    # Bad Data
    ["INVALID_FACILITY", 2024, 4, "1", "Stuff", "", 100, "kg", 1, "kg", ""],
]

with open("test_scope3.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(s3_headers)
    writer.writerows(s3_rows)

print("Generated test_scope2.csv and test_scope3.csv")
