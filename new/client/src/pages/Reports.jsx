import { ChevronDown, Download, FileSpreadsheet, FileText, RotateCcw } from "lucide-react";
import { NativeSelect } from "../ui/NativeSelect";
import { Button, DataTable, Menu, MenuContent, MenuItem, MenuTrigger, PageHeader, Field, StatusPill } from "../ui";
import React, { useState, useEffect } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import "./Reports.css";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import MultiSelectDropdown from "../components/MultiSelectDropdown";
import "../pages/Dashboard.css";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import { getActiveGwpFactors } from "../constants";
import { apiError } from "../utils/apiError";
import { useGwpStandard } from "../hooks/useGwpStandard";

// BUG-013: GWP option labels are generated from constants.js so they always
// show the values the report generator will actually apply. "20yr" resolves
// to AR5 20-year in resolveGwpFactors (ModernReportGenerator).
const gwpOptionLabel = (standard, horizon) => {
  const f = getActiveGwpFactors(standard, horizon);
  return `IPCC ${standard} (${horizon}-yr: CH4=${f.CH4}, N2O=${f.N2O})`;
};

const NA = (v) => v || "N/A";
const fmt = (num) =>
  num === null || num === undefined
    ? "0.00"
    : parseFloat(num).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 3 });

const RECORD_COLUMNS = [
  { accessorKey: "id", header: "ID", cell: (c) => <span className="text-xs text-text-secondary">{c.getValue()}</span> },
  { id: "date", header: "Date", accessorFn: (r) => r.year * 100 + r.month, cell: (c) => `${c.row.original.month}/${c.row.original.year}` },
  { accessorKey: "scope", header: "Scope", cell: (c) => <span className={`scope-badge scope-${c.getValue()}`}>Scope {c.getValue()}</span> },
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

const Reports = () => {
  const { user } = useAuth();
  const toast = useToast();
  const [facilities, setFacilities] = useState([]);
  const [baseYear, setBaseYear] = useState(null); // configured base year (the option was labelled 2020)
  const [availableFilters, setAvailableFilters] = useState({
    years: [],
    regions: [],
  });
  const [emissions, setEmissions] = useState([]);
  const [loading, setLoading] = useState(false);

  // Filters
  const [year, setYear] = useState("all");
  const [month, setMonth] = useState("all");
  const [division, setDivision] = useState("all");
  const [field, setField] = useState("all");
  const [methodFilter, setMethodFilter] = useState("all");
  const [regionId, setRegionId] = useState("all");
  const [processType, setProcessType] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  // BUG-021: debounce the search box so we issue one request per pause, not per keystroke
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [groupBy, setGroupBy] = useState("none"); // none, facility, process, month

  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);

  const [scope, setScope] = useState("all");

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
        const facilitiesData = Array.isArray(facRes.data)
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
  const prevFiltersRef = React.useRef({
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
  const buildFilterParams = () => {
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

      console.log("[Reports] Fetching with params:", params);
      const res = await api.get("/emissions", { params });
      console.log(
        "[Reports] Received records:",
        res.data.emissions?.length,
        "Total reported by API:",
        res.data.total,
      );
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

  const handleMasterReportDownload = async (targetFacilityId = null) => {
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


  const getGroupedData = () => {
    if (groupBy === "none") return emissions;
    const grouped = {};
    emissions.forEach((em) => {
      let key;
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

  const formatNumber = (num) => {
    if (num === null || num === undefined) return "0.00";
    return parseFloat(num).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 3,
    });
  };

  // Report Generation State
  const [reportYear, setReportYear] = useState(
    new Date().getFullYear().toString(),
  );
  const [comparisonYear, setComparisonYear] = useState("none"); // [NEW] Comparison Year State
  // the report's GWP set starts at the organisation's active standard (it always started at AR5)
  const { standard: activeGwpStandard } = useGwpStandard();
  const [reportGwpStandard, setReportGwpStandard] = useState(activeGwpStandard || "AR5");
  const gwpTouched = React.useRef(false);
  useEffect(() => {
    if (activeGwpStandard && !gwpTouched.current) setReportGwpStandard(activeGwpStandard);
  }, [activeGwpStandard]);
  const [reportSelectedRegions, setReportSelectedRegions] = useState([]); // Multiselect

  // Derived options
  const regionOptions = facilities.map((f) => ({
    value: f.id.toString(),
    label: f.name,
    subLabel: f.field,
  }));

  const [showConfigModal, setShowConfigModal] = useState(false);
  const [reportFormat, setReportFormat] = useState("master");
  const [exclusionCriteria, setExclusionCriteria] = useState("Sources contributing less than 1% of the total footprint are excluded.");
  const [verificationStatus, setVerificationStatus] = useState("Not externally verified");

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

      await generateModernPDF(api, filters);
      toast.success("Report generated successfully!");
    } catch (err) {
      console.error("Report Generation Error", err);
      toast.error("Failed to generate report.");
    } finally {
      setLoading(false);
    }
  };

  // Chips helper
  const removeRegion = (val) => {
    setReportSelectedRegions((prev) => prev.filter((v) => v !== val));
  };

  return (
    <div className="reports-page">
      <div className="reports-container">
        <div className="content-wrapper">
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
            className="mb-6"
          />

          {/* NEW: Create Report Card (Matches Legacy UI) */}
          <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.78))] [backdrop-filter:blur(14px)] [border-radius:var(--radius-lg)] [padding:28px] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [box-shadow:var(--shadow-card)] [position:relative] [overflow:hidden] [transition:transform_0.22s_ease,_box-shadow_0.22s_ease] hover:[border-color:rgba(255,_255,_255,_0.95)] before:[content:''] before:[position:absolute] before:[top:0] before:[left:0] before:[width:4px] before:[height:100%] before:[background:var(--accent-gradient,_linear-gradient(135deg,_var(--accent-color)_0%,_#ff8a4d_100%))] mb-[24px]!">
            <div className="[display:flex] [align-items:center] [gap:12px] [margin-bottom:20px]">
              <div className="[background:rgba(255,_102,_0,_0.1)] [padding:10px] [border-radius:var(--radius-md)] [display:flex] [align-items:center] [justify-content:center] [color:var(--color-link)]">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="12" y1="18" x2="12" y2="12" />
                  <line x1="9" y1="15" x2="15" y2="15" />
                </svg>
              </div>
              <h3 className="card-title">Create New Report</h3>
            </div>

            <div className="[display:grid] [grid-template-columns:repeat(auto-fit,_minmax(200px,_1fr))] [gap:20px] [align-items:end]!">
              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">
                  Reporting Year{" "}
                  <span className="text-[color:var(--danger)]!">*</span>
                </label>
                <NativeSelect
                  className="component-select"
                  value={reportYear}
                  onChange={(e) => setReportYear(e.target.value)}
                >
                  <option value="all">All Years</option>
                  {availableFilters.years.length > 0 ? (
                    availableFilters.years.map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))
                  ) : (
                    <option value={new Date().getFullYear()}>
                      {new Date().getFullYear()}
                    </option>
                  )}
                </NativeSelect>
              </div>

              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">Compare With</label>
                <NativeSelect
                  className="component-select"
                  value={comparisonYear}
                  onChange={(e) => setComparisonYear(e.target.value)}
                >
                  <option value="none">None (Single Year)</option>
                  {availableFilters.years
                    .filter((y) => y.toString() !== reportYear)
                    .map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))}
                  {baseYear && <option value="baseline">Baseline ({baseYear})</option>}
                </NativeSelect>
              </div>

              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">GWP Metric Standard</label>
                <NativeSelect
                  className="component-select"
                  value={reportGwpStandard}
                  onChange={(e) => { gwpTouched.current = true; setReportGwpStandard(e.target.value); }}
                >
                  <option value="AR5">{gwpOptionLabel("AR5", "100")}</option>
                  <option value="AR6">{gwpOptionLabel("AR6", "100")}</option>
                  <option value="AR4">{gwpOptionLabel("AR4", "100")}</option>
                  <option value="20yr">{gwpOptionLabel("AR5", "20")}</option>
                </NativeSelect>
              </div>

              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%] [flex:2]!">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">
                  Regions / Facilities{" "}
                  <span className="text-[color:var(--danger)]!">*</span>
                </label>
                {/* MultiSelect Component */}
                <React.Suspense fallback={<div>Loading...</div>}>
                  <MultiSelectDropdown
                    options={regionOptions}
                    selectedValues={reportSelectedRegions}
                    onChange={setReportSelectedRegions}
                    label="Select Regions..."
                  />
                </React.Suspense>
              </div>

              <button
                className="[background:linear-gradient(135deg,_var(--accent-color)_0%,_#ff8a4d_100%)] [color:white] [padding:12px_28px] [border-radius:var(--radius-md)] [font-weight:600] [border:none] [display:flex] [align-items:center] [justify-content:center] [gap:10px] [height:45px] [transition:all_0.2s] [width:100%] hover:[box-shadow:0_4px_15px_rgba(255,_102,_0,_0.3)] hover:[transform:translateY(-1px)]"
                onClick={openConfigModal}
                disabled={loading}
                style={{
                  opacity: loading ? 0.7 : 1,
                  cursor: loading ? "not-allowed" : "pointer",
                }}
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                >
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                {loading ? "Generating..." : "Create Report"}
              </button>
            </div>

            {/* Chips */}
            <div
              className="flex! flex-wrap! gap-[8px]! mt-[15px]!"
            >
              {reportSelectedRegions.map((rId) => {
                const rName =
                  facilities.find((f) => f.id.toString() === rId)?.name || rId;
                return (
                  <span
                    key={rId}
                    className="inline-flex! items-center! p-[4px_10px]! rounded-[16px]! bg-[color:rgba(255,_107,_0,_0.1)]! text-[color:var(--primary-color)]! text-[length:0.85rem]!"
                  >
                    {rName}
                    <button
                      onClick={() => removeRegion(rId)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "inherit",
                        marginLeft: "6px",
                        cursor: "pointer",
                        padding: 0,
                      }}
                    >
                      ×
                    </button>
                  </span>
                );
              })}
            </div>
          </div>

          {/* Filter Card */}
          <div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.78))] [backdrop-filter:blur(14px)] [border-radius:var(--radius-lg)] [padding:28px] [margin-bottom:32px] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [box-shadow:var(--shadow-card)] [position:relative] [overflow:hidden] [transition:transform_0.22s_ease,_box-shadow_0.22s_ease] hover:[border-color:rgba(255,_255,_255,_0.95)] before:[content:''] before:[position:absolute] before:[top:0] before:[left:0] before:[width:4px] before:[height:100%] before:[background:var(--accent-gradient,_linear-gradient(135deg,_var(--accent-color)_0%,_#ff8a4d_100%))]">
            <div className="[display:flex] [align-items:center] [gap:12px] [margin-bottom:20px]">
              <div className="[background:rgba(255,_102,_0,_0.1)] [padding:10px] [border-radius:var(--radius-md)] [display:flex] [align-items:center] [justify-content:center] [color:var(--color-link)]">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                </svg>
              </div>
              <h3 className="card-title">Filter & Group Data</h3>
            </div>

            <div className="[display:grid] [grid-template-columns:repeat(auto-fit,_minmax(200px,_1fr))] [gap:20px] [align-items:end]">
              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">Inventory Scope</label>
                <NativeSelect
                  className="component-select"
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                >
                  <option value="all">Total Inventory (Scope 1,2,3)</option>
                  <option value="1">Scope 1 (Direct)</option>
                  <option value="2">Scope 2 (Indirect)</option>
                  <option value="3">Scope 3 (Value Chain)</option>
                </NativeSelect>
              </div>

              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">Reporting Year</label>
                <NativeSelect
                  className="component-select"
                  value={year}
                  onChange={(e) => {
                    console.log(
                      "[Reports] User changed Year to:",
                      e.target.value,
                    );
                    setYear(e.target.value);
                  }}
                >
                  <option value="all">All Years</option>
                  {availableFilters.years.map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
                </NativeSelect>
              </div>

              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">Month</label>
                <NativeSelect
                  className="component-select"
                  value={month}
                  onChange={(e) => setMonth(e.target.value)}
                >
                  <option value="all">All Months</option>
                  {[...Array(12)].map((_, i) => (
                    <option key={i + 1} value={i + 1}>
                      {new Date(0, i).toLocaleString("default", {
                        month: "long",
                      })}
                    </option>
                  ))}
                </NativeSelect>
              </div>
              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">Region (Grid)</label>
                <NativeSelect
                  className="component-select"
                  value={regionId}
                  onChange={(e) => setRegionId(e.target.value)}
                >
                  <option value="all">All Regions</option>
                  {facilities.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name} {f.field ? ` - ${f.field}` : ""}
                    </option>
                  ))}
                </NativeSelect>
              </div>

              {scope === "1" && (
                <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                  <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">Process Type</label>
                  <NativeSelect
                    className="component-select"
                    value={processType}
                    onChange={(e) => setProcessType(e.target.value)}
                  >
                    <option value="all">All Processes</option>
                    <option value="combustion">Stationary Combustion</option>
                    <option value="mobile">Mobile Combustion</option>
                    <option value="flaring">Flaring</option>
                    <option value="venting">Venting</option>
                    <option value="fugitive">Fugitive Emissions</option>
                    <option value="pneumatic">Pneumatic Devices</option>
                    <option value="tank">Storage Tank</option>
                  </NativeSelect>
                </div>
              )}
              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">Division</label>
                <NativeSelect
                  className="component-select"
                  value={division}
                  onChange={(e) => setDivision(e.target.value)}
                >
                  <option value="all">All Divisions</option>
                  {[...new Set(facilities.map((f) => f.division))]
                    .filter(Boolean)
                    .map((div) => (
                      <option key={div} value={div}>
                        {div}
                      </option>
                    ))}
                </NativeSelect>
              </div>
              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">Field</label>
                <NativeSelect
                  className="component-select"
                  value={field}
                  onChange={(e) => setField(e.target.value)}
                >
                  <option value="all">All Fields</option>
                  {[...new Set(facilities.map((f) => f.field))]
                    .filter(Boolean)
                    .map((fld) => (
                      <option key={fld} value={fld}>
                        {fld}
                      </option>
                    ))}
                </NativeSelect>
              </div>
              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">Calc Method</label>
                <NativeSelect
                  className="component-select"
                  value={methodFilter}
                  onChange={(e) => setMethodFilter(e.target.value)}
                >
                  <option value="all">All Methods</option>
                  <option value="custom">Custom Factor</option>
                  <option value="API">API Engine</option>
                  <option value="Location-based">Location-based</option>
                </NativeSelect>
              </div>
              <div className="[display:flex] [flex-direction:column] [gap:6px] [width:100%]">
                <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">Group By</label>
                <NativeSelect
                  className="component-select"
                  value={groupBy}
                  onChange={(e) => setGroupBy(e.target.value)}
                >
                  <option value="none">No Grouping</option>
                  <option value="facility">By Facility</option>
                  <option value="process">By Category/Process</option>
                  <option value="month">By Month</option>
                  <option value="scope">By Scope</option>
                </NativeSelect>
              </div>
            </div>
          </div>

          {/* Filters */}
          <div className="[background:var(--bg-card)] [padding:20px_24px] [border-radius:var(--radius-lg)] [margin-bottom:24px] [display:flex] [gap:20px] [align-items:center] [border:1px_solid_var(--border-color)] [flex-wrap:wrap]">
            <div className="search-input-wrapper">
              <label className="[display:block] [font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary)] [margin-bottom:8px]">Search</label>
              <div className="relative!">
                <input
                  type="text"
                  className="[width:100%] [padding:10px_12px_10px_36px] [background:var(--bg-input)] [border:1px_solid_var(--border-color)] [&&]:[border-radius:var(--radius-md)] [color:var(--text-primary)] [font-size:var(--text-base)] [outline:none] [transition:all_0.2s] [box-sizing:border-box] focus:[border-color:var(--accent-color)] focus:[background:var(--color-white)]"
                  placeholder="Search records..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
          </div>

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
              {(groupBy === "none" ? [[null, emissions]] : Object.entries(getGroupedData())).map(([groupKey, rows]) => (
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
                        Subtotal {formatNumber(rows.reduce((sum, r) => sum + (Number(r.co2e_total) || 0), 0))} tCO₂e
                      </span>
                    </h3>
                  )}
                  <DataTable
                    tableId="reports"
                    caption={groupKey ?? "Emission records"}
                    columns={RECORD_COLUMNS}
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
            <div className="[display:flex] [justify-content:space-between] [align-items:center] [padding:16px_24px] [border-top:1px_solid_var(--border-color)] [background:var(--bg-card)]">
              <button
                className="[background:var(--bg-card)]! [border:1px_solid_var(--border-color)]! [color:var(--text-primary)] [padding:8px_16px] [&&]:[border-radius:var(--radius-md)]! [cursor:pointer] [font-size:var(--text-base)] [transition:all_0.2s] [&:hover:not(:disabled)]:[background:var(--bg-hover)]! [&:hover:not(:disabled)]:[border-color:var(--accent-color)]! disabled:[opacity:0.5] disabled:[cursor:not-allowed]"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Previous
              </button>
              <span
                className="text-[length:0.9rem]! text-[color:var(--text-secondary)]!"
              >
                Page {page} of {totalPages} ({totalRecords} records)
              </span>
              <button
                className="[background:var(--bg-card)]! [border:1px_solid_var(--border-color)]! [color:var(--text-primary)] [padding:8px_16px] [&&]:[border-radius:var(--radius-md)]! [cursor:pointer] [font-size:var(--text-base)] [transition:all_0.2s] [&:hover:not(:disabled)]:[background:var(--bg-hover)]! [&:hover:not(:disabled)]:[border-color:var(--accent-color)]! disabled:[opacity:0.5] disabled:[cursor:not-allowed]"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>

      {showConfigModal && (
        <div className="modal-overlay">
          <div className="modal-content max-w-[560px]!">
            <div className="modal-header">
              <h2>Generate Executive GHG Report</h2>
              <button className="close-btn [background:none] [border:none] [font-size:var(--text-xl)] [cursor:pointer] [color:var(--color-ink-500)]" onClick={() => setShowConfigModal(false)}>×</button>
            </div>
            <div className="modal-body flex! flex-col! gap-[16px]!">
              <div className="input-group">
                <label className="font-semibold!">Select Report Format</label>
                <div className="flex! gap-[10px]! mt-[6px]!">
                  <button
                    type="button"
                    onClick={() => setReportFormat("master")}
                    style={{
                      flex: 1,
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: reportFormat === "master" ? '2px solid #f97316' : '1px solid #cbd5e1',
                      background: reportFormat === "master" ? '#fff7ed' : '#ffffff',
                      color: reportFormat === "master" ? '#c2410c' : '#475569',
                      fontWeight: 600,
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontSize: '0.85rem'
                    }}
                  >
                    🏆 2025 Master Analytical Report (Vertical A4, 15 Charts, 18 Tables)
                  </button>
                  <button
                    type="button"
                    onClick={() => setReportFormat("iso")}
                    style={{
                      flex: 1,
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: reportFormat === "iso" ? '2px solid var(--primary-color, #2563eb)' : '1px solid #cbd5e1',
                      background: reportFormat === "iso" ? '#eff6ff' : '#ffffff',
                      color: reportFormat === "iso" ? '#1d4ed8' : '#475569',
                      fontWeight: 600,
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontSize: '0.85rem'
                    }}
                  >
                    📋 ISO 14064-1 Compliance Report
                  </button>
                </div>
              </div>

              {reportFormat === "master" ? (
                <div className="bg-[color:#f8fafc]! p-[14px]! rounded-[8px]! [border:1px_solid_#e2e8f0]!">
                  <h4 className="m-[0_0_6px_0]! text-[color:#0f172a]! text-[length:0.9rem]!">
                    Authentic Groupement Berkine (HBNS & El Merk) 2021–2025
                  </h4>
                  <ul className="m-[0]! pl-[20px]! text-[length:0.8rem]! text-[color:#475569]! leading-[1.5]!">
                    <li><strong>Vertical A4 Portrait</strong> format (25 publication pages).</li>
                    <li><strong>15 High-Resolution Charts (300 DPI)</strong>: Scopes 1 & 2, SANGEA modules, 2030 decarbonization target trajectory (-25%), methane abatement (-76.7%), routine vs safety flaring, intensities, JV equity allocation, and Criteria Air Pollutants.</li>
                    <li><strong>18 Multi-Year Appendix Tables</strong>: Complete raw tables A.1 through A.16 matching Groupement Berkine's corporate reporting standards.</li>
                  </ul>
                </div>
              ) : (
                <>
                  <p className="text-[length:0.875rem]! text-[color:var(--text-secondary)]!">
                    To ensure 100% compliance with ISO 14064-1, please provide the following mandatory declarations before generating the report.
                  </p>
                  <div className="input-group">
                    <label>Exclusion Criteria (Significance)</label>
                    <p className="text-[length:0.75rem]! text-[color:var(--text-muted)]! mb-[4px]!">
                      Document the criteria used to define which indirect emissions are significant and justify any exclusions.
                    </p>
                    <textarea
                      value={exclusionCriteria}
                      onChange={(e) => setExclusionCriteria(e.target.value)}
                      rows={2}
                      className="w-full! p-[8px]! [border:1px_solid_#e2e8f0]! rounded-[4px]! [resize:vertical]!"
                    />
                  </div>
                  <div className="input-group">
                    <label>Verification Status</label>
                    <p className="text-[length:0.75rem]! text-[color:var(--text-muted)]! mb-[4px]!">
                      State whether the report has been verified, the type of verification, and the level of assurance.
                    </p>
                    <input
                      type="text"
                      value={verificationStatus}
                      onChange={(e) => setVerificationStatus(e.target.value)}
                      className="w-full! p-[8px]! [border:1px_solid_#e2e8f0]! rounded-[4px]!"
                    />
                  </div>
                  <Field className="input-group" label="GWP Metric Standard">
<NativeSelect
                      className="component-select"
                      value={reportGwpStandard}
                      onChange={(e) => { gwpTouched.current = true; setReportGwpStandard(e.target.value); }}
                      style={{ width: '100%', padding: '8px', border: '1px solid #e2e8f0', borderRadius: '4px' }}
                    >
                      <option value="AR5">{`${gwpOptionLabel("AR5", "100")} — Default`}</option>
                      <option value="AR6">{gwpOptionLabel("AR6", "100")}</option>
                      <option value="AR4">{gwpOptionLabel("AR4", "100")}</option>
                      <option value="20yr">{gwpOptionLabel("AR5", "20")}</option>
                    </NativeSelect>
</Field>
                </>
              )}
            </div>
            <div className="modal-footer mt-[24px]! flex! justify-end! gap-[12px]!">
              <Button variant="secondary" type="submit" onClick={() => setShowConfigModal(false)}>Cancel</Button>
              <Button type="submit" onClick={handleGenerateModalReport} disabled={loading} style={{ background: reportFormat === 'master' ? 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)' : undefined, border: 'none' }}>
                {loading ? "Generating..." : reportFormat === 'master' ? "Download Master Report (PDF)" : "Generate ISO PDF"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Reports;
