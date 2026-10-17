"""scripts/recalculate_emissions.py: rebuilding stored Scope 1 records with the current engine.

The tool must leave every record the current application saves unchanged (otherwise --apply --all
would send good records back to review with different numbers), and must report, not write, the
records it cannot rebuild. Records come from every entry path: the file import (every catalog fuel
in every offered unit, every template example in every offered unit) and the single POST with the
form's calc_inputs (the API Compendium exhibit payloads).
"""
import csv
import io
import json
import logging
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
import recalculate_emissions as tool  # noqa: E402

GASES = ("co2_emissions", "ch4_emissions", "n2o_emissions", "co2e_total")


def _gwp():
    from calculations.constants import get_active_gwp

    return get_active_gwp()


@pytest.fixture(scope="module")
def rworld():
    from app import app as flask_app
    from extensions import db
    from models import CustomFactor, Facility, User

    tag = uuid.uuid4().hex[:6]
    with flask_app.app_context():
        f = Facility(name=f"Recalc {tag}", region=f"RcR{tag}", activity="EP", division="D", field="F",
                     segment="Upstream", code=f"RC{tag}")
        admin = User(email=f"rc_admin_{tag}@test.com", fullName="Rc Admin", orgName="T", sector="Energy",
                     role="admin", location="Global Corporate Head Office")
        user = User(email=f"rc_user_{tag}@test.com", fullName="Rc User", orgName="T", sector="Energy",
                    role="user", location=f"RcR{tag}")
        for u in (admin, user):
            u.set_password("RecalcPass123!")
        db.session.add_all([f, admin, user])
        db.session.flush()
        cf = CustomFactor(name=f"Rc Site Fuel {tag}", co2_factor=70.0, ch4_factor=0.01, n2o_factor=0.001,
                          unit="kg/MMBtu", source="lab", usage="combustion", status="Approved", created_by=admin.id)
        db.session.add(cf)
        db.session.commit()
        return {"fid": f.id, "fname": f.name, "admin": admin.id, "admin_email": admin.email,
                "user_email": user.email, "cfid": cf.id, "cfname": cf.name, "tag": tag}


def _login(client, uid):
    with client.session_transaction() as s:
        s["user_id"] = uid


def _upload(client, rows):
    keys = sorted({k for r in rows for k in r})
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(keys)
    for r in rows:
        w.writerow([r.get(k, "") for k in keys])
    res = client.post("/api/emissions/upload/start",
                      data={"scope": "1", "global_factor_type": "auto", "decimal_mark": "point",
                            "file": (io.BytesIO(buf.getvalue().encode()), "rc.csv")},
                      content_type="multipart/form-data")
    assert res.status_code == 200, res.get_json()
    job = res.get_json()["job_id"]
    for _ in range(6000):
        st = client.get(f"/api/emissions/upload/status/{job}").get_json()
        if st["status"] != "processing":
            return st
        time.sleep(0.05)
    raise AssertionError("upload did not finish")


def _recalc_all(app, fid):
    """{record id: (label, stored, recalculated or the error, notes)} for every record of the facility."""
    from models import Emission

    out = {}
    with app.app_context():
        for rec in Emission.query.filter_by(facility_id=fid).order_by(Emission.id).all():
            stored = {g: getattr(rec, g) for g in GASES}
            label = (rec.equipment_id, rec.process_type, rec.fuel_type, rec.unit, rec.factor_source)
            try:
                new, notes = tool.recalculate(rec, _gwp())
                out[rec.id] = (label, stored, new, notes)
            except Exception as err:
                out[rec.id] = (label, stored, err, [])
    return out


def _differences(results):
    bad = []
    for rid, (label, stored, new, notes) in results.items():
        if isinstance(new, Exception):
            bad.append(f"{rid} {label}: cannot recalculate: {getattr(new, 'message', None) or new}")
            continue
        for g in GASES:
            a, b = float(stored[g] or 0), float(new[g] or 0)
            if abs(a - b) > 1e-9 * max(abs(a), abs(b), 1e-12):
                bad.append(f"{rid} {label}: {g} stored {a!r} recalculated {b!r} {notes}")
        if notes:
            bad.append(f"{rid} {label}: notes on a fresh record: {notes}")
    return bad


