"""Parity: one Scope 1 input through the single POST, file upload, JSON /import and legacy /bulk-upload.

Every path must store the same gases, CO2e, uncertainty and factor. Cases differ only in
process/fuel/inputs; month is unique per path so records stay separate.
"""
import pytest

from tests.test_bulk_uploaders import csv_rows, emissions, env, reasons, upload  # noqa: F401

COLS = ("co2_emissions", "ch4_emissions", "n2o_emissions", "co2e_total", "uncertainty",
        "uncertainty_ch4", "uncertainty_n2o", "fuel_type", "factor_source", "calc_method")

# (id, process_type, fuel, amount, unit, extra csv header -> value)
CASES = [
    ("ng_scf", "combustion", "Natural Gas", 50000, "scf", {}),
    ("ng_mmbtu", "combustion", "Natural Gas", 1200, "MMBtu", {}),
    ("diesel_gal", "combustion", "Diesel (No. 2 Fuel Oil)", 800, "gal", {}),
    ("pneu", "pneumatic", "Production high-bleed controller (API study)", 12, "devices",
     {"activity_key": "prod_pc_high_bleed_api", "activity_hours": "720"}),
]
# file column carrying the same input as the API field
FILE_COL = {"activity_hours": "Operating Hours"}
FILE_SKIP = {"activity_key"}  # the file resolves the fuel label to the activity key itself


def _row(fac, month, case):
    _, proc, fuel, amt, unit, extra = case
    return {"year": 2025, "month": month, "facility_id": fac, "facility_name": fac,
            "process_type": proc, "fuel": fuel, "amount": amt, "quantity": amt, "unit": unit, **extra}


def _snap(app, fid, month):
    rows = emissions(app, fid, year=2025, month=month)
    assert len(rows) == 1, f"month {month}: {len(rows)} records"
    return {c: getattr(rows[0], c) for c in COLS}


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_four_path_parity(app, client, env, case):  # noqa: F811
    fid, fac = env["fid"], env["fac"]
    _, proc, fuel, amt, unit, extra = case

    # A: single POST (month 1)
    r = client.post("/api/emissions/", json={**_row(fid, 1, case), "facility_id": fid, "factor_source": "default"})
    assert r.status_code == 201, r.get_data(as_text=True)[:300]

    # B: file upload (month 2)
    fx = {k: v for k, v in extra.items() if k not in FILE_SKIP}
    hdr = ["Date", "Facility", "Process Type", "Fuel", "Quantity", "Unit", "Factor Type"] + [FILE_COL[k] for k in fx]
    line = ["2025-02", fac, proc, fuel, str(amt), unit, "default"] + [str(v) for v in fx.values()]
    st = upload(client, 1, csv_rows(",".join(hdr), [",".join('"%s"' % v for v in line)]))
    assert st["skipped_count"] == 0, reasons(st)

    # C: JSON /import (month 3)
    r = client.post("/api/emissions/import", json={"records": [
        {**_row(fac, 3, case), "facility_id": fac, "factor_source": "default"}]})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:300]
    assert not (r.get_json() or {}).get("errors"), r.get_json()

    # D: legacy /bulk-upload (month 4)
    r = client.post("/api/emissions/bulk-upload", json={"confirm": True, "records": [
        {k: (str(v) if not isinstance(v, str) else v) for k, v in
         {**_row(fac, 4, case), "date": "2025-04-01"}.items() if k not in ("year", "month", "facility_id")}]})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:300]
    assert not (r.get_json() or {}).get("errors"), r.get_json()

    ref = _snap(app, fid, 1)
    assert ref["co2e_total"] > 0
    for month, name in ((2, "file upload"), (3, "json import"), (4, "legacy bulk-upload")):
        got = _snap(app, fid, month)
        for c in COLS:
            if isinstance(ref[c], float):
                assert got[c] == pytest.approx(ref[c], rel=1e-9), f"{name}: {c}"
            else:
                assert got[c] == ref[c], f"{name}: {c}"
