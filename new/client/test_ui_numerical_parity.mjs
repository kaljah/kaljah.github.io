import { formatNumber, formatCompactNumber, calculateTrend } from './src/utils/formatters.js';
import assert from 'node:assert';

console.log('=== Running UI Numerical Formatter Parity Tests (Node.js) ===\n');

// 1. Basic formatNumber precision tests
console.log('1. Testing formatNumber decimals and thousands separators...');
assert.strictEqual(formatNumber(1234.5678, 3), '1,234.568');
assert.strictEqual(formatNumber(1234.5, 3), '1,234.500');
assert.strictEqual(formatNumber(0, 3), '0.000');
assert.strictEqual(formatNumber('1234.56', 2), '1,234.56');
assert.strictEqual(formatNumber(null, 3), '0');
assert.strictEqual(formatNumber(undefined, 3), '0');
assert.strictEqual(formatNumber(NaN, 3), '0');

// 2. High-precision trace gases (CH4, N2O - 5 decimals)
console.log('2. Testing trace gas precision (5 decimals for CH4 and N2O)...');
assert.strictEqual(formatNumber(0.000254, 5), '0.00025');
assert.strictEqual(formatNumber(0.00001, 5), '0.00001');
assert.strictEqual(formatNumber(0.000006, 5), '0.00001');
assert.strictEqual(formatNumber(0.000004, 5), '0.00000');
assert.strictEqual(formatNumber(1.234567, 5), '1.23457');

// 3. Compact numbers for Dashboard KPIs
console.log('3. Testing formatCompactNumber for Dashboard KPIs...');
const compact1M = formatCompactNumber(1250000, 1);
assert.ok(compact1M.includes('1.3M') || compact1M.includes('1.2M') || compact1M.includes('1.25M'));
const compact45K = formatCompactNumber(45200, 1);
assert.ok(compact45K.toUpperCase().includes('45.2K'));
assert.strictEqual(formatCompactNumber(0), '0');

// 4. Trend calculation
console.log('4. Testing calculateTrend...');
assert.strictEqual(calculateTrend(110, 100), '+10.0%');
assert.strictEqual(calculateTrend(90, 100), '-10.0%');
assert.strictEqual(calculateTrend(100, 0), '—');

// 5. Simulated calculation pipeline verification
console.log('5. Testing simulated backend-to-UI calculation pipeline...');
const qty_m3 = 10000;
const ef_co2_kg_m3 = 1.8849;
const ef_ch4_kg_m3 = 0.000037;
const ef_n2o_kg_m3 = 0.000033;
const gwp_ch4 = 28.0;
const gwp_n2o = 265.0;

const co2_mass_tonnes = (qty_m3 * ef_co2_kg_m3) / 1000;
const ch4_mass_tonnes = (qty_m3 * ef_ch4_kg_m3) / 1000;
const n2o_mass_tonnes = (qty_m3 * ef_n2o_kg_m3) / 1000;
const total_co2e = co2_mass_tonnes * 1.0 + ch4_mass_tonnes * gwp_ch4 + n2o_mass_tonnes * gwp_n2o;

const ui_display_qty = `${formatNumber(qty_m3, 2)} m3`;
const ui_display_co2 = formatNumber(co2_mass_tonnes, 3);
const ui_display_ch4 = formatNumber(ch4_mass_tonnes, 5);
const ui_display_n2o = formatNumber(n2o_mass_tonnes, 5);
const ui_display_co2e = formatNumber(total_co2e, 3);

assert.strictEqual(ui_display_qty, '10,000.00 m3');
assert.strictEqual(ui_display_co2, '18.849');
assert.strictEqual(ui_display_ch4, '0.00037');
assert.strictEqual(ui_display_n2o, '0.00033');
assert.strictEqual(ui_display_co2e, '18.947');

// CalculationDetails Modal Display
const modal_co2 = formatNumber(co2_mass_tonnes, 3);
const modal_ch4 = formatNumber(ch4_mass_tonnes, 4);
const modal_n2o = formatNumber(n2o_mass_tonnes, 4);
const modal_total = formatNumber(total_co2e, 3);

assert.strictEqual(modal_co2, '18.849');
assert.strictEqual(modal_ch4, '0.0004');
assert.strictEqual(modal_n2o, '0.0003');
assert.strictEqual(modal_total, '18.947');

// Scope 2 Example: 50,000 kWh at 0.385 kg CO2e/kWh
const s2_kwh = 50000;
const s2_ef = 0.385;
const s2_co2e = (s2_kwh * s2_ef) / 1000;
assert.strictEqual(formatNumber(s2_kwh, 0) + ' kWh', '50,000 kWh');
assert.strictEqual(formatNumber(s2_ef, 4), '0.3850');
assert.strictEqual(formatNumber(s2_co2e, 3), '19.250');

// Scope 3 Example: $100,000 spend at 0.35 kg CO2e / $1
const s3_spend = 100000;
const s3_ef = 0.35;
const s3_co2e = (s3_spend * s3_ef) / 1000;
assert.strictEqual(formatNumber(s3_spend, 2), '100,000.00');
assert.strictEqual(formatNumber(s3_ef, 2), '0.35');
assert.strictEqual(formatNumber(s3_co2e, 3), '35.000');

// Dashboard Aggregate Total
const total_inventory = total_co2e + s2_co2e + s3_co2e;
assert.strictEqual(formatNumber(total_inventory, 3), '73.197');

console.log('\n[PASS] All UI numerical formatter parity checks passed successfully!');
