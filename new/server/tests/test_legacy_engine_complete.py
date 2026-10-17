"""calculations/legacy_engine.py: the factor-math fallback behind the API 2021 dispatcher. The dispatcher is
replaced by a recorder where a test needs the fallback on its own. Fixed while testing: an unreadable factor
was taken as 0 (no emissions booked) and an unreadable HHV or density was ignored.
"""
import pytest

import calculations.legacy_engine as le

GWP = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}
FACTOR = {"co2": 50.0, "ch4": 1.0, "n2o": 0.1, "unit": "kg/m3"}


@pytest.fixture
def no_dispatch(monkeypatch):
    calls = []

    def record(process, inputs, factor_data, uncertainties, gwp_dict=None):
        calls.append((process, inputs))
        return None

    monkeypatch.setattr(le.api2021_dispatcher, "dispatch", record)
    return calls


@pytest.mark.parametrize("alias,process", [
    ("pneumatics", "pneumatic"), ("tanks", "tank"), ("mud degassing", "drilling"), ("well completions", "completions"),
    ("dehydrators", "dehydrator"), ("blowdowns", "venting"), ("liquid unloading", "unloading"),
    ("associated gas venting", "associated_gas_venting"), ("associated venting", "associated_gas_venting"),
    ("associated gas", "associated_gas_venting"),
])
def test_frontend_process_names(no_dispatch, alias, process):
    le._compute_emissions_impl({"process_type": alias, "amount": 1, "unit": "m3"}, dict(FACTOR), gwp_dict=GWP)
    assert no_dispatch[0][0] == process


@pytest.mark.parametrize("process,gases", [
    ("combustion", ("co2", "ch4", "n2o")), ("mobile", ("co2", "ch4", "n2o")), ("flaring", ("co2", "ch4", "n2o")),
    ("other_process", ("co2", "ch4", "n2o")),
    ("venting", ("co2", "ch4")), ("loading", ("co2", "ch4")), ("separation", ("co2", "ch4")),
    ("associated_gas_venting", ("co2", "ch4")), ("tank", ("co2", "ch4")), ("agr", ("co2", "ch4")),
    ("drilling", ("co2", "ch4")), ("completions", ("co2", "ch4")), ("unloading", ("co2", "ch4")),
    ("fugitive", ("ch4",)), ("pneumatic", ("ch4",)), ("dehydrator", ("ch4",)),
])
def test_fallback_gases_by_process(no_dispatch, process, gases):
    em, method = le._compute_emissions_impl({"process_type": process, "amount": 10, "unit": "m3"}, dict(FACTOR),
                                            gwp_dict=GWP)
    assert method == "server_default"
    expected = {g: (10 * FACTOR[g] / 1000 if g in gases else 0) for g in ("co2", "ch4", "n2o")}
    assert {g: em[g] for g in expected} == pytest.approx(expected)
    assert em["totalCo2e"] == pytest.approx(expected["co2"] + 28 * expected["ch4"] + 265 * expected["n2o"])


def test_custom_factor_fallback_keeps_every_gas(no_dispatch):
    em, method = le._compute_emissions_impl({"process_type": "fugitive", "amount": 10, "unit": "m3"},
                                            {**FACTOR, "type": "custom"}, gwp_dict=GWP)
    assert method == "server_custom_factor"
    assert (em["co2"], em["ch4"], em["n2o"]) == pytest.approx((0.5, 0.01, 0.001))


def test_catalog_hhv_reaches_the_dispatcher(no_dispatch):
    le._compute_emissions_impl({"process_type": "combustion", "amount": 1, "unit": "scf", "fuel": "Natural Gas"},
                               {"co2": 53.06, "unit": "kg/MMBtu", "hhv": 1020, "type": "gases"}, gwp_dict=GWP)
    assert no_dispatch[0][1]["hhv"] == 1020


def test_placeholder_hhv_is_no_hhv(no_dispatch):
    em, _ = le._compute_emissions_impl({"process_type": "venting", "amount": 10, "unit": "m3", "hhv": "-"},
                                       dict(FACTOR), gwp_dict=GWP)
    assert em["ch4"] == pytest.approx(0.01)


@pytest.mark.parametrize("payload,factor,match", [
    ({"hhv": "abc"}, dict(FACTOR), "Heating value"),
    ({"density": "heavy"}, dict(FACTOR), "fuel density"),
    ({}, {**FACTOR, "co2": "fifty"}, "Emission factor 'co2' is not a number"),
])
def test_unreadable_numbers_are_refused(no_dispatch, payload, factor, match):
    with pytest.raises(ValueError, match=match):
        le._compute_emissions_impl({"process_type": "combustion", "amount": 10, "unit": "m3", **payload}, factor,
                                   gwp_dict=GWP)


def test_density_reaches_the_dispatcher(no_dispatch):
    le._compute_emissions_impl({"process_type": "venting", "amount": 10, "unit": "m3", "density": "0.8"},
                               dict(FACTOR), gwp_dict=GWP)
    assert no_dispatch[0][1]["density"] == 0.8


def test_dispatcher_results_with_missing_gases(monkeypatch):
    monkeypatch.setattr(le.api2021_dispatcher, "dispatch",
                        lambda *a, **k: {"results": {"co2": None, "ch4": {"value": 2.0}, "n2o": 0.5}, "method": "x"})
    em, method = le._compute_emissions_impl({"process_type": "venting", "amount": 1, "unit": "m3"}, {}, gwp_dict=GWP)
    assert (em["co2"], em["ch4"], em["n2o"], method) == (0, 2.0, 0.5, "x")
    assert em["totalCo2e"] == pytest.approx(2.0 * 28 + 0.5 * 265)


def test_factor_conversion_helpers():
    assert le._convert_factor_to_kg(None, "kg/m3", "m3") == 0.0
    assert le._convert_factor_to_kg(2.0, "", "m3") == 2.0
    assert le._calculate_default_kg(10, "m3", {}, "co2") == 0.0
    assert le._calculate_default_kg(10, "m3", {"co2": -1}, "co2") == 0.0
    with pytest.raises(ValueError):
        le._convert_factor_to_kg(2.0, "kg/kWh", "gal")


def test_unreadable_catalog_density_is_refused(no_dispatch):
    with pytest.raises(ValueError, match="Fuel density is not a number"):
        le._compute_emissions_impl({"process_type": "combustion", "amount": 10, "unit": "m3"},
                                   {**FACTOR, "density": "dense"}, gwp_dict=GWP)
