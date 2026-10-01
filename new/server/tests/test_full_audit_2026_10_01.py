"""Full-platform audit 2026-10-01 (AUDIT_MEMORY.md section 8, A-01 .. A-09)."""
import json

import pytest

from extensions import db
from models import ActivityLog, BaseYearRecalculation, CustomFactor, Emission, Goal, User
from tests.audit_helpers import login, make_facility, make_user, upload


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


NEW_PW = "N3w!Password#2026"


# ── A-01: password reset only on accounts with a lower role ─────────────────────
@pytest.mark.parametrize("actor,target,expected", [
    ("it", "admin", 403),
    ("it", "it_admin", 403),
    ("it", "superuser", 403),
    ("it", "it", 403),
    ("it", "user", 200),
    ("it_admin", "it_manager", 403),
    ("it_admin", "admin", 200),
    ("it_manager", "superuser", 200),
])
def test_a01_password_reset_requires_higher_role(app, ctx, actor, target, expected):
    victim = make_user(target)
    with app.test_client() as c:
        login(c, make_user(actor))
        r = c.post(f"/api/auth/users/{victim.id}/reset-password", json={"newPassword": NEW_PW})
    assert r.status_code == expected, r.get_data(as_text=True)
    db.session.expire_all()
    assert db.session.get(User, victim.id).check_password(NEW_PW) is (expected == 200)


# ── A-02: account creation follows the same separation of duties as role changes ─
@pytest.mark.parametrize("actor,role,expected", [
    ("it_admin", "superuser", 403),
    ("it_admin", "admin", 403),
    ("it_admin", "user", 201),
    ("it_manager", "superuser", 201),
])
def test_a02_register_separation_of_duties(app, ctx, actor, role, expected):
    with app.test_client() as c:
        login(c, make_user(actor))
        r = c.post("/api/auth/users", json={
            "fullName": "New", "orgName": "Org", "email": f"new_{actor}_{role}@audit.test",
            "sector": "Oil & Gas", "password": NEW_PW, "role": role, "location": "West",
        })
    assert r.status_code == expected, r.get_data(as_text=True)


# ── A-03: global settings never land in (or are masked by) user preferences ─────
def test_a03_settings_secret_not_copied_into_preferences(app, ctx):
    from routes.auth import save_setting_to_db, _app_settings

    before = _app_settings.get("copernicus_password", "")
    admin = make_user("admin")
    try:
        with app.test_client() as c:
            login(c, admin)
            r = c.put("/api/auth/settings", json={"copernicus_password": "S3cretValue", "language": "fr"})
            assert r.status_code == 200
        db.session.expire_all()
        prefs = json.loads(db.session.get(User, admin.id).preferences or "{}")
        assert "copernicus_password" not in prefs
        assert prefs.get("language") == "fr"  # personal preferences are still saved
    finally:
        save_setting_to_db("copernicus_password", before)


def test_a03_stale_preference_does_not_mask_global_gwp(app, ctx):
    from routes.auth import _app_settings

    admin = make_user("admin")
    admin.preferences = json.dumps({"gwp_standard": "AR4", "copernicus_password": "legacy-leak", "theme": "light"})
    db.session.commit()
    with app.test_client() as c:
        login(c, admin)
        body = c.get("/api/auth/settings").get_json()
        assert body["gwp_standard"] == (_app_settings.get("gwp_standard") or "AR5")
        assert body.get("copernicus_password") in (None, "", "********")
        # a later save removes the legacy copies from the stored preferences
        assert c.put("/api/auth/settings", json={"theme": "light"}).status_code == 200
    db.session.expire_all()
    prefs = json.loads(db.session.get(User, admin.id).preferences)
    assert "gwp_standard" not in prefs and "copernicus_password" not in prefs


# ── A-04: user.location is matched as a value, not a LIKE pattern ───────────────
def test_a04_location_wildcards_do_not_widen_scope(app, ctx):
    from utils import get_allowed_facility_ids

    own = make_facility(region="Blk_405")
    other = make_facility(region="BlkX405")
    user = make_user("user", location="Blk_405")
    allowed = get_allowed_facility_ids(user)
    assert own.id in allowed and other.id not in allowed
    assert get_allowed_facility_ids(make_user("user", location="%")) == []


