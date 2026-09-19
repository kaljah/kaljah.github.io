// Number formatting utilities

/**
 * Format number with compact notation (M, k, B)
 * @param {number|string} value - The number to format
 * @param {number} decimals - Number of decimal places (clamped 0-20)
 * @returns {string} Formatted number
 */
export const formatCompactNumber = (value, decimals = 1) => {
  if (value === null || value === undefined || value === "") return "0";
  const num = parseFloat(value);
  if (!Number.isFinite(num)) {
    if (num === Infinity) return "∞";
    if (num === -Infinity) return "-∞";
    return "0";
  }

  const safeDecimals = Math.max(0, Math.min(20, Math.round(Number(decimals) || 0)));

  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    compactDisplay: "short",
    maximumFractionDigits: safeDecimals,
  }).format(num);
};

/**
 * Format number with thousand separators
 * @param {number|string} value - The number to format
 * @param {number} decimals - Number of decimal places (clamped 0-20)
 * @returns {string} Formatted number
 */
export const formatNumber = (value, decimals = 3) => {
  if (value === null || value === undefined || value === "") return "0";
  const num = parseFloat(value);
  if (!Number.isFinite(num)) {
    if (num === Infinity) return "∞";
    if (num === -Infinity) return "-∞";
    return "0";
  }

  const safeDecimals = Math.max(0, Math.min(20, Math.round(Number(decimals) || 0)));

  return num.toLocaleString("en-US", {
    minimumFractionDigits: safeDecimals,
    maximumFractionDigits: safeDecimals,
  });
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