# ---------------------------------------------------------------- idempotence on every entry path
def test_file_import_records_recalculate_unchanged(app, client, rworld):
    from services import scope1_template as T

    logging.disable(logging.CRITICAL)
    try:
        _login(client, rworld["admin"])
        rows = []
        for proc, units in T.PROCESS_UNITS.items():
            for unit in units:
                for fuel in T.fuels_by_process().get(proc, []):
                    rows.append(dict(date="2025-02", facility_name=rworld["fname"], process_type=proc, fuel=fuel,
                                     quantity="10", unit=unit, equipment_id=f"F{len(rows):05d}", tier="1",
                                     operating_hours="744", activity_days="28"))
        for proc, tier, cells in T.examples(rworld["fname"]):
            for unit in T.PROCESS_UNITS[proc]:
                row = dict(cells, date="2025-02", unit=unit, equipment_id=f"E{len(rows):05d}", tier=tier)
                for col in ("tank_unit", "agr_unit"):
                    if col in row:
                        row[col] = unit
                rows.append(row)
        st = _upload(client, rows)
        assert st["status"] == "completed", st
    finally:
        logging.disable(logging.NOTSET)
    results = _recalc_all(app, rworld["fid"])
    assert len(results) > 300, len(results)
    bad = _differences(results)
    assert not bad, f"{len(bad)} of {len(results)} records change on recalculation:\n" + "\n".join(bad[:40])


def test_single_post_records_recalculate_unchanged(app, client, rworld):
    from models import Emission
    from tests.test_api_compendium_exhibits import CASES

    _login(client, rworld["admin"])
    eqs = []
    for i, param in enumerate(CASES):
        body = json.loads(json.dumps(param.values[0]))
        body.update(year=2024, month=(i % 12) + 1, facility_id=rworld["fid"], equipment_id=f"PX{i:03d}")
        res = client.post("/api/emissions/", json=body)
        assert res.status_code in (200, 201), (param.id, res.get_json())
        eqs.append(body["equipment_id"])
    # Tier 2 with a saved custom factor and with a site HHV; Tier 3 entered factors
    for eq, body in (
        ("PT2CF", {"process_type": "combustion", "fuel": rworld["cfname"], "amount": 500, "unit": "MMBtu",
                   "factor_source": "custom", "custom_factor_id": rworld["cfid"]}),
        ("PT2HHV", {"process_type": "combustion", "fuel": "Natural Gas", "amount": 50000, "unit": "scf",
                    "factor_source": "custom", "hhv": 1050, "hhv_unit": "Btu/scf"}),
        ("PT3SF", {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1000, "unit": "m3",
                   "factor_source": "specific", "hhv": 1020, "combustion_efficiency": 99.5,
                   "specific_factors": {"co2": 1.9, "co2Unit": "kg/m3", "ch4": 0.01, "ch4Unit": "kg/m3"}}),
    ):
        res = client.post("/api/emissions/", json={**body, "year": 2024, "month": 6, "facility_id": rworld["fid"],
                                                    "equipment_id": eq})
        assert res.status_code in (200, 201), (eq, res.get_json())
        eqs.append(eq)
    with app.app_context():
        ids = {e.id for e in Emission.query.filter(Emission.facility_id == rworld["fid"],
                                                   Emission.equipment_id.in_(eqs)).all()}
    assert len(ids) == len(eqs)
    results = {k: v for k, v in _recalc_all(app, rworld["fid"]).items() if k in ids}
    bad = _differences(results)
    assert not bad, "\n".join(bad)


# ---------------------------------------------------------------- the command line
def _record(app, rworld, **kw):
    from extensions import db
    from models import Emission

    payload = kw.pop("payload", None) or {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1000,
                                          "unit": "MMBtu", "factor_source": "default"}
    fields = dict(facility_id=rworld["fid"], year=2023, month=3, process_type="combustion", fuel_type="Natural Gas",
                  quantity=1000, unit="MMBtu", factor_source="default", co2e_total=53.1, co2_emissions=53.06,
                  status="Verified", gwp_version="AR5", source_payload=json.dumps(payload),
                  equipment_id=f"CLI{uuid.uuid4().hex[:6]}")
    fields.update(kw)
    with app.app_context():
        rec = Emission(**fields)
        db.session.add(rec)
        db.session.commit()
        return rec.id


def _get(app, rid):
    from extensions import db
    from models import Emission

    with app.app_context():
        db.session.expire_all()
        return db.session.get(Emission, rid)


def _set(app, rid, **values):
    from extensions import db
    from models import Emission

    with app.app_context():
        rec = db.session.get(Emission, rid)
        for k, v in values.items():
            setattr(rec, k, v)
        db.session.commit()


def _exact(app, rid):
    """Store what the tool computes, so the record is current."""
    new = tool.recalculate(_get(app, rid), _gwp())[0]
    _set(app, rid, **{g: new[g] for g in GASES})
    return new


