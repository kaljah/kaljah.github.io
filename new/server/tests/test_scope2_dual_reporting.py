"""Scope 2 gas split (ADM-14) and market-based totals on the dashboard (SU-12 / ADM-13)."""
import pytest

from extensions import db
from tests.audit_helpers import login, make_facility, make_user, uniq


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def test_grid_electricity_split_market_total_and_gwp20(client, ctx):
    from electricity_factors import grid_entry
    from services.dashboard_filters import gwp_pair

    f = make_facility(region=uniq("West"))
    login(client, make_user("admin", "Global"))
    base = dict(facility_id=f.id, year=2024, month=1, source_type="electricity", unit="kWh",
                electricity_kwh=1_000_000, grid_region="Algerian National Grid")
    r = client.post("/api/scope2", json=base)
    assert r.status_code == 201, r.get_data(as_text=True)
    r2 = client.post("/api/scope2", json={**base, "month": 2, "market_instrument_type": "REC"})
    assert r2.status_code == 201
    entry = grid_entry("Algerian National Grid")[1]
    em = r.get_json()["emissions"]
    assert em["co2"] == pytest.approx(1_000_000 * entry["co2"] / 1000)
    assert em["ch4"] == pytest.approx(1_000_000 * entry["ch4"] / 1000) and em["ch4"] > 0

    rows = client.get(f"/api/scope2?facility_id={f.id}").get_json()
    assert all(row["ch4"] > 0 and row["co2"] < row["co2e"] for row in rows)

    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()
    s100 = client.get(f"/api/dashboard/summary?year=2024&facilityId={f.id}").get_json()[0]
    loc = sum(row["co2e"] for row in rows)
    assert s100["scope2_total"] == pytest.approx(loc)
    assert s100["scope2_market_total"] == pytest.approx(loc / 2)  # the REC month is zero-carbon
    s20 = client.get(f"/api/dashboard/summary?year=2024&facilityId={f.id}&gwp_horizon=20").get_json()[0]
    c100, n100 = gwp_pair("100")
    c20, n20 = gwp_pair("20")
    kwh = 2_000_000
    delta = kwh * (entry["ch4"] * (c20 - c100) + entry["n2o"] * (n20 - n100)) / 1000
    assert s20["scope2_total"] == pytest.approx(loc + delta)
