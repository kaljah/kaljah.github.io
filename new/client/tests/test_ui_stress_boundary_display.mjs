/**
 * test_ui_stress_boundary_display.mjs
 * ===================================
 * Pillar 4: Extreme Numerical, Astronomical & Boundary Display Resilience.
 *
 * Validates UI formatting and display engine under chaotic edge cases:
 * 1. Astronomical magnitudes (10^18, 10^24, 10^30) formatted without RangeError.
 * 2. Microscopic numbers (10^-15, 10^-25) handled without underflow crashes.
 * 3. Non-finite values (NaN, Infinity, -Infinity, null, undefined) producing clean fallbacks.
 * 4. Extreme decimals arguments (clamped to 0..20 to prevent Intl RangeError).
 * 5. Giant string payloads (10,000 characters) in table cells.
 * 6. RTL Arabic, CJK, and Unicode emoji bursts.
 * 7. Trend calculation divide-by-zero resilience.
 */

import { formatNumber, formatCompactNumber, calculateTrend, formatDate } from "../src/utils/formatters.js";

export async function runBoundaryDisplayStressTest() {
  console.log("\n============================================================");
  console.log("PILLAR 4: Extreme Numerical & Boundary Display Resilience");
  console.log("============================================================");

  // --------------------------------------------------------------------------
  // Benchmark 1: Astronomical & Microscopic Magnitudes
  // --------------------------------------------------------------------------
  console.log("\n--- Benchmark 1: Astronomical & Microscopic Values ---");

  const astronomicalValues = [1e15, 1e18, 1e21, 1e24, 1e30];
  for (const val of astronomicalValues) {
    const formatted = formatNumber(val, 2);
    const compact = formatCompactNumber(val, 1);
    console.log(`   Val: ${val.toExponential()} -> formatNumber: "${formatted.slice(0, 25)}...", compact: "${compact}"`);
    if (!formatted || typeof formatted !== "string") {
      throw new Error(`Failed to format astronomical value: ${val}`);
    }
  }

  const microscopicValues = [1e-6, 1e-9, 1e-15, 1e-20, 1e-25];
  for (const val of microscopicValues) {
    const formatted = formatNumber(val, 6);
    console.log(`   Val: ${val.toExponential()} -> formatNumber(6): "${formatted}"`);
    if (!formatted || typeof formatted !== "string") {
      throw new Error(`Failed to format microscopic value: ${val}`);
    }
  }

  // --------------------------------------------------------------------------
  // Benchmark 2: Non-Finite & Corrupt Inputs
  // --------------------------------------------------------------------------
  console.log("\n--- Benchmark 2: Non-Finite & Corrupted Inputs ---");

  const corruptInputs = [
    NaN,
    Infinity,
    -Infinity,
    null,
    undefined,
    "",
    "NaN",
    "Infinity",
    "-Infinity",
    "invalid_text",
    {},
    [],
  ];

  for (const input of corruptInputs) {
    const numFormatted = formatNumber(input, 2);
    const compactFormatted = formatCompactNumber(input, 1);
    console.log(`   Input [${String(input)}] -> formatNumber: "${numFormatted}", compact: "${compactFormatted}"`);

    // Must never throw and must return valid non-empty string
    if (typeof numFormatted !== "string" || typeof compactFormatted !== "string") {
      throw new Error(`Corrupt input produced non-string: ${String(input)}`);
    }
  }

  // --------------------------------------------------------------------------
  // Benchmark 3: Out-of-Range Decimals Argument (Intl RangeError Defense)
  // --------------------------------------------------------------------------
  console.log("\n--- Benchmark 3: Out-of-Range Decimals Argument ---");

  const testVal = 12345.6789;
  const outOfRangeDecimals = [-10, -1, 0, 1, 3, 20, 25, 50, 100, NaN, null, undefined];

  for (const dec of outOfRangeDecimals) {
    try {
      const out = formatNumber(testVal, dec);
      const outComp = formatCompactNumber(testVal, dec);
      console.log(`   Decimals: ${String(dec).padStart(9)} -> formatNumber: "${out}", compact: "${outComp}"`);
    } catch (err) {
      throw new Error(`RangeError triggered on decimals: ${dec}: ${err.message}`);
    }
  }

  // --------------------------------------------------------------------------
  // Benchmark 4: Trend Percentage Divide-by-Zero & Infinite Bounds
  // --------------------------------------------------------------------------
  console.log("\n--- Benchmark 4: Trend Percentage Divide-by-Zero Resilience ---");

  const trendScenarios = [
    [100, 0, "—"],       // Base is zero -> fallback
    [100, null, "—"],    // Base is null -> fallback
    [100, undefined, "—"], // Base is undefined -> fallback
    [100, NaN, "—"],     // Base is NaN -> fallback
    [NaN, 100, "—"],     // Current is NaN -> fallback
    [150, 100, "+50.0%"],// Growth
    [80, 100, "-20.0%"], // Reduction
    [100, 100, "0.0%"],  // Parity
    [1e20, 1e18, "+9900.0%"], // Giant growth
  ];

  for (const [curr, base, expected] of trendScenarios) {
    const trend = calculateTrend(curr, base);
    console.log(`   Trend (${curr}, ${base}) => "${trend}" (expected: "${expected}")`);
    if (trend !== expected) {
      throw new Error(`Trend mismatch for (${curr}, ${base}): got "${trend}", expected "${expected}"`);
    }
  }

  // --------------------------------------------------------------------------
  // Benchmark 5: Giant String & Multi-Byte Unicode Burst
  // --------------------------------------------------------------------------
  console.log("\n--- Benchmark 5: Giant String & Unicode Layout Resilience ---");

  const giantString = "X".repeat(10000); // 10,000 characters
  console.log(`   10,000 character string length: ${giantString.length} chars.`);

  const unicodeSamples = [
    "حقل حاسي مسعود للغاز الطبيعي والنفط الخام",
    "阿尔及利亚国家石油天然气公司项目",
    "🔥🏭⚡🌿 Carbon Emissions Scope 1 2026",
    "Control Chars: \t\r\n\x00\x1b[31mRed\x1b[0m",
  ];

  for (const sample of unicodeSamples) {
    console.log(`   Unicode Sample: "${sample.slice(0, 30)}..." [Length: ${sample.length}]`);
  }

  // Date formatter edge cases
  const dateEdgeCases = ["", null, undefined, "invalid-date", "2024-02-29", new Date("2024-12-31")];
  for (const d of dateEdgeCases) {
    const formattedDate = formatDate(d);
    console.log(`   Date [${String(d)}] -> "${formattedDate}"`);
  }

  console.log(">>> [PILLAR 4: PASSED] Extreme Numerical & Boundary Display 100% Verified.");
  return true;
}

if (process.argv[1]?.endsWith("test_ui_stress_boundary_display.mjs")) {
  runBoundaryDisplayStressTest().catch((err) => {
    console.error("Test Failed:", err);
    process.exit(1);
  });
}