def test_report_only_and_csv(app, rworld, capsys, tmp_path):
    rid = _record(app, rworld)
    _exact(app, rid)
    out_csv = tmp_path / "r.csv"
    tool.main(["--ids", str(rid), "--csv", str(out_csv)])
    text = capsys.readouterr().out
    assert "1 records: 0 change, 1 unchanged, 0 cannot be recalculated (report only; nothing written)" in text
    rows = list(csv.DictReader(out_csv.open(encoding="utf-8")))
    assert [r["result"] for r in rows] == ["unchanged"]
    assert list(rows[0]) == ["id", "period", "process", "fuel", "status", "old_co2e", "new_co2e", "change_pct",
                             "result", "notes"]
    assert rows[0]["period"] == "2023-03"


def test_report_shows_the_change_without_writing(app, rworld, capsys):
    rid = _record(app, rworld, co2e_total=1.0)
    tool.main(["--ids", str(rid)])
    out = capsys.readouterr().out
    assert " changes" in out and "%" in out
    assert _get(app, rid).co2e_total == 1.0 and _get(app, rid).status == "Verified"


def test_tolerance_decides_what_changes(app, rworld, capsys):
    rid = _record(app, rworld)
    new = _exact(app, rid)
    _set(app, rid, co2e_total=new["co2e_total"] * (1 + 1e-4))
    tool.main(["--ids", str(rid)])
    assert "1 change" in capsys.readouterr().out
    tool.main(["--ids", str(rid), "--tolerance", "1e-3"])
    assert "1 unchanged" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [["--apply"], ["--apply", "--user", "x@y.z"], ["--apply", "--ids", "1"],
                                  ["--apply", "--all"]])
def test_apply_needs_user_and_selection(argv):
    with pytest.raises(SystemExit) as e:
        tool.main(argv)
    assert e.value.code == 2


def test_apply_refuses_non_admin_and_unknown_accounts(app, rworld):
    rid = _record(app, rworld, co2e_total=1.0)
    for email in (rworld["user_email"], "nobody-here@example.com"):
        with pytest.raises(SystemExit) as e:
            tool.main(["--apply", "--user", email, "--ids", str(rid)])
        assert e.value.code == 2
    assert _get(app, rid).co2e_total == 1.0


def test_apply_changes_only_records_that_differ(app, rworld, capsys):
    from models import ActivityLog

    stale = _record(app, rworld, co2e_total=1.0, co2_emissions=1.0)
    fresh = _record(app, rworld)
    exact = _exact(app, fresh)
    tool.main(["--apply", "--user", rworld["admin_email"].upper(), "--ids", f"{stale},{fresh}"])
    assert "recalculated (Pending)" in capsys.readouterr().out
    s, f = _get(app, stale), _get(app, fresh)
    assert s.status == "Pending" and s.approved_by is None and s.updated_by == rworld["admin"]
    assert s.co2e_total == pytest.approx(exact["co2e_total"])
    assert f.status == "Verified" and f.co2e_total == exact["co2e_total"]
    with app.app_context():
        logs = ActivityLog.query.filter_by(action="RECALCULATE", record_id=str(stale)).all()
        assert len(logs) == 1 and logs[0].user_id == rworld["admin"]
        assert ActivityLog.query.filter_by(action="RECALCULATE", record_id=str(fresh)).count() == 0


def test_records_that_cannot_be_rebuilt_are_reported_not_written(app, rworld, capsys):
    wrong_dimension = _record(app, rworld, unit="gal", co2e_total=7.0,
                              payload={"process_type": "combustion", "fuel": "Natural Gas", "amount": 1000,
                                       "unit": "gal", "factor_source": "default"})
    unknown = _record(app, rworld, process_type="no_such_process", fuel_type="Nothing", co2e_total=8.0,
                      source_payload="{not json")
    implausible = _record(app, rworld, quantity=1e15, co2e_total=9.0,
                          payload={"process_type": "combustion", "fuel": "Natural Gas", "amount": 1e15,
                                   "unit": "MMBtu", "factor_source": "default"})
    tool.main(["--apply", "--user", rworld["admin_email"], "--ids", f"{wrong_dimension},{unknown},{implausible}"])
    out = capsys.readouterr().out
    assert out.count("cannot recalculate") == 3, out
    assert "3 cannot be recalculated" in out
    for rid, v in ((wrong_dimension, 7.0), (unknown, 8.0), (implausible, 9.0)):
        rec = _get(app, rid)
        assert rec.co2e_total == v and rec.status == "Verified"


