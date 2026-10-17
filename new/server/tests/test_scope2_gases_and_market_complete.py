"""Exhaustive test suite for Scope 2 calculation engines, market instruments, gas splits, and indirect energy.

Covers:
- services/scope2_gases.py (_grid, gas_split, list_row_gases, yearly_totals, record_totals)
- services/scope2_market.py (is_zero_emission_instrument, contractual_factor, market_factor)
- routes/scope2.py (resolve_electricity_factor, default_scope2_uncertainty, _calc_indirect_steam,
                    _steam_fuel_factor_kg_per_mmbtu, _recalc_indirect_steam, _calc_cogen_allocation)
- Cooling and heat calculations across multiple engineering units.
"""
from types import SimpleNamespace
import pytest
from extensions import db
from input_validation import ValidationError
from models import Scope2Emission, Facility
from tests.audit_helpers import login, make_facility, make_user, uniq
from services.scope2_gases import (
    _grid,
    gas_split,
    list_row_gases,
    yearly_totals,
    record_totals,
)
from services.scope2_market import (
    ZERO_EMISSION_INSTRUMENTS,
    is_zero_emission_instrument,
    contractual_factor,
    market_factor,
)
from routes.scope2 import (
    resolve_electricity_factor,
    default_scope2_uncertainty,
    _calc_indirect_steam,
    _steam_fuel_factor_kg_per_mmbtu,
    _recalc_indirect_steam,
    _calc_cogen_allocation,
    _DEFAULT_BOILER_EF_KG_PER_MMBTU,
    MAX_GRID_EF_KG_PER_KWH,
)
from electricity_factors import GRID_FACTORS, grid_entry, grid_factor_kg_co2e_per_kwh
from calculations.constants import get_active_gwp
from services.dashboard_filters import gwp_pair


# ---------------------------------------------------------------------------
# services/scope2_market.py Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("instr", [
    "rec", "REC", "  rec  ", "ppa_zero", "PPA_ZERO", "go_zero",
    "renewable_ppa", "RENEWABLE_PPA", "green_tariff_zero", "GREEN_TARIFF_ZERO"
])
def test_is_zero_emission_instrument_valid(instr):
    assert is_zero_emission_instrument(instr) is True


@pytest.mark.parametrize("instr", [
    None, "", "   ", "ppa", "standard_ppa", "grid", "fossil", "unknown", 123
])
def test_is_zero_emission_instrument_invalid(instr):
    assert is_zero_emission_instrument(instr) is False


def test_contractual_factor_zero_emission_success():
    for instr in ZERO_EMISSION_INSTRUMENTS:
        assert contractual_factor(instr, None) == 0.0
        assert contractual_factor(instr, "") == 0.0
        assert contractual_factor(instr, 0) == 0.0
        assert contractual_factor(instr, "0.0") == 0.0


def test_contractual_factor_zero_emission_contradiction_raises():
    for instr in ("REC", "ppa_zero", "renewable_ppa"):
        with pytest.raises(ValidationError) as exc:
            contractual_factor(instr, 0.15)
        assert exc.value.field == "market_emission_factor"
        assert "cannot have a supplier emission factor" in exc.value.message


def test_contractual_factor_supplier_specific():
    assert contractual_factor("standard_ppa", 0.35) == 0.35
    assert contractual_factor(None, "0.42") == 0.42
    assert contractual_factor("", 0.28) == 0.28


def test_contractual_factor_fallback_to_none():
    assert contractual_factor("standard_ppa", None) is None
    assert contractual_factor(None, None) is None
    assert contractual_factor("", "") is None


def test_market_factor_exhaustive():
    # 1. Zero-emission instrument -> market factor is 0.0, stored is 0.0
    fac, stored = market_factor(0.65, "REC", None)
    assert fac == 0.0 and stored == 0.0

    # 2. Supplier factor provided -> market factor is supplier, stored is supplier
    fac, stored = market_factor(0.65, "supplier_ppa", 0.25)
    assert fac == 0.25 and stored == 0.25

    # 3. Fallback to location-based grid factor -> market factor is location, stored is None
    fac, stored = market_factor(0.65, None, None)
    assert fac == 0.65 and stored is None

    # 4. Fallback with None location_ef defaults to 0.0
    fac, stored = market_factor(None, None, None)
    assert fac == 0.0 and stored is None


# ---------------------------------------------------------------------------
# services/scope2_gases.py Tests
# ---------------------------------------------------------------------------

