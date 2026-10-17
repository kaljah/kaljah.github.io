"""Scope 1 entry matrix: admin, superuser and user through the single POST, the JSON import and the
file upload, Tiers 1 to 3, with all-pairs coverage of the other inputs (quantity boundaries, month,
year bounds, facility).

Every accepted row must store the same values as the admin's single POST of the same input (parity
oracle) and, where the source tables give one, the independently computed value. Role rules: admin
records are Verified (unless flagged), superuser and user records Pending; scoped roles cannot write
outside their region on any path. Rejected input must leave no record and no CREATE audit entry.

Volume run (the plan's 10,000 rows per role): SCOPE1_VOLUME_ROWS=10000 python -m pytest
tests/test_scope1_entry_matrix.py -k volume  (skipped when unset). Files for manual / e2e testing:
scripts/gen_scope1_test_data.py.
"""
import datetime
import logging
import os
import uuid

import pytest

from tests import scope1_matrix_data as M
from tests.test_bulk_uploaders import reasons, upload

COLS = ("co2_emissions", "ch4_emissions", "n2o_emissions", "co2e_total", "ef_used_co2", "ef_used_ch4",
        "ef_used_n2o", "uncertainty", "fuel_type", "factor_source", "calc_method", "process_type", "unit",
        "quantity", "custom_factor_id")
EXPECTED_STATUS = {"admin": "Verified", "superuser": "Pending", "user": "Pending"}
CURRENT_YEAR = datetime.date.today().year


@pytest.fixture(scope="module")
def world():
    """Two facilities in the scoped region, one outside it, one reference facility; one account per
    role; an approved custom factor."""
    from app import app as flask_app
    from extensions import db
    from models import CustomFactor, Facility, User

    tag = uuid.uuid4().hex[:6]
    region, other = f"MxReg{tag}", f"MxOther{tag}"
    with flask_app.app_context():
        def fac(name, reg):
            return Facility(name=f"{name} {tag}", region=reg, activity="EP", division="D", field="F",
                            segment="Upstream", code=f"{name[:3]}{name[-3:]}{tag}")
        facs = [fac("Matrix A", region), fac("Matrix B", region), fac("Matrix Out", other), fac("Matrix Ref", other)]
        users = {}
        for role in ("admin", "superuser", "user", "auditor", "it_admin"):
            u = User(email=f"mx_{role}_{tag}@test.com", fullName=f"Matrix {role}", orgName="T", sector="Energy",
                     role=role, location="Global Corporate Head Office" if role in ("admin", "it_admin") else region)
            u.set_password("MatrixPass123!")
            users[role] = u
        db.session.add_all(facs + list(users.values()))
        db.session.flush()
        f = M.CUSTOM_FACTOR
        cf = CustomFactor(name=f["name"], co2_factor=f["co2_factor"], ch4_factor=f["ch4_factor"],
                          n2o_factor=f["n2o_factor"], unit=f["unit"], source=f["source"], usage="combustion",
                          status="Approved", created_by=users["admin"].id)
        pending = CustomFactor(name=f"Matrix Pending {tag}", co2_factor=60.0, ch4_factor=0.0, n2o_factor=0.0,
                               unit="kg/MMBtu", source="lab", usage="combustion", status="Pending",
                               created_by=users["user"].id)
        db.session.add_all([cf, pending])
        db.session.commit()
        return {"fids": [x.id for x in facs], "names": [x.name for x in facs], "uids": {r: u.id for r, u in users.items()},
                "cfid": cf.id, "pending_cfid": pending.id}


def login(client, world, role):
    with client.session_transaction() as s:
        s["user_id"] = world["uids"][role]


def by_eq(eq):
    from app import app as flask_app
    from models import Emission

    with flask_app.app_context():
        return Emission.query.filter_by(equipment_id=eq).all()


def counts():
    from app import app as flask_app
    from models import ActivityLog, Emission

    with flask_app.app_context():
        return Emission.query.count(), ActivityLog.query.filter_by(action="CREATE", entity="Emission").count()


