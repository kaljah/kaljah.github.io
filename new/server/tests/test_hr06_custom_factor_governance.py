"""HR-06 custom factor governance (HSE decision 2026-10-08).

- a source/method reference is required;
- a value outside the plausibility bounds (CO2 > 500, CH4 > 100, N2O > 10 kg/MMBtu) is refused unless a
  written justification is given, and the factor then waits for approval;
- an admin may approve a factor they created (decision D10, 2026-11-21); a superuser may not.
"""
import uuid

import pytest

from app import app as flask_app
from extensions import db
from models import CustomFactor, User

PW = "Hr06Governance1!"


def _user(role, tag):
    email = f"hr06_{tag}_{uuid.uuid4().hex[:6]}@example.com"
    with flask_app.app_context():
        u = User(email=email, fullName=f"HR06 {tag}", orgName="Audit", sector="Oil & Gas", role=role, location="Global")
        u.set_password(PW)
        db.session.add(u)
        db.session.commit()
    return email


def _login(client, email):
    assert client.post("/api/auth/login", json={"email": email, "password": PW}).status_code == 200


def _body(**kw):
    body = {"name": f"HR06 {uuid.uuid4().hex[:8]}", "co2_factor": 56.1, "ch4_factor": 0.001,
            "unit": "kg/MMBtu", "source": "API Compendium 2021 Table 5-1"}
    body.update(kw)
    return body


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_source_is_required(client):
    _login(client, _user("admin", "a"))
    r = client.post("/api/custom-factors", json=_body(source=""))
    assert r.status_code == 422 and "source" in r.get_json()["error"].lower()


@pytest.mark.parametrize("field,value", [("co2_factor", 501), ("ch4_factor", 100.5), ("n2o_factor", 10.1)])
def test_out_of_range_needs_justification(client, field, value):
    _login(client, _user("admin", "b"))
    r = client.post("/api/custom-factors", json=_body(**{field: value}))
    assert r.status_code == 422 and field in r.get_json()["error"]
    r = client.post("/api/custom-factors", json=_body(**{field: value, "justification": "short"}))
    assert r.status_code == 422


def test_justified_out_of_range_is_saved_pending_with_the_reason(client):
    _login(client, _user("admin", "c"))
    r = client.post("/api/custom-factors", json=_body(co2_factor=600, justification="Measured on site, high-carbon coke"))
    assert r.status_code == 201
    with flask_app.app_context():
        cf = db.session.get(CustomFactor, r.get_json()["id"])
        assert cf.status == "Pending"
        assert "high-carbon coke" in cf.description


def test_in_range_edit_to_out_of_range_needs_justification(client):
    _login(client, _user("admin", "d"))
    fid = client.post("/api/custom-factors", json=_body()).get_json()["id"]
    assert client.put(f"/api/custom-factors/{fid}", json={"co2_factor": 900}).status_code == 422
    ok = client.put(f"/api/custom-factors/{fid}", json={"co2_factor": 900, "justification": "Re-measured at the plant"})
    assert ok.status_code == 200


def test_admin_may_approve_own_factor_superuser_may_not(client):
    """GB RY2022 decision D10 (2026-11-21): an administrator accepts their own factor; a superuser's needs someone else."""
    creator = _user("admin", "e")
    _login(client, creator)
    fid = client.post("/api/custom-factors", json=_body()).get_json()["id"]
    with flask_app.app_context():
        assert db.session.get(CustomFactor, fid).status == "Pending"
    assert client.post(f"/api/custom-factors/{fid}/approve").status_code == 200
    with flask_app.app_context():
        from models import ActivityLog
        log = ActivityLog.query.filter_by(entity="CustomFactor", record_id=str(fid), action="APPROVE").one()
        assert "self-approval" in log.details
    su = _user("superuser", "f2")
    with flask_app.app_context():
        u = User.query.filter_by(email=su).one()
        u.location = "Field X"
        db.session.commit()
    _login(client, su)
    fid2 = client.post("/api/custom-factors", json=_body()).get_json()["id"]
    assert client.post(f"/api/custom-factors/{fid2}/approve").status_code == 403


def test_second_approver_can_be_switched_off(client, monkeypatch):
    monkeypatch.setenv("CUSTOM_FACTOR_SECOND_APPROVER", "false")
    _login(client, _user("admin", "g"))
    fid = client.post("/api/custom-factors", json=_body()).get_json()["id"]
    with flask_app.app_context():
        assert db.session.get(CustomFactor, fid).status == "Approved"


def test_import_skips_rows_without_source_or_justification(client):
    _login(client, _user("admin", "h"))
    rows = [
        {"name": f"HR06 imp {uuid.uuid4().hex[:6]}", "co2_factor": 50, "unit": "kg/m3", "source": "Lab"},
        {"name": f"HR06 imp {uuid.uuid4().hex[:6]}", "co2_factor": 50, "unit": "kg/m3"},
        # the bounds are per MMBtu: a per-volume factor is not compared (audit 2026-11 F-FAC-03)
        {"name": f"HR06 imp {uuid.uuid4().hex[:6]}", "co2_factor": 5000, "unit": "kg/MMBtu", "source": "Lab"},
    ]
    r = client.post("/api/custom-factors/import", json={"factors": rows})
    body = r.get_json()
    assert r.status_code == 200 and body["imported"] == 1 and len(body["skipped"]) == 2


def test_file_import_applies_governance(client, tmp_path):
    """GB RY2022 GB-016: the CSV / Excel import of custom factors goes through the same rules as the form."""
    import io
    import time
    _login(client, _user("admin", "i"))
    tok = client.get("/api/csrf-token").get_json()["csrf_token"]
    name_ok, name_nosrc = f"HR06 csv {uuid.uuid4().hex[:6]}", f"HR06 csv {uuid.uuid4().hex[:6]}"
    csv_text = "\n".join(["name,co2_factor,ch4_factor,n2o_factor,unit,source",
                          f"{name_ok},69.25,0.003,0.0006,kg/MMBtu,API Compendium 2021 Table 4-5",
                          f"{name_nosrc},69.25,0.003,0.0006,kg/MMBtu,", ""])
    r = client.post("/api/emissions/upload/start", data={"scope": "custom_factors", "decimal_mark": "point",
                    "file": (io.BytesIO(csv_text.encode()), "f.csv")}, content_type="multipart/form-data",
                    headers={"X-CSRFToken": tok})
    job = r.get_json()["job_id"]
    for _ in range(100):
        st = client.get(f"/api/emissions/upload/status/{job}").get_json()
        if st.get("status") in ("completed", "failed"):
            break
        time.sleep(0.1)
    with flask_app.app_context():
        ok = CustomFactor.query.filter_by(name=name_ok).one()
        assert ok.status == "Pending" and ok.approved_by is None
        assert CustomFactor.query.filter_by(name=name_nosrc).first() is None
    assert any("source" in (x.get("reason") or "").lower() for x in st.get("skipped_preview", []))
