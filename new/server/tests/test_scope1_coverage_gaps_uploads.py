"""Scope 1 upload and import coverage gap tests (split from test_scope1_coverage_gaps.py)."""
import io
import json
import logging
import uuid
import pytest
from extensions import db
from models import CustomFactor, Emission, Facility, User
from tests.test_bulk_uploaders import upload
from tests.test_scope1_coverage_gaps import ACTORS, _as, _seed, lifecycle_world

# ---------------------------------------------------------------- upload request checks
def test_upload_request_is_checked(client, lifecycle_world):
    w = lifecycle_world

    def start(actor="user", files=True, name="a.csv", body=b"Date\n", **form):
        _as(client, w, actor)
        data = {"scope": form.pop("scope", "1"), **form}
        if files:
            data["file"] = (io.BytesIO(body), name)
        return client.post("/api/emissions/upload/start", data=data, content_type="multipart/form-data")

    assert start(files=False).status_code == 400
    assert start(name="").status_code == 400
    r = start(name="old.xls")
    assert r.status_code == 400 and ".xls" in r.get_json()["error"]
    assert start(name="data.txt").status_code == 400
    assert start(actor="auditor").status_code == 403
    assert start(actor="it_admin").status_code == 403
    assert start(scope="9").status_code == 400
    assert start(column_mapping="{not json").status_code == 400
    assert start(column_mapping="[1, 2]").status_code == 400
    r = start(name="fake.xlsx", body=b"this is not a workbook")
    assert r.status_code == 400, r.get_json()


# ---------------------------------------------------------------- file rows refused for reasons no test reached
def test_file_rows_refused_with_their_reason(app, client, lifecycle_world):
    from extensions import db
    from models import CustomFactor, Facility

    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    with app.app_context():
        fname = db.session.get(Facility, w["fids"]["in"]).name
        for _ in range(2):   # two active factors with the same name: ambiguous in a file
            db.session.add(CustomFactor(name=f"Twin {tag}", co2_factor=50, ch4_factor=0, n2o_factor=0, unit="kg/MMBtu",
                                        source="lab", status="Approved", created_by=w["uids"]["admin"]))
        db.session.commit()
    _as(client, w, "admin")
    head = "Date,Facility,Process Type,Fuel,Quantity,Unit,Factor Type,Equipment ID,ch4_content,activity_key\n"
    rows = [
        (f"2025-07,{fname},combustion,Natural Gas,10,MMBtu,magic,R{tag}1,,", "Unknown factor type"),
        (f"2025-07,{fname},combustion,Twin {tag},10,MMBtu,custom,R{tag}2,,", "not unique"),
        (f"2025-07,{fname},flaring,Natural Gas (Flaring),10,m3,default,R{tag}3,,no_such_key", "Unknown activity factor"),
        (f"2025-07,{fname},venting,Natural Gas (Venting/Blowdown),10,m3,default,R{tag}4,abc%,", "ch4_content"),
        (f"2025-07,{fname},combustion,Natural Gas,2000000000,MMBtu,default,R{tag}5,,", "Implausible"),
    ]
    st = upload(client, 1, head + "\n".join(r for r, _ in rows) + "\n")
    got = " | ".join(s["reason"] for s in st["skipped_preview"])
    assert st["skipped_count"] == len(rows), got
    for _, frag in rows:
        assert frag.lower() in got.lower(), (frag, got)


def test_file_row_with_an_activity_key_of_another_process(app, client, lifecycle_world):
    from calculations.activity_factors import ACTIVITY_FACTORS
    from extensions import db
    from models import Facility

    w = lifecycle_world
    key, row = next((k, r) for k, r in ACTIVITY_FACTORS.items() if "combustion" not in r["processes"])
    with app.app_context():
        fname = db.session.get(Facility, w["fids"]["in"]).name
    _as(client, w, "admin")
    st = upload(client, 1, "Date,Facility,Process Type,Fuel,Quantity,Unit,activity_key\n"
                           f"2025-08,{fname},combustion,Natural Gas,10,{row['activity']},{key}\n")
    assert st["skipped_count"] == 1 and "is not a combustion factor" in st["skipped_preview"][0]["reason"]


