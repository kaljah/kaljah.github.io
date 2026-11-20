import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  ClipboardList,
  Compass,
  Play,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import api from "../../api";
import { useToast } from "../../components/Toast";
import { Badge, Button, Field, Input, NativeSelect, Textarea, controlClass } from "../../ui";
import { RecordTable, Td, Tr } from "./MdParts";
import { t } from "../../i18n";
import type {
  OgmpAnnualReport,
  OgmpAuditTrailEntry,
  OgmpCatalogItem,
  OgmpCatalogResponse,
  OgmpEmissionSource,
  OgmpImplementationPlan,
  OgmpPathwayDefinition,
  OgmpPortfolioMateriality,
  OgmpReportingEntity,
  OgmpSiteMeasurement,
  OgmpTarget,
} from "../../types/ogmp";

export type OgmpWorkspaceSubTab = "sources" | "reconcile" | "entities" | "plan";

export interface OgmpL4L5PanelProps {
  activeSubTab: OgmpWorkspaceSubTab;
  facilities: Array<{
    id: string | number;
    name: string;
    field?: string;
    segment?: string;
    activity?: string;
    division?: string;
    country?: string;
    operator_status?: string;
    equity_share_pct?: number;
    ogmp_membership_year?: number;
    [key: string]: any;
  }>;
  NON_OG_ACTIVITIES: string[];
  onDataUpdated?: () => void;
}

const DEFAULT_PATHWAYS: OgmpPathwayDefinition[] = [
  { code: "1", title: "Pathway 1 (Coarse L4 + Annual L5)", description: "Single consolidated L4 inventory with annual L5 site measurement." },
  { code: "2a", title: "Pathway 2a (Temporal Breakdown)", description: "Time-resolved L4 emission profile paired with site snapshots." },
  { code: "2b", title: "Pathway 2b (Spatial / Area)", description: "Area-resolved bottom-up groups matched against plumes." },
  { code: "2c", title: "Pathway 2c (Source-Category)", description: "Split into vented, fugitive, and incomplete combustion components." },
  { code: "2d", title: "Pathway 2d (Measurement-Informed L4)", description: "Continuous/periodic component measurement informing L4 factors." },
  { code: "3", title: "Pathway 3 (Facility Direct Reconciliation)", description: "Direct reconciliation between L4 catalog sum and L5 site total." },
];

