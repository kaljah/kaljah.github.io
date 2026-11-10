"""
PHASE 9: FLOAT AND PRECISION AUDIT SUITE
========================================
Audits floating-point precision, accumulation error, and rounding policies:
1. Accumulation Drift on Large Sums (100,000 increments of 0.1 vs Decimal arithmetic)
2. Premature Rounding vs Final Display Rounding
3. SQLite Numeric Affinity & Integer Division Safety
4. String-to-number locale coercion ('1,500.50' vs '1.500,50')
"""

import math
import sqlite3
from decimal import Decimal, getcontext
import pytest

getcontext().prec = 50


class TestFloatPrecisionAndAccumulation:
    """Audits floating-point accumulation error and numeric fidelity."""

    def test_float_accumulation_drift_100k_rows(self):
        """
        Quantifies IEEE 754 floating-point drift over 100,000 iterative additions.
        Adding 0.1 tonnes 100,000 times:
        Exact Decimal truth: 10,000.00000000000000000000 tonnes.
        IEEE 754 float sum: exhibits binary representation drift (~1.88e-11 relative).
        """
        n = 100000
        step_dec = Decimal("0.1")
        step_flt = 0.1

        # Decimal exact accumulator
        total_dec = Decimal("0.0")
        for _ in range(n):
            total_dec += step_dec

        # Float accumulator
        total_flt = 0.0
        for _ in range(n):
            total_flt += step_flt

        assert total_dec == Decimal("10000.0")

        drift = abs(float(total_dec) - total_flt)
        # Verify drift is bounded and precisely matches IEEE 754 float epsilon propagation
        assert drift < 1e-7, f"Float accumulation drift exceeded threshold: {drift}"
        assert drift == pytest.approx(1.8848e-8, rel=1e-2)

    def test_intermediate_rounding_drift(self):
        """
        Proves that premature rounding during intermediate calculation steps causes
        systematic error compared to rounding only at display time.
        """
        # Scenario: 1,000 emission sources each generating 1.0049 tonnes
        raw_values = [1.0049] * 1000

        # Method A (Standard Compliant): Preserve full precision, round at display
        sum_raw = sum(raw_values)
        display_sum_a = round(sum_raw, 2) # round(1004.9, 2) = 1004.90

        # Method B (Defective): Round each intermediate item to 2 decimal places before summing
        rounded_items = [round(v, 2) for v in raw_values] # each becomes 1.00
        display_sum_b = sum(rounded_items) # 1000.00

        # Discrepancy: 4.90 tonnes lost due to premature truncation!
        drift = abs(display_sum_a - display_sum_b)
        assert drift == pytest.approx(4.90, rel=1e-3)

    def test_sqlite_integer_division_and_coercion(self, tmp_path):
        """
        Verifies SQLite numeric behavior:
        - Division of integers in SQL: 'CAST(a AS REAL) / b' vs integer division 'a / b'
        - String coercion of decimal numbers vs comma numbers
        """
        db_path = str(tmp_path / "sqlite_num.db")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        cur.execute("CREATE TABLE test_num (id INT, int_val INT, real_val REAL, str_val TEXT)")
        cur.execute("INSERT INTO test_num VALUES (1, 1, 1.0, '1500.75')")
        cur.execute("INSERT INTO test_num VALUES (2, 2, 2.0, '1,500.75')")

        # Integer division in SQLite: 1 / 2 yields 0!
        cur.execute("SELECT int_val / 2 FROM test_num WHERE id = 1")
        int_div_result = cur.fetchone()[0]
        assert int_div_result == 0, "SQLite did not truncate integer division 1 / 2 to 0"

        # Explicit float division: CAST(int_val AS REAL) / 2 yields 0.5
        cur.execute("SELECT CAST(int_val AS REAL) / 2 FROM test_num WHERE id = 1")
        real_div_result = cur.fetchone()[0]
        assert real_div_result == 0.5

        # String coercion: '1500.75' casts cleanly to 1500.75
        cur.execute("SELECT CAST(str_val AS REAL) FROM test_num WHERE id = 1")
        clean_cast = cur.fetchone()[0]
        assert clean_cast == 1500.75

        # Comma string: SQLite CAST('1,500.75' AS REAL) truncates at comma to 1.0!
        cur.execute("SELECT CAST(str_val AS REAL) FROM test_num WHERE id = 2")
        comma_cast = cur.fetchone()[0]
        assert comma_cast == 1.0, "SQLite unexpectedly parsed comma-formatted string"

        conn.close()
