export type OgmpLevel = 1 | 2 | 3 | 4 | 5;

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
