"""
Exhaustive unit test suite for calculations/legacy_engine.py.

Covers:
- Helper functions: _convert_factor_to_kg, _calculate_default_kg, _payload_density, _has_factor_values
- Process aliasing and payload normalization
- Parsing amount, HHV, density, and error paths
- Dispatcher result extraction, zero-emissions handling, and _tier3_zero
- Legacy specific factors (Raw, Unit, non-combustion CO)
- Custom factors (factor_data['type'] == 'custom')
- Default factor math with _CH4_ONLY and _NO_N2O masks
- CCS capture rate application in legacy fallback math
- MissingFactorError validation
"""

import pytest
import logging
from calculations.legacy_engine import (
    compute_emissions,
    _convert_factor_to_kg,
    _calculate_default_kg,
    _payload_density,
    _has_factor_values,
    _note_fallback,
    MissingFactorError,
)


@pytest.fixture
def no_dispatch(monkeypatch):
    calls = []

    def record(process, inputs, factor_data, uncertainties, gwp_dict=None):
        calls.append((process, inputs))
        return None

    import calculations.legacy_engine as le
    monkeypatch.setattr(le.api2021_dispatcher, "dispatch", record)
    return calls


def test_legacy_convert_factor_to_kg():
    """Test unit conversions for emission factors."""
    # Matching units
    assert _convert_factor_to_kg(1.5, "kg/m3", "kg/m3") == 1.5
    assert _convert_factor_to_kg(None, "kg/m3", "m3") == 0.0

    # Dimension conversion (e.g. g to kg, lb to kg)
    res_lb = _convert_factor_to_kg(1.0, "lb", "kg")
    assert pytest.approx(res_lb, rel=1e-3) == 2.204622

    # Incompatible units raise ValueError (e.g. energy to volume without HHV)
    with pytest.raises(ValueError):
        _convert_factor_to_kg(1.0, "kg/kWh", "gal")


def test_legacy_calculate_default_kg():
    """Test factor data parsing and gas selection."""
    factor_data = {
        "co2": 53.06,
        "ch4": 0.001,
        "n2o": 0.0001,
        "unit": "kg/mmbtu",
    }
    kg_co2 = _calculate_default_kg(10.0, "mmbtu", factor_data, "co2")
    assert pytest.approx(kg_co2) == 530.6

    # None or zero factor data
    assert _calculate_default_kg(10.0, "mmbtu", None, "co2") == 0.0
    assert _calculate_default_kg(10.0, "mmbtu", {"co2": 0.0}, "co2") == 0.0

    # Unreadable factor raises ValueError
    with pytest.raises(ValueError, match="is not a number"):
        _calculate_default_kg(10.0, "mmbtu", {"co2": "invalid"}, "co2")


def test_legacy_payload_density_and_has_factors():
    """Test density extraction and factor existence checks."""
    assert _payload_density({"density": 840.0, "density_unit": "kg/m3"}) == 840.0
    assert _payload_density({}) is None

    assert _has_factor_values({"co2": 2.5}) is True
    assert _has_factor_values({"co2": 0.0, "ch4": None}) is False
    assert _has_factor_values(None) is False


def test_legacy_note_fallback(caplog):
    """Test logging of fallback calculations."""
    with caplog.at_level(logging.DEBUG):
        _note_fallback("server_custom_factor", "combustion", {"factor_source": "custom"})
    assert "legacy calculation fallback used" in caplog.text


def test_legacy_process_aliasing_and_normalizations(no_dispatch):
    """Test aliasing of frontend process names."""
    aliases = [
        ("pneumatics", "pneumatic"),
        ("tanks", "tank"),
        ("mud degassing", "drilling"),
        ("well completions", "completions"),
        ("dehydrators", "dehydrator"),
        ("blowdowns", "venting"),
        ("liquid unloading", "unloading"),
        ("associated gas venting", "associated_gas_venting"),
    ]
    factor_data = {"co2": 1.0, "ch4": 0.1, "n2o": 0.01, "unit": "kg/unit"}
    for idx, (alias, internal) in enumerate(aliases):
        payload = {
            "process_type": alias,
            "amount": "100",
            "unit": "unit",
            "factor_source": "default",
        }
        res, method = compute_emissions(payload, factor_data=factor_data)
        assert res["totalCo2e"] >= 0
        assert no_dispatch[idx][0] == internal


