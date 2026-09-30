"""RC-11 SBTi trajectory regressions (BUG-014/019/028/059). Hand values in each test."""
import datetime

import pytest

from extensions import db
from models import Emission, SbtiTarget, Scope3Emission
from tests.audit_helpers import login, make_facility, make_user

CY = datetime.date.today().year


@pytest.fixture
def setup(client, app):
    with app.app_context():
        SbtiTarget.query.delete()
        Emission.query.filter(Emission.year.in_([2020, 2023, CY])).delete(synchronize_session=False)
        Scope3Emission.query.filter(Scope3Emission.year.in_([2020, 2023])).delete(synchronize_session=False)
        db.session.commit()
        f = make_facility(region="West")
        db.session.add(SbtiTarget(base_year=2020, base_year_emissions=1000.0, target_year=2030,
                                  reduction_rate_pct=4.2, pathway_type="1.5C", scope_coverage="S1S2S3"))
        db.session.commit()
        login(client, make_user("admin", "Global"))
        yield client, f


def traj(c, **q):
    qs = "&".join(f"{k}={v}" for k, v in q.items())
    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    return c.get(f"/api/dashboard/sbti-trajectory?{qs}").get_json()


def test_bug028_no_data_is_not_on_track(setup):
    c, f = setup
    d = traj(c, facility_id=f.id)  # isolated from other tests' data
    assert d["on_track"] is None and d["reduction_achieved_pct"] is None and d["current_actual"] is None


def test_bug014_current_partial_year_is_not_the_progress_year(setup):
    c, f = setup
    db.session.add_all([
        Emission(facility_id=f.id, year=2020, month=1, process_type="combustion", co2e_total=1000, status="Verified"),
        Emission(facility_id=f.id, year=2023, month=1, process_type="combustion", co2e_total=950, status="Verified"),
        Emission(facility_id=f.id, year=CY, month=1, process_type="combustion", co2e_total=10, status="Verified"),
    ])
    db.session.commit()
    d = traj(c, facility_id=f.id)
    # 2023: target 1000 x (1 - 0.042 x 3) = 874; actual 950 -> 5 % reduction, behind
    assert d["latest_actual_year"] == 2023
    assert d["current_target"] == pytest.approx(874.0)
    assert d["reduction_achieved_pct"] == pytest.approx(5.0)
    assert d["on_track"] is False
    assert d["ytd_year"] == CY and d["ytd_actual"] == pytest.approx(10)


def test_bug019_scope_subset_uses_its_own_baseline(setup):
    c, f = setup
    db.session.add_all([
        Emission(facility_id=f.id, year=2020, month=1, process_type="combustion", co2e_total=800, status="Verified"),
        Scope3Emission(facility_id=f.id, year=2020, month=1, category="Category 1", co2e=200, status="Verified"),
        Emission(facility_id=f.id, year=2023, month=1, process_type="combustion", co2e_total=750, status="Verified"),
        Scope3Emission(facility_id=f.id, year=2023, month=1, category="Category 1", co2e=200, status="Verified"),
    ])
    db.session.commit()
    d = traj(c, scope="s1_s2", facility_id=f.id)
    # S1+S2 baseline 800; 2023 target 800 x 0.874 = 699.2; actual 750 -> 6.25 %
    assert d["base_year_emissions"] == pytest.approx(800)
    assert d["current_target"] == pytest.approx(699.2)
    assert d["reduction_achieved_pct"] == pytest.approx(6.25)
    assert d["on_track"] is False


def test_bug019_region_restricted_user_uses_region_baseline(setup, app):
    c, f = setup
    east = make_facility(region="East")
    db.session.add_all([
        Emission(facility_id=f.id, year=2020, month=1, process_type="combustion", co2e_total=500, status="Verified"),
        Emission(facility_id=east.id, year=2020, month=1, process_type="combustion", co2e_total=500, status="Verified"),
        Emission(facility_id=f.id, year=2023, month=1, process_type="combustion", co2e_total=450, status="Verified"),
    ])
    db.session.commit()
    with app.test_client() as west:
        login(west, make_user("user", "West"))
        d = traj(west)
    # West baseline 500 (not the corporate 1000): target 437, reduction 10 %, behind
    assert d["base_year_emissions"] == pytest.approx(500)
    assert d["current_target"] == pytest.approx(437.0)
    assert d["reduction_achieved_pct"] == pytest.approx(10.0)
    assert d["on_track"] is False


def test_bug059_label_follows_pathway(setup):
    c, f = setup
    assert traj(c)["pathway_label"].startswith("SBTi 1.5")
    SbtiTarget.query.delete()
    db.session.add(SbtiTarget(base_year=2020, base_year_emissions=1000, target_year=2030, reduction_rate_pct=1.0,
                              pathway_type="custom"))
    db.session.commit()
    assert traj(c)["pathway_label"] == "Custom Linear Target"
