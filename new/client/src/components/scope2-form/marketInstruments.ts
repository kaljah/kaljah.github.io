// Contractual instruments for market-based Scope 2 (GHG Protocol Scope 2 Guidance). The server treats a
// REC as zero-carbon when no factor is given; other instruments use the entered contract factor, or
// fall back to the location-based grid factor.
export const MARKET_INSTRUMENTS: Array<{ value: string; label: string }> = [
  { value: "", label: "None (location-based fallback)" },
  { value: "PPA", label: "Power Purchase Agreement (PPA)" },
  { value: "REC", label: "Renewable Energy Certificate (REC)" },
  { value: "GO", label: "Guarantee of Origin (GO)" },
  { value: "supplier_tariff", label: "Green Tariff / Supplier Specific" },
];
