import React, { useState, useEffect, useMemo } from "react";
import { ArrowLeft, ArrowRight, Search, Layers, ChevronRight } from "lucide-react";
import { Card } from "../../ui/Card";
import { Badge } from "../../ui/Badge";
import { BarChart as BarChartWrapper } from "../../components/charts";
import { formatCompactNumber } from "../../utils/formatters";
import { recordsLink } from "../../utils/reportLinks";
import { useNavigate } from "react-router-dom";
import api from "../../api";
import { t } from "../../i18n";

export interface SourceEquipmentCardProps {
  title: string;
  data: Array<{
    name: string;
    value: number;
    color?: string;
    [key: string]: any;
  }>;
  year?: string;
  facilityId?: string;
  activity?: string;
  division?: string;
  segment?: string;
  includePending?: boolean;
}

interface EquipmentItem {
  equipment_id: string;
  name: string;
  facility_id?: number | string;
  emissions: number;
  ch4_emissions?: number;
  record_count?: number;
  share_pct?: number;
}

interface EquipmentResponse {
  source: string;
  total_emissions: number;
  total_equipment_count: number;
  equipment: EquipmentItem[];
  other_emissions: number;
  other_count: number;
  other_share_pct: number;
  unassigned_emissions: number;
  unassigned_count: number;
  unassigned_share_pct: number;
}

const PALETTE = [
  "var(--color-brand-500)",
  "var(--color-blue-600)",
  "var(--color-green-500)",
  "var(--color-violet-500)",
  "var(--color-amber-500)",
  "var(--color-cyan-500)",
  "var(--color-teal-600)",
];

