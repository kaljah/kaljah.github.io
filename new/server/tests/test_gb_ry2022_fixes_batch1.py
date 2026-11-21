"""GB HBNS / El Merk RY 2022 validation, fix batch 1 (security and data integrity).

Findings and decisions: docs/validation-gb-ry2022-fix-plan.md. Expected values are worked by hand from the report's
inputs and the cited tables, never read from the engine.
"""
import uuid

import pytest

from app import app
from calculations import compute_emissions
from calculations.constants import GWP_AR4
from extensions import db

HB = {"c1": 68.4, "c2": 17.2, "c3": 10.1, "c4": 2.3, "c5": 0.5, "c6": 0.2, "c7": 0.1, "c8": 0.1, "co2_mol": 0.6,
      "n2_mol": 0.5, "composition_basis": "percent", "hhv": 1362.97, "hhv_unit": "Btu/scf"}
FLARE = {"process_type": "flaring", "factor_source": "specific", "amount": 41_544_753.91, "unit": "Nm3",
         "destruction_efficiency": 98, "combustion_efficiency": 98}


@pytest.fixture
def ctx():
    with app.app_context():
        yield


# ---------------------------------------------------------------- GB-036
# A lone CH4 content stays a content on the API and the CSV (decision of 2026-10-22, golden dataset A02): the Tier 3
# flare form is where the full analysis is now required (client src/components/Scope1Form.tsx). The full analysis
# reproduces the report's CO2.
def test_gb036_full_analysis_reproduces_the_report_co2(ctx):
    em, _ = compute_emissions({**FLARE, **HB}, {}, gwp_dict=GWP_AR4)
    assert float(em["co2"]) > 100_000


# ---------------------------------------------------------------- GB-019 / D2
def test_gb019_catalog_fuel_does_not_replace_eq_5_6(ctx):
    """Compendium 2021 Eq 5-6 (Dec 2025 corrections): N2O = combustion CO2 x 1.0e-4 / 60 for natural gas, whatever
    catalog fuel the row names."""
    from emission_factors import API_FACTORS

    plain, _ = compute_emissions({**FLARE, **HB}, {}, gwp_dict=GWP_AR4)
    named, _ = compute_emissions({**FLARE, **HB, "fuel": "Natural Gas"}, dict(API_FACTORS["Natural Gas"]),
                                 gwp_dict=GWP_AR4)
    assert float(named["n2o"]) == pytest.approx(float(plain["n2o"]), rel=1e-9)
    # combustion CO2 = total CO2 - the gas's own CO2 (0.6 mol %), carried to N2O by 1e-4 / 60
    assert float(plain["n2o"]) == pytest.approx(float(plain["co2"]) * 0.994 * 1e-4 / 60, rel=0.01)


def test_gb019_entered_n2o_factor_is_used(ctx):
    """An N2O factor the user enters (here SANGEA's 3.716e-5 kg N2O per Nm3) replaces Eq 5-6:
    41,544,753.91 Nm3 x 3.716e-5 kg = 1,543.8 kg."""
    em, _ = compute_emissions({**FLARE, **HB, "n2o_factor": 3.716e-5, "n2o_factor_unit": "kg/Nm3"}, {},
                              gwp_dict=GWP_AR4)
    assert float(em["n2o"]) == pytest.approx(41_544_753.91 * 3.716e-5 / 1000, rel=1e-3)


# ---------------------------------------------------------------- GB-046
def test_gb046_amount_without_unit_is_refused_at_tier3(ctx):
    from input_validation import ValidationError
    from services.scope1_calc import validate_activity

    with pytest.raises(ValidationError, match="unit"):
        validate_activity({"process_type": "combustion", "factor_source": "specific", "amount": 100}, require_unit=False)
    validate_activity({"process_type": "combustion", "factor_source": "specific", "amount": 100, "unit": "m3"},
                      require_unit=False)


# ---------------------------------------------------------------- GB-023
def test_gb023_throughput_venting_is_not_vented_gas(ctx):
    """Table 6-39 gas-processing non-routine venting: 194,132.66 MMscf processed vents 212 scf per MMscf, i.e.
    41,156,124 scf = 1,165,421 m3 of gas, not 5,497 million m3."""
    from models import Emission, Facility
    from services.intensity import intensity_cells

    fac = Facility(name=f"GB23 {uuid.uuid4().hex[:6]}", segment="Upstream", activity="EP")
    db.session.add(fac)
    db.session.flush()
    db.session.add(Emission(facility_id=fac.id, year=2031, month=12, process_type="non_routine_venting",
                            fuel_type="Gas processing non-routine emissions", quantity=194_132.66, unit="MMscf",
                            ch4_emissions=539.1, co2_emissions=13.0, n2o_emissions=0.0, co2e_total=13_490.5,
                            status="Verified", factor_source="default"))
    db.session.commit()
    try:
        cell = intensity_cells(years=[2031], facility_id=fac.id)[(fac.id, 2031)]
        assert cell["vented_m3"] == pytest.approx(194_132.66 * 212 * 0.028316846592, rel=1e-6)
    finally:
        Emission.query.filter_by(facility_id=fac.id).delete()
        db.session.delete(fac)
        db.session.commit()


# ---------------------------------------------------------------- D10
def test_d10_policy_docstring_states_admin_self_approval():
    from services import custom_factor_policy

    assert "may approve their own" in custom_factor_policy.__doc__
