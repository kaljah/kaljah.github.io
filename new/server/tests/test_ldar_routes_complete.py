"""routes/ldar.py: every endpoint, role, input rule and audit entry.

Found while testing: audit entries were added after the commit and discarded with the request (none was
ever stored), edits and deletes wrote none, an unreadable quantity / hours silently became 1 / 8,760 and
a text ppm or leaking-hours value was a 500.
"""
import json
import uuid

import pytest


@pytest.fixture
def lw(app):
    from extensions import db
    from models import Facility, User

    tag = uuid.uuid4().hex[:6]
    region = f"LdR{tag}"
    with app.app_context():
        fac = Facility(name=f"Ldar {tag}", region=region, code=f"LD{tag}", activity="EP", division="D", field="F")
        other = Facility(name=f"Ldar Other {tag}", region=f"LdO{tag}", code=f"LO{tag}", activity="EP", division="D", field="F")
        users = {}
        for role in ("admin", "superuser", "user", "auditor", "it_admin"):
            u = User(email=f"ld_{role}_{tag}@test.com", fullName=f"Ld {role}", orgName="T", sector="Energy", role=role,
                     location="Global" if role == "auditor" else ("Global Corporate Head Office" if role in ("admin", "it_admin") else region))
            u.set_password("LdarPass123!")
            users[role] = u
        db.session.add_all([fac, other, *users.values()])
        db.session.commit()
        return {"fid": fac.id, "other": other.id, "uids": {r: u.id for r, u in users.items()}}


def _as(client, lw, role):
    with client.session_transaction() as s:
        s["user_id"] = lw["uids"][role]


def _audit(app, entity, action=None):
    from models import ActivityLog

    with app.app_context():
        q = ActivityLog.query.filter_by(entity=entity)
        if action:
            q = q.filter_by(action=action)
        return q.order_by(ActivityLog.id).all()


def _component(client, lw, **kw):
    body = {"facility_id": lw["fid"], "equipment_type": "Wellhead", "component_type": "Valve", **kw}
    return client.post("/api/ldar/components", json=body)


def _survey(client, lw, **kw):
    return client.post("/api/ldar/surveys", json={"facility_id": lw["fid"], **kw})


# ---------------------------------------------------------------- input rules
@pytest.mark.parametrize("field,value", [
    ("quantity", "abc"), ("quantity", 1.5), ("quantity", -1), ("operating_hours", "x"), ("operating_hours", 9000),
    ("operating_hours", -1), ("factor_value", "ten"), ("factor_value", -0.1), ("quantity", True),
])
def test_component_numbers_are_strict(client, lw, field, value):
    _as(client, lw, "admin")
    res = _component(client, lw, **{field: value})
    assert res.status_code == 400 and res.get_json()["field"] == field, res.get_json()


def test_component_defaults_and_parsed_values(client, lw):
    _as(client, lw, "admin")
    c = _component(client, lw).get_json()["component"]
    assert (c["quantity"], c["operating_hours"], c["service_type"], c["methodology"], c["status"]) == (
        1, 8760.0, "Gas", "Component Average", "Active")
    c = _component(client, lw, quantity="12", operating_hours="744", factor_value="2.94e-06").get_json()["component"]
    assert (c["quantity"], c["operating_hours"], c["factor_value"]) == (12, 744.0, 2.94e-06)
    assert _component(client, lw, quantity=0).get_json()["component"]["quantity"] == 0


