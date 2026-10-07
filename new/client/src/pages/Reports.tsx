import { ChevronDown, Download, FilePlus, FileSpreadsheet, FileText, Funnel, Pencil, Plus, RotateCcw, Search } from "lucide-react";
import { NativeSelect } from "../ui/NativeSelect";
import { Badge, Button, Card, CardHeader, DataTable, Dialog, Field, Input, Menu, MenuContent, MenuItem, MenuTrigger, Page, PageHeader, SegmentedControl, StatusPill, Textarea, type BadgeTone } from "../ui";
import { controlClass } from "../components/import-wizard/mapping";
import React, { useState, useEffect, useMemo, useRef } from "react";
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
  { accessorKey: "id", header: "ID", cell: (c) => <span className="text-xs text-text-secondary">{c.getValue()}</span> },
  { id: "date", header: "Date", accessorFn: (r) => r.year * 100 + r.month, cell: (c) => `${c.row.original.month}/${c.row.original.year}` },
  { accessorKey: "scope", header: "Scope", cell: (c) => {
    const tones: Record<string | number, BadgeTone> = { 1: "brand", 2: "info" };
    return <Badge tone={tones[c.getValue()] || "neutral"}>Scope {c.getValue()}</Badge>;
  } },
  { accessorKey: "division", header: "Division", cell: (c) => NA(c.getValue()) },
  { accessorKey: "field", header: "Field", cell: (c) => NA(c.getValue()) },
  { accessorKey: "facility_name", header: "Facility", cell: (c) => NA(c.getValue()) },
  { accessorKey: "group_name", header: "Group", cell: (c) => NA(c.getValue()) },
  { accessorKey: "equipment_id", header: "Equipment", cell: (c) => NA(c.getValue()) },
  { accessorKey: "process_type", header: "Category/Process", cell: (c) => <span className="font-medium">{c.getValue()}</span> },
  { accessorKey: "fuel", header: "Fuel/Source", cell: (c) => NA(c.getValue()) },
  { accessorKey: "factor_type", header: "Factor Type", cell: (c) => <span className="text-sm">{NA(c.getValue())}</span> },
  {
    accessorKey: "amount",
    header: "Qty",
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
    header: "Total",
    meta: { numeric: true, unit: "tCO₂e" },
    // BUG-UI-06 FIX: show an em dash for null instead of a misleading 0.00
    cell: (c) => <span className="font-bold text-primary">{c.getValue() != null ? fmt(c.getValue()) : "—"}</span>,
  },
  { accessorKey: "status", header: "Status", cell: (c) => <StatusPill status={c.getValue() || "Verified"} /> },
];

