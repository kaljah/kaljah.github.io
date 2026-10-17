import React, { useState, useEffect, useMemo } from "react";
import { Wrench, CheckCircle, AlertTriangle, ArrowRight, Layers, Activity, Search } from "lucide-react";
import api from "../../api";
import { t } from "../../i18n";

export interface MethaneIntensityLdarCardProps {
  selectedYear: string | number;
  selectedFacilityId: string | number;
  facilities: Array<{
    id: string | number;
    name: string;
    activity?: string;
    division?: string;
    segment?: string;
    [key: string]: any;
  }>;
  currentActivity?: string;
  currentDivision?: string;
  onNavigateToLdar: () => void;
}

interface ComponentItem {
  id: number;
  facility_id: number;
  facility_name?: string;
  equipment_type: string;
  component_type: string;
  service_type: string;
  quantity: number;
  status: string;
}

interface SurveyItem {
  id: number;
  facility_id: number;
  facility_name?: string;
  component_inventory_id?: number;
  survey_method: string;
  survey_date: string;
  leak_status: string;
  screening_value_ppm?: number;
  repair_date?: string;
}

export const MethaneIntensityLdarCard: React.FC<MethaneIntensityLdarCardProps> = ({
  selectedYear,
  selectedFacilityId,
  facilities,
  currentActivity = "all",
  currentDivision = "all",
  onNavigateToLdar,
}) => {
  const [components, setComponents] = useState<ComponentItem[]>([]);
  const [surveys, setSurveys] = useState<SurveyItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchLdarData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [compRes, surveyRes] = await Promise.all([
          api.get("/ldar/components"),
          api.get("/ldar/surveys"),
        ]);
        if (isMounted) {
          setComponents(compRes.data?.components || []);
          setSurveys(surveyRes.data?.surveys || []);
        }
      } catch (err: any) {
        if (isMounted) {
          console.error("Failed to load LDAR operational metrics:", err);
          setError("Failed to load LDAR metrics");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchLdarData();
    return () => {
      isMounted = false;
    };
  }, []);

  // Filter facilities based on current top bar selections
  const matchingFacilityIds = useMemo(() => {
    if (selectedFacilityId && selectedFacilityId !== "all") {
      return new Set([String(selectedFacilityId)]);
    }
    let facs = facilities;
    if (currentActivity && currentActivity !== "all") {
      facs = facs.filter((f) => f.activity === currentActivity);
    }
    if (currentDivision && currentDivision !== "all") {
      facs = facs.filter((f) => f.division === currentDivision);
    }
    return new Set(facs.map((f) => String(f.id)));
  }, [facilities, selectedFacilityId, currentActivity, currentDivision]);

  // Selected facility name for display
  const facilityDisplayName = useMemo(() => {
    if (selectedFacilityId && selectedFacilityId !== "all") {
      const match = facilities.find((f) => String(f.id) === String(selectedFacilityId));
      return match?.name || t("Selected Facility");
    }
    return t("Enterprise Scope");
  }, [facilities, selectedFacilityId]);

  // Filtered components
  const filteredComponents = useMemo(() => {
    return components.filter((c) => {
      if (matchingFacilityIds.size > 0 && !matchingFacilityIds.has(String(c.facility_id))) {
        return false;
      }
      return true;
    });
  }, [components, matchingFacilityIds]);

  // Filtered surveys (by facility and year)
  const filteredSurveys = useMemo(() => {
    return surveys.filter((s) => {
      if (matchingFacilityIds.size > 0 && !matchingFacilityIds.has(String(s.facility_id))) {
        return false;
      }
      if (selectedYear && selectedYear !== "all") {
        if (!s.survey_date || !String(s.survey_date).startsWith(String(selectedYear))) {
          return false;
        }
      }
      return true;
    });
  }, [surveys, matchingFacilityIds, selectedYear]);

  // Aggregate metrics
  const totalComponents = useMemo(() => {
    // a component row without a quantity is one component (the server default); 0 stays 0
    return filteredComponents.reduce((acc, c) => {
      const q = Number(c.quantity ?? 1);
      return acc + (Number.isFinite(q) ? q : 0);
    }, 0);
  }, [filteredComponents]);

  const openLeaksCount = useMemo(() => {
    const leakingSurveys = filteredSurveys.filter((s) => s.leak_status === "Leaking").length;
    if (filteredSurveys.length > 0) {
      return leakingSurveys;
    }
    // Fallback to component inventory broken status if no surveys are logged for period
    return filteredComponents.filter((c) => {
      const st = String(c.status || "").toLowerCase();
      // the server's routes.ldar.is_broken_status
      return ["broken", "leaking", "damaged", "faulty", "needs repair"].includes(st.trim());
    }).length;
  }, [filteredSurveys, filteredComponents]);

  const repairedCount = useMemo(() => {
    return filteredSurveys.filter((s) => s.leak_status === "Repaired").length;
  }, [filteredSurveys]);

  const leakRatePct = useMemo(() => {
    if (filteredSurveys.length > 0) {
      return Number(((openLeaksCount / filteredSurveys.length) * 100).toFixed(2));
    }
    if (totalComponents > 0) {
      return Number(((openLeaksCount / totalComponents) * 100).toFixed(2));
    }
    return 0;
  }, [filteredSurveys, openLeaksCount, totalComponents]);

  // Survey methods breakdown
  const methodCounts = useMemo(() => {
    let method21 = 0;
    let ogi = 0;
    let acoustic = 0;
    filteredSurveys.forEach((s) => {
      const m = String(s.survey_method || "").toLowerCase();
      if (m.includes("21")) method21++;
      else if (m.includes("ogi") || m.includes("optical")) ogi++;
      else if (m.includes("acoustic")) acoustic++;
    });
    return { method21, ogi, acoustic };
  }, [filteredSurveys]);

  // Top leaking equipment / component type
  const topLeakingEquipment = useMemo(() => {
    const counts: Record<string, number> = {};
    filteredSurveys
      .filter((s) => s.leak_status === "Leaking")
      .forEach((s) => {
        const comp = components.find((c) => c.id === s.component_inventory_id);
        const eq = comp?.equipment_type || "Component";
        counts[eq] = (counts[eq] || 0) + 1;
      });

    if (Object.keys(counts).length === 0) {
      filteredComponents
        .filter((c) => {
          const st = String(c.status || "").toLowerCase();
          // the server's routes.ldar.is_broken_status
      return ["broken", "leaking", "damaged", "faulty", "needs repair"].includes(st.trim());
        })
        .forEach((c) => {
          const eq = c.equipment_type || "Component";
          counts[eq] = (counts[eq] || 0) + (Number(c.quantity) || 1);
        });
    }

    const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    if (entries.length === 0) return null;
    return { equipment: entries[0][0], count: entries[0][1] };
  }, [filteredSurveys, filteredComponents, components]);

  // EPA / OGMP leak rate compliance benchmark
  const benchmarkStatus = useMemo(() => {
    if (leakRatePct < 0.2) {
      return {
        label: t("< 0.2% Compliant"),
        badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-300",
        icon: CheckCircle,
      };
    }
    if (leakRatePct <= 1.0) {
      return {
        label: t("0.2 - 1.0% Warning"),
        badgeClass: "bg-amber-50 text-amber-800 border-amber-300",
        icon: AlertTriangle,
      };
    }
    return {
      label: t("> 1.0% High Leak Rate"),
      badgeClass: "bg-rose-50 text-rose-800 border-rose-300",
      icon: AlertTriangle,
    };
  }, [leakRatePct]);

  return (
    <div className="card [padding:20px_24px] [border-radius:var(--radius-lg)] [background:var(--bg-card)] [border:1px_solid_var(--border-color)] [box-shadow:0_1px_3px_rgba(0,0,0,0.05)]">
      {/* Header Row */}
      <div className="[display:flex] [flex-wrap:wrap] [align-items:center] [justify-content:space-between] [gap:16px] [margin-bottom:18px] [padding-bottom:14px] [border-bottom:1px_solid_var(--border-color)]">
        <div className="[display:flex] [align-items:center] [gap:12px]">
          <div className="[display:flex] [align-items:center] [justify-content:center] [width:38px] [height:38px] [border-radius:var(--radius-md)] [background:rgba(37,99,235,0.1)] [color:var(--color-blue-600)]">
            <Wrench size={20} />
          </div>
          <div>
            <div className="[display:flex] [align-items:center] [gap:10px]">
              <h3 className="[font-size:var(--text-base)] [font-weight:700] [color:var(--text-primary)] [margin:0]">
                {t("LDAR Fugitive Component Tracking")}
              </h3>
              <span className="[display:inline-flex] [align-items:center] [gap:4px] [padding:2px_10px] [border-radius:var(--radius-full)] [font-size:var(--text-xs)] [font-weight:600] [background:var(--color-ink-100)] [color:var(--text-secondary)] [border:1px_solid_var(--border-color)]">
                {facilityDisplayName} • {selectedYear === "all" ? t("All-Time") : selectedYear}
              </span>
            </div>
            <p className="[font-size:var(--text-xs)] [color:var(--text-secondary)] [margin:2px_0_0_0]">
              {t("Bottom-up EPA Method 21 & Optical Gas Imaging (OGI) leak detection surveys")}
            </p>
          </div>
        </div>

        <div className="[display:flex] [align-items:center] [gap:12px]">
          {topLeakingEquipment && (
            <span className="[display:inline-flex] [align-items:center] [gap:6px] [padding:4px_10px] [border-radius:var(--radius-full)] [font-size:var(--text-xs)] [font-weight:600] [background:#fef3c7] [color:#92400e] [border:1px_solid_#fcd34d]">
              <AlertTriangle size={13} className="text-amber-600" />
              {t("Most Leaks:")} {topLeakingEquipment.equipment} ({topLeakingEquipment.count})
            </span>
          )}
          <button
            type="button"
            onClick={onNavigateToLdar}
            className="[display:inline-flex] [align-items:center] [gap:6px] [padding:6px_14px] [border-radius:var(--radius-md)] [font-size:var(--text-xs)] [font-weight:600] [background:transparent] [color:var(--color-blue-600)] [border:1px_solid_var(--color-blue-600)] [cursor:pointer] [transition:all_0.15s_ease] [&:hover]:[background:rgba(37,99,235,0.08)]"
          >
            <span>{t("Manage LDAR")}</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* 4-Column Metric Grid */}
      <div className="[display:grid] [grid-template-columns:repeat(auto-fit,minmax(220px,1fr))] [gap:14px]">
        {/* Tile 1: Monitored Components */}
        <div className="[padding:14px_16px] [border-radius:var(--radius-md)] [border:1px_solid_#bfdbfe] [background:#eff6ff]">
          <div className="[display:flex] [align-items:center] [justify-content:space-between] [margin-bottom:6px]">
            <span className="[font-size:11px] [font-weight:700] [text-transform:uppercase] [letter-spacing:0.05em] [color:#1e40af]">
              {t("Monitored Components")}
            </span>
            <Layers size={15} className="[color:#3b82f6]" />
          </div>
          <div className="[font-size:24px] [font-weight:800] [color:#172554] [line-height:1.2]">
            {loading ? "..." : totalComponents.toLocaleString()}
          </div>
          <div className="[font-size:11px] [color:#3b82f6] [margin-top:4px]">
            {filteredSurveys.length > 0
              ? t("{{count}} surveys ({{m21}} M21, {{ogi}} OGI)", {
                  count: filteredSurveys.length,
                  m21: methodCounts.method21,
                  ogi: methodCounts.ogi,
                })
              : t("{{count}} component items in inventory", { count: filteredComponents.length })}
          </div>
        </div>

        {/* Tile 2: Open / Active Leaks */}
        <div
          className={`[padding:14px_16px] [border-radius:var(--radius-md)] [border:1px_solid] ${
            openLeaksCount > 0
              ? "[border-color:#fecdd3] [background:#fff1f2]"
              : "[border-color:#bbf7d0] [background:#f0fdf4]"
          }`}
        >
          <div className="[display:flex] [align-items:center] [justify-content:space-between] [margin-bottom:6px]">
            <span
              className={`[font-size:11px] [font-weight:700] [text-transform:uppercase] [letter-spacing:0.05em] ${
                openLeaksCount > 0 ? "[color:#9f1239]" : "[color:#166534]"
              }`}
            >
              {t("Active / Open Leaks")}
            </span>
            {openLeaksCount > 0 ? (
              <AlertTriangle size={15} className="[color:#e11d48]" />
            ) : (
              <CheckCircle size={15} className="[color:#16a34a]" />
            )}
          </div>
          <div
            className={`[font-size:24px] [font-weight:800] [line-height:1.2] ${
              openLeaksCount > 0 ? "[color:#881337]" : "[color:#14532d]"
            }`}
          >
            {loading ? "..." : openLeaksCount}
          </div>
          <div
            className={`[font-size:11px] [margin-top:4px] ${
              openLeaksCount > 0 ? "[color:#be123c]" : "[color:#15803d]"
            }`}
          >
            {openLeaksCount > 0
              ? t("Requires repair & verification")
              : t("Zero active leaks reported")}
          </div>
        </div>

        {/* Tile 3: Repaired Leaks */}
        <div className="[padding:14px_16px] [border-radius:var(--radius-md)] [border:1px_solid_#bbf7d0] [background:#f0fdf4]">
          <div className="[display:flex] [align-items:center] [justify-content:space-between] [margin-bottom:6px]">
            <span className="[font-size:11px] [font-weight:700] [text-transform:uppercase] [letter-spacing:0.05em] [color:#166534]">
              {t("Repaired Leaks")}
            </span>
            <CheckCircle size={15} className="[color:#16a34a]" />
          </div>
          <div className="[font-size:24px] [font-weight:800] [color:#14532d] [line-height:1.2]">
            {loading ? "..." : repairedCount}
          </div>
          <div className="[font-size:11px] [color:#15803d] [margin-top:4px]">
            {t("Verified repaired post-survey")}
          </div>
        </div>

        {/* Tile 4: Component Leak Rate */}
        <div className="[padding:14px_16px] [border-radius:var(--radius-md)] [border:1px_solid_#c7d2fe] [background:#eef2ff]">
          <div className="[display:flex] [align-items:center] [justify-content:space-between] [margin-bottom:6px]">
            <span className="[font-size:11px] [font-weight:700] [text-transform:uppercase] [letter-spacing:0.05em] [color:#3730a3]">
              {t("Component Leak Rate")}
            </span>
            <Activity size={15} className="[color:#6366f1]" />
          </div>
          <div className="[font-size:24px] [font-weight:800] [color:#1e1b4b] [line-height:1.2]">
            {loading ? "..." : `${leakRatePct.toFixed(2)}%`}
          </div>
          <div className="[margin-top:4px]">
            <span
              className={`[display:inline-flex] [align-items:center] [gap:4px] [padding:1px_8px] [border-radius:var(--radius-full)] [font-size:10px] [font-weight:700] [border:1px_solid] ${benchmarkStatus.badgeClass}`}
            >
              <benchmarkStatus.icon size={11} />
              {benchmarkStatus.label}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MethaneIntensityLdarCard;
