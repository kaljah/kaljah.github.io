import { ChevronDown, Download, FilePlus, FileSpreadsheet, FileText, Funnel, Pencil, Plus, RotateCcw, Search } from "lucide-react";
import { NativeSelect } from "../ui/NativeSelect";
import { Badge, Button, Card, CardHeader, DataTable, Dialog, Field, Input, Menu, MenuContent, MenuItem, MenuTrigger, Page, PageHeader, SegmentedControl, StatusPill, Textarea, type BadgeTone } from "../ui";
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

  // Filters
  const [year, setYear] = useState<string>(deepLink.year || "all");
  const [month, setMonth] = useState<string>(deepLink.month || "all");
  const [division, setDivision] = useState<string>("all");
  const [field, setField] = useState<string>("all");
  const [methodFilter, setMethodFilter] = useState<string>("all");
  const [regionId, setRegionId] = useState<string>(deepLink.facility || "all");
  const [processType, setProcessType] = useState<string>(deepLink.process || "all");
  const [searchTerm, setSearchTerm] = useState<string>("");
  // BUG-021: debounce the search box so we issue one request per pause, not per keystroke
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");
  const [groupBy, setGroupBy] = useState<string>("none"); // none, facility, process, month

  // Pagination
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalRecords, setTotalRecords] = useState<number>(0);

  const [scope, setScope] = useState<string>(deepLink.scope || "all");

  const resetFilters = () => {
    setYear("all");
    setMonth("all");
    setRegionId("all");
    setProcessType("all");
    setScope("all");
    setDivision("all");
    setField("all");
    setMethodFilter("all");
    setSearchTerm("");
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
        } else {
          setYear("all");
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

  const handleMasterReportDownload = async (targetFacilityId: string | number | null = null) => {
    try {
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
      setLoading(false);
    }
  };

  const getGroupedData = (): Record<string, EmissionRecord[]> => {
    if (groupBy === "none") return { all: emissions };
    const grouped: Record<string, EmissionRecord[]> = {};
    emissions.forEach((em) => {
      let key = "Unknown";
      if (groupBy === "facility") key = em.facility_name || "Unknown";
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

  // Derived options
  const regionOptions = facilities.map((f) => ({
    value: f.id.toString(),
    label: f.name,
    subLabel: f.field,
  }));

  const [showConfigModal, setShowConfigModal] = useState<boolean>(false);
  const [reportFormat, setReportFormat] = useState<string>("iso");
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
    if (reportSelectedRegions.length === 0) {
      toast.error(tr("Please select at least one region/facility."));
      return;
    }
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

      const isAllRegions = reportSelectedRegions.length === facilities.length;

      const filters = {
        year: reportYear,
        comparisonYear: comparisonYear !== "none" ? comparisonYear : undefined,
        scope: "all",
        regionId: isAllRegions ? "all" : reportSelectedRegions,
        processType: "all",
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
                <MenuItem icon={FileSpreadsheet} onSelect={handleOGMPExport}>
                  {tr("OGMP 2.0 (Excel)")}
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

      <Card>
        <CardHeader title={<span className="flex items-center gap-3"><FilePlus className="size-6 text-brand-500" aria-hidden="true" />{" "}{tr("Create New Report")}</span>} />
        <div className="grid items-end gap-5 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))]">
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
          {selectBase(tr("GWP Metric Standard"), reportGwpStandard, onGwp, gwpOptions(), { className: "sm:[grid-column:span_2]" })}
          <div className="flex w-full flex-col gap-1.5 [grid-column:span_2] max-[640px]:[grid-column:auto]">
            <span className="text-sm font-medium text-text">
              {tr("Regions / Facilities")}{" "}<span className="text-danger-fg">*</span>
            </span>
            <React.Suspense fallback={<div>{tr("Loading...")}</div>}>
              <MultiSelectDropdown options={regionOptions} selectedValues={reportSelectedRegions} onChange={setReportSelectedRegions} label={tr("Select Regions...")} />
            </React.Suspense>
          </div>
          <Button size="lg" onClick={openConfigModal} loading={loading} disabled={loading}>
            <Plus className="size-[18px]" aria-hidden="true" />
            {loading ? tr("Generating...") : tr("Create Report")}
          </Button>
        </div>

        {reportSelectedRegions.length > 0 && (
          <ul className="m-0 mt-4 flex list-none flex-wrap gap-2 p-0">
            {reportSelectedRegions.map((rId) => {
              const rName = facilities.find((f) => f.id.toString() === rId)?.name || rId;
              return (
                <li key={rId}>
                  <Badge tone="brand" className="gap-1.5 px-2.5 py-1 text-sm">
                    {rName}
                    <button type="button" aria-label={`Remove ${rName}`} onClick={() => removeRegion(rId)} className="cursor-pointer border-0 bg-transparent p-0 text-inherit">
                      ×
                    </button>
                  </Badge>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      <Card>
        <CardHeader title={<span className="flex items-center gap-3"><Funnel className="size-6 text-brand-500" aria-hidden="true" />{" "}{tr("Filter & Group Data")}</span>} />
        <div className="grid items-end gap-5 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))]">
          {selectBase(
            tr("Inventory Scope"),
            scope,
            (e) => setScope(e.target.value),
            <>
              <option value="all">{tr("Total Inventory (Scope 1,2,3)")}</option>
              <option value="1">{tr("Scope 1 (Direct)")}</option>
              <option value="2">{tr("Scope 2 (Indirect)")}</option>
              <option value="3">{tr("Scope 3 (Value Chain)")}</option>
            </>,
          )}
          {selectBase(
            tr("Reporting Year"),
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
            tr("Region (Grid)"),
            regionId,
            (e) => setRegionId(e.target.value),
            <>
              <option value="all">{tr("All Regions")}</option>
              {facilities.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} {f.field ? ` - ${f.field}` : ""}
                </option>
              ))}
            </>,
          )}
          {scope === "1" &&
            selectBase(
              tr("Process Type"),
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
              <option value="facility">{tr("By Facility")}</option>
              <option value="process">{tr("By Category/Process")}</option>
              <option value="month">{tr("By Month")}</option>
              <option value="scope">{tr("By Scope")}</option>
            </>,
          )}
        </div>
      </Card>

      <Card>
        <Field label={tr("Search")}>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-secondary" aria-hidden="true" />
            <Input className="pl-9" placeholder={tr("Search records...")} value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
          </div>
        </Field>
      </Card>

      {/* Data Grid */}
      {loading && (
        <div className="min-h-[300px]!">
          <LoadingSpinner />
        </div>
      )}

      {!loading && emissions.length === 0 && (
        <div
          className="text-center! p-[40px]! text-[color:var(--text-secondary)]!"
        >
          {tr("No emission records found. Adjust your filters or add new emissions.")}
        </div>
      )}

      {!loading && emissions.length > 0 && (
        <div className="flex flex-col gap-4" role="region" aria-label={tr("Emission records")}>
          {/* BUG-022: rendered through getGroupedData so Group By takes effect */}
          {((groupBy === "none" ? [[null, emissions]] : Object.entries(getGroupedData())) as [string | null, EmissionRecord[]][]).map(([groupKey, rows]) => (
            <section key={groupKey ?? "__all__"} className="flex flex-col gap-2">
              {groupKey !== null && (
                <h3 className="m-0 flex flex-wrap items-baseline justify-between gap-2 rounded-md bg-ink-100 px-3 py-2 text-base font-semibold text-text">
                  <span>
                    {groupKey}{" "}
                    <span className="font-normal text-text-secondary">
                      ({rows.length}{" "}{tr("record")}{rows.length === 1 ? "" : "s"}{" "}{tr("on this page)")}
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

      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between gap-3 border-t border-border px-6 py-4">
          <Button variant="secondary" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
            {tr("Previous")}
          </Button>
          <span className="text-sm text-text-secondary">
            {tr("Page")}{" "}{page}{" "}{tr("of")}{" "}{totalPages} ({totalRecords}{" "}{tr("records)")}
          </span>
          <Button variant="secondary" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
            {tr("Next")}
          </Button>
        </div>
      )}

      <Dialog
        open={showConfigModal}
        onOpenChange={(o) => !o && setShowConfigModal(false)}
        title={tr("Generate Executive GHG Report")}
        maxWidth="35rem"
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
          <SegmentedControl label={tr("Report format")} value={effectiveReportFormat} onChange={setReportFormat} options={FORMATS} className="flex-col sm:flex-row" />

          {effectiveReportFormat === "master" ? (
            <div className="rounded-md border border-border bg-ink-50 p-3.5">
              <h4 className="m-0 mb-1.5 text-base font-semibold text-text">{tr("Authentic Groupement Berkine (HBNS & El Merk) 2021–2025")}</h4>
              <ul className="m-0 flex list-disc flex-col gap-1 pl-5 text-sm leading-normal text-text-secondary">
                <li>
                  <strong>{tr("Vertical A4 Portrait")}</strong>{" "}{tr("format (25 publication pages).")}
                </li>
                <li>
                  <strong>{tr("15 High-Resolution Charts (300 DPI)")}</strong>{tr(": Scopes 1 & 2, SANGEA modules, 2030 decarbonization target trajectory (-25%), methane abatement (-76.7%), routine flaring reduction and more.")}
                </li>
                <li>
                  <strong>{tr("18 Multi-Year Appendix Tables")}</strong>{tr(": Complete raw tables A.1 through A.16 matching Groupement Berkine's corporate reporting standards.")}
                </li>
              </ul>
            </div>
          ) : (
            <>
              <p className="m-0 text-sm text-text-secondary">{tr("Please provide the following declarations required by ISO 14064-1 before generating the report.")}</p>
              <Field label={tr("Exclusion Criteria (Significance)")} hint={tr("Document the criteria used to define which indirect emissions are significant and justify any exclusions.")}>
                <Textarea rows={2} value={exclusionCriteria} onChange={(e) => setExclusionCriteria(e.target.value)} />
              </Field>
              <Field label={tr("Verification Status")} hint={tr("State whether the report has been verified, the type of verification, and the level of assurance.")}>
                <Input value={verificationStatus} onChange={(e) => setVerificationStatus(e.target.value)} />
              </Field>
              {selectBase(tr("GWP Metric Standard"), reportGwpStandard, onGwp, gwpOptions(tr(" — Default")))}
            </>
          )}
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
