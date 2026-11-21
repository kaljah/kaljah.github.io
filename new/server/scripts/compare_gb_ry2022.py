"""Run the GB HBNS / El Merk RY 2022 inventory (tests/gb_ry2022_cases.py) through the calculation engine and print
the platform's figures beside the printed ones.

    cd new/server && python scripts/compare_gb_ry2022.py [--csv out.csv]

No database or app is needed: compute_emissions is called with the AR4 GWP set directly.
"""
import argparse
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
sys.path.insert(0, SERVER)
sys.path.insert(0, os.path.join(SERVER, "tests"))

from calculations.constants import GWP_AR4  # noqa: E402
from gb_ry2022_cases import SOURCES, EMK_ONROAD_PRINTED, MODULE_TOTALS, SITE_TOTALS, run_source  # noqa: E402

GASES = ("co2", "ch4", "n2o", "co2e")


def delta(got, want):
    if want in (None, 0) or got is None:
        return None
    return (got - want) / want * 100.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    args = ap.parse_args()
    rows, totals = [], {}
    for src in SOURCES:
        res, err = None, ""
        if src["kind"] == "reproduce":
            try:
                res = run_source(src, GWP_AR4)
            except Exception as e:  # report, never stop
                err = f"{type(e).__name__}: {e}"
        row = {"site": src["site"], "module": src["module"], "source": src["name"], "kind": src["kind"],
               "error": err, "note": src["note"]}
        for g in GASES:
            want = src["printed"].get(g)
            got = res.get(g) if res else None
            row[f"{g}_printed"], row[f"{g}_platform"], row[f"{g}_delta_pct"] = want, got, delta(got, want)
        if res:
            t = totals.setdefault((src["site"], src["module"]), 0.0)
            totals[(src["site"], src["module"])] = t + res["co2e"]
        rows.append(row)

    fmt = lambda v, n=2: "" if v is None else f"{v:,.{n}f}"  # noqa: E731
    print(f"{'site':8} {'source':28} {'kind':9} {'CO2 printed':>13} {'CO2 platf.':>13} {'dCO2%':>7} "
          f"{'CH4 pr.':>9} {'CH4 pl.':>9} {'dCH4%':>7} {'N2O pr.':>7} {'N2O pl.':>7} {'dN2O%':>7} {'dCO2e%':>7}")
    for r in rows:
        print(f"{r['site']:8} {r['source'][:28]:28} {r['kind']:9} {fmt(r['co2_printed']):>13} "
              f"{fmt(r['co2_platform']):>13} {fmt(r['co2_delta_pct']):>7} {fmt(r['ch4_printed'], 3):>9} "
              f"{fmt(r['ch4_platform'], 3):>9} {fmt(r['ch4_delta_pct']):>7} {fmt(r['n2o_printed'], 3):>7} "
              f"{fmt(r['n2o_platform'], 3):>7} {fmt(r['n2o_delta_pct']):>7} {fmt(r['co2e_delta_pct']):>7}"
              + (f"  ERROR {r['error']}" if r["error"] else ""))
    onroad = [r for r in rows if r["site"] == "El Merk" and r["source"].startswith("On-Road")]
    s = {g: sum(r[f"{g}_platform"] or 0 for r in onroad) for g in GASES}
    print("\nEl Merk on-road total: " + ", ".join(
        f"{g} {s[g]:,.3f} vs {EMK_ONROAD_PRINTED[g]:,.2f} ({delta(s[g], EMK_ONROAD_PRINTED[g]):+.2f} %)" for g in GASES))
    print("\nModule CO2e (platform, reproduced sources only) vs printed module total:")
    for site, mods in MODULE_TOTALS.items():
        for mod, want in mods.items():
            got = totals.get((site, mod))
            print(f"  {site:8} {mod:26} {fmt(got):>14} {want:>14,.2f} {fmt(delta(got, want)):>7}")
        print(f"  {site:8} {'site total printed':26} {'':>14} {SITE_TOTALS[site]['co2e']:>14,.2f}")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
