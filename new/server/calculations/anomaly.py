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
        Returns flagged=True if |z| > 3 (99.7% confidence outlier) or outside IQR fence.
        """
        if value is None or math.isnan(value) or math.isinf(value):
            return {
                "flagged": True,
                "z_score": None,
                "reason": "invalid_value",
                "message": f"Value {value} is not a valid finite number.",
                "expected_range": None,
            }

        if not historical or len(historical) < 3:
            return {"flagged": False, "reason": "insufficient_history", "z_score": None, "expected_range": None}

        n = len(historical)
        mean = sum(historical) / n
        # Use Bessel's correction (sample variance n-1) for small sample sizes
        variance = sum((x - mean) ** 2 for x in historical) / max(1, n - 1 if n > 1 else 1)
        std = math.sqrt(variance) if variance > 0 else 0

        if std == 0:
            # All historical values identical — flag only if new value differs significantly
            if (abs(mean) > 0 and abs(value - mean) / abs(mean) > 0.5) or (mean == 0 and abs(value) > 0):
                return {
                    "flagged": True,
                    "z_score": None,
                    "mean": mean,
                    "std": 0,
                    "expected_range": [mean * 0.5, mean * 1.5] if abs(mean) > 0 else [0.0, 0.0],
                    "reason": "constant_history_deviation",
                    "message": f"Historical values are constant ({mean:.1f}) but new value is {value:.1f}."
                }
            return {"flagged": False, "z_score": 0, "expected_range": [mean, mean]}

        z = (value - mean) / std

        # IQR fence as secondary check (requires at least 4 observations for quartiles)
        sorted_h = sorted(historical)
        flagged_iqr = False
        lower_fence = 0.0
        upper_fence = 0.0
        if len(sorted_h) >= 4:
            def _quantile(sorted_vals, p):
                n = len(sorted_vals)
                pos = p * (n - 1)
                idx = int(pos)
                frac = pos - idx
                if idx + 1 < n:
                    return sorted_vals[idx] + frac * (sorted_vals[idx + 1] - sorted_vals[idx])
                return sorted_vals[idx]

            q1 = _quantile(sorted_h, 0.25)
            q3 = _quantile(sorted_h, 0.75)
            iqr = q3 - q1
            lower_fence = q1 - 3 * iqr
            upper_fence = q3 + 3 * iqr
            flagged_iqr = iqr > 0 and (value < lower_fence or value > upper_fence)

        flagged_z = abs(z) > 3

        flagged = flagged_z or flagged_iqr
        if flagged_z:
            expected_low = max(0.0, mean - 3 * std)
            expected_high = mean + 3 * std
            msg = (
                f"Value {value:.2f} is {abs(z):.1f} standard deviations from the average of the same source "
                f"over the previous 12 months ({mean:.2f} ± {std:.2f}, {n} records). "
                f"Expected range: [{expected_low:.2f} – {expected_high:.2f}]."
            )
            exp_range = [round(expected_low, 2), round(expected_high, 2)]
        elif flagged_iqr:
            msg = (
                f"Value {value:.2f} is an IQR outlier outside the interquartile range fence "
                f"[{lower_fence:.2f} – {upper_fence:.2f}]."
            )
            exp_range = [round(lower_fence, 2), round(upper_fence, 2)]
        else:
            expected_low = max(0.0, mean - 3 * std)
            expected_high = mean + 3 * std
            msg = None
            exp_range = [round(expected_low, 2), round(expected_high, 2)]

        return {
            "flagged": flagged,
            "z_score": round(z, 2),
            "mean": round(mean, 2),
            "std": round(std, 2),
            "expected_range": exp_range,
            "iqr_flagged": flagged_iqr,
            "reason": "z_score" if flagged_z else ("iqr" if flagged_iqr else None),
            "message": msg
        }

    # ─── History: the same series over the 12 calendar months before the record ─────
    # A Scope 1 series is one facility, one process and one source (equipment ID, else fuel /
    # activity). The history used to be the last 12 *records* of the facility and process: one
    # month with many sources filled the window and every source was compared with the others
    # (a 100k-row import flagged 15 % of its rows), while the message said "12-month average".

    _SERIES = {
        "1": ("Emission", "process_type", "co2e_total"),
        "2": ("Scope2Emission", "source_type", "co2e"),
        "3": ("Scope3Emission", "category", "co2e"),
    }

    @staticmethod
    def _source_filter(m, source):
        """(column, value) restricting a Scope 1 series to one source, or None."""
        if not source:
            return None
        kind, value = source
        if value in (None, ""):
            return None
        return getattr(m, "equipment_id" if kind == "equipment" else "fuel_type"), value

    def _rows(self, scope, facility_id, key, source=None, year=None):
        """(year, month, value, status, qa_flag) of a series; from year - 1 on when a year is given."""
        import models

        name, key_col, val_col = self._SERIES[scope]
        m = getattr(models, name)
        q = self._get_db().session.query(m.year, m.month, getattr(m, val_col), m.status, m.qa_flag).filter(
            m.facility_id == facility_id, getattr(m, key_col) == key, getattr(m, val_col).isnot(None))
        sf = self._source_filter(m, source) if scope == "1" else None
        if sf is not None:
            q = q.filter(sf[0] == sf[1])
        if year is not None:
            q = q.filter(m.year >= int(year) - 1)
        return q.all()

    @staticmethod
    def _history(rows, year, month):
        """Values in the 12 calendar months strictly before (year, month): Verified records, or the
        unflagged ones when fewer than 3 are Verified (onboarding)."""
        def in_window(r):
            ry, rm = r[0] or 0, r[1] or 0
            if year is None:
                return True
            if month is None:
                return ry == int(year) - 1
            d = (int(year) * 12 + int(month)) - (ry * 12 + rm)
            return 1 <= d <= 12

        win = [r for r in rows if in_window(r)]
        historical = [float(r[2]) for r in win if r[3] == "Verified"]
        if len(historical) < 3:
            fb = [float(r[2]) for r in win if r[4] is None]
            if len(fb) >= len(historical):
                historical = fb
        return historical

    def _check(self, scope, facility_id, key, value, year, month, source=None):
        try:
            historical = self._history(self._rows(scope, facility_id, key, source, year), year, month)
            result = self._z_score_check(value, historical)
            result.update(scope=scope, facility_id=facility_id, value=value, history_n=len(historical))
            return result
        except Exception as e:
            return {"flagged": False, "error": str(e)}

    def check_scope1(self, facility_id: int, process_type: str, co2e: float, year: int, month: int,
                     source=None) -> dict:
        """Scope 1 CO2e against the same facility, process and source over the previous 12 months.
        source: ("equipment", equipment_id) or ("fuel", fuel_type); None compares the whole process."""
        res = self._check("1", facility_id, process_type, co2e, year, month, source)
        res.setdefault("process_type", process_type)
        return res

    def check_scope2(self, facility_id: int, source_type: str, co2e: float, year: int, month: int) -> dict:
        """Scope 2 CO2e against the same facility and source type over the previous 12 months."""
        res = self._check("2", facility_id, source_type, co2e, year, month)
        res.setdefault("source_type", source_type)
        return res

    def check_scope3(self, facility_id: int, category: str, co2e: float, year: int, month: int) -> dict:
        """Scope 3 CO2e against the same facility and category over the previous 12 months."""
        res = self._check("3", facility_id, category, co2e, year, month)
        res.setdefault("category", category)
        return res


def scope1_source(equipment_id=None, fuel_type=None):
    """The source key of a Scope 1 record for the anomaly series (equipment ID first, else fuel)."""
    if equipment_id not in (None, "") and str(equipment_id).strip():
        return ("equipment", str(equipment_id).strip())
    if fuel_type not in (None, "") and str(fuel_type).strip():
        return ("fuel", str(fuel_type).strip())
    return None


# ── Hard plausibility bounds for a single record (audit BUG-007) ─────────────────
# The largest single industrial sources emit on the order of 10-30 Mt CO2e per YEAR, so one
# record (one source, one month) above 100 Mt is certainly a data-entry error, and anything
# above 1 Mt needs a human look before it can count as Verified.
PLAUSIBILITY_REJECT_TCO2E = 1e8
PLAUSIBILITY_FLAG_TCO2E = 1e6


def plausibility_check(co2e_tonnes, z_flag=None):
    """Return (verdict, message): verdict is "reject", "flag" or None."""
    try:
        v = float(co2e_tonnes or 0)
    except (TypeError, ValueError):
        return "reject", "Calculated emissions are not a number"
    if v > PLAUSIBILITY_REJECT_TCO2E:
        return "reject", (f"Implausible value: {v:,.0f} tCO2e in one record exceeds {PLAUSIBILITY_REJECT_TCO2E:,.0f} t; "
                          "check the quantity and unit")
    if v > PLAUSIBILITY_FLAG_TCO2E:
        return "flag", f"Plausibility review: {v:,.0f} tCO2e in one record exceeds {PLAUSIBILITY_FLAG_TCO2E:,.0f} t"
    if z_flag:
        return "flag", z_flag
    return None, None


class BatchAnomalyDetector(AnomalyDetector):
    """Same checks as AnomalyDetector for a bulk import: each series' history is read once and
    the 12-month windows are taken in memory (one query per series instead of one per row)."""

    def __init__(self, db_session=None):
        super().__init__(db_session)
        self._cache = {}
        # the import flushes its rows in batches before the commit: the history is the data that
        # existed when the import started, never the file's own earlier rows
        self._max_id = {}
        try:
            import models
            from sqlalchemy import func

            for sc, (name, _k, _v) in self._SERIES.items():
                m = getattr(models, name)
                self._max_id[sc] = self._get_db().session.query(func.max(m.id)).scalar() or 0
        except Exception:
            self._max_id = {}

    def _rows(self, scope, facility_id, key, source=None, year=None):
        # one query per facility / process series (sources are filtered in memory: a query per source
        # tripled the import time when every row has its own equipment ID)
        ck = (scope, facility_id, key)
        if ck not in self._cache:
            import models

            name, key_col, val_col = self._SERIES[scope]
            m = getattr(models, name)
            cols = [m.year, m.month, getattr(m, val_col), m.status, m.qa_flag]
            if scope == "1":
                cols += [m.equipment_id, m.fuel_type]
            q = self._get_db().session.query(*cols).filter(
                m.facility_id == facility_id, getattr(m, key_col) == key, getattr(m, val_col).isnot(None))
            if scope in self._max_id:
                q = q.filter(m.id <= self._max_id[scope])
            rows = q.all()
            by_source = {}
            for r in rows:
                by_source.setdefault(None, []).append(r[:5])
                if scope == "1":
                    if r[5] not in (None, ""):
                        by_source.setdefault(("equipment", r[5]), []).append(r[:5])
                    if r[6] not in (None, ""):
                        by_source.setdefault(("fuel", r[6]), []).append(r[:5])
            self._cache[ck] = by_source
        by_source = self._cache[ck]
        if scope == "1" and source and source[1] not in (None, ""):
            return by_source.get(source, [])
        return by_source.get(None, [])
