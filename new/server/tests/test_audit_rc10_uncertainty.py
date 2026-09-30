"""RC-10 inventory uncertainty regressions (BUG-008/018/025/037/043/055).

Hand values: a record with EF 5 % and AD 10 % (95 % half-widths) has 1-sigma components
u_EF = 0.025, u_AD = 0.05 (IPCC 2006 Vol.1 Eq. 3.1, k = 2)."""
import math

import pytest

from extensions import db
from models import Emission
from services.inventory_uncertainty import inventory_uncertainty
from tests.audit_helpers import login, make_facility, make_user


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def _rec(fac, year, co2, u_ad=0.05, u_ef=0.025, key="catalog:Natural Gas", status="Verified"):
    e = Emission(facility_id=fac.id, year=year, month=1, process_type="combustion", fuel_type="Natural Gas",
                 co2_emissions=co2, ch4_emissions=0.0, n2o_emissions=0.0, co2e_total=co2, status=status,
                 uncertainty=math.hypot(u_ad, u_ef), uncertainty_ad=u_ad, uncertainty_ef_co2=u_ef, ef_key=key)
    db.session.add(e)
    return e


def test_bug008_ef_part_is_correlated_across_records(ctx):
    f = make_facility(region="West")
    for m in range(12):
        _rec(f, 2013, 10.0)
    _rec(make_facility(region="West"), 2014, 120.0)
    db.session.commit()
    split = inventory_uncertainty(2013, facility_id=f.id)
    # EF fully correlated (0.025 x E), AD independent (0.05 x E_i): sqrt(0.025^2 + 0.05^2/12)
    assert split["inventory_uncertainty_1sigma"] == pytest.approx(math.sqrt(0.025 ** 2 + 0.05 ** 2 / 12))
    # without correlation the old code gave sqrt(0.025^2+0.05^2)/sqrt(12): the EF part must not shrink
    assert split["inventory_uncertainty_1sigma"] > 0.025


def test_bug008_single_record(ctx):
    f = make_facility(region="West")
    _rec(f, 2015, 120.0)
    db.session.commit()
    r = inventory_uncertainty(2015, facility_id=f.id)
    assert r["inventory_uncertainty_decimal"] == pytest.approx(2 * math.hypot(0.025, 0.05))  # 11.18 %


def test_bug018_co2e_weighted_by_gas(ctx):
    """1 t CO2 (u_EF 0.025) + 0.1 t CH4 x 28 = 2.8 t (u_EF 0.30): no max-of-gases."""
    from calculations.constants import get_active_gwp

    g = get_active_gwp(horizon="100")["CH4"]
    f = make_facility(region="West")
    db.session.add(Emission(facility_id=f.id, year=2016, month=1, process_type="combustion", fuel_type="x",
                            co2_emissions=1.0, ch4_emissions=0.1, n2o_emissions=0, co2e_total=1.0 + 0.1 * g,
                            status="Verified", uncertainty_ad=0.0001, uncertainty_ef_co2=0.025, uncertainty_ef_ch4=0.30,
                            uncertainty=0.025, uncertainty_ch4=0.30, ef_key="k18"))
    db.session.commit()
    r = inventory_uncertainty(2016, facility_id=f.id)
    e = 1.0 + 0.1 * g
    expected = math.sqrt((0.025 * 1.0) ** 2 + (0.30 * 0.1 * g) ** 2 + (0.0001 * e) ** 2) / e
    assert r["inventory_uncertainty_1sigma"] == pytest.approx(expected)
    assert r["inventory_uncertainty_1sigma"] < 0.30  # not the max of the gases


def test_bug043_out_of_range_stored_values_flagged(ctx):
    f = make_facility(region="West")
    db.session.add(Emission(facility_id=f.id, year=2017, month=1, process_type="combustion", co2_emissions=5.0,
                            co2e_total=5.0, status="Verified", uncertainty=36.0))
    db.session.commit()
    r = inventory_uncertainty(2017, facility_id=f.id)
    assert r["records_with_invalid_uncertainty"] >= 1
    assert r["inventory_uncertainty_decimal"] < 1.0  # not +/-3600 %


def test_bug025_meter_and_gc_overrides_applied():
    from calculations.legacy_engine import compute_emissions

    base = {"process_type": "stationary_combustion", "fuel": "Natural Gas", "unit": "m3", "factor_source": "default",
            "quantity": 1000, "amount": 1000}
    from routes.emissions import _lookup_api_factor

    fd = _lookup_api_factor("Natural Gas")
    u0 = compute_emissions(dict(base), fd)[0]["_full_api_res"]["results"]["co2"]["uncertainty"]
    u1 = compute_emissions(dict(base, meter_uncertainty_pct=40), fd)[0]["_full_api_res"]["results"]["co2"]["uncertainty"]
    u2 = compute_emissions(dict(base, meter_uncertainty_pct=40, gc_uncertainty_pct=30), fd)[0]["_full_api_res"]["results"]["co2"]["uncertainty"]
    assert u0 == pytest.approx(math.hypot(0.025, 0.05))
    assert u1 == pytest.approx(math.hypot(0.025, 0.20))
    assert u2 == pytest.approx(math.sqrt(0.025 ** 2 + 0.20 ** 2 + 0.15 ** 2))


def test_bug055_qa_card_equals_uncertainty_page(client, ctx):
    f = make_facility(region="West")
    _rec(f, 2018, 50.0)
    _rec(f, 2018, 999.0, status="Pending")  # excluded from both
    db.session.commit()
    login(client, make_user("admin", "Global"))
    page = client.get(f"/api/dashboard/uncertainty?year=2018").get_json()
    qa = client.get(f"/api/qaqc/dashboard?year=2018").get_json()["tier1_uncertainty"]
    assert qa["overall"] == pytest.approx(page["inventory_uncertainty_decimal"])
    assert qa["confidence_level_pct"] == 95
