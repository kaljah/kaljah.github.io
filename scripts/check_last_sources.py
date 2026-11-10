import json

with open("scripts/full_reconciled_sources.json", "r", encoding="utf-8") as f:
    sources = json.load(f)

for i in range(55, len(sources)):
    s = sources[i]
    print(f"Source {i+1}: {s.get('entity')} - {s.get('source_name')} | rep_co2e: {s.get('rep_co2e')} | activity: {s.get('activity_data')} {s.get('activity_unit')}")
