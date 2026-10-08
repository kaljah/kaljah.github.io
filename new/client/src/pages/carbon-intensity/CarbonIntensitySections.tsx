import React from "react";
import { useNavigate } from "react-router-dom";
import { recordsLink } from "../../utils/reportLinks";
import { BarChart2, FileText, Grid } from "lucide-react";
import { Badge, SegmentedControl } from "../../ui";
import { BarChart, LineChart } from "../../components/charts";
import { formatNumber } from "../../utils/formatters";
import { ChartCard, Heatmap, type HeatmapRow } from "../intensity/IntensityParts";

const th = "whitespace-nowrap border-b-2 border-border px-4 py-3 text-left text-sm font-semibold uppercase tracking-wide text-text-secondary";
const td = "border-b border-border px-4 py-3.5 text-text";

const pick = (obj: any, a: string, b: string) => obj?.[a] ?? obj?.[b];

export interface CbamSectionProps {
  products: any[];
  facilities: { id: string | number; name: string; [key: string]: any }[];
}

/** EU CBAM product-specific embedded emissions table (rows come from /data/cbam-exports). */
export const CbamSection: React.FC<CbamSectionProps> = ({ products, facilities }) => (
  <ChartCard
    className="cbam-section"
    title={
      <span className="flex items-center gap-2">
        <FileText className="size-5 text-brand-500" aria-hidden="true" /> EU CBAM Product Specific Embedded Emissions
      </span>
    }
    subtitle="Direct & indirect specific embedded emissions per export product (EU Regulation 2023/956)"
    actions={<Badge tone="brand" className="cbam-benchmark-badge px-3.5 py-1.5 text-sm">EU ETS Benchmark (Product-Specific): ~0.025 - 1.2 tCO₂e/t</Badge>}
  >
    {products.length > 0 ? (
      <div className="overflow-x-auto">
        <table className="custom-table w-full border-collapse text-base">
          <thead>
            <tr>
              {["Facility", "Product Name", "EU CN Code", "Period", "Export Qty (t)", "Destination", "Direct Intensity (tCO₂e/t)", "Indirect Intensity (tCO₂e/t)", "Total Embedded (tCO₂e)"].map((h) => (
                <th key={h} scope="col" className={th}>
                  {h}
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
              const total = p.totalEmbeddedEmissions ?? p.total_embedded_emissions ?? qty * ((direct || 0) + (indirect || 0));
              return (
                <tr key={p.id || idx} className="hover:bg-ink-100">
                  <td className={`${td} font-semibold`}>{fac ? fac.name : p.facilityName || p.facility_name || "—"}</td>
                  <td className={td}>{pick(p, "productName", "product_name") || "—"}</td>
                  <td className={td}>
                    <span className="code-pill rounded-sm border border-border bg-ink-100 px-2 py-0.5 font-mono text-sm">{pick(p, "cnCode", "cn_code") || "—"}</span>
                  </td>
                  <td className={td}>
                    {p.year}-{String(p.month || 1).padStart(2, "0")}
                  </td>
                  <td className={td}>{formatNumber(qty, 0)}</td>
                  <td className={td}>{pick(p, "exportDestination", "export_destination") || "EU"}</td>
                  <td className={td}>
                    <strong className="text-brand-700">{typeof direct === "number" ? direct.toFixed(4) : "—"}</strong>
                  </td>
                  <td className={td}>{typeof indirect === "number" ? indirect.toFixed(4) : "—"}</td>
                  <td className={td}>
                    <strong>{formatNumber(total, 1)}</strong>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    ) : (
      <p className="m-0 px-5 py-10 text-center text-base text-text-secondary">
        No CBAM product export records registered for the selected filters. Track exports via <strong>Manage Data &gt; CBAM Products</strong>.
      </p>
    )}
  </ChartCard>
);

const GAS_TO_BOE = 0.178;

export interface RegionalChartsProps {
  data: any[];
  gwpHorizon: string;
  year?: string;
}

/** Four per-facility bar charts: intensity, scope 1 vs 2, oil BOE and gas BOE. */
export const RegionalCharts: React.FC<RegionalChartsProps> = ({ data, gwpHorizon, year }) => {
  const g20 = gwpHorizon === "20";
  const navigate = useNavigate();
  const openRecords = (r: any) => navigate(recordsLink({ facilityId: r.id, year }));
  const named = (fn: (d: any) => any) => data.map((d) => ({ id: d.facility_id, name: d.facility_name, ...fn(d) }));
  return (
    <div className="chart-grid grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(min(100%,450px),1fr))]">
      <ChartCard className="card" title="GHG Intensity by Facility (kg CO₂e / BOE)" rule="var(--color-brand-500)">
        <BarChart data={named((d) => ({ value: g20 ? d.co2_intensity_gwp20 || d.co2_intensity : d.co2_intensity }))} dataKey="value" xKey="name" horizontal sortDesc onSelect={openRecords} selectLabel={(r) => `Open ${r.name} records`} exportName="ghg-intensity-by-facility" color="var(--color-brand-500)" />
      </ChartCard>
      <ChartCard className="card" title="Scope 1 Direct vs Scope 2 Intensity" rule="var(--color-blue-600)">
        <BarChart
            data={named((d) => ({
              scope1: Number(((g20 ? d.scope1_intensity_gwp20 || d.scope1_intensity : d.scope1_intensity) || 0).toFixed(2)),
              scope2: Number((d.scope2_intensity || 0).toFixed(2)),
            }))}
            bars={[
              { dataKey: "scope1", name: g20 ? "Scope 1 (GWP₂₀ Direct)" : "Scope 1 (Direct)", color: "var(--color-blue-600)" },
              { dataKey: "scope2", name: "Scope 2 (Indirect)", color: "var(--color-legacy-0ea5e9)" },
            ]}
            xKey="name"
            exportName="scope1-vs-scope2-intensity-by-facility"
          />
      </ChartCard>
      <ChartCard className="card" title="Oil BOE Contribution by Facility" rule="var(--color-legacy-ea580c)">
        <BarChart data={named((d) => ({ value: d.total_oil || 0 }))} dataKey="value" xKey="name" horizontal sortDesc onSelect={openRecords} selectLabel={(r) => `Open ${r.name} records`} exportName="oil-boe-by-facility" color="var(--color-legacy-ea580c)" />
      </ChartCard>
      <ChartCard className="card" title="Gas BOE Contribution by Facility" rule="var(--color-violet-500)">
        <BarChart data={named((d) => ({ value: (d.total_gas || 0) * GAS_TO_BOE }))} dataKey="value" xKey="name" horizontal sortDesc onSelect={openRecords} selectLabel={(r) => `Open ${r.name} records`} exportName="gas-boe-by-facility" color="var(--color-violet-500)" />
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

/** Five-year intensity trend as a line chart or a facility x year heatmap. */
export const TrendSection: React.FC<TrendSectionProps> = ({ view, onView, trendChartData, rawTrendData, regionalData, gwpHorizon, activeGwpStandard }) => {
  const g20 = gwpHorizon === "20";
  const rows: HeatmapRow[] = regionalData.map((fac) => ({
    id: fac.facility_id,
    name: fac.facility_name,
    cells: rawTrendData.map((y) => {
      const record = y.data.find((r: any) => r.facility_id === fac.facility_id);
      const raw = record ? (g20 ? record.co2_intensity_gwp20 || record.co2_intensity : record.co2_intensity) : 0;
      const value = Number.isFinite(Number(raw)) ? Number(raw) : 0;
      return { key: y.year, value, title: `${y.year} Intensity: ${value.toFixed(3)} kg CO2e/BOE` };
    }),
  }));
  return (
    <ChartCard
      className="trend-section"
      title="Historical Carbon Intensity Trends"
      subtitle="5-Year Performance Track (kg CO₂e / BOE)"
      actions={
        <SegmentedControl
          label="Trend view"
          value={view}
          onChange={onView}
          options={[
            { value: "chart", className: "view-btn", label: <span className="inline-flex items-center gap-1.5"><BarChart2 className="size-4" aria-hidden="true" /> Chart</span> },
            { value: "heatmap", className: "view-btn", label: <span className="inline-flex items-center gap-1.5"><Grid className="size-4" aria-hidden="true" /> Heatmap</span> },
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
              { key: "co2_100", color: "var(--color-brand-700)", name: `GHG Intensity (${activeGwpStandard} 100-Yr GWP)` },
              { key: "co2_20", color: "var(--color-legacy-ea580c)", name: `GHG Intensity (${activeGwpStandard} 20-Yr GWP)`, dash: "5 5" },
            ]}
          />
        </div>
      ) : (
        <Heatmap years={rawTrendData.map((d) => d.year)} rows={rows} />
      )}
    </ChartCard>
  );
};