# ── A-05: goals and the base year are organisation-wide and audited ────────────
def test_a05_regional_superuser_cannot_delete_goal_or_move_base_year(app, ctx):
    db.session.add(Goal(year=2093, target_amount=1000.0))
    db.session.commit()
    with app.test_client() as c:
        login(c, make_user("superuser", location="West"))
        assert c.delete("/api/goals/2093").status_code == 403
        r = c.post("/api/base-years", json={"year": 2019, "reason": "regional attempt"})
        assert r.status_code == 403
    assert Goal.query.filter_by(year=2093).first() is not None


def test_a05_goal_and_base_year_changes_are_audited(app, ctx):
    db.session.add(Goal(year=2094, target_amount=500.0))
    db.session.commit()
    with app.test_client() as c:
        login(c, make_user("admin"))
        assert c.delete("/api/goals/2094").status_code == 200
        r = c.post("/api/base-years", json={"year": 2020, "reason": "audit A-05 acquisition"})
        assert r.status_code == 201, r.get_data(as_text=True)
        rec_id = r.get_json()["id"]
        assert c.delete(f"/api/base-years/{rec_id}").status_code == 200
    assert ActivityLog.query.filter_by(record_id="goal-2094", action="DELETE").count() == 1
    assert ActivityLog.query.filter_by(record_id=f"base-year-{rec_id}").count() == 2
    assert db.session.get(BaseYearRecalculation, rec_id) is None


# ── A-06: unknown e-mail costs the same hash work as a wrong password ───────────
def test_a06_login_unknown_email_runs_password_hash(app, ctx, monkeypatch):
    import routes.auth as auth

    calls = []
    real = auth.check_password_hash
    monkeypatch.setattr(auth, "check_password_hash", lambda h, p: calls.append(h) or real(h, p))
    with app.test_client() as c:
        r = c.post("/api/auth/login", json={"email": "nobody-a06@audit.test", "password": "x"})
    assert r.status_code == 401 and calls == [auth._DUMMY_PASSWORD_HASH]


# ── A-07: the batch dashboard cache key carries the shared invalidation epoch ───
def test_a07_batch_dashboard_cache_key_has_epoch(app, ctx, monkeypatch):
    import routes.dashboard as dash

    admin = make_user("admin")
    with app.test_client() as c:
        login(c, admin)
        dash.DASHBOARD_CACHE.clear()
        assert c.get("/api/dashboard/batch-all?year=2024").status_code == 200
        keys = [k for k in dash.DASHBOARD_CACHE.keys() if isinstance(k, tuple) and k and k[0] == "batch_all"]
        assert keys and keys[0][1] == dash._get_global_cache_epoch()
        # a newer epoch (another worker's commit) must miss the old entry
        monkeypatch.setattr(dash, "_get_global_cache_epoch", lambda: keys[0][1] + 1.0)
        assert c.get("/api/dashboard/batch-all?year=2024").status_code == 200
        assert len([k for k in dash.DASHBOARD_CACHE.keys() if isinstance(k, tuple) and k and k[0] == "batch_all"]) == 2


# ── A-09: per-user cap on concurrent bulk uploads ───────────────────────────────
def test_a09_concurrent_upload_cap(app, ctx, monkeypatch):
    import background_processor as bp

    user = make_user("user", location="West")
    monkeypatch.setenv("MAX_CONCURRENT_UPLOADS_PER_USER", "1")
    with bp.upload_jobs_lock:
        bp.upload_jobs["a09-running"] = {"status": "processing", "owner_id": user.id, "created_at": 0}
    try:
        with app.test_client() as c:
            login(c, user)
            r, job, _ = upload(c, "date,facility_name\n", "1", wait=False)
        assert r.status_code == 429 and job is None
    finally:
        with bp.upload_jobs_lock:
            bp.upload_jobs.pop("a09-running", None)


# ── Owner decisions 2026-10-01 ─────────────────────────────────────────────────
# Superusers are limited to one region; organisation-wide records are admin only.
def test_superuser_without_region_sees_nothing(app, ctx):
    from utils import facility_in_user_scope, get_allowed_facility_ids

    make_facility(region="West")
    for loc in ("Global", "all", "", None):
        su = make_user("superuser", location=loc)
        assert get_allowed_facility_ids(su) == []
        assert facility_in_user_scope(su, region="West") is False
    west = make_facility(region="West")
    assert west.id in get_allowed_facility_ids(make_user("superuser", location="West"))


