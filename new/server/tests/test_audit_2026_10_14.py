"""Regression tests for the 2026-10-14 zero-baseline audit (BUG-0001..0074).

BUG-0001 and BUG-0002 are covered in tests/test_it_role_security.py and
tests/test_audit_rc1_authz_reports.py.
"""
import io
import time

import pytest

from app import app
from audit_helpers import login, make_facility, make_user, uniq
from extensions import db
from models import Emission


@pytest.fixture
def ctx():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        yield


CSV_HDR = "date,facility_name,process_type,fuel,quantity,unit,tier\n"


def _start(client, text, name):
    r = client.post("/api/emissions/upload/start", content_type="multipart/form-data",
                    data={"file": (io.BytesIO(text.encode()), name), "scope": "1", "decimal_mark": "point"})
    assert r.status_code in (200, 202), r.get_data(as_text=True)[:300]
    return r.get_json()["job_id"]


def _wait(client, jobs, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        states = [client.get(f"/api/emissions/upload/status/{j}").get_json()["status"] for j in jobs]
        if all(s not in ("processing", "queued", "pending", "running") for s in states):
            return states
        time.sleep(0.2)
    raise AssertionError(f"uploads did not finish: {states}")


# ── BUG-0003: concurrent identical uploads must not insert duplicates ──────────────

def test_bug0003_concurrent_identical_uploads_store_rows_once(ctx, monkeypatch):
    import calculations

    real = calculations.compute_emissions

    def slow(*a, **kw):  # keep each job running long enough for the three to overlap
        time.sleep(0.05)
        return real(*a, **kw)

    monkeypatch.setattr(calculations, "compute_emissions", slow)
    fac = make_facility(name=uniq("RaceFac"))
    admin = make_user("admin", "Global")
    year = 2009
    text = CSV_HDR + "".join(f"{year}-{m:02d},{fac.name},stationary_combustion,Natural Gas,10,MMBtu,1\n"
                             for m in range(1, 13))
    with app.test_client() as c:
        login(c, admin)
        jobs = [_start(c, text, f"race{i}.csv") for i in range(3)]
        states = _wait(c, jobs)
        skipped = [c.get(f"/api/emissions/upload/status/{j}").get_json().get("skipped_count", 0) for j in jobs]
    db.session.expire_all()
    n = Emission.query.filter_by(facility_id=fac.id, year=year).count()
    assert n == 12, (n, states, skipped)
    assert sorted(skipped) == [0, 12, 12]


# ── BUG-0004 / BUG-0023: equity allocation ─────────────────────────────────────────

def _partner(code):
    from models import JvPartner
    from routes.equity_routes import ensure_default_partners

    ensure_default_partners()
    return JvPartner.query.filter_by(code=code).first()


def _alloc(client, fac, year):
    r = client.get(f"/api/equity/allocation?year={year}&facility_id={fac.id}")
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    row = r.get_json()[0]
    return row, {p["partner_code"]: p for p in row["partners"]}


def test_bug0004_operator_takes_the_remainder_not_100_on_top(ctx):
    fac = make_facility()
    year = 2008
    db.session.add(Emission(facility_id=fac.id, year=year, month=3, process_type="combustion",
                            co2e_total=1000.0, ch4_emissions=2.0, status="Verified"))
    db.session.commit()
    admin = make_user("admin", "Global")
    eni = _partner("ENI")
    with app.test_client() as c:
        login(c, admin)
        r = c.post("/api/equity/shares", json={"facility_id": fac.id, "partner_id": eni.id,
                                               "equity_share_pct": 40, "effective_start_date": f"{year}-01-01"})
        assert r.status_code == 200, r.get_data(as_text=True)
        row, by = _alloc(c, fac, year)
    assert by["SH"]["equity_pct"] == pytest.approx(60.0)
    assert by["ENI"]["equity_pct"] == pytest.approx(40.0)
    assert sum(p["allocated_co2e"] for p in row["partners"]) == pytest.approx(1000.0)
    assert row["is_fully_allocated"]


def test_bug0023_mid_year_share_change_follows_the_months_of_the_emissions(ctx):
    fac = make_facility(equity_share_pct=0.0)  # operator holds nothing: ENI is the only partner
    year = 2007
    for m in range(1, 7):  # all emissions January to June
        db.session.add(Emission(facility_id=fac.id, year=year, month=m, process_type="combustion",
                                co2e_total=100.0, status="Verified"))
    db.session.commit()
    admin = make_user("admin", "Global")
    eni = _partner("ENI")
    with app.test_client() as c:
        login(c, admin)
        for start, end, pct in ((f"{year}-01-01", f"{year}-06-30", 50), (f"{year}-07-01", None, 100)):
            body = {"facility_id": fac.id, "partner_id": eni.id, "equity_share_pct": pct,
                    "effective_start_date": start, "effective_end_date": end}
            assert c.post("/api/equity/shares", json=body).status_code == 200
        row, by = _alloc(c, fac, year)
    assert by["ENI"]["allocated_co2e"] == pytest.approx(300.0)  # 50 % of 600 t, not 75.2 %
    assert row["unallocated_co2e"] == pytest.approx(300.0)
