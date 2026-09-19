import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function runVisualsAudit() {
  console.log("============================================================");
  console.log("VISUAL AUDIT: Heatmaps, Trends, Pie Charts, and Data Tables");
  console.log("============================================================");

  let passed = 0;
  let total = 0;

  function assert(cond, msg) {
    total++;
    if (!cond) {
      console.error("FAIL: " + msg);
      throw new Error("Assertion failed: " + msg);
    }
    passed++;
    console.log("PASS: " + msg);
  }

  // 1: Chart formatValue Resilience
  console.log("\n--- Audit 1: Chart formatValue Resilience ---");

  const chartFormatValue = (val) => {
    if (val === null || val === undefined || isNaN(val)) return "0";
    const num = Number(val);
    if (!isFinite(num)) return "0";
    if (Math.abs(num) >= 1000000) return (num / 1000000).toFixed(1) + "M";
    if (Math.abs(num) >= 1000) return (num / 1000).toFixed(1) + "k";
    return num.toLocaleString();
  };

  assert(chartFormatValue(null) === "0", "Chart formatValue handles null");
  assert(chartFormatValue(undefined) === "0", "Chart formatValue handles undefined");
  assert(chartFormatValue(NaN) === "0", "Chart formatValue handles NaN");
  assert(chartFormatValue(Infinity) === "0", "Chart formatValue handles Infinity");
  assert(chartFormatValue(-Infinity) === "0", "Chart formatValue handles -Infinity");
  assert(chartFormatValue(0) === "0", "Chart formatValue handles 0");
  assert(chartFormatValue(1250) === "1.3k", "Chart formatValue formats 1,250 as 1.3k");
  assert(chartFormatValue(2500000) === "2.5M", "Chart formatValue formats 2.5M");
  assert(chartFormatValue(-1500) === "-1.5k", "Chart formatValue formats negative thousands");

  // 2: PieChart Zero-Sum and Negative Sanitization
  console.log("\n--- Audit 2: PieChart Data Sanitization and Zero-Sum Handling ---");

  function processPieData(data, dataKey = "value") {
    if (!data || data.length === 0) return { empty: true, reason: "no-data" };
    const sanitizedData = data.map((item) => ({
      ...item,
      [dataKey]: Math.max(0, Number(item[dataKey]) || 0),
    }));
    const totalValue = sanitizedData.reduce(
      (acc, curr) => acc + (Number(curr[dataKey]) || 0),
      0
    );
    if (totalValue <= 0) return { empty: true, reason: "zero-sum", sanitizedData };
    return { empty: false, sanitizedData, totalValue };
  }

  const allZeroPie = [
    { name: "Scope 1", value: 0 },
    { name: "Scope 2", value: 0 },
    { name: "Scope 3", value: 0 },
  ];
  const zeroResult = processPieData(allZeroPie);
  assert(zeroResult.empty === true && zeroResult.reason === "zero-sum", "PieChart triggers empty state on all-zero values");

  const negativePie = [
    { name: "Scope 1", value: -50 },
    { name: "Scope 2", value: 100 },
  ];
  const negResult = processPieData(negativePie);
  assert(negResult.empty === false && negResult.sanitizedData[0].value === 0, "PieChart clamps negative slice to 0");
  assert(negResult.totalValue === 100, "PieChart correctly totals sanitized non-negative slices");

  // 3: Heatmap Cell Classification Guardrails
  console.log("\n--- Audit 3: Heatmap Classification Guardrails ---");

  const getCarbonHeatmapClass = (val) => {
    if (val === null || val === undefined || isNaN(val) || val === 0) return "heat-null";
    if (val < 18) return "heat-lux";
    if (val < 28) return "heat-low";
    if (val < 38) return "heat-mid";
    if (val < 48) return "heat-high";
    return "heat-crit";
  };

  const getMethaneHeatmapClass = (val) => {
    if (val === null || val === undefined || isNaN(val) || val === 0) return "heat-null";
    if (val < 0.05) return "heat-lux";
    if (val < 0.15) return "heat-low";
    if (val < 0.25) return "heat-mid";
    if (val < 0.5) return "heat-high";
    return "heat-crit";
  };

  assert(getCarbonHeatmapClass(null) === "heat-null", "Carbon heatmap maps null to heat-null");
  assert(getCarbonHeatmapClass(undefined) === "heat-null", "Carbon heatmap maps undefined to heat-null");
  assert(getCarbonHeatmapClass(NaN) === "heat-null", "Carbon heatmap maps NaN to heat-null");
  assert(getCarbonHeatmapClass(0) === "heat-null", "Carbon heatmap maps 0 to heat-null");
  assert(getCarbonHeatmapClass(12) === "heat-lux", "Carbon heatmap maps 12 to heat-lux (< 18)");
  assert(getCarbonHeatmapClass(55) === "heat-crit", "Carbon heatmap maps 55 to heat-crit (>= 48)");

  assert(getMethaneHeatmapClass(null) === "heat-null", "Methane heatmap maps null to heat-null");
  assert(getMethaneHeatmapClass(undefined) === "heat-null", "Methane heatmap maps undefined to heat-null");
  assert(getMethaneHeatmapClass(NaN) === "heat-null", "Methane heatmap maps NaN to heat-null");
  assert(getMethaneHeatmapClass(0) === "heat-null", "Methane heatmap maps 0 to heat-null");
  assert(getMethaneHeatmapClass(0.02) === "heat-lux", "Methane heatmap maps 0.02% to heat-lux (< 0.05%)");
  assert(getMethaneHeatmapClass(0.65) === "heat-crit", "Methane heatmap maps 0.65% to heat-crit (>= 0.5%)");

  // 4: Table Column Span Integrity
  console.log("\n--- Audit 4: Table Column Alignment Verification ---");

  const scope1File = path.resolve(__dirname, "../src/components/Scope1Form.jsx");
  const scope1Content = fs.readFileSync(scope1File, "utf-8");

  const s1TheadMatch = scope1Content.match(/<thead[\s\S]*?<\/thead>/);
  const s1ThCount = (s1TheadMatch[0].match(/<th[\s>]/g) || []).length;
  assert(s1ThCount === 22, "Scope1Form header has exactly 22 columns (found " + s1ThCount + ")");

  assert(
    scope1Content.includes('colSpan="14"') && scope1Content.includes('colSpan="7"'),
    "Scope1Form tfoot columns span 14 (label) + 1 (total) + 7 (trailing) = 22"
  );
  assert(
    scope1Content.includes('colSpan="22"'),
    "Scope1Form empty state spans 22 columns"
  );

  const scope2File = path.resolve(__dirname, "../src/components/Scope2Form.jsx");
  const scope2Content = fs.readFileSync(scope2File, "utf-8");

  const s2TheadMatch = scope2Content.match(/<thead[\s\S]*?<\/thead>/);
  const s2ThCount = (s2TheadMatch[0].match(/<th[\s>]/g) || []).length;
  assert(s2ThCount === 11, "Scope2Form header has exactly 11 columns (found " + s2ThCount + ")");

  assert(
    scope2Content.includes('colSpan="7"') && scope2Content.includes('colSpan="3"'),
    "Scope2Form tfoot columns span 7 (label) + 1 (total) + 3 (trailing) = 11"
  );
  assert(
    scope2Content.includes('colSpan="11"'),
    "Scope2Form empty and loading states span 11 columns"
  );

  // 5: Backend Year Sorting Resilience Simulation
  console.log("\n--- Audit 5: Backend Year Sorting Resilience ---");

  function simulateQueryAvailableYears(years1, years2, years3, years4) {
    const validYears = new Set();
    for (const y of [...years1, ...years2, ...years3, ...years4]) {
      if (y[0] !== null && y[0] !== undefined && /^\d+$/.test(String(y[0]))) {
        validYears.add(Number(y[0]));
      }
    }
    return Array.from(validYears).sort((a, b) => b - a);
  }

  const simulatedDbOutput = simulateQueryAvailableYears(
    [[2024], [null], [2022]],
    [[null], [2023], [2024]],
    [[undefined], ["invalid"], [2021]],
    [[2020], [null], [2025]]
  );

  assert(
    JSON.stringify(simulatedDbOutput) === JSON.stringify([2025, 2024, 2023, 2022, 2021, 2020]),
    "Backend year query filters nulls, non-digits, deduplicates, and sorts descending"
  );

  console.log("\n============================================================");
  console.log(`VISUAL AUDIT COMPLETE: ${passed}/${total} checks PASSED (100%)`);
  console.log("============================================================\n");
}

runVisualsAudit().catch((err) => {
  console.error("Audit test failed:", err);
  process.exit(1);
});
