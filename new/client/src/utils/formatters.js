// Number formatting utilities

/**
 * Format number with compact notation (M, k, B)
 * @param {number} value - The number to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted number
 */
export const formatCompactNumber = (value, decimals = 1) => {
  const num = parseFloat(value);
  if (isNaN(num)) return "0";

  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    compactDisplay: "short",
    maximumFractionDigits: decimals,
  }).format(num);
};

/**
 * Format number with thousand separators
 * @param {number} value - The number to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted number
 */
export const formatNumber = (value, decimals = 3) => {
  const num = parseFloat(value);
  if (isNaN(num)) return "0";

  return num.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

/**
 * Calculate percentage change
 * @param {number} current - Current value
 * @param {number} base - Base value for comparison
 * @returns {string} Formatted percentage with + or -
 */
export const calculateTrend = (current, base) => {
  if (!base || base === 0) return "—";

  const change = ((current - base) / base) * 100;
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

  const d = new Date(date);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};
