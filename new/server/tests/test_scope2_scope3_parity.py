"""Scope 2 and Scope 3: the single POST, the file upload and the JSON bulk-import must store the same values."""
import csv
import io
import logging
import uuid

import pytest

from tests.test_bulk_uploaders import env, upload  # noqa: F401


def _facs(app, n=3):
    from extensions import db
    from models import Facility

    tag = uuid.uuid4().hex[:6]
    with app.app_context():
        fs = [Facility(name=f"P{i} {tag}", region="R", activity="EP", division="D", field="F", segment="Upstream",
                       code=f"P{i}{tag}") for i in range(n)]
        db.session.add_all(fs)
        db.session.commit()
        return [(f.id, f.name) for f in fs]


def _grid_names():
    from electricity_factors import GRID_FACTORS
    return list(GRID_FACTORS)[:2]


def _write(rows, header):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


S2_COLS = ("source_type", "electricity_kwh", "heat_mmbtu", "emission_factor", "co2e", "co2e_location_based",
           "co2e_market_based", "market_instrument_type", "market_emission_factor", "uncertainty", "grid_region")


def _s2_rows(app, fid):
    from models import Scope2Emission

    with app.app_context():
        return {e.month: {c: getattr(e, c) for c in S2_COLS}
                for e in Scope2Emission.query.filter_by(facility_id=fid, year=2025).all()}