def test_grid_helper():
    # Non-electricity source
    e1 = SimpleNamespace(source_type="steam", grid_region="Algerian National Grid", electricity_kwh=1000)
    assert _grid(e1) is None

    # None source_type
    e2 = SimpleNamespace(source_type=None, grid_region="Algerian National Grid", electricity_kwh=1000)
    assert _grid(e2) is None

    # Missing grid_region
    e3 = SimpleNamespace(source_type="electricity", grid_region=None, electricity_kwh=1000)
    assert _grid(e3) is None

    # Missing or zero electricity_kwh
    e4 = SimpleNamespace(source_type="electricity", grid_region="Algerian National Grid", electricity_kwh=0)
    assert _grid(e4) is None

    # Valid grid electricity
    e5 = SimpleNamespace(source_type="electricity", grid_region="Algerian National Grid", electricity_kwh=5000)
    res = _grid(e5)
    assert res is not None
    assert "co2" in res and "ch4" in res and "n2o" in res


def test_gas_split_non_grid():
    # Steam or supplier without grid region
    e = SimpleNamespace(source_type="steam", grid_region=None, electricity_kwh=None, co2e=12.5)
    split = gas_split(e)
    assert split == {"co2": 12.5, "ch4": 0.0, "n2o": 0.0}

    # None co2e
    e2 = SimpleNamespace(source_type="steam", grid_region=None, electricity_kwh=None, co2e=None)
    split2 = gas_split(e2)
    assert split2 == {"co2": 0.0, "ch4": 0.0, "n2o": 0.0}


def test_gas_split_grid_math():
    region = "Algerian National Grid"
    entry = grid_entry(region)[1]
    kwh = 100_000.0
    e = SimpleNamespace(source_type="electricity", grid_region=region, electricity_kwh=kwh, co2e=50.0)
    split = gas_split(e)

    assert split["co2"] == pytest.approx(kwh * entry["co2"] / 1000.0)
    assert split["ch4"] == pytest.approx(kwh * entry["ch4"] / 1000.0)
    assert split["n2o"] == pytest.approx(kwh * entry["n2o"] / 1000.0)


def test_list_row_gases_exact_match():
    region = "Algerian National Grid"
    entry = grid_entry(region)[1]
    gwp = get_active_gwp()
    kwh = 50_000.0
    co2 = kwh * entry["co2"] / 1000.0
    ch4 = kwh * entry["ch4"] / 1000.0
    n2o = kwh * entry["n2o"] / 1000.0
    expected_co2e = co2 + ch4 * float(gwp["CH4"]) + n2o * float(gwp["N2O"])

    row = SimpleNamespace(fuel=region, amount=kwh, co2e_total=expected_co2e)
    res = list_row_gases(row)

    assert res["co2_emissions"] == pytest.approx(co2)
    assert res["ch4_emissions"] == pytest.approx(ch4)
    assert res["n2o_emissions"] == pytest.approx(n2o)


def test_list_row_gases_mismatch_fallback():
    # If the stored CO2e does not match grid split (e.g. customized factor), fall back to CO2 only
    row = SimpleNamespace(fuel="Algerian National Grid", amount=50_000.0, co2e_total=100.0)
    res = list_row_gases(row)
    assert res["co2_emissions"] == 100.0
    assert res["ch4_emissions"] == 0.0
    assert res["n2o_emissions"] == 0.0


def test_record_totals_gwp_horizons():
    region = "Algerian National Grid"
    entry = grid_entry(region)[1]
    kwh = 10_000.0
    co2e_loc = 5.5

    # Case 1: Horizon 100, market-based is None (fallback to location)
    e1 = SimpleNamespace(
        source_type="electricity", grid_region=region, electricity_kwh=kwh,
        co2e=co2e_loc, co2e_market_based=None
    )
    loc, mkt = record_totals(e1, horizon="100")
    assert loc == 5.5
    assert mkt == 5.5

    # Case 2: Horizon 100, market-based is 0.0 (REC)
    e2 = SimpleNamespace(
        source_type="electricity", grid_region=region, electricity_kwh=kwh,
        co2e=co2e_loc, co2e_market_based=0.0
    )
    loc, mkt = record_totals(e2, horizon="100")
    assert loc == 5.5
    assert mkt == 0.0

    # Case 3: Horizon 20, market-based is None
    c100, n100 = gwp_pair("100")
    c20, n20 = gwp_pair("20")
    delta = kwh * (entry["ch4"] * (c20 - c100) + entry["n2o"] * (n20 - n100)) / 1000.0

    loc20, mkt20 = record_totals(e1, horizon="20")
    assert loc20 == pytest.approx(co2e_loc + delta)
    assert mkt20 == pytest.approx(co2e_loc + delta)

    # Case 4: Horizon 20, market-based is 0.0 (REC remains 0.0, delta not added to user contractual market value)
    loc20_rec, mkt20_rec = record_totals(e2, horizon="20")
    assert loc20_rec == pytest.approx(co2e_loc + delta)
    assert mkt20_rec == 0.0


