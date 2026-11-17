// Number formatting utilities

/**
 * Format number with compact notation (M, k, B)
 * @param value - The number to format
 * @param decimals - Number of decimal places (clamped 0-20)
 * @returns Formatted number
 */
export const formatCompactNumber = (
  value: number | string | null | undefined,
  decimals: number = 1,
): string => {
  // a missing value is shown as missing, not as a measured zero (BA-027)
  if (value === null || value === undefined || value === "") return "—";
  let num = typeof value === "number" ? value : parseFloat(String(value));
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
 * @param value - The number to format
 * @param decimals - Number of decimal places (clamped 0-20)
 * @returns Formatted number
 */
export const formatNumber = (
  value: number | string | null | undefined,
  decimals: number = 3,
): string => {
  // a missing value is shown as missing, not as a measured zero (BA-027)
  if (value === null || value === undefined || value === "") return "—";
  let num = typeof value === "number" ? value : parseFloat(String(value));
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
export const formatEmission = (
  value: number | string | null | undefined,
  decimals: number = 3,
): string => {
  const num = typeof value === "number" ? value : parseFloat(String(value));
  if (Number.isFinite(num) && num !== 0 && Math.abs(num) < 0.5 * Math.pow(10, -decimals)) {
    return num.toExponential(2);
  }
  return formatNumber(value, decimals);
};

/**
 * Calculate percentage change
 * @param current - Current value
 * @param base - Base value for comparison
 * @returns Formatted percentage with + or -
 */
export const calculateTrend = (
  current: number | string | null | undefined,
  base: number | string | null | undefined,
): string => {
  const c = typeof current === "number" ? current : parseFloat(String(current));
  const b = typeof base === "number" ? base : parseFloat(String(base));
  if (!Number.isFinite(c) || !Number.isFinite(b) || b === 0) return "—";

  const change = ((c - b) / Math.abs(b)) * 100;
  if (!Number.isFinite(change)) return "—";
  const sign = change > 0 ? "+" : "";

  return `${sign}${change.toFixed(1)}%`;
};

/**
 * Format date to readable string
 * @param date - Date to format
 * @returns Formatted date
 */
export const formatDate = (date: string | number | Date | null | undefined): string => {
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


/**
 * Whole-number percentage shares that add up to 100 (largest remainder): each share rounded on its own gave
 * 33 + 33 + 33 = 99 % (BA-021). Returns null for every share when the total is not positive.
 */
export const roundedShares = (values: number[]): (number | null)[] => {
  const nums = values.map((v) => (Number.isFinite(v) && v > 0 ? v : 0));
  const total = nums.reduce((a, b) => a + b, 0);
  if (!(total > 0)) return nums.map(() => null);
  const raw = nums.map((v) => (v / total) * 100);
  const floors = raw.map((r) => Math.floor(r));
  let rest = 100 - floors.reduce((a, b) => a + b, 0);
  const order = raw.map((r, i) => [r - Math.floor(r), i] as [number, number]).sort((a, b) => b[0] - a[0]);
  for (const [, i] of order) {
    if (rest <= 0) break;
    floors[i] += 1;
    rest -= 1;
  }
  return floors;
};
