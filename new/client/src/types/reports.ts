export type CbamQuarter = "Q1-Q4" | "Q1" | "Q2" | "Q3" | "Q4";

export interface ReportFilters {
  year?: number | string | null;
  quarter?: CbamQuarter | string | null;
  month?: number | string | null;
  facility_id?: number | string | null;
  facilityId?: number | string | null;
  scope?: "all" | "1" | "2" | "3" | "scope1" | "scope2" | "scope3";
  process_type?: string | null;
  division?: string | null;
  field?: string | null;
  method?: string | null;
  search?: string | null;
}

export interface CbamExportRecord {
  id: number;
  facility_id: number;
  year: number;
  month: number;
  quarter?: string;
  product_name: string;
  cn_code: string;
  quantity_tonnes: number;
  export_destination: string;
  specific_embedded_direct: number;
  specific_embedded_indirect: number;
  captured_co2_tonnes?: number;
  ccs_certificate_id?: string | null;
  carbon_price_paid_eur?: number;
  carbon_price_legal_ref?: string | null;
  is_complex_good?: boolean;
  precursor_name?: string | null;
  precursor_cn_code?: string | null;
  precursor_ratio?: number | null;
  precursor_see_dir?: number | null;
  precursor_see_indir?: number | null;
  notes?: string | null;
}

export interface CbamValidationIssue {
  record_id: number | null;
  field: string;
  message: string;
}

export interface CbamValidationCheck {
  id: string;
  label: string;
  status: "pass" | "warning" | "fail";
  detail: string;
}

export interface CbamValidationRecord {
  id: number;
  facility_id: number;
  facility_name: string;
  product_name: string;
  cn_code: string;
  year: number;
  quarter: string;
  quantity_tonnes: number;
  gross_direct_see: number;
  ccs_reduction_see: number;
  net_direct_see: number;
  indirect_see: number;
  precursor_see: number;
  total_see: number;
  total_embedded_tco2e: number;
  has_scope1_data: boolean;
  has_scope2_data: boolean;
}

export interface CbamValidationReport {
  ready: boolean;
  quarter: CbamQuarter | string;
  period_start: string;
  period_end: string;
  year: string;
  assurance_level: string;
  assurance_provider?: string;
  record_count: number;
  errors: CbamValidationIssue[];
  warnings: CbamValidationIssue[];
  checks: CbamValidationCheck[];
  summary: {
    total_quantity_tonnes: number;
    total_embedded_emissions_tco2e: number;
    total_captured_co2_tonnes: number;
    total_carbon_price_paid_eur: number;
    complex_goods_count: number;
  };
  records: CbamValidationRecord[];
}
