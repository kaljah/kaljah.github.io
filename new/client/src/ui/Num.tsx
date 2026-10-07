import React from "react";
import { formatCompactNumber, formatEmission, formatNumber } from "../utils/formatters";
import { cn } from "./cn";

export type NumFormat = "compact" | "emission" | "number" | "percent";

const FORMATTERS: Record<NumFormat, (v: number | string | null | undefined, d?: number) => string> = {
  compact: (v, d) => formatCompactNumber(v, d ?? 1),
  emission: (v, d) => formatEmission(v, d ?? 3),
  number: (v, d) => formatNumber(v, d ?? 3),
  percent: (v, d) => `${formatNumber(v, d ?? 1)}%`,
};

export interface NumProps {
  value: number | string | null | undefined;
  format?: NumFormat;
  decimals?: number;
  className?: string;
}

/** A number with tabular figures. Compact values show the exact value on hover. */
export const Num: React.FC<NumProps> = ({ value, format = "number", decimals, className }) => {
  const text = FORMATTERS[format](value, decimals);
  const exact = format === "compact" ? formatNumber(value, 3) : undefined;
  return (
    <span className={cn("tabular-nums", className)} title={exact}>
      {text}
    </span>
  );
};

const UNITS: Record<string, string> = {
  tCO2e: "tCO₂e",
  tCH4: "tCH₄",
  tN2O: "tN₂O",
  kSm3: "kSm³",
  m3: "m³",
  "kgCO2e/BOE": "kg CO₂e/BOE",
  "kgCH4/BOE": "kg CH₄/BOE",
};

export interface UnitProps {
  children?: string;
  className?: string;
}

/** Normalizes unit display, so tCO2e is shown with a subscript 2. Unknown units are shown as given. */
export const Unit: React.FC<UnitProps> = ({ children, className }) => (
  <span className={cn("text-text-secondary", className)}>
    {children ? (UNITS[children] ?? children) : ""}
  </span>
);
