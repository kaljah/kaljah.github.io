import pytest
from calculations.anomaly import AnomalyDetector


def test_anomaly_stdev_zero_or_tiny_noise():
    detector = AnomalyDetector()
    # 9 historical records with identical value 1.913 (which caused the 2.22e+17 bug)
    history_identical = [1.913] * 9
    
    # New value identical to history -> not flagged
    res_same = detector._z_score_check(1.913, history_identical)
    assert res_same["flagged"] is False
    assert res_same["z_score"] == 0.0

    # New value 54.18 (the actual bug case)
    res_outlier = detector._z_score_check(54.18, history_identical)
    assert res_outlier["flagged"] is True
    # Z-score must be capped at 10.0, NOT 2.22e+17
    assert res_outlier["z_score"] <= 10.0
    assert "221912853722100864" not in str(res_outlier.get("message", ""))
    assert "e+" not in str(res_outlier.get("message", ""))


def test_anomaly_insufficient_history():
    detector = AnomalyDetector()
    assert detector._z_score_check(100.0, [50.0])["flagged"] is False
    assert detector._z_score_check(100.0, [50.0, 52.0])["flagged"] is False
    assert detector._z_score_check(100.0, [50.0, 52.0])["reason"] == "insufficient_history"


def test_anomaly_z_score_capped_at_ten():
    detector = AnomalyDetector()
    # History with small standard deviation
    history = [10.0, 10.1, 9.9, 10.0, 10.2]
    # Extreme outlier (1,000,000)
    res = detector._z_score_check(1000000.0, history)
    assert res["flagged"] is True
    assert res["z_score"] == 10.0
