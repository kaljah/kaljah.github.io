import React from "react";
import { formatCompactNumber, formatEmission, formatNumber } from "../utils/formatters";
import { cn } from "./cn";

const FORMATTERS = {
  compact: (v, d) => formatCompactNumber(v, d ?? 1),
  emission: (v, d) => formatEmission(v, d ?? 3),
  number: (v, d) => formatNumber(v, d ?? 3),
  percent: (v, d) => `${formatNumber(v, d ?? 1)}%`,
};

/** A number with tabular figures. Compact values show the exact value on hover. */
export const Num = ({ value, format = "number", decimals, className }) => {
  const text = FORMATTERS[format](value, decimals);
  const exact = format === "compact" ? formatNumber(value, 3) : undefined;
  return (
    <span className={cn("tabular-nums", className)} title={exact}>
      {text}
    </span>
  );
};

const UNITS = {
  tCO2e: "tCO₂e",
  tCH4: "tCH₄",
  tN2O: "tN₂O",
  kSm3: "kSm³",
  m3: "m³",
  "kgCO2e/BOE": "kg CO₂e/BOE",
  "kgCH4/BOE": "kg CH₄/BOE",
};

/** Normalizes unit display, so tCO2e is shown with a subscript 2. Unknown units are shown as given. */
export const Unit = ({ children, className }) => (
  <span className={cn("text-text-secondary", className)}>{UNITS[children] ?? children}</span>
);