def test_yearly_totals_aggregation():
    class MockQuery:
        def __init__(self, records):
            self.records = records
        def all(self):
            return self.records

    records = [
        SimpleNamespace(year=2024, facility_id=1, source_type="steam", grid_region=None,
                        electricity_kwh=0, co2e=10.0, co2e_market_based=None),
        SimpleNamespace(year=2024, facility_id=1, source_type="electricity", grid_region="Algerian National Grid",
                        electricity_kwh=10_000, co2e=5.0, co2e_market_based=0.0),
        SimpleNamespace(year=2024, facility_id=2, source_type="steam", grid_region=None,
                        electricity_kwh=0, co2e=20.0, co2e_market_based=15.0),
        SimpleNamespace(year=2025, facility_id=1, source_type="electricity", grid_region="Algerian National Grid",
                        electricity_kwh=20_000, co2e=10.0, co2e_market_based=None),
    ]

    # Aggregated by total
    tot = yearly_totals(MockQuery(records), by_fac=False, horizon="100")
    assert tot[(2024, "total")]["location"] == pytest.approx(10.0 + 5.0 + 20.0)
    assert tot[(2024, "total")]["market"] == pytest.approx(10.0 + 0.0 + 15.0)
    assert tot[(2024, "total")]["energy"] == pytest.approx(10_000.0)

    assert tot[(2025, "total")]["location"] == pytest.approx(10.0)
    assert tot[(2025, "total")]["market"] == pytest.approx(10.0)
    assert tot[(2025, "total")]["energy"] == pytest.approx(20_000.0)

    # Aggregated by facility
    tot_fac = yearly_totals(MockQuery(records), by_fac=True, horizon="100")
    assert tot_fac[(2024, 1)]["location"] == pytest.approx(15.0)
    assert tot_fac[(2024, 1)]["market"] == pytest.approx(10.0)
    assert tot_fac[(2024, 2)]["location"] == pytest.approx(20.0)
    assert tot_fac[(2024, 2)]["market"] == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# routes/scope2.py Helper & Calculation Tests
# ---------------------------------------------------------------------------

def test_resolve_electricity_factor_known_grid():
    factor, name = resolve_electricity_factor("Algerian National Grid", None)
    entry = grid_entry("Algerian National Grid")[1]
    expected_ef = grid_factor_kg_co2e_per_kwh(entry)
    assert factor == pytest.approx(expected_ef)
    assert name == "Algerian National Grid"


def test_resolve_electricity_factor_supplier():
    factor, name = resolve_electricity_factor("CleanPower Inc.", 0.125)
    assert factor == 0.125
    assert name == "CleanPower Inc."


def test_resolve_electricity_factor_unknown_without_ef_raises():
    with pytest.raises(ValidationError) as exc:
        resolve_electricity_factor("Unknown Grid Region", None)
    assert exc.value.field == "grid_region"
    assert "valid_regions" in exc.value.extra


def test_resolve_electricity_factor_out_of_bounds():
    with pytest.raises(ValidationError):
        resolve_electricity_factor("CleanPower", -0.01)
    with pytest.raises(ValidationError):
        resolve_electricity_factor("CleanPower", MAX_GRID_EF_KG_PER_KWH + 0.5)


def test_default_scope2_uncertainty():
    unc = default_scope2_uncertainty(100.0)
    assert 0.02 < unc < 0.04  # ~2.69% at 1-sigma


def test_steam_fuel_factor_kg_per_mmbtu():
    # Custom factor in kg/MMBtu
    assert _steam_fuel_factor_kg_per_mmbtu(60.0) == 60.0

    # Custom factor in t/MMBtu (< 1.0 -> multiplied by 1000)
    assert _steam_fuel_factor_kg_per_mmbtu(0.065) == 65.0

    # Default factor includes AP-42 natural gas CH4 and N2O
    default_ef = _steam_fuel_factor_kg_per_mmbtu(None)
    gwp = get_active_gwp()
    expected = _DEFAULT_BOILER_EF_KG_PER_MMBTU + 0.001 * float(gwp["CH4"]) + 0.0001 * float(gwp["N2O"])
    assert default_ef == pytest.approx(expected)


def test_calc_indirect_steam_mmbtu():
    # 1,000 MMBtu delivered heat, 80% boiler efficiency, 5% transmission loss
    # Net efficiency = 0.80 * (1 - 0.05) = 0.76
    # Fuel consumed = 1,000 / 0.76 = 1315.789 MMBtu
    data = {
        "amount": 1000.0,
        "unit": "mmbtu",
        "boiler_efficiency": 0.80,
        "calc_inputs": {
            "indirect_steam": {
                "trans_loss": 0.05,
                "ef_co2": 53.06,
            }
        }
    }
    co2e_t, energy_mmbtu, ef = _calc_indirect_steam(data)
    assert energy_mmbtu == 1000.0
    assert ef == 53.06

    expected_ef = _steam_fuel_factor_kg_per_mmbtu(53.06)
    expected_co2e = (1000.0 / 0.76) * expected_ef / 1000.0
    assert co2e_t == pytest.approx(expected_co2e, rel=1e-5)