@pytest.mark.parametrize("body,field", [
    ({"leaking_hours": "abc"}, "leaking_hours"), ({"leaking_hours": 9000}, "leaking_hours"),
    ({"screening_value_ppm": "lots"}, "screening_value_ppm"), ({"screening_value_ppm": 2e6}, "screening_value_ppm"),
    ({"detection_threshold_ppm": -1}, "detection_threshold_ppm"), ({"measured_emission_rate": -0.5}, "measured_emission_rate"),
    ({"survey_date": "16/10/2026"}, "survey_date"), ({"repair_date": "yesterday"}, "repair_date"),
    ({"component_inventory_id": 999999999}, "component_inventory_id"), ({"component_inventory_id": "x"}, "component_inventory_id"),
])
def test_survey_inputs_are_strict(client, lw, body, field):
    _as(client, lw, "admin")
    res = _survey(client, lw, **body)
    assert res.status_code == 400 and res.get_json()["field"] == field, res.get_json()


def test_survey_defaults_and_component_link(client, lw):
    import datetime

    _as(client, lw, "user")
    s = _survey(client, lw).get_json()["survey"]
    assert (s["survey_method"], s["leak_status"], s["measurement_unit"], s["leaking_hours"], s["surveyor_name"]) == (
        "Method 21", "Non-leaking", "kg/hr", 8760.0, "Ld user")
    assert s["survey_date"] == datetime.date.today().isoformat()
    comp = _component(client, lw).get_json()["component"]["id"]
    s = _survey(client, lw, component_inventory_id=comp, screening_value_ppm="12000", survey_date="2026-03-01",
                measured_emission_rate="0.5", leaking_hours="100").get_json()["survey"]
    assert (s["component_inventory_id"], s["screening_value_ppm"], s["survey_date"], s["measured_emission_rate"],
            s["leaking_hours"]) == (comp, 12000.0, "2026-03-01", 0.5, 100.0)
    # a component of another facility cannot be linked
    _as(client, lw, "admin")
    other_comp = client.post("/api/ldar/components", json={"facility_id": lw["other"], "equipment_type": "E",
                                                           "component_type": "C"}).get_json()["component"]["id"]
    res = _survey(client, lw, component_inventory_id=other_comp)
    assert res.status_code == 400 and res.get_json()["field"] == "component_inventory_id"


@pytest.mark.parametrize("body,code", [({}, 400), ({"facility_id": "x"}, 400), ({"facility_id": 999999999}, 404)])
def test_create_needs_a_known_facility(client, lw, body, code):
    _as(client, lw, "admin")
    assert client.post("/api/ldar/components", json={"equipment_type": "E", "component_type": "C", **body}).status_code == code
    assert client.post("/api/ldar/surveys", json=body).status_code == code


def test_component_needs_equipment_and_component_type(client, lw):
    _as(client, lw, "admin")
    assert client.post("/api/ldar/components", json={"facility_id": lw["fid"], "equipment_type": " "}).status_code == 400


# ---------------------------------------------------------------- audit trail
def test_every_change_is_audited_with_the_change(app, client, lw):
    _as(client, lw, "superuser")
    cid = _component(client, lw, quantity=3).get_json()["component"]["id"]
    assert client.put(f"/api/ldar/components/{cid}", json={"quantity": 5, "status": "Leaking"}).status_code == 200
    sid = _survey(client, lw, leak_status="Leaking", screening_value_ppm=500, survey_date="2026-03-01").get_json()["survey"]["id"]
    assert client.patch(f"/api/ldar/surveys/{sid}", json={"leak_status": "Repaired", "repair_date": "2026-04-01"}).status_code == 200
    assert client.post("/api/ldar/components/bulk-update", json={"ids": [cid], "operating_hours": 100}).status_code == 200
    assert client.post("/api/ldar/surveys/bulk-update", json={"ids": [sid], "notes": "checked"}).status_code == 200
    cid2 = _component(client, lw).get_json()["component"]["id"]
    sid2 = _survey(client, lw).get_json()["survey"]["id"]
    assert client.delete(f"/api/ldar/components/{cid}").status_code == 200
    assert client.delete(f"/api/ldar/surveys/{sid}").status_code == 200
    assert client.post("/api/ldar/components/bulk-delete", json={"ids": [cid2]}).status_code == 200
    assert client.post("/api/ldar/surveys/bulk-delete", json={"ids": [sid2]}).status_code == 200

    comp_logs = {(a.action, a.entity_id) for a in _audit(app, "ComponentInventory")}
    survey_logs = {(a.action, a.entity_id) for a in _audit(app, "FugitiveSurvey")}
    assert {("CREATE", str(cid)), ("UPDATE", str(cid)), ("BULK_UPDATE", "bulk"), ("DELETE", str(cid)),
            ("CREATE", str(cid2)), ("BULK_DELETE", "bulk")} <= comp_logs
    assert {("CREATE", str(sid)), ("UPDATE", str(sid)), ("BULK_UPDATE", "bulk"), ("DELETE", str(sid)),
            ("CREATE", str(sid2)), ("BULK_DELETE", "bulk")} <= survey_logs
    upd = [a for a in _audit(app, "ComponentInventory", "UPDATE") if a.entity_id == str(cid)][-1]
    assert json.loads(upd.old_values)["quantity"] == 3 and json.loads(upd.new_values)["quantity"] == 5
    assert upd.facility_id == lw["fid"]
    dele = [a for a in _audit(app, "FugitiveSurvey", "DELETE") if a.entity_id == str(sid)][-1]
    assert json.loads(dele.old_values)["leak_status"] == "Repaired"


