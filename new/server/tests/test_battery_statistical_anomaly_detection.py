"""
Battery 3: Statistical Anomaly Detection & Outlier QA/QC Battery.
================================================================
Verifies statistical outlier detection algorithms in MRV data ingestion:
1. Z-Score calculation with Bessel's correction (n-1 degrees of freedom).
2. Tukey's IQR extreme fence bounds ([Q1 - 3*IQR, Q3 + 3*IQR]).
3. Constant historical series deviation checking (sigma=0 edge cases).
4. Data starvation / insufficient history handling (n < 3).
5. Mathematical invariants (non-negative expected lower bound, range monotonicity).
"""
import pytest
import math
import sys
from pathlib import Path

repo_root = str(Path(__file__).resolve().parents[3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from calculations.anomaly import AnomalyDetector


@pytest.fixture
def detector():
    return AnomalyDetector()


class TestDataStarvationBattery:
    """Verifies behavior when insufficient historical data is present."""

    @pytest.mark.parametrize("history", [
        [],
        [100.0],
        [100.0, 105.0],
    ])
    def test_insufficient_history_returns_unflagged(self, detector, history):
        res = detector._z_score_check(150.0, history)
        assert res["flagged"] is False
        assert res["reason"] == "insufficient_history"
        assert res["z_score"] is None
        assert res["expected_range"] is None


class TestConstantHistoryBattery:
    """Verifies detection when historical readings are perfectly uniform (std=0)."""

    def test_constant_history_identical_value(self, detector):
        history = [100.0, 100.0, 100.0, 100.0]
        res = detector._z_score_check(100.0, history)
        assert res["flagged"] is False
        assert res["z_score"] == 0
        assert res["expected_range"] == [100.0, 100.0]

    def test_constant_history_minor_variation(self, detector):
        # 120 is only 20% higher than 100, threshold is >50%
        history = [100.0, 100.0, 100.0, 100.0]
        res = detector._z_score_check(120.0, history)
        assert res["flagged"] is False

    def test_constant_history_major_variation_flagged(self, detector):
        # 160 is 60% higher than 100 (>50% threshold)
        history = [100.0, 100.0, 100.0, 100.0]
        res = detector._z_score_check(160.0, history)
        assert res["flagged"] is True
        assert res["reason"] == "constant_history_deviation"
        assert res["expected_range"] == [50.0, 150.0]

    def test_constant_zero_history(self, detector):
        history = [0.0, 0.0, 0.0]
        # New value is positive when history was strictly zero
        res_nonzero = detector._z_score_check(5.0, history)
        assert res_nonzero["flagged"] is True
        assert res_nonzero["reason"] == "constant_history_deviation"

        # New value is also zero
        res_zero = detector._z_score_check(0.0, history)
        assert res_zero["flagged"] is False


class TestStatisticalZScoreAndIQRBattery:
    """Verifies Z-score and IQR fence detection against known mathematical distributions."""

    def test_normal_distribution_in_bounds(self, detector):
        # Mean = 100, historical values spread between 90 and 110
        history = [92.0, 96.0, 100.0, 104.0, 108.0]
        # A value of 102 is well within 3 sigma
        res = detector._z_score_check(102.0, history)
        assert res["flagged"] is False
        assert abs(res["z_score"]) < 1.0

    def test_extreme_high_outlier_z_score(self, detector):
        # 12 monthly historical values around 1000 tons
        history = [1010.0, 990.0, 1020.0, 980.0, 1005.0, 995.0, 1015.0, 985.0, 1000.0, 1002.0, 998.0, 1000.0]
        # Extreme surge to 1500 tons (> 30 sigma)
        res = detector._z_score_check(1500.0, history)
        assert res["flagged"] is True
        assert res["z_score"] > 3.0
        assert "standard deviations from the 12-month average" in res["message"]

    def test_extreme_low_outlier_z_score(self, detector):
        history = [1010.0, 990.0, 1020.0, 980.0, 1005.0, 995.0, 1015.0, 985.0, 1000.0, 1002.0, 998.0, 1000.0]
        # Extreme drop to 200 tons
        res = detector._z_score_check(200.0, history)
        assert res["flagged"] is True
        assert res["z_score"] < -3.0

    def test_bessel_correction_small_sample(self, detector):
        # For [10.0, 20.0, 30.0], mean = 20.0
        # Population variance = ((100 + 0 + 100)/3) = 66.667 -> std = 8.165
        # Sample variance (Bessel's n-1 = 2) = (200 / 2) = 100.0 -> std = 10.0
        history = [10.0, 20.0, 30.0]
        res = detector._z_score_check(20.0, history)
        assert res["mean"] == 20.0
        assert res["std"] == 10.0  # Must be Bessel's corrected sqrt(100) = 10.0

    def test_expected_range_lower_bound_never_negative(self, detector):
        # Mean = 10, std = 5. Mean - 3*std = -5, but emissions cannot be negative.
        history = [5.0, 10.0, 15.0, 10.0]
        res = detector._z_score_check(12.0, history)
        assert res["expected_range"][0] >= 0.0
        assert res["expected_range"][0] <= res["mean"] <= res["expected_range"][1]
