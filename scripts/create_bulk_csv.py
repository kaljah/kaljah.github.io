import json

with open("scripts/full_reconciled_sources.json", "r", encoding="utf-8") as f:
    sources = json.load(f)

csv_rows = ["date,year,month,facility_name,process,fuel,quantity,unit,equipment"]
for i, s in enumerate(sources):
    ent = s["entity"]
    fac = "HBNS (Hassi Berkine South)" if ent == "HBNS" else "El Merk"
    name = s["source_name"].replace('"', '""')
    fname = f"{ent} - {s['source_name']} EF".replace('"', '""')
    act = float(s["activity_data"] or 0.0)
    csv_rows.append(f'2022-12-31,2022,12,"{fac}",combustion,"{fname}",{act},m3,"{name}"')

csv_text = "\n".join(csv_rows)
with open("berkine_2022_all_68_sources.csv", "w", encoding="utf-8") as f:
    f.write(csv_text)

print(f"Updated berkine_2022_all_68_sources.csv with {len(sources)} rows.")
