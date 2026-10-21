"""2026-10-22: an entered efficiency on unloading, blowdown, tank and dehydrator rows is the flare's efficiency (it was
the share sent to a 98 % flare), and steam net efficiency is boiler efficiency - transmission loss (API Compendium
2021 Exhibit 8.3; it was boiler x (1 - loss))."""
import pytest

from calculations.dispatcher import CalculationDispatcher
from calculations.indirect import IndirectSteamCalculator


@pytest.fixture
def d():
    return CalculationDispatcher()


def _v(res, gas):
    r = res["results"][gas]
    return r["value"] if isinstance(r, dict) else r


@pytest.mark.parametrize("inputs,share,eff", [
    ({}, 0.0, None),
    ({"control_efficiency": 0}, 0.0, None),                                   # "0 = Vented" on the forms
    ({"control_efficiency": 98}, 1.0, 0.98),                                  # all to a flare burning at 98 %
    ({"control_efficiency": 90, "disposition": "Flared"}, 1.0, 0.90),
    ({"disposition": "flared"}, 1.0, None),                                   # the defaults (98 % / 96.5 %)
    ({"disposition": "vented"}, 0.0, None),
    ({"control_efficiency": 40, "disposition": "vented"}, 0.4, None),          # that share to a default flare
])
def test_controlled_share_is_share_and_efficiency(d, inputs, share, eff):
    got_share, got_eff = d._controlled_share(inputs, ["control_efficiency"])
    assert got_share == pytest.approx(share)
    assert got_eff == (None if eff is None else pytest.approx(eff))


def test_controlled_share_refuses_recovered(d):
    with pytest.raises(ValueError, match="'recovered' is not available for this process: vented or flared"):
        d._controlled_share({"disposition": "recovered", "control_efficiency": 50}, ["control_efficiency"])


def test_blowdown_flare_efficiency_is_the_flares(d):
    base = {"factor_source": "specific", "blowdown_volume": 100, "blowdown_unit": "m3", "pressure": 500,
            "events": 10, "ch4_content": 90}
    vented = _v(d.dispatch("blowdown", base, {}, {}), "ch4")
    flared = _v(d.dispatch("blowdown", {**base, "control_efficiency": 98}, {}, {}), "ch4")
    assert flared == pytest.approx(vented * 0.02)                             # it was 0.02 + 0.98 x 0.02
    at_90 = _v(d.dispatch("blowdown", {**base, "control_efficiency": 90}, {}, {}), "ch4")
    assert at_90 == pytest.approx(vented * 0.10)


def test_tank_flare_efficiency_is_the_flares(d):
    tank = {"factor_source": "specific", "throughput": 1000, "amount": 1000, "unit": "bbl", "method": "table_6_22"}
    vented = _v(d.dispatch("tank_flashing", tank, {}, {}), "ch4")
    at_95 = d.dispatch("tank_flashing", {**tank, "tank_control_eff": 95}, {}, {})
    assert _v(at_95, "ch4") == pytest.approx(vented * 0.05)
    default = d.dispatch("tank_flashing", {**tank, "disposition": "flared"}, {}, {})
    assert _v(at_95, "co2") < _v(default, "co2")                              # 95 % vs 96.5 % carbon to CO2


def test_unloading_flare_efficiency_is_the_flares(d):
    unload = {"factor_source": "default", "amount": 10, "unit": "events", "unloading_type": "without_plunger",
              "ch4_content": 80, "well_count": 1}
    vented = _v(d.dispatch("unloading", unload, {}, {}), "ch4")
    at_99 = _v(d.dispatch("unloading", {**unload, "unload_flare_eff": 99}, {}, {}), "ch4")
    assert at_99 == pytest.approx(vented * 0.01)


def test_dehydrator_flared_and_device_efficiency(d):
    base = {"factor_source": "specific", "dehy_throughput": 100, "ch4_content": 78.8}
    open_vent = _v(d.dispatch("dehydrator", base, {}, {}), "ch4")
    assert open_vent == pytest.approx(100 * 0.0052859)                        # Table 6-17
    flared = _v(d.dispatch("dehydrator", {**base, "disposition": "flared"}, {}, {}), "ch4")
    assert flared == pytest.approx(open_vent * 0.02)                          # it was cut to 0
    condenser = _v(d.dispatch("dehydrator", {**base, "dehy_eff": 60}, {}, {}), "ch4")
    assert condenser == pytest.approx(open_vent * 0.40)


# ---------------------------------------------------------------- steam: API Compendium 2021 Exhibit 8.3
def test_exhibit_8_3_steam():
    """15 million lb of 600 psig / 700 F steam (1350 - 180 Btu/lb), natural-gas boiler at 92 %, 10 % transport
    loss: 1,263 t CO2, 0.0235 t CH4 and 0.0064 t N2O."""
    res = IndirectSteamCalculator().calculate(
        heat_energy=15e6, heat_unit="lb", steam_enthalpy_btu_lb=1350 - 180, ef_co2=59.0, ef_ch4=1.1e-3,
        ef_n2o=3.0e-4, boiler_efficiency=0.92, transmission_loss=0.10, uncertainties={})
    assert _v(res, "co2") == pytest.approx(1263, abs=0.5)
    assert _v(res, "ch4") == pytest.approx(0.0235, abs=5e-5)
    assert _v(res, "n2o") == pytest.approx(0.0064, abs=5e-5)


@pytest.mark.parametrize("loss", [0.80, 0.95])
def test_steam_loss_at_or_above_the_boiler_efficiency_refused(loss):
    with pytest.raises(ValueError, match="Net efficiency must be greater than 0"):
        IndirectSteamCalculator().calculate(heat_energy=100, heat_unit="mmbtu", ef_co2=53.06, boiler_efficiency=0.80,
                                            transmission_loss=loss, uncertainties={})


def test_scope2_route_steam_uses_exhibit_8_3():
    from routes.scope2 import _calc_indirect_steam

    co2e, heat, _ = _calc_indirect_steam({"amount": 1000, "unit": "mmbtu", "boiler_efficiency": 92,
                                          "calc_inputs": {"indirect_steam": {"trans_loss": 0.10, "ef_co2": 59.0}}})
    assert heat == pytest.approx(1000)
    assert co2e == pytest.approx(1000 / 0.82 * 59.0 / 1000, rel=2e-3)        # CH4 / N2O of Table 4-6 are small
