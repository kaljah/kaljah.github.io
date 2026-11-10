import json

with open("scripts/full_reconciled_sources.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Keys in source 1:", list(data[0].keys()))
for k, v in data[0].items():
    print(f"  {k}: {v}")

print("\nSample source with activity (Source 4):")
for k, v in data[3].items():
    print(f"  {k}: {v}")
