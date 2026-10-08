"""Year-over-year bridge: the steps must reconcile start -> end, and the route must respect roles."""
from app import app
from routes.dashboard_bridge import build_bridge
from tests.audit_helpers import login, make_user


def _row(year, **parts):
    base = {"year": year, "combustion": 0, "flaring": 0, "venting": 0, "fugitive": 0, "process": 0, "other": 0,
            "scope2_total": 0}
    base.update(parts)
    return base


def test_bridge_reconciles_and_orders_steps():
    rows = [_row(2024, combustion=100, flaring=50, scope2_total=20), _row(2025, combustion=90, flaring=70, venting=5, other=3, scope2_total=18)]
    b = build_bridge(rows, 2025)
    assert b["prev_year"] == 2024 and b["year"] == 2025
    assert b["start"] == 170 and b["end"] == 186
    deltas = {s["name"]: s["delta"] for s in b["steps"]}
    assert deltas == {"Combustion": -10, "Flaring": 20, "Venting": 5, "Fugitive": 0, "Process & other": 3, "Scope 2": -2}
    assert b["reconciles"] is True


def test_bridge_uses_closest_earlier_year_and_defaults_to_latest():
    rows = [_row(2021, combustion=10), _row(2024, combustion=30)]
    b = build_bridge(rows, None)
    assert (b["prev_year"], b["year"]) == (2021, 2024)


def test_bridge_without_an_earlier_year_is_none():
    assert build_bridge([_row(2024, combustion=1)], 2024) is None
    assert build_bridge([], None) is None
    assert build_bridge([_row(2023), _row(2024)], 2022) is None


def test_route_returns_steps_for_admin():
    client = app.test_client()
    login(client, make_user("admin"))
    r = client.get("/api/dashboard/yoy-bridge?year=all")
    assert r.status_code == 200 and "steps" in r.get_json()
    assert client.get("/api/dashboard/yoy-bridge?year=abc").status_code == 400


def test_route_is_closed_to_it_roles():
    client = app.test_client()
    login(client, make_user("it_admin"))
    assert client.get("/api/dashboard/yoy-bridge").status_code == 403


def test_scope3_step_is_added_only_on_request():
    rows = [_row(2024, combustion=100, scope3=40), _row(2025, combustion=100, scope3=55)]
    plain = build_bridge(rows, 2025)
    assert [s["name"] for s in plain["steps"]][-1] == "Scope 2" and plain["end"] == 100
    with3 = build_bridge(rows, 2025, include_scope3=True)
    assert with3["steps"][-1] == {"name": "Scope 3", "delta": 15}
    assert with3["start"] == 140 and with3["end"] == 155 and with3["scope3"] is True and with3["reconciles"]


def test_route_accepts_include_scope3():
    client = app.test_client()
    login(client, make_user("admin"))
    r = client.get("/api/dashboard/yoy-bridge?year=all&includeScope3=true")
    assert r.status_code == 200
