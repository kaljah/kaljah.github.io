"""Compare records saved through the real form (form_parity.mjs output) with the CSV import of the same
activity (exhibits_e2e harness). python form_parity.py <cases.json> <form_out.json> <db>"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exhibits_e2e as E  # noqa: E402

cases = json.load(open(sys.argv[1]))
form = {r["id"]: r for r in json.load(open(sys.argv[2]))}
csv_res = E.run(sys.argv[3], [(c["id"], c["id"], c["csv"], {}, 0) for c in cases])
rows = []
for c, cr in zip(cases, csv_res):
    f = form.get(c["id"], {})
    fe = (f.get("body") or {}).get("emissions") if isinstance(f.get("body"), dict) else None
    ce = cr.get("got")
    if not fe or not ce:
        status = "FORM-ERR" if not fe else "CSV-REFUSED"
        detail = f.get("error") or (f.get("body") if not fe else cr.get("reason"))
    else:
        diffs = {g: (fe.get(g) or 0, ce[g] or 0) for g in ("co2", "ch4", "n2o")}
        bad = {g: v for g, v in diffs.items() if abs(v[0] - v[1]) > 1e-6 * max(abs(v[0]), abs(v[1]), 1e-9)}
        status, detail = ("SAME" if not bad else "DIFF"), (bad or {g: round(v[0], 6) for g, v in diffs.items()})
    rows.append({"id": c["id"], "status": status, "detail": detail, "payload": f.get("payload")})
    print(f"{c['id']:28} {status:11} {str(detail)[:200]}")
json.dump(rows, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "form_parity.json"), "w"),
          indent=1, default=str, ensure_ascii=False)
