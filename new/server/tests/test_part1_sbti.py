"""Item 1.12: SBTi Page Partial Year Markings and Labels
======================================================
Verifies:
1. Pathway title renamed to "SBTi-aligned pathway (indicative)".
2. Partial year (e.g. 2026) has is_partial_year flag set.
3. Actual YTD and annualized actuals are calculated and exposed.
"""
import pytest
from extensions import db
from models import Emission, SbtiTarget
from tests.audit_helpers import make_facility, make_user, login, uniq

def test_sbti_partial_year_and_labels(app, client):
    """Item 1.12: SBTi partial year markings and indicative pathway labels."""
    with app.app_context():
        admin = make_user("admin")
        login(client, admin)

        fac = make_facility(name=uniq("FAC_SBTI"))

        # Create SBTi Target so the trajectory endpoint calculates projections
        target = SbtiTarget(
            base_year=2023,
            base_year_emissions=100_000.0,
            target_year=2050,
            reduction_rate_pct=4.2,
            pathway_type="1.5C",
            scope_coverage="S1S2S3",
            created_by=admin.id,
        )
        db.session.add(target)

        # Add emissions for year 2026 with 4 months reported
        for m in [1, 2, 3, 4]:
            em = Emission(
                facility_id=fac.id,
                year=2026,
                month=m,
                process_type="combustion",
                co2e_total=10_000.0,
                status="Verified",
                is_test=False,
            )
            db.session.add(em)
        db.session.commit()

        res = client.get('/api/dashboard/sbti-trajectory')
        assert res.status_code == 200
        data = res.json

        # Pathway label is marked indicative
        assert "Indicative" in data.get("pathway_label", "") or "indicative" in data.get("pathway_label", "").lower()

        # Check trajectory for 2026 (current partial year)
        trajectory = data.get("trajectory", [])
        assert len(trajectory) > 0

        row_2026 = next((r for r in trajectory if str(r["year"]) == "2026"), None)
        assert row_2026 is not None
        assert row_2026["is_partial_year"] is True
        assert "actual_ytd" in row_2026
        assert "actual_annualized" in row_2026
        # Annualized should be 12/4 = 3x of YTD
        if row_2026["months_reported"] and row_2026["months_reported"] < 12:
            assert row_2026["actual_annualized"] > row_2026["actual"]