# ---------------------------------------------------------------- JSON import: refusals no test reached
def test_json_import_refusals(app, client, lifecycle_world):
    from extensions import db
    from models import Facility

    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    with app.app_context():   # two facilities sharing a name in the user's region
        reg = db.session.get(Facility, w["fids"]["in"]).region
        for i in range(2):
            db.session.add(Facility(name=f"Same {tag}", region=reg, activity="EP", division="D", field="F",
                                    segment="Upstream", code=f"SM{i}{tag}"))
        try:
            db.session.commit()
            twin = True
        except Exception:     # facility names are unique (audit 2026-10-14): ambiguity cannot arise
            db.session.rollback()
            twin = False
    _as(client, w, "user")
    assert client.post("/api/emissions/import", json={"records": []}).status_code == 400
    base = {"year": 2025, "month": 9, "process_type": "combustion", "fuel": "Natural Gas", "amount": 10,
            "unit": "MMBtu", "factor_source": "default"}
    res = client.post("/api/emissions/import", json={"records": [
        {**base, "facility_id": w["fids"]["in"], "amount": 2.0e9, "equipment_id": f"J{tag}2"},
        {**base, "facility_id": "999999999", "equipment_id": f"J{tag}3"},
        {**base, "facility_id": w["fids"]["in"], "equipment_id": f"J{tag}4"},
    ]})
    body = res.get_json()
    errs = " | ".join(body.get("errors") or body.get("details") or [])
    assert body.get("imported") == 1, body
    assert "Implausible" in errs and "999999999" in errs, errs
    print("\nduplicate facility names possible:", twin)


# ---------------------------------------------------------------- legacy JSON bulk upload
def test_legacy_bulk_upload_preview_roles_and_dates(app, client, lifecycle_world):
    from extensions import db
    from models import Emission, Facility

    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    with app.app_context():
        fname = db.session.get(Facility, w["fids"]["in"]).name
    rec = {"date": "2025-10-01", "facility_name": fname, "type": "combustion", "fuel": "Natural Gas",
           "quantity": "10", "unit": "MMBtu", "equipment": f"LB{tag}"}
    for actor in ("auditor", "it_admin"):
        _as(client, w, actor)
        assert client.post("/api/emissions/bulk-upload", json={"records": [rec]}).status_code == 403
    _as(client, w, "user")
    res = client.post("/api/emissions/bulk-upload", json={"records": [rec, {**rec, "date": "10/2025", "equipment": f"LB{tag}b"}]})
    body = res.get_json()
    assert res.status_code == 200 and body["status"] == "preview" and body["valid_count"] == 1, body
    with app.app_context():
        assert not Emission.query.filter(Emission.equipment_id.like(f"LB{tag}%")).all()   # a preview saves nothing
    res = client.post("/api/emissions/bulk-upload", json={"records": [rec], "confirm": True})
    assert res.status_code in (200, 201), res.get_json()
    with app.app_context():
        saved = Emission.query.filter_by(equipment_id=f"LB{tag}").one()
        assert saved.status == "Pending" and saved.process_type == "combustion"


