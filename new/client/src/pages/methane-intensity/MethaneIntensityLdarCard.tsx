import React, { useState, useEffect, useMemo } from "react";
import { Wrench, CheckCircle, AlertTriangle, ArrowRight, Layers, Activity } from "lucide-react";
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
  const [, setError] = useState<string | null>(null);

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
      if (selectedFacilityId === "none") return new Set<string>();
      const ids = String(selectedFacilityId).split(",").map((s) => s.trim()).filter(Boolean);
      return new Set(ids);
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
      if (selectedFacilityId === "none") return t("No Facility Selected");
      const ids = String(selectedFacilityId).split(",").map((s) => s.trim()).filter(Boolean);
      if (ids.length === 1) {
        const match = facilities.find((f) => String(f.id) === ids[0]);
        return match?.name || t("Selected Facility");
      }
      return `${ids.length} ${t("Facilities Selected")}`;
    }
    return t("Enterprise Scope");
  }, [facilities, selectedFacilityId]);

  // Filtered components
  const filteredComponents = useMemo(() => {
    return components.filter((c) => {
      if (selectedFacilityId === "none") return false;
      if (matchingFacilityIds.size > 0 && !matchingFacilityIds.has(String(c.facility_id))) {
        return false;
      }
      return true;
    });
  }, [components, matchingFacilityIds, selectedFacilityId]);

  // Filtered surveys (by facility and year)
  const filteredSurveys = useMemo(() => {
    return surveys.filter((s) => {
      if (selectedFacilityId === "none") return false;
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
  }, [surveys, matchingFacilityIds, selectedYear, selectedFacilityId]);

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
    <div className="card p-6 rounded-lg bg-surface border border-border shadow-card">
      {/* Header Row */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4 pb-3.5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center size-[38px] rounded-md bg-info-bg text-info-fg">
            <Wrench size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h3 className="text-base font-bold text-text m-0">
                {t("LDAR Fugitive Component Tracking")}
              </h3>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-ink-100 text-text-secondary border border-border">
                {facilityDisplayName} • {selectedYear === "all" ? t("All-Time") : selectedYear}
              </span>
            </div>
            <p className="text-xs text-text-secondary m-0 mt-0.5">
              {t("Bottom-up EPA Method 21 & Optical Gas Imaging (OGI) leak detection surveys")}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {topLeakingEquipment && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-900 border border-amber-300">
              <AlertTriangle size={13} className="text-amber-600" />
              {t("Most Leaks:")} {topLeakingEquipment.equipment} ({topLeakingEquipment.count})
            </span>
          )}
          <button
            type="button"
            onClick={onNavigateToLdar}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-transparent text-blue-600 border border-blue-600 cursor-pointer transition-colors hover:bg-blue-50"
          >
            <span>{t("Manage LDAR")}</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* 4-Column Metric Grid */}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3.5">
        {/* Tile 1: Monitored Components */}
        <div className="p-3.5 rounded-md border border-border border-l-2 border-l-blue-500 bg-surface">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-text-secondary">
              {t("Monitored Components")}
            </span>
            <Layers size={15} className="text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-text tabular-nums leading-tight">
            {loading ? "..." : totalComponents.toLocaleString()}
          </div>
          <div className="text-xs text-text-secondary mt-1">
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
          className={`p-3.5 rounded-md border border-border border-l-2 bg-surface ${
            openLeaksCount > 0
              ? "border-l-rose-600"
              : "border-l-emerald-600"
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span
              className={`text-xs font-medium ${
                openLeaksCount > 0 ? "text-rose-700" : "text-emerald-700"
              }`}
            >
              {t("Active / Open Leaks")}
            </span>
            {openLeaksCount > 0 ? (
              <AlertTriangle size={15} className="text-rose-600" />
            ) : (
              <CheckCircle size={15} className="text-emerald-600" />
            )}
          </div>
          <div
            className={`text-2xl font-bold tabular-nums leading-tight ${
              openLeaksCount > 0 ? "text-rose-700" : "text-emerald-800"
            }`}
          >
            {loading ? "..." : openLeaksCount}
          </div>
          <div
            className={`text-xs mt-1 ${
              openLeaksCount > 0 ? "text-rose-600" : "text-emerald-700"
            }`}
          >
            {openLeaksCount > 0
              ? t("Requires repair & verification")
              : t("Zero active leaks reported")}
          </div>
        </div>

        {/* Tile 3: Repaired Leaks */}
        <div className="p-3.5 rounded-md border border-border border-l-2 border-l-emerald-600 bg-surface">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-text-secondary">
              {t("Repaired Leaks")}
            </span>
            <CheckCircle size={15} className="text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-text tabular-nums leading-tight">
            {loading ? "..." : repairedCount}
          </div>
          <div className="text-xs text-text-secondary mt-1">
            {t("Verified repaired post-survey")}
          </div>
        </div>

        {/* Tile 4: Component Leak Rate */}
        <div className="p-3.5 rounded-md border border-border border-l-2 border-l-indigo-500 bg-surface">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-text-secondary">
              {t("Component Leak Rate")}
            </span>
            <Activity size={15} className="text-indigo-500" />
          </div>
          <div className="text-2xl font-bold text-text tabular-nums leading-tight">
            {loading ? "..." : `${leakRatePct.toFixed(2)}%`}
          </div>
          <div className="mt-1">
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${benchmarkStatus.badgeClass}`}
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