export const SourceEquipmentCard: React.FC<SourceEquipmentCardProps> = ({
  title,
  data,
  year = "all",
  facilityId = "all",
  activity = "all",
  division = "all",
  segment = "all",
  includePending = false,
}) => {
  const navigate = useNavigate();
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [equipmentData, setEquipmentData] = useState<EquipmentResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    if (!selectedSource) {
      setEquipmentData(null);
      return;
    }

    let isMounted = true;
    const fetchEquipment = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.set("source", selectedSource.toLowerCase());
        if (year && year !== "all") params.set("year", year);
        if (facilityId && facilityId !== "all") params.set("facilityId", facilityId);
        if (activity && activity !== "all") params.set("activity", activity);
        if (division && division !== "all") params.set("division", division);
        if (segment && segment !== "all") params.set("segment", segment);
        if (includePending) params.set("includePending", "true");

        const res = await api.get(`/dashboard/equipment-emissions?${params.toString()}`);
        if (isMounted) {
          setEquipmentData(res.data);
        }
      } catch (err) {
        if (isMounted) {
          console.error("Failed to load equipment breakdown:", err);
          setEquipmentData(null);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchEquipment();
    return () => {
      isMounted = false;
    };
  }, [selectedSource, year, facilityId, activity, division, segment, includePending]);

  // Stage 2: Transform equipment items into chart bars
  const equipmentBars = useMemo(() => {
    if (!equipmentData) return [];

    let list = equipmentData.equipment || [];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (eq) =>
          eq.equipment_id.toLowerCase().includes(q) ||
          (eq.name && eq.name.toLowerCase().includes(q)),
      );
      return list.map((eq, i) => ({
        name: eq.name && eq.name !== eq.equipment_id ? `${eq.equipment_id} (${eq.name})` : eq.equipment_id,
        equipment_id: eq.equipment_id,
        value: eq.emissions,
        facility_id: eq.facility_id,
        color: PALETTE[i % PALETTE.length],
      }));
    }

    const bars = list.map((eq, i) => ({
      name: eq.name && eq.name !== eq.equipment_id ? `${eq.equipment_id} (${eq.name})` : eq.equipment_id,
      equipment_id: eq.equipment_id,
      value: eq.emissions,
      facility_id: eq.facility_id,
      color: PALETTE[i % PALETTE.length],
    }));

    if (equipmentData.other_emissions > 0) {
      bars.push({
        name: t("Other ({{count}} assets)", { count: equipmentData.other_count }),
        equipment_id: "",
        value: equipmentData.other_emissions,
        facility_id: undefined,
        color: "var(--color-ink-400, #94a3b8)",
      });
    }

    if (equipmentData.unassigned_emissions > 0) {
      bars.push({
        name: t("Unassigned / General"),
        equipment_id: "",
        value: equipmentData.unassigned_emissions,
        facility_id: undefined,
        color: "var(--color-ink-300, #cbd5e1)",
      });
    }

    return bars;
  }, [equipmentData, searchQuery]);

  // Handle click on equipment row (opens records table)
  const handleEquipmentSelect = (row: any) => {
    if (row && row.equipment_id) {
      navigate(
        recordsLink({
          facilityId: row.facility_id || (facilityId !== "all" ? facilityId : undefined),
          year: year !== "all" ? year : undefined,
          process: selectedSource?.toLowerCase(),
          search: row.equipment_id,
        }),
      );
    }
  };

  return (
    <Card data-testid="emissions-by-source-card" className="min-w-0 transition-all duration-200">
      {/* Header */}
      <div className="mb-2 flex items-center justify-between gap-2">
        {!selectedSource ? (
          <div>
            <div className="flex items-center gap-2">
              <h3 className="m-0 text-md font-bold text-ink-800">{title}</h3>
              <Badge tone="brand" className="gap-1 text-[10px] py-0 px-1.5 font-medium">
                <Layers className="size-3" />
                {t("Clickable Drilldown")}
              </Badge>
            </div>
            <p className="m-0 mt-0.5 text-xs text-ink-600">
              {t("Click any source bar to drill down into equipment")}
            </p>
          </div>
        ) : (
          <div className="flex w-full items-center justify-between gap-1.5">
            <div className="flex items-center gap-1.5 min-w-0 flex-1">
              <button
                type="button"
                onClick={() => {
                  setSelectedSource(null);
                  setSearchQuery("");
                }}
                className="inline-flex items-center gap-1 rounded-md border border-border bg-surface px-2 py-0.5 text-xs font-semibold text-brand-600 hover:bg-brand-50 hover:border-brand-300 transition-colors shrink-0 shadow-xs"
                title={t("Back to all sources")}
              >
                <ArrowLeft className="size-3.5" />
                <span>{t("All Sources")}</span>
              </button>
              <ChevronRight className="size-3.5 text-ink-400 shrink-0" />
              <h3 className="m-0 text-xs font-bold text-ink-800 truncate" title={`${selectedSource} ${t("Equipment")}`}>
                {selectedSource} {t("Equipment")}
              </h3>
            </div>

            <div className="relative shrink-0">
              <Search className="size-3 absolute left-2 top-2 text-ink-400 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t("Filter tag...")}
                className="h-6 w-24 focus:w-32 transition-all rounded-md border border-border bg-surface pl-6 pr-2 text-xs text-text placeholder:text-ink-400 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
        )}
      </div>

      {/* Sub-header / Status Description for Stage 2 */}
      {selectedSource && (
        <p className="m-0 mb-2 text-xs text-ink-600">
          {loading
            ? t("Loading equipment emissions...")
            : equipmentData
            ? t("Showing top emitters • Total: {{total}} tCO₂e • Click bar to view records", {
                total: formatCompactNumber(equipmentData.total_emissions),
              })
            : t("No equipment breakdown available")}
        </p>
      )}

      {/* Chart Body */}
      <div className="relative h-[195px] w-full min-w-0">
        {!selectedSource ? (
          <BarChartWrapper
            data={data}
            dataKey="value"
            xKey="name"
            height={195}
            horizontal
            sortDesc
            showShare
            showLegend={false}
            formatValue={formatCompactNumber}
            onSelect={(row) => setSelectedSource(row.name)}
            selectLabel={(row) => t("Drill down into {{name}} equipment", { name: row.name })}
            exportName="emissions-by-source"
          />
        ) : loading ? (
          <div className="flex h-full w-full items-center justify-center text-xs text-ink-500">
            {t("Loading equipment data...")}
          </div>
        ) : equipmentBars.length > 0 ? (
          <BarChartWrapper
            data={equipmentBars}
            dataKey="value"
            xKey="name"
            height={195}
            horizontal
            sortDesc
            showShare
            showLegend={false}
            formatValue={formatCompactNumber}
            onSelect={handleEquipmentSelect}
            selectLabel={(row) =>
              row.equipment_id ? t("Open records for {{name}}", { name: row.name }) : row.name
            }
            exportName={`${selectedSource.toLowerCase()}-equipment-emissions`}
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-xs text-ink-500">
            <span>{t("No equipment matching filter")}</span>
            <button
              type="button"
              onClick={() => {
                setSelectedSource(null);
                setSearchQuery("");
              }}
              className="text-brand-600 underline"
            >
              {t("Return to Sources")}
            </button>
          </div>
        )}
      </div>
    </Card>
  );
};

export default SourceEquipmentCard;
