// Scope 3 activity factors, kg CO2e per unit at AR5, with their source noted per category.
// factor: null = no published default; the user enters a supplier / site factor.
export const CATEGORY_ACTIVITIES = {
  1: [
    // EPA Supply Chain GHG Emission Factors v1.3.0, kg CO2e per 2022 USD (purchaser price, with margins, AR5)
    { value: "Iron & steel products (NAICS 331110)", unit: "USD", factor: 0.787 },
    { value: "Steel pipe & tube (NAICS 331210)", unit: "USD", factor: 0.36 },
    { value: "Cement (NAICS 327310)", unit: "USD", factor: 3.924 },
    { value: "Organic chemicals (NAICS 325199)", unit: "USD", factor: 1.184 },
    { value: "Inorganic chemicals (NAICS 325180)", unit: "USD", factor: 1.01 },
    { value: "Oil & gas support services (NAICS 213112)", unit: "USD", factor: 0.372 },
    { value: "Engineering services (NAICS 541330)", unit: "USD", factor: 0.103 },
  ],
  2: [
    // EPA Supply Chain GHG Emission Factors v1.3.0, kg CO2e per 2022 USD (purchaser price, with margins, AR5)
    { value: "Oil & gas field machinery (NAICS 333132)", unit: "USD", factor: 0.219 },
    { value: "Pipeline construction (NAICS 237120)", unit: "USD", factor: 0.277 },
    { value: "Commercial / industrial buildings (NAICS 236220)", unit: "USD", factor: 0.224 },
    { value: "Computers (NAICS 334111)", unit: "USD", factor: 0.058 },
  ],
  3: [
    // EPA Supply Chain GHG Emission Factors v1.3.0 (cradle-to-gate of the purchased fuel), kg CO2e per 2022 USD
    { value: "Purchased refined fuels, upstream (NAICS 324110)", unit: "USD", factor: 0.27 },
    { value: "Purchased natural gas, upstream (NAICS 211130)", unit: "USD", factor: 0.405 },
    // T&D losses: kWh lost x the site grid factor (Scope 2 grid list); no fixed default
    { value: "T&D Losses (Electricity)", unit: "kWh", factor: null },
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
    // EPA Supply Chain GHG Emission Factors v1.3.0, NAICS 531120, kg CO2e per 2022 USD of rent
    { value: "Leased buildings (rent) (NAICS 531120)", unit: "USD", factor: 0.246 },
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
    // electricity: enter the grid factor of the processing site (kg CO2e / kWh, Scope 2 grid list)
    { value: "Processing (Electricity)", unit: "kWh", factor: null },
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
  13: [
    // EPA Supply Chain GHG Emission Factors v1.3.0, NAICS 531120, kg CO2e per 2022 USD of rent
    { value: "Downstream leased buildings (rent) (NAICS 531120)", unit: "USD", factor: 0.246 },
  ],
  14: [
    // no EPA factor: enter the franchisee's reported emission intensity
    { value: "Franchise operations", unit: "USD", factor: null },
  ],
  15: [
    // no EPA factor: enter the investee factor (e.g. PCAF), kg CO2e per USD invested
    { value: "Equity Investments", unit: "USD", factor: null },
    { value: "Project Finance", unit: "USD", factor: null },
  ],
};
