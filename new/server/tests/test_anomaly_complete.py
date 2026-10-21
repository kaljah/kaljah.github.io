"""calculations/anomaly.py: the z-score / IQR check, the 12-month window, the source series, the batch detector
and the plausibility bounds.
"""
import pytest

from calculations.anomaly import AnomalyDetector, BatchAnomalyDetector, plausibility_check, scope1_source


@pytest.fixture
def d():
    return AnomalyDetector()


@pytest.mark.parametrize("value", [None, float("nan"), float("inf")])
def test_invalid_value_flagged(d, value):
    assert d._z_score_check(value, [1, 2, 3])["reason"] == "invalid_value"


def test_short_and_constant_history(d):
    assert d._z_score_check(5, [1, 2])["reason"] == "insufficient_history"
    same = d._z_score_check(100, [100, 100, 100])
    assert same == {"flagged": False, "z_score": 0, "expected_range": [100, 100]}
    off = d._z_score_check(200, [100, 100, 100])
    assert off["reason"] == "constant_history_deviation" and off["expected_range"] == [50, 150]
    zero = d._z_score_check(1, [0, 0, 0])
    assert zero["flagged"] and zero["expected_range"] == [0.0, 0.0]


def test_tiny_spread_history(d):
    hist = [1.0, 1.0 + 1e-9, 1.0 - 1e-9]
    assert d._z_score_check(1.0, hist)["z_score"] == 0
    assert d._z_score_check(2.0, hist)["z_score"] == 999.0
    assert d._z_score_check(0.0, hist)["z_score"] == -999.0


def test_z_score_outlier_and_in_range(d):
    hist = [10, 12, 11, 13, 9, 10, 12, 11, 10, 12]
    out = d._z_score_check(100, hist)
    assert out["flagged"] and out["reason"] == "z_score" and "standard deviations" in out["message"]
    ok = d._z_score_check(11, hist)
    assert not ok["flagged"] and ok["message"] is None and ok["reason"] is None


def test_iqr_outlier_below_three_sigma(d):
    # a tight core with one far historical point: the spread is large (no z flag) but the IQR fence is narrow
    hist = [10, 10, 10.1, 10.2, 10, 10.1, 10, 1000]
    res = d._z_score_check(30, hist)
    assert res["iqr_flagged"] and res["reason"] == "iqr" and "interquartile" in res["message"]
    assert abs(res["z_score"]) < 3


def test_history_window():
    rows = [(2024, 12, 1.0, "Verified", None), (2025, 1, 2.0, "Verified", None), (2025, 6, 3.0, "Pending", None),
            (2025, 7, 4.0, "Pending", "z"), (2023, 5, 9.0, "Verified", None), (None, None, 7.0, "Verified", None)]
    assert AnomalyDetector._history(rows, None, None) == [1.0, 2.0, 9.0, 7.0]
    assert AnomalyDetector._history(rows, 2024, None) == [9.0]                                    # the year before
    assert AnomalyDetector._history(rows, 2025, 8) == [1.0, 2.0, 3.0]                            # unflagged fallback (Dec 24, Jan 25, Jun 25)
    verified = [(2025, m, float(m), "Verified", None) for m in (1, 2, 3)] + [(2025, 4, 9.0, "Pending", "x")]
    assert AnomalyDetector._history(verified, 2025, 5) == [1.0, 2.0, 3.0]
    few = [(2025, 1, 1.0, "Verified", "a"), (2025, 2, 2.0, "Verified", None), (2025, 3, 3.0, "Pending", "x")]
    assert AnomalyDetector._history(few, 2025, 5) == [1.0, 2.0]                                   # fallback is shorter


def test_source_key_and_filter():
    from models import Emission

    assert scope1_source(" P-101 ", "Diesel") == ("equipment", "P-101")
    assert scope1_source("  ", "Diesel") == ("fuel", "Diesel")
    assert scope1_source(None, " ") is None
    assert AnomalyDetector._source_filter(Emission, None) is None
    assert AnomalyDetector._source_filter(Emission, ("fuel", "")) is None
    col, value = AnomalyDetector._source_filter(Emission, ("equipment", "P-1"))
    assert col is Emission.equipment_id and value == "P-1"


