"""Regression tests for the clean-room calculation audit of November 2026, batch S (Scope 2 / 3).

Finding IDs refer to CALC_AUDIT_2026-11/REPORT.md. Expected values are worked by hand from the inputs and the
cited norm (GHG Protocol Scope 2 Guidance, AIB European Residual Mixes 2023, API Compendium 2021 s8.2), never read
from the engine.
"""
import pytest

from app import app
from input_validation import ValidationError

MMBTU_PER_MWH = 3.412142


@pytest.fixture
def ctx():
    with app.app_context():
        yield


# ---------------------------------------------------------------- F-S23-02 / F-S23-07 market-based factor
def test_f_s23_02_market_without_instrument_uses_residual_mix():
    from services.scope2_market import market_basis, market_factor

    # AIB 2023 Table 2: Germany residual mix 719.90 g CO2/kWh (the grid average is 338.7)
    used, stored = market_factor(0.3387, None, None, grid_name="Germany (grid average)")
    assert used == pytest.approx(0.7199)
    assert stored is None
    assert "residual mix" in market_basis(None, None, "Germany (grid average)")


def test_f_s23_02_grid_without_residual_mix_falls_back_to_the_grid():
    from services.scope2_market import market_basis, market_factor

    used, stored = market_factor(0.5, None, None, grid_name="No such grid")
    assert (used, stored) == (0.5, None)
    assert "grid average" in market_basis(None, None, "No such grid")


def test_f_s23_07_guarantee_of_origin_is_zero_emission():
    from services.scope2_market import market_factor

    assert market_factor(0.3387, "go", None, grid_name="Germany (grid average)") == (0.0, 0.0)


def test_supplier_instrument_needs_its_factor():
    from services.scope2_market import market_factor

    with pytest.raises(ValidationError, match="needs its emission factor"):
        market_factor(0.3387, "supplier_specific", None)
    assert market_factor(0.3387, "supplier_specific", 0.2) == (0.2, 0.2)


# ---------------------------------------------------------------- F-S23-03 Scope 3 natural gas per MMBtu
def test_f_s23_03_sold_natural_gas_factor_is_per_mmbtu():
    from emission_factors.scope3_activity_factors import SCOPE3_ACTIVITY_FACTORS as F

    # Table 4-5 53.06 kg CO2 + Table 4-6 0.001 kg CH4 x 28 + 0.0001 kg N2O x 265 = 53.1145 kg CO2e/MMBtu
    rows = {(cat, name): (unit, f) for cat, lst in F.items() for name, unit, f in lst}
    assert rows[(11, "Natural Gas")] == ("MMBtu", pytest.approx(53.06 + 0.028 + 0.0265, abs=0.005))
    assert rows[(10, "Processing (Natural Gas)")] == ("MMBtu", pytest.approx(53.1145, abs=0.005))


# ---------------------------------------------------------------- F-GUI-02 / F-S23-08 GWP-20 re-weighting
def test_f_gui_02_steam_gases_are_reweighted_at_gwp20(ctx):
    from services.dashboard_filters import gwp_pair
    from services.scope2_gases import record_totals_fields

    c100, n100 = gwp_pair("100")
    c20, n20 = gwp_pair("20")
    ch4_t, n2o_t = 0.5, 0.01
    loc, mkt = record_totals_fields("indirect_steam", None, None, 100.0, 100.0, "20", ch4_t=ch4_t, n2o_t=n2o_t)
    delta = ch4_t * (c20 - c100) + n2o_t * (n20 - n100)
    assert loc == pytest.approx(100.0 + delta)
    assert mkt == pytest.approx(100.0 + delta)  # steam has no contractual factor: market = location
    assert record_totals_fields("indirect_steam", None, None, 100.0, 100.0, "100", ch4_t=ch4_t, n2o_t=n2o_t) == (100.0, 100.0)


def test_f_s23_08_contractual_market_value_is_not_reweighted(ctx):
    from services.scope2_gases import record_totals_fields

    # a REC: the market value is the contract's 0, whatever the GWP horizon
    _, mkt = record_totals_fields("electricity", "US-ERCT (ERCOT All)", 1000.0, 0.394, 0.0, "20", market_ef=0.0)
    assert mkt == 0.0


# ---------------------------------------------------------------- F-S23-01 CHP buyer's share
def _chp(**kw):
    from routes.scope2 import _calc_cogen_allocation

    base = {"total_emissions": 1000.0, "heat_output_mmbtu": 800.0, "power_output_mwh": 100.0,
            "allocation_method": "wri_efficiency"}
    base.update(kw)
    with app.test_request_context():
        return _calc_cogen_allocation(base)


def test_f_s23_01_chp_books_only_the_heat_bought():
    # Eq 8-5 with the Compendium defaults 80 % heat / 35 % power, then x bought / total (Exhibit 8.4 step 5)
    heat_share = 800.0 / 0.80
    power_share = 100.0 * MMBTU_PER_MWH / 0.35
    heat_t = 1000.0 * heat_share / (heat_share + power_share)
    assert _chp(purchased_stream="heat", quantity_bought=400.0) == pytest.approx(heat_t * 400.0 / 800.0, rel=1e-4)


