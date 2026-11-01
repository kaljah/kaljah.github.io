import React, { useState, useEffect } from "react";
import { BookOpen, Search, ExternalLink, HelpCircle, Layers, Award, Sigma } from "lucide-react";
import { Dialog, Badge, Input, Button, Skeleton } from "../ui";
import { t } from "../i18n";
import api from "../api";

export interface KpiDefinition {
  id: string;
  name: string;
  short_name: string;
  unit: string;
  category: string;
  formula: string;
  standard: string;
  description: string;
  tier_support?: string[];
  notes?: string;
}

export interface KpiMethodologyDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialKpiId?: string | null;
}

export const KpiMethodologyDrawer: React.FC<KpiMethodologyDrawerProps> = ({
  open,
  onOpenChange,
  initialKpiId,
}) => {
  const [kpis, setKpis] = useState<KpiDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [activeKpiId, setActiveKpiId] = useState<string | null>(initialKpiId || null);

  useEffect(() => {
    if (open) {
      if (initialKpiId) {
        setActiveKpiId(initialKpiId);
      }
      if (kpis.length === 0) {
        setLoading(true);
        api
          .get("/api/dashboard/kpi-definitions")
          .then((res) => {
            if (res.data?.kpis) {
              setKpis(res.data.kpis);
            }
          })
          .catch((err) => {
            console.error("Failed to load KPI definitions:", err);
          })
          .finally(() => {
            setLoading(false);
          });
      }
    }
  }, [open, initialKpiId]);

  const categories = ["All", "Emissions Inventory", "Production Denominator", "Intensity & Performance", "Methane & Flaring", "Regulatory & Maturity", "Assurance & QA/QC"];

  const filtered = kpis.filter((k) => {
    const matchesCat = selectedCategory === "All" || k.category === selectedCategory;
    const q = search.toLowerCase().trim();
    const matchesSearch =
      !q ||
      k.name.toLowerCase().includes(q) ||
      k.short_name.toLowerCase().includes(q) ||
      k.formula.toLowerCase().includes(q) ||
      k.standard.toLowerCase().includes(q) ||
      k.description.toLowerCase().includes(q);
    return matchesCat && matchesSearch;
  });

  const activeKpi = kpis.find((k) => k.id === activeKpiId) || (filtered.length > 0 ? filtered[0] : null);

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={
        <span className="flex items-center gap-2">
          <BookOpen className="size-5 text-brand-600" aria-hidden="true" />
          <span>{t("KPI Methodology & Calculation Registry")}</span>
        </span>
      }
      description={t(
        "Standardized mathematical formulas, source citations (API Compendium 2021, GHG Protocol, OGMP 2.0), and audit definitions.",
      )}
      footer={<Button onClick={() => onOpenChange(false)}>{t("Close")}</Button>}
      className="max-w-4xl"
    >
      <div className="flex flex-col gap-4">
        {/* Search and Category Filter Bar */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-secondary"
              aria-hidden="true"
            />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("Search by formula, standard, or KPI name...")}
              className="pl-9 h-9"
              aria-label={t("Filter KPI definitions")}
            />
          </div>
          <div className="flex flex-wrap gap-1">
            {categories.slice(0, 4).map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`cursor-pointer rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                  selectedCategory === cat
                    ? "bg-brand-500 text-white"
                    : "bg-ink-100 text-text-secondary hover:bg-ink-200 hover:text-text"
                }`}
              >
                {cat === "All" ? t("All") : t(cat)}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="space-y-3 py-4">
            <Skeleton className="h-8 w-1/3" />
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : filtered.length === 0 ? (
          <p className="py-8 text-center text-sm text-text-secondary">
            {t("No KPI definitions match your filter criteria.")}
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-12 gap-4 max-h-[60vh] overflow-hidden">
            {/* KPI List Selector Sidebar */}
            <div className="md:col-span-5 flex flex-col gap-1.5 overflow-y-auto pr-1 max-h-[58vh]">
              {filtered.map((k) => {
                const isSelected = activeKpi?.id === k.id;
                return (
                  <button
                    key={k.id}
                    type="button"
                    onClick={() => setActiveKpiId(k.id)}
                    className={`text-left p-2.5 rounded-lg border transition-all cursor-pointer flex flex-col gap-1 ${
                      isSelected
                        ? "border-brand-500 bg-brand-50/50 shadow-xs"
                        : "border-border hover:border-border-strong hover:bg-ink-50/70"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-1.5">
                      <span className="font-semibold text-xs text-text truncate">{k.name}</span>
                      <Badge tone={isSelected ? "brand" : "neutral"} className="text-[0.65rem] shrink-0">
                        {k.unit}
                      </Badge>
                    </div>
                    <span className="text-[0.7rem] text-text-secondary line-clamp-1">{k.standard}</span>
                  </button>
                );
              })}
            </div>

            {/* Active KPI Detailed Card */}
            {activeKpi && (
              <div className="md:col-span-7 flex flex-col gap-3 overflow-y-auto p-4 rounded-xl border border-border bg-surface shadow-xs max-h-[58vh]">
                <div className="flex items-start justify-between gap-2 border-b border-border pb-3">
                  <div>
                    <h3 className="text-base font-bold text-text m-0">{activeKpi.name}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge tone="brand" className="text-xs">
                        {activeKpi.category}
                      </Badge>
                      <span className="text-xs font-mono text-text-secondary">
                        {t("Unit")}: <strong>{activeKpi.unit}</strong>
                      </span>
                    </div>
                  </div>
                </div>

                {/* Mathematical Formula */}
                <div className="flex flex-col gap-1 rounded-lg bg-ink-50 p-3 border border-border">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-text">
                    <Sigma className="size-3.5 text-brand-600" aria-hidden="true" />
                    <span>{t("Mathematical Formula")}</span>
                  </div>
                  <pre className="m-0 font-mono text-xs whitespace-pre-wrap text-brand-900 bg-white/80 p-2 rounded border border-border/60">
                    {activeKpi.formula}
                  </pre>
                </div>

                {/* Regulatory / Industry Standard */}
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-text">
                    <Award className="size-3.5 text-amber-600" aria-hidden="true" />
                    <span>{t("Authoritative Standard & Reference")}</span>
                  </div>
                  <p className="text-xs text-text-secondary m-0 bg-ink-50/50 p-2 rounded border border-border/40">
                    {activeKpi.standard}
                  </p>
                </div>

                {/* Plain-Language Explanation */}
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-text">
                    <HelpCircle className="size-3.5 text-emerald-600" aria-hidden="true" />
                    <span>{t("Plain-Language Explanation & Methodology")}</span>
                  </div>
                  <p className="text-xs leading-relaxed text-text m-0">
                    {activeKpi.description}
                  </p>
                </div>

                {/* Tier Support */}
                {activeKpi.tier_support && activeKpi.tier_support.length > 0 && (
                  <div className="flex flex-col gap-1 pt-1">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-text">
                      <Layers className="size-3.5 text-blue-600" aria-hidden="true" />
                      <span>{t("Supported Calculation Tiers")}</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {activeKpi.tier_support.map((tier) => (
                        <Badge key={tier} tone="neutral" className="text-[0.7rem]">
                          {tier}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Notes */}
                {activeKpi.notes && (
                  <div className="mt-1 rounded-md bg-amber-50/60 border border-amber-200/60 p-2.5 text-[0.75rem] text-amber-900 leading-normal">
                    <strong>{t("Audit Note")}:</strong> {activeKpi.notes}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Dialog>
  );
};
