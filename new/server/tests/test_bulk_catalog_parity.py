"""Catalog-wide parity: every API factor fuel and every Compendium activity row, calculated through
the single POST, the file upload, JSON /import and legacy /bulk-upload. Each path must accept the
same rows and store identical results (the four paths use separate facilities)."""
import csv
import logging
import io
import json
import uuid

import pytest

from calculations.activity_factors import ACTIVITY_FACTORS
from emission_factors import API_FACTORS
from tests.test_bulk_uploaders import emissions, upload  # noqa: F401

COLS = ("co2_emissions", "ch4_emissions", "n2o_emissions", "co2e_total", "uncertainty", "uncertainty_ch4",
        "uncertainty_n2o", "fuel_type", "factor_source", "calc_method", "process_type", "unit", "quantity",
        "ef_used_co2", "ef_used_ch4", "ef_used_n2o")


def _cases():
    out = []
    for key, r in ACTIVITY_FACTORS.items():
        out.append({"id": f"act:{key}", "process_type": r["processes"][0], "fuel": r["label"],
                    "activity_key": key, "unit": r["activity"]})
    for name, f in API_FACTORS.items():
        usage = f.get("usage")
        proc = (usage if isinstance(usage, str) else (usage or [None])[0]) or f.get("process_category")
        unit = str(f.get("unit") or "").split("/")[-1].strip()
        if proc and unit:
            out.append({"id": f"fuel:{name}", "process_type": proc, "fuel": name, "unit": unit})
    for i, c in enumerate(out):
        c["eq"] = f"EQ{i:04d}"
    return out


CASES = _cases()


@pytest.fixture
def fac4(app):
    from extensions import db
    from models import Facility, User

    tag = uuid.uuid4().hex[:6]
    with app.app_context():
        u = User(email=f"cat_{tag}@test.com", fullName="Cat Admin", orgName="T", sector="Energy", role="admin",
                 location="Global Corporate Head Office")
        u.set_password("CatAdmin123!")
        fs = [Facility(name=f"Cat {p} {tag}", region="R", activity="EP", division="D", field="F", segment="Upstream",
                       code=f"C{p}{tag}") for p in "ABCD"]
        db.session.add_all([u] + fs)
        db.session.commit()
        return {"uid": u.id, "fids": [f.id for f in fs], "names": [f.name for f in fs]}


def _snap(app, fid):
    return {e.equipment_id: {c: getattr(e, c) for c in COLS} for e in emissions(app, fid, year=2025, month=1)}


def test_catalog_parity(app, client, fac4):
    logging.disable(logging.CRITICAL)
    with client.session_transaction() as s:
        s["user_id"] = fac4["uid"]
    fids, names = fac4["fids"], fac4["names"]
    # keep the run bounded and deterministic: every case, amount 3
    rows = [{**c, "amount": 3} for c in CASES]

    # A single POST
    for c in rows:
        client.post("/api/emissions/", json={"year": 2025, "month": 1, "facility_id": fids[0], "factor_source": "default",
                                             "equipment_id": c["eq"], **{k: c[k] for k in
                                             ("process_type", "fuel", "activity_key", "unit", "amount") if k in c}})
    # B file upload
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Facility", "Process Type", "Fuel", "Quantity", "Unit", "Factor Type", "Equipment ID"])
    for c in rows:
        w.writerow(["2025-01", names[1], c["process_type"], c["fuel"], c["amount"], c["unit"], "default", c["eq"]])
    from tests.test_bulk_uploaders import upload as up
    up(client, 1, buf.getvalue())
    # C JSON import
    client.post("/api/emissions/import", json={"records": [
        {"year": 2025, "month": 1, "facility_id": names[2], "factor_source": "default", "equipment_id": c["eq"],
         **{k: c[k] for k in ("process_type", "fuel", "activity_key", "unit", "amount") if k in c}} for c in rows]})
    # D legacy bulk-upload
    client.post("/api/emissions/bulk-upload", json={"confirm": True, "records": [
        {"date": "2025-01-01", "facility_name": names[3], "process_type": c["process_type"], "fuel": c["fuel"],
         "quantity": str(c["amount"]), "unit": c["unit"], "equipment": c["eq"],
         **({"activity_key": c["activity_key"]} if "activity_key" in c else {})} for c in rows]})

    snaps = [_snap(app, f) for f in fids]
    ref = snaps[0]
    print(f"\naccepted: single={len(snaps[0])} file={len(snaps[1])} json={len(snaps[2])} legacy={len(snaps[3])} of {len(rows)}")
    assert len(ref) > 100, "too few catalog rows accepted by the single POST to be a meaningful check"
    problems = []
    for label, sn in zip(("file", "json", "legacy"), snaps[1:]):
        for eq in sorted(set(ref) | set(sn)):
            c = next(x for x in rows if x["eq"] == eq)
            if (eq in ref) != (eq in sn):
                problems.append(f"{label}: {c['id']} accepted by {'single' if eq in ref else label} only")
                continue
            for col in COLS:
                a, b = ref[eq][col], sn[eq][col]
                ok = (abs(a - b) <= 1e-9 * max(1.0, abs(a))) if isinstance(a, float) and isinstance(b, float) else a == b
                if not ok:
                    problems.append(f"{label}: {c['id']} {col}: single={a!r} {label}={b!r}")
    print("\n".join(problems[:60]), f"\n{len(problems)} divergences")
    assert not problems