# ---------------------------------------------------------------- custom factors: edit, reject, archive, import
def test_custom_factor_edit_reject_archive_import(app, client, lifecycle_world):
    from extensions import db
    from models import CustomFactor

    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    _as(client, w, "superuser")
    r = client.post("/api/custom-factors", json={"name": f"CF {tag}", "co2_factor": 60, "ch4_factor": 0.01,
                                                  "n2o_factor": 0.001, "unit": "kg/MMBtu", "source": "Lab 2025"})
    assert r.status_code in (200, 201), r.get_json()
    cfid = r.get_json().get("id") or r.get_json()["factor"]["id"]

    assert client.put("/api/custom-factors/999999999", json={"co2_factor": 1}).status_code == 404
    assert client.put(f"/api/custom-factors/{cfid}", json={}).status_code == 400
    assert client.put(f"/api/custom-factors/{cfid}", json={"unit": "furlongs"}).status_code == 400
    assert client.put(f"/api/custom-factors/{cfid}", json={"ch4_factor": -1}).status_code == 400
    assert client.put(f"/api/custom-factors/{cfid}", json={"parent_fuel": "Unobtainium"}).status_code == 400
    r = client.put(f"/api/custom-factors/{cfid}", json={
        "name": f"CF {tag} v2", "unit": "kg/MMBtu", "co2_factor": 61, "ch4_factor": 0.02, "n2o_factor": 0.002,
        "co_factor": 0, "hhv_factor": 1.02, "uncertainty": 5, "co2_uncertainty": 2, "ch4_uncertainty": 50,
        "n2o_uncertainty": 100, "usage": "combustion", "version": "2", "source": "Lab 2025 rev"})
    assert r.status_code == 200, r.get_json()
    with app.app_context():
        f = db.session.get(CustomFactor, cfid)
        assert (f.name, f.co2_factor, f.ch4_factor, f.version, f.n2o_uncertainty) == (f"CF {tag} v2", 61, 0.02, "2", 100)

    # reject: makers cannot, unknown factor 404, a pending factor is rejected with the reviewer recorded
    _as(client, w, "user")
    assert client.post(f"/api/custom-factors/{cfid}/reject", json={}).status_code == 403
    _as(client, w, "admin")
    assert client.post("/api/custom-factors/999999999/reject", json={}).status_code == 404
    r = client.post(f"/api/custom-factors/{cfid}/reject", json={"reason": "source missing"})
    assert r.status_code == 200, r.get_json()
    with app.app_context():
        f = db.session.get(CustomFactor, cfid)
        assert f.status == "Rejected" and f.approved_by == w["uids"]["admin"]
    assert client.post("/api/custom-factors/999999999/approve").status_code == 404
    assert client.post("/api/custom-factors/999999999/archive", json={}).status_code == 404
    assert client.delete("/api/custom-factors/999999999").status_code == 404

    # restoring an archived factor whose name is taken by an active one is refused
    with app.app_context():
        old = CustomFactor(name=f"Dup {tag}", co2_factor=1, ch4_factor=0, n2o_factor=0, unit="kg/MMBtu", source="s",
                           status="Approved", is_archived=True, created_by=w["uids"]["admin"])
        new = CustomFactor(name=f"Dup {tag}", co2_factor=2, ch4_factor=0, n2o_factor=0, unit="kg/MMBtu", source="s",
                           status="Approved", created_by=w["uids"]["admin"])
        db.session.add_all([old, new])
        db.session.commit()
        old_id = old.id
    r = client.post(f"/api/custom-factors/{old_id}/archive", json={"restore": True})
    assert r.status_code == 409, r.get_json()

    # import: rows without name / unit, duplicate names and bad values are skipped with a reason
    r = client.post("/api/custom-factors/import", json={"factors": []})
    assert r.status_code == 400
    r = client.post("/api/custom-factors/import", json={"factors": [
        {"name": f"Imp {tag}", "unit": "kg/MMBtu", "co2_factor": 50, "source": "lab"},
        {"name": f"Imp {tag}", "unit": "kg/MMBtu", "co2_factor": 51, "source": "lab"},
        {"name": "", "unit": "kg/MMBtu", "co2_factor": 1, "source": "lab"},
        {"name": f"Imp2 {tag}", "unit": "furlongs", "co2_factor": 1, "source": "lab"},
        {"name": f"Imp3 {tag}", "unit": "kg/MMBtu", "co2_factor": -4, "source": "lab"},
    ]})
    body = r.get_json()
    assert r.status_code in (200, 201), body
    assert len(body.get("skipped", [])) == 4, body


