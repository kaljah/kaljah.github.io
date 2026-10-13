import { ChevronDown, Download, FilePlus, FileSpreadsheet, FileText, FileCode, Funnel, Pencil, Plus, RotateCcw, Search, ShieldCheck, Sparkles, SlidersHorizontal, Table } from "lucide-react";
import { NativeSelect } from "../ui/NativeSelect";
import { Badge, Button, Card, CardHeader, DataTable, Dialog, Field, Input, Menu, MenuContent, MenuItem, MenuTrigger, Page, PageHeader, SegmentedControl, StatusPill, Textarea, cn, type BadgeTone } from "../ui";
import { controlClass } from "../components/import-wizard/mapping";
import React, { useState, useEffect, useMemo, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import MultiSelectDropdown from "../components/MultiSelectDropdown";
import EditEmissionModal from "../components/modals/EditEmissionModal";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import { getActiveGwpFactors } from "../constants";
import { apiError } from "../utils/apiError";
import { useGwpStandard } from "../hooks/useGwpStandard";
import type { ColumnDef } from "@tanstack/react-table";
import { t as tr } from "../i18n";

interface EmissionRecord {
  id: number | string;
  year: number;
  month: number;
  scope: number | string;
  division?: string;
  field?: string;
  facility_name?: string;
  facility_id?: number | string;
  group_name?: string;
  equipment_id?: string;
  process_type?: string;
  fuel?: string;
  factor_type?: string;
  amount?: number | string | null;
  unit?: string;
  co2e_total?: number | string | null;
  status?: string;
  [key: string]: any;
}

interface Facility {
  id: number | string;
  name: string;
  field?: string;
  division?: string;
  [key: string]: any;
}

// BUG-013: GWP option labels are generated from constants.js so they always
// show the values the report generator will actually apply. "20yr" resolves
// to AR5 20-year in resolveGwpFactors (ModernReportGenerator).
const gwpOptionLabel = (standard: string, horizon: string) => {
  const f = getActiveGwpFactors(standard, horizon);
  return `IPCC ${standard} (${horizon}-yr: CH4=${f.CH4}, N2O=${f.N2O})`;
};

const NA = (v: any) => v || "N/A";
const fmt = (num: any) =>
  num === null || num === undefined
    ? "0.00"
    : parseFloat(num).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 3 });

const RECORD_COLUMNS: ColumnDef<EmissionRecord, any>[] = [
  { accessorKey: "id", header: tr("ID"), cell: (c) => <span className="text-xs text-text-secondary">{c.getValue()}</span> },
  { id: "date", header: tr("Date"), accessorFn: (r) => r.year * 100 + r.month, cell: (c) => `${c.row.original.month}/${c.row.original.year}` },
  { accessorKey: "scope", header: tr("Scope"), cell: (c) => {
    const tones: Record<string | number, BadgeTone> = { 1: "brand", 2: "info" };
    return <Badge tone={tones[c.getValue()] || "neutral"}>{tr("Scope")}{" "}{c.getValue()}</Badge>;
  } },
  { accessorKey: "division", header: tr("Division"), cell: (c) => NA(c.getValue()) },
  { accessorKey: "field", header: tr("Field"), cell: (c) => NA(c.getValue()) },
  { accessorKey: "facility_name", header: tr("Facility"), cell: (c) => NA(c.getValue()) },
  { accessorKey: "group_name", header: tr("Group"), cell: (c) => NA(c.getValue()) },
  { accessorKey: "equipment_id", header: tr("Equipment"), cell: (c) => NA(c.getValue()) },
  { accessorKey: "process_type", header: tr("Category/Process"), cell: (c) => <span className="font-medium">{c.getValue()}</span> },
  { accessorKey: "fuel", header: tr("Fuel/Source"), cell: (c) => NA(c.getValue()) },
  { accessorKey: "factor_type", header: tr("Factor Type"), cell: (c) => <span className="text-sm">{NA(c.getValue())}</span> },
  {
    accessorKey: "amount",
    header: tr("Qty"),
    meta: { numeric: true },
    cell: (c) =>
      c.getValue() ? (
        <>
          {fmt(c.getValue())} <span className="text-xs text-text-secondary">{c.row.original.unit}</span>
        </>
      ) : (
        "-"
      ),
  },
  {
    accessorKey: "co2e_total",
    header: tr("Total"),
    meta: { numeric: true, unit: "tCO₂e" },
    // BUG-UI-06 FIX: show an em dash for null instead of a misleading 0.00
    cell: (c) => <span className="font-bold text-primary">{c.getValue() != null ? fmt(c.getValue()) : "—"}</span>,
  },
  { accessorKey: "status", header: tr("Status"), cell: (c) => <StatusPill status={c.getValue() || "Verified"} /> },
];