def test_superuser_needs_a_region_when_created_or_assigned(app, ctx):
    with app.test_client() as c:
        login(c, make_user("it_manager"))
        body = {"fullName": "S", "orgName": "O", "sector": "Oil & Gas", "password": NEW_PW, "role": "superuser"}
        r = c.post("/api/auth/users", json={**body, "email": "su_global@audit.test", "location": "Global"})
        assert r.status_code == 400 and r.get_json()["field"] == "location"
        r = c.post("/api/auth/users", json={**body, "email": "su_west@audit.test", "location": "West"})
        assert r.status_code == 201
        uid = r.get_json()["user"]["id"]
        assert c.put(f"/api/auth/users/{uid}", json={"location": "all"}).status_code == 400
        # a legacy organisation-wide superuser can still be deactivated
        legacy = make_user("superuser", location="Global")
        assert c.put(f"/api/auth/users/{legacy.id}", json={"status": "disabled"}).status_code == 200


def test_org_wide_settings_and_factors_are_admin_only(app, ctx):
    with app.test_client() as c:
        login(c, make_user("superuser", location="West"))
        assert c.put("/api/auth/settings", json={"reconciliation_threshold": 15}).status_code == 403
        r = c.post("/api/custom-factors", json={"factor_name": "su-factor", "unit": "scf", "co2_factor": 0.05})
        assert r.status_code == 403
        assert c.post("/api/reporting-metadata", json={"year": 2024}).status_code == 403
    with app.test_client() as c:
        login(c, make_user("admin"))
        r = c.post("/api/custom-factors", json={"factor_name": "admin-factor-o4", "unit": "scf", "co2_factor": 0.05})
        assert r.status_code in (200, 201), r.get_data(as_text=True)


# Custom factors used by records keep their values (O-04).
def test_referenced_custom_factor_values_are_locked(app, ctx):
    admin = make_user("admin")
    fac = make_facility(region="West")
    cf = CustomFactor(name="o4-locked", unit="scf", co2_factor=0.05, ch4_factor=0.001, n2o_factor=0.0)
    db.session.add(cf)
    db.session.commit()
    db.session.add(Emission(record_id="o4-rec", facility_id=fac.id, year=2024, month=1, process_type="combustion",
                            fuel_type="o4-locked", custom_factor_id=cf.id, quantity=1.0, unit="scf", status="Verified"))
    db.session.commit()
    with app.test_client() as c:
        login(c, admin)
        r = c.put(f"/api/custom-factors/{cf.id}", json={"co2_factor": 0.07})
        assert r.status_code == 409 and r.get_json()["fields"] == ["co2_factor"]
        # resending the same values (forms send the whole factor) and metadata edits are allowed
        r = c.put(f"/api/custom-factors/{cf.id}", json={"co2_factor": 0.05, "description": "documented"})
        assert r.status_code == 200, r.get_data(as_text=True)
    db.session.expire_all()
    assert db.session.get(CustomFactor, cf.id).co2_factor == 0.05
    log = ActivityLog.query.filter_by(entity="CustomFactor", record_id=str(cf.id), action="UPDATE").one()
    assert json.loads(log.new_values) == {"description": "documented"} and json.loads(log.old_values) == {"description": None}


def test_unreferenced_custom_factor_edit_logs_old_and_new_values(app, ctx):
    cf = CustomFactor(name="o4-free", unit="scf", co2_factor=0.05)
    db.session.add(cf)
    db.session.commit()
    with app.test_client() as c:
        login(c, make_user("admin"))
        assert c.put(f"/api/custom-factors/{cf.id}", json={"co2_factor": 0.06}).status_code == 200
    log = ActivityLog.query.filter_by(entity="CustomFactor", record_id=str(cf.id), action="UPDATE").one()
    assert json.loads(log.old_values) == {"co2_factor": 0.05} and json.loads(log.new_values) == {"co2_factor": 0.06}