export const OgmpL4L5Panel: React.FC<OgmpL4L5PanelProps> = ({
  activeSubTab,
  facilities,
  NON_OG_ACTIVITIES,
  onDataUpdated,
}) => {
  const toast = useToast();
  const ogFacilities = useMemo(
    () => facilities.filter((f) => !NON_OG_ACTIVITIES.includes(f.activity || "")),
    [facilities, NON_OG_ACTIVITIES],
  );
  const defaultFacId = ogFacilities[0] ? String(ogFacilities[0].id) : "";
  const currentYear = new Date().getFullYear();

  const [selectedFacilityId, setSelectedFacilityId] = useState<string>(defaultFacId);
  const [selectedYear, setSelectedYear] = useState<number>(currentYear);
  const [loading, setLoading] = useState<boolean>(false);

  const [catalog, setCatalog] = useState<OgmpCatalogResponse | null>(null);
  const [entities, setEntities] = useState<OgmpReportingEntity[]>([]);
  const [targets, setTargets] = useState<OgmpTarget[]>([]);
  const [sources, setSources] = useState<OgmpEmissionSource[]>([]);
  const [measurements, setMeasurements] = useState<OgmpSiteMeasurement[]>([]);
  const [annualReports, setAnnualReports] = useState<OgmpAnnualReport[]>([]);
  const [plans, setPlans] = useState<OgmpImplementationPlan[]>([]);
  const [portfolio, setPortfolio] = useState<OgmpPortfolioMateriality | null>(null);
  const [auditTrail, setAuditTrail] = useState<OgmpAuditTrailEntry[]>([]);

  // Source Catalog form
  const [srcForm, setSrcForm] = useState({
    facility_id: defaultFacId,
    year: currentYear,
    segment: "Upstream",
    source_code: "",
    source_name: "",
    source_category: "Fugitive",
    ogmp_level: 4,
    status_flag: "Quantified",
    ch4_tonnes: "",
    // no hidden defaults saved as measured data (audit 2026-11 F-GOGMP-05)
    uncertainty_pct: "",
    emission_factor_ref: "",
    quantification_method: "",
    pathway_code: "",
    yoy_explanation: "",
    zero_emission_explanation: "",
  });

  // L5 Measurement & Reconcile forms
  const [measForm, setMeasForm] = useState({
    facility_id: defaultFacId,
    year: currentYear,
    campaign_date: "",
    survey_type: "Aircraft / Hyperspectral Imaging",
    instrument_vendor: "",
    measurement_mode: "Annualized",
    option_mode: "Option 1",
    measured_rate_kg_hr: "",
    operating_hours_year: "8760",
    uncertainty_pct: "",
    detection_threshold_kg_hr: "",
    meteorological_notes: "",
  });
  const [recParams, setRecParams] = useState({
    option_mode: "Option 1",
    pathway_code: "",
    pathway_explanation: "",
    threshold_pct: "20",
    l4_justification: "",
  });

  // Entity & Target forms
  const [entityForm, setEntityForm] = useState({
    facility_id: defaultFacId,
    entity_name: "",
    asset_name: "",
    segment: "Upstream",
    operator_status: "operated",
    operating_company: "",
    working_interest_pct: "100",
    membership_year: String(currentYear - 2),
    is_nojv_material_excluded: false,
    exclusion_reason: "",
    is_member_reported_nojv: false,
  });
  const [targetForm, setTargetForm] = useState({
    reporting_entity_id: "",
    target_year: String(currentYear + 2),
    upstream_target_pct: "",
    midstream_target_pct: "",
    notes: "",
  });

  // Implementation plan milestone form
  const [planForm, setPlanForm] = useState({
    facility_id: defaultFacId,
    milestone_horizon: "Y3",
    planned_year: String(currentYear + 1),
    target_level: "5",
    source_scope: "All Material CH4 Sources (>= 90%)",
    methodology_upgrade: "Deploy L4 source measurement + L5 site campaign",
    milestone_status: "In Progress",
    justification: "",
  });

  // the first facility is chosen on first load only: "All facilities" stays selectable (audit 2026-11 F-GOGMP-11)
  const facInit = React.useRef(false);
  useEffect(() => {
    if (!facInit.current && !selectedFacilityId && defaultFacId) {
      facInit.current = true;
      setSelectedFacilityId(defaultFacId);
      setSrcForm((p) => ({ ...p, facility_id: defaultFacId }));
      setMeasForm((p) => ({ ...p, facility_id: defaultFacId }));
      setEntityForm((p) => ({ ...p, facility_id: defaultFacId }));
      setPlanForm((p) => ({ ...p, facility_id: defaultFacId }));
    }
  }, [defaultFacId, selectedFacilityId]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [catRes, entRes, tgtRes, srcRes, measRes, repRes, planRes, portRes, auditRes] = await Promise.all([
        api.get("/ogmp/catalogs").catch(() => ({ data: null })),
        api.get("/ogmp/entities").catch(() => ({ data: [] })),
        api.get("/ogmp/targets").catch(() => ({ data: [] })),
        api.get("/ogmp/emission-sources").catch(() => ({ data: [] })),
        api.get("/ogmp/site-measurements").catch(() => ({ data: [] })),
        api.get("/ogmp/annual-reports").catch(() => ({ data: [] })),
        api.get("/ogmp/implementation-plans").catch(() => ({ data: [] })),
        // the selected year's materiality (every year was summed: audit 2026-11 F-GOGMP-06)
        api.get("/ogmp/portfolio-materiality", { params: { year: selectedYear } }).catch(() => ({ data: null })),
        api.get("/ogmp/audit-trail").catch(() => ({ data: [] })),
      ]);

      if (catRes.data && typeof catRes.data === "object" && !Array.isArray(catRes.data)) {
        setCatalog(catRes.data as OgmpCatalogResponse);
      }
      setEntities(Array.isArray(entRes.data) ? entRes.data : []);
      setTargets(Array.isArray(tgtRes.data) ? tgtRes.data : []);
      setSources(Array.isArray(srcRes.data) ? srcRes.data : []);
      setMeasurements(Array.isArray(measRes.data) ? measRes.data : []);
      setAnnualReports(Array.isArray(repRes.data) ? repRes.data : []);
      setPlans(Array.isArray(planRes.data) ? planRes.data : []);
      setPortfolio(
        portRes.data && typeof portRes.data === "object" && !Array.isArray(portRes.data)
          ? (portRes.data as OgmpPortfolioMateriality)
          : null,
      );
      setAuditTrail(Array.isArray(auditRes.data) ? auditRes.data : []);
    } finally {
      setLoading(false);
    }
  }, [selectedYear]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const catalogList: OgmpCatalogItem[] = useMemo(() => {
    if (!catalog) return [];
    const seg = String(srcForm.segment || "").toLowerCase();
    if (seg.includes("mid") || seg.includes("down")) {
      return Array.isArray(catalog.mid_downstream) ? catalog.mid_downstream : [];
    }
    return Array.isArray(catalog.upstream) ? catalog.upstream : [];
  }, [catalog, srcForm.segment]);

  const liveMateriality = useMemo(() => {
    const scoped = sources.filter(
      (s) =>
        (!selectedFacilityId || String(s.facility_id) === String(selectedFacilityId)) &&
        Number(s.year) === Number(selectedYear) &&
        s.status_flag === "Quantified",
    );
    const total = scoped.reduce((acc, s) => acc + Number(s.ch4_tonnes || 0), 0);
    const l4 = scoped
      .filter((s) => Number(s.ogmp_level) >= 4)
      .reduce((acc, s) => acc + Number(s.ch4_tonnes || 0), 0);
    const belowL3 = scoped
      .filter((s) => Number(s.ogmp_level) < 3 && total > 0 && Number(s.ch4_tonnes || 0) / total >= 0.05)
      .length;
    const pct = total > 0 ? (l4 / total) * 100 : 0;
    return {
      total,
      pct,
      count: scoped.length,
      meets90: pct >= 90,
      meets70WithJust: pct >= 70 && belowL3 === 0,
    };
  }, [sources, selectedFacilityId, selectedYear]);

  const pathways = (catalog?.pathways && catalog.pathways.length > 0) ? catalog.pathways : DEFAULT_PATHWAYS;

  // Handlers
  const handleAddSource = async (e: React.FormEvent) => {
    e.preventDefault();
    const fid = srcForm.facility_id || selectedFacilityId;
    if (!fid) {
      toast.error(t("Select an Oil & Gas facility first."));
      return;
    }
    try {
      await api.post("/ogmp/emission-sources", {
        ...srcForm,
        facility_id: Number(fid),
        year: Number(selectedYear),
        ogmp_level: Number(srcForm.ogmp_level),
        ch4_tonnes: srcForm.status_flag === "Quantified" ? Number(srcForm.ch4_tonnes || 0) : 0,
        uncertainty_pct: Number(srcForm.uncertainty_pct || 0),
      });
      toast.success(t("OGMP source disclosure saved."));
      setSrcForm((p) => ({ ...p, ch4_tonnes: "", yoy_explanation: "", zero_emission_explanation: "" }));
      await loadAll();
      onDataUpdated?.();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to save OGMP source."));
    }
  };

  const handleDeleteSource = async (id: number) => {
    try {
      await api.delete(`/ogmp/emission-sources/${id}`);
      toast.success(t("Source disclosure removed."));
      await loadAll();
      onDataUpdated?.();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to delete source."));
    }
  };

  const handleAddMeasurement = async (e: React.FormEvent) => {
    e.preventDefault();
    const fid = measForm.facility_id || selectedFacilityId;
    if (!fid) {
      toast.error(t("Select an Oil & Gas facility first."));
      return;
    }
    try {
      await api.post("/ogmp/site-measurements", {
        ...measForm,
        facility_id: Number(fid),
        year: Number(selectedYear),
        measured_rate_kg_hr: Number(measForm.measured_rate_kg_hr || 0),
        // an entered 0 stays 0 (`||` replaced it); the uncertainty is the campaign's own (F-GOGMP-05)
        operating_hours_year: measForm.operating_hours_year === "" ? 8760 : Number(measForm.operating_hours_year),
        uncertainty_pct: measForm.uncertainty_pct === "" ? undefined : Number(measForm.uncertainty_pct),
        detection_threshold_kg_hr: measForm.detection_threshold_kg_hr ? Number(measForm.detection_threshold_kg_hr) : null,
      });
      toast.success(t("L5 site measurement campaign logged."));
      setMeasForm((p) => ({ ...p, measured_rate_kg_hr: "", meteorological_notes: "" }));
      await loadAll();
      onDataUpdated?.();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to log site measurement."));
    }
  };

  const handleDeleteMeasurement = async (id: number) => {
    try {
      await api.delete(`/ogmp/site-measurements/${id}`);
      toast.success(t("Site measurement removed."));
      await loadAll();
      onDataUpdated?.();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to delete measurement."));
    }
  };

  const handleRunReconciliation = async () => {
    if (!selectedFacilityId) {
      toast.error(t("Select a facility to reconcile."));
      return;
    }
    try {
      const res = await api.post("/ogmp/reconcile", {
        facility_id: Number(selectedFacilityId),
        year: Number(selectedYear),
        option_mode: recParams.option_mode,
        pathway_code: recParams.pathway_code || undefined,
        pathway_explanation: recParams.pathway_explanation || undefined,
        threshold_pct: recParams.threshold_pct === "" ? 20 : Number(recParams.threshold_pct),
        l4_justification: recParams.l4_justification,
      });
      const rep = res.data?.annual_report;
      toast.success(
        rep
          ? t("Reconciliation complete: Level {{lvl}} ({{result}}), saved as {{status}} for review.", {
              lvl: rep.reporting_level,
              result: t(rep.reconciliation_status),
              status: t(rep.status),
            })
          : t("Reconciliation complete."),
      );
      await loadAll();
      onDataUpdated?.();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to run L4/L5 reconciliation."));
    }
  };

  const handleAddEntity = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/ogmp/entities", {
        ...entityForm,
        facility_id: entityForm.facility_id ? Number(entityForm.facility_id) : null,
        working_interest_pct: Number(entityForm.working_interest_pct || 100),
        membership_year: Number(entityForm.membership_year || 2023),
      });
      toast.success(t("OGMP reporting entity saved."));
      // the NOJV flags are reset too: a hidden checked box blocked or corrupted the next entity (F-GOGMP-10)
      setEntityForm((p) => ({ ...p, entity_name: "", operating_company: "", exclusion_reason: "",
        is_nojv_material_excluded: false, is_member_reported_nojv: false }));
      await loadAll();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to save reporting entity."));
    }
  };

  const handleDeleteEntity = async (id: number) => {
    try {
      await api.delete(`/ogmp/entities/${id}`);
      toast.success(t("Reporting entity removed."));
      await loadAll();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to delete reporting entity."));
    }
  };

  const handleAddTarget = async (e: React.FormEvent) => {
    e.preventDefault();
    const eid = targetForm.reporting_entity_id || (entities[0]?.id ? String(entities[0].id) : "");
    if (!eid) {
      toast.error(t("Create a reporting entity before adding corporate targets."));
      return;
    }
    try {
      await api.post("/ogmp/targets", {
        ...targetForm,
        reporting_entity_id: Number(eid),
        target_year: Number(targetForm.target_year),
        upstream_target_pct: Number(targetForm.upstream_target_pct),
        midstream_target_pct: Number(targetForm.midstream_target_pct),
      });
      toast.success(t("Corporate OGMP target saved."));
      setTargetForm((p) => ({ ...p, notes: "" }));
      await loadAll();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to save OGMP target."));
    }
  };

  const handleGenerateDefaultPlan = async () => {
    if (!selectedFacilityId) {
      toast.error(t("Select an Oil & Gas facility first."));
      return;
    }
    const payload = { facility_id: Number(selectedFacilityId), generate_default: true };
    try {
      try {
        await api.post("/ogmp/implementation-plans", payload);
      } catch (err: any) {
        // the facility already has milestones: the default plan replaces them, so ask first
        if (err?.response?.status !== 409 || !err.response.data?.requires_confirmation) throw err;
        const ok = window.confirm(
          t("This facility already has {{count}} implementation-plan milestones. Replace them with the default Y0–Y10 plan?", {
            count: err.response.data.existing_count,
          }),
        );
        if (!ok) return;
        await api.post("/ogmp/implementation-plans", { ...payload, confirm: true });
      }
      toast.success(t("Generated Y0–Y10 UNEP OGMP 2.0 Implementation Plan milestones."));
      await loadAll();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to generate default implementation plan."));
    }
  };

  const handleAddMilestone = async (e: React.FormEvent) => {
    e.preventDefault();
    const fid = planForm.facility_id || selectedFacilityId;
    if (!fid) {
      toast.error(t("Select a facility first."));
      return;
    }
    try {
      await api.post("/ogmp/implementation-plans", {
        ...planForm,
        facility_id: Number(fid),
        planned_year: Number(planForm.planned_year),
        target_level: Number(planForm.target_level),
      });
      toast.success(t("Implementation milestone added."));
      await loadAll();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to add milestone."));
    }
  };

  const handleDeletePlan = async (id: number) => {
    try {
      await api.delete(`/ogmp/implementation-plans/${id}`);
      toast.success(t("Milestone deleted."));
      await loadAll();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || t("Failed to delete milestone."));
    }
  };

  const yearOptions = [currentYear + 1, currentYear, currentYear - 1, currentYear - 2, currentYear - 3];

  return (
    <div className="flex flex-col gap-6">
      {/* Shared Scope Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-ink-50 p-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <label htmlFor="ogmp-l4l5-facility" className="text-xs font-semibold text-text-secondary">
              {t("Asset / Facility")}
            </label>
            <NativeSelect
              id="ogmp-l4l5-facility"
              value={selectedFacilityId}
              onChange={(e) => {
                const v = e.target.value;
                setSelectedFacilityId(v);
                setSrcForm((p) => ({ ...p, facility_id: v }));
                setMeasForm((p) => ({ ...p, facility_id: v }));
                setEntityForm((p) => ({ ...p, facility_id: v }));
                setPlanForm((p) => ({ ...p, facility_id: v }));
              }}
              className="h-8 min-w-[200px] rounded-md border border-border bg-surface px-2.5 text-sm text-text"
            >
              <option value="">{t("All Oil & Gas Facilities")}</option>
              {ogFacilities.map((f) => (
                <option key={f.id} value={String(f.id)}>
                  {f.name} ({f.segment || "Upstream"})
                </option>
              ))}
            </NativeSelect>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="ogmp-l4l5-year" className="text-xs font-semibold text-text-secondary">
              {t("Reporting Year")}
            </label>
            <NativeSelect
              id="ogmp-l4l5-year"
              value={String(selectedYear)}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="h-8 w-28 rounded-md border border-border bg-surface px-2.5 text-sm text-text"
            >
              {yearOptions.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </NativeSelect>
          </div>
        </div>
        <Button size="sm" variant="secondary" onClick={loadAll} disabled={loading} className="gap-1.5">
          <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} aria-hidden="true" />
          {t("Refresh")}
        </Button>
      </div>

      {/* 1. SOURCE CATALOG (15 UP / 12 MID-DOWN, MI/N/A, YOY & ZERO EXPLANATIONS) */}
      {activeSubTab === "sources" && (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div className="rounded-lg border border-border bg-surface p-4">
              <div className="text-xs text-text-secondary">{t("Quantified Sources")}</div>
              <div className="mt-1 text-xl font-bold text-text">{liveMateriality.count}</div>
            </div>
            <div className="rounded-lg border border-border bg-surface p-4">
              <div className="text-xs text-text-secondary">{t("Total Bottom-Up CH₄")}</div>
              <div className="mt-1 text-xl font-bold font-mono text-text">
                {liveMateriality.total.toFixed(2)} tCH₄
              </div>
            </div>
            <div className="rounded-lg border border-border bg-surface p-4 sm:col-span-2">
              <div className="flex items-center justify-between text-xs text-text-secondary">
                <span>{t("L4 Source-Level Materiality Threshold (≥ 90% Standard / ≥ 70% w/ L3+ Justification)")}</span>
                <strong className="font-mono text-text">{liveMateriality.pct.toFixed(1)}%</strong>
              </div>
              <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-ink-100">
                <div
                  className={`h-full transition-all ${
                    liveMateriality.meets90
                      ? "bg-emerald-600"
                      : liveMateriality.meets70WithJust
                        ? "bg-amber-500"
                        : "bg-red-500"
                  }`}
                  style={{ width: `${Math.min(100, liveMateriality.pct)}%` }}
                />
              </div>
            </div>
          </div>

          <form onSubmit={handleAddSource} className="rounded-lg border border-border bg-surface p-4 flex flex-col gap-4">
            <h3 className="m-0 text-sm font-bold text-text flex items-center gap-2">
              <ClipboardList className="size-4 text-brand-600" aria-hidden="true" />
              {t("Log UNEP OGMP 2.0 Emission Source (L1–L4, Quantified / MI / N/A)")}
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <Field label={t("Segment")}>
                <NativeSelect
                  className={controlClass}
                  value={srcForm.segment}
                  onChange={(e) => setSrcForm((p) => ({ ...p, segment: e.target.value, source_code: "", source_name: "" }))}
                >
                  <option value="Upstream">{t("Upstream (15 Core Sources)")}</option>
                  <option value="Midstream">{t("Midstream / Downstream (12 Core Sources)")}</option>
                  <option value="Downstream">{t("Downstream")}</option>
                </NativeSelect>
              </Field>

              <Field label={t("Standard UNEP Source Category")}>
                <NativeSelect
                  className={controlClass}
                  value={srcForm.source_code}
                  onChange={(e) => {
                    const code = e.target.value;
                    const item = catalogList.find((c) => c.code === code);
                    setSrcForm((p) => ({
                      ...p,
                      source_code: code,
                      source_name: item?.name || p.source_name,
                      source_category: item?.category || p.source_category,
                      emission_factor_ref: item?.default_ef_ref || p.emission_factor_ref,
                    }));
                  }}
                >
                  <option value="">{t("Select catalog source or enter custom...")}</option>
                  {catalogList.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.code} — {c.name}
                    </option>
                  ))}
                </NativeSelect>
              </Field>

              <Field label={t("Status Flag")}>
                <NativeSelect
                  className={controlClass}
                  value={srcForm.status_flag}
                  onChange={(e) => setSrcForm((p) => ({ ...p, status_flag: e.target.value }))}
                >
                  <option value="Quantified">{t("Quantified")}</option>
                  <option value="MI">{t("MI (Missing Information)")}</option>
                  <option value="N/A">{t("N/A (Not Applicable / Absent)")}</option>
                </NativeSelect>
              </Field>

              <Field label={t("OGMP Reporting Level")}>
                <NativeSelect
                  className={controlClass}
                  value={String(srcForm.ogmp_level)}
                  onChange={(e) => setSrcForm((p) => ({ ...p, ogmp_level: Number(e.target.value) }))}
                >
                  <option value="4">{t("Level 4 — Direct Source Measurement / Eng.")}</option>
                  <option value="3">{t("Level 3 — Generic Component / Eq. EF")}</option>
                  <option value="2">{t("Level 2 — Simplified Category EF")}</option>
                  <option value="1">{t("Level 1 — Asset-Level Estimate")}</option>
                </NativeSelect>
              </Field>

              <Field label={t("Source Code *")}>
                <Input
                  value={srcForm.source_code}
                  onChange={(e) => setSrcForm((p) => ({ ...p, source_code: e.target.value }))}
                  placeholder="e.g. UP-01"
                  required
                />
              </Field>

              <Field label={t("Source Name *")}>
                <Input
                  value={srcForm.source_name}
                  onChange={(e) => setSrcForm((p) => ({ ...p, source_name: e.target.value }))}
                  placeholder="e.g. Fugitive component leaks (LDAR)"
                  required
                />
              </Field>

              <Field label={t("CH₄ Emissions (tCH₄)")}>
                <Input
                  type="number"
                  step="any"
                  min="0"
                  disabled={srcForm.status_flag !== "Quantified"}
                  value={srcForm.status_flag === "Quantified" ? srcForm.ch4_tonnes : "0"}
                  onChange={(e) => setSrcForm((p) => ({ ...p, ch4_tonnes: e.target.value }))}
                  placeholder="e.g. 42.5"
                />
              </Field>

              <Field label={t("95% Uncertainty (±%)")}>
                <Input
                  type="number"
                  step="any"
                  min="0"
                  max="500"
                  value={srcForm.uncertainty_pct}
                  onChange={(e) => setSrcForm((p) => ({ ...p, uncertainty_pct: e.target.value }))}
                />
              </Field>

              <Field label={t("Methodology / Pathway")}>
                <NativeSelect
                  className={controlClass}
                  value={srcForm.pathway_code}
                  onChange={(e) => setSrcForm((p) => ({ ...p, pathway_code: e.target.value }))}
                >
                  {pathways.map((pw) => (
                    <option key={pw.code} value={pw.code}>
                      {pw.title}
                    </option>
                  ))}
                </NativeSelect>
              </Field>

              <Field label={t("YoY > ±10% Change Explanation (if triggered)")}>
                <Input
                  value={srcForm.yoy_explanation}
                  onChange={(e) => setSrcForm((p) => ({ ...p, yoy_explanation: e.target.value }))}
                  placeholder={t("Required when YoY change exceeds ±10%")}
                />
              </Field>

              <Field label={t("Zero-Emission Explanation (if 0 tCH₄ Quantified)")} className="sm:col-span-2">
                <Input
                  value={srcForm.zero_emission_explanation}
                  onChange={(e) => setSrcForm((p) => ({ ...p, zero_emission_explanation: e.target.value }))}
                  placeholder={t("Explain e.g. zero-bleed instrument air retrofit / flare recovery online")}
                />
              </Field>
            </div>

            <div className="flex justify-end">
              <Button type="submit" variant="primary" className="gap-1.5">
                <Plus className="size-4" aria-hidden="true" />
                {t("Add Source Disclosure")}
              </Button>
            </div>
          </form>

          <RecordTable
            title={t("Registered L1–L4 Source Disclosures")}
            head={[
              t("Facility"),
              t("Year"),
              t("Code"),
              t("Source Name"),
              t("Level"),
              t("Flag"),
              t("CH₄ (t)"),
              t("Unc. (±%)"),
              t("YoY %"),
              t("Actions"),
            ]}
            empty={sources.length === 0 && t("No OGMP emission source records logged yet.")}
          >
            {sources.map((s) => (
              <Tr key={s.id}>
                <Td className="font-semibold">{s.facility_name || `#${s.facility_id}`}</Td>
                <Td>{s.year}</Td>
                <Td className="font-mono text-xs">{s.source_code}</Td>
                <Td>
                  <div>{s.source_name}</div>
                  {s.yoy_explanation && <div className="text-xs text-text-secondary">YoY: {s.yoy_explanation}</div>}
                  {s.zero_emission_explanation && (
                    <div className="text-xs text-text-secondary">0 tCH₄: {s.zero_emission_explanation}</div>
                  )}
                </Td>
                <Td>
                  <Badge tone={s.ogmp_level >= 4 ? "success" : s.ogmp_level === 3 ? "info" : "warning"}>L{s.ogmp_level}</Badge>
                </Td>
                <Td>
                  <Badge tone={s.status_flag === "Quantified" ? "brand" : "neutral"}>{t(s.status_flag)}</Badge>
                </Td>
                <Td className="font-mono font-semibold">{Number(s.ch4_tonnes || 0).toFixed(2)}</Td>
                <Td className="font-mono">±{Number(s.uncertainty_pct || 0).toFixed(1)}%</Td>
                <Td className="font-mono text-xs">
                  {s.yoy_change_pct != null ? `${s.yoy_change_pct > 0 ? "+" : ""}${s.yoy_change_pct}%` : "—"}
                </Td>
                <Td>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => handleDeleteSource(s.id)}
                    className="h-7 px-2 text-xs gap-1"
                  >
                    <Trash2 className="size-3" aria-hidden="true" />
                    {t("Delete")}
                  </Button>
                </Td>
              </Tr>
            ))}
          </RecordTable>
        </div>
      )}

      {/* 2. L5 SITE MEASUREMENTS & RSS RECONCILIATION */}
      {activeSubTab === "reconcile" && (
        <div className="flex flex-col gap-6">
          <div className="rounded-lg border border-brand-200 bg-brand-50/40 p-4 flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="m-0 text-sm font-bold text-text">{t("Run Level 4 vs. Level 5 RSS 95% CI Reconciliation")}</h3>
                <p className="m-0 mt-1 text-xs text-text-secondary">
                  {t("Computes RSS uncertainty bands, 95% CI overlap, ±20% variance check, L4 materiality (≥90% / ≥70% w/ justification), and Pathway 1–3 assignment.")}
                </p>
              </div>
              <Button variant="primary" onClick={handleRunReconciliation} className="gap-1.5">
                <Play className="size-4" aria-hidden="true" />
                {t("Run L4/L5 Reconciliation")}
              </Button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <Field label={t("Option Mode")}>
                <NativeSelect
                  className={controlClass}
                  value={recParams.option_mode}
                  onChange={(e) => setRecParams((p) => ({ ...p, option_mode: e.target.value }))}
                >
                  <option value="Option 1">{t("Option 1 (Annualized Site Comparison)")}</option>
                  <option value="Option 2">{t("Option 2 (Source-Aware Campaign)")}</option>
                </NativeSelect>
              </Field>
              {/* only a documented Pathway 2 conclusion can be recorded; it needs its explanation (F-GOGMP-01) */}
              <Field label={t("Pathway 2 conclusion (explained discrepancy)")}>
                <NativeSelect
                  className={controlClass}
                  value={recParams.pathway_code}
                  onChange={(e) => setRecParams((p) => ({ ...p, pathway_code: e.target.value }))}
                >
                  <option value="">{t("Auto-detect from sources & measurements")}</option>
                  {pathways.filter((pw) => String(pw.code).startsWith("2")).map((pw) => (
                    <option key={pw.code} value={pw.code}>
                      {t(pw.title)}
                    </option>
                  ))}
                </NativeSelect>
              </Field>
              {recParams.pathway_code && (
                <Field label={t("Explanation of the discrepancy")}>
                  <Input
                    value={recParams.pathway_explanation}
                    onChange={(e) => setRecParams((p) => ({ ...p, pathway_explanation: e.target.value }))}
                    required
                  />
                </Field>
              )}
              <Field label={t("Variance Threshold (±%)")}>
                <Input
                  type="number"
                  step="any"
                  value={recParams.threshold_pct}
                  onChange={(e) => setRecParams((p) => ({ ...p, threshold_pct: e.target.value }))}
                />
              </Field>
              <Field label={t("70–89% L4 Materiality Justification")}>
                <Input
                  value={recParams.l4_justification}
                  onChange={(e) => setRecParams((p) => ({ ...p, l4_justification: e.target.value }))}
                  placeholder={t("Justification if L4 materiality is 70–89.9%")}
                />
              </Field>
            </div>
          </div>

          <RecordTable
            title={t("Annual OGMP 2.0 Level 4 / Level 5 Reconciliation Reports")}
            head={[
              t("Facility"),
              t("Year"),
              t("OGMP Level"),
              t("Pathway"),
              t("Bottom-Up L4 (95% CI)"),
              t("Top-Down L5 (95% CI)"),
              t("L4 Mat. %"),
              t("Variance %"),
              t("CI Overlap"),
              t("Status"),
            ]}
            empty={annualReports.length === 0 && t("No annual reconciliation reports computed yet.")}
          >
            {annualReports.map((r) => (
              <Tr key={r.id}>
                <Td className="font-semibold">{r.facility_name || `#${r.facility_id}`}</Td>
                <Td>{r.year}</Td>
                <Td>
                  <Badge tone={r.reporting_level >= 5 ? "success" : r.reporting_level >= 4 ? "info" : "warning"}>
                    {r.reporting_level != null ? t("Level {{n}}", { n: r.reporting_level }) : t("Not assessable")}
                  </Badge>
                </Td>
                <Td>
                  <Badge tone="brand">P{r.pathway_code}</Badge>
                </Td>
                <Td className="font-mono text-xs">
                  <strong>{Number(r.total_bottom_up_tch4).toFixed(2)} t</strong>{" "}
                  [{Number(r.bu_ci_low_tch4).toFixed(1)}–{Number(r.bu_ci_high_tch4).toFixed(1)}]
                </Td>
                <Td className="font-mono text-xs">
                  <strong>{Number(r.total_top_down_tch4).toFixed(2)} t</strong>{" "}
                  [{Number(r.td_ci_low_tch4).toFixed(1)}–{Number(r.td_ci_high_tch4).toFixed(1)}]
                </Td>
                <Td className="font-mono">{Number(r.l4_materiality_pct).toFixed(1)}%</Td>
                <Td className="font-mono">{r.variance_pct != null ? `${r.variance_pct > 0 ? "+" : ""}${r.variance_pct}%` : "—"}</Td>
                <Td>
                  {r.ci_overlaps ? (
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700">
                      <CheckCircle2 className="size-3.5" aria-hidden="true" />
                      {t("Overlap")}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-700">
                      <AlertTriangle className="size-3.5" aria-hidden="true" />
                      {t("Disjoint")}
                    </span>
                  )}
                </Td>
                <Td>
                  {/* the engine's own outcome text (unknown statuses were shown as "Draft": F-GOGMP-02) */}
                  <span className="text-xs font-semibold">{t(r.reconciliation_status || "Not recorded")}</span>
                </Td>
              </Tr>
            ))}
          </RecordTable>

          <form onSubmit={handleAddMeasurement} className="rounded-lg border border-border bg-surface p-4 flex flex-col gap-4">
            <h3 className="m-0 text-sm font-bold text-text">{t("Log L5 Site Measurement Campaign (Instantaneous / Annualized)")}</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <Field label={t("Campaign Date *")}>
                <Input
                  type="date"
                  value={measForm.campaign_date}
                  onChange={(e) => setMeasForm((p) => ({ ...p, campaign_date: e.target.value }))}
                  required
                />
              </Field>
              <Field label={t("Measurement Method *")}>
                <NativeSelect
                  className={controlClass}
                  value={measForm.survey_type}
                  onChange={(e) => setMeasForm((p) => ({ ...p, survey_type: e.target.value }))}
                >
                  <option value="Aircraft / Hyperspectral Imaging">{t("Aircraft / Hyperspectral Imaging")}</option>
                  <option value="Drone LiDAR / OGI Survey">{t("Drone LiDAR / OGI Survey")}</option>
                  <option value="Satellite (Sentinel-5P/MethaneSAT)">{t("Satellite (Sentinel-5P/MethaneSAT)")}</option>
                  <option value="Mobile Van OGI / Tracer Gas">{t("Mobile Van OGI / Tracer Gas")}</option>
                  <option value="Fixed Continuous Sensor Network">{t("Fixed Continuous Sensor Network")}</option>
                </NativeSelect>
              </Field>
              <Field label={t("Mode")}>
                <NativeSelect
                  className={controlClass}
                  value={measForm.measurement_mode}
                  onChange={(e) => setMeasForm((p) => ({ ...p, measurement_mode: e.target.value }))}
                >
                  <option value="Annualized">{t("Annualized")}</option>
                  <option value="Instantaneous">{t("Instantaneous")}</option>
                </NativeSelect>
              </Field>
              <Field label={t("Reconciliation Option")}>
                <NativeSelect
                  className={controlClass}
                  value={measForm.option_mode}
                  onChange={(e) => setMeasForm((p) => ({ ...p, option_mode: e.target.value }))}
                >
                  <option value="Option 1">{t("Option 1")}</option>
                  <option value="Option 2">{t("Option 2")}</option>
                </NativeSelect>
              </Field>
              <Field label={t("Measured Rate (kg CH₄/hr) *")}>
                <Input
                  type="number"
                  step="any"
                  min="0"
                  value={measForm.measured_rate_kg_hr}
                  onChange={(e) => setMeasForm((p) => ({ ...p, measured_rate_kg_hr: e.target.value }))}
                  placeholder="e.g. 22.5"
                  required
                />
              </Field>
              <Field label={t("Operating Hours/yr")}>
                <Input
                  type="number"
                  step="any"
                  min="0"
                  max="8784"
                  value={measForm.operating_hours_year}
                  onChange={(e) => setMeasForm((p) => ({ ...p, operating_hours_year: e.target.value }))}
                />
              </Field>
              <Field label={t("95% Uncertainty (±%)")}>
                <Input
                  type="number"
                  step="any"
                  min="0"
                  max="500"
                  value={measForm.uncertainty_pct}
                  onChange={(e) => setMeasForm((p) => ({ ...p, uncertainty_pct: e.target.value }))}
                />
              </Field>
              {/* vendor and detection threshold are the campaign's own, entered here (F-GOGMP-05) */}
              <Field label={t("Instrument Vendor")}>
                <Input
                  value={measForm.instrument_vendor}
                  onChange={(e) => setMeasForm((p) => ({ ...p, instrument_vendor: e.target.value }))}
                />
              </Field>
              <Field label={t("Detection Threshold (kg/h)")}>
                <Input
                  type="number"
                  step="any"
                  min="0"
                  value={measForm.detection_threshold_kg_hr}
                  onChange={(e) => setMeasForm((p) => ({ ...p, detection_threshold_kg_hr: e.target.value }))}
                />
              </Field>
              <Field label={t("Notes (meteorology)")}>
                <Input
                  value={measForm.meteorological_notes}
                  onChange={(e) => setMeasForm((p) => ({ ...p, meteorological_notes: e.target.value }))}
                  placeholder={t("Wind 3.4 m/s SW")}
                />
              </Field>
            </div>
            <div className="flex justify-end">
              <Button type="submit" variant="primary" className="gap-1.5">
                <Plus className="size-4" aria-hidden="true" />
                {t("Save L5 Site Measurement")}
              </Button>
            </div>
          </form>

          <RecordTable
            title={t("L5 Site-Level Measurement Campaigns")}
            head={[t("Facility"), t("Date"), t("Method"), t("Mode / Option"), t("Rate (kg/hr)"), t("Annualized (tCH₄)"), t("95% CI"), t("Actions")]}
            empty={measurements.length === 0 && t("No L5 site measurement campaigns recorded yet.")}
          >
            {measurements.map((m) => (
              <Tr key={m.id}>
                <Td className="font-semibold">{m.facility_name || `#${m.facility_id}`}</Td>
                <Td className="whitespace-nowrap">{m.campaign_date}</Td>
                <Td>{m.survey_type}</Td>
                <Td className="text-xs">
                  {t(m.measurement_mode)} / {t(m.option_mode)}
                </Td>
                <Td className="font-mono">{Number(m.measured_rate_kg_hr).toFixed(2)}</Td>
                <Td className="font-mono font-bold text-success-fg">{Number(m.annualized_tch4).toFixed(2)}</Td>
                <Td className="font-mono text-xs">
                  [{Number(m.ci_low_tch4).toFixed(1)}–{Number(m.ci_high_tch4).toFixed(1)}] (±{m.uncertainty_pct}%)
                </Td>
                <Td>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => handleDeleteMeasurement(m.id)}
                    className="h-7 px-2 text-xs gap-1"
                  >
                    <Trash2 className="size-3" aria-hidden="true" />
                    {t("Delete")}
                  </Button>
                </Td>
              </Tr>
            ))}
          </RecordTable>
        </div>
      )}

      {/* 3. REPORTING ENTITIES, PORTFOLIO 95% MATERIALITY & TARGETS */}
      {activeSubTab === "entities" && (
        <div className="flex flex-col gap-6">
          {portfolio && (
            <div className="rounded-lg border border-border bg-surface p-4 flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-text-secondary flex items-center gap-1.5">
                  <Building2 className="size-4 text-brand-600" aria-hidden="true" />
                  {t("Portfolio Equity CH₄ Materiality Coverage (UNEP ≥ 95% Target)")}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-4 text-sm">
                  <span>
                    {t("Included Equity CH₄")}: <strong className="font-mono">{portfolio.included_equity_ch4_tch4.toFixed(2)} t</strong>
                  </span>
                  <span>
                    {t("Total Equity CH₄")}: <strong className="font-mono">{portfolio.total_equity_ch4_tch4.toFixed(2)} t</strong>
                  </span>
                  <span>
                    {t("Excluded NOJVs (<5%)")}: <strong>{portfolio.nojv_exclusion_count}</strong>
                  </span>
                  <span>
                    {t("Member-Reported NOJVs")}: <strong>{portfolio.member_reported_nojv_count}</strong>
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-2xl font-bold text-text">{portfolio.included_coverage_pct.toFixed(1)}%</span>
                <Badge tone={portfolio.meets_95pct_threshold ? "success" : "danger"}>
                  {portfolio.meets_95pct_threshold ? t("≥ 95% Materiality Met") : t("Below 95% Threshold")}
                </Badge>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <form onSubmit={handleAddEntity} className="rounded-lg border border-border bg-surface p-4 flex flex-col gap-3">
              <h3 className="m-0 text-sm font-bold text-text">{t("Register OGMP Reporting Entity / JV Boundary")}</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Field label={t("Entity Name *")}>
                  <Input
                    value={entityForm.entity_name}
                    onChange={(e) => setEntityForm((p) => ({ ...p, entity_name: e.target.value }))}
                    placeholder="e.g. Demo Basin Production JV"
                    required
                  />
                </Field>
                <Field label={t("Operator Status")}>
                  <NativeSelect
                    className={controlClass}
                    value={entityForm.operator_status}
                    onChange={(e) => setEntityForm((p) => ({ ...p, operator_status: e.target.value }))}
                  >
                    <option value="operated">{t("Operated (3-Yr Gold Horizon)")}</option>
                    <option value="non_operated">{t("Non-Operated JV (5-Yr Horizon)")}</option>
                  </NativeSelect>
                </Field>
                <Field label={t("Working Interest (%)")}>
                  <Input
                    type="number"
                    step="any"
                    min="0"
                    max="100"
                    value={entityForm.working_interest_pct}
                    onChange={(e) => setEntityForm((p) => ({ ...p, working_interest_pct: e.target.value }))}
                  />
                </Field>
                <Field label={t("Membership Year")}>
                  <Input
                    type="number"
                    value={entityForm.membership_year}
                    onChange={(e) => setEntityForm((p) => ({ ...p, membership_year: e.target.value }))}
                  />
                </Field>
              </div>
              {entityForm.operator_status === "non_operated" && (
                <div className="flex flex-col gap-2 rounded-md border border-border bg-ink-50 p-3 text-xs">
                  <label className="inline-flex items-center gap-2 font-medium text-text cursor-pointer">
                    <input
                      type="checkbox"
                      checked={entityForm.is_member_reported_nojv}
                      onChange={(e) => setEntityForm((p) => ({ ...p, is_member_reported_nojv: e.target.checked }))}
                    />
                    {t("Operator is an OGMP 2.0 Member Reporting Independently (NOJV Flag)")}
                  </label>
                  <label className="inline-flex items-center gap-2 font-medium text-text cursor-pointer">
                    <input
                      type="checkbox"
                      checked={entityForm.is_nojv_material_excluded}
                      onChange={(e) => setEntityForm((p) => ({ ...p, is_nojv_material_excluded: e.target.checked }))}
                    />
                    {t("Exclude under < 5% Equity Materiality Threshold")}
                  </label>
                  {entityForm.is_nojv_material_excluded && (
                    <Input
                      value={entityForm.exclusion_reason}
                      onChange={(e) => setEntityForm((p) => ({ ...p, exclusion_reason: e.target.value }))}
                      placeholder={t("Required justification for < 5% NOJV exclusion")}
                      required
                    />
                  )}
                </div>
              )}
              <div className="flex justify-end">
                <Button type="submit" variant="primary" size="sm" className="gap-1.5">
                  <Plus className="size-4" aria-hidden="true" />
                  {t("Save Reporting Entity")}
                </Button>
              </div>
            </form>

            <form onSubmit={handleAddTarget} className="rounded-lg border border-border bg-surface p-4 flex flex-col gap-3">
              <h3 className="m-0 text-sm font-bold text-text">{t("Set Corporate OGMP 2.0 Methane Targets")}</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Field label={t("Reporting Entity *")}>
                  <NativeSelect
                    className={controlClass}
                    value={targetForm.reporting_entity_id || (entities[0]?.id ? String(entities[0].id) : "")}
                    onChange={(e) => setTargetForm((p) => ({ ...p, reporting_entity_id: e.target.value }))}
                  >
                    <option value="">{t("Select Entity")}</option>
                    {entities.map((ent) => (
                      <option key={ent.id} value={String(ent.id)}>
                        {ent.entity_name}
                      </option>
                    ))}
                  </NativeSelect>
                </Field>
                <Field label={t("Target Year")}>
                  <Input
                    type="number"
                    value={targetForm.target_year}
                    onChange={(e) => setTargetForm((p) => ({ ...p, target_year: e.target.value }))}
                    required
                  />
                </Field>
                <Field label={t("Upstream Target (%)")}>
                  <Input
                    type="number"
                    step="any"
                    value={targetForm.upstream_target_pct}
                    onChange={(e) => setTargetForm((p) => ({ ...p, upstream_target_pct: e.target.value }))}
                  />
                </Field>
                <Field label={t("Mid/Downstream Target (%)")}>
                  <Input
                    type="number"
                    step="any"
                    value={targetForm.midstream_target_pct}
                    onChange={(e) => setTargetForm((p) => ({ ...p, midstream_target_pct: e.target.value }))}
                  />
                </Field>
              </div>
              <Field label={t("Commitment Notes")}>
                <Input
                  value={targetForm.notes}
                  onChange={(e) => setTargetForm((p) => ({ ...p, notes: e.target.value }))}
                  placeholder={t("e.g. UNEP OGMP 2.0 2025/2026 Gold Standard commitment")}
                />
              </Field>
              <div className="flex justify-end">
                <Button type="submit" variant="primary" size="sm" className="gap-1.5">
                  <Plus className="size-4" aria-hidden="true" />
                  {t("Save Target")}
                </Button>
              </div>
            </form>
          </div>

          <RecordTable
            title={t("Registered OGMP Reporting Entities & Equity Materiality")}
            head={[t("Entity"), t("Facility"), t("Operator Status"), t("Equity WI %"), t("Gold Target"), t("NOJV Flags"), t("Actions")]}
            empty={entities.length === 0 && t("No OGMP reporting entities registered yet.")}
          >
            {entities.map((e) => (
              <Tr key={e.id}>
                <Td className="font-semibold">{e.entity_name}</Td>
                <Td>{e.facility_name || "Portfolio-Wide"}</Td>
                <Td>{e.operator_status === "operated" ? t("Operated") : t("Non-Operated JV")}</Td>
                <Td className="font-mono">{e.working_interest_pct}%</Td>
                <Td className="font-mono">{e.target_gold_year}</Td>
                <Td className="text-xs">
                  {e.is_member_reported_nojv && <Badge tone="info">{t("Member NOJV")}</Badge>}
                  {e.is_nojv_material_excluded && <Badge tone="warning">{t("<5% Excluded")}</Badge>}
                </Td>
                <Td>
                  <Button size="sm" variant="danger" onClick={() => handleDeleteEntity(e.id)} className="h-7 px-2 text-xs">
                    {t("Delete")}
                  </Button>
                </Td>
              </Tr>
            ))}
          </RecordTable>

          {targets.length > 0 && (
            <RecordTable
              title={t("Corporate Targets")}
              head={[t("Entity"), t("Target Year"), t("Upstream Target"), t("Mid/Downstream Target"), t("Notes")]}
            >
              {targets.map((tg) => (
                <Tr key={tg.id}>
                  <Td className="font-semibold">{tg.entity_name || `#${tg.reporting_entity_id}`}</Td>
                  <Td className="font-mono">{tg.target_year}</Td>
                  <Td className="font-mono">{tg.upstream_target_pct}%</Td>
                  <Td className="font-mono">{tg.midstream_target_pct}%</Td>
                  <Td className="text-xs text-text-secondary">{tg.notes || "—"}</Td>
                </Tr>
              ))}
            </RecordTable>
          )}
        </div>
      )}

      {/* 4. Y0-Y10 IMPLEMENTATION PLAN & AUDIT TRAIL */}
      {activeSubTab === "plan" && (
        <div className="flex flex-col gap-6">
          <div className="rounded-lg border border-border bg-surface p-4 flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="m-0 text-sm font-bold text-text flex items-center gap-2">
                  <Compass className="size-4 text-brand-600" aria-hidden="true" />
                  {t("Y0–Y10 UNEP Gold Standard Implementation Plan")}
                </h3>
                <p className="m-0 mt-1 text-xs text-text-secondary">
                  {t("Tracks 3-year operated and 5-year non-operated Gold Standard milestones through Y10.")}
                </p>
              </div>
              <Button variant="secondary" onClick={handleGenerateDefaultPlan} className="gap-1.5">
                <Plus className="size-4" aria-hidden="true" />
                {t("Generate Y0–Y10 Default Plan")}
              </Button>
            </div>

            <form onSubmit={handleAddMilestone} className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-6 gap-3 items-end">
              <Field label={t("Horizon")}>
                <NativeSelect
                  className={controlClass}
                  value={planForm.milestone_horizon}
                  onChange={(e) => setPlanForm((p) => ({ ...p, milestone_horizon: e.target.value }))}
                >
                  {Array.from({ length: 11 }, (_, i) => `Y${i}`).map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </NativeSelect>
              </Field>
              <Field label={t("Planned Year")}>
                <Input
                  type="number"
                  value={planForm.planned_year}
                  onChange={(e) => setPlanForm((p) => ({ ...p, planned_year: e.target.value }))}
                />
              </Field>
              <Field label={t("Target Level")}>
                <NativeSelect
                  className={controlClass}
                  value={planForm.target_level}
                  onChange={(e) => setPlanForm((p) => ({ ...p, target_level: e.target.value }))}
                >
                  <option value="3">{t("Level {{n}}", { n: 3 })}</option>
                  <option value="4">{t("Level {{n}}", { n: 4 })}</option>
                  <option value="5">{t("Level {{n}}", { n: 5 })}</option>
                </NativeSelect>
              </Field>
              <Field label={t("Status")}>
                <NativeSelect
                  className={controlClass}
                  value={planForm.milestone_status}
                  onChange={(e) => setPlanForm((p) => ({ ...p, milestone_status: e.target.value }))}
                >
                  <option value="Planned">Planned</option>
                  <option value="In Progress">In Progress</option>
                  <option value="Completed">Completed</option>
                  <option value="Deferred">Deferred</option>
                </NativeSelect>
              </Field>
              <Field label={t("Methodology Upgrade")}>
                <Input
                  value={planForm.methodology_upgrade}
                  onChange={(e) => setPlanForm((p) => ({ ...p, methodology_upgrade: e.target.value }))}
                />
              </Field>
              <Button type="submit" variant="primary" className="gap-1.5">
                <Plus className="size-4" aria-hidden="true" />
                {t("Add Milestone")}
              </Button>
            </form>
          </div>

          <RecordTable
            title={t("Implementation Milestones")}
            head={[t("Facility"), t("Horizon"), t("Planned Year"), t("Target Level"), t("Status"), t("Methodology Upgrade"), t("Actions")]}
            empty={plans.length === 0 && t("No Y0–Y10 implementation milestones generated yet.")}
          >
            {plans.map((p) => (
              <Tr key={p.id}>
                <Td className="font-semibold">{p.asset_name || p.facility_name || `#${p.facility_id}`}</Td>
                <Td className="font-mono font-bold">{p.milestone_horizon}</Td>
                <Td className="font-mono">{p.planned_year}</Td>
                <Td>
                  <Badge tone={p.target_level >= 5 ? "success" : p.target_level === 4 ? "info" : "neutral"}>
                    {t("Level {{n}}", { n: p.target_level })}
                  </Badge>
                </Td>
                <Td>
                  <span className="text-xs font-semibold">{t(p.milestone_status || "Not recorded")}</span>
                </Td>
                <Td className="text-xs text-text-secondary">{p.methodology_upgrade || p.source_scope || "—"}</Td>
                <Td>
                  <Button size="sm" variant="danger" onClick={() => handleDeletePlan(p.id)} className="h-7 px-2 text-xs">
                    {t("Delete")}
                  </Button>
                </Td>
              </Tr>
            ))}
          </RecordTable>

          <RecordTable
            title={t("OGMP 2.0 Submission Audit Trail")}
            head={[t("Timestamp"), t("Actor"), t("Action"), t("Entity"), t("Summary")]}
            empty={auditTrail.length === 0 && t("No OGMP audit events recorded yet.")}
          >
            {auditTrail.slice(0, 25).map((a) => (
              <Tr key={a.id}>
                <Td className="whitespace-nowrap text-xs font-mono">
                  {a.created_at ? new Date(a.created_at).toLocaleString() : "—"}
                </Td>
                <Td className="text-xs font-medium">{a.actor_name}</Td>
                <Td>
                  <Badge tone="brand" className="text-[0.65rem]">
                    {a.action}
                  </Badge>
                </Td>
                <Td className="text-xs font-mono">
                  {a.entity_type} #{a.entity_id}
                </Td>
                <Td className="text-xs text-text-secondary">{a.summary}</Td>
              </Tr>
            ))}
          </RecordTable>
        </div>
      )}
    </div>
  );
};

export default OgmpL4L5Panel;
