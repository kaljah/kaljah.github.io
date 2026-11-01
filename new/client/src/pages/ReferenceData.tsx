import { PageHeader, Button, Input, TableSkeleton } from "../ui";
import { NativeSelect } from "../ui/NativeSelect";
import React, { useState, useEffect } from "react";
import { activateOnKey } from "../utils/a11yKeys";
import {
  Search,
  ChevronDown,
  ChevronRight,
  Zap,
  Wind,
  Flame,
  Database,
  Filter,
  Info,
  Star,
  Globe,
  Ruler,
  Percent,
  Activity,
  Settings,
} from "lucide-react";
import api from "../api";
import { apiError } from "../utils/apiError";
import "./ReferenceData.css";
import { t } from "../i18n";
import { PROCESS_TYPES } from "../utils/EmissionFactors";

/** Process name shown on a factor's usage badge (the stored value is the process key). */
const usageLabel = (key: string): string => PROCESS_TYPES[key] || key.replace(/_/g, " ");

interface CustomFactor {
  name: string;
  hhv_factor?: number | string;
  co2_factor?: number | string;
  ch4_factor?: number | string;
  n2o_factor?: number | string;
  unit?: string;
  usage?: string;
  [key: string]: any;
}

interface FactorItem {
  name: string;
  hhv?: number | string;
  co2?: number | string;
  ch4?: number | string;
  n2o?: number | string;
  unit?: string;
  usage: string[];
  isCustom?: boolean;
  type?: string;
  description?: string;
  [key: string]: any;
}

interface CategoryDef {
  title: string;
  icon: React.ReactNode;
  color: string;
  isStatic?: boolean;
  columns?: string[];
  items?: Record<string, any>[];
  filteredItems?: Record<string, any>[];
  factors?: FactorItem[];
}