# ---------------------------------------------------------------- QA/QC resolve
def test_qaqc_resolve_rules(app, client, lifecycle_world):
    from extensions import db
    from models import Emission

    w = lifecycle_world
    rid = _seed(app, w["fids"]["in"], w["uids"]["superuser"], status="Pending", qa_flag="z-score 4.1")
    other = _seed(app, w["fids"]["in"], w["uids"]["user"], status="Pending", qa_flag="z-score 5.0")
    _as(client, w, "user")
    assert client.post(f"/api/qaqc/resolve/{rid}", json={"resolution": "Verified"}).status_code == 403
    assert client.post("/api/qaqc/bulk-resolve", json={"records": [{"id": rid, "scope": 1}], "resolution": "Verified"}).status_code == 403
    _as(client, w, "superuser")
    assert client.post(f"/api/qaqc/resolve/{rid}", json={"resolution": "Maybe"}).status_code == 400
    assert client.post(f"/api/qaqc/resolve/{rid}", json={"resolution": "Verified", "scope": 7}).status_code == 400
    r = client.post(f"/api/qaqc/resolve/{rid}", json={"resolution": "Verified", "scope": 1})
    assert r.status_code == 403 and "Maker-checker" in r.get_json()["error"]     # their own record
    assert client.post("/api/qaqc/bulk-resolve", json={"records": [{"id": other, "scope": 1}], "resolution": "Maybe"}).status_code == 400
    assert client.post("/api/qaqc/bulk-resolve", json={"records": [], "resolution": "Verified"}).status_code == 400
    r = client.post("/api/qaqc/bulk-resolve", json={"records": [{"id": other, "scope": 1}, {"id": "abc", "scope": 1}],
                                                    "resolution": "Verified"})
    assert r.status_code == 400                      # one malformed item refuses the whole batch
    with app.app_context():
        assert db.session.get(Emission, other).status == "Pending"
    r = client.post("/api/qaqc/bulk-resolve", json={"records": [{"id": other, "scope": 1}], "resolution": "Verified"})
    assert r.status_code == 200, r.get_json()
    with app.app_context():
        assert db.session.get(Emission, other).status == "Verified"
        assert db.session.get(Emission, rid).status == "Pending"


# ---------------------------------------------------------------- null factor source (stored by older imports)
def test_null_factor_source_calculates_as_tier1(app, client, lifecycle_world):
    from extensions import db
    from models import Emission

    w = lifecycle_world
    _as(client, w, "admin")
    base = {"year": 2025, "month": 11, "facility_id": w["fids"]["in"], "process_type": "combustion",
            "fuel": "Natural Gas", "amount": 100, "unit": "MMBtu"}
    tag = uuid.uuid4().hex[:4]
    assert client.post("/api/emissions/", json={**base, "factor_source": "default", "equipment_id": f"NF{tag}a"}).status_code == 201
    r = client.post("/api/emissions/", json={**base, "factor_source": None, "equipment_id": f"NF{tag}b"})
    assert r.status_code == 201, r.get_json()
    with app.app_context():
        a = Emission.query.filter_by(equipment_id=f"NF{tag}a").one()
        b = Emission.query.filter_by(equipment_id=f"NF{tag}b").one()
        assert b.co2e_total == pytest.approx(a.co2e_total, rel=1e-12)
        b.factor_source = None                      # as 169 of the dev database's records are stored
        db.session.commit()
        bid, a_total = b.id, a.co2e_total
    r = client.put(f"/api/emissions/{bid}", json={"amount": 200})
    assert r.status_code == 200, r.get_json()
    with app.app_context():
        assert db.session.get(Emission, bid).co2e_total == pytest.approx(2 * a_total, rel=1e-12)




@pytest.fixture(autouse=True)
def _restore_logging():
    yield
    logging.disable(logging.NOTSET)
