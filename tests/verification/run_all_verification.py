"""
MASTER VERIFICATION SUITE RUNNER (PHASE 12 REGRESSION LOCK)
===========================================================
Executes the comprehensive verification suite across all phases:
- Phase 1: Golden Cases & Compendium Exhibits (test_golden_cases.py)
- Phase 2: Factor & Constant Provenance (test_factor_provenance.py)
- Phase 3: Pint Dimensional Safety (test_unit_safety_pint.py)
- Phase 4: Property-Based & Metamorphic Testing (test_property_metamorphic.py)
- Phase 6: Differential Testing (test_differential.py)
- Phase 7: KPI & Dashboard Reconciliation (test_kpi_reconciliation.py)
- Phase 8: API Contract & Fuzzing (test_api_contract_fuzzing.py)
- Phase 9: Float & Precision Audit (test_float_precision.py)
- Phase 11: Performance & Scaling (test_performance_scaling.py)

Single command entry point for local and CI regression gating.
Exits with code 0 on complete green pass; non-zero if any test fails.
"""

import sys
import os
import time
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

MODULES = [
    ("Phase 1: Golden Cases & Compendium Exhibits", "tests/verification/test_golden_cases.py"),
    ("Phase 2: Factor & Constant Provenance", "tests/verification/test_factor_provenance.py"),
    ("Phase 3: Pint Dimensional Safety", "tests/verification/test_unit_safety_pint.py"),
    ("Phase 4: Property-Based & Metamorphic Invariants", "tests/verification/test_property_metamorphic.py"),
    ("Phase 6: 3-Way Differential Parity (Vectorized vs Oracle vs App)", "tests/verification/test_differential.py"),
    ("Phase 7: KPI & Dashboard Reconciliation", "tests/verification/test_kpi_reconciliation.py"),
    ("Phase 8: API Contract & Fuzzing", "tests/verification/test_api_contract_fuzzing.py"),
    ("Phase 9: Float Accumulation & Numeric Precision", "tests/verification/test_float_precision.py"),
    ("Phase 11: Performance Scaling & Cache Invariance", "tests/verification/test_performance_scaling.py"),
]


def run_verification_suite():
    print("=" * 80)
    print("      GHG EMISSIONS CALCULATOR COMPREHENSIVE VERIFICATION SUITE")
    print("=" * 80)
    print(f"Repository Root: {REPO_ROOT}")
    print(f"Python Runtime : {sys.executable}\n")

    overall_start = time.perf_counter()
    results = []

    for phase_name, module_path in MODULES:
        full_path = os.path.join(REPO_ROOT, module_path)
        if not os.path.exists(full_path):
            print(f"[MISSING] {phase_name}: {module_path} not found!")
            results.append((phase_name, module_path, "MISSING", 0.0))
            continue

        print(f"Running [{phase_name}]...")
        t0 = time.perf_counter()
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", module_path, "-q", "--tb=short"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        duration = time.perf_counter() - t0

        if proc.returncode == 0:
            print(f"  -> PASS ({duration:.2f}s)")
            status = "PASS"
        else:
            print(f"  -> FAIL ({duration:.2f}s)")
            print("--- Output ---")
            print(proc.stdout)
            print(proc.stderr)
            print("--------------")
            status = "FAIL"

        results.append((phase_name, module_path, status, duration))

    total_duration = time.perf_counter() - overall_start

    print("\n" + "=" * 80)
    print("                     VERIFICATION SUMMARY MATRIX")
    print("=" * 80)
    print(f"{'Phase / Test Module':<55} | {'Status':^8} | {'Time (s)':^8}")
    print("-" * 80)
    passed_count = 0
    for name, path, status, dur in results:
        status_str = f"\033[92m{status}\033[0m" if status == "PASS" else f"\033[91m{status}\033[0m"
        print(f"{name:<55} | {status_str:^17} | {dur:>7.2f}s")
        if status == "PASS":
            passed_count += 1

    print("-" * 80)
    print(f"Total Modules Evaluated: {len(results)}")
    print(f"Total Modules Passed   : {passed_count}")
    print(f"Total Modules Failed   : {len(results) - passed_count}")
    print(f"Total Execution Time   : {total_duration:.2f}s")
    print("=" * 80)

    if passed_count == len(results):
        print("\nALL VERIFICATION MODULES PASSED CLEANLY. REGRESSION LOCK ESTABLISHED.\n")
        return 0
    else:
        print("\nONE OR MORE VERIFICATION MODULES FAILED. INVESTIGATION REQUIRED.\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_verification_suite())