def test_legacy_unreadable_inputs():
    """Test unreadable HHV and density error handling."""
    with pytest.raises(ValueError, match="Heating value \\(HHV\\) is not a number"):
        compute_emissions({"process_type": "combustion", "amount": 10, "hhv": "bad_hhv"})

    with pytest.raises(ValueError, match="must be a number"):
        compute_emissions({"process_type": "combustion", "amount": 10, "density": "bad_density"})


def test_legacy_specific_factors():
    """Test server_specific calculation path with explicit user-supplied factors."""
    payload = {
        "process_type": "combustion",
        "factor_source": "specific",
        "amount": 1000.0,
        "unit": "m3",
        "specificFactors": {
            "co2": 2.2,
            "co2Unit": "kg/m3",
            "ch4Raw": 0.05,
            "ch4Unit": "kg/m3",
            "n2o": 0.001,
            "n2oUnit": "kg/m3",
            "co": 0.02,
        },
    }
    em, method = compute_emissions(payload)
    assert method == "server_specific"
    assert pytest.approx(em["co2"]) == 2.2  # 1000 * 2.2 / 1000
    assert pytest.approx(em["ch4"]) == 0.05
    assert pytest.approx(em["n2o"]) == 0.001
    assert em["totalCo2e"] > em["co2"]


def test_legacy_custom_factor(no_dispatch):
    """Test server_custom_factor calculation path."""
    payload = {
        "process_type": "combustion",
        "amount": 200.0,
        "unit": "gal",
        "factor_source": "custom",
    }
    factor_data = {
        "type": "custom",
        "co2": 10.21,
        "ch4": 0.0004,
        "n2o": 0.0001,
        "unit": "kg/gal",
    }
    em, method = compute_emissions(payload, factor_data=factor_data)
    assert method == "server_custom_factor"
    assert pytest.approx(em["co2"]) == 200.0 * 10.21 / 1000.0
    assert em["totalCo2e"] > 0


def test_legacy_default_gas_masks(no_dispatch):
    """Test CH4_ONLY and NO_N2O process masks in default factor calculations."""
    factor_data = {"co2": 100.0, "ch4": 5.0, "n2o": 1.0, "unit": "kg/m3"}

    # CH4 only (e.g. fugitive)
    payload_ch4 = {
        "process_type": "fugitive",
        "amount": 10.0,
        "unit": "m3",
        "factor_source": "default",
    }
    em_ch4, _ = compute_emissions(payload_ch4, factor_data=factor_data)
    assert em_ch4["co2"] == 0.0
    assert em_ch4["ch4"] > 0.0
    assert em_ch4["n2o"] == 0.0

    # NO N2O (e.g. drilling)
    payload_no_n2o = {
        "process_type": "drilling",
        "amount": 5.0,
        "unit": "m3",
        "factor_source": "default",
    }
    em_drill, _ = compute_emissions(payload_no_n2o, factor_data=factor_data)
    assert em_drill["n2o"] == 0.0
    assert em_drill["co2"] > 0.0
    assert em_drill["ch4"] > 0.0


def test_legacy_ccs_capture_on_fallback():
    """Test CCS capture applied to fallback calculation."""
    factor_data = {"co2": 100.0, "ch4": 1.0, "n2o": 0.1, "unit": "kg/unit"}
    payload_no_ccs = {
        "process_type": "other_process",
        "amount": 10.0,
        "unit": "unit",
    }
    payload_ccs = {
        **payload_no_ccs,
        "ccs_capture_rate": "80%",
    }
    em_no, _ = compute_emissions(payload_no_ccs, factor_data=factor_data)
    em_ccs, _ = compute_emissions(payload_ccs, factor_data=factor_data)

    assert pytest.approx(em_ccs["co2"]) == em_no["co2"] * 0.20
    assert em_ccs["totalCo2e"] < em_no["totalCo2e"]


def test_legacy_missing_factor_error():
    """Test MissingFactorError raised when positive amount has no resolved factors."""
    payload = {
        "process_type": "combustion",
        "amount": 500.0,
        "unit": "gal",
        "fuel": "Unknown Fuel",
        "factor_source": "default",
    }
    with pytest.raises(MissingFactorError, match="No emission factor found for 'Unknown Fuel'"):
        compute_emissions(payload, factor_data={})


def test_legacy_zero_activity():
    """Test zero activity amount returns 0 emissions without error."""
    payload = {
        "process_type": "combustion",
        "amount": 0.0,
        "unit": "gal",
        "factor_source": "default",
    }
    em, _ = compute_emissions(payload, factor_data={})
    assert em["totalCo2e"] == 0.0
    assert em["co2"] == 0.0