def test_failed_commit_answers_a_generic_500_and_stores_nothing(app, client, lw, monkeypatch):
    from extensions import db
    from models import ComponentInventory

    _as(client, lw, "admin")
    before = len(_audit(app, "ComponentInventory"))

    def boom():
        raise RuntimeError("secret connection string")

    monkeypatch.setattr(db.session, "commit", boom)
    res = _component(client, lw, component_type=f"Fail {uuid.uuid4().hex[:4]}")
    monkeypatch.undo()
    assert res.status_code == 500 and "secret" not in res.get_data(as_text=True)
    assert len(_audit(app, "ComponentInventory")) == before
    with app.app_context():
        assert ComponentInventory.query.filter(ComponentInventory.component_type.like("Fail %")).count() == 0


# ---------------------------------------------------------------- reading, filters, scope
def test_lists_filters_and_scope(client, lw):
    _as(client, lw, "admin")
    a = _component(client, lw, status="Active").get_json()["component"]["id"]
    b = _component(client, lw, status="Broken").get_json()["component"]["id"]
    out = client.post("/api/ldar/components", json={"facility_id": lw["other"], "equipment_type": "E",
                                                    "component_type": "C"}).get_json()["component"]["id"]
    _survey(client, lw, leak_status="Leaking")
    rows = client.get(f"/api/ldar/components?facility_id={lw['fid']}&status=Broken").get_json()["components"]
    assert [r["id"] for r in rows] == [b]
    assert client.get(f"/api/ldar/components?facilityId={lw['fid']}").get_json()["count"] >= 2
    assert all(s["leak_status"] == "Leaking"
               for s in client.get(f"/api/ldar/surveys?facility_id={lw['fid']}&leak_status=Leaking").get_json()["surveys"])
    for path in ("components", "surveys"):
        res = client.get(f"/api/ldar/{path}?facility_id=abc")
        assert res.status_code == 422 and res.get_json()["field"] == "facility_id"
    _as(client, lw, "user")   # scoped to the first facility's region
    ids = {r["id"] for r in client.get("/api/ldar/components").get_json()["components"]}
    assert {a, b} <= ids and out not in ids
    assert all(s["facility_id"] == lw["fid"] for s in client.get("/api/ldar/surveys").get_json()["surveys"])
    assert client.get(f"/api/ldar/components?facility_id={lw['other']}").status_code == 403
    assert client.get(f"/api/ldar/surveys?facility_id={lw['other']}").status_code == 403
    assert client.get(f"/api/ldar/components/{out}").status_code == 403
    assert client.get(f"/api/ldar/components/{a}").get_json()["component"]["id"] == a
    assert client.get("/api/ldar/components/999999999").status_code == 404
    assert client.get("/api/ldar/surveys/999999999").status_code == 404
    assert client.post("/api/ldar/components", json={"facility_id": lw["other"], "equipment_type": "E",
                                                     "component_type": "C"}).status_code == 403
    assert client.put(f"/api/ldar/components/{out}", json={"status": "x"}).status_code == 403


