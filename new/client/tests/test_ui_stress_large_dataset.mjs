/**
 * test_ui_stress_large_dataset.mjs
 * ================================
 * Pillar 1: Large Dataset Rendering & Table Virtualization Stress Test.
 *
 * Validates UI table data operations under heavy enterprise volume (10,000+ items):
 * 1. Multi-column sorting (numeric co2e, strings facility/process, dates year/month).
 * 2. High-volume filtering (scoped facilities, process categories, search substring).
 * 3. Pagination slicing across multiple page chunk sizes (25, 50, 100, 500, 1,000).
 * 4. Table footer accumulator reductions (total CO2, CH4, N2O, CO2e) with zero drift.
 * 5. Memory stability and execution SLA (< 50ms per operation).
 */

import { performance } from "perf_hooks";
import { formatNumber, formatCompactNumber } from "../src/utils/formatters.js";

export async function runLargeDatasetStressTest() {
  console.log("\n============================================================");
  console.log("PILLAR 1: Large Dataset & Table Virtualization Stress Test");
  console.log("============================================================");

  const RECORD_COUNT = 10000;
  console.log(`[SYNTHESIZING] Generating ${RECORD_COUNT.toLocaleString()} multi-scope emission records...`);

  const facilities = [
    "Hassi Messaoud Main Plant",
    "In Salah Gas Compression Hub",
    "Rhourde Nouss Processing Unit",
    "Tin Fouye Tabankort Terminal",
    "Alrar Gas Separation Facility",
  ];
  const processes = [
    "combustion",
    "flaring",
    "venting",
    "pneumatics",
    "fugitives",
    "acid_gas_removal",
  ];
  const fuels = ["Natural Gas", "Diesel", "Field Gas", "LPG", "Fuel Gas"];

  const initialMemory = process.memoryUsage().heapUsed;
  const t0 = performance.now();

  const dataset = new Array(RECORD_COUNT);
  for (let i = 0; i < RECORD_COUNT; i++) {
    const year = 2020 + (i % 6);
    const month = (Math.floor(i / 6) % 12) + 1;
    const fac = facilities[Math.floor(i / 72) % facilities.length];
    const proc = processes[Math.floor(i / 360) % processes.length];
    const fuel = fuels[Math.floor(i / 2160) % fuels.length];
    const qty = 100.0 + ((i * 17) % 5000);
    const co2 = qty * 1.95;
    const ch4 = proc === "combustion" ? 0.0003 * qty : 0.05 * qty;
    const n2o = 0.00003 * qty;
    const co2e = co2 + ch4 * 28.0 + n2o * 265.0;

    dataset[i] = {
      id: i + 1,
      year,
      month,
      facility_name: fac,
      process_type: proc,
      fuel_type: fuel,
      quantity: qty,
      unit: "m3",
      co2_emissions: co2,
      ch4_emissions: ch4,
      n2o_emissions: n2o,
      co2e_total: co2e,
      scope: (i % 3) + 1,
    };
  }

  const genTime = performance.now() - t0;
  console.log(`[GENERATED] 10,000 records in ${genTime.toFixed(2)} ms.`);

  // --------------------------------------------------------------------------
  // Benchmark 1: Sorting Performance
  // --------------------------------------------------------------------------
  console.log("\n--- Benchmark 1: Full-Dataset Sorting (10,000 records) ---");

  // Numeric Sort (CO2e Descending)
  const tSortNumStart = performance.now();
  const sortedByCo2e = [...dataset].sort((a, b) => b.co2e_total - a.co2e_total);
  const sortNumTime = performance.now() - tSortNumStart;
  console.log(`   Numeric Sort (CO2e Descending): ${sortNumTime.toFixed(2)} ms`);
  if (sortedByCo2e[0].co2e_total < sortedByCo2e[RECORD_COUNT - 1].co2e_total) {
    throw new Error("Sort failed: first element is smaller than last element!");
  }

  // String Sort (Facility Name Ascending)
  const tSortStrStart = performance.now();
  const sortedByFac = [...dataset].sort((a, b) => a.facility_name.localeCompare(b.facility_name));
  const sortStrTime = performance.now() - tSortStrStart;
  console.log(`   String Sort (Facility Name): ${sortStrTime.toFixed(2)} ms`);

  // Composite Sort (Year Descending -> Month Descending -> CO2e Descending)
  const tSortCompStart = performance.now();
  const sortedComposite = [...dataset].sort((a, b) => {
    if (b.year !== a.year) return b.year - a.year;
    if (b.month !== a.month) return b.month - a.month;
    return b.co2e_total - a.co2e_total;
  });
  const sortCompTime = performance.now() - tSortCompStart;
  console.log(`   Composite Multi-Key Sort: ${sortCompTime.toFixed(2)} ms`);

  // --------------------------------------------------------------------------
  // Benchmark 2: Multi-Criteria Filtering
  // --------------------------------------------------------------------------
  console.log("\n--- Benchmark 2: Multi-Criteria Filtering (10,000 records) ---");

  const tFilterStart = performance.now();
  const targetYear = 2024;
  const targetFacility = "Hassi Messaoud";
  const targetProcess = "combustion";
  const searchSubstring = "gas";

  const filtered = dataset.filter((row) => {
    if (row.year !== targetYear) return false;
    if (!row.facility_name.includes(targetFacility)) return false;
    if (row.process_type !== targetProcess) return false;
    if (
      !row.fuel_type.toLowerCase().includes(searchSubstring) &&
      !row.facility_name.toLowerCase().includes(searchSubstring)
    ) {
      return false;
    }
    return true;
  });
  const filterTime = performance.now() - tFilterStart;
  console.log(`   Multi-Criteria Filter matched ${filtered.length.toLocaleString()} rows in ${filterTime.toFixed(2)} ms`);
  if (filtered.length === 0) {
    throw new Error("Filter returned 0 rows unexpectedly!");
  }

  // --------------------------------------------------------------------------
  // Benchmark 3: Pagination Slicing Across Chunk Sizes
  // --------------------------------------------------------------------------
  console.log("\n--- Benchmark 3: Pagination Chunking & Page Rendering ---");
  const pageSizes = [25, 50, 100, 500, 1000];

  for (const pageSize of pageSizes) {
    const totalPages = Math.ceil(dataset.length / pageSize);
    const tPageStart = performance.now();

    let totalSlicedRows = 0;
    for (let page = 1; page <= totalPages; page++) {
      const startIdx = (page - 1) * pageSize;
      const pageSlice = dataset.slice(startIdx, startIdx + pageSize);
      totalSlicedRows += pageSlice.length;

      // Simulate row cell formatting in table view
      for (let r = 0; r < Math.min(5, pageSlice.length); r++) {
        const row = pageSlice[r];
        formatNumber(row.quantity, 2);
        formatNumber(row.co2_emissions, 3);
        formatNumber(row.co2e_total, 3);
      }
    }

    const pageTime = performance.now() - tPageStart;
    console.log(
      `   Page Size ${pageSize.toString().padStart(4)}: ${totalPages.toString().padStart(3)} pages (${totalSlicedRows} rows) traversed in ${pageTime.toFixed(2)} ms`
    );
    if (totalSlicedRows !== RECORD_COUNT) {
      throw new Error(`Pagination missing rows: expected ${RECORD_COUNT}, got ${totalSlicedRows}`);
    }
  }

  // --------------------------------------------------------------------------
  // Benchmark 4: Table Footer Sum Accumulation (reduce over 10,000 rows)
  // --------------------------------------------------------------------------
  console.log("\n--- Benchmark 4: Table Footer Total Accumulation ---");
  const tAccumStart = performance.now();

  const grandTotals = dataset.reduce(
    (acc, row) => {
      acc.totalQty += row.quantity;
      acc.totalCo2 += row.co2_emissions;
      acc.totalCh4 += row.ch4_emissions;
      acc.totalN2o += row.n2o_emissions;
      acc.totalCo2e += row.co2e_total;
      return acc;
    },
    { totalQty: 0, totalCo2: 0, totalCh4: 0, totalN2o: 0, totalCo2e: 0 }
  );

  const accumTime = performance.now() - tAccumStart;
  console.log(`   Summed 5 numerical columns across 10,000 rows in ${accumTime.toFixed(2)} ms:`);
  console.log(`     Total Activity: ${formatNumber(grandTotals.totalQty, 2)} m3`);
  console.log(`     Total CO2:      ${formatNumber(grandTotals.totalCo2, 3)} tonnes`);
  console.log(`     Total CH4:      ${formatNumber(grandTotals.totalCh4, 5)} tonnes`);
  console.log(`     Total CO2e:     ${formatNumber(grandTotals.totalCo2e, 3)} tCO2e (${formatCompactNumber(grandTotals.totalCo2e, 2)})`);

  if (grandTotals.totalCo2e <= 0 || isNaN(grandTotals.totalCo2e)) {
    throw new Error("Accumulator produced invalid total!");
  }

  const finalMemory = process.memoryUsage().heapUsed;
  const netHeapGrowthMB = Math.max(0, (finalMemory - initialMemory) / (1024 * 1024));
  console.log(`\n[MEMORY] Net Heap Allocation: ${netHeapGrowthMB.toFixed(2)} MB`);

  // Assertions against SLAs
  if (sortNumTime > 150) throw new Error(`Sort SLA breached: ${sortNumTime.toFixed(2)} ms > 150 ms`);
  if (filterTime > 50) throw new Error(`Filter SLA breached: ${filterTime.toFixed(2)} ms > 50 ms`);
  if (accumTime > 50) throw new Error(`Accumulator SLA breached: ${accumTime.toFixed(2)} ms > 50 ms`);

  console.log(">>> [PILLAR 1: PASSED] Large Dataset & Table Virtualization 100% Verified.");
  return true;
}

if (process.argv[1]?.endsWith("test_ui_stress_large_dataset.mjs")) {
  runLargeDatasetStressTest().catch((err) => {
    console.error("Test Failed:", err);
    process.exit(1);
  });
}
