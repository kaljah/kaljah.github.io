// Scope 3 activity factors, kg CO2e per unit at AR5. Sources are noted per category; categories
// without a note (1, 2, 3, 8 office space, 10 electricity, 13, 14, 15) have no verified source.
export const CATEGORY_ACTIVITIES = {
  1: [
    { value: "Steel", unit: "kg", factor: 1.85 },
    { value: "Cement", unit: "kg", factor: 0.82 },
    { value: "Chemicals", unit: "kg", factor: 2.1 },
    { value: "Equipment", unit: "USD", factor: 0.42 },
    { value: "Services", unit: "USD", factor: 0.18 },
  ],
  2: [
    { value: "Machinery & Equipment", unit: "USD", factor: 0.45 },
    { value: "Buildings & Infrastructure", unit: "USD", factor: 0.85 },
    { value: "IT Equipment", unit: "USD", factor: 0.35 },
  ],
  3: [
    { value: "Upstream of Purchased Fuels", unit: "kg", factor: 0.25 },
    { value: "T&D Losses (Electricity)", unit: "kWh", factor: 0.05 },
  ],
  4: [
    // EPA GHG Emission Factors Hub 2025, Table 8 (short ton-mile), as kg CO2e per tonne-km at AR5
    { value: "Truck Transport", unit: "ton-km", factor: 0.12841 },
    { value: "Rail Transport", unit: "ton-km", factor: 0.01451 },
    { value: "Ship Transport", unit: "ton-km", factor: 0.0537 },
    { value: "Air Freight", unit: "ton-km", factor: 0.74991 },
  ],
  5: [
    // EPA GHG Emission Factors Hub 2025, Table 9 (WARM), t CO2e / short ton as kg CO2e / kg
    { value: "Landfill (mixed MSW)", unit: "kg", factor: 0.6393 },
    { value: "Incineration (mixed MSW)", unit: "kg", factor: 0.474 },
    { value: "Recycling (mixed recyclables)", unit: "kg", factor: 0.0992 },
    { value: "Composting (mixed organics)", unit: "kg", factor: 0.1433 },
  ],
  6: [
    // EPA GHG Emission Factors Hub 2025, Table 10, per passenger-km / vehicle-km at AR5
    { value: "Air - Short Haul (< 300 mi)", unit: "passenger-km", factor: 0.12982 },
    { value: "Air - Medium Haul (300-2300 mi)", unit: "passenger-km", factor: 0.08084 },
    { value: "Air - Long Haul (>= 2300 mi)", unit: "passenger-km", factor: 0.10215 },
    { value: "Passenger Car", unit: "km", factor: 0.18552 },
    { value: "Light-Duty Truck / SUV", unit: "km", factor: 0.24646 },
    { value: "Intercity Rail", unit: "passenger-km", factor: 0.06012 },
    { value: "Bus", unit: "passenger-km", factor: 0.0414 },
  ],
  7: [
    // EPA GHG Emission Factors Hub 2025, Table 10, per vehicle-km / passenger-km at AR5
    { value: "Passenger Car", unit: "km", factor: 0.18552 },
    { value: "Light-Duty Truck / SUV", unit: "km", factor: 0.24646 },
    { value: "Bus", unit: "passenger-km", factor: 0.0414 },
    { value: "Commuter Rail", unit: "passenger-km", factor: 0.08325 },
    { value: "Transit Rail (subway, tram)", unit: "passenger-km", factor: 0.05808 },
  ],
  8: [
    { value: "Leased Office Space", unit: "sq ft", factor: 5.5 },
    // EPA GHG Emission Factors Hub 2025, Table 10 passenger car, per vehicle-km at AR5
    { value: "Leased Vehicles (passenger car)", unit: "km", factor: 0.18552 },
  ],
  9: [
    // EPA GHG Emission Factors Hub 2025, Table 8 (short ton-mile), as kg CO2e per tonne-km at AR5
    { value: "Truck Transport", unit: "ton-km", factor: 0.12841 },
    { value: "Rail Transport", unit: "ton-km", factor: 0.01451 },
    { value: "Ship Transport", unit: "ton-km", factor: 0.0537 },
    { value: "Air Freight", unit: "ton-km", factor: 0.74991 },
  ],
  10: [
    { value: "Processing (Electricity)", unit: "kWh", factor: 0.4 },
    { value: "Processing (Natural Gas)", unit: "mcf", factor: 54.18 },
  ],
  11: [
    // Combustion of sold products: API Compendium 2021 Table 4-5 heating value and CO2, Table 4-6 CH4 / N2O,
    // as kg CO2e per unit at AR5 (natural gas 1,020 Btu/scf, Table 3-8)
    { value: "Crude Oil", unit: "bbl", factor: 433.44 },
    { value: "Natural Gas", unit: "mcf", factor: 54.18 },
    { value: "NGL - Ethane", unit: "gal", factor: 4.07 },
    { value: "NGL - Propane", unit: "gal", factor: 5.74 },
    { value: "NGL - Butane", unit: "gal", factor: 6.7 },
    { value: "NGL - Mixed (as LPG)", unit: "gal", factor: 5.7 },
  ],
  12: [
    // EPA GHG Emission Factors Hub 2025, Table 9 (WARM), t CO2e / short ton as kg CO2e / kg
    { value: "Landfill (mixed MSW)", unit: "kg", factor: 0.6393 },
    { value: "Recycling (mixed recyclables)", unit: "kg", factor: 0.0992 },
    { value: "Incineration (mixed MSW)", unit: "kg", factor: 0.474 },
  ],
  13: [{ value: "Downstream Leased Space", unit: "sq ft", factor: 5.5 }],
  14: [{ value: "Retail Franchise", unit: "sq ft", factor: 10.0 }],
  15: [
    { value: "Equity Investments", unit: "USD", factor: 0.001 },
    { value: "Project Finance", unit: "USD", factor: 0.005 },
  ],
};
