import React, { useState, useEffect } from "react";
import { BarChart } from "../components/charts";
import {
  Info,
  Download,
} from "lucide-react";
import api from "../api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import CustomDropdown from "../components/CustomDropdown";
import { getUserOperationalDefaults } from "../utils/userDefaults";
import "./UncertaintyAssessment.css";

interface Contributor {
  name: string;
  uncertainty: string;
  contribution: number;
}

interface CategorySection {
  category: string;
  level: string;
  uncertainty_pct: string;
  top_contributors: Contributor[];
}

interface UncertaintyData {
  inventory_uncertainty_decimal?: number;
  inventory_uncertainty_pct?: string;
  confidence_level_pct?: number;
  coverage_factor?: number;
  tier_breakdown?: Record<string, number>;
  uncertainty_bands?: Record<string, number>;
  categories: CategorySection[];
  [key: string]: any;
}

interface Facility {
  id?: string | number;
  facility_id?: string | number;
  name?: string;
  facility_name?: string;
  [key: string]: any;
}

const UncertaintyAssessment: React.FC = () => {
  const { user } = useAuth();
  const toast = useToast();

  const [data, setData] = useState<UncertaintyData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedYear, setSelectedYear] = useState<string>("all");
  const [selectedScope, setSelectedScope] = useState<string>("all");
  const [selectedFacility, setSelectedFacility] = useState<string>("all");
  const [availableYears, setAvailableYears] = useState<(string | number)[]>([]);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [exporting, setExporting] = useState<boolean>(false);

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
          const facList: Facility[] = Array.isArray(facRes.data) ? facRes.data : facRes.data.facilities || [];
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
  const getTierColorClass = (tierName: string) => {
    if (tierName === "Tier 3") return "tier-3-color";
    if (tierName === "Tier 2") return "tier-2-color";
    return "tier-1-color";
  };

  // Inventory uncertainty level
  // BUG-062: same thresholds as the legend and the backend `level` (<=10 % low, <=30 % medium, 95 % CI)
  const getUncertaintyLevel = (decimal?: number | null) => {
    if (decimal == null) return "";
    if (decimal <= 0.1) return "level-low";
    if (decimal <= 0.3) return "level-medium";
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
      <div className="[padding:24px_32px_48px] [max-width:1600px] [margin:0_auto] [color:var(--text-primary,_var(--color-ink-900))]">
        <LoadingSpinner message="Quantifying Inventory Uncertainty..." />
      </div>
    );
  }

  return (
    <div className="[padding:24px_32px_48px] [max-width:1600px] [margin:0_auto] [color:var(--text-primary,_var(--color-ink-900))]">
      {/* ── Page Header ── */}
      <div className="[margin-bottom:40px] [display:flex] [justify-content:space-between] [align-items:flex-end]! [gap:24px] [flex-wrap:wrap]! [@media(max-width:900px)]:[flex-direction:column]! [@media(max-width:900px)]:[align-items:flex-start]!">
        <div>
          <h1 className="ua-title">Data Reliability Analysis</h1>
          <p className="[font-size:var(--text-lg)] [color:var(--text-secondary,_var(--color-ink-500))] [max-width:800px] [margin:0] [line-height:1.5]">
            Dynamic uncertainty quantification across the complete GHG
            inventory, compliant with ISO 14064-1 §7.5 and IPCC 2006 GL Vol.1
            §3.3.
          </p>
          {data && (
            <div className="[display:inline-flex] [align-items:center] [gap:16px] [background:var(--bg-card,_rgba(255,_255,_255,_0.78))] [padding:14px_20px] [border-radius:var(--radius-lg)] [border:1px_solid_var(--border-color,_rgba(0,_0,_0,_0.05))] [margin-top:16px]">
              <div className="[font-size:var(--text-base)] [color:var(--text-secondary,_var(--color-ink-500))] [margin-bottom:4px]">Inventory Uncertainty</div>
              <div
                className={`ua-inventory-value ${getUncertaintyLevel(data.inventory_uncertainty_decimal)}`}
              >
                {data.inventory_uncertainty_pct}
              </div>
              {data.confidence_level_pct && (
                <div className="[display:inline-flex] [align-items:center] [gap:6px] [margin-top:8px] [padding:4px_10px] [border-radius:var(--radius-md)] [font-size:var(--text-xs)] [font-weight:700] [letter-spacing:0.03em] [background:rgba(59,_130,_246,_0.08)] [color:var(--color-blue-600)] [border:1px_solid_rgba(59,_130,_246,_0.15)]">
                  {data.confidence_level_pct}% CI (k={data.coverage_factor})
                </div>
              )}
            </div>
          )}
        </div>

        <div className="[display:flex] [gap:20px] [align-items:flex-end] [flex-wrap:wrap]! [@media(max-width:900px)]:[flex-direction:column]! [@media(max-width:900px)]:[width:100%]">
          <div className="[display:flex] [flex-direction:column] [gap:8px] w-[130px]!">
            <CustomDropdown
              options={yearOptions}
              value={selectedYear}
              onChange={setSelectedYear}
              placeholder="Year"
            />
          </div>
          <div className="[display:flex] [flex-direction:column] [gap:8px] w-[150px]!">
            <CustomDropdown
              options={scopeOptions}
              value={selectedScope}
              onChange={setSelectedScope}
              placeholder="Scope"
            />
          </div>
          <div className="[display:flex] [flex-direction:column] [gap:8px] w-[200px]!">
            <CustomDropdown
              options={facilityOptions}
              value={selectedFacility}
              onChange={setSelectedFacility}
              placeholder="Facility"
            />
          </div>

          <button
            className="[display:inline-flex] [align-items:center] [gap:8px] [padding:10px_20px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [background:var(--bg-card,_var(--color-white))] [color:var(--text-primary,_var(--color-ink-800))] [font-size:var(--text-base)] [font-weight:600] [cursor:pointer] [transition:all_0.2s_ease] hover:[background:var(--color-primary)] hover:[color:var(--color-white)] hover:[border-color:var(--accent-color,_var(--color-brand-500))] hover:[transform:translateY(-1px)] hover:[box-shadow:var(--shadow-card)]"
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
        <div className="ua-methodology-box mt-[24px]!">
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
          <div className="[display:grid] [grid-template-columns:repeat(3,_1fr)]! [gap:20px] [margin-bottom:40px] [@media(max-width:900px)]:[grid-template-columns:1fr]!">
            {Object.entries(data.tier_breakdown || {}).map(([tier, pct]) => (
              <div key={tier} className="[background:var(--bg-card,_rgba(255,_255,_255,_0.78))] [padding:20px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [box-shadow:var(--shadow-card,_0_1px_3px_rgba(0,_0,_0,_0.05))] [transition:transform_0.2s_ease,_box-shadow_0.2s_ease] hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card-elevated,_0_4px_12px_rgba(0,_0,_0,_0.1))]">
                <div className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-500))] [font-weight:600]">{tier} (share of Scope 1)</div>
                <div className={`ua-tier-value ${getTierColorClass(tier)}`}>
                  {pct}%
                </div>
                <div className="[width:100%] [height:4px] [background:var(--border-color,_var(--color-ink-100))] [border-radius:var(--radius-sm)] [overflow:hidden]">
                  <div
                    className={`ua-tier-bar-fill ${getTierColorClass(tier)}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* ── Uncertainty bands (whole inventory) ── */}
          {data.uncertainty_bands && (
            <div className="[display:grid] [grid-template-columns:repeat(3,_1fr)]! [gap:20px] [margin-bottom:40px] [@media(max-width:900px)]:[grid-template-columns:1fr]!">
              {[["low", "Low Uncertainty (≤ ±10%)", "band-low"],
                ["medium", "Medium Uncertainty (±10% to ±30%)", "band-medium"],
                ["high", "High Uncertainty (> ±30%)", "band-high"]].map(([band, label, cls]) => (
                <div key={band} className="[background:var(--bg-card,_rgba(255,_255,_255,_0.78))] [padding:20px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [box-shadow:var(--shadow-card,_0_1px_3px_rgba(0,_0,_0,_0.05))] [transition:transform_0.2s_ease,_box-shadow_0.2s_ease] hover:[transform:translateY(-2px)] hover:[box-shadow:var(--shadow-card-elevated,_0_4px_12px_rgba(0,_0,_0,_0.1))]">
                  <div className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-500))] [font-weight:600]">{label}</div>
                  <div className={`ua-tier-value ${cls}`}>{data.uncertainty_bands?.[band] ?? 0}%</div>
                  <div className="[width:100%] [height:4px] [background:var(--border-color,_var(--color-ink-100))] [border-radius:var(--radius-sm)] [overflow:hidden]">
                    <div className={`ua-tier-bar-fill ${cls}`} style={{ width: `${data.uncertainty_bands?.[band] ?? 0}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Legend ── */}
          <div className="[display:flex] [gap:24px] [margin-bottom:32px] [flex-wrap:wrap] [background:var(--bg-card,_rgba(255,_255,_255,_0.4))] [padding:16px_24px] [border-radius:var(--radius-md)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))]">
            <div className="[display:flex] [align-items:center] [gap:10px] [font-size:var(--text-base)] [color:var(--text-secondary,_var(--color-ink-600))] [font-weight:600]">
              <div className="[width:12px] [height:12px] [border-radius:50%] [flex-shrink:0] bg-[color:var(--color-unc-low)]!" />
              Low Uncertainty (≤ ±10%)
            </div>
            <div className="[display:flex] [align-items:center] [gap:10px] [font-size:var(--text-base)] [color:var(--text-secondary,_var(--color-ink-600))] [font-weight:600]">
              <div className="[width:12px] [height:12px] [border-radius:50%] [flex-shrink:0] bg-[color:var(--color-unc-medium)]!" />
              Medium Uncertainty (±10% to ±30%)
            </div>
            <div className="[display:flex] [align-items:center] [gap:10px] [font-size:var(--text-base)] [color:var(--text-secondary,_var(--color-ink-600))] [font-weight:600]">
              <div className="[width:12px] [height:12px] [border-radius:50%] [flex-shrink:0] bg-[color:var(--color-unc-high)]!" />
              High Uncertainty (&gt; ±30%)
            </div>
          </div>

          {/* ── Uncertainty by category, ranked, against the high-uncertainty threshold ── */}
          {data.categories.length > 0 && (
            <div className="category-section [margin-bottom:24px]">
              <div className="category-header">
                <h3 className="category-title">Uncertainty by Category (±%)</h3>
              </div>
              <div className="h-[260px] w-full min-w-0">
                <BarChart
                  data={data.categories.map((c) => {
                    const value = Math.abs(parseFloat(String(c.uncertainty_pct).replace(/[^0-9.\-]/g, ""))) || 0;
                    // Same bands as the legend above: low <= 10, medium <= 30, high > 30.
                    const color = value <= 10 ? "var(--color-unc-low)" : value <= 30 ? "var(--color-unc-medium)" : "var(--color-unc-high)";
                    return { name: c.category, value, color };
                  })}
                  dataKey="value"
                  xKey="name"
                  color="var(--color-unc-high)"
                  horizontal
                  sortDesc
                  height={260}
                  referenceValue={30}
                  referenceLabel="High (±30%)"
                  exportName="uncertainty-by-category"
                  formatValue={(v) => `±${Number(v).toFixed(1)}%`}
                />
              </div>
            </div>
          )}

          {/* ── Category Sections ── */}
          <div className="category-grid">
            {data.categories.map((section, idx) => (
              <div key={idx} className="category-section">
                <div className="category-header">
                  <h3 className="category-title">{section.category}</h3>
                  <div
                    className={`[display:inline-flex] [align-items:center] [gap:6px] [padding:4px_12px] [border-radius:999px] [font-size:var(--text-sm)] [font-weight:700] [letter-spacing:0.02em] [text-transform:uppercase] uncertainty-${section.level}`}
                  >
                    {section.uncertainty_pct}
                  </div>
                </div>

                <div className="uncertainty-grid">
                  {section.top_contributors.map((factor, fIdx) => (
                    <div key={fIdx} className="[background:var(--bg-card,_rgba(255,_255,_255,_0.78))] [backdrop-filter:blur(14px)] [-webkit-backdrop-filter:blur(14px)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.8))] [&&]:[border-radius:var(--radius-lg)] [padding:24px] [transition:transform_0.22s_cubic-bezier(0.16,_1,_0.3,_1),_box-shadow_0.22s_ease,_border-color_0.22s_ease] [box-shadow:var(--shadow-card,_0_4px_6px_-1px_rgba(0,_0,_0,_0.1))] hover:[transform:translateY(-3px)] hover:[box-shadow:var(--shadow-card-elevated,_0_10px_25px_-5px_rgba(0,_0,_0,_0.12))] hover:[border-color:rgba(255,_255,_255,_0.95)]">
                      <div className="[display:flex] [justify-content:space-between] [align-items:flex-start] [margin-bottom:15px]">
                        <div>
                          <div className="factor-name">{factor.name}</div>
                          <div className="[font-size:var(--text-sm)] [font-weight:600] [color:var(--text-secondary,_var(--color-ink-500))] [text-transform:uppercase] [letter-spacing:0.04em]">Primary Contributor</div>
                        </div>
                        <div className="[font-size:var(--text-base)] [font-weight:600] [color:var(--text-secondary,_var(--color-ink-500))] [padding:4px_8px] [background:var(--border-color,_var(--color-ink-100))] [border-radius:var(--radius-sm)] [white-space:nowrap]">
                          {factor.uncertainty}
                        </div>
                      </div>
                      <div className="[display:flex] [align-items:center] [gap:15px]">
                        <div className="[flex:1]">
                          <div className="[display:flex] [justify-content:space-between] [font-size:var(--text-sm)] [margin-bottom:4px] [color:var(--text-secondary,_var(--color-ink-500))]">
                            <span>Impact on Category</span>
                            <span className="[font-weight:700] [color:var(--text-primary,_var(--color-ink-900))]">
                              {factor.contribution}%
                            </span>
                          </div>
                          <div className="[width:100%] [height:6px] [background:var(--border-color,_var(--color-ink-100))] [border-radius:var(--radius-sm)] [overflow:hidden]">
                            <div
                              className="[height:100%] [background:var(--color-blue-500)] [border-radius:var(--radius-sm)] [transition:width_0.5s_cubic-bezier(0.16,_1,_0.3,_1)]"
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