const Reports: React.FC = () => {
  const [searchParams] = useSearchParams();
  // Deep link from a chart (?year=2025&facility=3&scope=1&process=flaring&month=4): read once on arrival.
  const [deepLink] = useState(() => ({
    year: searchParams.get("year"),
    month: searchParams.get("month"),
    facility: searchParams.get("facility"),
    scope: searchParams.get("scope"),
    process: searchParams.get("process"),
    search: searchParams.get("search") || searchParams.get("q") || searchParams.get("equipment"),
  }));
  const { user } = useAuth();
  const toast = useToast();
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [baseYear, setBaseYear] = useState<number | string | null>(null); // configured base year (the option was labelled 2020)
  const [editingEmission, setEditingEmission] = useState<EmissionRecord | null>(null);

  const columns = useMemo<ColumnDef<EmissionRecord, any>[]>(
    () => [
      ...RECORD_COLUMNS,
      {
        id: "actions",
        header: tr("Actions"),
        cell: (c) => (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setEditingEmission(c.row.original)}
            className="gap-1 px-2.5 py-1 text-xs"
          >
            <Pencil className="size-3" aria-hidden="true" />
            {tr("Edit")}
          </Button>
        ),
      },
    ],
    [],
  );

  const [availableFilters, setAvailableFilters] = useState<{
    years: (string | number)[];
    regions: any[];
    segments?: any[];
  }>({
    years: [],
    regions: [],
  });
  const [emissions, setEmissions] = useState<EmissionRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isGeneratingMasterPdf, setIsGeneratingMasterPdf] = useState<boolean>(false);

  // Filters
  const [year, setYear] = useState<string>(deepLink.year || "all");
  const [month, setMonth] = useState<string>(deepLink.month || "all");
  const [division, setDivision] = useState<string>("all");
  const [field, setField] = useState<string>("all");
  const [methodFilter, setMethodFilter] = useState<string>("all");
  const [regionId, setRegionId] = useState<string>(deepLink.facility || "all");
  const [processType, setProcessType] = useState<string>(deepLink.process || "all");
  const [searchTerm, setSearchTerm] = useState<string>(deepLink.search || "");
  // BUG-021: debounce the search box so we issue one request per pause, not per keystroke
  const [debouncedSearch, setDebouncedSearch] = useState<string>(deepLink.search || "");
  const [groupBy, setGroupBy] = useState<string>("none"); // none, facility, process, month

  // Pagination
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalRecords, setTotalRecords] = useState<number>(0);

  const [scope, setScope] = useState<string>(deepLink.scope || "all");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState<boolean>(false);

  const resetFilters = () => {
    setYear("all");
    setReportYear("all");
    setMonth("all");
    setRegionId("all");
    setReportSelectedRegions([]);
    setProcessType("all");
    setScope("all");
    setDivision("all");
    setField("all");
    setMethodFilter("all");
    setGroupBy("none");
    setComparisonYear("none");
    setSearchTerm("");
    setReportGwpStandard("AR6");
    setPage(1);
    toast.info(tr("Filters reset to defaults."));
  };

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [facRes, filterRes, baseRes] = await Promise.all([
          api.get("/facilities"),
          api.get("/filters/available"),
          api.get("/dashboard/base-year").catch(() => ({ data: null })),
        ]);
        setBaseYear(baseRes.data?.year ?? null);
        const facilitiesData: Facility[] = Array.isArray(facRes.data)
          ? facRes.data
          : facRes.data?.data || [];
        setFacilities(facilitiesData);
        setAvailableFilters({
          years: Array.isArray(filterRes.data?.years)
            ? filterRes.data.years
            : [],
          regions: Array.isArray(filterRes.data?.regions)
            ? filterRes.data.regions
            : [],
          segments: Array.isArray(filterRes.data?.segments)
            ? filterRes.data.segments
            : [],
        });

        // Sync year picker to the most recent year that has actual data
        if (deepLink.year) {
          // a chart linked to a specific year: keep it
        } else if (filterRes.data.years?.length > 0) {
          const mostRecentYear = filterRes.data.years[0].toString();
          setYear(mostRecentYear);
          setReportYear(mostRecentYear);
        } else {
          setYear("all");
          setReportYear("all");
        }

        const opDefaults = getUserOperationalDefaults(user, facilitiesData);
        if (opDefaults.isRestricted || facilitiesData.length === 1) {
          if (opDefaults.defaultFacilityId && !deepLink.facility) setRegionId(opDefaults.defaultFacilityId);
          if (opDefaults.defaultDivision) setDivision(opDefaults.defaultDivision);
        }
      } catch (err) {
        console.error("Error fetching initial data", err);
        toast.error(tr("Failed to load filter data"));
      }
    };
    loadInitialData();
  }, [user]);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchTerm), 300);
    return () => clearTimeout(t);
  }, [searchTerm]);

  // Reset page to 1 whenever filters change (but not on page itself changing)
  const prevFiltersRef = useRef({
    year,
    month,
    regionId,
    processType,
    scope,
    division,
    field,
    methodFilter,
    search: debouncedSearch,
  });
  useEffect(() => {
    const prev = prevFiltersRef.current;
    const filterChanged =
      prev.year !== year ||
      prev.month !== month ||
      prev.regionId !== regionId ||
      prev.processType !== processType ||
      prev.scope !== scope ||
      prev.division !== division ||
      prev.field !== field ||
      prev.methodFilter !== methodFilter ||
      prev.search !== debouncedSearch;
    prevFiltersRef.current = {
      year,
      month,
      regionId,
      processType,
      scope,
      division,
      field,
      methodFilter,
      search: debouncedSearch,
    };
    if (filterChanged && page !== 1) {
      setPage(1);
      return; // page change will trigger the next fetchEmissions
    }
    fetchEmissions();
  }, [
    year,
    month,
    regionId,
    processType,
    scope,
    division,
    field,
    methodFilter,
    page,
    debouncedSearch,
  ]);

  // BUG-006: one source of truth for the on-screen filters, shared by the
  // table query and both exports so the exported file matches the table.
  const buildFilterParams = (): Record<string, any> => {
    const cleanYear =
      year && year !== "all" && year !== "undefined" && year !== "null"
        ? year
        : undefined;
    return {
      scope,
      ...(cleanYear && { year: cleanYear }),
      ...(month !== "all" && { month }),
      ...(regionId !== "all" && { facility_id: regionId }),
      ...(division !== "all" && { division: division }),
      ...(field !== "all" && { field: field }),
      ...(methodFilter !== "all" && { method: methodFilter }),
      ...(processType !== "all" && { process_type: processType }),
      ...(debouncedSearch && { search: debouncedSearch }),
    };
  };

  const fetchEmissions = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        per_page: 50,
        ...buildFilterParams(),
      };

      const res = await api.get("/emissions", { params });
      // BUG-021: if the current page is past the last page (e.g. the result
      // set shrank), jump back to the last valid page instead of showing 0 rows.
      const serverPages = Number(res.data.pages);
      if (Number.isFinite(serverPages) && page > Math.max(1, serverPages)) {
        setPage(Math.max(1, serverPages));
        return; // page change triggers a refetch
      }
      setEmissions(res.data.emissions || res.data.data || res.data || []);
      setTotalRecords(res.data.total || res.data.length || 0);
      setTotalPages(res.data.pages || 1);
    } catch (err) {
      console.error("Error fetching emissions", err);
      toast.error(apiError(err, tr("Failed to load emissions data")));
      setEmissions([]);
      setTotalRecords(0);
    } finally {
      setLoading(false);
    }
  };

  const handleExcelExport = async () => {
    try {
      const params = {
        ...buildFilterParams(),
        format: "excel",
      };

      const res = await api.get("/emissions/export", {
        params,
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(
        new Blob([res.data], {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = `emissions_${year}_${month}.xlsx`;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        link.remove();
        window.URL.revokeObjectURL(url);
      }, 1000);
    } catch (err) {
      console.error("Export error", err);
      toast.error(tr("Export failed. Please try again."));
    }
  };

  const handlePDFExport = async () => {
    try {
      const params = new URLSearchParams(buildFilterParams());

      const response = await api.get(`/reports/export?${params.toString()}`, {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(
        new Blob([response.data], { type: "application/pdf" }),
      );
      const link = document.createElement("a");
      link.href = url;
      const yearStr = year && year !== "all" ? year : "all";
      const monthStr = month && month !== "all" ? month : "all";
      link.download = `emissions_${yearStr}_${monthStr}.pdf`;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        link.remove();
        window.URL.revokeObjectURL(url);
      }, 1000);
    } catch (error) {
      console.error("PDF export failed:", error);
      toast.error(tr("Failed to export PDF. Please try again."));
    }
  };

  const handleOGMPExport = async () => {
    try {
      toast.info(tr("Generating OGMP 2.0 Excel Workbook..."));
      // the table's filters first (the export used the "Create report" year and every facility)
      const yr =
        year !== "all" ? year : reportYear !== "all" ? reportYear
          : String(availableFilters.years[0] || new Date().getFullYear()); // latest year with data (was always 2024)
      const response = await api.get("/reports/ogmp-export", {
        params: { year: yr, ...(regionId !== "all" && { facility_id: regionId }) },
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(
        new Blob([response.data], {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = `OGMP_2.0_Methane_Report_${yr}.xlsx`;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        link.remove();
        window.URL.revokeObjectURL(url);
      }, 1000);
      toast.success(tr("OGMP 2.0 Excel report for {{year}} downloaded successfully!", { year: yr }));
    } catch (error) {
      console.error("OGMP Excel export failed:", error);
      toast.error(tr("Failed to export OGMP 2.0 Excel report."));
    }
  };

  const handleCBAMExport = async (format: "excel" | "xml") => {
    try {
      const isXml = format === "xml";
      toast.info(isXml ? tr("Generating EU CBAM XML Declaration...") : tr("Generating EU CBAM Excel Communication Template..."));
      const yr =
        year !== "all" ? year : reportYear !== "all" ? reportYear
          : String(availableFilters.years[0] || new Date().getFullYear());
      const response = await api.get("/reports/cbam-export", {
        params: { year: yr, format, ...(regionId !== "all" && { facility_id: regionId }) },
        responseType: "blob",
      });
      const mime = isXml ? "application/xml" : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
      const ext = isXml ? "xml" : "xlsx";
      const prefix = isXml ? "CBAM_Transitional_Declaration" : "EU_CBAM_Communication_Template";
      const url = window.URL.createObjectURL(new Blob([response.data], { type: mime }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `${prefix}_${yr}.${ext}`;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        link.remove();
        window.URL.revokeObjectURL(url);
      }, 1000);
      toast.success(isXml ? tr("EU CBAM XML Declaration for {{year}} downloaded successfully!", { year: yr }) : tr("EU CBAM Template for {{year}} downloaded successfully!", { year: yr }));
    } catch (error) {
      console.error("CBAM export failed:", error);
      toast.error(tr("Failed to export EU CBAM document."));
    }
  };

  const handleNationalInventoryExport = async () => {
    try {
      toast.info(tr("Generating Décret 21-330 / ISO 14064-1 Official Excel Template..."));
      const yr =
        year !== "all" ? year : reportYear !== "all" ? reportYear
          : String(availableFilters.years[0] || new Date().getFullYear());
      const response = await api.get("/reports/national-inventory-export", {
        params: { year: yr, ...(regionId !== "all" && { facility_id: regionId }) },
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(
        new Blob([response.data], {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = `Inventaire_National_Decret_21-330_ISO_14064-1_${yr}.xlsx`;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        link.remove();
        window.URL.revokeObjectURL(url);
      }, 1000);
      toast.success(tr("Décret 21-330 Excel report for {{year}} downloaded successfully!", { year: yr }));
    } catch (error) {
      console.error("National inventory export failed:", error);
      toast.error(tr("Failed to export Décret 21-330 inventory report."));
    }
  };

  const handleMasterReportDownload = async (targetFacilityId: string | number | null = null) => {
    if (isGeneratingMasterPdf) return;
    try {
      setIsGeneratingMasterPdf(true);
      setLoading(true);
      // BUG-002: only accept a real id; never a click event or other object.
      const explicitId =
        typeof targetFacilityId === "string" || typeof targetFacilityId === "number"
          ? targetFacilityId
          : null;
      const selectedId = explicitId || (reportSelectedRegions.length === 1 ? reportSelectedRegions[0] : (regionId !== "all" ? regionId : null));
      const isElMerk = selectedId === "170" || selectedId === 170;
      const reportTitle = isElMerk ? tr("El Merk (Block 208) Master Report") : tr("Groupement Berkine Master Report");
      const downloadFilename = isElMerk ? "El_Merk_2025_Annual_GHG_Report.pdf" : "Groupement_Berkine_2025_Annual_GHG_Report.pdf";

      toast.info(tr("Downloading {{title}} (PDF)...", { title: reportTitle }));
      const endpoint = selectedId ? `/reports/master-annual-report?facility_id=${encodeURIComponent(selectedId)}` : "/reports/master-annual-report";
      const response = await api.get(endpoint, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = downloadFilename;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        link.remove();
        window.URL.revokeObjectURL(url);
      }, 1000);
      toast.success(tr("{{title}} downloaded successfully!", { title: reportTitle }));
    } catch (error) {
      console.error("Master report download failed:", error);
      toast.error(tr("Failed to download Master Report."));
    } finally {
      setIsGeneratingMasterPdf(false);
      setLoading(false);
    }
  };

  const getGroupedData = (): Record<string, EmissionRecord[]> => {
    if (groupBy === "none") return { all: emissions };
    const grouped: Record<string, EmissionRecord[]> = {};
    emissions.forEach((em) => {
      let key = "Unknown";
      if (groupBy === "facility") key = em.region || em.facility_name || "Unknown";
      else if (groupBy === "process") key = em.process_type || "Unknown";
      else if (groupBy === "month")
        key = `${em.year}-${String(em.month).padStart(2, "0")}`;
      else if (groupBy === "scope") key = `Scope ${em.scope}`;

      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(em);
    });
    return grouped;
  };

  const formatNumber = (num: any) => {
    if (num === null || num === undefined) return "0.00";
    return parseFloat(num).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 3,
    });
  };

  // Report Generation State
  const [reportYear, setReportYear] = useState<string>(
    new Date().getFullYear().toString(),
  );
  const [comparisonYear, setComparisonYear] = useState<string>("none"); // [NEW] Comparison Year State
  // the report's GWP set starts at the organisation's active standard (it always started at AR5)
  const { standard: activeGwpStandard } = useGwpStandard();
  const [reportGwpStandard, setReportGwpStandard] = useState<string>(activeGwpStandard || "AR5");
  const gwpTouched = useRef<boolean>(false);
  useEffect(() => {
    if (activeGwpStandard && !gwpTouched.current) setReportGwpStandard(activeGwpStandard);
  }, [activeGwpStandard]);
  const [reportSelectedRegions, setReportSelectedRegions] = useState<any[]>([]); // Multiselect

  const hasActiveFilters = Boolean(
    scope !== "all" ||
    year !== "all" ||
    month !== "all" ||
    regionId !== "all" ||
    processType !== "all" ||
    division !== "all" ||
    field !== "all" ||
    methodFilter !== "all" ||
    groupBy !== "none" ||
    comparisonYear !== "none" ||
    searchTerm.trim() !== "" ||
    reportGwpStandard !== "AR6"
  );

  const activeSecondaryCount = [
    processType !== "all",
    division !== "all",
    field !== "all",
    methodFilter !== "all",
    groupBy !== "none",
    comparisonYear !== "none",
    reportGwpStandard !== "AR6",
  ].filter(Boolean).length;

  // Derived options
  const regionOptions = facilities.map((f) => ({
    value: f.id.toString(),
    label: f.name,
    subLabel: f.field,
  }));

  const [showConfigModal, setShowConfigModal] = useState<boolean>(false);
  const [reportFormat, setReportFormat] = useState<string>("iso");

  const isTableFilteredDifferently = Boolean(
    (year !== "all" && year !== reportYear) ||
    (regionId !== "all" && (reportSelectedRegions.length !== 1 || String(reportSelectedRegions[0]) !== String(regionId))) ||
    (regionId === "all" && reportSelectedRegions.length > 0)
  );

  const tableFacilityName = facilities.find((f) => f.id.toString() === regionId.toString())?.name;

  const tableFilterSummary = [
    regionId !== "all" ? tableFacilityName || regionId : null,
    scope !== "all" ? `Scope ${scope}` : null,
    year !== "all" ? year : null,
  ].filter(Boolean).join(" • ");

  const handleSyncFromTable = () => {
    if (year !== "all") {
      setReportYear(year);
    }
    if (regionId !== "all") {
      setReportSelectedRegions([regionId]);
    } else {
      setReportSelectedRegions([]);
    }
    toast.success(tr("Report boundary synchronized with active table filters!"));
  };
  // A master report exists only for El Merk (facility 170) and, for organisation-wide accounts, the
  // consolidated entity (server MASTER_REPORTS); it used to be offered (and fail) for every facility.
  const masterAvailableFor = (ids: any[]): boolean => {
    const sel = ids.map(String).filter((v) => v && v !== "all");
    if (sel.length === 1) return sel[0] === "170";
    return (sel.length === 0 || sel.length === facilities.length) && user?.role === "admin";
  };
  const dialogMasterAvailable = masterAvailableFor(reportSelectedRegions);
  const effectiveReportFormat = reportFormat === "master" && !dialogMasterAvailable ? "iso" : reportFormat;
  const [exclusionCriteria, setExclusionCriteria] = useState<string>("Sources contributing less than 1% of the total footprint are excluded.");
  const [verificationStatus, setVerificationStatus] = useState<string>("Not externally verified");

  const openConfigModal = () => {
    setShowConfigModal(true);
  };

  const handleGenerateModalReport = async () => {
    setShowConfigModal(false);
    if (effectiveReportFormat === "master") {
      await handleMasterReportDownload();
      return;
    }
    await handleISOReportWrapper();
  };

  const handleISOReportWrapper = async () => {
    setLoading(true);
    toast.info(tr("Generating ISO 14064-1 Report..."));
    try {
      const { generateModernPDF } = await import("../utils/ModernReportGenerator");

      const activeYear = year !== "all" ? year : reportYear;
      const activeFacility = regionId !== "all" ? regionId : (reportSelectedRegions.length > 0 ? reportSelectedRegions : "all");

      const filters = {
        year: activeYear,
        comparisonYear: comparisonYear !== "none" ? comparisonYear : undefined,
        scope: scope,
        regionId: activeFacility,
        processType: processType,
        exclusionCriteria: exclusionCriteria,
        verificationStatus: verificationStatus,
        gwpStandard: reportGwpStandard,
        personResponsible: user || { username: "Logged In User" },
      };

      await generateModernPDF(api, filters as any);
      toast.success(tr("Report generated successfully!"));
    } catch (err) {
      console.error("Report Generation Error", err);
      toast.error(tr("Failed to generate report."));
    } finally {
      setLoading(false);
    }
  };

  // Chips helper
  const removeRegion = (val: any) => {
    setReportSelectedRegions((prev) => prev.filter((v) => v !== val));
  };

  const selectBase = (label: string, value: any, onChange: (e: any) => void, children: React.ReactNode, extra: Record<string, any> = {}) => (
    <Field label={label} className={extra.className}>
      <NativeSelect className={controlClass} value={value} onChange={onChange}>
        {children}
      </NativeSelect>
    </Field>
  );
  const MONTHS = [...Array(12)].map((_, i) => ({ value: i + 1, label: new Date(0, i).toLocaleString("default", { month: "long" }) }));
  const uniq = (key: string) => [...new Set(facilities.map((f) => f[key]))].filter(Boolean);
  const gwpOptions = (suffix = "") => (
    <>
      <option value="AR5">{`${gwpOptionLabel("AR5", "100")}${suffix}`}</option>
      <option value="AR6">{gwpOptionLabel("AR6", "100")}</option>
      <option value="AR4">{gwpOptionLabel("AR4", "100")}</option>
      <option value="20yr">{gwpOptionLabel("AR5", "20")}</option>
    </>
  );
  const onGwp = (e: any) => {
    gwpTouched.current = true;
    setReportGwpStandard(e.target.value);
  };
  const FORMATS = [
    ...(dialogMasterAvailable
      ? [{ value: "master", label: tr("🏆 2025 Master Analytical Report (Vertical A4, 15 Charts, 18 Tables)") }]
      : []),
    { value: "iso", label: tr("📋 ISO 14064-1 Report") },
  ];
  const years = availableFilters.years;

  return (
    <Page className="reports-page max-w-[1600px]">
      <PageHeader
        title={tr("Reports")}
        description={
          <>
            {tr("Emission database and exports. Complete history of all recorded emissions and compliance data.")}{" "}
            <span className="whitespace-nowrap font-semibold text-text">
              {tr("Total records:")}{" "}{totalRecords}{" "}{tr("| Showing:")}{" "}{emissions.length}
            </span>
          </>
        }
        actions={
          <>
            <Button variant="secondary" onClick={resetFilters}>
              <RotateCcw className="size-4" aria-hidden="true" />
              {tr("Reset filters")}
            </Button>
            <Menu>
              <MenuTrigger asChild>
                <Button>
                  <Download className="size-4" aria-hidden="true" />
                  {tr("Export")}
                  <ChevronDown className="size-4" aria-hidden="true" />
                </Button>
              </MenuTrigger>
              <MenuContent>
                <MenuItem icon={FileSpreadsheet} onSelect={handleNationalInventoryExport}>
                  {tr("Décret 21-330 / ISO 14064-1 (Excel)")}
                </MenuItem>
                <MenuItem icon={FileSpreadsheet} onSelect={handleOGMPExport}>
                  {tr("OGMP 2.0 (Excel)")}
                </MenuItem>
                <MenuItem icon={FileSpreadsheet} onSelect={() => handleCBAMExport("excel")}>
                  {tr("EU CBAM Template (Excel)")}
                </MenuItem>
                <MenuItem icon={FileCode} onSelect={() => handleCBAMExport("xml")}>
                  {tr("EU CBAM Declaration (XML)")}
                </MenuItem>
                <MenuItem icon={FileSpreadsheet} onSelect={handleExcelExport}>
                  {tr("Excel export")}
                </MenuItem>
                <MenuItem icon={FileText} onSelect={handlePDFExport}>
                  {tr("PDF report")}
                </MenuItem>
                {masterAvailableFor(regionId === "all" ? [] : [regionId]) && (
                  <MenuItem icon={FileText} onSelect={() => handleMasterReportDownload()}>
                    {tr("2025 Master report (PDF)")}
                  </MenuItem>
                )}
              </MenuContent>
            </Menu>
          </>
        }
      />

      {/* 1-Click Regulatory Compliance Presets Hub */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* ISO 14064-1 Card */}
        <Card className="flex flex-col justify-between border-t-2 border-t-brand-500 p-5 shadow-xs transition-shadow hover:shadow-md">
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="flex size-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <FileText className="size-5" aria-hidden="true" />
              </span>
              <Badge tone="brand">{tr("ISO 14064-1")}</Badge>
            </div>
            <div>
              <h3 className="m-0 text-base font-bold text-text">{tr("Corporate Inventory")}</h3>
              <p className="m-0 mt-1 text-xs text-text-secondary leading-relaxed">
                {tr("Comprehensive inventory across Scope 1, 2, and 3 compliant with ISO verification requirements.")}
              </p>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-border flex flex-col gap-2">
            <Button size="sm" variant="secondary" className="w-full justify-center gap-1.5" onClick={handleNationalInventoryExport}>
              <Download className="size-3.5" aria-hidden="true" />
              {tr("Export Décret 21-330 Excel")}
            </Button>
            <Button size="sm" variant="ghost" className="w-full justify-center gap-1.5" onClick={openConfigModal}>
              <Plus className="size-3.5" aria-hidden="true" />
              {tr("Configure ISO Report")}
            </Button>
          </div>
        </Card>

        {/* OGMP 2.0 Card */}
        <Card className="flex flex-col justify-between border-t-2 border-t-blue-500 p-5 shadow-xs transition-shadow hover:shadow-md">
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="flex size-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                <FileSpreadsheet className="size-5" aria-hidden="true" />
              </span>
              <Badge tone="info">{tr("UNEP / IMEO")}</Badge>
            </div>
            <div>
              <h3 className="m-0 text-base font-bold text-text">{tr("OGMP 2.0 Workbook")}</h3>
              <p className="m-0 mt-1 text-xs text-text-secondary leading-relaxed">
                {tr("Methane emissions workbook formatted for Gold Standard compliance and level 4/5 reporting.")}
              </p>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-border">
            <Button size="sm" variant="secondary" className="w-full justify-center gap-1.5" onClick={handleOGMPExport}>
              <Download className="size-3.5" aria-hidden="true" />
              {tr("Export OGMP Excel")}
            </Button>
          </div>
        </Card>

        {/* Executive Master Brief Card */}
        <Card className="flex flex-col justify-between border-t-2 border-t-amber-500 p-5 shadow-xs transition-shadow hover:shadow-md">
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="flex size-9 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
                <Sparkles className="size-5" aria-hidden="true" />
              </span>
              <Badge tone="warning">{tr("Executive A4")}</Badge>
            </div>
            <div>
              <h3 className="m-0 text-base font-bold text-text">{tr("Executive Master Brief")}</h3>
              <p className="m-0 mt-1 text-xs text-text-secondary leading-relaxed">
                {tr("Full synthesis document with 15 analytical charts and 18 operational compliance tables.")}
              </p>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-border">
            <Button
              size="sm"
              variant="secondary"
              className="w-full justify-center gap-1.5"
              disabled={isGeneratingMasterPdf}
              onClick={() => handleMasterReportDownload()}
            >
              {isGeneratingMasterPdf ? (
                <>
                  <span className="inline-block size-3.5 animate-spin rounded-full border-2 border-solid border-current border-r-transparent" />
                  {tr("Generating Master PDF, please wait...")}
                </>
              ) : (
                <>
                  <FileText className="size-3.5" aria-hidden="true" />
                  {tr("Download Master PDF")}
                </>
              )}
            </Button>
          </div>
        </Card>

        {/* Raw Activity Ledger Card */}
        <Card className="flex flex-col justify-between border-t-2 border-t-emerald-500 p-5 shadow-xs transition-shadow hover:shadow-md">
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between">
              <span className="flex size-9 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                <Table className="size-5" aria-hidden="true" />
              </span>
              <Badge tone="success">{tr("Full Ledger")}</Badge>
            </div>
            <div>
              <h3 className="m-0 text-base font-bold text-text">{tr("Activity Data Ledger")}</h3>
              <p className="m-0 mt-1 text-xs text-text-secondary leading-relaxed">
                {tr("Complete granular ledger export for third-party auditing, verification, and data science teams.")}
              </p>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-border">
            <Button size="sm" variant="secondary" className="w-full justify-center gap-1.5" onClick={handleExcelExport}>
              <Download className="size-3.5" aria-hidden="true" />
              {tr("Export Full Ledger")}
            </Button>
          </div>
        </Card>
      </div>

      {/* Separate Card 1: Report Generation Workbench */}
      <Card className="flex flex-col gap-4 p-5 shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600 shadow-xs">
              <SlidersHorizontal className="size-5 text-brand-500" aria-hidden="true" />
            </span>
            <div>
              <h2 className="m-0 text-base font-bold text-text">
                {tr("Report Generation Workbench")}
              </h2>
              <p className="m-0 mt-0.5 text-xs text-text-secondary">
                {tr("Configure organizational boundaries, reporting scope, comparison periods, and GWP standards to generate official compliance reports.")}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {isTableFilteredDifferently && (
              <Button
                variant="secondary"
                size="md"
                onClick={handleSyncFromTable}
                className="gap-1.5 border-brand-200 bg-brand-50/70 text-brand-700 hover:bg-brand-100 hover:border-brand-300 text-xs font-semibold shadow-2xs transition-colors"
              >
                <RotateCcw className="size-3.5 text-brand-600" aria-hidden="true" />
                <span>{tr("Sync from Table Filters")}</span>
                {tableFilterSummary && (
                  <span className="hidden md:inline font-normal text-brand-700/80">
                    ({tableFilterSummary})
                  </span>
                )}
              </Button>
            )}
            <Button onClick={openConfigModal} loading={loading} disabled={loading} className="gap-1.5 shadow-sm">
              <Plus className="size-4" aria-hidden="true" />
              {loading ? tr("Generating...") : tr("Create Report")}
            </Button>
          </div>
        </div>

        {/* Workbench Parameters Grid */}
        <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))] items-end">
          {selectBase(
            tr("Reporting Year *"),
            reportYear,
            (e) => setReportYear(e.target.value),
            <>
              <option value="all">{tr("All Years")}</option>
              {years.length > 0 ? (
                years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))
              ) : (
                <option value={new Date().getFullYear()}>{new Date().getFullYear()}</option>
              )}
            </>,
          )}

          {selectBase(
            tr("Target Scope"),
            scope,
            (e) => setScope(e.target.value),
            <>
              <option value="all">{tr("Total Inventory (Scope 1, 2, 3)")}</option>
              <option value="1">{tr("Scope 1 (Direct)")}</option>
              <option value="2">{tr("Scope 2 (Indirect)")}</option>
              <option value="3">{tr("Scope 3 (Value Chain)")}</option>
            </>,
          )}

          {selectBase(
            tr("Compare With"),
            comparisonYear,
            (e) => setComparisonYear(e.target.value),
            <>
              <option value="none">{tr("None (Single Year)")}</option>
              {years
                .filter((y) => y.toString() !== reportYear)
                .map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              {baseYear && <option value="baseline">{tr("Baseline (")}{baseYear})</option>}
            </>,
          )}

          {selectBase(tr("GWP Metric Standard"), reportGwpStandard, onGwp, gwpOptions())}

          <div className="flex w-full flex-col gap-1.5 [grid-column:span_2] max-[640px]:[grid-column:auto]">
            <span className="text-xs font-semibold text-text-secondary">
              {tr("Target Facilities / Operating Units")}
            </span>
            <React.Suspense fallback={<div className="text-xs text-text-secondary">{tr("Loading facilities...")}</div>}>
              <MultiSelectDropdown
                options={regionOptions}
                selectedValues={reportSelectedRegions}
                onChange={setReportSelectedRegions}
                label={tr("Select facilities (empty for consolidated all)...")}
              />
            </React.Suspense>
          </div>
        </div>

        {reportSelectedRegions.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-border/60">
            <span className="text-xs font-semibold text-text-secondary mr-1">{tr("Selected Facilities:")}</span>
            {reportSelectedRegions.map((rId) => {
              const rName = facilities.find((f) => f.id.toString() === rId)?.name || rId;
              return (
                <Badge key={rId} tone="brand" className="gap-1 text-xs py-0.5">
                  {rName}
                  <button
                    type="button"
                    aria-label={`Remove ${rName}`}
                    onClick={() => removeRegion(rId)}
                    className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0"
                  >
                    ×
                  </button>
                </Badge>
              );
            })}
            <button
              type="button"
              onClick={() => setReportSelectedRegions([])}
              className="text-xs text-brand-600 hover:text-brand-700 hover:underline font-semibold ml-2 cursor-pointer border-0 bg-transparent p-0"
            >
              {tr("Clear selection")}
            </button>
          </div>
        )}
      </Card>

      {/* Separate Card 2: Emissions Activity Ledger & Data Filters */}
      <Card className="flex flex-col gap-4 p-5 shadow-card">
        {/* Table Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 shadow-xs">
              <Table className="size-5 text-emerald-600" aria-hidden="true" />
            </span>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h2 className="m-0 text-base font-bold text-text">
                  {tr("Emissions Activity Ledger")}
                </h2>
                <Badge tone="neutral" className="text-xs font-semibold">
                  {tr("{{count}} total records", { count: totalRecords })}
                </Badge>
                {emissions.length > 0 && emissions.length !== totalRecords && (
                  <Badge tone="brand" className="text-xs font-medium">
                    {tr("{{count}} filtered", { count: emissions.length })}
                  </Badge>
                )}
              </div>
              <p className="m-0 mt-0.5 text-xs text-text-secondary">
                {tr("Filter and inspect granular activity records across facilities, emission sources, and calculation methods.")}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="secondary" onClick={handleExcelExport} className="gap-1.5">
              <Download className="size-4" aria-hidden="true" />
              {tr("Export Excel")}
            </Button>
            {hasActiveFilters && (
              <Button variant="ghost" onClick={resetFilters} className="gap-1.5 text-text-secondary hover:text-text">
                <RotateCcw className="size-4" aria-hidden="true" />
                {tr("Reset Filters")}
              </Button>
            )}
          </div>
        </div>

        {/* Integrated Filter Controls */}
        <div className="flex flex-col gap-3">
          {/* Primary Toolbar: Search + Core Reporting Boundaries */}
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(180px,1fr))] items-end">
            <div className="relative min-w-[200px]">
              <label className="mb-1 block text-xs font-semibold text-text-secondary">{tr("Search Records")}</label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-secondary" aria-hidden="true" />
                <Input
                  className="h-9 pl-9 pr-7"
                  placeholder={tr("Keyword, fuel, facility, equipment...")}
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                {searchTerm && (
                  <button
                    type="button"
                    onClick={() => setSearchTerm("")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-sm text-text-secondary hover:text-text cursor-pointer p-0.5 border-0 bg-transparent"
                    aria-label={tr("Clear search")}
                  >
                    ×
                  </button>
                )}
              </div>
            </div>

            {selectBase(
              tr("Inventory Scope"),
              scope,
              (e) => setScope(e.target.value),
              <>
                <option value="all">{tr("Total Inventory (Scope 1, 2, 3)")}</option>
                <option value="1">{tr("Scope 1 (Direct)")}</option>
                <option value="2">{tr("Scope 2 (Indirect)")}</option>
                <option value="3">{tr("Scope 3 (Value Chain)")}</option>
              </>,
            )}

            {selectBase(
              tr("Reporting Year *"),
              year,
              (e) => setYear(e.target.value),
              <>
                <option value="all">{tr("All Years")}</option>
                {years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </>,
            )}

            {selectBase(
              tr("Month"),
              month,
              (e) => setMonth(e.target.value),
              <>
                <option value="all">{tr("All Months")}</option>
                {MONTHS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </>,
            )}

            {selectBase(
              tr("Region / Facility"),
              regionId,
              (e) => setRegionId(e.target.value),
              <>
                <option value="all">{tr("All Regions & Facilities")}</option>
                {facilities.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name} {f.field ? ` - ${f.field}` : ""}
                  </option>
                ))}
              </>,
            )}

            <div className="flex items-end">
              <Button
                variant={showAdvancedFilters || activeSecondaryCount > 0 ? "secondary" : "ghost"}
                size="md"
                className="h-9 w-full justify-between gap-2 border border-border"
                onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              >
                <span className="flex items-center gap-1.5">
                  <SlidersHorizontal className="size-3.5 text-brand-500" aria-hidden="true" />
                  {tr("More Filters")}
                  {activeSecondaryCount > 0 && (
                    <Badge tone="brand" className="px-1.5 py-0 text-[10px]">
                      {activeSecondaryCount}
                    </Badge>
                  )}
                </span>
                <ChevronDown
                  className={cn("size-3.5 text-text-secondary transition-transform", showAdvancedFilters && "rotate-180")}
                  aria-hidden="true"
                />
              </Button>
            </div>
          </div>

          {/* Secondary Drill-Down Filter Panel (Collapsible) */}
          {showAdvancedFilters && (
            <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(180px,1fr))] rounded-lg border border-border bg-ink-50/60 p-3.5">
              {(scope === "all" || scope === "1") &&
                selectBase(
                  tr("Process / Category"),
                  processType,
                  (e) => setProcessType(e.target.value),
                  <>
                    <option value="all">{tr("All Processes")}</option>
                    <option value="combustion">{tr("Stationary Combustion")}</option>
                    <option value="mobile">{tr("Mobile Combustion")}</option>
                    <option value="flaring">{tr("Flaring")}</option>
                    <option value="venting">{tr("Venting")}</option>
                    <option value="fugitive">{tr("Fugitive Emissions")}</option>
                    <option value="pneumatic">{tr("Pneumatic Devices")}</option>
                    <option value="tank">{tr("Storage Tank")}</option>
                  </>,
                )}

              {selectBase(
                tr("Division"),
                division,
                (e) => setDivision(e.target.value),
                <>
                  <option value="all">{tr("All Divisions")}</option>
                  {uniq("division").map((d) => (
                    <option key={String(d)} value={String(d)}>
                      {String(d)}
                    </option>
                  ))}
                </>,
              )}

              {selectBase(
                tr("Field"),
                field,
                (e) => setField(e.target.value),
                <>
                  <option value="all">{tr("All Fields")}</option>
                  {uniq("field").map((f) => (
                    <option key={String(f)} value={String(f)}>
                      {String(f)}
                    </option>
                  ))}
                </>,
              )}

              {selectBase(
                tr("Calc Method"),
                methodFilter,
                (e) => setMethodFilter(e.target.value),
                <>
                  <option value="all">{tr("All Methods")}</option>
                  <option value="custom">{tr("Custom Factor")}</option>
                  <option value="API">{tr("API Engine")}</option>
                  <option value="Location-based">{tr("Location-based")}</option>
                </>,
              )}

              {selectBase(
                tr("Group By"),
                groupBy,
                (e) => setGroupBy(e.target.value),
                <>
                  <option value="none">{tr("No Grouping")}</option>
                  <option value="facility">{tr("By Region")}</option>
                  <option value="process">{tr("By Category/Process")}</option>
                  <option value="month">{tr("By Month")}</option>
                  <option value="scope">{tr("By Scope")}</option>
                </>,
              )}

              {selectBase(
                tr("Compare With"),
                comparisonYear,
                (e) => setComparisonYear(e.target.value),
                <>
                  <option value="none">{tr("None (Single Year)")}</option>
                  {years
                    .filter((y) => y.toString() !== year)
                    .map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))}
                  {baseYear && <option value="baseline">{tr("Baseline (")}{baseYear})</option>}
                </>,
              )}

              {selectBase(tr("GWP Metric Standard"), reportGwpStandard, onGwp, gwpOptions())}
            </div>
          )}

          {/* Active Filter Chips Strip */}
          {hasActiveFilters && (
            <div className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-border/60">
              <span className="text-xs font-semibold text-text-secondary mr-1">{tr("Active Filters:")}</span>
              {scope !== "all" && (
                <Badge tone="brand" className="gap-1 text-xs py-0.5">
                  {tr("Scope {{scope}}", { scope })}
                  <button type="button" onClick={() => setScope("all")} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              {year !== "all" && (
                <Badge tone="brand" className="gap-1 text-xs py-0.5">
                  {tr("Year: {{year}}", { year })}
                  <button type="button" onClick={() => { setYear("all"); setReportYear("all"); }} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              {month !== "all" && (
                <Badge tone="neutral" className="gap-1 text-xs py-0.5">
                  {MONTHS.find(m => m.value.toString() === month.toString())?.label || month}
                  <button type="button" onClick={() => setMonth("all")} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              {regionId !== "all" && (
                <Badge tone="info" className="gap-1 text-xs py-0.5">
                  {facilities.find(f => f.id.toString() === regionId.toString())?.name || regionId}
                  <button type="button" onClick={() => { setRegionId("all"); setReportSelectedRegions([]); }} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              {processType !== "all" && (
                <Badge tone="neutral" className="gap-1 text-xs py-0.5">
                  {processType}
                  <button type="button" onClick={() => setProcessType("all")} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              {division !== "all" && (
                <Badge tone="neutral" className="gap-1 text-xs py-0.5">
                  {tr("Division: {{division}}", { division })}
                  <button type="button" onClick={() => setDivision("all")} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              {field !== "all" && (
                <Badge tone="neutral" className="gap-1 text-xs py-0.5">
                  {tr("Field: {{field}}", { field })}
                  <button type="button" onClick={() => setField("all")} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              {methodFilter !== "all" && (
                <Badge tone="neutral" className="gap-1 text-xs py-0.5">
                  {tr("Method: {{method}}", { method: methodFilter })}
                  <button type="button" onClick={() => setMethodFilter("all")} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              {groupBy !== "none" && (
                <Badge tone="neutral" className="gap-1 text-xs py-0.5">
                  {tr("Group: {{group}}", { group: groupBy })}
                  <button type="button" onClick={() => setGroupBy("none")} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              {comparisonYear !== "none" && (
                <Badge tone="neutral" className="gap-1 text-xs py-0.5">
                  {tr("Compare: {{comp}}", { comp: comparisonYear })}
                  <button type="button" onClick={() => setComparisonYear("none")} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              {searchTerm.trim() !== "" && (
                <Badge tone="neutral" className="gap-1 text-xs py-0.5">
                  {tr('Search: "{{term}}"', { term: searchTerm })}
                  <button type="button" onClick={() => setSearchTerm("")} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              {reportGwpStandard !== "AR6" && (
                <Badge tone="warning" className="gap-1 text-xs py-0.5">
                  {reportGwpStandard}
                  <button type="button" onClick={() => setReportGwpStandard("AR6")} className="cursor-pointer ml-1 text-inherit hover:opacity-75 border-0 bg-transparent p-0">×</button>
                </Badge>
              )}
              <button
                type="button"
                onClick={resetFilters}
                className="text-xs text-brand-600 hover:text-brand-700 hover:underline font-semibold ml-2 cursor-pointer border-0 bg-transparent p-0"
              >
                {tr("Clear all")}
              </button>
            </div>
          )}
        </div>

        {/* Data Grid Section directly inside Card */}
        {loading && (
          <div className="py-12 flex justify-center items-center">
            <LoadingSpinner />
          </div>
        )}

        {!loading && emissions.length === 0 && (
          <div className="rounded-lg border border-dashed border-border p-8 text-center text-text-secondary flex flex-col items-center gap-2">
            <p className="m-0 text-sm font-medium text-text">{tr("No emission records found matching the active filters.")}</p>
            <p className="m-0 text-xs text-text-secondary">{tr("Try adjusting your scope, facility, or reporting year boundary.")}</p>
            {hasActiveFilters && (
              <Button size="sm" variant="secondary" onClick={resetFilters} className="mt-2 gap-1.5">
                <RotateCcw className="size-3.5" aria-hidden="true" />
                {tr("Reset Filters")}
              </Button>
            )}
          </div>
        )}

        {!loading && emissions.length > 0 && (
          <div className="flex flex-col gap-4" role="region" aria-label={tr("Emission records")}>
            {((groupBy === "none" ? [[null, emissions]] : Object.entries(getGroupedData())) as [string | null, EmissionRecord[]][]).map(([groupKey, rows]) => (
              <section key={groupKey ?? "__all__"} className="flex flex-col gap-2">
                {groupKey !== null && (
                  <h3 className="m-0 flex flex-wrap items-baseline justify-between gap-2 rounded-md bg-ink-100 px-3 py-2 text-sm font-semibold text-text">
                    <span>
                      {groupKey}{" "}
                      <span className="font-normal text-text-secondary">
                        ({rows.length} {rows.length === 1 ? tr("record") : tr("records")})
                      </span>
                    </span>
                    <span title={tr("Subtotal of the records shown on this page")}>
                      {tr("Subtotal")}{" "}{formatNumber(rows.reduce((sum: number, r: EmissionRecord) => sum + (Number(r.co2e_total) || 0), 0))}{" "}{tr("tCO₂e")}
                    </span>
                  </h3>
                )}
                <DataTable
                  tableId="reports"
                  caption={groupKey ?? tr("Emission records")}
                  columns={columns}
                  data={rows}
                  getRowId={(r) => String(r.id)}
                  pageSize={Math.max(rows.length, 1)}
                  showPagination={false}
                  showColumnMenu={groupKey === null}
                />
              </section>
            ))}
          </div>
        )}

        {/* Integrated Pagination Footer */}
        {!loading && totalPages > 1 && (
          <div className="flex items-center justify-between gap-3 border-t border-border pt-4 mt-1">
            <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
              {tr("Previous")}
            </Button>
            <span className="text-xs text-text-secondary">
              {tr("Page {{page}} of {{totalPages}} ({{total}} records)", { page, totalPages, total: totalRecords })}
            </span>
            <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
              {tr("Next")}
            </Button>
          </div>
        )}
      </Card>

      <Dialog
        open={showConfigModal}
        onOpenChange={(o) => !o && setShowConfigModal(false)}
        title={tr("Generate Executive GHG Report")}
        maxWidth="48rem"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowConfigModal(false)}>
              {tr("Cancel")}
            </Button>
            <Button onClick={handleGenerateModalReport} loading={loading} disabled={loading}>
              {loading ? tr("Generating...") : effectiveReportFormat === "master" ? tr("Download Master Report (PDF)") : tr("Generate ISO PDF")}
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          {/* Active Configuration Summary Badge Strip */}
          <div className="rounded-lg border border-border bg-ink-50 p-3 text-xs text-text-secondary flex flex-wrap gap-2 items-center">
            <span className="font-semibold text-text uppercase tracking-wider">{tr("Active Scope & Boundaries:")}</span>
            <Badge tone="brand">{reportYear === "all" ? tr("All Years") : `${tr("Year:")} ${reportYear}`}</Badge>
            <Badge tone={scope === "all" ? "neutral" : "brand"}>{scope === "all" ? tr("All Scopes") : `${tr("Scope")} ${scope}`}</Badge>
            <Badge tone="info">
              {reportSelectedRegions.length === 0
                ? tr("All Facilities (Consolidated)")
                : reportSelectedRegions.map((id) => facilities.find((f) => f.id.toString() === id.toString())?.name || id).join(", ")}
            </Badge>
            <Badge tone="warning">{reportGwpStandard}</Badge>
          </div>

          <SegmentedControl label={tr("Report format")} value={effectiveReportFormat} onChange={setReportFormat} options={FORMATS} className="flex-col sm:flex-row" />

          {/* 2-Column Split: Controls on Left, Document Preview on Right */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-start pt-1">
            {/* Left Column: Configuration Forms (7 cols) */}
            <div className="md:col-span-7 flex flex-col gap-3.5">
              {effectiveReportFormat === "master" ? (
                <div className="rounded-md border border-border bg-ink-50 p-3.5">
                  <h4 className="m-0 mb-1.5 text-sm font-semibold text-text">{tr("Authentic Groupement Berkine (HBNS & El Merk) 2021–2025")}</h4>
                  <p className="m-0 text-xs text-text-secondary leading-relaxed mb-2.5">
                    {tr("Executive annual publication with certified SANGEA GHG quantification and 2030 decarbonization trajectory.")}
                  </p>
                  <ul className="m-0 flex list-disc flex-col gap-1 pl-4 text-xs leading-normal text-text-secondary">
                    <li><strong>{tr("Vertical A4 Portrait")}</strong> {tr("format (25 publication pages).")}</li>
                    <li><strong>{tr("15 High-Resolution Charts (300 DPI)")}</strong>{tr(": Scopes 1 & 2, methane abatement (-76.7%), flaring reduction.")}</li>
                    <li><strong>{tr("18 Multi-Year Appendix Tables")}</strong>{tr(": Raw tables A.1 through A.16.")}</li>
                  </ul>
                </div>
              ) : (
                <>
                  <p className="m-0 text-xs text-text-secondary leading-relaxed">
                    {tr("Please provide the declarations required by ISO 14064-1:2018 before compiling the verified document.")}
                  </p>
                  <Field label={tr("Exclusion Criteria (Significance)")} hint={tr("Criteria used to define significant indirect emissions.")}>
                    <Textarea rows={2} value={exclusionCriteria} onChange={(e) => setExclusionCriteria(e.target.value)} />
                  </Field>
                  <Field label={tr("Verification Status")} hint={tr("Verification type and assurance level.")}>
                    <Input value={verificationStatus} onChange={(e) => setVerificationStatus(e.target.value)} />
                  </Field>
                  {selectBase(tr("GWP Metric Standard"), reportGwpStandard, onGwp, gwpOptions(tr(" — Default")))}
                </>
              )}
            </div>

            {/* Right Column: Live Document Preview Thumbnail (5 cols) */}
            <div className="md:col-span-5 flex flex-col gap-2.5">
              <div className="rounded-lg border border-border bg-ink-50/70 p-3 flex flex-col items-center">
                <div className="w-full flex items-center justify-between mb-2">
                  <span className="text-[11px] font-semibold tracking-wider text-text-secondary uppercase">
                    {tr("Document Preview")}
                  </span>
                  <Badge tone="brand" className="text-[10px] px-1.5 py-0">
                    {effectiveReportFormat === "master" ? tr("25 Pages") : tr("~12 Pages")}
                  </Badge>
                </div>

                {/* Miniature Realistic A4 Sheet Representation */}
                <div className="w-[170px] h-[225px] rounded-sm border border-border/80 bg-surface shadow-md p-2.5 flex flex-col justify-between relative overflow-hidden select-none">
                  {/* Top accent bar */}
                  <div className="absolute top-0 left-0 right-0 h-1 bg-brand-500" />

                  {/* Document Header */}
                  <div className="flex flex-col gap-0.5 mt-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[8px] font-black tracking-widest text-brand-600 uppercase">NEOCARBON</span>
                      <span className="text-[7px] text-text-secondary font-mono">{effectiveReportFormat === "master" ? "E&P" : "ISO 14064"}</span>
                    </div>
                    <div className="h-px w-full bg-border/60 my-0.5" />
                    <div className="text-[8.5px] font-bold leading-tight text-text line-clamp-2">
                      {effectiveReportFormat === "master" ? tr("Groupement Berkine Master Report") : tr("GHG Inventory Statement")}
                    </div>
                    <div className="text-[7px] text-text-secondary font-medium truncate">
                      {effectiveReportFormat === "master"
                        ? "HBNS & El Merk Operating Units"
                        : (reportSelectedRegions.length === 1
                            ? facilities.find((f) => f.id.toString() === reportSelectedRegions[0]?.toString())?.name || "Facility Report"
                            : tr("Consolidated Corporate Boundary"))}
                    </div>
                    <div className="text-[7px] text-brand-600 font-semibold">
                      {tr("Period:")} {reportYear}
                    </div>
                  </div>

                  {/* Mini Wireframe Elements (Charts & Tables) */}
                  <div className="flex flex-col gap-1.5 my-auto py-1">
                    <div className="flex items-end gap-1 h-6 border-b border-border/60 pb-0.5 px-1">
                      <div className="w-2.5 bg-brand-500/70 rounded-xs h-5" />
                      <div className="w-2.5 bg-brand-400/60 rounded-xs h-3.5" />
                      <div className="w-2.5 bg-brand-600/80 rounded-xs h-4.5" />
                      <div className="w-2.5 bg-ink-300 rounded-xs h-3" />
                      <div className="w-2.5 bg-ink-400 rounded-xs h-4" />
                      <div className="w-2.5 bg-brand-500 rounded-xs h-3.5" />
                    </div>
                    <div className="flex flex-col gap-0.5 px-0.5">
                      <div className="h-1 bg-ink-200/80 rounded-xs w-full" />
                      <div className="h-1 bg-ink-200/60 rounded-xs w-4/5" />
                      <div className="h-1 bg-ink-200/40 rounded-xs w-3/5" />
                    </div>
                  </div>

                  {/* Document Footer Miniature */}
                  <div className="border-t border-border/60 pt-1 flex items-center justify-between text-[6.5px] text-text-secondary">
                    <span>Sonatrach E&P</span>
                    <span className="font-mono">P. 1 / {effectiveReportFormat === "master" ? "25" : "12"}</span>
                  </div>
                </div>

                {/* Document Specs Badges */}
                <div className="flex flex-wrap gap-1 mt-2.5 justify-center text-[10px]">
                  <Badge tone="neutral" className="text-[9.5px] py-0 px-1">{tr("A4 Portrait")}</Badge>
                  <Badge tone="neutral" className="text-[9.5px] py-0 px-1">{tr("300 DPI")}</Badge>
                  <Badge tone="neutral" className="text-[9.5px] py-0 px-1">{tr("PDF/A")}</Badge>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Dialog>

      {editingEmission && (
        <EditEmissionModal
          isOpen={Boolean(editingEmission)}
          onClose={() => setEditingEmission(null)}
          emission={editingEmission}
          facilities={facilities}
          onSuccess={() => fetchEmissions()}
        />
      )}
    </Page>
  );
};

export default Reports;