def test_calc_indirect_steam_percentage_strings():
    # 85% passed as 85 or "85%"
    data1 = {"amount": 500.0, "unit": "mmbtu", "boiler_efficiency": 85}
    co2e_1, _, _ = _calc_indirect_steam(data1)

    data2 = {"amount": 500.0, "unit": "mmbtu", "boiler_efficiency": "85%"}
    co2e_2, _, _ = _calc_indirect_steam(data2)

    assert co2e_1 == pytest.approx(co2e_2)


def test_calc_indirect_steam_validation_errors():
    # Negative or 0 boiler efficiency
    with pytest.raises(ValidationError):
        _calc_indirect_steam({"amount": 100, "boiler_efficiency": -0.5})
    with pytest.raises(ValidationError):
        _calc_indirect_steam({"amount": 100, "boiler_efficiency": "0%"})

    # Transmission loss >= 1.0 or < 0
    with pytest.raises(ValidationError):
        _calc_indirect_steam({"amount": 100, "calc_inputs": {"indirect_steam": {"trans_loss": 1.0}}})
    with pytest.raises(ValidationError):
        _calc_indirect_steam({"amount": 100, "calc_inputs": {"indirect_steam": {"trans_loss": -0.1}}})

    # Invalid unit
    with pytest.raises(ValidationError):
        _calc_indirect_steam({"amount": 100, "unit": "lightyears"})


def test_recalc_indirect_steam():
    # Initial: 1000 MMBtu heat, 100 tCO2e, factor 53.06
    old_heat = 1000.0
    old_co2e = 100.0
    old_ef = 53.06
    emission = SimpleNamespace(heat_mmbtu=old_heat, co2e=old_co2e, steam_ton=0)

    # Edit without specifying boiler eff: must preserve the derived net efficiency
    new_co2e, heat = _recalc_indirect_steam(
        emission=emission,
        data={},
        factor=53.06,
        old_heat=old_heat,
        old_co2e=old_co2e,
        old_ef=old_ef,
    )
    assert heat == 1000.0
    assert new_co2e == pytest.approx(old_co2e)


def test_calc_cogen_allocation():
    # Test zero emissions or zero outputs
    assert _calc_cogen_allocation({"total_emissions": 0, "heat_output_mmbtu": 100, "power_output_mwh": 50}) == 0.0
    assert _calc_cogen_allocation({"total_emissions": 1000, "heat_output_mmbtu": 0, "power_output_mwh": 0}) == 0.0

    # Fuel consumed fallback
    data_fuel = {
        "fuel_consumed_mmbtu": 10_000.0,
        "heat_output_mmbtu": 4000.0,
        "power_output_mwh": 1000.0,
        "allocation_method": "wri_efficiency",
        "heat_efficiency": 0.8,
        "power_efficiency": 0.35,
    }
    allocated_heat_tonnes = _calc_cogen_allocation(data_fuel)
    assert allocated_heat_tonnes > 0
    assert allocated_heat_tonnes < (10_000.0 * 53.06 / 1000.0)


# ---------------------------------------------------------------------------
# Scope 2 API Endpoints (Single entry, Cooling, Recalculate)
# ---------------------------------------------------------------------------

def test_scope2_cooling_api_flow(client, app):
    with app.app_context():
        user = make_user("admin", "Global")
        login(client, user)
        fac = make_facility(region=uniq("CoolingReg"))

        payload = {
            "facility_id": fac.id,
            "year": 2025,
            "month": 4,
            "source_type": "cooling",
            "cooling_ton": 5000.0,
            "emission_factor": 120.0,  # kg CO2e / ton-hour
        }
        res = client.post("/api/scope2", json=payload)
        assert res.status_code == 201, res.get_data(as_text=True)
        data = res.get_json()
        rec_id = data["id"]
        # Expected: 5000 * 120 / 1000 = 600.0 tCO2e
        assert data["emissions"]["co2"] == pytest.approx(600.0)

        # GET and verify
        rec = db.session.get(Scope2Emission, rec_id)
        assert rec.cooling_ton == 5000.0
        assert rec.co2e == pytest.approx(600.0)

        # Edit factor to 150 kg CO2e/ton-hour -> updates to 750 tCO2e
        put_res = client.put(f"/api/scope2/{rec_id}", json={
            "cooling_ton": 5000.0,
            "emission_factor": 150.0,
        })
        assert put_res.status_code == 200
        rec_updated = db.session.get(Scope2Emission, rec_id)
        assert rec_updated.co2e == pytest.approx(750.0)
