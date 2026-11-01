"""Regression tests for Part 1.5: Scope 3 unit basis, conversions, and completeness warning.

Requirements:
- Cat 11 natural gas uses EF 54.18 with unit MMBtu (not mcf).
- Convert activity units (e.g. mcf to MMBtu via HHV = 1.020 MMBtu/mcf) before multiplying.
- Reject incompatible units (e.g. liquid volume to gas volume, mass to currency, etc.).
- Warn 'Scope 3 incomplete' on Dashboard and Carbon Intensity when Cat 11 has no data for a year with production.
"""
import pytest
from calculations.units import compute_scope3_co2e, _scope3_activity_in_factor_unit
from emission_factors.scope3_activity_factors import SCOPE3_ACTIVITY_FACTORS
from input_validation import ValidationError


def test_category_11_natural_gas_factor_unit():
    cat11 = dict((item[0], (item[1], item[2])) for item in SCOPE3_ACTIVITY_FACTORS[11])
    assert "Natural Gas" in cat11
    unit, factor = cat11["Natural Gas"]
    # Explicit denominator unit must be MMBtu (not mcf or scf)
    assert unit == "MMBtu"
    assert factor == 54.18


def test_mcf_to_mmbtu_hhv_conversion():
    # 1 mcf of natural gas has HHV of 1.020 MMBtu (API Compendium 2021 Table 3-8 / §8.1)
    scale = _scope3_activity_in_factor_unit("mcf", "mmbtu")
    assert pytest.approx(scale, rel=1e-3) == 1.020

    # 5,000 mcf of natural gas at 54.18 kg CO2e / MMBtu
    # Expected: 5,000 mcf * 1.020 MMBtu/mcf * 54.18 kg CO2e/MMBtu / 1000 = 276.318 tCO2e
    co2e = compute_scope3_co2e(5000.0, 54.18, "kg CO2e / MMBtu", activity_unit="mcf")
    assert pytest.approx(co2e, rel=1e-4) == 276.318


def test_unit_conversion_rejects_incompatible():
    # Incompatible dimensions must raise ValidationError
    with pytest.raises(ValidationError):
        compute_scope3_co2e(100.0, 54.18, "kg CO2e / MMBtu", activity_unit="USD")

    with pytest.raises(ValidationError):
        compute_scope3_co2e(100.0, 54.18, "kg CO2e / MMBtu", activity_unit="bbl")

    with pytest.raises(ValidationError):
        compute_scope3_co2e(100.0, 0.787, "kg CO2e / USD", activity_unit="m3")


def test_scope3_completeness_warning_contract(app):
    from routes.dashboard import _query_scope3_summary, clear_dashboard_cache
    from services.intensity import intensity_cells, facility_row
    from models import Facility, ProductionData, Scope3Emission
    from extensions import db
    from tests.audit_helpers import make_facility, uniq

    with app.app_context():
        clear_dashboard_cache()
        fac = make_facility(name=uniq("FAC_S3_TEST"))
        test_year = 2031

        # Add production data for facility in test_year
        prod = ProductionData(
            facility_id=fac.id,
            year=test_year,
            month=1,
            oil_amount=500.0,
            oil_unit="bbl",
            gas_amount=2000.0,
            gas_unit="mscf",
        )
        db.session.add(prod)

        # Add only Category 1 (no Category 11)
        s3 = Scope3Emission(
            facility_id=fac.id,
            year=test_year,
            month=1,
            category="Category 1",
            sub_category="Steel pipe & tube (NAICS 331210)",
            activity_data=500.0,
            unit="USD",
            emission_factor=0.36,
            factor_unit="kg CO2e / USD",
            co2e=0.18,
            status="Verified",
        )
        db.session.add(s3)
        db.session.commit()

        # Scope 3 summary should flag scope3_incomplete = True
        summary = _query_scope3_summary(facility_id=str(fac.id), year=str(test_year))
        assert summary["scope3_incomplete"] is True

        # Carbon Intensity regional row should flag scope3_cat11_missing = True
        cells = intensity_cells(years=[test_year], facility_id=str(fac.id))
        row = facility_row(fac.id, list(cells.items()), fac, str(test_year))
        assert row["scope3_cat11_missing"] is True
