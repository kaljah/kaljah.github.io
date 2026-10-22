"""Behaviours found while hand-working the calculation tests (2026-10-22), now decided and fixed:

1. an entered custom (Tier 2) factor is used by completions and liquids unloading (it was silently ignored);
2. a gas analysis of two or more components must total 100 % (99.5 to 100.5 is rounding); it was rescaled between 98 and
   100 % and used as given below that;
3. Equation 6-10 counts the flow-line term SFR x (HR - X) once per well-year, as the Compendium prints it;
4. liquids unloading is counted in events or wells: "m3" is refused (it was read as a number of wells);
5. the Table 6-8 associated-gas CH4 factor is converted from its own unit to kg per bbl (it was read as kg/bbl whatever it was);
6. the wellbore-volume unloading method no longer calls itself a Compendium equation.
"""
import pytest

from calculations.constants import GWP_AR5
from calculations.dispatcher import CalculationDispatcher
from calculations.units import composition_fractions
from calculations.vented_unloading import LiquidsUnloadingCalculator

AR5 = GWP_AR5


@pytest.fixture(scope="module")
def d():
    return CalculationDispatcher()


def _gas(res, gas):
    r = res["results"][gas]
    return float(r["value"] if isinstance(r, dict) else r)


# ---- 1. custom factors -------------------------------------------------------------------------------------------

def test_completions_use_an_entered_custom_factor(d):
    """100 m3 of flowback x a custom 0.5 kg CH4 per m3 = 50 kg (the Tier 3 gas-analysis result would be 54 kg)."""
    res = d.dispatch("completions", {"factor_source": "custom", "amount": 100, "unit": "m3", "ch4_content": 80},
                     {"ch4": 0.5, "unit": "kg/m3", "type": "custom"}, {}, gwp_dict=AR5)
    assert _gas(res, "ch4") == pytest.approx(0.05, rel=1e-12)
    assert res["total_co2e"] == pytest.approx(0.05 * 28.0, rel=1e-12)


def test_unloading_uses_an_entered_per_well_year_factor(d):
    """10 wells x 2,000 kg CH4/well-year = 20 t for a year; a January record covers 31/365 of it."""
    ef = {"ch4": 2000, "unit": "kg/well-year", "type": "custom"}
    year = d.dispatch("liquids_unloading", {"factor_source": "custom", "amount": 10, "unit": "wells"}, ef, {},
                      gwp_dict=AR5)
    assert _gas(year, "ch4") == pytest.approx(20.0, rel=1e-12)
    jan = d.dispatch("liquids_unloading", {"factor_source": "custom", "amount": 10, "unit": "wells", "year": 2025,
                                           "month": 1}, ef, {}, gwp_dict=AR5)
    assert _gas(jan, "ch4") == pytest.approx(20.0 * 31 / 365, rel=1e-12)


def test_unloading_uses_an_entered_per_event_factor(d):
    res = d.dispatch("liquids_unloading", {"factor_source": "custom", "amount": 10, "unit": "events"},
                     {"ch4": 150, "unit": "kg/event", "type": "custom"}, {}, gwp_dict=AR5)
    assert _gas(res, "ch4") == pytest.approx(1.5, rel=1e-12)


def test_default_factor_source_still_uses_the_table(d):
    """The catalog (Table 6-11) path is unchanged: 10 plunger wells x 1.774 t."""
    res = d.dispatch("liquids_unloading", {"factor_source": "default", "amount": 10, "unit": "wells"}, {}, {},
                     gwp_dict=AR5)
    assert _gas(res, "ch4") == pytest.approx(17.74, rel=1e-9)


# ---- 2. gas analysis total -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("raw", [{"c1": 90, "c2": 5}, {"c1": 70, "co2": 5}, {"c1": 85, "c2": 8, "co2": 3},
                                 {"c1": 98, "c2": 1}])
def test_an_analysis_that_does_not_total_100_is_refused(raw):
    with pytest.raises(ValueError, match="must total 100 %"):
        composition_fractions(raw)


@pytest.mark.parametrize("raw, c1", [({"c1": 90, "n2": 10}, 0.90), ({"c1": 99.6, "n2": 0}, 1.0),
                                     ({"c1": 90.3, "c2": 5, "n2": 5}, 0.903 / 1.003)])
def test_an_analysis_totalling_100_within_rounding_is_accepted(raw, c1):
    fr, _ = composition_fractions(raw)
    assert sum(fr.values()) == pytest.approx(1.0) and fr["c1"] == pytest.approx(c1)


def test_a_dispatch_with_an_incomplete_analysis_says_what_to_add(d):
    with pytest.raises(ValueError, match="enter the remainder as N2"):
        d.dispatch("flaring", {"factor_source": "specific", "amount": 1000, "unit": "m3", "c1": 80, "c2": 10}, {}, {})


# ---- 3. Equation 6-10 ----------------------------------------------------------------------------------------------

