import React, { useState, useEffect, useMemo } from "react";
import { Badge, Button, Field, Input, cn } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import Modal from "../../components/Modal";
import { useToast } from "../../components/Toast";
import { TabCard, RecordTable, Tr, Td } from "./MdParts";
import { t } from "../../i18n";
import api from "../../api";
import { apiError } from "../../utils/apiError";
import { Wrench, Plus, CheckCircle, AlertTriangle, RotateCcw, CheckSquare, Trash2, Edit3 } from "lucide-react";

export interface LdarTabProps {
  facilities: Array<{
    id: string | number;
    name: string;
    activity?: string;
    division?: string;
    location?: string;
    region_identifier?: string;
    [key: string]: any;
  }>;
  isPrivileged?: boolean;
  searchTerm?: string;
  filterActivity?: string;
  filterDivision?: string;
  filterRegion?: string;
}

interface ComponentItem {
  id: number;
  facility_id: number;
  facility_name?: string;
  equipment_type: string;
  component_type: string;
  service_type: string;
  quantity: number;
  operating_hours: number;
  status: string;
  description?: string;
}

interface SurveyItem {
  id: number;
  facility_id: number;
  facility_name?: string;
  component_inventory_id?: number;
  survey_method: string;
  survey_date: string;
  detection_threshold_ppm?: number;
  screening_value_ppm?: number;
  leak_status: string;
  measured_emission_rate?: number;
  measurement_unit?: string;
  repair_date?: string;
  leaking_hours?: number;
  surveyor_name?: string;
  notes?: string;
}

