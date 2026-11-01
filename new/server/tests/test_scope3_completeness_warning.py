import pytest
from tests.audit_helpers import make_facility, uniq
from models import ProductionData, Scope3Emission
from extensions import db
from routes.dashboard import _query_scope3_summary, clear_dashboard_cache
from services.intensity import intensity_cells, facility_row


def test_scope3_incomplete_flag_when_cat11_missing(app):
    """Item 1.5: Warn when Cat 11 (use of sold products) has no data for a year with production."""
    with app.app_context():
        clear_dashboard_cache()
        fac = make_facility(name=uniq("FAC_S3"))
        yr = 2029

        # Add production data for 2029
        prod = ProductionData(
            facility_id=fac.id,
            year=yr,
            month=1,
            oil_amount=1000.0,
            oil_unit="bbl",
            gas_amount=5000.0,
            gas_unit="mscf",
        )
        db.session.add(prod)

        # Add a Category 1 Scope 3 record (Purchased Goods), but NO Category 11
        s3_cat1 = Scope3Emission(
            facility_id=fac.id,
            year=yr,
            month=1,
            category="Category 1",
            sub_category="Steel pipe & tube (NAICS 331210)",
            activity_data=1000.0,
            unit="USD",
            emission_factor=0.36,
            factor_unit="kg CO2e / USD",
            co2e=0.36,
            status="Verified",
        )
        db.session.add(s3_cat1)
        db.session.commit()

        # Query summary for 2029
        summary = _query_scope3_summary(facility_id=str(fac.id), year=str(yr))
        assert summary["scope3_incomplete"] is True

        # Test facility_row in intensity.py
        cells = intensity_cells(years=[yr], facility_id=str(fac.id))
        row = facility_row(fac.id, list(cells.items()), fac, str(yr))
        assert row["total_boe"] > 0
        assert row["total_scope3_cat11"] == 0.0
        assert row["scope3_cat11_missing"] is True

        # Now add a Category 11 Scope 3 record (Use of Sold Products)
        s3_cat11 = Scope3Emission(
            facility_id=fac.id,
            year=yr,
            month=1,
            category="Category 11",
            sub_category="Natural Gas",
            activity_data=1000.0,
            unit="mcf",
            emission_factor=54.18,
            factor_unit="kg CO2e / MMBtu",
            co2e=55.2636,
            status="Verified",
        )
        db.session.add(s3_cat11)
        db.session.commit()

        clear_dashboard_cache()
        summary2 = _query_scope3_summary(facility_id=str(fac.id), year=str(yr))
        assert summary2["scope3_incomplete"] is False

        cells2 = intensity_cells(years=[yr], facility_id=str(fac.id))
        row2 = facility_row(fac.id, list(cells2.items()), fac, str(yr))
        assert row2["total_scope3_cat11"] > 0
        assert row2["scope3_cat11_missing"] is False
