import React, { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { recordsLink } from "../../utils/reportLinks";
import { BarChart2, FileText, Grid, FileSpreadsheet, FileCode } from "lucide-react";
import { Badge, Button, SegmentedControl } from "../../ui";
import { BarChart, LineChart } from "../../components/charts";
import { formatNumber } from "../../utils/formatters";
import { ChartCard, Heatmap, type HeatmapRow } from "../intensity/IntensityParts";
import { t } from "../../i18n";
import api from "../../api";
import { useToast } from "../../components/Toast";

const th = "whitespace-nowrap border-b-2 border-border px-4 py-3 text-left text-sm font-semibold uppercase tracking-wide text-text-secondary";
const td = "border-b border-border px-4 py-3.5 text-text";

const pick = (obj: any, a: string, b: string) => obj?.[a] ?? obj?.[b];

export interface CbamSectionProps {
  products: any[];
  facilities: { id: string | number; name: string; [key: string]: any }[];
  selectedYear?: string;
  selectedFacility?: string;
}

/** EU CBAM product-specific embedded emissions table (rows come from /data/cbam-exports). */
export const CbamSection: React.FC<CbamSectionProps> = ({
  products,
  facilities,
  selectedYear,
  selectedFacility,
}) => {
  const toast = useToast();
  const [downloadingFormat, setDownloadingFormat] = useState<"excel" | "xml" | null>(null);

  const handleExport = async (format: "excel" | "xml") => {
    try {
      setDownloadingFormat(format);
      const isXml = format === "xml";
      toast.info(isXml ? t("Generating EU CBAM XML Declaration...") : t("Generating EU CBAM Excel Communication Template..."));
      const params = new URLSearchParams();
      if (selectedYear && selectedYear !== "all") params.append("year", selectedYear);
      if (selectedFacility && selectedFacility !== "all") params.append("facility_id", selectedFacility);
      params.append("format", format);

      const res = await api.get(`/reports/cbam-export?${params.toString()}`, {
        responseType: "blob",
      });

      const mime = isXml ? "application/xml" : "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
      const ext = isXml ? "xml" : "xlsx";
      const yr = selectedYear && selectedYear !== "all" ? selectedYear : "Consolidated";
      const prefix = isXml ? "CBAM_Transitional_Declaration" : "EU_CBAM_Communication_Template";

      const blob = new Blob([res.data], { type: mime });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${prefix}_${yr}.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success(isXml ? t("EU CBAM XML Declaration downloaded successfully.") : t("EU CBAM Communication Template downloaded successfully."));
    } catch (err) {
      console.error("CBAM export error:", err);
      toast.error(t("Failed to export CBAM submission document."));
    } finally {
      setDownloadingFormat(null);
    }
  };

  return (
    <ChartCard
      className="cbam-section"
      title={
        <span className="flex items-center gap-2">
          <FileText className="size-5 text-brand-500" aria-hidden="true" />{" "}{t("EU CBAM Product Specific Embedded Emissions")}
        </span>
      }
      subtitle={t("Direct & indirect specific embedded emissions per export product")}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="brand" className="cbam-benchmark-badge max-w-full shrink whitespace-normal px-3.5 py-1.5 text-sm">
            {t("EU ETS Benchmark (Product-Specific): ~0.025 - 1.2 tCO₂e/t")}
          </Badge>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => handleExport("excel")}
            disabled={downloadingFormat !== null}
            className="inline-flex items-center gap-1.5"
          >
            <FileSpreadsheet className="size-4 text-emerald-600" aria-hidden="true" />
            {downloadingFormat === "excel" ? t("Exporting...") : t("Export CBAM Excel")}
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => handleExport("xml")}
            disabled={downloadingFormat !== null}
            className="inline-flex items-center gap-1.5"
          >
            <FileCode className="size-4 text-blue-600" aria-hidden="true" />
            {downloadingFormat === "xml" ? t("Exporting...") : t("Export CBAM XML")}
          </Button>
        </div>
      }
    >
    {products.length > 0 ? (
      <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={t("CBAM embedded emissions by product")}>
        <table className="custom-table w-full border-collapse text-base">
          <thead>
            <tr>
              {["Facility", "Product Name", "EU CN Code", "Period", "Export Qty (t)", "Destination", "CCS Captured", "Direct SEE (tCO₂e/t)", "Indirect SEE (tCO₂e/t)", "Precursor SEE", "Total Embedded (tCO₂e)", "Origin Tax"].map((h) => (
                <th key={h} scope="col" className={th}>
                  {t(h)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {products.map((p, idx) => {
              const fac = facilities.find((f) => String(f.id) === String(p.facility_id));
              const qty = p.quantityTonnes ?? p.quantity_tonnes ?? 0;
              const direct = p.specificEmbeddedDirect ?? p.specific_embedded_direct;
              const indirect = p.specificEmbeddedIndirect ?? p.specific_embedded_indirect;
              const ccs = p.capturedCo2Tonnes ?? p.captured_co2_tonnes ?? 0;
              const isComplex = Boolean(p.isComplexGood ?? p.is_complex_good);
              const pRatio = p.precursorRatio ?? p.precursor_ratio ?? 0;
              const pDir = p.precursorSeeDir ?? p.precursor_see_dir ?? 0;
              const pIndir = p.precursorSeeIndir ?? p.precursor_see_indir ?? 0;
              const pContrib = isComplex ? pRatio * (pDir + pIndir) : 0;
              const taxPaid = p.carbonPricePaidEur ?? p.carbon_price_paid_eur ?? 0;
              const qtr = p.quarter || `Q${Math.floor(((Number(p.month || 1) - 1) / 3)) + 1}`;
              const total = p.totalEmbeddedEmissions ?? p.total_embedded_emissions ?? (qty * (((direct || 0) + (indirect || 0)) + pContrib));
              return (
                <tr key={p.id || idx} className="hover:bg-ink-100">
                  <td className={`${td} font-semibold`}>{fac ? fac.name : p.facilityName || p.facility_name || "—"}</td>
                  <td className={td}>{pick(p, "productName", "product_name") || "—"}</td>
                  <td className={td}>
                    <span className="code-pill rounded-sm border border-border bg-ink-100 px-2 py-0.5 font-mono text-sm">{pick(p, "cnCode", "cn_code") || "—"}</span>
                  </td>
                  <td className={`${td} whitespace-nowrap`}>
                    {p.year} - {qtr} (M{p.month || 1})
                  </td>
                  <td className={td}>{formatNumber(qty, 0)}</td>
                  <td className={td}>{pick(p, "exportDestination", "export_destination") || "EU"}</td>
                  <td className={td}>
                    {ccs > 0 ? (
                      <span className="font-mono text-emerald-600 dark:text-emerald-400 font-semibold">-{formatNumber(ccs, 1)} t</span>
                    ) : (
                      <span className="text-text-secondary">—</span>
                    )}
                  </td>
                  <td className={td}>
                    <strong className="text-brand-700 font-mono">{typeof direct === "number" ? direct.toFixed(4) : "—"}</strong>
                  </td>
                  <td className={`${td} font-mono`}>{typeof indirect === "number" ? indirect.toFixed(4) : "—"}</td>
                  <td className={`${td} font-mono`}>
                    {pContrib > 0 ? <span className="text-blue-600 dark:text-blue-400 font-medium">+{pContrib.toFixed(4)}</span> : "—"}
                  </td>
                  <td className={td}>
                    <strong className="font-mono text-link">{formatNumber(total, 1)}</strong>
                  </td>
                  <td className={td}>
                    {taxPaid > 0 ? (
                      <span className="font-mono text-xs font-semibold text-amber-600 dark:text-amber-400">€{Number(taxPaid).toFixed(2)}/t</span>
                    ) : (
                      <span className="text-text-secondary">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    ) : (
      <p className="m-0 px-5 py-10 text-center text-base text-text-secondary">
        {t("No CBAM product export records registered for the selected filters. Track exports via")}{" "}<strong>{t("Manage Data > CBAM Products")}</strong>.
      </p>
    )}
  </ChartCard>
);
};

const GAS_TO_BOE = (1.02 / 5.8);

export interface RegionalChartsProps {
  data: any[];
  gwpHorizon: string;
  year?: string;
}

/** Four per-region bar charts: intensity, scope 1 vs 2, oil BOE and gas BOE. */
export const RegionalCharts: React.FC<RegionalChartsProps> = ({ data, gwpHorizon, year }) => {
  const g20 = gwpHorizon === "20";
  const navigate = useNavigate();
  const openRecords = (r: any) => navigate(recordsLink({ facilityId: r.id, year }));

  const regionalAggregated = useMemo(() => {
    const map = new Map<string, any>();
    data.forEach((d) => {
      const regName = d.region || d.facility_name;
      if (!map.has(regName)) {
        map.set(regName, {
          id: d.facility_id,
          name: regName,
          total_oil: 0,
          total_gas: 0,
          total_boe: 0,
          total_scope1: 0,
          total_scope1_gwp20: 0,
          total_scope2: 0,
          total_co2e: 0,
          total_co2e_gwp20: 0,
        });
      }
      const item = map.get(regName);
      item.total_oil += d.total_oil || 0;
      item.total_gas += d.total_gas || 0;
      item.total_boe += d.total_boe || 0;
      item.total_scope1 += d.total_scope1 || 0;
      item.total_scope1_gwp20 += d.total_scope1_gwp20 ?? d.total_scope1 ?? 0;
      item.total_scope2 += d.total_scope2 || 0;
      item.total_co2e += d.total_co2e || 0;
      item.total_co2e_gwp20 += d.total_co2e_gwp20 ?? d.total_co2e ?? 0;
    });

    return Array.from(map.values()).map((r) => {
      const boe = r.total_boe > 0 ? r.total_boe : 0;
      return {
        id: r.id,
        name: r.name,
        value: boe > 0 ? (g20 ? (r.total_co2e_gwp20 * 1000.0) / boe : (r.total_co2e * 1000.0) / boe) : 0,
        scope1: boe > 0 ? Number((((g20 ? r.total_scope1_gwp20 : r.total_scope1) * 1000.0) / boe).toFixed(2)) : 0,
        scope2: boe > 0 ? Number(((r.total_scope2 * 1000.0) / boe).toFixed(2)) : 0,
        oil_value: r.total_oil || 0,
        gas_value: (r.total_gas || 0) * GAS_TO_BOE,
      };
    });
  }, [data, g20]);

  return (
    <div className="chart-grid grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(min(100%,450px),1fr))]">
      <ChartCard className="card" title={t("GHG Intensity by Region (kg CO₂e / BOE)")} rule="var(--color-brand-500)">
        <BarChart
          data={regionalAggregated.map((d) => ({ id: d.id, name: d.name, value: d.value }))}
          dataKey="value"
          xKey="name"
          horizontal
          sortDesc
          onSelect={openRecords}
          selectLabel={(r) => t("Open {{name}} records", { name: r.name })}
          exportName="ghg-intensity-by-region"
          color="var(--color-brand-500)"
        />
      </ChartCard>
      <ChartCard className="card" title={t("Scope 1 Direct vs Scope 2 Intensity by Region")} rule="var(--color-blue-600)">
        <BarChart
          data={regionalAggregated.map((d) => ({ id: d.id, name: d.name, scope1: d.scope1, scope2: d.scope2 }))}
          bars={[
            { dataKey: "scope1", name: g20 ? t("Scope 1 (GWP₂₀ Direct)") : t("Scope 1 (Direct)"), color: "var(--color-blue-600)" },
            { dataKey: "scope2", name: t("Scope 2 (Indirect)"), color: "var(--color-legacy-0ea5e9)" },
          ]}
          xKey="name"
          exportName="scope1-vs-scope2-intensity-by-region"
        />
      </ChartCard>
      <ChartCard className="card" title={t("Oil BOE Contribution by Region")} rule="var(--color-legacy-ea580c)">
        <BarChart
          data={regionalAggregated.map((d) => ({ id: d.id, name: d.name, value: d.oil_value }))}
          dataKey="value"
          xKey="name"
          horizontal
          sortDesc
          onSelect={openRecords}
          selectLabel={(r) => t("Open {{name}} records", { name: r.name })}
          exportName="oil-boe-by-region"
          color="var(--color-legacy-ea580c)"
        />
      </ChartCard>
      <ChartCard className="card" title={t("Gas BOE Contribution by Region")} rule="var(--color-violet-500)">
        <BarChart
          data={regionalAggregated.map((d) => ({ id: d.id, name: d.name, value: d.gas_value }))}
          dataKey="value"
          xKey="name"
          horizontal
          sortDesc
          onSelect={openRecords}
          selectLabel={(r) => t("Open {{name}} records", { name: r.name })}
          exportName="gas-boe-by-region"
          color="var(--color-violet-500)"
        />
      </ChartCard>
    </div>
  );
};

export interface TrendSectionProps {
  view: string;
  onView: (view: string) => void;
  trendChartData: any[];
  rawTrendData: any[];
  regionalData: any[];
  gwpHorizon: string;
  activeGwpStandard: string;
}

/** Five-year intensity trend as a line chart or a region x year heatmap. */
export const TrendSection: React.FC<TrendSectionProps> = ({ view, onView, trendChartData, rawTrendData, regionalData, gwpHorizon, activeGwpStandard }) => {
  const g20 = gwpHorizon === "20";
  const rows: HeatmapRow[] = useMemo(() => {
    const regionMap = new Map<string, { id: any; name: string; facIds: any[] }>();
    regionalData.forEach((fac) => {
      const regName = fac.region || fac.facility_name;
      if (!regionMap.has(regName)) {
        regionMap.set(regName, { id: fac.facility_id, name: regName, facIds: [] });
      }
      regionMap.get(regName)!.facIds.push(fac.facility_id);
    });

    return Array.from(regionMap.values()).map((reg) => ({
      id: reg.id,
      name: reg.name,
      cells: rawTrendData.map((y) => {
        const records = y.data.filter((r: any) => reg.facIds.includes(r.facility_id));
        let totalEmissions = 0;
        let totalBoe = 0;
        records.forEach((record: any) => {
          const boe = record.total_boe || 0;
          const intVal = g20 ? record.co2_intensity_gwp20 || record.co2_intensity : record.co2_intensity;
          if (boe > 0 && intVal != null) {
            totalEmissions += intVal * boe;
            totalBoe += boe;
          } else if (intVal != null && records.length === 1) {
            totalEmissions = intVal;
            totalBoe = 1;
          }
        });
        const raw = totalBoe > 0 ? totalEmissions / totalBoe : 0;
        const value = Number.isFinite(Number(raw)) ? Number(raw) : 0;
        return { key: y.year, value, title: `${y.year} Intensity: ${value.toFixed(3)} kg CO2e/BOE` };
      }),
    }));
  }, [regionalData, rawTrendData, g20]);
  return (
    <ChartCard
      className="trend-section"
      title={t("Historical Carbon Intensity Trends")}
      subtitle={t("5-Year Performance Track (kg CO₂e / BOE)")}
      actions={
        <SegmentedControl
          label={t("Trend view")}
          value={view}
          onChange={onView}
          options={[
            { value: "chart", className: "view-btn", label: <span className="inline-flex items-center gap-1.5"><BarChart2 className="size-4" aria-hidden="true" />{" "}{t("Chart")}</span> },
            { value: "heatmap", className: "view-btn", label: <span className="inline-flex items-center gap-1.5"><Grid className="size-4" aria-hidden="true" />{" "}{t("Heatmap")}</span> },
          ]}
        />
      }
    >
      {view === "chart" ? (
        <div>
          <LineChart
            data={trendChartData}
            xKey="year"
            series={[
              { key: "co2_100", color: "var(--color-brand-700)", name: t("GHG Intensity ({{standard}} 100-Yr GWP)", { standard: activeGwpStandard }) },
              { key: "co2_20", color: "var(--color-legacy-ea580c)", name: t("GHG Intensity ({{standard}} 20-Yr GWP)", { standard: activeGwpStandard }), dash: "5 5" },
            ]}
          />
        </div>
      ) : (
        <Heatmap years={rawTrendData.map((d) => d.year)} rows={rows} />
      )}
    </ChartCard>
  );
};
