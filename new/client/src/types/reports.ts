export interface ReportFilters {
  year?: number | string | null;
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
  product_name: string;
  cn_code: string;
  quantity_tonnes: number;
  export_destination: string;
  specific_embedded_direct: number;
  specific_embedded_indirect: number;
  notes?: string | null;
}
