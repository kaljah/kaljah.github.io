"""Step 3 regression tests (UNV-06 / UNV-07): boiler/steam defaults and configurability."""

import pytest

from app import app
from calculations.dispatcher import CalculationDispatcher
from calculations.indirect import IndirectSteamCalculator
from extensions import db, limiter
from models import Facility, User
from routes.scope2 import _steam_fuel_factor_kg_per_mmbtu

EMAIL = "step3-steam@example.org"
PASSWORD = "Step3-Steam-Test-Password!"


@pytest.fixture
def steam_client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["RATELIMIT_ENABLED"] = False
    limiter.enabled = False

    with app.test_client() as client:
        with app.app_context():
            user = User.query.filter_by(email=EMAIL).first()
            if not user:
                user = User(
                    email=EMAIL,
                    fullName="Step 3 Steam Admin",
                    orgName="Demo Operator Co.",
                    sector="Energy",
                    role="admin",
                    location="Global",
                )
                user.set_password(PASSWORD)
                db.session.add(user)
            fac = Facility.query.filter_by(code="STEP3-STEAM").first()
            if not fac:
                fac = Facility(
                    name="Step 3 Steam Facility",
                    code="STEP3-STEAM",
                    region="Basin Alpha",
                    segment="Upstream",
                )
                db.session.add(fac)
            db.session.commit()
            fac_id = fac.id

        login = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert login.status_code == 200
        yield client, fac_id


def test_indirect_steam_default_is_80pct_and_zero_loss():
    """UNV-06/07: omitted parameters restore the 80% boiler efficiency and 0% line loss defaults."""
    calc = IndirectSteamCalculator()
    res = calc.calculate(100.0, 50.0, None, None, {}, heat_unit="mmbtu")

    assert res["inputs"]["boiler_efficiency"] == pytest.approx(0.80)
    assert res["inputs"]["transmission_loss"] == pytest.approx(0.0)
    assert res["inputs"]["net_efficiency"] == pytest.approx(0.80)
    assert res["results"]["co2"]["value"] == pytest.approx(100.0 / 0.80 * 50.0 / 1000.0)
    assert res["has_silent_defaults"] is True

    by_id = {d["factor_id"]: d for d in res["silent_defaults"]}
    assert by_id["SCP2-004"]["applied_value"] == pytest.approx(0.80)
    assert by_id["SCP2-005"]["applied_value"] == pytest.approx(0.0)
    assert "80%" in by_id["SCP2-004"]["warning"]
    assert "0%" in by_id["SCP2-005"]["warning"]
    assert "Exhibit 8.3" in by_id["SCP2-004"]["warning"]
    assert "82%" in by_id["SCP2-004"]["warning"]
    assert "Exhibit 8.3" in by_id["SCP2-005"]["warning"]
    assert "10%" in by_id["SCP2-005"]["warning"]


def test_indirect_steam_user_configurable_exhibit_8_3_example():
    """UNV-06/07: users can supply custom parameters including the optional 82%/10% Exhibit 8.3 values."""
    calc = IndirectSteamCalculator()
    res = calc.calculate(100.0, 50.0, 0.82, 0.10, {}, heat_unit="mmbtu")
    assert res["inputs"]["boiler_efficiency"] == pytest.approx(0.82)
    assert res["inputs"]["transmission_loss"] == pytest.approx(0.10)
    assert res["inputs"]["net_efficiency"] == pytest.approx(0.72)
    assert res["results"]["co2"]["value"] == pytest.approx(100.0 / 0.72 * 50.0 / 1000.0)
    assert res["has_silent_defaults"] is False

    res_pct = calc.calculate(100.0, 50.0, "82%", "10%", {}, heat_unit="mmbtu")
    assert res_pct["results"]["co2"]["value"] == pytest.approx(res["results"]["co2"]["value"])


def test_dispatcher_indirect_steam_defaults_and_overrides():
    """Dispatcher defaults to 80%/0% when omitted and honors Exhibit 8.3 overrides when supplied."""
    disp = CalculationDispatcher()
    default_res = disp.dispatch(
        "indirect_steam",
        {"amount": 100.0, "unit": "mmbtu", "factor_source": "specific"},
        {"co2": 50.0},
        {},
    )
    assert default_res["inputs"]["net_efficiency"] == pytest.approx(0.80)
    assert default_res["results"]["co2"]["value"] == pytest.approx(100.0 / 0.80 * 50.0 / 1000.0)

    ex83_res = disp.dispatch(
        "indirect_steam",
        {
            "amount": 100.0,
            "unit": "mmbtu",
            "factor_source": "specific",
            "boiler_eff": 82,
            "trans_loss": 10,
        },
        {"co2": 50.0},
        {},
    )
    assert ex83_res["inputs"]["net_efficiency"] == pytest.approx(0.72)
    assert ex83_res["results"]["co2"]["value"] == pytest.approx(100.0 / 0.72 * 50.0 / 1000.0)


def test_scope2_route_steam_defaults_and_configurable_params(steam_client):
    """POST /api/scope2 defaults to 80%/0% and supports user-configured top-level & nested overrides."""
    client, fac_id = steam_client
    fuel_ef = _steam_fuel_factor_kg_per_mmbtu(None)

    # 1. Defaults omitted -> 80% / 0%
    r_def = client.post(
        "/api/scope2",
        json={
            "facility_id": fac_id,
            "year": 2025,
            "month": 1,
            "source_type": "indirect_steam",
            "amount": 720.0,
            "unit": "mmbtu",
        },
    )
    assert r_def.status_code == 201, r_def.get_json()
    expected_def = (720.0 / 0.80) * fuel_ef / 1000.0
    assert r_def.get_json()["co2e"] == pytest.approx(expected_def, rel=1e-5)

    # 2. Nested Exhibit 8.3 overrides (82% / 10%)
    r_nested = client.post(
        "/api/scope2",
        json={
            "facility_id": fac_id,
            "year": 2025,
            "month": 2,
            "source_type": "indirect_steam",
            "amount": 720.0,
            "unit": "mmbtu",
            "calc_inputs": {
                "indirect_steam": {
                    "boiler_eff": 0.82,
                    "trans_loss": 0.10,
                }
            },
        },
    )
    assert r_nested.status_code == 201, r_nested.get_json()
    expected_ex83 = (720.0 / 0.72) * fuel_ef / 1000.0
    assert r_nested.get_json()["co2e"] == pytest.approx(expected_ex83, rel=1e-5)

    # 3. Top-level overrides using boiler_efficiency + transmission_loss
    r_top = client.post(
        "/api/scope2",
        json={
            "facility_id": fac_id,
            "year": 2025,
            "month": 3,
            "source_type": "indirect_steam",
            "amount": 720.0,
            "unit": "mmbtu",
            "boiler_efficiency": 0.82,
            "transmission_loss": "10%",
        },
    )
    assert r_top.status_code == 201, r_top.get_json()
    assert r_top.get_json()["co2e"] == pytest.approx(expected_ex83, rel=1e-5)
