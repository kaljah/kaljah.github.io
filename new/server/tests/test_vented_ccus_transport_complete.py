"""calculations/vented_ccus_transport.py beyond the exhibit tests: every activity, unit and refusal, with values
from API Compendium 2021 sections 6.9 / 6.10 (Equation 6-27, Tables 6-47 to 6-49). Without site data the CH4
share of the TOC is 15 % (the tables' footnotes; Exhibit 6-35's 12 % is that example's site value); the
capture rate, CO2 density and CO2 mass fraction have no default.
"""
import pytest

from calculations.vented_ccus_transport import CCUSVentingCalculator, CrudeTransportLossesCalculator


def val(res, gas):
    r = res["results"][gas]
    return (r or {}).get("value", 0.0) if isinstance(r, dict) or r is None else r


@pytest.fixture
def ccus():
    return CCUSVentingCalculator()


@pytest.fixture
def crude():
    return CrudeTransportLossesCalculator()


def test_stripper_vent_measured_and_percent_capture(ccus):
    m = ccus.calculate(activity="stripper_vent", vented_co2_tonnes=120, vented_ch4_tonnes=0.3)
    assert (val(m, "co2"), val(m, "ch4")) == pytest.approx((120, 0.3))
    pct = ccus.calculate(activity="stripper_vent", inlet_co2_tonnes=10_000, capture_efficiency=95)
    assert val(pct, "co2") == pytest.approx(500)


def test_wellhead_blowdown_eq_6_27(ccus):
    res = ccus.calculate(activity="wellhead_blowdown", physical_volume_m3=2.0, events=None, co2_density_kg_m3=800,
                         co2_weight_fraction=98.5)
    assert val(res, "co2") == pytest.approx(1 * 2.0 * 800 * 0.985 * 0.001)
    assert val(ccus.calculate(activity="wellhead_blowdown", physical_volume_m3=2.0, events=0, co2_density_kg_m3=800,
                              co2_weight_fraction=0.985), "co2") == 0


def test_monitoring_vent(ccus):
    res = ccus.calculate(activity="Monitoring_Vent", vented_co2_tonnes=4.2)
    assert val(res, "co2") == pytest.approx(4.2) and val(res, "ch4") == 0


@pytest.mark.parametrize("kwargs,match", [
    (dict(activity="stripper_vent"), "inlet_co2_tonnes or vented_co2_tonnes"),
    (dict(activity="stripper_vent", inlet_co2_tonnes=100), "capture efficiency"),
    (dict(activity="wellhead_blowdown", physical_volume_m3=1, co2_weight_fraction=0.98), "co2_density_kg_m3"),
    (dict(activity="wellhead_blowdown", physical_volume_m3=1, co2_density_kg_m3=650), "co2_weight_fraction"),
    (dict(activity="leak"), "Unknown CCUS activity"),
])
def test_ccus_refusals(ccus, kwargs, match):
    with pytest.raises(ValueError, match=match):
        ccus.calculate(**kwargs)


@pytest.mark.parametrize("service,ef", [("submerged_dedicated", 0.91), ("submerged_vapor_balance", 1.51),
                                        ("splash_dedicated", 2.20), ("splash_vapor_balance", 1.51),
                                        ("marine_ships", 0.28), ("Marine_Barges", 0.45)])
def test_loading_table_6_47_default_ch4_share(crude, service, ef):
    res = crude.calculate(activity="loading", loading_service=service, volume_loaded_gal=1_000_000)
    assert res["inputs"]["total_toc_tonnes"] == pytest.approx(ef)
    assert val(res, "ch4") == pytest.approx(ef * 0.15)                      # 15 % without site data


def test_ch4_share_is_percent(crude):
    res = crude.calculate(activity="loading", volume_loaded_bbl=1000, ch4_weight_pct=0.5)
    assert val(res, "ch4") == pytest.approx(1000 * 42 / 1e6 * 2.20 * 0.005)   # 0.5 %, not 50 %


@pytest.mark.parametrize("cond,ef", [("fully_loaded", 0.420), ("lightered", 0.647), ("typical", 0.488)])
def test_ballasting_table_6_48(crude, cond, ef):
    res = crude.calculate(activity="ballasting", ballast_condition=cond, ballast_water_gal=2_000_000, ch4_weight_pct=10)
    assert val(res, "ch4") == pytest.approx(2 * ef * 0.10)


def test_transit_table_6_49_trips_and_zeroes(crude):
    res = crude.calculate(activity="transit", volume_transported_bbl=100_000, trip_duration_days=21, trips_per_year=4)
    assert val(res, "ch4") == pytest.approx(0.57 * 4.2 * 3 * 4 * 0.15)
    assert val(crude.calculate(activity="transit", volume_transported_bbl=100_000, trip_duration_days=21,
                               trips_per_year=0), "ch4") == 0
    assert val(crude.calculate(activity="transit", volume_transported_bbl=100_000, trip_duration_days=0), "ch4") == 0


def test_control_efficiency(crude):
    res = crude.calculate(activity="loading", volume_loaded_gal=1_000_000, control_efficiency=95)
    assert val(res, "ch4") == pytest.approx(2.20 * 0.15 * 0.05)


@pytest.mark.parametrize("kwargs,match", [
    (dict(activity="loading"), "volume_loaded_bbl or volume_loaded_gal"),
    (dict(activity="loading", volume_loaded_gal=1, loading_service="pipeline"), "Unknown loading service"),
    (dict(activity="ballasting"), "ballast_water_bbl or ballast_water_gal"),
    (dict(activity="ballasting", ballast_water_gal=1, ballast_condition="half"), "Unknown ballast condition"),
    (dict(activity="transit", volume_transported_bbl=10), "trip_duration_days"),
    (dict(activity="transit", trip_duration_days=3), "volume_transported_bbl"),
    (dict(activity="storage"), "Unknown crude transport activity"),
])
def test_transport_refusals(crude, kwargs, match):
    with pytest.raises(ValueError, match=match):
        crude.calculate(**kwargs)
