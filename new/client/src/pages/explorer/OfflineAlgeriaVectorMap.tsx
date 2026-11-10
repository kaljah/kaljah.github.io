import React, { useMemo, useState, useEffect } from "react";
import { Plus, Minus, RotateCcw, Flame } from "lucide-react";
import { ALGERIA_BORDER_GEOJSON, ALGERIA_BOUNDS } from "../../data/algeriaBoundary";
import { cn } from "../../ui";
import { t } from "../../i18n";

const SVG_W = 800;
const SVG_H = 720;
const PAD = 36;
const MIN_LAT = ALGERIA_BOUNDS[0][0];
const MAX_LAT = ALGERIA_BOUNDS[1][0];
const MIN_LON = ALGERIA_BOUNDS[0][1];
const MAX_LON = ALGERIA_BOUNDS[1][1];

export function projectAlgeriaCoord(lat: number, lon: number): { x: number; y: number } {
  const x = PAD + ((lon - MIN_LON) / (MAX_LON - MIN_LON)) * (SVG_W - 2 * PAD);
  const y = PAD + ((MAX_LAT - lat) / (MAX_LAT - MIN_LAT)) * (SVG_H - 2 * PAD);
  return { x, y };
}

export interface OfflineFacilityMarker {
  id: number | string;
  name: string;
  code?: string;
  latitude?: number | string;
  longitude?: number | string;
  region?: string;
  activity?: string;
  division?: string;
  [key: string]: any;
}

export interface OfflineAlgeriaVectorMapProps {
  facilities: OfflineFacilityMarker[];
  selectedFacilityId?: number | string | null;
  centeredFacility?: OfflineFacilityMarker | null;
  zoomNonce?: number;
  isDrawerOpen?: boolean;
  viewMode: string;
  showPlumeRings: boolean;
  getStats: (facilityId: number | string) => {
    total_ch4?: number;
    total_co2e?: number;
    [key: string]: any;
  };
  getSeverity: (val: number) => string;
  formatCompact: (val: any) => string;
  onSelectFacility: (facility: any) => void;
}