const ReferenceData: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [customFactors, setCustomFactors] = useState<CustomFactor[]>([]);
  const [apiFactors, setApiFactors] = useState<Record<string, any>>({});
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [categoryPages, setCategoryPages] = useState<Record<string, number>>({});
  const PAGE_SIZE = 20;

  const [loadErrors, setLoadErrors] = useState<string[]>([]);

  // BUG-105: each catalog loads independently (allSettled); a failure is shown, not rendered as
  // an empty catalog, and one failing endpoint no longer discards the other
  const fetchData = async () => {
    const [customRes, apiRes] = await Promise.allSettled([
      api.get("/custom-factors"),
      api.get("/emission-factors"),
    ]);
    const errors: string[] = [];
    if (customRes.status === "fulfilled") {
      const d = customRes.value.data;
      setCustomFactors(Array.isArray(d) ? d : d?.data || []);
    } else {
      errors.push(apiError(customRes.reason, t("Custom factors could not be loaded")));
    }
    if (apiRes.status === "fulfilled") {
      setApiFactors(apiRes.value.data?.factors || {});
    } else {
      errors.push(apiError(apiRes.reason, t("The API emission-factor catalog could not be loaded")));
    }
    setLoadErrors(errors);
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const toggleCategory = (cat: string) => {
    setCollapsed((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  const filterFactors = (factorsObj: Record<string, any>): FactorItem[] => {
    return Object.entries(factorsObj)
      .filter(([name]) => name.toLowerCase().includes(searchTerm.toLowerCase()))
      .map(([name, data]) => ({
        name,
        ...data,
        usage: data.usage || [],
      }));
  };

  const categories: Record<string, CategoryDef> = {
    custom: {
      title: t("Custom & Regional Factors"),
      icon: <Star size={20} className="text-[color:var(--color-green-700)]!" />,
      color: "var(--color-green-500)",
      factors: customFactors
        .filter((f) => f.name?.toLowerCase().includes(searchTerm.toLowerCase()))
        .map((f) => ({
          name: f.name,
          hhv: f.hhv_factor,
          co2: f.co2_factor,
          ch4: f.ch4_factor,
          n2o: f.n2o_factor,
          unit: f.unit,
          usage: f.usage ? [f.usage] : ["Custom"],
          isCustom: true,
        })),
    },
    gases: {
      title: t("Gaseous Fuels"),
      icon: <Wind size={20} />,
      color: "var(--color-blue-500)",
      factors: filterFactors(apiFactors).filter((f) => f.type === "gases"),
    },
    liquids: {
      title: t("Liquid Fuels"),
      icon: <Database size={20} />,
      color: "var(--color-violet-500)",
      factors: filterFactors(apiFactors).filter((f) => f.type === "liquids"),
    },
    solids: {
      title: t("Solid Fuels"),
      icon: <Zap size={20} />,
      color: "var(--color-amber-500)",
      factors: filterFactors(apiFactors).filter((f) => f.type === "solids"),
    },
    equipment: {
      title: t("Equipment & Fugitive Factors"),
      icon: <Filter size={20} />,
      color: "var(--color-brand-500)",
      factors: filterFactors(apiFactors).filter((f) => f.type === "equipment"),
    },
    gwp: {
      title: t("Global Warming Potentials (GWPs)"),
      icon: <Globe size={20} />,
      color: "var(--color-legacy-0ea5e9)",
      isStatic: true,
      columns: [t("Gas"), "AR4 (2007)", "AR5 (2013)", "AR6 (2021)"],
      items: [
        { gas: t("Carbon Dioxide (CO₂)"), ar4: "1", ar5: "1", ar6: "1" },
        { gas: t("Methane (CH₄)"), ar4: "25", ar5: "28", ar6: t("29.8 (fossil)") },
        { gas: t("Nitrous Oxide (N₂O)"), ar4: "298", ar5: "265", ar6: "273" },
      ],
    },
    conversions: {
      title: t("Unit Conversions"),
      icon: <Ruler size={20} />,
      color: "var(--color-brand-500)",
      isStatic: true,
      columns: [t("From Unit"), t("To Unit"), t("Multiplier / Factor")],
      items: [
        { from: t("1 MJ (Megajoule)"), to: "MMBtu", mult: "0.000947817" },
        { from: t("1 GJ (Gigajoule)"), to: "MMBtu", mult: "0.947817" },
        { from: "1 kWh", to: "MMBtu", mult: "0.003412142" },
        { from: "1 MWh", to: "MMBtu", mult: "3.412142" },
        { from: "1 BTU", to: "MMBtu", mult: "0.000001" },
        { from: t("1 BOE (Barrel of Oil Equivalent)"), to: "MMBtu", mult: "5.8" },
      ],
    },
    uncertainty: {
      title: t("Data Quality & Uncertainty Tiers"),
      icon: <Percent size={20} />,
      color: "var(--color-pink-500)",
      isStatic: true,
      columns: [t("Tier"), t("Condition"), t("Description")],
      items: [
        {
          tier: t("Tier 3 (High)"),
          cond: t("≤ 5% Uncertainty"),
          desc: t("High quality data based on direct measurement (e.g. flow meter with ±2.0% calibration)."),
        },
        {
          tier: t("Tier 2 (Medium)"),
          cond: t("≤ 15% Uncertainty"),
          desc: t("Good quality data based on engineering calculations and reliable operational parameters."),
        },
        {
          tier: t("Tier 1 (Low)"),
          cond: t("> 15% Uncertainty"),
          desc: t("Estimated data based on generic default emission factors and production throughput."),
        },
      ],
    },
    hhv_defaults: {
      title: t("Default Fuel Heating Values (HHV)"),
      icon: <Flame size={20} />,
      color: "var(--color-legacy-f97316)",
      isStatic: true,
      columns: [t("Fuel Type"), t("Default Heating Value"), t("Unit"), t("Usage context")],
      items: [
        {
          fuel: t("Natural Gas"),
          hhv: "1,020",
          unit: "BTU/scf",
          context: t("Fallback for generic gas combustion"),
        },
        {
          fuel: t("Diesel"),
          hhv: "138,700",
          unit: "BTU/gal",
          context: t("Fallback for diesel generators/vehicles"),
        },
        {
          fuel: t("Gasoline"),
          hhv: "125,000",
          unit: "BTU/gal",
          context: t("Fallback for light vehicles"),
        },
        {
          fuel: t("Fuel Oil"),
          hhv: "138,000",
          unit: "BTU/gal",
          context: t("Fallback for heavy heating oil"),
        },
        {
          fuel: t("Propane"),
          hhv: "91,500",
          unit: "BTU/gal",
          context: t("Fallback for LPG"),
        },
        {
          fuel: t("Butane"),
          hhv: "103,000",
          unit: "BTU/gal",
          context: t("Fallback for LPG"),
        },
      ],
    },
    process_types: {
      title: t("API Compendium Process Mappings"),
      icon: <Activity size={20} />,
      color: "var(--color-legacy-6366f1)",
      isStatic: true,
      columns: [t("Process Name"), t("Category"), t("API Section"), t("Description")],
      items: [
        {
          name: t("Stationary Combustion"),
          cat: t("Combustion"),
          sec: t("Section 5.1"),
          desc: t("Emissions from stationary fuel combustion sources"),
        },
        {
          name: t("Flaring"),
          cat: t("Combustion"),
          sec: t("Section 5.2"),
          desc: t("Gas flaring with dual-efficiency model"),
        },
        {
          name: t("Drilling - Mud Degassing"),
          cat: t("Vented"),
          sec: t("Section 6.2 & 6.3"),
          desc: t("CH₄ emissions from well drilling (Table 6-3) and mud degassing (Table 6-2)"),
        },
        {
          name: t("Well Completions & Workovers"),
          cat: t("Vented"),
          sec: t("Section 6.3"),
          desc: t("Flowback emissions during well completion"),
        },
        {
          name: t("Liquids Unloading"),
          cat: t("Vented"),
          sec: t("Section 6.4"),
          desc: t("Gas venting during liquids unloading operations"),
        },
        {
          name: t("Storage Tanks"),
          cat: t("Vented"),
          sec: t("Section 6.8"),
          desc: t("Flash emissions from crude oil and condensate storage"),
        },
        {
          name: t("Glycol Dehydrator"),
          cat: t("Vented"),
          sec: t("Section 6.11"),
          desc: t("CH₄ emissions from glycol dehydrators"),
        },
        {
          name: t("Acid Gas Removal (AGR)"),
          cat: t("Vented"),
          sec: t("Section 6.12"),
          desc: t("CO₂ venting from AGR units"),
        },
        {
          name: t("Wellhead Fugitive Emissions"),
          cat: t("Fugitive"),
          sec: t("Section 7.2.2"),
          desc: t("Equipment leaks from wellheads (oil/gas)"),
        },
        {
          name: t("Gathering & Boosting"),
          cat: t("Fugitive"),
          sec: t("Section 7.2.3"),
          desc: t("Fugitive emissions from gathering and boosting facilities"),
        },
        {
          name: t("Natural Gas Processing"),
          cat: t("Fugitive"),
          sec: t("Section 7.3"),
          desc: t("Emissions from gas processing plants"),
        },
        {
          name: t("Refinery Gas Systems"),
          cat: t("Fugitive"),
          sec: t("Section 7.4.1"),
          desc: t("Fugitive emissions from refinery gas systems"),
        },
        {
          name: t("Chemical Production (Process CO₂)"),
          cat: t("Process"),
          sec: t("Section 6 (Table 6-167)"),
          desc: t("Process CO₂ from chemical manufacturing"),
        },
      ],
    },
    scope2_defaults: {
      title: t("Scope 2 & 3 Methodological Defaults"),
      icon: <Settings size={20} />,
      color: "var(--color-violet-500)",
      isStatic: true,
      columns: [t("Category"), t("Parameter"), t("Default Value"), t("Source / Rationale")],
      items: [
        {
          cat: t("Scope 2 (Indirect Steam)"),
          param: t("Boiler Emission Factor"),
          val: "53.06 kg CO₂/MMBtu",
          src: t("API standard for generic natural gas fired boilers"),
        },
        {
          cat: t("Scope 2 (Overall)"),
          param: t("Normative Uncertainty"),
          val: "± 30%",
          src: t("GHG Protocol Value Chain default assigned when specific data is missing"),
        },
        {
          cat: t("Scope 3 (Overall)"),
          param: t("Normative Uncertainty"),
          val: "± 30%",
          src: t("GHG Protocol Value Chain default assigned when specific data is missing"),
        },
      ],
    },
  };

  const visibleCategories = Object.entries(categories).filter(([key, cat]) => {
    const matchesType = categoryFilter === "all" || categoryFilter === key;

    if (cat.isStatic) {
      cat.filteredItems = cat.items || [];
      if (searchTerm) {
        cat.filteredItems = (cat.items || []).filter((item) =>
          Object.values(item).some((v) =>
            v.toString().toLowerCase().includes(searchTerm.toLowerCase()),
          ),
        );
      }
      return matchesType && (cat.filteredItems?.length || 0) > 0;
    }

    const hasFactors = (cat.factors?.length || 0) > 0;
    return matchesType && hasFactors;
  });

  return (
    <div className="reference-data">
      <PageHeader
        className="mb-8"
        title={t("Reference Data Library")}
        description={
          <>
            {t("Centralized repository for emission factors, global warming potentials (GWPs), unit conversions, and data quality tiers. Custom regional factors tagged with")}{" "}<Star size={14} className="custom-star inline" aria-hidden="true" />{" "}
            {t("override global defaults.")}
          </>
        }
      />

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 p-5 mb-7 rounded-xl border border-border bg-surface shadow-xs">
        <div className="relative flex-1 min-w-0">
          <Search
            className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-text-secondary"
            aria-hidden="true"
          />
          <Input
            type="text"
            className="pl-10 h-10 w-full"
            placeholder={t("Search by name, fuel type, code, or value...")}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <NativeSelect
          wrapperClassName="w-full sm:w-72 shrink-0"
          className="h-10"
          aria-label={t("Filter by category")}
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value="all">{t("All Categories")}</option>
          <option value="hhv_defaults">{t("Default Heating Values")}</option>
          <option value="process_types">{t("API Process Mappings")}</option>
          <option value="scope2_defaults">{t("Scope 2 & 3 Defaults")}</option>
          <option value="gwp">{t("Global Warming Potentials")}</option>
          <option value="conversions">{t("Unit Conversions")}</option>
          <option value="uncertainty">{t("Data Quality Tiers")}</option>
          <option value="custom">{t("Custom & Regional")}</option>
          <option value="gases">{t("Gases")}</option>
          <option value="liquids">{t("Liquids")}</option>
          <option value="solids">{t("Solids")}</option>
          <option value="equipment">{t("Equipment")}</option>
        </NativeSelect>
      </div>

      {loadErrors.length > 0 && (
        <div
          role="alert"
          className="m-[0_0_16px]! p-[12px_16px]! rounded-[8px]! bg-[color:var(--color-red-50)]! [border:1px_solid_var(--color-legacy-fecaca)]! text-[color:var(--color-legacy-991b1b)]! flex! gap-[12px]! items-center!"
        >
          <div className="flex-1!">{loadErrors.map((e) => <div key={e}>{e}</div>)}</div>
          <Button type="button" variant="ghost" onClick={() => { setLoading(true); fetchData(); }}>{t("Retry")}</Button>
        </div>
      )}
      {loading ? (
        <div className="flex flex-col gap-6 py-4">
          <TableSkeleton rows={8} cols={6} />
          <TableSkeleton rows={6} cols={5} />
        </div>
      ) : (
        <div className="factors-list">
          {visibleCategories.map(([key, cat]) => {
            const allItems = cat.isStatic ? cat.filteredItems || [] : cat.factors || [];
            const currentPage = categoryPages[key] || 1;
            const totalCatPages = Math.max(1, Math.ceil(allItems.length / PAGE_SIZE));
            const pagedItems = allItems.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

            return (
              <div
                key={key}
                className="category-section"
                style={{ borderLeftColor: cat.color }}
              >
                <div role="button" tabIndex={0} onKeyDown={activateOnKey}
                  className="category-header"
                  onClick={() => toggleCategory(key)}
                >
                  <div className="category-title">
                    {cat.icon}
                    {cat.title}
                    <span
                      className="[background:var(--color-primary)] [padding:3px_10px] [border-radius:999px] [font-size:var(--text-sm)] [font-weight:700] bg-[color:var(--color-ink-100)]! text-[color:var(--color-ink-800)]!"
                    >
                      {allItems.length}
                    </span>
                  </div>
                  {collapsed[key] ? (
                    <ChevronRight size={20} />
                  ) : (
                    <ChevronDown size={20} />
                  )}
                </div>

                {!collapsed[key] && (
                  <div className="[width:100%] [overflow-x:auto]">
                    <table className="factors-table">
                      <thead>
                        <tr>
                          {cat.isStatic ? (
                            cat.columns?.map((col, cIdx) => (
                              <th key={cIdx}>{col}</th>
                            ))
                          ) : (
                            <>
                              <th>{t("Name")}</th>
                              {key !== "equipment" ? (
                                <>
                                  <th className="num">{t("HHV")}</th>
                                  <th className="num">{t("CO₂")}</th>
                                  <th className="num">{t("CH₄")}</th>
                                  <th className="num">N₂O</th>
                                  <th>{t("Unit")}</th>
                                </>
                              ) : (
                                <>
                                  <th className="num">{t("CH₄ Factor")}</th>
                                  <th>{t("Unit")}</th>
                                  <th>{t("Description")}</th>
                                </>
                              )}
                              <th>{t("Usage")}</th>
                            </>
                          )}
                        </tr>
                      </thead>
                      <tbody>
                        {cat.isStatic
                          ? (pagedItems as Record<string, any>[]).map((item, idx) => (
                              <tr key={idx}>
                                {Object.values(item).map((val, i) => (
                                  <td
                                    key={i}
                                    style={
                                      i === 0
                                        ? { fontWeight: 600, color: "var(--color-ink-800)" }
                                        : {}
                                    }
                                  >
                                    {val}
                                  </td>
                                ))}
                              </tr>
                            ))
                          : (pagedItems as FactorItem[]).map((f, idx) => (
                              <tr key={idx}>
                                <td className="factor-name">
                                  {f.name}
                                  {f.isCustom && (
                                    <Star size={14} className="custom-star" />
                                  )}
                                </td>
                                {key !== "equipment" ? (
                                  <>
                                    <td className="num">{f.hhv || "-"}</td>
                                    <td className="num">{f.co2 || "-"}</td>
                                    <td className="num">{f.ch4 || "-"}</td>
                                    <td className="num">{f.n2o || "-"}</td>
                                    <td>{f.unit}</td>
                                  </>
                                ) : (
                                  <>
                                    <td className="num">{f.ch4 || "-"}</td>
                                    <td>{f.unit}</td>
                                    <td>{f.description}</td>
                                  </>
                                )}
                                <td>
                                  <div className="flex! gap-[6px]!">
                                    {f.usage.map((u, uIdx) => (
                                      <span
                                        key={uIdx}
                                        className={`[display:inline-flex] [padding:3px_8px] [border-radius:var(--radius-sm)] [font-size:var(--text-xs)] [font-weight:600] usage-${u.toLowerCase()}`}
                                      >
                                        {t(usageLabel(u))}
                                      </span>
                                    ))}
                                  </div>
                                </td>
                              </tr>
                            ))}
                      </tbody>
                    </table>
                    {totalCatPages > 1 && (
                      <div className="flex items-center justify-between border-t border-border px-4 py-2.5 bg-ink-50/50">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setCategoryPages((prev) => ({ ...prev, [key]: Math.max(1, currentPage - 1) }))}
                          disabled={currentPage === 1}
                        >
                          {t("Previous")}
                        </Button>
                        <span className="text-xs text-text-secondary">
                          {t("Page {{page}} of {{total}} ({{count}} items)", {
                            page: currentPage,
                            total: totalCatPages,
                            count: allItems.length,
                          })}
                        </span>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setCategoryPages((prev) => ({ ...prev, [key]: Math.min(totalCatPages, currentPage + 1) }))}
                          disabled={currentPage === totalCatPages}
                        >
                          {t("Next")}
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {visibleCategories.length === 0 && (
            <div
              className="text-center! p-[60px]! bg-[color:rgba(255,255,255,0.4)]! rounded-[16px]! [border:1px_dashed_rgba(0,0,0,0.1)]!"
            >
              <Info
                size={40}
                className="text-[color:var(--color-ink-600)]! mb-[16px]!"
              />
              <h3 className="text-[color:var(--color-ink-800)]! mb-[8px]!">
                {t("No factors found")}
              </h3>
              <p className="text-[color:var(--color-ink-500)]!">
                {t("Try adjusting your search term or category filter.")}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ReferenceData;