def test_plausibility_bounds():
    assert plausibility_check("abc")[0] == "reject"
    assert plausibility_check(float("nan"))[0] == "reject" and plausibility_check(float("-inf"))[0] == "reject"
    assert plausibility_check(2e8)[0] == "reject"
    assert plausibility_check(2e6)[0] == "flag"
    assert plausibility_check(10, z_flag="z outlier") == ("flag", "z outlier")
    assert plausibility_check(None) == (None, None)


def test_check_reports_errors_unflagged():
    class Broken:
        @property
        def session(self):
            raise RuntimeError("no database")

    res = AnomalyDetector(Broken()).check_scope2(1, "electricity", 5.0, 2025, 1)
    assert res == {"flagged": False, "error": "no database", "source_type": "electricity"}
    batch = BatchAnomalyDetector(Broken())
    assert batch._max_id == {}
    assert batch.check_scope3(1, "Category 1", 5.0, 2025, 1)["error"] == "no database"


@pytest.fixture
def series(app):
    from extensions import db
    from models import Emission, Facility, Scope2Emission, Scope3Emission

    with app.app_context():
        fac = Facility(name="Anomaly series T", code="ANOM-T")
        db.session.add(fac)
        db.session.flush()
        rows = [Emission(facility_id=fac.id, year=2025, month=m, process_type="combustion",
                         fuel_type="Diesel" if m < 6 else None, equipment_id="G-1" if m % 2 else None, quantity=1, co2e_total=100.0 + m, status="Verified")
                for m in range(1, 7)]
        rows += [Scope2Emission(facility_id=fac.id, year=2025, month=m, source_type="electricity", co2e=50.0 + m,
                                status="Verified") for m in range(1, 5)]
        rows += [Scope3Emission(facility_id=fac.id, year=2025, month=m, category="Category 1", co2e=20.0 + m,
                                status="Verified") for m in range(1, 5)]
        db.session.add_all(rows)
        db.session.commit()
        fac_id = fac.id
    yield fac_id
    with app.app_context():
        for m in (Emission, Scope2Emission, Scope3Emission):
            m.query.filter_by(facility_id=fac_id).delete()
        Facility.query.filter_by(id=fac_id).delete()
        db.session.commit()


def test_series_checks(app, series):
    from extensions import db

    with app.app_context():
        d = AnomalyDetector(db)
        whole = d.check_scope1(series, "combustion", 5000.0, 2025, 7)
        assert whole["flagged"] and whole["history_n"] == 6 and whole["process_type"] == "combustion"
        equip = d.check_scope1(series, "combustion", 104.0, 2025, 7, source=("equipment", "G-1"))
        assert equip["history_n"] == 3 and not equip["flagged"]                                   # months 1, 3, 5
        assert d.check_scope1(series, "combustion", 104.0, None, None)["history_n"] == 6           # no year: all
        assert d.check_scope2(series, "electricity", 500.0, 2025, 5)["flagged"]
        assert d.check_scope3(series, "Category 1", 22.5, 2025, 5)["flagged"] is False


def test_batch_detector_reads_each_series_once(app, series):
    from extensions import db
    from models import Emission

    with app.app_context():
        b = BatchAnomalyDetector()
        db.session.add(Emission(facility_id=series, year=2025, month=7, process_type="combustion", quantity=1,
                                co2e_total=9e5, status="Verified"))                               # after the start
        db.session.flush()
        assert b.check_scope1(series, "combustion", 5000.0, 2025, 8)["history_n"] == 6
        assert b.check_scope1(series, "combustion", 104.0, 2025, 8, source=("fuel", "Diesel"))["history_n"] == 5
        assert b.check_scope1(series, "combustion", 104.0, 2025, 8, source=("equipment", "G-1"))["history_n"] == 3
        assert b.check_scope1(series, "combustion", 104.0, 2025, 8, source=("equipment", ""))["history_n"] == 6
        assert len(b._cache) == 1
        db.session.rollback()
        b._max_id = {}                                                                            # no start snapshot
        assert b.check_scope2(series, "electricity", 53.0, 2025, 5)["history_n"] == 4
