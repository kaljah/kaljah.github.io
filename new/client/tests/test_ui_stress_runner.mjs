/**
 * test_ui_stress_runner.mjs
 * =========================
 * Master Industrial UI Stress Test Runner.
 *
 * Sequentially orchestrates and benchmarks all UI stress test suites:
 * - Pillar 1: Large Dataset Rendering & Table Virtualization (10,000 records).
 * - Pillar 2: Rapid Concurrent Filter & Search Mutation Stress Test (1,000 mutations).
 * - Pillar 3: Massive Client-Side File Ingestion & Parsing (50,000 rows / 6.3 MB).
 * - Pillar 4: Extreme Numerical, Astronomical & Boundary Display Resilience (10^30, NaN, Inf, RTL).
 */

import { performance } from "perf_hooks";
import { runLargeDatasetStressTest } from "./test_ui_stress_large_dataset.mjs";
import { runFuzzingMutationsStressTest } from "./test_ui_stress_fuzzing_mutations.mjs";
import { runBulkParsingStressTest } from "./test_ui_stress_bulk_parsing.mjs";
import { runBoundaryDisplayStressTest } from "./test_ui_stress_boundary_display.mjs";

async function runAllUiStressTests() {
  console.log("############################################################");
  console.log("###   INDUSTRIAL UI STRESS TEST MASTER SUITE STARTING    ###");
  console.log("############################################################");

  const suiteStart = performance.now();
  const results = [];

  try {
    const t1 = performance.now();
    await runLargeDatasetStressTest();
    results.push({ name: "Pillar 1: Large Dataset & Table Virtualization", time: performance.now() - t1, status: "PASS" });

    const t2 = performance.now();
    await runFuzzingMutationsStressTest();
    results.push({ name: "Pillar 2: Rapid Filter Fuzzing & Race Defense", time: performance.now() - t2, status: "PASS" });

    const t3 = performance.now();
    await runBulkParsingStressTest();
    results.push({ name: "Pillar 3: Massive Client-Side CSV Parsing", time: performance.now() - t3, status: "PASS" });

    const t4 = performance.now();
    await runBoundaryDisplayStressTest();
    results.push({ name: "Pillar 4: Extreme Numerical & Boundary Display", time: performance.now() - t4, status: "PASS" });

    const totalElapsed = (performance.now() - suiteStart) / 1000;

    console.log("\n============================================================");
    console.log("###       MASTER UI STRESS TEST SUMMARY REPORT           ###");
    console.log("============================================================");
    for (const r of results) {
      console.log(`   [${r.status}] ${r.name.padEnd(48)} (${r.time.toFixed(1)} ms)`);
    }
    console.log("------------------------------------------------------------");
    console.log(`>>> TOTAL EXECUTION TIME: ${totalElapsed.toFixed(2)}s`);
    console.log(">>> ALL UI STRESS TEST PILLARS PASSED (100% SUCCESS)");
    console.log("============================================================\n");

    process.exit(0);
  } catch (error) {
    console.error("\n!!! UI STRESS TEST SUITE FAILED !!!", error);
    process.exit(1);
  }
}

runAllUiStressTests();
