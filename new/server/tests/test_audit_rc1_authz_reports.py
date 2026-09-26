"""RC-1 authorization regressions, part 2 (BUG-020/032/038/046/076)."""
import pytest

from extensions import db
from tests.audit_helpers import login, make_facility, make_user, uniq, upload


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


# ── BUG-020: master annual report ────────────────────────────────────────────────

@pytest.mark.parametrize("role,location,fid,expected", [
    ("it_admin", "Global", "170", 403),
    ("user", "West", "170", 403),       # 170 is not in West
    ("user", "West", "", 403),          # consolidated report needs org-wide access
    ("admin", "Global", "999999", 404),  # unsupported facility
])
def test_bug020_master_report_authorization(client, ctx, role, location, fid, expected):
    login(client, make_user(role, location))
    r = client.get(f"/api/reports/master-annual-report?facility_id={fid}")
    assert r.status_code == expected


def test_bug020_object_object_param_is_not_a_facility(client, ctx):
    login(client, make_user("admin", "Global"))
    assert client.get("/api/reports/master-annual-report?facility_id=[object%20Object]").status_code == 404


# ── BUG-032: SBTi baseline suggestion is region-scoped ────────────────────────────

def test_bug032_sbti_suggestion_scoped_to_region(client, ctx):
    from models import Emission

    west = make_facility(region="West")
    east = make_facility(region="East")
    for f, v in ((west, 10.0), (east, 1000.0)):
        db.session.add(Emission(facility_id=f.id, year=2012, month=1, process_type="combustion", co2e_total=v, status="Verified"))
    db.session.commit()
    login(client, make_user("user", "West"))
    data = client.get("/api/manage/sbti?base_year=2012").get_json()
    # only West facilities' emissions; the other region's 1000 t must not leak
    assert data["suggested_by_scope"]["scope1"] < 1000.0
    assert data["suggested_base_year_emissions"] < 1000.0


def test_bug032_regional_superuser_cannot_overwrite_corporate_target(client, ctx):
    login(client, make_user("superuser", "West"))
    r = client.post("/api/manage/sbti", json={"base_year": 2020, "base_year_emissions": 100, "target_year": 2030,
                                              "reduction_rate_pct": 4.2, "pathway_type": "1.5C"})
    assert r.status_code == 403


# ── BUG-038: audit trail region scoping ────────────────────────────────────────────

def test_bug038_regional_superuser_sees_only_own_region_audit_entries(client, ctx, app):
    from models import ActivityLog

    west = make_facility(region="West")
    east = make_facility(region="East")
    tag = uniq("AUD")
    db.session.add_all([
        ActivityLog(action="UPDATE", record_id="1", details=f"{tag} west", entity="Emission", facility_id=west.id),
        ActivityLog(action="UPDATE", record_id="2", details=f"{tag} east", entity="Emission", facility_id=east.id),
        ActivityLog(action="UPDATE", record_id="3", details=f"{tag} none", entity="Emission", facility_id=None),
    ])
    db.session.commit()
    login(client, make_user("superuser", "West"))
    r = client.get(f"/api/audit/?search={tag}&per_page=50")
    assert r.status_code == 200
    text = r.get_data(as_text=True)
    assert f"{tag} west" in text and f"{tag} east" not in text and f"{tag} none" not in text
    exp = client.get(f"/api/audit/export?search={tag}").get_data(as_text=True)
    assert f"{tag} east" not in exp
    with app.test_client() as admin_c:
        login(admin_c, make_user("admin", "Global"))
        assert f"{tag} east" in admin_c.get(f"/api/audit/?search={tag}&per_page=50").get_data(as_text=True)


# ── BUG-046: equity shares ─────────────────────────────────────────────────────────

def _partner():
    from models import JvPartner

    p = JvPartner(name=uniq("P"), code=uniq("C"))
    db.session.add(p)
    db.session.commit()
    return p


@pytest.mark.parametrize("pct", [500, -50, "inf", "abc"])
def test_bug046_equity_pct_validated(client, ctx, pct):
    f = make_facility(region="West")
    p = _partner()
    login(client, make_user("admin", "Global"))
    r = client.post("/api/equity/shares", json={"facility_id": f.id, "partner_id": p.id, "equity_share_pct": pct})
    assert r.status_code == 400


def test_bug046_user_role_cannot_rewrite_ownership(client, ctx):
    f = make_facility(region="West")
    p = _partner()
    login(client, make_user("user", "West"))
    r = client.post("/api/equity/shares", json={"facility_id": f.id, "partner_id": p.id, "equity_share_pct": 10})
    assert r.status_code == 403


def test_bug046_overlapping_shares_cannot_exceed_100(client, ctx):
    f = make_facility(region="West")
    p1, p2 = _partner(), _partner()
    login(client, make_user("admin", "Global"))
    assert client.post("/api/equity/shares", json={"facility_id": f.id, "partner_id": p1.id, "equity_share_pct": 70,
                                                   "effective_start_date": "2020-01-01"}).status_code == 200
    r = client.post("/api/equity/shares", json={"facility_id": f.id, "partner_id": p2.id, "equity_share_pct": 40,
                                                "effective_start_date": "2021-01-01"})
    assert r.status_code == 400
    # sequential (non-overlapping) slices for the same partner are fine
    assert client.post("/api/equity/shares", json={"facility_id": f.id, "partner_id": p2.id, "equity_share_pct": 30,
                                                   "effective_start_date": "2021-01-01"}).status_code == 200


def test_bug046_allocation_is_time_weighted_by_effective_dates():
    """Hand calc: 20 % from 1 Jan-30 Jun 2023 (181 d) and 50 % from 1 Jul-31 Dec (184 d):
    (20*181 + 50*184) / 365 = 35.1233 %. A slice ending in 2022 must not count for 2023."""
    from routes.equity_routes import effective_share_pct

    class S:
        def __init__(self, pct, start, end=None):
            self.equity_share_pct, self.effective_start_date, self.effective_end_date = pct, start, end

    slices = [S(99, "2019-01-01", "2022-12-31"), S(20, "2023-01-01", "2023-06-30"), S(50, "2023-07-01")]
    assert effective_share_pct(slices, 2023) == pytest.approx((20 * 181 + 50 * 184) / 365, rel=1e-9)
    assert effective_share_pct(slices, 2022) == pytest.approx(99.0)
    assert effective_share_pct([S(10, "2030-01-01")], 2023) is None


# ── BUG-076: bulk job ownership ────────────────────────────────────────────────────

def test_bug076_job_status_only_visible_to_owner_or_admin(client, ctx, app):
    fac = make_facility(region="West")
    owner = make_user("user", "West")
    login(client, owner)
    csv = f"date,facility_name,process_type,fuel_type,quantity,unit\n2024-01,{fac.name},combustion,Natural Gas,1,MMBtu\n"
    r, job, st = upload(client, csv, "1")
    assert job and "error_csv_path" not in st
    for role in ("it_admin", "user"):
        with app.test_client() as other:
            login(other, make_user(role, "West" if role == "user" else "Global"))
            assert other.get(f"/api/emissions/upload/status/{job}").status_code == 404
            assert other.get(f"/api/emissions/upload/errors/{job}").status_code == 404