def test_role_rules(client, lw):
    _as(client, lw, "admin")
    cid = _component(client, lw).get_json()["component"]["id"]
    sid = _survey(client, lw).get_json()["survey"]["id"]
    _as(client, lw, "it_admin")
    for path in ("/api/ldar/components", "/api/ldar/surveys", f"/api/ldar/components/{cid}", f"/api/ldar/surveys/{sid}"):
        assert client.get(path).status_code == 403, path
    for role in ("it_admin", "auditor"):
        _as(client, lw, role)
        assert _component(client, lw).status_code == 403
        assert _survey(client, lw).status_code == 403
        assert client.put(f"/api/ldar/components/{cid}", json={}).status_code == 403
        assert client.patch(f"/api/ldar/surveys/{sid}", json={}).status_code == 403
        assert client.post("/api/ldar/components/bulk-update", json={"ids": [cid]}).status_code == 403
        assert client.post("/api/ldar/surveys/bulk-update", json={"ids": [sid]}).status_code == 403
    _as(client, lw, "auditor")
    assert client.get(f"/api/ldar/components/{cid}").status_code == 200       # read-only access
    for role in ("user", "auditor"):
        _as(client, lw, role)
        assert client.delete(f"/api/ldar/components/{cid}").status_code == 403
        assert client.delete(f"/api/ldar/surveys/{sid}").status_code == 403
        assert client.post("/api/ldar/components/bulk-delete", json={"ids": [cid]}).status_code == 403
        assert client.post("/api/ldar/surveys/bulk-delete", json={"ids": [sid]}).status_code == 403


# ---------------------------------------------------------------- edits
def test_component_update_rules_and_notification(app, client, lw):
    from models import Notification

    _as(client, lw, "user")
    cid = _component(client, lw).get_json()["component"]["id"]
    for body, field in (({"quantity": ""}, "quantity"), ({"quantity": "x"}, "quantity"),
                        ({"operating_hours": None}, "operating_hours"), ({"operating_hours": 1e5}, "operating_hours"),
                        ({"factor_value": "bad"}, "factor_value")):
        res = client.put(f"/api/ldar/components/{cid}", json=body)
        assert res.status_code == 400 and res.get_json()["field"] == field, body
    res = client.put(f"/api/ldar/components/{cid}", json={"status": "Needs Repair", "factor_value": "1e-6",
                                                          "description": "seal worn"})
    c = res.get_json()["component"]
    assert (c["status"], c["factor_value"], c["description"]) == ("Needs Repair", 1e-6, "seal worn")
    with app.app_context():
        assert Notification.query.filter(Notification.metadata_json.like(f'%"component_id": {cid}%')).count() == 1
    assert client.put("/api/ldar/components/999999999", json={}).status_code == 404


def test_survey_update_rules_and_notification(app, client, lw):
    from models import Notification

    _as(client, lw, "user")
    sid = _survey(client, lw).get_json()["survey"]["id"]
    for body, field in (({"leaking_hours": ""}, "leaking_hours"), ({"leaking_hours": "many"}, "leaking_hours"),
                        ({"survey_date": ""}, "survey_date"), ({"survey_date": "2026-13-01"}, "survey_date"),
                        ({"screening_value_ppm": "high"}, "screening_value_ppm")):
        res = client.patch(f"/api/ldar/surveys/{sid}", json=body)
        assert res.status_code == 400 and res.get_json()["field"] == field, body
    s = client.put(f"/api/ldar/surveys/{sid}", json={"leak_status": "Leaking", "leaking_hours": "200",
                                                     "repair_date": ""}).get_json()["survey"]
    assert (s["leak_status"], s["leaking_hours"], s["repair_date"]) == ("Leaking", 200.0, None)
    with app.app_context():
        assert Notification.query.filter(Notification.metadata_json.like(f'%"survey_id": {sid}%')).count() == 1
    assert client.patch("/api/ldar/surveys/999999999", json={}).status_code == 404


