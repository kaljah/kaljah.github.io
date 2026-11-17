export type OgmpLevel = 1 | 2 | 3 | 4 | 5;

export type OgmpSourceStatusFlag = "Quantified" | "MI" | "N/A";
export type OgmpMeasurementMode = "Instantaneous" | "Annualized" | "Mixed";
export type OgmpOptionMode = "Option 1" | "Option 2";
export type OgmpPathwayCode = "1" | "2a" | "2b" | "2c" | "2d" | "3";

export interface OgmpCatalogItem {
  code: string;
  name: string;
  category: string;
  default_ef_ref?: string;
}

export interface OgmpPathwayDefinition {
  code: OgmpPathwayCode;
  title: string;
  description: string;
}

export interface OgmpCatalogResponse {
  upstream: OgmpCatalogItem[];
  mid_downstream: OgmpCatalogItem[];
  active: OgmpCatalogItem[];
  pathways: OgmpPathwayDefinition[];
  status_flags: OgmpSourceStatusFlag[];
  measurement_modes: ("Instantaneous" | "Annualized")[];
  option_modes: OgmpOptionMode[];
}

export interface OgmpSurvey {
  id: number;
  facility_id: number;
  facility_name?: string;
  year: number;
  survey_date: string;
  survey_type: string;
  source_type?: string;
  measured_rate_kg_hr?: number;
  operating_hours_year?: number;
  estimated_annual_tch4?: number;
  detection_threshold?: number;
  instrument_vendor?: string;
  bottom_up_tch4?: number;
  variance_pct?: number;
  variance_flag?: boolean;
  reconciliation_status?: string;
  status: "Pending" | "Verified" | "Rejected";
  operator_notes?: string | null;
  created_by?: number;
  created_at?: string;
}

export interface OgmpReportingEntity {
  id: number;
  facility_id?: number | null;
  facility_name?: string | null;
  entity_name: string;
  asset_name?: string;
  segment: string;
  sub_segment?: string;
  country?: string;
  operator_status: "operated" | "non_operated" | string;
  operating_company?: string;
  working_interest_pct: number;
  has_operational_control?: boolean;
  membership_year: number;
  target_gold_year: number;
  is_nojv_material_excluded: boolean;
  exclusion_reason?: string;
  is_member_reported_nojv: boolean;
  created_at?: string | null;
}

export interface OgmpTarget {
  id: number;
  reporting_entity_id: number;
  entity_name?: string | null;
  target_year: number;
  metric_type?: string;
  upstream_target_pct: number;
  midstream_target_pct: number;
  reduction_target_pct?: number;
  base_year?: number;
  notes?: string;
  created_at?: string | null;
}

export interface OgmpEmissionSource {
  id: number;
  facility_id: number;
  facility_name?: string | null;
  annual_report_id?: number | null;
  year: number;
  segment: string;
  source_code: string;
  source_name: string;
  source_category?: string;
  ogmp_level: OgmpLevel;
  status_flag: OgmpSourceStatusFlag;
  ch4_tonnes: number;
  uncertainty_pct: number;
  emission_factor_ref?: string;
  quantification_method?: string;
  pathway_code?: OgmpPathwayCode | null;
  yoy_change_pct?: number | null;
  yoy_explanation?: string;
  zero_emission_explanation?: string;
  created_at?: string | null;
}

export interface OgmpSiteMeasurement {
  id: number;
  facility_id: number;
  facility_name?: string | null;
  annual_report_id?: number | null;
  year: number;
  campaign_date: string;
  survey_type: string;
  instrument_vendor?: string;
  measurement_mode: "Instantaneous" | "Annualized" | string;
  option_mode: OgmpOptionMode | string;
  measured_rate_kg_hr: number;
  operating_hours_year: number;
  annualized_tch4: number;
  uncertainty_pct: number;
  ci_low_tch4: number;
  ci_high_tch4: number;
  detection_threshold_kg_hr?: number | null;
  meteorological_notes?: string;
  created_at?: string | null;
}

export interface OgmpAnnualReport {
  id: number;
  facility_id: number;
  facility_name?: string | null;
  reporting_entity_id?: number | null;
  year: number;
  reporting_level: OgmpLevel;
  status: string;
  total_bottom_up_tch4: number;
  total_top_down_tch4: number;
  bu_uncertainty_pct: number;
  bu_ci_low_tch4: number;
  bu_ci_high_tch4: number;
  td_uncertainty_pct: number;
  td_ci_low_tch4: number;
  td_ci_high_tch4: number;
  ci_overlaps: boolean;
  variance_pct?: number | null;
  variance_flag: boolean;
  reconciliation_status: string;
  l4_materiality_pct: number;
  l4_justification?: string;
  pathway_code: OgmpPathwayCode | string;
  measurement_mode: OgmpMeasurementMode | string;
  option_mode: OgmpOptionMode | string;
  gas_production_m3?: number | null;
  ch4_intensity_pct?: number | null;
  equity_ch4_tch4?: number | null;
  updated_at?: string | null;
  created_at?: string | null;
}

export interface OgmpImplementationPlan {
  id: number;
  facility_id: number;
  facility_name?: string | null;
  reporting_entity_id?: number | null;
  asset_name?: string;
  operator_status: string;
  base_year: number;
  milestone_horizon: string;
  planned_year: number;
  target_level: OgmpLevel;
  actual_level?: OgmpLevel | null;
  source_scope?: string;
  methodology_upgrade?: string;
  milestone_status: string;
  justification?: string;
  created_at?: string | null;
}

export interface OgmpPortfolioEntitySummary {
  id: number | null;
  facility_id?: number | null;
  entity_name: string;
  asset_name?: string;
  segment: string;
  country?: string;
  operator_status: string;
  operating_company?: string;
  working_interest_pct: number;
  facility_ch4_tch4: number;
  equity_ch4_tch4: number;
  portfolio_equity_share_pct: number;
  eligible_below_5pct_exclusion: boolean;
  is_nojv_material_excluded: boolean;
  exclusion_valid: boolean;
  exclusion_reason?: string;
  is_member_reported_nojv: boolean;
}

export interface OgmpPortfolioMateriality {
  total_equity_ch4_tch4: number;
  included_equity_ch4_tch4: number;
  excluded_equity_ch4_tch4: number;
  included_coverage_pct: number;
  meets_95pct_threshold: boolean;
  nojv_exclusion_count: number;
  nojv_exclusions: OgmpPortfolioEntitySummary[];
  member_reported_nojv_count: number;
  member_reported_nojvs: OgmpPortfolioEntitySummary[];
  entities: OgmpPortfolioEntitySummary[];
}

export interface OgmpAuditTrailEntry {
  id: number;
  facility_id?: number | null;
  facility_name?: string | null;
  annual_report_id?: number | null;
  entity_type: string;
  entity_id: string;
  action: string;
  actor_id?: number | null;
  actor_name: string;
  summary: string;
  before?: Record<string, any> | null;
  after?: Record<string, any> | null;
  created_at?: string | null;
}
