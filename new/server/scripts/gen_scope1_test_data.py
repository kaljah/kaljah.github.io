"""Writes Scope 1 test data for manual and e2e entry testing, per role.

    python scripts/gen_scope1_test_data.py --facility "Plant A" --facility "Plant B" [--rows 10000] [--out DIR]

For each role (admin, superuser, user) it writes:
  scope1_<role>_bulk.csv       --rows unique valid rows for the file upload (one header line)
  scope1_<role>_manual.json    the all-pairs matrix rows of that role, as single-POST bodies
                               (facility_id holds the facility NAME: replace with the id, or send
                               to /api/emissions/import, which takes names)
  scope1_invalid.csv           one row per file validation rule, each expected to be skipped
  coverage.txt                 pair coverage of the matrix

The cases, tiers and expected values are those of tests/scope1_matrix_data.py. Superuser and user
accounts must be assigned the region of the facilities given. Rows are dated 2025; Tier 2 rows need
the approved custom factor "Matrix Site Fuel" (70 / 0.01 / 0.001 kg/MMBtu).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests import scope1_matrix_data as M  # noqa: E402

INVALID = [  # (Date, Process, Fuel, Quantity, Unit, expected reason)
    ("2025-13", "combustion", "Natural Gas", "1", "scf", "Invalid date"),
    ("2025-06", "combustion", "Natural Gas", "-5", "scf", "Invalid quantity"),
    ("2025-06", "combustion", "Natural Gas", "abc", "scf", "Invalid quantity"),
    ("2025-06", "combustion", "Diesel (No. 2 Fuel Oil)", "5", "ton", "'ton' is ambiguous"),
    ("2025-06", "combustion", "Unobtainium", "5", "scf", "not in the emission factor catalog"),
    ("2025-06", "electricity", "Natural Gas", "5", "scf", "Scope 2 source"),
    ("2025-06", "combustion", "Natural Gas", "", "scf", "Missing quantity"),
    ("EXAMPLE 2024-01", "combustion", "Natural Gas", "1", "scf", "Example row: not imported"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--facility", action="append", required=True, help="facility name (repeat for several)")
    ap.add_argument("--rows", type=int, default=10000, help="bulk rows per role (default 10000)")
    ap.add_argument("--out", default="scope1_test_data")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    matrix = M.matrix_rows()
    for role in M.ROLES:
        rows = M.volume_rows(a.rows, a.facility, role[:2].upper())
        with open(os.path.join(a.out, f"scope1_{role}_bulk.csv"), "w", encoding="utf-8", newline="") as f:
            f.write(M.to_csv([M.file_row(*r) for r in rows]))
        bodies = [M.payload(r["case"], r["quantity"], r["year"], r["month"],
                            a.facility[r["facility"] % len(a.facility)], f"{role[:2].upper()}{r['eq']}")
                  for r in matrix if r["role"] == role]
        with open(os.path.join(a.out, f"scope1_{role}_manual.json"), "w", encoding="utf-8") as f:
            json.dump(bodies, f, indent=1)

    bad = [[d, a.facility[0], p, fu, q, u, "default", f"INV{i:02d}", "", "", why]
           for i, (d, p, fu, q, u, why) in enumerate(INVALID)]
    with open(os.path.join(a.out, "scope1_invalid.csv"), "w", encoding="utf-8", newline="") as f:
        f.write(M.to_csv(bad, M.FILE_HEADER + ["expected_reason"]))

    cov = M.coverage(matrix, M.PARAMS)
    with open(os.path.join(a.out, "coverage.txt"), "w", encoding="utf-8") as f:
        f.write(f"matrix rows: {len(matrix)}\npairs covered: {cov['pairs_covered']}/{cov['pairs_total']} "
                f"({cov['pair_coverage']:.0%})\nvalue coverage: {cov['value_coverage']}\n")
    print(f"wrote {a.out}: {a.rows} bulk rows x {len(M.ROLES)} roles, {len(matrix)} matrix rows, "
          f"pair coverage {cov['pair_coverage']:.0%}")


if __name__ == "__main__":
    main()
