"""API Compendium (2021) §8.1.5 & Exhibit 8.3 compliance tests (UNV-06 / UNV-07)."""

import pytest
from app import app
from background_processor import _process_row_scope2
from calculations.dispatcher import CalculationDispatcher
from calculations.indirect import (
    DEFAULT_BOILER_EFFICIENCY,
    DEFAULT_TRANSMISSION_LOSS,
    IndirectSteamCalculator,
)
from extensions import db, limiter
from models import Facility, User
from routes.scope2 import (
    _recalc_indirect_steam,
    _steam_fuel_factor_kg_per_mmbtu,
)
from scripts.verified_factors_seed_data import ALL_VERIFIED_FACTORS

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


def test_indirect_steam_default_matches_compendium_exhibit_8_3():
    """UNV-06/07: omitted params default to API Compendium (2021) §8.1.5 / Exhibit 8.3 (92% boiler, 10% loss = 82% net)."""
    assert DEFAULT_BOILER_EFFICIENCY == pytest.approx(0.92)
    assert DEFAULT_TRANSMISSION_LOSS == pytest.approx(0.10)

    calc = IndirectSteamCalculator()
    res = calc.calculate(100.0, 50.0, None, None, {}, heat_unit="mmbtu")

    assert res["inputs"]["boiler_efficiency"] == pytest.approx(0.92)
    assert res["inputs"]["transmission_loss"] == pytest.approx(0.10)
    assert res["inputs"]["net_efficiency"] == pytest.approx(0.82)
    assert res["results"]["co2"]["value"] == pytest.approx(100.0 / 0.82 * 50.0 / 1000.0)
    assert res["has_silent_defaults"] is True

    by_id = {d["factor_id"]: d for d in res["silent_defaults"]}
    assert by_id["SCP2-004"]["applied_value"] == pytest.approx(0.92)
    assert by_id["SCP2-005"]["applied_value"] == pytest.approx(0.10)
    assert "92%" in by_id["SCP2-004"]["warning"]
    assert "10%" in by_id["SCP2-005"]["warning"]
    assert "8.1.5" in by_id["SCP2-004"]["source"]
    assert "Exhibit 8.3" in by_id["SCP2-005"]["source"]


def test_indirect_steam_user_configurable_custom_overrides():
    """UNV-06/07: users can supply custom parameters (e.g. 80% boiler, 0% loss or 85% / 5%) overriding defaults."""
    calc = IndirectSteamCalculator()
    res = calc.calculate(100.0, 50.0, 0.80, 0.0, {}, heat_unit="mmbtu")
    assert res["inputs"]["boiler_efficiency"] == pytest.approx(0.80)
    assert res["inputs"]["transmission_loss"] == pytest.approx(0.0)
    assert res["inputs"]["net_efficiency"] == pytest.approx(0.80)
    assert res["results"]["co2"]["value"] == pytest.approx(100.0 / 0.80 * 50.0 / 1000.0)
    assert res["has_silent_defaults"] is False

    res_pct = calc.calculate(100.0, 50.0, "85%", "5%", {}, heat_unit="mmbtu")
    assert res_pct["inputs"]["net_efficiency"] == pytest.approx(0.80)
    assert res_pct["results"]["co2"]["value"] == pytest.approx(res["results"]["co2"]["value"])


def test_dispatcher_indirect_steam_compendium_defaults_and_overrides():
    """Dispatcher defaults to 92%/10% (net 82%) when omitted and honors custom overrides when supplied."""
    disp = CalculationDispatcher()
    default_res = disp.dispatch(
        "indirect_steam",
        {"amount": 100.0, "unit": "mmbtu", "factor_source": "specific"},
        {"co2": 50.0},
        {},
    )
    assert default_res["inputs"]["boiler_efficiency"] == pytest.approx(0.92)
    assert default_res["inputs"]["transmission_loss"] == pytest.approx(0.10)
    assert default_res["inputs"]["net_efficiency"] == pytest.approx(0.82)
    assert default_res["results"]["co2"]["value"] == pytest.approx(100.0 / 0.82 * 50.0 / 1000.0)

    custom_res = disp.dispatch(
        "indirect_steam",
        {
            "amount": 100.0,
            "unit": "mmbtu",
            "factor_source": "specific",
            "boiler_eff": 80,
            "trans_loss": 0,
        },
        {"co2": 50.0},
        {},
    )
    assert custom_res["inputs"]["net_efficiency"] == pytest.approx(0.80)
    assert custom_res["results"]["co2"]["value"] == pytest.approx(100.0 / 0.80 * 50.0 / 1000.0)