def test_f_s23_01_chp_power_share():
    heat_share = 800.0 / 0.80
    power_share = 100.0 * MMBTU_PER_MWH / 0.35
    power_t = 1000.0 * power_share / (heat_share + power_share)
    assert _chp(purchased_stream="power", quantity_bought=25.0) == pytest.approx(power_t * 25.0 / 100.0, rel=1e-4)


def test_f_s23_01_chp_refusals():
    with pytest.raises(ValidationError, match="quantity of the stream bought"):
        _chp(purchased_stream="heat")
    with pytest.raises(ValidationError, match="cannot exceed"):
        _chp(purchased_stream="heat", quantity_bought=900.0)
    with pytest.raises(ValidationError, match="total heat output"):
        _chp(power_output_mwh=0, purchased_stream="heat", quantity_bought=10.0)


# ---------------------------------------------------------------- F-UPL-03 slash-less factor unit keeps its mass
def test_f_upl_03_tco2e_factor_without_denominator():
    from calculations.units_scope3 import compute_scope3_co2e, scope3_complete_factor_unit

    unit = scope3_complete_factor_unit("tCO2e", "tonne")
    assert unit == "tCO2e / tonne"
    # 100 tonne x 0.5 t CO2e per tonne = 50 t (it was read as kg: 0.05 t)
    assert compute_scope3_co2e(100, 0.5, unit, activity_unit="tonne") == pytest.approx(50.0)
    assert scope3_complete_factor_unit("", "km") == "kg CO2e / km"
    assert scope3_complete_factor_unit("kg CO2e / km", "mile") == "kg CO2e / km"


def test_f_upl_03_unknown_mass_is_refused():
    from calculations.units_scope3 import compute_scope3_co2e, scope3_complete_factor_unit

    with pytest.raises(ValidationError):
        compute_scope3_co2e(100, 0.5, scope3_complete_factor_unit("widgets", "tonne"), activity_unit="tonne")


# ---------------------------------------------------------------- F-UPL-04 duplicate key matches the DB constraint
def test_f_upl_04_scope3_key_ignores_the_unit():
    from background_processor import _scope3_key

    assert _scope3_key(1, 2025, 1, "Category 6", "Taxi", "km") == _scope3_key(1, 2025, 1, "Category 6", "taxi", "mile")


# ---------------------------------------------------------------- F-S23-05 / F-UPL-08 EEIO spend basis
def test_f_upl_08_non_usd_spend_needs_its_rate():
    from services.eeio_spend import spend_in_factor_usd

    with pytest.raises(ValidationError, match="exchange rate"):
        spend_in_factor_usd(10_000, "EUR", None, 2022)
    usd, notes = spend_in_factor_usd(10_000, "EUR", 1.05, 2022)
    assert usd == pytest.approx(10_500.0)
    assert any("1.05" in n for n in notes)


def test_f_s23_05_deflator_and_note():
    from services.eeio_spend import spend_in_factor_usd

    usd, notes = spend_in_factor_usd(1000, "USD", None, 2024, deflator_to_2022=0.95)
    assert usd == pytest.approx(950.0)
    usd, notes = spend_in_factor_usd(1000, "USD", None, 2024)
    assert usd == 1000.0 and any("not deflated" in n for n in notes)
    assert spend_in_factor_usd(1000, None, None, 2022) == (1000.0, [])


# ---------------------------------------------------------------- F-S23-12 cooling from the chiller COP (Eq 8-2)
def test_f_s23_12_cooling_from_cop(ctx):
    from services.scope2_policy import cooling_factor_from_cop

    ef, kwh_per_th, _ = cooling_factor_from_cop(4.2, "US-RMPA (WECC Rockies)")
    assert kwh_per_th == pytest.approx(12000 / 4.2 / 3412.142)
    # 1,000 ton-hours, COP 4.2, RMPA (Table 8-2: 0.564 kg CO2, 5.31e-5 CH4, 7.71e-6 N2O per kWh, AR5) = 0.4752 t
    grid = 0.564 + 5.31e-5 * 28 + 7.71e-6 * 265
    assert 1000 * ef / 1000 == pytest.approx(1000 * kwh_per_th * grid / 1000, rel=1e-3)
    assert 1000 * ef / 1000 == pytest.approx(0.4752, rel=2e-3)
    with pytest.raises(ValidationError, match="COP"):
        cooling_factor_from_cop(0, "US-RMPA (WECC Rockies)")


# ---------------------------------------------------------------- F-S23-10 steam factor unit is never guessed
def test_f_s23_10_small_boiler_factor_without_unit_is_refused(ctx):
    from services.scope2_policy import steam_emissions

    base = {"amount": 1000, "unit": "mmbtu", "calc_inputs": {"indirect_steam": {"boiler_eff": 0.92, "trans_loss": 0.10}}}
    with pytest.raises(ValidationError, match="unit"):
        steam_emissions({**base, "calc_inputs": {"indirect_steam": {**base["calc_inputs"]["indirect_steam"], "ef_co2": 0.053}}})
    r = steam_emissions({**base, "calc_inputs": {"indirect_steam": {**base["calc_inputs"]["indirect_steam"],
                                                                  "ef_co2": 0.053, "ef_unit": "t/mmbtu"}}})
    # 1,000 MMBtu / (0.92 - 0.10) x 53 kg CO2/MMBtu = 64.63 t CO2
    assert r["co2"] == pytest.approx(1000 / 0.82 * 53.0 / 1000, rel=1e-6)