def saved(st):
    """Records an upload saved ("processed" counts the rows read, skipped ones included)."""
    return sum((st.get("status_counts") or {}).values())


def _close(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= 1e-9 * max(1.0, abs(a))
    return a == b


# ---------------------------------------------------------------- coverage of the generated set
def test_generated_matrix_has_full_pair_and_triple_coverage():
    rows = M.matrix_rows()
    cov = M.coverage(rows, M.PARAMS)
    print(f"\n{len(rows)} rows; pairs {cov['pairs_covered']}/{cov['pairs_total']}; values {cov['value_coverage']}")
    assert cov["pair_coverage"] == 1.0
    assert all(v == 1.0 for v in cov["value_coverage"].values())
    triples = {(r["case"], r["role"], r["path"]) for r in rows}
    wanted = {t for t in [(c, r, p) for c in M.CASES for r in M.ROLES for p in M.PATHS]
              if M.allowed({"case": t[0], "path": t[2]})}
    assert triples == wanted
    assert len({r["eq"] for r in rows}) == len(rows)
    assert all(M.allowed(r) for r in rows)


# ---------------------------------------------------------------- the matrix
def test_scope1_entry_matrix(client, world):
    logging.disable(logging.CRITICAL)
    rows = M.matrix_rows()
    fids, names, cfid = world["fids"], world["names"], world["cfid"]

    # Oracle: the admin's single POST of the same input into the reference facility
    login(client, world, "admin")
    for r in rows:
        res = client.post("/api/emissions/", json=M.payload(r["case"], r["quantity"], r["year"], r["month"], fids[3],
                                                             "R" + r["eq"], cfid))
        assert res.status_code == 201, (r, res.get_json())

    for role in M.ROLES:
        login(client, world, role)
        mine = [r for r in rows if r["role"] == role]
        for r in (x for x in mine if x["path"] == "single"):
            res = client.post("/api/emissions/", json=M.payload(r["case"], r["quantity"], r["year"], r["month"],
                                                                 fids[r["facility"]], r["eq"], cfid))
            assert res.status_code == 201, (r, res.get_json())
        js = [r for r in mine if r["path"] == "json"]
        if js:
            res = client.post("/api/emissions/import", json={"records": [
                M.payload(r["case"], r["quantity"], r["year"], r["month"], names[r["facility"]], r["eq"], cfid) for r in js]})
            body = res.get_json()
            assert res.status_code == 200 and not body.get("errors") and body["imported"] == len(js), body
        fl = [r for r in mine if r["path"] == "file"]
        if fl:
            st = upload(client, 1, M.to_csv([M.file_row(r["case"], r["quantity"], r["year"], r["month"],
                                                        names[r["facility"]], r["eq"]) for r in fl]))
            assert st["status"] == "completed" and st["skipped_count"] == 0, reasons(st)
            assert saved(st) == len(fl), st

    problems = []
    for r in rows:
        got, ref = by_eq(r["eq"]), by_eq("R" + r["eq"])
        if len(got) != 1 or len(ref) != 1:
            problems.append(f"{r}: stored {len(got)} record(s), reference {len(ref)}")
            continue
        g, f = got[0], ref[0]
        for col in COLS:
            if not _close(getattr(g, col), getattr(f, col)):
                problems.append(f"{r['eq']} {r['case']} {r['path']}/{r['role']} {col}: {getattr(g, col)!r} != ref {getattr(f, col)!r}")
        for col, val in (M.expected_tonnes(r["case"], r["quantity"]) or {}).items():
            if abs(getattr(g, col) - val) > 1e-6 * max(1.0, abs(val)):
                problems.append(f"{r['eq']} {r['case']} {col}: {getattr(g, col)!r} != source tables {val!r}")
        want = EXPECTED_STATUS[r["role"]]
        if g.status != want and not (want == "Verified" and g.qa_flag and g.status == "Pending"):
            problems.append(f"{r['eq']} {r['role']}/{r['path']}: status {g.status} (qa_flag {g.qa_flag!r})")
        if g.created_by != world["uids"][r["role"]] or g.facility_id != fids[r["facility"]]:
            problems.append(f"{r['eq']}: created_by {g.created_by} facility {g.facility_id}")
        if (g.year, g.month) != (r["year"], r["month"]):
            problems.append(f"{r['eq']}: period {g.year}-{g.month}")
        if r["quantity"] == 0 and g.co2e_total != 0:
            problems.append(f"{r['eq']}: zero activity stored {g.co2e_total} t")
    print("\n".join(problems[:60]), f"\n{len(problems)} problems over {len(rows)} rows")
    assert not problems


def test_every_single_entry_is_audited_and_the_chain_verifies(client, world):
    """Runs after the matrix (file order): each single-POST record has its CREATE entry; the chain holds."""
    from app import app as flask_app
    from models import ActivityLog, Emission

    single_rows = {r["eq"] for r in M.matrix_rows() if r["path"] == "single"}
    with flask_app.app_context():
        recs = Emission.query.filter(Emission.equipment_id.in_(single_rows)).all()
        assert len(recs) == len(single_rows), "run with the matrix test"
        logged = {a.entity_id for a in ActivityLog.query.filter_by(action="CREATE", entity="Emission").all()}
        missing = [e.equipment_id for e in recs if str(e.id) not in logged]
    assert not missing, missing
    login(client, world, "admin")
    res = client.get("/api/audit/verify-chain")
    assert res.status_code == 200 and res.get_json()["status"] == "verified", res.get_json()


# ---------------------------------------------------------------- access control on every path
@pytest.mark.parametrize("role", M.ROLES)
def test_out_of_region_facility_on_every_path(client, world, role):
    logging.disable(logging.CRITICAL)
    login(client, world, role)
    fid_out, name_out = world["fids"][2], world["names"][2]
    tag = uuid.uuid4().hex[:6]
    scoped = role != "admin"

    res = client.post("/api/emissions/", json=M.payload("t1_ng_scf", 100, 2025, 3, fid_out, f"OS{tag}"))
    assert res.status_code == (403 if scoped else 201), res.get_json()
    assert len(by_eq(f"OS{tag}")) == (0 if scoped else 1)

    res = client.post("/api/emissions/import", json={"records": [M.payload("t1_ng_scf", 100, 2025, 3, name_out, f"OJ{tag}")]})
    body = res.get_json()
    assert len(by_eq(f"OJ{tag}")) == (0 if scoped else 1), body
    if scoped:  # every record refused: the reply is an error with the row details
        assert any("Unauthorized" in e for e in body.get("errors") or body.get("details") or []), body

    st = upload(client, 1, M.to_csv([M.file_row("t1_ng_scf", 100, 2025, 3, name_out, f"OF{tag}")]))
    assert len(by_eq(f"OF{tag}")) == (0 if scoped else 1), st
    if scoped:
        assert st["skipped_count"] == 1 and "Access denied" in reasons(st)[0]


@pytest.mark.parametrize("role", ["auditor", "it_admin"])
def test_read_only_and_it_roles_cannot_create(client, world, role):
    login(client, world, role)
    before = counts()
    res = client.post("/api/emissions/", json=M.payload("t1_ng_scf", 100, 2025, 3, world["fids"][0], "RO" + role))
    assert res.status_code == 403
    assert counts() == before


# ---------------------------------------------------------------- manual entry: validation rules
def _invalid_cases(world):
    """(id, payload change, expected status, error field or text); None removes a field."""
    pend = world["pending_cfid"]
    return [
        ("missing_year", {"year": None}, 422, "year"),
        ("missing_month", {"month": None}, 422, "month"),
        ("missing_facility", {"facility_id": None}, 422, "facility_id"),
        ("missing_process", {"process_type": None}, 422, "process_type"),
        ("missing_quantity", {"amount": None}, 422, "quantity"),
        ("missing_unit", {"unit": ""}, 422, "unit"),
        ("month_0", {"month": 0}, 422, "month"),
        ("month_13", {"month": 13}, 422, "month"),
        ("year_1899", {"year": 1899}, 422, "year"),
        ("year_next_plus_1", {"year": CURRENT_YEAR + 2}, 422, "year"),
        ("negative_quantity", {"amount": -1}, 422, "amount"),
        ("text_quantity", {"amount": "abc"}, 422, "amount"),
        ("comma_text_quantity", {"amount": "1,000"}, 422, "amount"),
        ("bare_ton", {"unit": "ton", "fuel": "Diesel (No. 2 Fuel Oil)"}, 422, "unit"),
        ("ambiguous_Mt", {"unit": "Mt"}, 422, "unit"),
        ("wrong_dimension_unit", {"unit": "km"}, 422, None),
        ("facility_text", {"facility_id": "abc"}, 422, None),
        ("facility_bool", {"facility_id": True}, 422, None),
        ("scope2_process", {"process_type": "electricity"}, 422, "process_type"),
        ("process_not_text", {"process_type": 7}, 422, None),
        ("fuel_too_long", {"fuel": "x" * 201}, 422, None),
        ("unknown_fuel", {"fuel": "Unobtainium"}, 422, None),
        ("tier2_without_factor", {"factor_source": "custom"}, 422, "custom_factor_id"),
        ("tier2_pending_factor", {"factor_source": "custom", "custom_factor_id": pend, "unit": "MMBtu"}, 422, "custom_factor_id"),
        ("tier2_unknown_factor", {"factor_source": "custom", "custom_factor_id": 99999999, "unit": "MMBtu"}, 422, "custom_factor_id"),
        ("tier3_bad_factor", {"factor_source": "specific", "unit": "m3", "hhv": 1020, "combustion_efficiency": 0.995,
                              "specific_factors": {"co2": "abc", "co2Unit": "kg/m3"}}, 422, None),
        ("ch4_content_over_100", {"process_type": "venting", "fuel": "Natural Gas (Venting/Blowdown)", "unit": "m3",
                                  "ch4_content": 150}, 422, None),
    ]


@pytest.mark.parametrize("role", M.ROLES)
def test_invalid_manual_entries_are_refused_without_side_effects(client, world, role):
    logging.disable(logging.CRITICAL)
    login(client, world, role)
    fails = []
    for cid, change, code, field in _invalid_cases(world):
        body = M.payload("t1_ng_scf", 100, 2025, 4, world["fids"][0], f"BAD-{cid}-{role}")
        for k, v in change.items():
            if v is None:
                body.pop(k, None)
            else:
                body[k] = v
        before = counts()
        res = client.post("/api/emissions/", json=body)
        err = res.get_json() or {}
        if res.status_code != code:
            fails.append(f"{cid}: {res.status_code} {err}")
        elif field and field != err.get("field") and field not in str(err.get("error", "")).lower():
            fails.append(f"{cid}: field {err.get('field')!r} / {err.get('error')!r}, expected {field}")
        if not err.get("error"):
            fails.append(f"{cid}: no error message")
        if counts() != before:
            fails.append(f"{cid}: a record or audit entry was written")
    assert not fails, "\n".join(fails)


def test_body_must_be_an_object(client, world):
    login(client, world, "user")
    before = counts()
    assert client.post("/api/emissions/", json=[1, 2]).status_code == 400
    assert counts() == before


@pytest.mark.parametrize("role", M.ROLES)
def test_unknown_facility(client, world, role):
    login(client, world, role)
    res = client.post("/api/emissions/", json=M.payload("t1_ng_scf", 100, 2025, 4, 99999999, f"NOFAC{role}"))
    # scoped roles are refused before the lookup, so the existence of other facilities does not leak
    assert res.status_code == (404 if role == "admin" else 403), res.get_json()


@pytest.mark.parametrize("role", M.ROLES)
def test_duplicate_needs_confirmation_then_goes_to_review(client, world, role):
    logging.disable(logging.CRITICAL)
    login(client, world, role)
    tag = uuid.uuid4().hex[:6]
    body = M.payload("t1_diesel_gal", 500, 2025, 5, world["fids"][1], f"DUP{tag}")
    assert client.post("/api/emissions/", json=body).status_code == 201
    before = counts()
    res = client.post("/api/emissions/", json=body)
    assert res.status_code == 409 and res.get_json()["requires_confirmation"] is True
    assert counts() == before
    res = client.post("/api/emissions/", json={**body, "allow_duplicate": True})
    assert res.status_code == 201
    recs = sorted(by_eq(f"DUP{tag}"), key=lambda e: e.id)
    assert len(recs) == 2 and recs[1].status == "Pending" and "duplicate" in (recs[1].qa_flag or "").lower()


@pytest.mark.parametrize("role", M.ROLES)
def test_draft_is_kept_as_draft_on_the_form(client, world, role):
    login(client, world, role)
    eq = f"DRAFT{uuid.uuid4().hex[:6]}"
    res = client.post("/api/emissions/", json={**M.payload("t1_ng_scf", 10, 2025, 7, world["fids"][0], eq), "status": "Draft"})
    assert res.status_code == 201
    assert by_eq(eq)[0].status == "Draft"


# ---------------------------------------------------------------- bulk: invalid rows, file structure
BAD_ROWS = [  # (Date, Quantity, Unit, Fuel, Process, reason fragment)
    ("2025-13", "1", "scf", "Natural Gas", "combustion", "Invalid date"),
    ("2025-06", "-5", "scf", "Natural Gas", "combustion", "Invalid quantity"),
    ("2025-06", "abc", "scf", "Natural Gas", "combustion", "Invalid quantity"),
    ("2025-06", "5", "ton", "Diesel (No. 2 Fuel Oil)", "combustion", "ambiguous"),
    ("2025-06", "5", "scf", "Unobtainium", "combustion", "not in the emission factor catalog"),
    ("2025-06", "5", "scf", "Natural Gas", "electricity", "Scope 2"),
    ("2025-06", "", "scf", "Natural Gas", "combustion", "quantity"),
]


@pytest.mark.parametrize("role", M.ROLES)
def test_mixed_file_imports_good_rows_and_reports_each_bad_row(client, world, role):
    logging.disable(logging.CRITICAL)
    login(client, world, role)
    tag = uuid.uuid4().hex[:6]
    name = world["names"][0]
    rows = []
    for i, (date, qty, unit, fuel, proc, _) in enumerate(BAD_ROWS):
        rows.append([date, name, proc, fuel, qty, unit, "default", f"BB{tag}{i}", "", ""])
        rows.append(M.file_row("t1_ng_scf", 100 + i, 2025, 6, name, f"GB{tag}{i}"))
    rows.append(["2025-06", world["names"][2], "combustion", "Natural Gas", "5", "scf", "default", f"BBOUT{tag}", "", ""])
    st = upload(client, 1, M.to_csv(rows))
    stored = len(BAD_ROWS) + (1 if role == "admin" else 0)   # the out-of-region row is the admin's to write
    assert saved(st) == stored and st["total"] == len(rows), st
    assert st["skipped_count"] == len(rows) - stored, reasons(st)
    got = reasons(st)
    for (_, _, _, _, _, frag) in BAD_ROWS:
        assert any(frag.lower() in r.lower() for r in got), (frag, got)
    for i in range(len(BAD_ROWS)):
        assert len(by_eq(f"GB{tag}{i}")) == 1 and not by_eq(f"BB{tag}{i}")
    assert len(by_eq(f"BBOUT{tag}")) == (1 if role == "admin" else 0)
    if role != "admin":
        assert st["status_counts"] == {"Pending": stored}, st["status_counts"]


@pytest.mark.parametrize("role", M.ROLES)
def test_json_import_isolates_bad_records(client, world, role):
    logging.disable(logging.CRITICAL)
    login(client, world, role)
    tag = uuid.uuid4().hex[:6]
    name = world["names"][1]
    good = M.payload("t1_ng_mmbtu", 50, 2025, 8, name, f"JG{tag}")
    bad = [{**M.payload("t1_ng_mmbtu", 50, 2025, 8, name, f"JB{tag}{i}"), **chg} for i, chg in enumerate([
        {"amount": -3}, {"unit": "ton"}, {"month": 13}, {"process_type": "electricity"}, {"fuel": "Unobtainium"}])]
    res = client.post("/api/emissions/import", json={"records": [good] + bad})
    body = res.get_json()
    assert res.status_code == 200 and body["imported"] == 1, body
    assert len(body["errors"]) == len(bad), body
    assert len(by_eq(f"JG{tag}")) == 1
    assert not any(by_eq(f"JB{tag}{i}") for i in range(len(bad)))


def test_file_structure_errors(client, world):
    logging.disable(logging.CRITICAL)
    login(client, world, "admin")
    name = world["names"][0]
    before = counts()[0]
    st = upload(client, 1, "")
    assert st["total"] == 0 and saved(st) == 0
    st = upload(client, 1, "foo,bar\n1,2\n")                       # unknown header: the row is refused
    assert saved(st) == 0 and st["skipped_count"] == 1 and "year" in reasons(st)[0]
    st = upload(client, 1, f"Date,Facility,Process Type,Fuel,Unit\n2025-04,{name},combustion,Natural Gas,scf\n")
    assert saved(st) == 0 and "quantity" in reasons(st)[0].lower()
    st = upload(client, 1, "Date,Facility,Process Type,Fuel,Quantity,Unit\n"
                           "EXAMPLE 2024-01,X,combustion,Natural Gas,1,scf\n")   # template example row
    assert saved(st) == 0 and "example" in reasons(st)[0].lower()
    assert counts()[0] == before


def test_semicolon_file_reads_decimal_comma(client, world):
    logging.disable(logging.CRITICAL)
    login(client, world, "admin")
    eq = f"SC{uuid.uuid4().hex[:6]}"
    st = upload(client, 1, f"Date;Facility;Process Type;Fuel;Quantity;Unit;Equipment ID\n"
                           f"2025-09;{world['names'][0]};combustion;Natural Gas;1,5;MMBtu;{eq}\n")
    assert saved(st) == 1, reasons(st)
    assert by_eq(eq)[0].quantity == pytest.approx(1.5)


# ---------------------------------------------------------------- volume (opt-in)
@pytest.mark.skipif(not os.environ.get("SCOPE1_VOLUME_ROWS"), reason="set SCOPE1_VOLUME_ROWS (e.g. 10000) to run")
@pytest.mark.timeout(3600)
@pytest.mark.parametrize("role", M.ROLES)
def test_volume_file_per_role(client, world, role):
    """N unique rows per role in one file: all stored, none skipped, totals equal the per-unit reference."""
    from app import app as flask_app
    from models import Emission

    logging.disable(logging.CRITICAL)
    n = int(os.environ["SCOPE1_VOLUME_ROWS"])
    names = world["names"][:2]
    tag = f"{role[:2]}{uuid.uuid4().hex[:4]}"
    rows = M.volume_rows(n, names, tag)
    login(client, world, "admin")
    unit_co2e = {}
    for case in {r[0] for r in rows}:   # factor-based cases are linear in the quantity
        eq = f"U{tag}{case}"
        res = client.post("/api/emissions/", json=M.payload(case, 1000, 2025, 2, world["fids"][3], eq, world["cfid"]))
        assert res.status_code == 201, res.get_json()
        unit_co2e[case] = by_eq(eq)[0].co2e_total / 1000
    login(client, world, role)
    st = upload(client, 1, M.to_csv([M.file_row(*r) for r in rows]))
    assert st["status"] == "completed" and st["skipped_count"] == 0, reasons(st)[:10]
    assert saved(st) == n
    with flask_app.app_context():
        stored = Emission.query.filter(Emission.equipment_id.like(f"V{tag}%")).all()
        assert len(stored) == n
        assert {e.status for e in stored} <= {EXPECTED_STATUS[role], "Pending"}
        total = sum(e.co2e_total for e in stored)
    expected = sum(unit_co2e[c] * q for c, q, *_ in rows)
    assert total == pytest.approx(expected, rel=1e-9)


@pytest.fixture(autouse=True)
def _restore_logging():
    """Tests here silence logging while they flood the importer; later tests must see errors again."""
    yield
    logging.disable(logging.NOTSET)