# ---------------------------------------------------------------- bulk requests
@pytest.mark.parametrize("path", ["components/bulk-update", "components/bulk-delete", "surveys/bulk-update",
                                  "surveys/bulk-delete"])
def test_bulk_requests_need_ids(client, lw, path):
    _as(client, lw, "admin")
    assert client.post(f"/api/ldar/{path}", json={}).status_code == 400
    assert client.post(f"/api/ldar/{path}", json={"ids": "1,2"}).status_code == 400
    assert client.post(f"/api/ldar/{path}", json={"ids": ["a"]}).status_code == 400
    assert client.post(f"/api/ldar/{path}", json={"ids": [999999999]}).status_code == 404


def test_bulk_updates(app, client, lw):
    from extensions import db
    from models import ComponentInventory, FugitiveSurvey

    _as(client, lw, "admin")
    cids = [_component(client, lw).get_json()["component"]["id"] for _ in range(2)]
    res = client.post("/api/ldar/components/bulk-update", json={"ids": cids, "operating_hours": "x"})
    assert res.status_code == 400 and res.get_json()["field"] == "operating_hours"
    res = client.post("/api/ldar/components/bulk-update", json={"ids": cids, "status": " Faulty ", "service_type": "Light Liquid",
                                                                "equipment_type": "Pump", "operating_hours": "4380"})
    assert res.get_json()["updated_ids"] == cids
    with app.app_context():
        for c in db.session.query(ComponentInventory).filter(ComponentInventory.id.in_(cids)):
            assert (c.status, c.service_type, c.equipment_type, c.operating_hours) == ("Faulty", "Light Liquid", "Pump", 4380.0)
    sids = [_survey(client, lw, notes="first", survey_date="2026-03-01").get_json()["survey"]["id"] for _ in range(2)]
    res = client.post("/api/ldar/surveys/bulk-update", json={"ids": sids, "screening_value_ppm": "much"})
    assert res.status_code == 400 and res.get_json()["field"] == "screening_value_ppm"
    res = client.post("/api/ldar/surveys/bulk-update", json={"ids": sids, "repair_date": "2026-13-40"})
    assert res.status_code == 400 and res.get_json()["field"] == "repair_date"
    assert client.post("/api/ldar/surveys/bulk-update", json={
        "ids": sids, "leak_status": "Leaking", "repair_date": "2026-05-02", "screening_value_ppm": 50,
        "notes": "rechecked", "survey_method": "OGI"}).status_code == 200
    assert client.post("/api/ldar/surveys/bulk-update", json={"ids": sids, "repair_date": ""}).status_code == 200
    with app.app_context():
        for s in db.session.query(FugitiveSurvey).filter(FugitiveSurvey.id.in_(sids)):
            assert (s.leak_status, s.repair_date, s.screening_value_ppm, s.notes, s.survey_method) == (
                "Leaking", None, 50.0, "first | rechecked", "OGI")


def test_broken_status_rules_and_no_repeat_notification(app, client, lw):
    from models import Notification
    from routes.ldar import is_broken_status

    assert not is_broken_status(None) and not is_broken_status("") and is_broken_status(" NEEDS REPAIR ")
    _as(client, lw, "admin")
    cid = _component(client, lw, status="Broken").get_json()["component"]["id"]
    assert client.put(f"/api/ldar/components/{cid}", json={"status": "Leaking"}).status_code == 200
    with app.app_context():   # created broken: one alert; still broken after the edit: no second one
        assert Notification.query.filter(Notification.metadata_json.like(f'%"component_id": {cid}%')).count() == 1
    res = client.post("/api/ldar/components/bulk-update", json={"ids": [cid], "description": "x"})
    assert res.status_code == 200
    assert client.delete("/api/ldar/components/999999999").status_code == 404
    assert client.delete("/api/ldar/surveys/999999999").status_code == 404


