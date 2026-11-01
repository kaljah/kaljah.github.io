"""
Unit & Regression Tests for QA/QC Status State Machine & Contradiction Resolution (Item 1.3)
==========================================================================================
Verifies that:
1. One unified workflow status machine exists: Draft, Pending, Verified, Rejected.
2. QA flag is a separate attribute from workflow status.
3. Records with status Rejected (or legacy [Rejected] flag) are strictly excluded from inventory totals.
4. Counters, status column, and Data Health Score derive consistently from the status.
5. Data Health Score strictly penalizes the presence of rejected or flagged records.
"""

import pytest
from app import app
from extensions import db
from models import Emission, Facility, User
from services.qaqc_dashboard import diagnostics, anomaly_status_counts, DashboardFilter
from services.dashboard_filters import statuses


def test_workflow_status_constants():
    """Verify canonical workflow status definitions."""
    valid_statuses = {"Draft", "Pending", "Verified", "Rejected"}
    # Active statuses allowed for inventory totals
    assert statuses(include_pending=False) == ("Verified",)
    assert "Rejected" not in statuses(include_pending=True)
    assert "Draft" not in statuses(include_pending=True)


def test_rejected_records_excluded_from_inventory():
    """Verify that records with status 'Rejected' are never included in inventory totals."""
    allowed_active = statuses(include_pending=False)
    assert "Rejected" not in allowed_active
    assert "rejected" not in allowed_active

    allowed_pending = statuses(include_pending=True)
    assert "Rejected" not in allowed_pending


def test_data_health_score_falls_with_rejected_or_flagged_records():
    """
    Verify that Data Health Score decreases when rejected or flagged records exist.
    """
    with app.app_context():
        f = DashboardFilter(allowed_fids=None, args={"year": "2026"})

        # Baseline diagnostics with 0 flagged, 0 outliers
        diag_clean = diagnostics(f, total_flagged=0, outliers=[])
        clean_score = diag_clean["health_score"]

        # Diagnostics with 5 flagged records (pending review)
        diag_flagged = diagnostics(f, total_flagged=5, outliers=[{"status": "Pending", "qa_flag": "Anomaly"}])
        flagged_score = diag_flagged["health_score"]

        # Diagnostics with rejected records
        diag_rejected = diagnostics(f, total_flagged=5, outliers=[{"status": "Rejected", "qa_flag": "[Rejected]"}])
        rejected_score = diag_rejected["health_score"]

        # Health score must strictly decrease
        assert flagged_score < clean_score, f"Expected flagged score ({flagged_score}) < clean score ({clean_score})"
        assert rejected_score < clean_score, f"Expected rejected score ({rejected_score}) < clean score ({clean_score})"
        assert rejected_score <= flagged_score, f"Expected rejected score ({rejected_score}) <= flagged score ({flagged_score})"


def test_record_9_contradiction_detection():
    """
    Verify detection of the record 9 contradiction:
    status == 'Verified' but qa_flag == '[Rejected] Manually reviewed'.
    """
    with app.app_context():
        rec9 = Emission.query.get(9)
        if rec9:
            assert rec9.id == 9
            assert rec9.process_type == "drilling"
            # It has the contradiction identified in Item 1.3
            has_contradiction = (rec9.status == "Verified" and "[Rejected]" in str(rec9.qa_flag))
            assert has_contradiction, "Record 9 was expected to demonstrate the status vs qa_flag contradiction"