def test_entered_activity_from_calc_inputs_is_used(app, rworld):
    """The record holds the activity converted (m3 -> scf); the tool rebuilds from what was entered."""
    payload = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1000, "unit": "m3",
               "factor_source": "default", "calc_inputs": {"combustion": {"amount": 1000, "unit": "m3"}}}
    rid = _record(app, rworld, quantity=35314.67, unit="scf", payload=payload)
    new, _ = tool.recalculate(_get(app, rid), _gwp())
    assert new["co2_emissions"] == pytest.approx(1000 * 35.3147 * 1020 / 1e6 * 53.06 / 1000, rel=1e-3)


def test_old_bulk_defaults_and_tier_column_are_reported(app, rworld):
    payload = {"process_type": "combustion", "fuel": "Natural Gas", "amount": 1000, "unit": "MMBtu",
               "factor_source": "default", "ch4_content": 85.0, "co2_content": 2.0}
    rid = _record(app, rworld, factor_source="liquids", payload=payload)
    new, notes = tool.recalculate(_get(app, rid), _gwp())
    assert "removed the bulk-import defaults CH4 85 % / CO2 2 %" in notes
    assert "tier column 'liquids' -> 'default'" in notes
    assert new["factor_source"] == "default"
    assert "ch4_content" not in json.loads(new["source_payload"])


def test_tier_column_fix_counts_as_a_change_even_with_equal_totals(app, rworld, capsys):
    rid = _record(app, rworld, factor_source="gases")
    new = tool.recalculate(_get(app, rid), _gwp())[0]
    _set(app, rid, **{g: new[g] for g in GASES})
    tool.main(["--ids", str(rid)])
    assert "1 change" in capsys.readouterr().out


def test_archived_custom_factor_still_rebuilds_its_records(app, rworld):
    from extensions import db
    from models import CustomFactor

    with app.app_context():
        cf = CustomFactor(name=f"Rc Archived {uuid.uuid4().hex[:4]}", co2_factor=80.0, ch4_factor=0.0, n2o_factor=0.0,
                          unit="kg/MMBtu", source="lab", usage="combustion", status="Approved",
                          created_by=rworld["admin"])
        db.session.add(cf)
        db.session.commit()
        cfid, name = cf.id, cf.name
    payload = {"process_type": "combustion", "fuel": name, "amount": 100, "unit": "MMBtu", "factor_source": "custom",
               "custom_factor_id": cfid}
    rid = _record(app, rworld, fuel_type=name, factor_source="custom", custom_factor_id=cfid, payload=payload)
    with app.app_context():
        db.session.get(CustomFactor, cfid).status = "Archived"
        db.session.commit()
    new, _ = tool.recalculate(_get(app, rid), _gwp())
    assert new["co2_emissions"] == pytest.approx(100 * 80.0 / 1000)


def test_period_blank_without_month(app, rworld, tmp_path):
    rid = _record(app, rworld, month=None)
    out_csv = tmp_path / "p.csv"
    tool.main(["--ids", str(rid), "--csv", str(out_csv)])
    assert list(csv.DictReader(out_csv.open(encoding="utf-8")))[0]["period"] == ""


def test_empty_selection(capsys, tmp_path):
    out_csv = tmp_path / "e.csv"
    tool.main(["--ids", "999999999", "--csv", str(out_csv)])
    assert "0 records" in capsys.readouterr().out
    assert out_csv.read_text(encoding="utf-8").strip() == ""


def test_drilling_tier2_plus_reads_as_tier_2_everywhere():
    """The drilling form stores factor_source 'tier2_plus' (Tier 2+, site gas composition): the inventory
    tier breakdown called it Tier 1, the OGMP level fell to 2 and this tool reported a tier fix each run."""
    from types import SimpleNamespace

    from services.inventory_uncertainty import _method_tier, default_rel_1sigma
    from services.ogmp import ogmp_level_for

    assert _method_tier("tier2_plus") == _method_tier("custom") == "Tier 2"
    assert (_method_tier("default"), _method_tier(None), _method_tier("specific")) == ("Tier 1", "Tier 1", "Tier 3")
    assert default_rel_1sigma(1, "drilling", "", "tier2_plus") == default_rel_1sigma(1, "drilling", "", "custom")
    lvl = lambda src: ogmp_level_for(SimpleNamespace(factor_source=src, calc_method="", ogmp_level=None))
    assert lvl("tier2_plus") == lvl("custom") == 3
    assert lvl("tier3") == lvl("specific") == 4 and lvl("default") == 2
    assert "tier2_plus" in tool.TIERS
