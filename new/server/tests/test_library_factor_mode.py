"""Library factors (the site's factor database: calculated or equipment factors) are a separate
choice from the API Compendium tiers.

- factor_mode="library" + a library factor -> activity x factor for any process
- API Compendium Tier 2 of engineering processes (completions, unloading, associated gas,
  fugitives) needs no library factor (it was wrongly rejected with 422)
- combustion Tier 2 without a library factor or site properties is still rejected (BUG-042)
"""
import pytest

from extensions import db
from models import CustomFactor
from tests.audit_helpers import login, make_facility, make_user


@pytest.fixture
def ctx(app, client):
    with app.app_context():
        f = make_facility(region="West")
        cf = CustomFactor(name="Compressor C-201 nameplate", ch4_factor=0.5, co2_factor=0.0, n2o_factor=0.0,
                          unit="kg/event", usage="completions", source="Equipment nameplate")
        db.session.add(cf)
        db.session.commit()
        login(client, make_user("admin", "Global"))
        yield f, cf


def post(client, f, **p):
    return client.post("/api/emissions/", json={"facility_id": f.id, "year": 2025, "month": 3, **p})


def test_engineering_tier2_needs_no_library_factor(client, ctx):
    f, _ = ctx
    r = post(client, f, process_type="unloading", factor_source="custom", amount=20, unit="events",
             calc_inputs={"unloading": {"tier": "tier2", "events": 20, "unloading_type": "plunger"}})
    assert r.status_code == 201, r.get_json()
    # API Table 6-10 plunger lift <= 100 events/yr: 0.185 t CH4/event -> 20 events = 3.7 t CH4
    assert r.get_json()["emissions"]["ch4"] == pytest.approx(3.7)

    r = post(client, f, process_type="completions", factor_source="custom", amount=1, unit="events",
             calc_inputs={"completions": {"tier": "tier2", "calc_method": "rate_duration", "comp_rate": 100,
                                          "comp_rate_unit": "Mcf/hr", "comp_duration": 10, "ch4_content": 80,
                                          "well_type": "gas"}})
    assert r.status_code == 201, r.get_json()
    # 100 Mcf/h x 10 h = 1e6 scf x 80 % CH4 -> 15.37 t CH4 (engine density convention)
    assert r.get_json()["emissions"]["ch4"] == pytest.approx(1e6 * 0.028316846592 * 0.80 * (16.04 / 23.685) / 1000, rel=1e-3)


def test_library_factor_is_activity_times_factor_for_any_process(client, ctx):
    f, cf = ctx
    r = post(client, f, process_type="completions", factor_source="custom", factor_mode="library",
             custom_factor_id=cf.id, fuel=str(cf.id), amount=4, unit="events",
             calc_inputs={"completions": {"amount": 4, "unit": "events", "tier": "tier1"}})
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["emissions"]["ch4"] == pytest.approx(4 * 0.5 / 1000)


def test_library_mode_requires_a_library_factor(client, ctx):
    f, _ = ctx
    r = post(client, f, process_type="pneumatic", factor_source="custom", factor_mode="library",
             amount=10, unit="devices", calc_inputs={"pneumatic": {"amount": 10}})
    assert r.status_code in (400, 422)
    assert "library factor" in r.get_json()["error"].lower()


def test_combustion_tier2_without_factor_or_site_properties_still_rejected(client, ctx):
    f, _ = ctx
    r = post(client, f, process_type="combustion", factor_source="custom", fuel="Natural Gas",
             amount=1000, unit="scf", calc_inputs={"combustion": {"amount": 1000, "unit": "scf"}})
    assert r.status_code in (400, 422)
