import pytest
from app import app
from models import db, Emission, Facility
from services.qaqc_dashboard import anomaly_status_counts, DashboardFilter, diagnostics
from services.intensity import intensity_cells


def test_rejected_record_status_derivation():
    with app.app_context():
        fac = Facility.query.first()
        if not fac:
            fac = Facility(name="Test Fac", country="Algeria")
            db.session.add(fac)
            db.session.commit()

        rec = Emission(
            facility_id=fac.id,
            year=2024,
            month=5,
            process_type="drilling",
            fuel_type="Diesel",
            quantity=100.0,
            unit="bbl",
            co2e_total=500.0,
            status="Verified",  # Contradictory status
            qa_flag="[Rejected] Manually reviewed",
        )
        db.session.add(rec)
        db.session.commit()

        f = DashboardFilter(allowed_fids=None, args={"year": "2024"})
        counts = anomaly_status_counts(f, outliers=[])
        # Record with [Rejected] qa_flag must be counted as rejected, NOT verified
        assert counts["rejected"] >= 1
        db.session.delete(rec)
        db.session.commit()


def test_data_health_score_decreases_with_rejected_records():
    with app.app_context():
        class MockFilter:
            allowed_fids = None
            year = 2024
            def scope(self, q, model):
                return q

        f = MockFilter()
        # Case A: 0 rejected, 0 pending, 0 flagged
        diag_clean = diagnostics(f, total_flagged=0, outliers=[])
        # Case B: 10 flagged, 2 rejected, 2 pending
        diag_flawed = diagnostics(f, total_flagged=10, outliers=[
            {"status": "Rejected", "qa_flag": "[Rejected] Bad data"},
            {"status": "Pending", "qa_flag": "Anomaly"},
        ])
        assert diag_flawed["health_score"] < diag_clean["health_score"]
        assert diag_flawed["anomalies_summary"]["rejected"] >= 1


def test_rejected_records_excluded_from_intensity_cells():
    with app.app_context():
        fac = Facility.query.first()
        if not fac:
            fac = Facility(name="Test Fac 2", country="Algeria")
            db.session.add(fac)
            db.session.commit()

        test_rec = Emission(
            facility_id=fac.id,
            year=2030,
            month=1,
            process_type="combustion",
            fuel_type="Natural Gas",
            quantity=1000.0,
            unit="mscf",
            co2e_total=99999.0,
            status="Verified",  # Even if contradictory status
            qa_flag="[Rejected] Bogus entry",
        )
        db.session.add(test_rec)
        db.session.commit()

        try:
            cells = intensity_cells(years=[2030], include_pending=False)
            cell = cells.get((fac.id, 2030))
            if cell:
                assert cell["s1"] < 99999.0
        finally:
            db.session.delete(test_rec)
            db.session.commit()
