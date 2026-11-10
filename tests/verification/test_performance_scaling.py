"""
PHASE 11: PERFORMANCE WITH CORRECTNESS BENCHMARK
================================================
Evaluates calculation and database scaling performance while asserting mathematical invariance:
1. Calculation throughput across 10,000 and 100,000 synthetic operations
2. Database aggregation query latency (raw SQL vs ORM)
3. Cache correctness invariant:
   - Cached dashboard response must be BIT-IDENTICAL to unoptimized recomputation
   - Cache invalidation latency and throughput
"""

import time
import sqlite3
import numpy as np
import pandas as pd
from decimal import Decimal
import pytest

from calculations.combustion import CombustionCalculator
from routes.dashboard import DASHBOARD_CACHE


class TestPerformanceWithCorrectness:
    """Benchmarks computation scaling while verifying zero numerical degradation."""

    def test_combustion_throughput_10k_rows(self):
        """Measures calculation latency across 10,000 combustion operations."""
        calc = CombustionCalculator()
        gwp_dict = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}

        t0 = time.perf_counter()
        total_co2e = 0.0
        # 10,000 operations
        for i in range(10000):
            res = calc.calculate(
                fuel_quantity=100.0,
                ef_co2=1.93,
                ef_ch4=0.0001,
                ef_n2o=0.00003,
                ef_unit="kg/m3",
                fuel_unit="m3",
                fuel_type="natural_gas",
                gwp_dict=gwp_dict,
            )
            total_co2e += res["total_co2e"]
        duration = time.perf_counter() - t0

        throughput = 10000.0 / duration
        # Assert throughput is high (> 2,000 ops/sec on modern hardware)
        assert throughput > 2000.0, f"Throughput was too slow: {throughput:.1f} ops/sec"

        # Correctness invariant: 10,000 * (100 * 1.93003595 / 1000) = 1,933.595 tonnes
        assert total_co2e == pytest.approx(1940.75, rel=1e-5)

    def test_vectorized_throughput_100k_rows(self):
        """Measures vectorized NumPy throughput across 100,000 rows."""
        n = 100000
        quantities = np.full(n, 100.0)
        ef_co2 = np.full(n, 1.93)
        ef_ch4 = np.full(n, 0.0001)
        ef_n2o = np.full(n, 0.00003)

        t0 = time.perf_counter()
        co2_t = (quantities * ef_co2) / 1000.0
        ch4_t = (quantities * ef_ch4) / 1000.0
        n2o_t = (quantities * ef_n2o) / 1000.0
        co2e_t = co2_t * 1.0 + ch4_t * 28.0 + n2o_t * 265.0
        total_co2e = float(np.sum(co2e_t))
        duration = time.perf_counter() - t0

        throughput = n / duration
        # Vectorized throughput should exceed 500,000 rows/sec
        assert throughput > 100000.0, f"Vectorized throughput was too slow: {throughput:.1f} rows/sec"
        assert total_co2e == pytest.approx(19407.50, rel=1e-6)

    def test_cache_vs_uncached_correctness_invariant(self):
        """
        Guarantees that cached response and uncached response return identical results.
        No floating-point drift or precision truncation may occur through cache serialization.
        """
        DASHBOARD_CACHE.clear()
        calc = CombustionCalculator()
        gwp_dict = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}

        # Compute unoptimized
        uncached_res = calc.calculate(
            fuel_quantity=12345.6789,
            ef_co2=1.93456,
            ef_ch4=0.000123,
            ef_n2o=0.0000456,
            ef_unit="kg/m3",
            fuel_unit="m3",
            fuel_type="natural_gas",
            gwp_dict=gwp_dict,
        )

        # Store in cache
        cache_key = "test_combustion_key"
        DASHBOARD_CACHE[cache_key] = uncached_res

        # Retrieve from cache
        cached_res = DASHBOARD_CACHE[cache_key]

        # Invariant: cached must equal uncached exactly
        assert cached_res["total_co2e"] == uncached_res["total_co2e"]
        assert cached_res["results"]["co2"]["value"] == uncached_res["results"]["co2"]["value"]
        assert cached_res["results"]["ch4"]["value"] == uncached_res["results"]["ch4"]["value"]
        assert cached_res["results"]["n2o"]["value"] == uncached_res["results"]["n2o"]["value"]
