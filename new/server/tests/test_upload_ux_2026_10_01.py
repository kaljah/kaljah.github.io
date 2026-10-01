"""Bulk-import usability (2026-10-01): grouped, actionable skip reasons; the "Check file" step (dry run that
saves nothing); upload limits for the wizard."""
import io
import os

import pytest

from app import app as flask_app
from extensions import db
from models import Emission, Facility, User
from services.import_feedback import classify, group_skips

FAC = "UX Check Facility"


@pytest.fixture(scope="module")
def client():
    with flask_app.app_context():
        u = User.query.filter_by(email="ux_check@ghg.com").first()
        if not u:
            u = User(email="ux_check@ghg.com", fullName="UX", orgName="Audit", sector="Oil & Gas", role="admin",
                     location="Global")
            u.set_password("UxCheck2026!")
            db.session.add(u)
        if not Facility.query.filter_by(name=FAC).first():
            db.session.add(Facility(name=FAC, location="Illizi", country="Algeria", region="Illizi"))
        db.session.commit()
    from extensions import limiter

    c = flask_app.test_client()
    prev = limiter.enabled
    limiter.enabled = False  # module fixture: runs before the per-test limiter switch-off in conftest
    try:
        assert c.post("/api/auth/login", json={"email": "ux_check@ghg.com", "password": "UxCheck2026!"}).status_code == 200
    finally:
        limiter.enabled = prev
    return c


def _csv(rows):
    header = "date,facility_name,process_type,fuel,quantity,unit,factor_type,equipment_id"
    return ("\n".join([header] + rows)).encode()


def test_reasons_are_grouped_with_column_and_fix():
    skipped = [
        {"row": 2, "reason": "'scf' is a gas volume but this fuel's heating value is per gal of liquid"},
        {"row": 3, "reason": "'mmscf' is a gas volume but this fuel's heating value is per gal of liquid"},
        {"row": 4, "reason": "Unknown process type 'teleportation_9'. Use a process key such as combustion"},
        {"row": 5, "reason": "'year' must be between 1990 and 2100"},
        {"row": 6, "reason": "Missing required field: CH4 content of the flowback gas (mol %)"},
    ]
    groups = group_skips(skipped)
    top = groups[0]
    assert top["title"] == "Gas volume unit used with a liquid fuel" and top["count"] == 2
    assert top["column"] == "unit" and top["fix"] and top["rows"] == [2, 3]
    titles = {g["title"] for g in groups}
    assert "Process type not recognised" in titles and "Date missing or out of range" in titles
    assert classify("Missing required field: CH4 content of the flowback gas (mol %)")[1].startswith("Required input missing")


def test_unknown_reason_falls_back_to_its_normalised_text():
    key, title, column, fix = classify("Something new happened on 'x' at 42")
    assert title == "Something new happened on '…' at N" and column is None and fix is None


def test_check_file_saves_nothing_and_previews_the_whole_file(client):
    rows = [f"2024-0{(i % 9) + 1},{FAC},combustion,Natural Gas,{100 + i},MMBtu,default,UXC-{i}" for i in range(40)]
    rows += [f"2024-01,{FAC},combustion,Natural Gas,10,scf_bad,default,UXB-{i}" for i in range(10)]   # bad unit
    rows += [f"2024-01,Nowhere Plant,combustion,Natural Gas,10,MMBtu,default,UXN-{i}" for i in range(5)]
    rows += [f"2031-13,{FAC},teleport,Natural Gas,10,MMBtu,default,UXD-{i}" for i in range(5)]
    with flask_app.app_context():
        before = Emission.query.count()
    r = client.post("/api/emissions/upload/check", content_type="multipart/form-data",
                    data={"file": (io.BytesIO(_csv(rows)), "check.csv"), "global_factor_type": "auto", "scope": "1",
                          "sample_rows": "100"})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    p = body["preview"]
    assert p["rows"] == 60 and p["checked"] == 60 and not p["is_estimate"]
    assert p["checked_ok"] == 40 and p["checked_skipped"] == 20
    assert p["period"]["from"] == "2024-01" and p["period"]["to"] == "2024-09" and p["period"]["unreadable_rows"] == 5
    assert p["unknown_facility_rows"] == 5 and any(f["name"] == "Nowhere Plant" and not f["known"] for f in p["facilities"])
    assert p["unknown_process_rows"] == 5
    assert p["columns"]["total"] == 8
    assert sum(g["count"] for g in body["skipped_groups"]) == 20
    with flask_app.app_context():
        assert Emission.query.count() == before        # nothing saved


def test_check_sample_is_spread_over_the_file(client):
    # the bad rows are all at the end: a first-rows sample would miss them
    rows = [f"2024-01,{FAC},combustion,Natural Gas,{100 + i},MMBtu,default,UXS-{i}" for i in range(300)]
    rows += [f"2024-01,{FAC},combustion,Natural Gas,10,bogus,default,UXT-{i}" for i in range(300)]
    r = client.post("/api/emissions/upload/check", content_type="multipart/form-data",
                    data={"file": (io.BytesIO(_csv(rows)), "check.csv"), "global_factor_type": "auto", "scope": "1",
                          "sample_rows": "100"})
    p = r.get_json()["preview"]
    assert p["is_estimate"] and p["checked"] == 100
    assert 250 <= p["estimated_skipped"] <= 350          # half the file, not 0


def test_upload_limits(client):
    r = client.get("/api/emissions/upload/limits")
    assert r.status_code == 200 and r.get_json()["max_bytes"] == flask_app.config["MAX_CONTENT_LENGTH"]


def test_job_status_carries_grouped_reasons(client):
    from background_processor import get_job_status, start_background_upload  # noqa: F401
    import time

    rows = [f"2024-02,{FAC},combustion,Natural Gas,10,bogus,default,UXJ-{i}-{os.urandom(2).hex()}" for i in range(7)]
    r = client.post("/api/emissions/upload/start", content_type="multipart/form-data",
                    data={"file": (io.BytesIO(_csv(rows)), "job.csv"), "global_factor_type": "auto", "scope": "1"})
    job = r.get_json()["job_id"]
    for _ in range(100):
        st = client.get(f"/api/emissions/upload/status/{job}").get_json()
        if st["status"] in ("completed", "error"):
            break
        time.sleep(0.1)
    assert st["status"] == "completed"
    assert st["skipped_groups"][0]["count"] == 7 and st["skipped_groups"][0]["title"] == "Unit not recognised"
    assert st["started_at"]


def test_check_reports_scope2_rows_separately(client):
    rows = [f"2024-01,{FAC},combustion,Natural Gas,{100 + i},MMBtu,default,UXP-{i}" for i in range(5)]
    rows += [f"2024-01,{FAC},purchased_electricity,Grid,1000,kWh,default,UXE-{i}" for i in range(3)]
    rows += [f"2024-01,{FAC},teleport,Natural Gas,10,MMBtu,default,UXQ-{i}" for i in range(2)]
    r = client.post("/api/emissions/upload/check", content_type="multipart/form-data",
                    data={"file": (io.BytesIO(_csv(rows)), "check.csv"), "global_factor_type": "auto", "scope": "1"})
    p = r.get_json()["preview"]
    assert p["scope2_rows"] == 3 and p["unknown_process_rows"] == 2
    groups = {g["title"]: g["count"] for g in r.get_json()["skipped_groups"]}
    assert groups.get("Scope 2 row in a Scope 1 file") == 3
