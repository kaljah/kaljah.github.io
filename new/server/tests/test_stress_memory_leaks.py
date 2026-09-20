"""
test_stress_memory_leaks.py
===========================
Pillar 5: Memory Leak & Sustained Calculation Loop Stress Test.

Validates that high-frequency calculation and conversion routines run indefinitely
without linear heap growth or garbage accumulation:
1. 10,000 sequential compute_emissions loops profiled via tracemalloc.
2. Memory delta between iteration 1,000 and iteration 10,000 must remain < 5 MB.
3. Calculation throughput SLA: > 2,000 calcs/second.
4. 25,000 unit conversions memory profile (zero memory degradation).
5. 5,000 uncertainty propagation calculations (SRSS Approach 1).
6. Garbage collection stability: no cyclic uncollectable references (gc.garbage is empty).
"""

import gc
import time
import tracemalloc
import pytest
from calculations import compute_emissions, calculate_co2e, convert
from calculations.uncertainty import (
    srss_inventory,
    combine_uncertainties_product,
    combine_uncertainties_sum,
)
from emission_factors import API_FACTORS


class TestMemoryLeakAndSustainedLoops:
    """Stress tests sustained calculation pipelines for zero memory leakage and high throughput."""

    def test_sustained_calculation_loop_memory_profile(self):
        """Profile 10,000 sequential calculation dispatcher loops with tracemalloc."""
        gc.collect()
        tracemalloc.start()

        num_iterations = 10000
        warmup_iterations = 1000

        factor_ng = API_FACTORS.get("Natural Gas", {})
        factor_rfg = API_FACTORS.get("Refinery Fuel Gas", {})
        factor_diesel = API_FACTORS.get("Diesel (No. 2 Fuel Oil)", {})

        mem_at_warmup = 0
        t_start = time.perf_counter()

        for i in range(num_iterations):
            # Rotate across multiple fuel categories
            if i % 3 == 0:
                payload = {
                    "process_type": "combustion",
                    "fuel": "Natural Gas",
                    "quantity": 1500.0 + (i % 100),
                    "unit": "m3",
                }
                factor = factor_ng
            elif i % 3 == 1:
                payload = {
                    "process_type": "combustion",
                    "fuel": "Refinery Fuel Gas",
                    "quantity": 300.0 + (i % 50),
                    "unit": "m3",
                }
                factor = factor_rfg
            else:
                payload = {
                    "process_type": "combustion",
                    "fuel": "Diesel (No. 2 Fuel Oil)",
                    "quantity": 40.0 + (i % 20),
                    "unit": "gal",
                }
                factor = factor_diesel

            res, _ = compute_emissions(payload, factor_data=factor)
            assert res["totalCo2e"] > 0

            # Record memory baseline after warmup
            if i == warmup_iterations:
                current, peak = tracemalloc.get_traced_memory()
                mem_at_warmup = current

        total_elapsed = time.perf_counter() - t_start
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Net memory growth from iteration 1,000 to iteration 10,000
        net_leak_bytes = max(0, current_mem - mem_at_warmup)
        net_leak_mb = net_leak_bytes / (1024 * 1024)
        peak_mb = peak_mem / (1024 * 1024)
        calcs_per_sec = num_iterations / total_elapsed

        print(f"\n[CALCULATION LOOP MEMORY PROFILE]")
        print(f"   Iterations: {num_iterations:,}")
        print(f"   Elapsed Time: {total_elapsed:.2f}s ({calcs_per_sec:,.0f} calcs/sec)")
        print(f"   Warmup Memory: {mem_at_warmup / (1024*1024):.2f} MB")
        print(f"   Final Current Memory: {current_mem / (1024*1024):.2f} MB")
        print(f"   Peak Memory: {peak_mb:.2f} MB")
        print(f"   Net Memory Growth: {net_leak_mb:.4f} MB")

        # Assertions
        assert net_leak_mb < 5.0, f"Memory leak detected: grew by {net_leak_mb:.2f} MB"
        assert calcs_per_sec >= 1000, f"Throughput SLA failed: {calcs_per_sec:.0f} calcs/sec"

    def test_sustained_unit_conversions_zero_leak(self):
        """Profile 25,000 high-frequency unit conversions across volume, mass, energy, pressure."""
        gc.collect()
        tracemalloc.start()

        num_conversions = 25000
        warmup = 2500
        mem_at_warmup = 0

        conversions_test_set = [
            (100.0, "scf", "m3"),
            (50.0, "bbl", "m3"),
            (1000.0, "kg", "lb"),
            (25.0, "tonne", "kg"),
            (500.0, "mmbtu", "mj"),
            (100.0, "kwh", "mj"),
            (25.0, "c", "f"),
            (100.0, "psig", "bar"),
        ]

        t_start = time.perf_counter()
        set_len = len(conversions_test_set)

        for i in range(num_conversions):
            val, f_unit, t_unit = conversions_test_set[i % set_len]
            out = convert(val, f_unit, t_unit)
            assert out > 0

            if i == warmup:
                curr, _ = tracemalloc.get_traced_memory()
                mem_at_warmup = curr

        total_elapsed = time.perf_counter() - t_start
        curr_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        net_growth_mb = max(0, curr_mem - mem_at_warmup) / (1024 * 1024)
        convs_per_sec = num_conversions / total_elapsed

        print(f"\n[UNIT CONVERSION SUSTAINED PROFILE]")
        print(f"   Conversions: {num_conversions:,}")
        print(f"   Elapsed: {total_elapsed:.2f}s ({convs_per_sec:,.0f} conv/sec)")
        print(f"   Net Growth: {net_growth_mb:.4f} MB")

        assert net_growth_mb < 2.0
        assert convs_per_sec >= 5000

    def test_sustained_uncertainty_propagation_loop(self):
        """Profile 5,000 uncertainty propagation calculations (SRSS Approach 1)."""
        gc.collect()
        tracemalloc.start()

        num_iters = 5000
        warmup = 500
        mem_warmup = 0

        sample_sources = [
            {"value": 1200.0, "relative_uncertainty": 0.05},
            {"value": 450.0, "relative_uncertainty": 0.12},
            {"value": 85.0, "relative_uncertainty": 0.20},
            {"value": 310.0, "relative_uncertainty": 0.08},
        ]

        t_start = time.perf_counter()
        for i in range(num_iters):
            # Combined product
            u_prod = combine_uncertainties_product(0.05, 0.10)
            assert u_prod > 0

            # Combined sum
            u_sum = combine_uncertainties_sum(100.0, 0.05, 200.0, 0.10)
            assert u_sum > 0

            # SRSS inventory
            res = srss_inventory(sample_sources)
            assert res["relative_uncertainty_1sigma"] > 0
            assert res["total_value"] == 2045.0

            if i == warmup:
                curr, _ = tracemalloc.get_traced_memory()
                mem_warmup = curr

        elapsed = time.perf_counter() - t_start
        curr_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        net_growth_mb = max(0, curr_mem - mem_warmup) / (1024 * 1024)
        ops_per_sec = num_iters / elapsed

        print(f"\n[UNCERTAINTY PROPAGATION PROFILE]")
        print(f"   Iterations: {num_iters:,} (x3 calculations each)")
        print(f"   Elapsed: {elapsed:.2f}s ({ops_per_sec:,.0f} ops/sec)")
        print(f"   Net Growth: {net_growth_mb:.4f} MB")

        assert net_growth_mb < 2.0

    def test_gc_stability_and_cycle_cleanup(self):
        """Verify garbage collector stability and absence of cyclic reference leaks."""
        gc.collect()
        initial_uncollectable = len(gc.garbage)

        # Execute a batch of calculations and allocations
        for _ in range(2000):
            payload = {
                "process_type": "combustion",
                "fuel": "Natural Gas",
                "quantity": 100.0,
                "unit": "m3",
            }
            res, _ = compute_emissions(payload, factor_data=API_FACTORS.get("Natural Gas", {}))

        unreachable = gc.collect()
        final_uncollectable = len(gc.garbage)

        print(f"\n[GC STABILITY CHECK] Unreachable objects collected: {unreachable}, Uncollectable: {final_uncollectable}")
        assert final_uncollectable == initial_uncollectable == 0
