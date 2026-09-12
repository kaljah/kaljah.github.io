"""
Anomaly Detection for GHG Emissions Data.

Uses Z-score (against 12-month rolling average per facility/metric) and
IQR fence as a secondary check to flag statistical outliers before they
skew the carbon inventory.
"""

import math
from typing import Optional


class AnomalyDetector:
    """
    Checks a new emission value against historical data for the same
    facility and metric to detect statistically significant outliers.

    Usage:
        detector = AnomalyDetector(db_session)
        result = detector.check_scope1(facility_id=5, process_type='combustion', co2e=99999.0, year=2024)
        if result['flagged']:
            print(result['message'])
    """

    def __init__(self, db_session=None):
        self.db = db_session

    def _get_db(self):
        if self.db:
            return self.db
        from extensions import db
        return db

    # ─── Z-Score Calculator ──────────────────────────────────────────────────

    def _z_score_check(self, value: float, historical: list[float]) -> dict:
        """
        Compute Z-score of a value against a list of historical values.
        Returns flagged=True if |z| > 3 (99.7% confidence outlier).
        """
        if not historical or len(historical) < 3:
            return {"flagged": False, "reason": "insufficient_history", "z_score": None, "expected_range": None}

        n = len(historical)
        mean = sum(historical) / n
        variance = sum((x - mean) ** 2 for x in historical) / n
        std = math.sqrt(variance) if variance > 0 else 0

        if std == 0:
            # All historical values identical — flag only if new value differs significantly
            if mean > 0 and abs(value - mean) / mean > 0.5:
                return {
                    "flagged": True,
                    "z_score": None,
                    "mean": mean,
                    "std": 0,
                    "expected_range": [mean * 0.5, mean * 1.5],
                    "reason": "constant_history_deviation",
                    "message": f"Historical values are constant ({mean:.1f}) but new value is {value:.1f}."
                }
            return {"flagged": False, "z_score": 0, "expected_range": [mean, mean]}

        z = (value - mean) / std

        # IQR fence as secondary check
        sorted_h = sorted(historical)
        q1 = sorted_h[len(sorted_h) // 4]
        q3 = sorted_h[(3 * len(sorted_h)) // 4]
        iqr = q3 - q1
        lower_fence = q1 - 3 * iqr
        upper_fence = q3 + 3 * iqr

        flagged_z = abs(z) > 3
        flagged_iqr = iqr > 0 and (value < lower_fence or value > upper_fence)

        flagged = flagged_z or flagged_iqr
        expected_low = max(0, mean - 3 * std)
        expected_high = mean + 3 * std

        return {
            "flagged": flagged,
            "z_score": round(z, 2),
            "mean": round(mean, 2),
            "std": round(std, 2),
            "expected_range": [round(expected_low, 2), round(expected_high, 2)],
            "iqr_flagged": flagged_iqr,
            "reason": "z_score" if flagged_z else ("iqr" if flagged_iqr else None),
            "message": (
                f"Value {value:.2f} is {abs(z):.1f} standard deviations from the 12-month average "
                f"({mean:.2f} ± {std:.2f}). Expected range: [{expected_low:.2f} – {expected_high:.2f}]."
            ) if flagged else None
        }

    # ─── Scope 1 ─────────────────────────────────────────────────────────────

    def check_scope1(
        self,
        facility_id: int,
        process_type: str,
        co2e: float,
        year: int,
        month: int,
    ) -> dict:
        """
        Check a Scope 1 CO2e value against the trailing 12 months strictly prior to
        the target (year, month) for the same facility and process type.
        """
        try:
            from models import Emission
            from sqlalchemy import or_, and_
            db = self._get_db()

            q = db.session.query(Emission.co2e_total).filter(
                Emission.facility_id == facility_id,
                Emission.process_type == process_type,
                Emission.status == "Verified",
                Emission.co2e_total.isnot(None),
            )
            if year is not None and month is not None:
                q = q.filter(
                    or_(
                        Emission.year < year,
                        and_(Emission.year == year, Emission.month < month),
                    )
                )
            elif year is not None:
                q = q.filter(Emission.year < year)

            historical_raw = q.order_by(Emission.year.desc(), Emission.month.desc()).limit(12).all()
            historical = [float(r[0]) for r in historical_raw if r[0] is not None]
            result = self._z_score_check(co2e, historical)
            result["scope"] = "1"
            result["facility_id"] = facility_id
            result["process_type"] = process_type
            result["value"] = co2e
            return result
        except Exception as e:
            return {"flagged": False, "error": str(e)}

    # ─── Scope 2 ─────────────────────────────────────────────────────────────

    def check_scope2(
        self,
        facility_id: int,
        source_type: str,
        co2e: float,
        year: int,
        month: int,
    ) -> dict:
        """
        Check a Scope 2 CO2e value against the trailing 12 months strictly prior to
        the target (year, month) for the same facility and source type.
        """
        try:
            from models import Scope2Emission
            from sqlalchemy import or_, and_
            db = self._get_db()

            q = db.session.query(Scope2Emission.co2e).filter(
                Scope2Emission.facility_id == facility_id,
                Scope2Emission.source_type == source_type,
                Scope2Emission.status == "Verified",
                Scope2Emission.co2e.isnot(None),
            )
            if year is not None and month is not None:
                q = q.filter(
                    or_(
                        Scope2Emission.year < year,
                        and_(Scope2Emission.year == year, Scope2Emission.month < month),
                    )
                )
            elif year is not None:
                q = q.filter(Scope2Emission.year < year)

            historical_raw = q.order_by(Scope2Emission.year.desc(), Scope2Emission.month.desc()).limit(12).all()
            historical = [float(r[0]) for r in historical_raw if r[0] is not None]
            result = self._z_score_check(co2e, historical)
            result["scope"] = "2"
            result["facility_id"] = facility_id
            result["source_type"] = source_type
            result["value"] = co2e
            return result
        except Exception as e:
            return {"flagged": False, "error": str(e)}

    # ─── Scope 3 ─────────────────────────────────────────────────────────────

    def check_scope3(
        self,
        facility_id: int,
        category: str,
        co2e: float,
        year: int,
        month: int,
    ) -> dict:
        """
        Check a Scope 3 CO2e value against the trailing 12 months strictly prior to
        the target (year, month) for the same facility and category.
        """
        try:
            from models import Scope3Emission
            from sqlalchemy import or_, and_
            db = self._get_db()

            q = db.session.query(Scope3Emission.co2e).filter(
                Scope3Emission.facility_id == facility_id,
                Scope3Emission.category == category,
                Scope3Emission.status == "Verified",
                Scope3Emission.co2e.isnot(None),
            )
            if year is not None and month is not None:
                q = q.filter(
                    or_(
                        Scope3Emission.year < year,
                        and_(Scope3Emission.year == year, Scope3Emission.month < month),
                    )
                )
            elif year is not None:
                q = q.filter(Scope3Emission.year < year)

            historical_raw = q.order_by(Scope3Emission.year.desc(), Scope3Emission.month.desc()).limit(12).all()
            historical = [float(r[0]) for r in historical_raw if r[0] is not None]
            result = self._z_score_check(co2e, historical)
            result["scope"] = "3"
            result["facility_id"] = facility_id
            result["category"] = category
            result["value"] = co2e
            return result
        except Exception as e:
            return {"flagged": False, "error": str(e)}
