// Number formatting utilities

/**
 * Format number with compact notation (M, k, B)
 * @param {number|string} value - The number to format
 * @param {number} decimals - Number of decimal places (clamped 0-20)
 * @returns {string} Formatted number
 */
export const formatCompactNumber = (value, decimals = 1) => {
  if (value === null || value === undefined || value === "") return "0";
  let num = parseFloat(value);
  if (!Number.isFinite(num)) {
    if (num === Infinity) return "∞";
    if (num === -Infinity) return "-∞";
    return "0";
  }

  const safeDecimals = Math.max(0, Math.min(20, Math.round(Number(decimals) || 0)));

  if (Object.is(num, -0) || Math.abs(num) < 1e-12) {
    num = 0;
  }

  const res = new Intl.NumberFormat("en-US", {
    notation: "compact",
    compactDisplay: "short",
    maximumFractionDigits: safeDecimals,
  }).format(num);

  return res.replace(/^-0(\.0+)?$/, "0$1");
};

/**
 * Format number with thousand separators
 * @param {number|string} value - The number to format
 * @param {number} decimals - Number of decimal places (clamped 0-20)
 * @returns {string} Formatted number
 */
export const formatNumber = (value, decimals = 3) => {
  if (value === null || value === undefined || value === "") return "0";
  let num = parseFloat(value);
  if (!Number.isFinite(num)) {
    if (num === Infinity) return "∞";
    if (num === -Infinity) return "-∞";
    return "0";
  }

  const safeDecimals = Math.max(0, Math.min(20, Math.round(Number(decimals) || 0)));

  if (Object.is(num, -0) || Math.abs(num) < Math.pow(10, -(safeDecimals + 1))) {
    num = 0;
  }

  const res = num.toLocaleString("en-US", {
    minimumFractionDigits: safeDecimals,
    maximumFractionDigits: safeDecimals,
  });

  return res.replace(/^-0(\.0+)?$/, "0$1");
};

/**
 * An emission in tonnes with `decimals` places; a non-zero value too small for them is shown in
 * scientific notation (2.70e-4) instead of 0.000.
 */
export const formatEmission = (value, decimals = 3) => {
  const num = parseFloat(value);
  if (Number.isFinite(num) && num !== 0 && Math.abs(num) < 0.5 * Math.pow(10, -decimals)) {
    return num.toExponential(2);
  }
  return formatNumber(value, decimals);
};

/**
 * Calculate percentage change
 * @param {number|string} current - Current value
 * @param {number|string} base - Base value for comparison
 * @returns {string} Formatted percentage with + or -
 */
export const calculateTrend = (current, base) => {
  const c = parseFloat(current);
  const b = parseFloat(base);
  if (!Number.isFinite(c) || !Number.isFinite(b) || b === 0) return "—";

  const change = ((c - b) / Math.abs(b)) * 100;
  if (!Number.isFinite(change)) return "—";
  const sign = change > 0 ? "+" : "";

  return `${sign}${change.toFixed(1)}%`;
};

/**
 * Format date to readable string
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date
 */
export const formatDate = (date) => {
  if (!date) return "";
  try {
    const d = new Date(date);
    if (isNaN(d.getTime())) return String(date);
    return d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return String(date);
  }
};
