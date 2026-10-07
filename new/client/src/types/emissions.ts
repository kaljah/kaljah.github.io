export type EmissionStatus = "Pending" | "Verified" | "Rejected";
export type ScopeCategory = "Scope 1" | "Scope 2" | "Scope 3";
export type CalculationTier = "Tier 1" | "Tier 2" | "Tier 3";

export interface Scope1Emission {
  id: number;
  facility_id: number;
  facility_name?: string;
  year: number;
  month: number;
  process_type: string;
  source_type?: string;
  activity_amount?: number;
  activity_unit?: string;
  emission_factor?: number;
  co2_emissions?: number;
  ch4_emissions?: number;
  n2o_emissions?: number;
  co2e_total: number;
  uncertainty?: number;
  uncertainty_pct?: number;
  tier?: CalculationTier | string;
  calc_method?: string;
  status: EmissionStatus;
  qa_flag?: string | null;
  notes?: string | null;
  created_by?: number;
  created_at?: string;
  approved_by?: number | null;
  approved_at?: string | null;
}

export interface Scope2Emission {
  id: number;
  facility_id: number;
  facility_name?: string;
  year: number;
  month: number;
  source_type: "purchased_electricity" | "indirect_steam" | "cogen_allocation" | string;
  activity_kwh?: number;
  grid_region?: string | null;
  location_ef?: number;
  market_ef?: number;
  co2e_location: number;
  co2e_market: number;
  co2e: number;
  heat_mmbtu?: number;
  steam_ton?: number;
  cooling_ton?: number;
  uncertainty?: number;
  status: EmissionStatus;
  qa_flag?: string | null;
  notes?: string | null;
  created_by?: number;
  created_at?: string;
  approved_by?: number | null;
  approved_at?: string | null;
}

export interface Scope3Emission {
  id: number;
  facility_id?: number | null;
  facility_name?: string;
  year: number;
  month: number;
  category: string;
  sub_category?: string;
  activity_data: number;
  unit: string;
  emission_factor: number;
  co2e: number;
  uncertainty?: number;
  uncertainty_pct?: number;
  calculation_method?: string;
  data_quality?: string;
  status: EmissionStatus;
  qa_flag?: string | null;
  notes?: string | null;
  created_by?: number;
  created_at?: string;
  approved_by?: number | null;
  approved_at?: string | null;
}

export interface CustomFactor {
  id: number;
  name: string;
  category: string;
  scope: string;
  factor_value: number;
  unit: string;
  gas?: string;
  source_reference?: string;
  facility_id?: number | null;
  status: "Approved" | "Pending" | "Rejected";
  approved_by?: number | null;
  approved_at?: string | null;
  is_archived?: boolean;
}