def test_scope2_route_and_csv_steam_compendium_defaults(steam_client):
    """POST/PUT /api/scope2 and CSV bulk import default to 92%/10% (net 82%) and allow user overrides."""
    client, fac_id = steam_client
    fuel_ef = _steam_fuel_factor_kg_per_mmbtu(None)

    # 1. Defaults omitted -> 92% / 10% (net 82%)
    r_def = client.post(
        "/api/scope2",
        json={
            "facility_id": fac_id,
            "year": 2025,
            "month": 1,
            "source_type": "indirect_steam",
            "amount": 820.0,
            "unit": "mmbtu",
        },
    )
    assert r_def.status_code == 201, r_def.get_json()
    expected_def = (820.0 / 0.82) * fuel_ef / 1000.0
    assert r_def.get_json()["co2e"] == pytest.approx(expected_def, rel=1e-5)

    # 2. Nested custom overrides (80% / 0%)
    r_nested = client.post(
        "/api/scope2",
        json={
            "facility_id": fac_id,
            "year": 2025,
            "month": 2,
            "source_type": "indirect_steam",
            "amount": 820.0,
            "unit": "mmbtu",
            "calc_inputs": {
                "indirect_steam": {
                    "boiler_eff": 0.80,
                    "trans_loss": 0.0,
                }
            },
        },
    )
    assert r_nested.status_code == 201, r_nested.get_json()
    expected_custom = (820.0 / 0.80) * fuel_ef / 1000.0
    assert r_nested.get_json()["co2e"] == pytest.approx(expected_custom, rel=1e-5)

    # 3. Top-level custom overrides using boiler_efficiency + transmission_loss
    r_top = client.post(
        "/api/scope2",
        json={
            "facility_id": fac_id,
            "year": 2025,
            "month": 3,
            "source_type": "indirect_steam",
            "amount": 820.0,
            "unit": "mmbtu",
            "boiler_efficiency": 0.85,
            "transmission_loss": "5%",
        },
    )
    assert r_top.status_code == 201, r_top.get_json()
    assert r_top.get_json()["co2e"] == pytest.approx(expected_custom, rel=1e-5)

    # 4. CSV upload with omitted boiler_eff / trans_loss matches API default (must NOT divide 0.10 by 100!)
    with app.app_context():
        fac = db.session.get(Facility, fac_id)
        admin = User.query.filter_by(email=EMAIL).first()
        obj, errs = _process_row_scope2(
            row={
                "date": "2025-04",
                "facility_name": fac.name,
                "source_type": "indirect_steam",
                "consumption": "820",
                "unit": "mmbtu",
            },
            user_id=admin.id,
            fac_name_map={fac.name.lower(): fac},
            fac_id_map={str(fac.id): fac},
            GRID_FACTORS={},
            job_id="compendium-steam-default",
            row_idx=1,
        )
        assert errs == []
        assert obj is not None
        assert obj.co2e == pytest.approx(expected_def, rel=1e-5)


def test_recalc_partial_override_uses_compendium_defaults():
    """Updating only boiler_efficiency or trans_loss falls back to Compendium defaults for the other."""
    from types import SimpleNamespace

    with app.app_context():
        emission = SimpleNamespace(heat_mmbtu=820.0, co2e=53.06, steam_ton=0.0)
        fuel_ef = _steam_fuel_factor_kg_per_mmbtu(None)
        # Only transmission_loss overridden to 0.0 -> boiler_eff defaults to 0.92 (net 0.92)
        co2e_a, heat_a = _recalc_indirect_steam(
            emission, {"trans_loss": 0.0}, None, 820.0, 53.06, None
        )
        assert heat_a == pytest.approx(820.0)
        assert co2e_a == pytest.approx((820.0 / 0.92) * fuel_ef / 1000.0, rel=1e-5)

        # Only boiler_efficiency overridden to 0.80 -> trans_loss defaults to 0.10 (net 0.70)
        co2e_b, _ = _recalc_indirect_steam(
            emission, {"boiler_efficiency": 0.80}, None, 820.0, 53.06, None
        )
        assert co2e_b == pytest.approx((820.0 / 0.70) * fuel_ef / 1000.0, rel=1e-5)


def test_verified_factors_registry_scp2_004_005_compendium():
    """Seed metadata SCP2-004 and SCP2-005 reflect API Compendium 2021 §8.1.5 / Exhibit 8.3 (0.92 and 0.10)."""
    by_id = {f["id"]: f for f in ALL_VERIFIED_FACTORS}
    assert by_id["SCP2-004"]["value"] == pytest.approx(0.92)
    assert by_id["SCP2-005"]["value"] == pytest.approx(0.10)
    assert "API Compendium" in by_id["SCP2-004"]["source_document"]
    assert "API Compendium" in by_id["SCP2-005"]["source_document"]
    assert "8-17" in by_id["SCP2-004"]["page_number"] or "8-19" in by_id["SCP2-004"]["page_number"]
    assert "8-19" in by_id["SCP2-005"]["page_number"]
    assert len(by_id["SCP2-004"]["verbatim_citation"].split()) <= 35
    assert len(by_id["SCP2-005"]["verbatim_citation"].split()) <= 35