def _close(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= 1e-9 * max(1.0, abs(a))
    return a == b


def test_scope2_parity(app, client, env):
    logging.disable(logging.CRITICAL)
    g1, g2 = _grid_names()
    # month, api fields, file columns
    cases = [
        (1, {"source_type": "electricity", "amount": 1500, "unit": "kWh", "grid_region": g1},
            {"Source Type": "electricity", "Consumption": 1500, "Unit": "kWh", "Grid Region": g1}),
        (2, {"source_type": "electricity", "amount": 12.5, "unit": "MWh", "grid_region": g2},
            {"Source Type": "electricity", "Consumption": 12.5, "Unit": "MWh", "Grid Region": g2}),
        (3, {"source_type": "electricity", "amount": 4000, "unit": "kWh", "grid_region": "Supplier X",
             "emission_factor": 0.2, "market_instrument_type": "PPA"},
            {"Source Type": "electricity", "Consumption": 4000, "Unit": "kWh", "Grid Region": "Supplier X",
             "Emission Factor": 0.2, "Market Instrument Type": "PPA"}),
        (4, {"source_type": "electricity", "amount": 2000, "unit": "kWh", "grid_region": g1,
             "market_instrument_type": "REC"},
            {"Source Type": "electricity", "Consumption": 2000, "Unit": "kWh", "Grid Region": g1,
             "Market Instrument Type": "REC"}),
        (5, {"source_type": "electricity", "amount": 2000, "unit": "kWh", "grid_region": g1,
             "market_instrument_type": "supplier_tariff", "market_emission_factor": 0.15},
            {"Source Type": "electricity", "Consumption": 2000, "Unit": "kWh", "Grid Region": g1,
             "Market Instrument Type": "supplier_tariff", "Market Emission Factor": 0.15}),
        (6, {"source_type": "indirect_steam", "amount": 500, "unit": "MMBtu", "boiler_efficiency": 0.85},
            {"Source Type": "indirect_steam", "Consumption": 500, "Unit": "MMBtu", "Boiler Eff": 85}),
        (7, {"source_type": "indirect_steam", "amount": 300, "unit": "GJ", "boiler_efficiency": 0.9},
            {"Source Type": "indirect_steam", "Consumption": 300, "Unit": "GJ", "Boiler Eff": 90}),
    ]
    (fa, na), (fb, nb), (fc, nc) = _facs(app)
    # A single POST, C JSON bulk-import
    for m, api, _ in cases:
        r = client.post("/api/scope2", json={"year": 2025, "month": m, "facility_id": fa, **api})
        assert r.status_code in (200, 201), (m, r.get_data(as_text=True)[:300])
    elec = [(m, api) for m, api, _ in cases if api["source_type"] == "electricity"]
    r = client.post("/api/scope2/bulk-import", json={"records": [
        {"year": 2025, "month": m, "facility_id": nc, "consumption": api["amount"],
         **{k: v for k, v in api.items() if k not in ("amount", "source_type")}} for m, api in elec]})
    assert r.status_code in (200, 201), r.get_data(as_text=True)[:300]
    assert not (r.get_json() or {}).get("errors"), r.get_json()
    # B file upload
    cols = sorted({k for _, _, f in cases for k in f})
    header = ["Date", "Facility"] + cols
    rows = [[f"2025-{m:02d}", nb] + [f.get(c, "") for c in cols] for m, _, f in cases]
    st = upload(client, 2, _write(rows, header))
    assert st["skipped_count"] == 0, st.get("skipped_preview")

    ref, f_, j_ = _s2_rows(app, fa), _s2_rows(app, fb), _s2_rows(app, fc)
    assert set(ref) == {m for m, _, _ in cases}
    problems = []
    for label, got in (("file", f_), ("json", j_)):
        for m in ref:
            if label == "json" and m not in {e[0] for e in elec}:
                continue  # the JSON import is electricity only
            for c in S2_COLS:
                if m not in got or not _close(ref[m][c], got[m][c]):
                    problems.append(f"{label} month {m} {c}: single={ref[m][c]!r} {label}={got.get(m, {}).get(c)!r}")
    assert not problems, "\n".join(problems)


S3_COLS = ("category", "sub_category", "activity_data", "unit", "emission_factor", "co2e", "uncertainty",
           "calculation_method")


def _s3_cases():
    from emission_factors.scope3_activity_factors import SCOPE3_ACTIVITY_FACTORS as A
    out = []
    for cat, rows in A.items():
        for name, unit, factor in rows:
            out.append({"category": f"Category {cat}", "sub_category": name, "unit": unit, "amount": 10,
                        "with_ef": factor is None, "cat_ef": factor})
    # an explicit factor, a supplier total and a spend factor in each of the first categories
    out.append({"category": "Category 1", "sub_category": "Own spend row", "unit": "USD", "amount": 2500.5,
                "emission_factor": 0.42})
    out.append({"category": "Category 11", "sub_category": "Sold fuel", "unit": "tonne", "amount": 12,
                "emission_factor": 2750.0})
    return out


def _s3_rows(app, fid):
    from models import Scope3Emission

    with app.app_context():
        return {(e.category, e.sub_category): {c: getattr(e, c) for c in S3_COLS}
                for e in Scope3Emission.query.filter_by(facility_id=fid, year=2025).all()}


def test_scope3_parity(app, client, env):
    logging.disable(logging.CRITICAL)
    cases = _s3_cases()
    for c in cases:
        if c.pop("with_ef", False):
            c["emission_factor"] = 1.5  # catalog row without a published factor needs one
    (fa, na), (fb, nb), (fc, nc) = _facs(app)

    def api(c):
        # the form fills the catalog factor in; the file and JSON imports look it up themselves
        ef = c.get("emission_factor", c.get("cat_ef"))
        return {k: v for k, v in c.items() if k not in ("amount", "cat_ef")} | {"activity_data": c["amount"],
                                                                                "emission_factor": ef}

    for c in cases:
        r = client.post("/api/scope3", json={"year": 2025, "month": 1, "facility_id": fa, **api(c)})
        assert r.status_code in (200, 201), (c, r.get_data(as_text=True)[:300])
    r = client.post("/api/scope3/bulk-import", json={"records": [
        {"year": 2025, "month": 1, "facility_id": nc, **{k: v for k, v in c.items() if k != "cat_ef"}} for c in cases]})
    json_errors = (r.get_json() or {}).get("errors")
    cols = ["Category", "Sub Category", "Amount", "Unit", "Emission Factor"]
    rows = [["2025-01", nb, c["category"], c["sub_category"], c["amount"], c["unit"], c.get("emission_factor", "")]
            for c in cases]
    st = upload(client, 3, _write(rows, ["Date", "Facility"] + cols))
    ref, f_, j_ = _s3_rows(app, fa), _s3_rows(app, fb), _s3_rows(app, fc)
    print(f"\nscope3 stored: single={len(ref)} file={len(f_)} json={len(j_)} of {len(cases)}; "
          f"file skipped={st.get('skipped_count')} json errors={len(json_errors or [])}")
    problems = []
    for label, got in (("file", f_), ("json", j_)):
        for k in ref:
            if k not in got:
                problems.append(f"{label}: {k} missing")
                continue
            for c in S3_COLS:
                if not _close(ref[k][c], got[k][c]):
                    problems.append(f"{label} {k} {c}: single={ref[k][c]!r} {label}={got[k][c]!r}")
    print("\n".join(problems[:40]), f"\n{len(problems)} scope3 divergences")
    assert len(ref) >= 55
    assert not problems
