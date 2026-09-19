import React, { useState, useEffect } from "react";
import {
  Info,
  ShieldCheck,
  Download,
  Database,
} from "lucide-react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { useLayout } from "../context/LayoutContext";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import CustomDropdown from "../components/CustomDropdown";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import "./UncertaintyAssessment.css";

const UncertaintyAssessment = () => {
  const { user } = useAuth();
  const toast = useToast();
  const { setTopBarLeft, setTopBarRight } = useLayout();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedYear, setSelectedYear] = useState("all");
  const [selectedScope, setSelectedScope] = useState("all");
  const [selectedFacility, setSelectedFacility] = useState("all");
  const [availableYears, setAvailableYears] = useState([]);
  const [facilities, setFacilities] = useState([]);
  const [exporting, setExporting] = useState(false);

  // Load filter options on mount
  useEffect(() => {
    const loadFilters = async () => {
      try {
        const [filterRes, facRes] = await Promise.all([
          api.get("/filters/available"),
          api.get("/facilities"),
        ]);
        if (filterRes.data?.years?.length > 0) {
          setAvailableYears(filterRes.data.years);
          if (selectedYear === "all") {
            setSelectedYear(filterRes.data.years[0].toString());
          }
        } else {
          setLoading(false);
        }
        if (facRes.data) {
          const facList = Array.isArray(facRes.data) ? facRes.data : facRes.data.facilities || [];
          setFacilities(facList);
          const opDefaults = getUserOperationalDefaults(user, facList);
          if (opDefaults.isRestricted && opDefaults.defaultFacilityId) {
            setSelectedFacility(opDefaults.defaultFacilityId);
          }
        }
      } catch (err) {
        console.error("Failed to load filters:", err);
        setLoading(false);
      }
    };
    loadFilters();
  }, [user]);

  // Fetch uncertainty data when filters change
  useEffect(() => {
    if (selectedYear === "all") {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.set("year", selectedYear);
        if (selectedScope !== "all") params.set("scope", selectedScope);
        if (selectedFacility !== "all") params.set("facility_id", selectedFacility);

        const res = await api.get(`/dashboard/uncertainty?${params.toString()}`);
        setData(res.data);
      } catch (error) {
        console.error("Failed to load uncertainty data:", error);
        toast.error("Failed to load uncertainty data");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [selectedYear, selectedScope, selectedFacility]);

  // TopBar layout integration — breadcrumb
  useEffect(() => {
    setTopBarLeft(
      <div className="breadcrumbs" style={{ borderRight: "none", paddingRight: 0 }}>
        <ShieldCheck
          size={16}
          style={{ color: "var(--accent-color, #ff6600)" }}
        />
        <span>Compliance</span>
        <span style={{ margin: "0 8px", color: "var(--text-secondary)" }}>/</span>
        <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
          Uncertainty Assessment
        </span>
      </div>
    );

    return () => {
      setTopBarLeft(null);
      setTopBarRight(null);
    };
  }, [setTopBarLeft, setTopBarRight]);

  // CSV export handler
  const handleExport = async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      params.set("year", selectedYear);
      params.set("export", "csv");
      if (selectedScope !== "all") params.set("scope", selectedScope);
      if (selectedFacility !== "all") params.set("facility_id", selectedFacility);

      const res = await api.get(`/dashboard/uncertainty?${params.toString()}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `uncertainty_${selectedYear}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Uncertainty assessment exported successfully");
    } catch (err) {
      console.error("Export failed:", err);
      toast.error("Export failed");
    } finally {
      setExporting(false);
    }
  };

  // Tier color utility
  const getTierColorClass = (tierName) => {
    if (tierName === "Tier 3") return "tier-3-color";
    if (tierName === "Tier 2") return "tier-2-color";
    return "tier-1-color";
  };

  // Inventory uncertainty level
  const getUncertaintyLevel = (decimal) => {
    if (decimal < 0.1) return "level-low";
    if (decimal < 0.2) return "level-medium";
    return "level-high";
  };

  // Build dropdown options
  const yearOptions = [
    { value: "all", label: "Select Year" },
    ...availableYears.map((y) => ({ value: y.toString(), label: y.toString() })),
  ];

  const scopeOptions = [
    { value: "all", label: "All Scopes" },
    { value: "1", label: "Scope 1" },
    { value: "2", label: "Scope 2" },
    { value: "3", label: "Scope 3" },
  ];

  const facilityOptions = [
    { value: "all", label: "All Facilities" },
    ...facilities.map((f) => ({
      value: (f.id || f.facility_id || "").toString(),
      label: f.name || f.facility_name || `Facility ${f.id}`,
    })),
  ];

  if (loading) {
    return (
      <div className="uncertainty-assessment">
        <LoadingSpinner message="Quantifying Inventory Uncertainty..." />
      </div>
    );
  }

  return (
    <div className="uncertainty-assessment">
      {/* ── Page Header ── */}
      <div className="ua-page-header">
        <div>
          <h1 className="ua-title">Data Reliability Analysis</h1>
          <p className="ua-subtitle">
            Dynamic uncertainty quantification across the complete GHG
            inventory, compliant with ISO 14064-1 §7.5 and IPCC 2006 GL Vol.1
            §3.3.
          </p>
          {data && (
            <div className="ua-inventory-badge">
              <div className="ua-inventory-label">Inventory Uncertainty</div>
              <div
                className={`ua-inventory-value ${getUncertaintyLevel(data.inventory_uncertainty_decimal)}`}
              >
                {data.inventory_uncertainty_pct}
              </div>
              {data.confidence_level_pct && (
                <div className="ua-confidence-badge">
                  {data.confidence_level_pct}% CI (k={data.coverage_factor})
                </div>
              )}
            </div>
          )}
        </div>

        <div className="ua-controls">
          <div className="ua-filter-group" style={{ width: "130px" }}>
            <CustomDropdown
              options={yearOptions}
              value={selectedYear}
              onChange={setSelectedYear}
              placeholder="Year"
            />
          </div>
          <div className="ua-filter-group" style={{ width: "150px" }}>
            <CustomDropdown
              options={scopeOptions}
              value={selectedScope}
              onChange={setSelectedScope}
              placeholder="Scope"
            />
          </div>
          <div className="ua-filter-group" style={{ width: "200px" }}>
            <CustomDropdown
              options={facilityOptions}
              value={selectedFacility}
              onChange={setSelectedFacility}
              placeholder="Facility"
            />
          </div>

          <button
            className="ua-export-btn"
            onClick={handleExport}
            disabled={exporting || !data}
            title="Export uncertainty assessment as CSV"
          >
            <Download size={16} />
            {exporting ? "Exporting..." : "Export CSV"}
          </button>
        </div>
      </div>

      {!data ? (
        <div className="ua-methodology-box" style={{ marginTop: "24px" }}>
          <Info size={24} className="ua-methodology-icon" />
          <div>
            <h4>No Uncertainty Data Available</h4>
            <p>
              No verified emission records found for the selected filters.
              Ensure emissions have been submitted and verified before running
              the uncertainty assessment.
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* ── Tier Breakdown Cards ── */}
      <div className="ua-tier-grid">
        {Object.entries(data.tier_breakdown || {}).map(([tier, pct]) => (
          <div key={tier} className="ua-tier-card">
            <div className="ua-tier-label">{tier} (Data Quality)</div>
            <div className={`ua-tier-value ${getTierColorClass(tier)}`}>
              {pct}%
            </div>
            <div className="ua-tier-bar">
              <div
                className={`ua-tier-bar-fill ${getTierColorClass(tier)}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* ── Legend ── */}
      <div className="legend-bar">
        <div className="legend-item">
          <div className="legend-dot" style={{ background: "#10b981" }} />
          Low Uncertainty (≤ ±10%)
        </div>
        <div className="legend-item">
          <div className="legend-dot" style={{ background: "#f59e0b" }} />
          Medium Uncertainty (±10% to ±30%)
        </div>
        <div className="legend-item">
          <div className="legend-dot" style={{ background: "#ef4444" }} />
          High Uncertainty (&gt; ±30%)
        </div>
      </div>

      {/* ── Category Sections ── */}
      <div className="category-grid">
        {data.categories.map((section, idx) => (
          <div key={idx} className="category-section">
            <div className="category-header">
              <h3 className="category-title">{section.category}</h3>
              <div
                className={`uncertainty-badge uncertainty-${section.level}`}
              >
                {section.uncertainty_pct}
              </div>
            </div>

            <div className="uncertainty-grid">
              {section.top_contributors.map((factor, fIdx) => (
                <div key={fIdx} className="factor-card">
                  <div className="factor-header">
                    <div>
                      <div className="factor-name">{factor.name}</div>
                      <div className="factor-source">Primary Contributor</div>
                    </div>
                    <div className="factor-uncertainty-tag">
                      {factor.uncertainty}
                    </div>
                  </div>
                  <div className="factor-stats">
                    <div className="factor-stat-bar-wrapper">
                      <div className="factor-stat-labels">
                        <span>Impact on Category</span>
                        <span className="factor-stat-value">
                          {factor.contribution}%
                        </span>
                      </div>
                      <div className="factor-stat-track">
                        <div
                          className="factor-stat-fill"
                          style={{ width: `${factor.contribution}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      </>
      )}

      {/* ── Methodology Footer ── */}
      <div className="ua-methodology-box">
        <Info size={24} className="ua-methodology-icon" />
        <div>
          <h4>Calculation Methodology</h4>
          <p>
            Uncertainty is quantified using the Square Root of Sum of Squares
            (SRSS) propagation method per IPCC 2006 GL Vol.1 §3.3 Eq. 3.3.
            Individual emission factor uncertainties are derived from the
            calculation tiers (IPCC/API). The coverage factor k=2 is applied
            per GUM §6.2 to derive the expanded uncertainty at the 95%
            confidence interval. Activity data uncertainties are tier-specific
            per IPCC GL Vol.1 Table 3.1.
          </p>
        </div>
      </div>
    </div>
  );
};

export default UncertaintyAssessment;
