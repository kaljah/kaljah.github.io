"""Import the 100k audit CSV into PostgreSQL (DB_TYPE=postgres) through the real import thread, in two
halves (the importer refuses files over 50,000 rows), and save the skipped rows for check.py.

python pg_100k.py <postgres_url> <csv> <out_dir>
"""
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import boot, run_csv  # noqa: E402

url, src, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
with open(src, newline="", encoding="utf-8") as f:
    rd = csv.reader(f)
    header = next(rd)
    rows = list(rd)
half = (len(rows) + 1) // 2
parts = []
for k, chunk in enumerate((rows[:half], rows[half:])):
    p = os.path.join(out, f"part{k + 1}.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(chunk)
    parts.append((p, chunk))
app = boot(url)
ref_col = header.index("source_ref")
skipped, summary = [], []
for p, chunk in parts:
    t0 = time.time()
    job = run_csv(app, p)
    for s in job.get("skipped", []):
        s = dict(s)
        s["source_ref"] = chunk[s["row"] - 2][ref_col] if 2 <= s.get("row", 0) < len(chunk) + 2 else None
        skipped.append(s)
    summary.append({"file": os.path.basename(p), "status": job.get("status"), "processed": job.get("processed"),
                    "skipped": len(job.get("skipped", [])), "errors": job.get("errors", [])[:5],
                    "elapsed_s": round(time.time() - t0, 1)})
    print(summary[-1], flush=True)
json.dump(skipped, open(os.path.join(out, "skipped.json"), "w"))
json.dump(summary, open(os.path.join(out, "import_summary.json"), "w"), indent=1)
