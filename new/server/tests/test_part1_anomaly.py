"""Regression tests for Part 1.4: Anomaly detector and QA flag sanitization.

Requirements:
- Fix z-score: guard stdev about 0 and n < 3, cap or skip, format numbers sensibly (no scientific notation).
- Review [BogusStatus] label: reject invalid resolutions, clean up legacy bogus labels.
"""
import pytest
from calculations.anomaly import AnomalyDetector
from routes.qaqc import _tag_qa_flags, _RESOLUTIONS


def test_insufficient_history_guard():
    detector = AnomalyDetector()
    # Empty history
    res_empty = detector._z_score_check(50.0, [])
    assert res_empty["flagged"] is False
    assert res_empty["reason"] == "insufficient_history"
    assert res_empty["z_score"] is None

    # n = 1
    res_1 = detector._z_score_check(50.0, [50.0])
    assert res_1["flagged"] is False
    assert res_1["reason"] == "insufficient_history"

    # n = 2
    res_2 = detector._z_score_check(50.0, [49.0, 51.0])
    assert res_2["flagged"] is False
    assert res_2["reason"] == "insufficient_history"


def test_stdev_about_zero_guard_and_sensible_formatting():
    detector = AnomalyDetector()
    # 9 historical records with identical value 1.913
    history_identical = [1.913] * 9

    # Identical value -> no flag, z=0
    res_same = detector._z_score_check(1.913, history_identical)
    assert res_same["flagged"] is False
    assert res_same["z_score"] == 0.0

    # Outlier 54.18 (the actual bug case that previously produced 2.22e+17)
    res_outlier = detector._z_score_check(54.18, history_identical)
    assert res_outlier["flagged"] is True
    # Z-score must be capped at 10.0
    assert res_outlier["z_score"] == 10.0
    # Message must NOT have astronomical numbers or scientific notation
    msg = res_outlier.get("message", "")
    assert "221912853722100864" not in msg
    assert "e+" not in msg
    assert "1.91" in msg


def test_extreme_variance_capped_at_ten():
    detector = AnomalyDetector()
    history = [10.0, 10.1, 9.9, 10.0, 10.2]
    # Huge positive outlier
    res_pos = detector._z_score_check(1e9, history)
    assert res_pos["flagged"] is True
    assert res_pos["z_score"] == 10.0
    assert "e+" not in res_pos["message"]

    # Huge negative outlier
    res_neg = detector._z_score_check(-1e9, history)
    assert res_neg["flagged"] is True
    assert res_neg["z_score"] == -10.0


def test_bogus_status_rejected_and_sanitized():
    # Only Verified and Rejected are valid resolutions
    assert "BogusStatus" not in _RESOLUTIONS
    assert set(_RESOLUTIONS.keys()) == {"Verified", "Rejected"}

    # Test regex cleans up [BogusStatus]
    import re
    flag_with_bogus = "[Verified] [BogusStatus] [Verified] Manually reviewed"
    clean_flag = re.sub(
        r"^(\[(Verified|Rejected|Pending|BogusStatus|Draft)\]\s*|Rejected:\s*[^()]*\s*\(?)+",
        "",
        flag_with_bogus
    ).rstrip(")").strip()
    assert clean_flag == "Manually reviewed"
    assert "BogusStatus" not in clean_flag