@pytest.mark.parametrize("method,path,body", [
    ("put", "components/{cid}", {"status": "x"}), ("delete", "components/{cid}", None),
    ("post", "components/bulk-update", {"ids": ["{cid}"], "status": "x"}),
    ("post", "components/bulk-delete", {"ids": ["{cid}"]}),
    ("post", "surveys", {"facility_id": "{fid}"}), ("patch", "surveys/{sid}", {"notes": "x"}),
    ("delete", "surveys/{sid}", None), ("post", "surveys/bulk-update", {"ids": ["{sid}"], "notes": "x"}),
    ("post", "surveys/bulk-delete", {"ids": ["{sid}"]}),
])
def test_every_write_fails_closed(app, client, lw, monkeypatch, method, path, body):
    from extensions import db

    _as(client, lw, "admin")
    ids = {"cid": _component(client, lw).get_json()["component"]["id"],
           "sid": _survey(client, lw).get_json()["survey"]["id"], "fid": lw["fid"]}
    fill = lambda v: int(v.format(**ids)) if isinstance(v, str) and v.startswith("{") else v
    if body:
        body = {k: ([fill(x) for x in v] if isinstance(v, list) else fill(v)) for k, v in body.items()}
    logs = len(_audit(app, "ComponentInventory")) + len(_audit(app, "FugitiveSurvey"))

    def boom():
        raise RuntimeError("secret detail")

    monkeypatch.setattr(db.session, "commit", boom)
    res = getattr(client, method)(f"/api/ldar/{path.format(**ids)}", **({"json": body} if body is not None else {}))
    monkeypatch.undo()
    assert res.status_code == 500 and "secret" not in res.get_data(as_text=True)
    assert len(_audit(app, "ComponentInventory")) + len(_audit(app, "FugitiveSurvey")) == logs


def test_repair_never_precedes_the_survey(client, lw):
    _as(client, lw, "admin")
    bad = _survey(client, lw, survey_date="2026-03-10", repair_date="2026-03-01", leak_status="Repaired")
    assert bad.status_code == 400 and bad.get_json()["field"] == "repair_date"
    sid = _survey(client, lw, survey_date="2026-03-10", leak_status="Leaking").get_json()["survey"]["id"]
    res = client.put(f"/api/ldar/surveys/{sid}", json={"repair_date": "2026-03-01"})              # one date edited
    assert res.status_code == 400 and res.get_json()["field"] == "repair_date"
    res = client.post("/api/ldar/surveys/bulk-update", json={"ids": [sid], "repair_date": "2026-03-01"})
    assert res.status_code == 400 and res.get_json()["field"] == "repair_date"
    assert client.put(f"/api/ldar/surveys/{sid}", json={"repair_date": "2026-03-12"}).status_code == 200
    assert client.post("/api/ldar/surveys/bulk-update", json={"ids": [sid], "leak_status": "Repaired"}).status_code == 200


def test_list_filter_takes_several_facilities(client, lw):
    _as(client, lw, "admin")
    a = _component(client, lw).get_json()["component"]["id"]
    b = _component(client, lw, facility_id=lw["other"]).get_json()["component"]["id"]
    rows = client.get(f"/api/ldar/components?facility_id={lw['fid']},{lw['other']}").get_json()["components"]
    assert {a, b} <= {r["id"] for r in rows}
    assert client.get(f"/api/ldar/components?facility_id={lw['fid']},x").status_code == 422
    assert client.get("/api/ldar/components?facility_id=all").status_code == 200
