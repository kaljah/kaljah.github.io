export type BoundaryType = "Operational Control" | "Financial Control" | "Equity Share";
export type SegmentType = "Upstream" | "Midstream" | "Downstream";
export type OperatorStatus = "operated" | "non-operated";

export interface Facility {
  id: number;
  name: string;
  location?: string | null;
  division?: string | null;
  activity?: string | null;
  region?: string | null;
  region_identifier?: string;
  boundary_notes?: string | null;
  boundary_type?: BoundaryType;
  boundary_detail?: string | null;
  equity_share_pct?: number | null;
  segment?: SegmentType | null;
  operator_status?: OperatorStatus;
  country?: string;
  ogmp_membership_year?: number;
  reconciliation_threshold?: number;
  field?: string | null;
  code?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}