const OfflineAlgeriaVectorMap: React.FC<OfflineAlgeriaVectorMapProps> = ({
  facilities,
  selectedFacilityId,
  centeredFacility,
  zoomNonce = 0,
  isDrawerOpen = true,
  viewMode,
  showPlumeRings,
  getStats,
  getSeverity,
  formatCompact,
  onSelectFacility,
}) => {
  const [zoom, setZoom] = useState<number>(1);
  const [focusCoord, setFocusCoord] = useState<{ x: number; y: number }>({
    x: SVG_W / 2,
    y: SVG_H / 2,
  });

  useEffect(() => {
    if (!centeredFacility) return;
    const lat = Number(centeredFacility.latitude);
    const lon = Number(centeredFacility.longitude);
    if (!Number.isNaN(lat) && !Number.isNaN(lon)) {
      setFocusCoord(projectAlgeriaCoord(lat, lon));
      setZoom((prev) => (prev < 1.6 ? 1.8 : prev));
    }
  }, [centeredFacility, zoomNonce]);

  const algeriaOutlinePath = useMemo(() => {
    const ring = ALGERIA_BORDER_GEOJSON.geometry.coordinates[0] || [];
    if (!ring.length) return "";
    return (
      ring
        .map(([lon, lat], idx) => {
          const { x, y } = projectAlgeriaCoord(lat, lon);
          return `${idx === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ") + " Z"
    );
  }, []);

  const latGrid = [20, 25, 30, 35].map((lat) => ({
    lat,
    y: projectAlgeriaCoord(lat, 0).y,
  }));
  const lonGrid = [-5, 0, 5, 10].map((lon) => ({
    lon,
    x: projectAlgeriaCoord(28, lon).x,
  }));

  const vbW = SVG_W / zoom;
  const vbH = SVG_H / zoom;
  const halfW = vbW / 2;
  const halfH = vbH / 2;
  const clampedCx = Math.max(halfW, Math.min(SVG_W - halfW, focusCoord.x));
  const clampedCy = Math.max(halfH, Math.min(SVG_H - halfH, focusCoord.y));
  const vbX = clampedCx - halfW;
  const vbY = clampedCy - halfH;

  const plottedFacilities = useMemo(() => {
    return facilities
      .filter((f) => {
        const lat = Number(f.latitude);
        const lon = Number(f.longitude);
        return !Number.isNaN(lat) && !Number.isNaN(lon) && lat !== 0 && lon !== 0;
      })
      .map((fac) => {
        const lat = Number(fac.latitude);
        const lon = Number(fac.longitude);
        const { x, y } = projectAlgeriaCoord(lat, lon);
        const st = getStats(fac.id);
        const val = viewMode === "total" ? Number(st.total_co2e || 0) : Number(st.total_ch4 || 0);
        const severity = getSeverity(val);
        return {
          fac,
          x,
          y,
          val,
          severity,
          isSelected: selectedFacilityId != null && Number(selectedFacilityId) === Number(fac.id),
        };
      });
  }, [facilities, getStats, viewMode, getSeverity, selectedFacilityId]);

  const handleResetView = () => {
    setZoom(1);
    setFocusCoord({ x: SVG_W / 2, y: SVG_H / 2 });
  };

  return (
    <div
      data-testid="offline-vector-map"
      role="region"
      aria-label={t("Offline Algeria vector boundary map")}
      className={cn(
        "relative flex h-full w-full items-center justify-center overflow-hidden bg-ink-100 p-4 pt-[76px] transition-[padding] duration-300",
        isDrawerOpen && "md:pl-[364px]",
      )}
    >
      <div className="relative flex h-full w-full items-center justify-center [container-type:size]">
        <div
          className="relative overflow-hidden rounded-xl border border-border/80 bg-ink-50/70 shadow-sm"
          style={{
            width: "min(96cqw, calc(96cqh * 800 / 720))",
            height: "min(96cqh, calc(96cqw * 720 / 800))",
          }}
        >
          <svg
            aria-hidden="true"
            viewBox={`${vbX.toFixed(1)} ${vbY.toFixed(1)} ${vbW.toFixed(1)} ${vbH.toFixed(1)}`}
            preserveAspectRatio="none"
            className="block h-full w-full"
          >
            {/* Subtle coordinate graticule */}
            <g stroke="#cbd5e1" strokeWidth={0.8 / zoom} strokeDasharray="4 4" opacity={0.7}>
              {latGrid.map((g) => (
                <line key={`lat-${g.lat}`} x1={PAD} y1={g.y} x2={SVG_W - PAD} y2={g.y} />
              ))}
              {lonGrid.map((g) => (
                <line key={`lon-${g.lon}`} x1={g.x} y1={PAD} x2={g.x} y2={SVG_H - PAD} />
              ))}
            </g>

            {/* Graticule labels */}
            <g fill="#64748b" fontSize={10 / zoom} fontFamily="monospace">
              {latGrid.map((g) => (
                <text key={`lbl-lat-${g.lat}`} x={PAD + 4} y={g.y - 3}>
                  {g.lat}°N
                </text>
              ))}
              {lonGrid.map((g) => (
                <text key={`lbl-lon-${g.lon}`} x={g.x + 3} y={SVG_H - PAD - 4}>
                  {g.lon === 0 ? "0°" : g.lon > 0 ? `${g.lon}°E` : `${Math.abs(g.lon)}°W`}
                </text>
              ))}
            </g>

            {/* Bundled Algeria sovereign border outline */}
            <path
              data-testid="algeria-vector-outline"
              d={algeriaOutlinePath}
              fill="var(--color-surface, #ffffff)"
              fillOpacity={0.92}
              stroke="var(--color-brand-600, #ea580c)"
              strokeWidth={2 / zoom}
              strokeLinejoin="round"
            />

            {/* Optional severity halo rings */}
            {showPlumeRings &&
              plottedFacilities.map(({ fac, x, y, severity }) => {
                const color =
                  severity === "high"
                    ? "var(--color-red-500, #ef4444)"
                    : severity === "medium"
                      ? "var(--color-amber-500, #f59e0b)"
                      : "var(--color-green-500, #10b981)";
                const outerR = (severity === "high" ? 26 : severity === "medium" ? 18 : 12) / Math.sqrt(zoom);
                const innerR = outerR * 0.5;
                return (
                  <g key={`ring-${fac.id}`}>
                    <circle
                      cx={x}
                      cy={y}
                      r={outerR}
                      fill={color}
                      fillOpacity={0.1}
                      stroke={color}
                      strokeWidth={1 / zoom}
                      strokeDasharray={`${4 / zoom} ${5 / zoom}`}
                    />
                    <circle
                      cx={x}
                      cy={y}
                      r={innerR}
                      fill={color}
                      fillOpacity={0.22}
                      stroke={color}
                      strokeWidth={1.2 / zoom}
                    />
                  </g>
                );
              })}
          </svg>

          {/* Accessible interactive facility marker buttons positioned 1:1 with projected coordinates */}
          {plottedFacilities.map(({ fac, x, y, val, severity, isSelected }) => {
            const leftPct = ((x - vbX) / vbW) * 100;
            const topPct = ((y - vbY) / vbH) * 100;
            if (leftPct < -5 || leftPct > 105 || topPct < -5 || topPct > 105) {
              return null;
            }

            const dotClass =
              severity === "high"
                ? "bg-red-500"
                : severity === "medium"
                  ? "bg-amber-500"
                  : "bg-emerald-500";

            const metricText =
              viewMode === "methane"
                ? `${formatCompact(val)} tCH₄/yr`
                : `${formatCompact(val)} tCO₂e/yr`;

            return (
              <button
                key={fac.id}
                type="button"
                data-testid={`vector-marker-${fac.id}`}
                aria-label={`${fac.name} (${severity} severity)`}
                aria-pressed={isSelected}
                title={`${fac.name} — ${metricText}`}
                onClick={() => onSelectFacility(fac)}
                className="group absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer border-0 bg-transparent p-1 focus:outline-none"
                style={{ left: `${leftPct}%`, top: `${topPct}%` }}
              >
                <span
                  className={cn(
                    "block rounded-full border-2 border-white shadow-sm transition-transform group-hover:scale-125 group-focus-visible:ring-2 group-focus-visible:ring-brand-500",
                    dotClass,
                    severity === "high" ? "size-4" : severity === "medium" ? "size-3.5" : "size-3",
                    isSelected && "scale-125 border-brand-500 ring-4 ring-brand-500/25",
                  )}
                />
                <span
                  className={cn(
                    "pointer-events-none absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap rounded border border-border bg-surface/95 px-1.5 py-0.5 text-[11px] font-semibold text-text shadow-xs transition-opacity",
                    isSelected ? "opacity-100 border-brand-400" : "opacity-85 group-hover:opacity-100",
                  )}
                >
                  <span className="inline-flex items-center gap-1">
                    {fac.name}
                    {isSelected && (
                      <span className="inline-flex items-center gap-0.5 text-brand-700">
                        · <Flame className="size-2.5" aria-hidden="true" /> {metricText}
                      </span>
                    )}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Vector Zoom & Reset Controls */}
      <div className="absolute bottom-4 right-4 z-20 flex flex-col overflow-hidden rounded-lg border border-border bg-surface shadow-md">
        <button
          type="button"
          onClick={() => setZoom((z) => Math.min(3, Number((z + 0.5).toFixed(2))))}
          aria-label={t("Zoom in vector map")}
          title={t("Zoom in")}
          className="flex size-8 cursor-pointer items-center justify-center border-0 border-b border-border bg-surface text-text hover:bg-ink-50"
        >
          <Plus className="size-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={() => setZoom((z) => Math.max(1, Number((z - 0.5).toFixed(2))))}
          aria-label={t("Zoom out vector map")}
          title={t("Zoom out")}
          className="flex size-8 cursor-pointer items-center justify-center border-0 border-b border-border bg-surface text-text hover:bg-ink-50"
        >
          <Minus className="size-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={handleResetView}
          aria-label={t("Reset vector map view")}
          title={t("Reset view")}
          className="flex size-8 cursor-pointer items-center justify-center border-0 bg-surface text-text hover:bg-ink-50"
        >
          <RotateCcw className="size-3.5" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
};

export default OfflineAlgeriaVectorMap;