const Reports: React.FC = () => {
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
        header: "Actions",
        cell: (c) => (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setEditingEmission(c.row.original)}
            className="gap-1 px-2.5 py-1 text-xs"
          >
            <Pencil className="size-3" aria-hidden="true" />
            Edit
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
  const [year, setYear] = useState<string>("all");
  const [month, setMonth] = useState<string>("all");
  const [division, setDivision] = useState<string>("all");
  const [field, setField] = useState<string>("all");
  const [methodFilter, setMethodFilter] = useState<string>("all");
  const [regionId, setRegionId] = useState<string>("all");
  const [processType, setProcessType] = useState<string>("all");
  const [searchTerm, setSearchTerm] = useState<string>("");
  // BUG-021: debounce the search box so we issue one request per pause, not per keystroke
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");
  const [groupBy, setGroupBy] = useState<string>("none"); // none, facility, process, month

  // Pagination
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalRecords, setTotalRecords] = useState<number>(0);

  const [scope, setScope] = useState<string>("all");

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
    toast.info("Filters reset to defaults.");
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
        if (filterRes.data.years?.length > 0) {
          const mostRecentYear = filterRes.data.years[0].toString();
          setYear(mostRecentYear);
        } else {
          setYear("all");
        }

        const opDefaults = getUserOperationalDefaults(user, facilitiesData);
        if (opDefaults.isRestricted || facilitiesData.length === 1) {
          if (opDefaults.defaultFacilityId) setRegionId(opDefaults.defaultFacilityId);
          if (opDefaults.defaultDivision) setDivision(opDefaults.defaultDivision);
        }
      } catch (err) {
        console.error("Error fetching initial data", err);
        toast.error("Failed to load filter data");
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
      toast.error(apiError(err, "Failed to load emissions data"));
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
      toast.error("Export failed. Please try again.");
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
      toast.error("Failed to export PDF. Please try again.");
    }
  };

  const handleOGMPExport = async () => {
    try {
      toast.info("Generating OGMP 2.0 Excel Workbook...");
      const yr =
        reportYear !== "all" ? reportYear : year !== "all" ? year
          : String(availableFilters.years[0] || new Date().getFullYear()); // latest year with data (was always 2024)
      const response = await api.get(`/reports/ogmp-export?year=${yr}`, {
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
      toast.success(`OGMP 2.0 Excel report for ${yr} downloaded successfully!`);
    } catch (error) {
      console.error("OGMP Excel export failed:", error);
      toast.error("Failed to export OGMP 2.0 Excel report.");
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
      const reportTitle = isElMerk ? "El Merk (Block 208) Master Report" : "Groupement Berkine Master Report";
      const downloadFilename = isElMerk ? "El_Merk_2025_Annual_GHG_Report.pdf" : "Groupement_Berkine_2025_Annual_GHG_Report.pdf";

      toast.info(`Downloading ${reportTitle} (PDF)...`);
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
      toast.success(`${reportTitle} downloaded successfully!`);
    } catch (error) {
      console.error("Master report download failed:", error);
      toast.error("Failed to download Master Report.");
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
  const [reportFormat, setReportFormat] = useState<string>("master");
  const [exclusionCriteria, setExclusionCriteria] = useState<string>("Sources contributing less than 1% of the total footprint are excluded.");
  const [verificationStatus, setVerificationStatus] = useState<string>("Not externally verified");

  const openConfigModal = () => {
    if (reportSelectedRegions.length === 0) {
      toast.error("Please select at least one region/facility.");
      return;
    }
    setShowConfigModal(true);
  };

  const handleGenerateModalReport = async () => {
    setShowConfigModal(false);
    if (reportFormat === "master") {
      await handleMasterReportDownload();
      return;
    }
    await handleISOReportWrapper();
  };

  const handleISOReportWrapper = async () => {
    setLoading(true);
    toast.info("Generating ISO 14064-1 Report...");
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
      toast.success("Report generated successfully!");
    } catch (err) {
      console.error("Report Generation Error", err);
      toast.error("Failed to generate report.");
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
    { value: "master", label: "🏆 2025 Master Analytical Report (Vertical A4, 15 Charts, 18 Tables)" },
    { value: "iso", label: "📋 ISO 14064-1 Compliance Report" },
  ];
  const years = availableFilters.years;

  return (
    <Page className="reports-page max-w-[1600px]">
      <PageHeader
        title="Reports"
        description={
          <>
            Emission database and exports. Complete history of all recorded emissions and compliance data.{" "}
            <span className="font-semibold text-text">
              Total records: {totalRecords} | Showing: {emissions.length}
            </span>
          </>
        }
        actions={
          <>
            <Button variant="secondary" onClick={resetFilters}>
              <RotateCcw className="size-4" aria-hidden="true" />
              Reset filters
            </Button>
            <Menu>
              <MenuTrigger asChild>
                <Button>
                  <Download className="size-4" aria-hidden="true" />
                  Export
                  <ChevronDown className="size-4" aria-hidden="true" />
                </Button>
              </MenuTrigger>
              <MenuContent>
                <MenuItem icon={FileSpreadsheet} onSelect={handleOGMPExport}>
                  OGMP 2.0 (Excel)
                </MenuItem>
                <MenuItem icon={FileSpreadsheet} onSelect={handleExcelExport}>
                  Excel export
                </MenuItem>
                <MenuItem icon={FileText} onSelect={handlePDFExport}>
                  PDF report
                </MenuItem>
                <MenuItem icon={FileText} onSelect={() => handleMasterReportDownload()}>
                  2025 Master report (PDF)
                </MenuItem>
              </MenuContent>
            </Menu>
          </>
        }
      />

      <Card>
        <CardHeader title={<span className="flex items-center gap-3"><FilePlus className="size-6 text-brand-500" aria-hidden="true" /> Create New Report</span>} />
        <div className="grid items-end gap-5 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))]">
          {selectBase(
            "Reporting Year *",
            reportYear,
            (e) => setReportYear(e.target.value),
            <>
              <option value="all">All Years</option>
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
            "Compare With",
            comparisonYear,
            (e) => setComparisonYear(e.target.value),
            <>
              <option value="none">None (Single Year)</option>
              {years
                .filter((y) => y.toString() !== reportYear)
                .map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              {baseYear && <option value="baseline">Baseline ({baseYear})</option>}
            </>,
          )}
          {selectBase("GWP Metric Standard", reportGwpStandard, onGwp, gwpOptions())}
          <div className="flex w-full flex-col gap-1.5 [grid-column:span_2] max-[640px]:[grid-column:auto]">
            <span className="text-sm font-medium text-text">
              Regions / Facilities <span className="text-danger-fg">*</span>
            </span>
            <React.Suspense fallback={<div>Loading...</div>}>
              <MultiSelectDropdown options={regionOptions} selectedValues={reportSelectedRegions} onChange={setReportSelectedRegions} label="Select Regions..." />
            </React.Suspense>
          </div>
          <Button size="lg" onClick={openConfigModal} loading={loading} disabled={loading}>
            <Plus className="size-[18px]" aria-hidden="true" />
            {loading ? "Generating..." : "Create Report"}
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
        <CardHeader title={<span className="flex items-center gap-3"><Funnel className="size-6 text-brand-500" aria-hidden="true" /> Filter &amp; Group Data</span>} />
        <div className="grid items-end gap-5 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))]">
          {selectBase(
            "Inventory Scope",
            scope,
            (e) => setScope(e.target.value),
            <>
              <option value="all">Total Inventory (Scope 1,2,3)</option>
              <option value="1">Scope 1 (Direct)</option>
              <option value="2">Scope 2 (Indirect)</option>
              <option value="3">Scope 3 (Value Chain)</option>
            </>,
          )}
          {selectBase(
            "Reporting Year",
            year,
            (e) => setYear(e.target.value),
            <>
              <option value="all">All Years</option>
              {years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </>,
          )}
          {selectBase(
            "Month",
            month,
            (e) => setMonth(e.target.value),
            <>
              <option value="all">All Months</option>
              {MONTHS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </>,
          )}
          {selectBase(
            "Region (Grid)",
            regionId,
            (e) => setRegionId(e.target.value),
            <>
              <option value="all">All Regions</option>
              {facilities.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} {f.field ? ` - ${f.field}` : ""}
                </option>
              ))}
            </>,
          )}
          {scope === "1" &&
            selectBase(
              "Process Type",
              processType,
              (e) => setProcessType(e.target.value),
              <>
                <option value="all">All Processes</option>
                <option value="combustion">Stationary Combustion</option>
                <option value="mobile">Mobile Combustion</option>
                <option value="flaring">Flaring</option>
                <option value="venting">Venting</option>
                <option value="fugitive">Fugitive Emissions</option>
                <option value="pneumatic">Pneumatic Devices</option>
                <option value="tank">Storage Tank</option>
              </>,
            )}
          {selectBase(
            "Division",
            division,
            (e) => setDivision(e.target.value),
            <>
              <option value="all">All Divisions</option>
              {uniq("division").map((d) => (
                <option key={String(d)} value={String(d)}>
                  {String(d)}
                </option>
              ))}
            </>,
          )}
          {selectBase(
            "Field",
            field,
            (e) => setField(e.target.value),
            <>
              <option value="all">All Fields</option>
              {uniq("field").map((f) => (
                <option key={String(f)} value={String(f)}>
                  {String(f)}
                </option>
              ))}
            </>,
          )}
          {selectBase(
            "Calc Method",
            methodFilter,
            (e) => setMethodFilter(e.target.value),
            <>
              <option value="all">All Methods</option>
              <option value="custom">Custom Factor</option>
              <option value="API">API Engine</option>
              <option value="Location-based">Location-based</option>
            </>,
          )}
          {selectBase(
            "Group By",
            groupBy,
            (e) => setGroupBy(e.target.value),
            <>
              <option value="none">No Grouping</option>
              <option value="facility">By Facility</option>
              <option value="process">By Category/Process</option>
              <option value="month">By Month</option>
              <option value="scope">By Scope</option>
            </>,
          )}
        </div>
      </Card>

      <Card>
        <Field label="Search">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-secondary" aria-hidden="true" />
            <Input className="pl-9" placeholder="Search records..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
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
          No emission records found. Adjust your filters or add new
          emissions.
        </div>
      )}

      {!loading && emissions.length > 0 && (
        <div className="flex flex-col gap-4" role="region" aria-label="Emission records">
          {/* BUG-022: rendered through getGroupedData so Group By takes effect */}
          {((groupBy === "none" ? [[null, emissions]] : Object.entries(getGroupedData())) as [string | null, EmissionRecord[]][]).map(([groupKey, rows]) => (
            <section key={groupKey ?? "__all__"} className="flex flex-col gap-2">
              {groupKey !== null && (
                <h3 className="m-0 flex flex-wrap items-baseline justify-between gap-2 rounded-md bg-ink-100 px-3 py-2 text-base font-semibold text-text">
                  <span>
                    {groupKey}{" "}
                    <span className="font-normal text-text-secondary">
                      ({rows.length} record{rows.length === 1 ? "" : "s"} on this page)
                    </span>
                  </span>
                  <span title="Subtotal of the records shown on this page">
                    Subtotal {formatNumber(rows.reduce((sum: number, r: EmissionRecord) => sum + (Number(r.co2e_total) || 0), 0))} tCO₂e
                  </span>
                </h3>
              )}
              <DataTable
                tableId="reports"
                caption={groupKey ?? "Emission records"}
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
            Previous
          </Button>
          <span className="text-sm text-text-secondary">
            Page {page} of {totalPages} ({totalRecords} records)
          </span>
          <Button variant="secondary" onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
            Next
          </Button>
        </div>
      )}

      <Dialog
        open={showConfigModal}
        onOpenChange={(o) => !o && setShowConfigModal(false)}
        title="Generate Executive GHG Report"
        maxWidth="35rem"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowConfigModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleGenerateModalReport} loading={loading} disabled={loading}>
              {loading ? "Generating..." : reportFormat === "master" ? "Download Master Report (PDF)" : "Generate ISO PDF"}
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <SegmentedControl label="Report format" value={reportFormat} onChange={setReportFormat} options={FORMATS} className="flex-col sm:flex-row" />

          {reportFormat === "master" ? (
            <div className="rounded-md border border-border bg-ink-50 p-3.5">
              <h4 className="m-0 mb-1.5 text-base font-semibold text-text">Authentic Groupement Berkine (HBNS &amp; El Merk) 2021–2025</h4>
              <ul className="m-0 flex list-disc flex-col gap-1 pl-5 text-sm leading-normal text-text-secondary">
                <li>
                  <strong>Vertical A4 Portrait</strong> format (25 publication pages).
                </li>
                <li>
                  <strong>15 High-Resolution Charts (300 DPI)</strong>: Scopes 1 &amp; 2, SANGEA modules, 2030 decarbonization target trajectory (-25%), methane abatement (-76.7%), routine flaring reduction and more.
                </li>
                <li>
                  <strong>18 Multi-Year Appendix Tables</strong>: Complete raw tables A.1 through A.16 matching Groupement Berkine&apos;s corporate reporting standards.
                </li>
              </ul>
            </div>
          ) : (
            <>
              <p className="m-0 text-sm text-text-secondary">To ensure 100% compliance with ISO 14064-1, please provide the following mandatory declarations before generating the report.</p>
              <Field label="Exclusion Criteria (Significance)" hint="Document the criteria used to define which indirect emissions are significant and justify any exclusions.">
                <Textarea rows={2} value={exclusionCriteria} onChange={(e) => setExclusionCriteria(e.target.value)} />
              </Field>
              <Field label="Verification Status" hint="State whether the report has been verified, the type of verification, and the level of assurance.">
                <Input value={verificationStatus} onChange={(e) => setVerificationStatus(e.target.value)} />
              </Field>
              {selectBase("GWP Metric Standard", reportGwpStandard, onGwp, gwpOptions(" — Default"))}
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