export const LdarTab: React.FC<LdarTabProps> = ({
  facilities,
  isPrivileged,
  searchTerm = "",
  filterActivity = "",
  filterDivision = "",
  filterRegion = "",
}) => {
  const toast = useToast();
  const [activeSubTab, setActiveSubTab] = useState<"surveys" | "components">("surveys");
  const [surveys, setSurveys] = useState<SurveyItem[]>([]);
  const [components, setComponents] = useState<ComponentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  // In-tab filters
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [methodFilter, setMethodFilter] = useState<string>("all");
  const [equipmentFilter, setEquipmentFilter] = useState<string>("all");
  const [componentStatusFilter, setComponentStatusFilter] = useState<string>("all");

  // Selection states for bulk actions
  const [selectedSurveyIds, setSelectedSurveyIds] = useState<Set<number>>(new Set());
  const [selectedCompIds, setSelectedCompIds] = useState<Set<number>>(new Set());

  // Bulk update modals state
  const [bulkCompModal, setBulkCompModal] = useState<{
    isOpen: boolean;
    status: string;
    service_type: string;
    operating_hours: string;
  }>({
    isOpen: false,
    status: "",
    service_type: "",
    operating_hours: "",
  });

  const [bulkSurveyModal, setBulkSurveyModal] = useState<{
    isOpen: boolean;
    leak_status: string;
    repairDate: string;
    postRepairPpm: string;
    notes: string;
  }>({
    isOpen: false,
    leak_status: "Repaired",
    repairDate: new Date().toISOString().split("T")[0],
    postRepairPpm: "0",
    notes: "",
  });

  // Repair Modal State
  const [repairModal, setRepairModal] = useState<{
    isOpen: boolean;
    survey: SurveyItem | null;
    repairDate: string;
    postRepairPpm: string;
    notes: string;
  }>({
    isOpen: false,
    survey: null,
    repairDate: new Date().toISOString().split("T")[0],
    postRepairPpm: "0",
    notes: "",
  });

  // Record Survey Modal State
  const [surveyModal, setSurveyModal] = useState<{
    isOpen: boolean;
    facility_id: string;
    component_inventory_id: string;
    survey_method: string;
    survey_date: string;
    screening_value_ppm: string;
    leak_status: string;
    leaking_hours: string;
    surveyor_name: string;
    notes: string;
  }>({
    isOpen: false,
    facility_id: "",
    component_inventory_id: "",
    survey_method: "Method 21",
    survey_date: new Date().toISOString().split("T")[0],
    screening_value_ppm: "0",
    leak_status: "Non-leaking",
    leaking_hours: "8760",
    surveyor_name: "",
    notes: "",
  });

  // Add Component Modal State
  const [compModal, setCompModal] = useState<{
    isOpen: boolean;
    facility_id: string;
    equipment_type: string;
    component_type: string;
    service_type: string;
    quantity: string;
    operating_hours: string;
    status: string;
    description: string;
  }>({
    isOpen: false,
    facility_id: "",
    equipment_type: "Valves",
    component_type: "Gate Valve",
    service_type: "Gas",
    quantity: "1",
    operating_hours: "8760",
    status: "Active",
    description: "",
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [surveysRes, compRes] = await Promise.all([
        api.get("/ldar/surveys"),
        api.get("/ldar/components"),
      ]);
      setSurveys(surveysRes.data?.surveys || []);
      setComponents(compRes.data?.components || []);
    } catch (err) {
      toast.show(apiError(err), "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleOpenRepairModal = (survey: SurveyItem) => {
    setRepairModal({
      isOpen: true,
      survey,
      repairDate: new Date().toISOString().split("T")[0],
      postRepairPpm: "0",
      notes: survey.notes || "",
    });
  };

  const handleSaveRepair = async () => {
    if (!repairModal.survey) return;
    try {
      await api.put(`/ldar/surveys/${repairModal.survey.id}`, {
        leak_status: "Repaired",
        repair_date: repairModal.repairDate,
        screening_value_ppm: parseFloat(repairModal.postRepairPpm) || 0,
        notes: repairModal.notes
          ? `${repairModal.survey.notes ? repairModal.survey.notes + " | " : ""}Repaired: ${repairModal.notes}`
          : repairModal.survey.notes,
      });
      toast.show(t("Leak marked as repaired successfully"), "success");
      setRepairModal((prev) => ({ ...prev, isOpen: false, survey: null }));
      fetchData();
    } catch (err) {
      toast.show(apiError(err), "error");
    }
  };

  const handleSaveSurvey = async () => {
    if (!surveyModal.facility_id) {
      toast.show(t("Facility is required"), "warning");
      return;
    }
    try {
      await api.post("/ldar/surveys", {
        facility_id: parseInt(surveyModal.facility_id, 10),
        component_inventory_id: surveyModal.component_inventory_id
          ? parseInt(surveyModal.component_inventory_id, 10)
          : null,
        survey_method: surveyModal.survey_method,
        survey_date: surveyModal.survey_date,
        screening_value_ppm: parseFloat(surveyModal.screening_value_ppm) || 0,
        leak_status: surveyModal.leak_status,
        leaking_hours: parseFloat(surveyModal.leaking_hours) || 8760,
        surveyor_name: surveyModal.surveyor_name,
        notes: surveyModal.notes,
      });
      toast.show(t("Survey logged successfully"), "success");
      setSurveyModal((prev) => ({ ...prev, isOpen: false }));
      fetchData();
    } catch (err) {
      toast.show(apiError(err), "error");
    }
  };

  const handleSaveComponent = async () => {
    if (!compModal.facility_id) {
      toast.show(t("Facility is required"), "warning");
      return;
    }
    try {
      await api.post("/ldar/components", {
        facility_id: parseInt(compModal.facility_id, 10),
        equipment_type: compModal.equipment_type,
        component_type: compModal.component_type,
        service_type: compModal.service_type,
        quantity: parseInt(compModal.quantity, 10) || 1,
        operating_hours: parseFloat(compModal.operating_hours) || 8760,
        status: compModal.status || "Active",
        description: compModal.description,
      });
      toast.show(t("Component added successfully"), "success");
      setCompModal((prev) => ({ ...prev, isOpen: false }));
      fetchData();
    } catch (err) {
      toast.show(apiError(err), "error");
    }
  };

  // Bulk Handlers for Components
  const handleBulkUpdateComponents = async () => {
    if (selectedCompIds.size === 0) return;
    const payload: Record<string, any> = {
      ids: Array.from(selectedCompIds),
    };
    if (bulkCompModal.status) payload.status = bulkCompModal.status;
    if (bulkCompModal.service_type) payload.service_type = bulkCompModal.service_type;
    if (bulkCompModal.operating_hours) {
      const hrs = parseFloat(bulkCompModal.operating_hours);
      if (!isNaN(hrs)) payload.operating_hours = hrs;
    }

    if (!payload.status && !payload.service_type && payload.operating_hours === undefined) {
      toast.show(t("Please select at least one attribute to update"), "warning");
      return;
    }

    try {
      const res = await api.post("/ldar/components/bulk-update", payload);
      toast.show(
        t("Successfully updated {{count}} components", {
          count: res.data?.updated_count || selectedCompIds.size,
        }),
        "success"
      );
      setBulkCompModal((prev) => ({ ...prev, isOpen: false }));
      setSelectedCompIds(new Set());
      fetchData();
    } catch (err) {
      toast.show(apiError(err), "error");
    }
  };

  const handleBulkDeleteComponents = async () => {
    if (selectedCompIds.size === 0) return;
    if (
      !window.confirm(
        t("Are you sure you want to delete {{count}} selected components?", {
          count: selectedCompIds.size,
        })
      )
    ) {
      return;
    }
    try {
      const res = await api.post("/ldar/components/bulk-delete", {
        ids: Array.from(selectedCompIds),
      });
      toast.show(
        t("Successfully deleted {{count}} components", {
          count: res.data?.deleted_count || selectedCompIds.size,
        }),
        "success"
      );
      setSelectedCompIds(new Set());
      fetchData();
    } catch (err) {
      toast.show(apiError(err), "error");
    }
  };

  // Bulk Handlers for Surveys
  const handleBulkUpdateSurveys = async () => {
    if (selectedSurveyIds.size === 0) return;
    const payload: Record<string, any> = {
      ids: Array.from(selectedSurveyIds),
      leak_status: bulkSurveyModal.leak_status,
    };
    if (bulkSurveyModal.leak_status === "Repaired") {
      payload.repair_date = bulkSurveyModal.repairDate;
      payload.screening_value_ppm = parseFloat(bulkSurveyModal.postRepairPpm) || 0;
    }
    if (bulkSurveyModal.notes) {
      payload.notes = bulkSurveyModal.notes;
    }

    try {
      const res = await api.post("/ldar/surveys/bulk-update", payload);
      toast.show(
        t("Successfully updated {{count}} surveys", {
          count: res.data?.updated_count || selectedSurveyIds.size,
        }),
        "success"
      );
      setBulkSurveyModal((prev) => ({ ...prev, isOpen: false }));
      setSelectedSurveyIds(new Set());
      fetchData();
    } catch (err) {
      toast.show(apiError(err), "error");
    }
  };

  const handleBulkDeleteSurveys = async () => {
    if (selectedSurveyIds.size === 0) return;
    if (
      !window.confirm(
        t("Are you sure you want to delete {{count}} selected surveys?", {
          count: selectedSurveyIds.size,
        })
      )
    ) {
      return;
    }
    try {
      const res = await api.post("/ldar/surveys/bulk-delete", {
        ids: Array.from(selectedSurveyIds),
      });
      toast.show(
        t("Successfully deleted {{count}} surveys", {
          count: res.data?.deleted_count || selectedSurveyIds.size,
        }),
        "success"
      );
      setSelectedSurveyIds(new Set());
      fetchData();
    } catch (err) {
      toast.show(apiError(err), "error");
    }
  };

  const surveyCounts = useMemo(() => {
    let leaking = 0;
    let repaired = 0;
    let nonLeaking = 0;
    surveys.forEach((s) => {
      if (s.leak_status === "Leaking") leaking++;
      else if (s.leak_status === "Repaired") repaired++;
      else nonLeaking++;
    });
    return { all: surveys.length, leaking, repaired, nonLeaking };
  }, [surveys]);

  const surveyStatusOptions = [
    { value: "all", label: t("All Statuses"), count: surveyCounts.all },
    { value: "Leaking", label: t("Leaking"), count: surveyCounts.leaking, tone: "danger" as const },
    { value: "Repaired", label: t("Repaired"), count: surveyCounts.repaired, tone: "success" as const },
    { value: "Non-leaking", label: t("Non-leaking"), count: surveyCounts.nonLeaking },
  ];

  const surveyMethodOptions = [
    { value: "all", label: t("All Methods") },
    { value: "Method 21", label: t("Method 21") },
    { value: "OGI", label: t("OGI") },
    { value: "Acoustic", label: t("Acoustic") },
  ];

  const compEquipmentOptions = [
    { value: "all", label: t("All Equipment") },
    { value: "Valves", label: t("Valves") },
    { value: "Flanges", label: t("Flanges") },
    { value: "Pumps", label: t("Pumps") },
    { value: "Compressors", label: t("Compressors") },
    { value: "Relief Valves", label: t("Relief Valves") },
  ];

  const compStatusOptions = [
    { value: "all", label: t("All Statuses") },
    { value: "Active", label: t("Active") },
    { value: "Broken", label: t("Broken") },
    { value: "Leaking", label: t("Leaking") },
    { value: "Inactive", label: t("Inactive") },
  ];

  const getComponentStatusBadge = (status: string) => {
    const s = (status || "Active").toLowerCase();
    if (s === "broken" || s === "leaking" || s === "damaged" || s === "faulty") {
      return (
        <Badge tone="danger" className="inline-flex items-center gap-1">
          <AlertTriangle className="size-3" />
          {t(status)}
        </Badge>
      );
    }
    if (s === "active") {
      return <Badge tone="success">{t("Active")}</Badge>;
    }
    return <Badge tone="neutral">{t(status || "Inactive")}</Badge>;
  };

  const filteredSurveys = useMemo(() => {
    return surveys.filter((s) => {
      const fac = facilities.find((f) => f.id === s.facility_id);
      const facName = s.facility_name || fac?.name || `Facility #${s.facility_id}`;

      if (filterRegion && filterRegion !== "all") {
        const facRegion = fac?.region_identifier || fac?.location || "";
        if (facRegion !== filterRegion && !facRegion.includes(filterRegion)) return false;
      }
      if (filterActivity) {
        if (!fac?.activity || fac.activity !== filterActivity) return false;
      }
      if (filterDivision) {
        if (!fac?.division || fac.division !== filterDivision) return false;
      }
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matches =
          facName.toLowerCase().includes(term) ||
          (s.survey_method || "").toLowerCase().includes(term) ||
          (s.surveyor_name || "").toLowerCase().includes(term) ||
          (s.notes || "").toLowerCase().includes(term) ||
          (s.survey_date || "").includes(term);
        if (!matches) return false;
      }

      if (statusFilter !== "all" && s.leak_status !== statusFilter) return false;
      if (methodFilter !== "all" && s.survey_method !== methodFilter) return false;

      return true;
    });
  }, [surveys, facilities, filterRegion, filterActivity, filterDivision, searchTerm, statusFilter, methodFilter]);

  const filteredComponents = useMemo(() => {
    return components.filter((c) => {
      const fac = facilities.find((f) => f.id === c.facility_id);
      const facName = c.facility_name || fac?.name || `Facility #${c.facility_id}`;

      if (filterRegion && filterRegion !== "all") {
        const facRegion = fac?.region_identifier || fac?.location || "";
        if (facRegion !== filterRegion && !facRegion.includes(filterRegion)) return false;
      }
      if (filterActivity) {
        if (!fac?.activity || fac.activity !== filterActivity) return false;
      }
      if (filterDivision) {
        if (!fac?.division || fac.division !== filterDivision) return false;
      }
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matches =
          facName.toLowerCase().includes(term) ||
          (c.equipment_type || "").toLowerCase().includes(term) ||
          (c.component_type || "").toLowerCase().includes(term) ||
          (c.service_type || "").toLowerCase().includes(term) ||
          (c.description || "").toLowerCase().includes(term);
        if (!matches) return false;
      }

      if (equipmentFilter !== "all" && c.equipment_type !== equipmentFilter) return false;
      if (componentStatusFilter !== "all" && (c.status || "Active") !== componentStatusFilter) return false;

      return true;
    });
  }, [components, facilities, filterRegion, filterActivity, filterDivision, searchTerm, equipmentFilter, componentStatusFilter]);

  const getStatusBadge = (status: string) => {
    if (status === "Leaking") {
      return (
        <Badge tone="danger" className="inline-flex items-center gap-1">
          <AlertTriangle className="size-3" />
          {t("Leaking")}
        </Badge>
      );
    }
    if (status === "Repaired") {
      return (
        <Badge tone="success" className="inline-flex items-center gap-1">
          <CheckCircle className="size-3" />
          {t("Repaired")}
        </Badge>
      );
    }
    return <Badge tone="neutral">{t(status || "Non-leaking")}</Badge>;
  };

  const isAllSurveysSelected =
    filteredSurveys.length > 0 &&
    filteredSurveys.every((s) => selectedSurveyIds.has(s.id));

  const toggleSelectAllSurveys = () => {
    if (isAllSurveysSelected) {
      setSelectedSurveyIds(new Set());
    } else {
      setSelectedSurveyIds(new Set(filteredSurveys.map((s) => s.id)));
    }
  };

  const toggleSurveySelection = (id: number) => {
    setSelectedSurveyIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const isAllCompsSelected =
    filteredComponents.length > 0 &&
    filteredComponents.every((c) => selectedCompIds.has(c.id));

  const toggleSelectAllComps = () => {
    if (isAllCompsSelected) {
      setSelectedCompIds(new Set());
    } else {
      setSelectedCompIds(new Set(filteredComponents.map((c) => c.id)));
    }
  };

  const toggleCompSelection = (id: number) => {
    setSelectedCompIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSwitchTab = (tab: "surveys" | "components") => {
    setActiveSubTab(tab);
    setSelectedSurveyIds(new Set());
    setSelectedCompIds(new Set());
  };

  return (
    <TabCard
      title={t("LDAR & Fugitive Leak Management")}
      description={t(
        "Track leak detection surveys (EPA Method 21 / OGI) and manage component inventories with leak repair workflow.",
      )}
      actions={
        <div className="flex flex-wrap items-center gap-3">
          {/* Subtab Segmented Switcher */}
          <div className="inline-flex items-center gap-1 rounded-lg border border-border bg-ink-100 p-1">
            <button
              type="button"
              onClick={() => handleSwitchTab("surveys")}
              className={cn(
                "inline-flex items-center gap-2 rounded-md px-3.5 py-1.5 text-xs font-semibold transition-all duration-150 cursor-pointer border-0",
                activeSubTab === "surveys"
                  ? "bg-surface text-text shadow-xs"
                  : "bg-transparent text-text-secondary hover:text-text hover:bg-surface/50"
              )}
            >
              <span>{t("Surveys & Repairs")}</span>
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[10px] font-bold transition-colors",
                  activeSubTab === "surveys"
                    ? "bg-ink-100 text-text"
                    : "bg-ink-200/70 text-text-secondary"
                )}
              >
                {filteredSurveys.length}
              </span>
            </button>
            <button
              type="button"
              onClick={() => handleSwitchTab("components")}
              className={cn(
                "inline-flex items-center gap-2 rounded-md px-3.5 py-1.5 text-xs font-semibold transition-all duration-150 cursor-pointer border-0",
                activeSubTab === "components"
                  ? "bg-surface text-text shadow-xs"
                  : "bg-transparent text-text-secondary hover:text-text hover:bg-surface/50"
              )}
            >
              <span>{t("Component Inventory")}</span>
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[10px] font-bold transition-colors",
                  activeSubTab === "components"
                    ? "bg-ink-100 text-text"
                    : "bg-ink-200/70 text-text-secondary"
                )}
              >
                {filteredComponents.length}
              </span>
            </button>
          </div>

          {activeSubTab === "surveys" ? (
            <Button
              variant="primary"
              onClick={() =>
                setSurveyModal((prev) => ({
                  ...prev,
                  isOpen: true,
                  facility_id: facilities[0]?.id ? String(facilities[0].id) : "",
                }))
              }
              className="inline-flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="size-4" />
              {t("Record Survey")}
            </Button>
          ) : (
            <Button
              variant="primary"
              onClick={() =>
                setCompModal((prev) => ({
                  ...prev,
                  isOpen: true,
                  facility_id: facilities[0]?.id ? String(facilities[0].id) : "",
                }))
              }
              className="inline-flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="size-4" />
              {t("Add Component")}
            </Button>
          )}
        </div>
      }
    >
      {activeSubTab === "surveys" ? (
        <>
          {/* Segmented Filter Pills */}
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-ink-50/50 p-3">
            <div className="flex flex-wrap items-center gap-4">
              {/* Leak Status */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                  {t("Status")}:
                </span>
                <div className="inline-flex flex-wrap items-center gap-1 rounded-lg border border-border bg-ink-100 p-1">
                  {surveyStatusOptions.map((opt) => {
                    const active = statusFilter === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setStatusFilter(opt.value)}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer border-0",
                          active
                            ? "bg-surface text-text shadow-xs"
                            : "bg-transparent text-text-secondary hover:text-text hover:bg-surface/50"
                        )}
                      >
                        {opt.tone === "danger" && (
                          <span className="size-2 rounded-full bg-danger-fg" />
                        )}
                        {opt.tone === "success" && (
                          <span className="size-2 rounded-full bg-success-fg" />
                        )}
                        <span>{opt.label}</span>
                        <span
                          className={cn(
                            "rounded-full px-1.5 py-0.2 text-[10px]",
                            active
                              ? "bg-ink-100 text-text font-bold"
                              : "bg-ink-200/60 text-text-secondary font-medium"
                          )}
                        >
                          {opt.count}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Method */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                  {t("Method")}:
                </span>
                <div className="inline-flex flex-wrap items-center gap-1 rounded-lg border border-border bg-ink-100 p-1">
                  {surveyMethodOptions.map((opt) => {
                    const active = methodFilter === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setMethodFilter(opt.value)}
                        className={cn(
                          "rounded-md px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer border-0",
                          active
                            ? "bg-surface text-text shadow-xs"
                            : "bg-transparent text-text-secondary hover:text-text hover:bg-surface/50"
                        )}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {(statusFilter !== "all" || methodFilter !== "all") && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setStatusFilter("all");
                  setMethodFilter("all");
                }}
                className="h-8 px-2.5 text-xs font-semibold text-text-secondary hover:text-text"
              >
                <RotateCcw className="size-3 mr-1" />
                {t("Reset")}
              </Button>
            )}
          </div>

          {/* Survey Bulk Action Bar */}
          {selectedSurveyIds.size > 0 && (
            <div
              role="region"
              aria-label={t("Survey bulk actions")}
              className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-brand-200 bg-brand-50/80 p-3 shadow-2xs"
            >
              <div className="flex items-center gap-2">
                <CheckSquare className="size-4 text-brand-600" />
                <span className="text-sm font-semibold text-brand-900">
                  {t("{{count}} survey(s) selected", { count: selectedSurveyIds.size })}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() =>
                    setBulkSurveyModal({
                      isOpen: true,
                      leak_status: "Repaired",
                      repairDate: new Date().toISOString().split("T")[0],
                      postRepairPpm: "0",
                      notes: "",
                    })
                  }
                  className="inline-flex items-center gap-1.5 shadow-2xs"
                >
                  <Wrench className="size-3.5" />
                  {t("Bulk Mark Repaired / Update")}
                </Button>
                {isPrivileged && (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={handleBulkDeleteSurveys}
                    className="inline-flex items-center gap-1.5 shadow-2xs"
                  >
                    <Trash2 className="size-3.5" />
                    {t("Bulk Delete")}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedSurveyIds(new Set())}
                  className="text-text-secondary hover:text-text text-xs font-semibold"
                >
                  {t("Deselect All")}
                </Button>
              </div>
            </div>
          )}

          <RecordTable
            title={t("Fugitive Leak Surveys")}
            head={[
              <input
                key="select-all-surveys"
                type="checkbox"
                aria-label={t("Select all surveys")}
                checked={isAllSurveysSelected}
                onChange={toggleSelectAllSurveys}
                className="size-4 rounded border-border text-brand-600 focus:ring-brand-500 cursor-pointer"
              />,
              t("Facility"),
              t("Date"),
              t("Method"),
              t("Screening (PPM)"),
              t("Leak Status"),
              t("Repair Date"),
              t("Duration (hrs)"),
              t("Actions"),
            ]}
            empty={loading ? t("Loading surveys...") : t("No LDAR surveys recorded yet.")}
          >
            {filteredSurveys.map((s) => (
              <Tr key={s.id} className={selectedSurveyIds.has(s.id) ? "bg-brand-50/30" : undefined}>
                <Td className="w-10">
                  <input
                    type="checkbox"
                    aria-label={`Select survey ${s.id}`}
                    checked={selectedSurveyIds.has(s.id)}
                    onChange={() => toggleSurveySelection(s.id)}
                    className="size-4 rounded border-border text-brand-600 focus:ring-brand-500 cursor-pointer"
                  />
                </Td>
                <Td className="font-medium text-text">
                  {s.facility_name || facilities.find((f) => f.id === s.facility_id)?.name || s.facility_id}
                </Td>
                <Td>{s.survey_date}</Td>
                <Td>
                  <span className="inline-flex items-center rounded-md bg-ink-100 px-2 py-0.5 text-xs font-medium text-text">
                    {s.survey_method}
                  </span>
                </Td>
                <Td className="font-mono">
                  {s.screening_value_ppm !== undefined && s.screening_value_ppm !== null
                    ? `${s.screening_value_ppm.toLocaleString()} ppm`
                    : "-"}
                </Td>
                <Td>{getStatusBadge(s.leak_status)}</Td>
                <Td>{s.repair_date || "-"}</Td>
                <Td className="font-mono">{s.leaking_hours !== undefined ? s.leaking_hours : 8760}</Td>
                <Td>
                  {s.leak_status === "Leaking" && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleOpenRepairModal(s)}
                      className="inline-flex items-center gap-1.5 rounded-md border border-brand-300 bg-brand-50/70 px-2.5 py-1 text-xs font-semibold text-brand-700 shadow-2xs hover:bg-brand-100 hover:border-brand-400 transition-colors"
                    >
                      <Wrench className="size-3.5 text-brand-600" />
                      {t("Mark Repaired")}
                    </Button>
                  )}
                  {s.leak_status === "Repaired" && (
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-success-fg">
                      <CheckCircle className="size-3.5" />
                      {t("Completed")}
                    </span>
                  )}
                  {s.leak_status !== "Leaking" && s.leak_status !== "Repaired" && (
                    <span className="text-xs text-text-secondary">-</span>
                  )}
                </Td>
              </Tr>
            ))}
          </RecordTable>
        </>
      ) : (
        <>
          {/* Component Inventory Segmented Filters */}
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-ink-50/50 p-3">
            <div className="flex flex-wrap items-center gap-4">
              {/* Equipment */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                  {t("Equipment")}:
                </span>
                <div className="inline-flex flex-wrap items-center gap-1 rounded-lg border border-border bg-ink-100 p-1">
                  {compEquipmentOptions.map((opt) => {
                    const active = equipmentFilter === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setEquipmentFilter(opt.value)}
                        className={cn(
                          "rounded-md px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer border-0",
                          active
                            ? "bg-surface text-text shadow-xs"
                            : "bg-transparent text-text-secondary hover:text-text hover:bg-surface/50"
                        )}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Status */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                  {t("Status")}:
                </span>
                <div className="inline-flex flex-wrap items-center gap-1 rounded-lg border border-border bg-ink-100 p-1">
                  {compStatusOptions.map((opt) => {
                    const active = componentStatusFilter === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setComponentStatusFilter(opt.value)}
                        className={cn(
                          "rounded-md px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer border-0",
                          active
                            ? "bg-surface text-text shadow-xs"
                            : "bg-transparent text-text-secondary hover:text-text hover:bg-surface/50"
                        )}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            {(equipmentFilter !== "all" || componentStatusFilter !== "all") && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setEquipmentFilter("all");
                  setComponentStatusFilter("all");
                }}
                className="h-8 px-2.5 text-xs font-semibold text-text-secondary hover:text-text"
              >
                <RotateCcw className="size-3 mr-1" />
                {t("Reset")}
              </Button>
            )}
          </div>

          {/* Component Bulk Action Bar */}
          {selectedCompIds.size > 0 && (
            <div
              role="region"
              aria-label={t("Component bulk actions")}
              className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-brand-200 bg-brand-50/80 p-3 shadow-2xs"
            >
              <div className="flex items-center gap-2">
                <CheckSquare className="size-4 text-brand-600" />
                <span className="text-sm font-semibold text-brand-900">
                  {t("{{count}} component(s) selected", { count: selectedCompIds.size })}
                </span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() =>
                    setBulkCompModal({
                      isOpen: true,
                      status: "",
                      service_type: "",
                      operating_hours: "",
                    })
                  }
                  className="inline-flex items-center gap-1.5 shadow-2xs"
                >
                  <Edit3 className="size-3.5" />
                  {t("Bulk Update")}
                </Button>
                {isPrivileged && (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={handleBulkDeleteComponents}
                    className="inline-flex items-center gap-1.5 shadow-2xs"
                  >
                    <Trash2 className="size-3.5" />
                    {t("Bulk Delete")}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedCompIds(new Set())}
                  className="text-text-secondary hover:text-text text-xs font-semibold"
                >
                  {t("Deselect All")}
                </Button>
              </div>
            </div>
          )}

          <RecordTable
            title={t("Component Inventory")}
            head={[
              <input
                key="select-all-comps"
                type="checkbox"
                aria-label={t("Select all components")}
                checked={isAllCompsSelected}
                onChange={toggleSelectAllComps}
                className="size-4 rounded border-border text-brand-600 focus:ring-brand-500 cursor-pointer"
              />,
              t("Facility"),
              t("Equipment"),
              t("Component"),
              t("Service"),
              t("Quantity"),
              t("Operating Hours"),
              t("Status"),
            ]}
            empty={loading ? t("Loading components...") : t("No components in inventory.")}
          >
            {filteredComponents.map((c) => (
              <Tr key={c.id} className={selectedCompIds.has(c.id) ? "bg-brand-50/30" : undefined}>
                <Td className="w-10">
                  <input
                    type="checkbox"
                    aria-label={`Select component ${c.id}`}
                    checked={selectedCompIds.has(c.id)}
                    onChange={() => toggleCompSelection(c.id)}
                    className="size-4 rounded border-border text-brand-600 focus:ring-brand-500 cursor-pointer"
                  />
                </Td>
                <Td className="font-medium text-text">
                  {c.facility_name || facilities.find((f) => f.id === c.facility_id)?.name || c.facility_id}
                </Td>
                <Td>{c.equipment_type}</Td>
                <Td>{c.component_type}</Td>
                <Td>{c.service_type}</Td>
                <Td className="font-mono">{c.quantity}</Td>
                <Td className="font-mono">{c.operating_hours}</Td>
                <Td>{getComponentStatusBadge(c.status)}</Td>
              </Tr>
            ))}
          </RecordTable>
        </>
      )}

      {/* Repair Modal */}
      {repairModal.isOpen && (
        <Modal
          title={t("Record Leak Repair")}
          onClose={() => setRepairModal((prev) => ({ ...prev, isOpen: false, survey: null }))}
        >
          <div className="space-y-4 p-4">
            <p className="text-sm text-text-secondary">
              {t("Confirm repair details for survey #")}
              {repairModal.survey?.id} ({repairModal.survey?.survey_method}).
            </p>
            <Field label={t("Repair Date")}>
              <Input
                type="date"
                value={repairModal.repairDate}
                onChange={(e) =>
                  setRepairModal((prev) => ({ ...prev, repairDate: e.target.value }))
                }
              />
            </Field>
            <Field label={t("Post-Repair Screening (PPM)")}>
              <Input
                type="number"
                min="0"
                step="any"
                value={repairModal.postRepairPpm}
                onChange={(e) =>
                  setRepairModal((prev) => ({ ...prev, postRepairPpm: e.target.value }))
                }
              />
            </Field>
            <Field label={t("Repair Notes")}>
              <Input
                type="text"
                placeholder={t("e.g. Packing tightened, flange retorqued")}
                value={repairModal.notes}
                onChange={(e) =>
                  setRepairModal((prev) => ({ ...prev, notes: e.target.value }))
                }
              />
            </Field>
            <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
              <Button
                variant="secondary"
                onClick={() => setRepairModal((prev) => ({ ...prev, isOpen: false, survey: null }))}
              >
                {t("Cancel")}
              </Button>
              <Button variant="primary" onClick={handleSaveRepair}>
                {t("Save Repair")}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Record Survey Modal */}
      {surveyModal.isOpen && (
        <Modal
          title={t("Record Leak Detection Survey")}
          onClose={() => setSurveyModal((prev) => ({ ...prev, isOpen: false }))}
        >
          <div className="space-y-4 p-4">
            <Field label={t("Facility")}>
              <NativeSelect
                value={surveyModal.facility_id}
                onChange={(e) =>
                  setSurveyModal((prev) => ({ ...prev, facility_id: e.target.value }))
                }
              >
                <option value="">{t("Select facility...")}</option>
                {facilities.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Survey Method")}>
                <NativeSelect
                  value={surveyModal.survey_method}
                  onChange={(e) =>
                    setSurveyModal((prev) => ({ ...prev, survey_method: e.target.value }))
                  }
                >
                  <option value="Method 21">EPA Method 21</option>
                  <option value="OGI">Optical Gas Imaging (OGI)</option>
                  <option value="Acoustic">Acoustic Leak Detection</option>
                </NativeSelect>
              </Field>
              <Field label={t("Survey Date")}>
                <Input
                  type="date"
                  value={surveyModal.survey_date}
                  onChange={(e) =>
                    setSurveyModal((prev) => ({ ...prev, survey_date: e.target.value }))
                  }
                />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Screening Value (PPM)")}>
                <Input
                  type="number"
                  min="0"
                  value={surveyModal.screening_value_ppm}
                  onChange={(e) => {
                    const ppm = parseFloat(e.target.value) || 0;
                    setSurveyModal((prev) => ({
                      ...prev,
                      screening_value_ppm: e.target.value,
                      leak_status: ppm >= 500 ? "Leaking" : "Non-leaking",
                    }));
                  }}
                />
              </Field>
              <Field label={t("Leak Status")}>
                <NativeSelect
                  value={surveyModal.leak_status}
                  onChange={(e) =>
                    setSurveyModal((prev) => ({ ...prev, leak_status: e.target.value }))
                  }
                >
                  <option value="Non-leaking">{t("Non-leaking")}</option>
                  <option value="Leaking">{t("Leaking")}</option>
                  <option value="Repaired">{t("Repaired")}</option>
                </NativeSelect>
              </Field>
            </div>
            <Field label={t("Surveyor Name")}>
              <Input
                type="text"
                placeholder={t("Operator or Inspector name")}
                value={surveyModal.surveyor_name}
                onChange={(e) =>
                  setSurveyModal((prev) => ({ ...prev, surveyor_name: e.target.value }))
                }
              />
            </Field>
            <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
              <Button
                variant="secondary"
                onClick={() => setSurveyModal((prev) => ({ ...prev, isOpen: false }))}
              >
                {t("Cancel")}
              </Button>
              <Button variant="primary" onClick={handleSaveSurvey}>
                {t("Log Survey")}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Add Component Modal */}
      {compModal.isOpen && (
        <Modal
          title={t("Add Component to Inventory")}
          onClose={() => setCompModal((prev) => ({ ...prev, isOpen: false }))}
        >
          <div className="space-y-4 p-4">
            <Field label={t("Facility")}>
              <NativeSelect
                value={compModal.facility_id}
                onChange={(e) =>
                  setCompModal((prev) => ({ ...prev, facility_id: e.target.value }))
                }
              >
                <option value="">{t("Select facility...")}</option>
                {facilities.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Equipment Type")}>
                <NativeSelect
                  value={compModal.equipment_type}
                  onChange={(e) =>
                    setCompModal((prev) => ({ ...prev, equipment_type: e.target.value }))
                  }
                >
                  <option value="Valves">Valves</option>
                  <option value="Flanges">Flanges</option>
                  <option value="Pumps">Pumps</option>
                  <option value="Compressors">Compressors</option>
                  <option value="Relief Valves">Relief Valves</option>
                  <option value="Open-ended Lines">Open-ended Lines</option>
                </NativeSelect>
              </Field>
              <Field label={t("Service Type")}>
                <NativeSelect
                  value={compModal.service_type}
                  onChange={(e) =>
                    setCompModal((prev) => ({ ...prev, service_type: e.target.value }))
                  }
                >
                  <option value="Gas">Gas</option>
                  <option value="Light Liquid">Light Liquid</option>
                  <option value="Heavy Liquid">Heavy Liquid</option>
                  <option value="Water / Oil">Water / Oil</option>
                </NativeSelect>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Quantity")}>
                <Input
                  type="number"
                  min="1"
                  value={compModal.quantity}
                  onChange={(e) =>
                    setCompModal((prev) => ({ ...prev, quantity: e.target.value }))
                  }
                />
              </Field>
              <Field label={t("Operating Hours / Year")}>
                <Input
                  type="number"
                  min="1"
                  max="8760"
                  value={compModal.operating_hours}
                  onChange={(e) =>
                    setCompModal((prev) => ({ ...prev, operating_hours: e.target.value }))
                  }
                />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Status")}>
                <NativeSelect
                  value={compModal.status}
                  onChange={(e) =>
                    setCompModal((prev) => ({ ...prev, status: e.target.value }))
                  }
                >
                  <option value="Active">{t("Active")}</option>
                  <option value="Broken">{t("Broken")}</option>
                  <option value="Leaking">{t("Leaking")}</option>
                  <option value="Inactive">{t("Inactive")}</option>
                </NativeSelect>
              </Field>
              <Field label={t("Description / Tag")}>
                <Input
                  type="text"
                  placeholder={t("e.g. Header isolation valves unit 4")}
                  value={compModal.description}
                  onChange={(e) =>
                    setCompModal((prev) => ({ ...prev, description: e.target.value }))
                  }
                />
              </Field>
            </div>
            <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
              <Button
                variant="secondary"
                onClick={() => setCompModal((prev) => ({ ...prev, isOpen: false }))}
              >
                {t("Cancel")}
              </Button>
              <Button variant="primary" onClick={handleSaveComponent}>
                {t("Save Component")}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Bulk Update Components Modal */}
      {bulkCompModal.isOpen && (
        <Modal
          title={t("Bulk Update Components ({{count}} selected)", { count: selectedCompIds.size })}
          onClose={() => setBulkCompModal((prev) => ({ ...prev, isOpen: false }))}
        >
          <div className="space-y-4 p-4">
            <p className="text-sm text-text-secondary">
              {t("Update attributes for {{count}} selected components. Blank or unselected fields will remain unchanged.", {
                count: selectedCompIds.size,
              })}
            </p>
            <Field label={t("Status")}>
              <NativeSelect
                value={bulkCompModal.status}
                onChange={(e) => setBulkCompModal((prev) => ({ ...prev, status: e.target.value }))}
              >
                <option value="">{t("-- Keep existing status --")}</option>
                <option value="Active">{t("Active")}</option>
                <option value="Broken">{t("Broken")}</option>
                <option value="Leaking">{t("Leaking")}</option>
                <option value="Inactive">{t("Inactive")}</option>
              </NativeSelect>
            </Field>
            <Field label={t("Service Type")}>
              <NativeSelect
                value={bulkCompModal.service_type}
                onChange={(e) => setBulkCompModal((prev) => ({ ...prev, service_type: e.target.value }))}
              >
                <option value="">{t("-- Keep existing service type --")}</option>
                <option value="Gas">Gas</option>
                <option value="Light Liquid">Light Liquid</option>
                <option value="Heavy Liquid">Heavy Liquid</option>
                <option value="Water / Oil">Water / Oil</option>
              </NativeSelect>
            </Field>
            <Field label={t("Operating Hours / Year (Optional)")}>
              <Input
                type="number"
                min="0"
                max="8760"
                placeholder={t("Leave blank to keep unchanged")}
                value={bulkCompModal.operating_hours}
                onChange={(e) => setBulkCompModal((prev) => ({ ...prev, operating_hours: e.target.value }))}
              />
            </Field>
            <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
              <Button
                variant="secondary"
                onClick={() => setBulkCompModal((prev) => ({ ...prev, isOpen: false }))}
              >
                {t("Cancel")}
              </Button>
              <Button variant="primary" onClick={handleBulkUpdateComponents}>
                {t("Apply Bulk Update")}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Bulk Update Surveys Modal */}
      {bulkSurveyModal.isOpen && (
        <Modal
          title={t("Bulk Update Surveys ({{count}} selected)", { count: selectedSurveyIds.size })}
          onClose={() => setBulkSurveyModal((prev) => ({ ...prev, isOpen: false }))}
        >
          <div className="space-y-4 p-4">
            <p className="text-sm text-text-secondary">
              {t("Update leak status and repair details for {{count}} selected surveys.", {
                count: selectedSurveyIds.size,
              })}
            </p>
            <Field label={t("Leak Status")}>
              <NativeSelect
                value={bulkSurveyModal.leak_status}
                onChange={(e) => setBulkSurveyModal((prev) => ({ ...prev, leak_status: e.target.value }))}
              >
                <option value="Repaired">{t("Repaired")}</option>
                <option value="Non-leaking">{t("Non-leaking")}</option>
                <option value="Leaking">{t("Leaking")}</option>
              </NativeSelect>
            </Field>
            {bulkSurveyModal.leak_status === "Repaired" && (
              <>
                <Field label={t("Repair Date")}>
                  <Input
                    type="date"
                    value={bulkSurveyModal.repairDate}
                    onChange={(e) =>
                      setBulkSurveyModal((prev) => ({ ...prev, repairDate: e.target.value }))
                    }
                  />
                </Field>
                <Field label={t("Post-Repair Screening (PPM)")}>
                  <Input
                    type="number"
                    min="0"
                    step="any"
                    value={bulkSurveyModal.postRepairPpm}
                    onChange={(e) =>
                      setBulkSurveyModal((prev) => ({ ...prev, postRepairPpm: e.target.value }))
                    }
                  />
                </Field>
              </>
            )}
            <Field label={t("Notes / Repair Details (Optional)")}>
              <Input
                type="text"
                placeholder={t("e.g. Bulk repaired during scheduled maintenance")}
                value={bulkSurveyModal.notes}
                onChange={(e) =>
                  setBulkSurveyModal((prev) => ({ ...prev, notes: e.target.value }))
                }
              />
            </Field>
            <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
              <Button
                variant="secondary"
                onClick={() => setBulkSurveyModal((prev) => ({ ...prev, isOpen: false }))}
              >
                {t("Cancel")}
              </Button>
              <Button variant="primary" onClick={handleBulkUpdateSurveys}>
                {t("Apply Bulk Update")}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </TabCard>
  );
};

export default LdarTab;