def test_equation_6_10_flowline_term_is_counted_once():
    """12 events: the wellbore term is x12, the flow-line term SFR x (HR - X) is not (Subpart W would give 12 x)."""
    u = LiquidsUnloadingCalculator()
    res = u.calculate_tier3_equation_6_10(events=12, well_depth=12000, diameter=10, pressure=250, sfr=35000,
                                          hours_open=3, unloading_type="non_plunger", ch4_content=0.80)
    wellbore = 12 * 0.37e-3 * 10 ** 2 * 12000 * 250                 # 1,332,000 scf
    flowline = 35000 * (3 - 1.0)                                      # once: 70,000 scf
    assert res["inputs"]["vr_per_well_scf"] == pytest.approx(wellbore + flowline, rel=1e-9)


# ---- 4. unloading units --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("unit", ["m3", "scf", "bbl", "devices", "count"])
def test_unloading_refuses_units_that_are_not_events_or_wells(d, unit):
    with pytest.raises(ValueError, match="events .* or wells"):
        d.dispatch("liquids_unloading", {"factor_source": "default", "amount": 10, "unit": unit}, {}, {})


# ---- 5. associated-gas factor unit ---------------------------------------------------------------------------------

def test_associated_gas_factor_is_converted_from_its_own_unit(d):
    """0.5 kg CH4 per m3 of oil on 100 m3 is 50 kg; read as kg/bbl it was 314 kg."""
    res = d.dispatch("associated_gas_venting", {"factor_source": "default", "amount": 100, "unit": "m3"},
                     {"ch4": 0.5, "unit": "kg/m3"}, {}, gwp_dict=AR5)
    assert _gas(res, "ch4") == pytest.approx(0.05, rel=1e-6)
    per_bbl = d.dispatch("associated_gas_venting", {"factor_source": "default", "amount": 100, "unit": "bbl"},
                         {"ch4": 1.4, "unit": "kg CH4/bbl"}, {}, gwp_dict=AR5)      # Table 6-8, US average
    assert _gas(per_bbl, "ch4") == pytest.approx(0.14, rel=1e-9)


def test_associated_gas_factor_that_is_not_per_volume_of_oil_is_refused(d):
    with pytest.raises(ValueError, match="kg CH4 per bbl"):
        d.dispatch("associated_gas_venting", {"factor_source": "default", "amount": 100, "unit": "bbl"},
                   {"ch4": 0.5, "unit": "kg/hr"}, {}, gwp_dict=AR5)


# ---- 6. label of the wellbore-volume method ----------------------------------------------------------------------

def test_wellbore_volume_method_is_not_labelled_as_a_compendium_equation():
    res = LiquidsUnloadingCalculator().calculate_volume_based(well_depth=6000, diameter=2.875, pressure=350,
                                                              ch4_content=0.85, events=10, gwp_dict=AR5)
    assert res["inputs"]["method"] == "api_equation_6_3"            # the stored key does not change
    assert "Equation 6-3" not in res["inputs"]["api_reference"] and "Eq. 6-3" not in res["inputs"]["calculation_level"]
    assert "platform method" in res["inputs"]["api_reference"].lower()


# ---- the CH4 + CO2 content short form is not an analysis ---------------------------------------------------------

def test_ch4_and_co2_content_short_form_is_not_checked_for_100(d):
    """A flare with ch4_content 80 and co2_content 5 (the import wizard's short form) keeps working: the rest of the gas
    is not described. 1,000 m3 = 42.22 kmol: 80 % CH4 burned at 96.5 % plus the 5 % CO2 already in the gas."""
    res = d.dispatch("flaring", {"factor_source": "specific", "amount": 1000, "unit": "m3", "ch4_content": 80,
                                 "co2_content": 5}, {}, {}, gwp_dict=AR5)
    kmol = 1000.0 / 23.685
    assert _gas(res, "co2") == pytest.approx(kmol * (0.80 * 0.965 + 0.05) * 44.01 / 1000.0, rel=1e-6)
    assert _gas(res, "ch4") == pytest.approx(kmol * 0.80 * 0.02 * 16.04 / 1000.0, rel=1e-6)


def test_the_same_numbers_as_an_analysis_are_checked(d):
    """c1 / co2_mol are analysis keys: 80 + 5 = 85 % is refused."""
    with pytest.raises(ValueError, match="must total 100 %"):
        d.dispatch("flaring", {"factor_source": "specific", "amount": 1000, "unit": "m3", "c1": 80, "co2_mol": 5}, {}, {})


def test_a_row_short_of_100_is_named_in_the_file_check():
    from services.import_feedback import classify
    title, _t, column, fix = classify("Calculation error for 'flaring': Gas composition sums to 85.00 %: it must total "
                                      "100 % (0.5 % rounding; enter the remainder as N2, CO2 or H2S)")
    assert title == "Gas analysis does not total 100 %" and column == "n2_mol"
    assert "n2_mol" in fix and "ch4_content" in fix
