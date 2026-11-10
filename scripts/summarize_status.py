import json

with open('scripts/full_reconciled_sources.json') as f:
    sources = json.load(f)

print(f"Total sources: {len(sources)}")

# Table of counts by status per entity and module
status_types = [
    "REPORT_ANOMALY",
    "REPORT_OMISSION_RECOVERED",
    "UNTESTED_NO_ACTIVITY",
    "ZERO_ACTIVITY_MATCH",
    "MINOR_ROUNDING",
    "EXACT_MATCH"
]

# Overall counts
print("=== Overall Counts by Status ===")
overall = {}
for s in sources:
    st = s["status"]
    overall[st] = overall.get(st, 0) + 1
for st in status_types:
    print(f"  {st:26s}: {overall.get(st, 0)}")

# Counts by Entity
print("\n=== Counts by Entity ===")
by_ent = {}
for s in sources:
    ent = s["entity"]
    st = s["status"]
    if ent not in by_ent:
        by_ent[ent] = {}
    by_ent[ent][st] = by_ent[ent].get(st, 0) + 1

for ent, sc in by_ent.items():
    print(f"[{ent}] Total: {sum(sc.values())}")
    for st in status_types:
        print(f"    {st:26s}: {sc.get(st, 0)}")

# Counts by Module per Entity
print("\n=== Counts by Module per Entity ===")
by_ent_mod = {}
for s in sources:
    ent = s["entity"]
    mod = s["module"]
    st = s["status"]
    key = (ent, mod)
    if key not in by_ent_mod:
        by_ent_mod[key] = {}
    by_ent_mod[key][st] = by_ent_mod[key].get(st, 0) + 1

for (ent, mod), sc in sorted(by_ent_mod.items()):
    print(f"[{ent} - {mod}] (Total: {sum(sc.values())})")
    for st, count in sorted(sc.items()):
        print(f"    {st}: {count}")
