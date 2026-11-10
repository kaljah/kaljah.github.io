import React, { useEffect } from "react";
import { Wind, Droplets, Layers, Zap } from "lucide-react";
import { Input, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import CustomDropdown from "../CustomDropdown";
import { API_FACTORS } from "../../utils/EmissionFactors";
import { t } from "../../i18n";

const ALL_UNITS = [
  { value: "m3", label: "m³" },
  { value: "scf", label: t("scf") },
  { value: "Mcf", label: t("Mcf") },
  { value: "MMscf", label: t("MMscf") },
  { value: "gal", label: t("gal") },
  { value: "bbl", label: t("bbl") },
  { value: "L", label: "L" },
  { value: "kg", label: t("kg") },
  { value: "short_ton", label: t("ton (short)") },
  { value: "tonne", label: t("tonne (metric)") },
  { value: "events", label: t("events") },
];
const UNIT_FAMILIES: Record<string, string[]> = {
  gas: ["m3", "scf", "Mcf", "MMscf"],
  liquid: ["m3", "gal", "bbl", "L"],
  solid: ["kg", "short_ton", "tonne"],
  event: ["events"],
};

// Units that can be applied to the selected catalog factor without a density (browser test F6:
// coal was offered m³, gases were offered kg and events)
function unitFamily(factor: any): string | null {
  if (!factor) return null;
  const base = String(factor.baseUnit || "").toLowerCase();
  const type = String(factor.type || "").toLowerCase();
  const unit = String(factor.unit || "").toLowerCase();
  if (["ton", "short_ton", "tonne", "kg", "lb"].includes(base) || type === "solids") return "solid";
  if (["gal", "bbl", "l"].includes(base) || type === "liquids") return "liquid";
  if (["scf", "m3", "mcf"].includes(base) || type === "gases" || /\/(m³|m3|scf|mcf)/.test(unit)) return "gas";
  if (unit.includes("event")) return "event";
  if (unit.includes("bbl")) return "liquid";
  return null;
}

// Process types that require HHV input per API Compendium 2021 Section 5
const HHV_REQUIRED_PROCESSES = [
  "combustion",
  "stationary_combustion",
  "flaring",
  "routine_flaring",
  "non_routine_flaring",
  "safety_flaring",
];

export interface Scope1SubFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
  sourceType?: string;
}

export const CombustionForm: React.FC<Scope1SubFormProps> = ({ data, onChange, sourceType }) => {
  const isFlaring = ["flaring", "routine_flaring", "non_routine_flaring", "safety_flaring"].includes(data.process_type);
  const isCombustion = ["combustion", "stationary_combustion"].includes(data.process_type);
  const needsHHV = HHV_REQUIRED_PROCESSES.includes(data.process_type);
  const family = sourceType === "library" ? null : unitFamily((API_FACTORS as Record<string, any>)[data.fuel]);
  const unitOptions = family ? ALL_UNITS.filter((u) => UNIT_FAMILIES[family].includes(u.value)) : ALL_UNITS;

  // a unit left over from another factor that cannot apply to this one is cleared
  useEffect(() => {
    if (family && data.unit && !UNIT_FAMILIES[family].includes(data.unit)) onChange("unit", undefined);
  }, [family, data.unit, onChange]);

  return (
    <div className="combustion-form">
      {family && (
        <div className="mb-2.5 flex items-center gap-2">
          <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
            {t("Fuel Form:")}
          </span>
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
              family === "gas"
                ? "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border border-blue-200"
                : family === "liquid"
                ? "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border border-amber-200"
                : family === "solid"
                ? "bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border border-slate-300"
                : "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300 border border-purple-200"
            }`}
          >
            {family === "gas" ? (
              <>
                <Wind size={12} className="shrink-0 text-blue-700 dark:text-blue-300" aria-hidden="true" />
                <span>{t("Gas Fuel")}</span>
              </>
            ) : family === "liquid" ? (
              <>
                <Droplets size={12} className="shrink-0 text-amber-700 dark:text-amber-300" aria-hidden="true" />
                <span>{t("Liquid Fuel")}</span>
              </>
            ) : family === "solid" ? (
              <>
                <Layers size={12} className="shrink-0 text-slate-700 dark:text-slate-300" aria-hidden="true" />
                <span>{t("Solid Fuel")}</span>
              </>
            ) : (
              <>
                <Zap size={12} className="shrink-0 text-purple-700 dark:text-purple-300" aria-hidden="true" />
                <span>{t("Event")}</span>
              </>
            )}
          </span>
        </div>
      )}
      <div className="form-grid-2">
        <Field
          className="input-group"
          label={
            <>
              {isFlaring
                ? t("Gas Volume Flared")
                : data.process_type === "loading"
                ? t("Volume Loaded")
                : data.process_type === "separation"
                ? t("Volume treated")
                : t("Quantity")}
            </>
          }
        >
          <Input
            type="number"
            min="0"
            value={data.amount || ""}
            onChange={(e) => onChange("amount", e.target.value)}
            placeholder="0.00"
          />
        </Field>

        <div className="input-group">
          <label>{t("Unit")}</label>
          <CustomDropdown
            options={unitOptions}
            value={data.unit}
            onChange={(val) => onChange("unit", val)}
          />
        </div>
      </div>

      {/* HHV — required in specific (Tier 3) mode */}
      {needsHHV && sourceType === "specific" && (
        <div className="[margin-bottom:12px] mt-[14px]!">
          <div className="form-grid-2 gap-[10px]!">
            <div className="input-group mb-[0px]!">
              <label className="block text-sm font-medium text-text mb-1.5">
                HHV
                <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
              </label>
              <Input
                id="hhv-input"
                type="number"
                min="0"
                value={data.hhv || ""}
                onChange={(e) => onChange("hhv", e.target.value)}
                placeholder={isFlaring ? t("e.g. 983 (natural gas)") : t("e.g. 1020 (BTU/scf)")}
                className={`${!data.hhv ? "[border-color:var(--color-legacy-fbbf24)]!" : "[border-color:var(--color-legacy-d1fae5)]!"}`}
              />
            </div>
            <div className="input-group mb-[0px]!">
              <label className="block text-sm font-medium text-text mb-1.5">{t("HHV Unit")}</label>
              <NativeSelect
                wrapperClassName="w-36 shrink-0"
                className="h-10 text-sm font-medium"
                value={data.hhv_unit || "BTU/scf"}
                onChange={(e) => onChange("hhv_unit", e.target.value)}
              >
                <option value="BTU/scf">BTU/scf</option>
                <option value="BTU/ft3">BTU/ft³</option>
                <option value="MJ/m3">MJ/m³</option>
                <option value="MJ/kg">MJ/kg</option>
                <option value="BTU/gal">BTU/gal</option>
                <option value="BTU/lb">BTU/lb</option>
                <option value="kcal/m3">kcal/m³</option>
              </NativeSelect>
            </div>
          </div>

          {/* Combustion efficiency — required for stationary combustion */}
          {isCombustion && (
            <div className="input-group mt-[10px]! mb-[0px]!">
              <label className="block text-sm font-medium text-text mb-1.5">
                {t("Combustion efficiency")}
                <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
              </label>
              <div className="flex! gap-[8px]! items-center!">
                <Input
                  id="combustion-efficiency-input"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={data.combustion_efficiency != null ? data.combustion_efficiency : ""}
                  onChange={(e) => onChange("combustion_efficiency", e.target.value)}
                  placeholder="e.g. 99.5"
                  style={{
                    flex: 1,
                    borderColor: data.combustion_efficiency == null ? "var(--color-legacy-fbbf24)" : "var(--color-legacy-d1fae5)",
                  }}
                />
                <span className="text-sm font-medium text-text-secondary whitespace-nowrap!">%</span>
              </div>
            </div>
          )}

          {/* Flare type & CH4 content for flaring */}
          {isFlaring && (
            <div className="form-grid-2 gap-[10px]! mt-[10px]!">
              <div className="input-group mb-[0px]!">
                <label className="block text-sm font-medium text-text mb-1.5">{t("Flare Type")}</label>
                <NativeSelect
                  id="flare-type-select"
                  aria-label={t("Flare Type")}
                  className="h-10 text-sm font-medium"
                  value={data.flare_type || "elevated"}
                  onChange={(e) => onChange("flare_type", e.target.value)}
                >
                  <option value="elevated">{t("Elevated (2 % CH₄ unburnt)")}</option>
                  <option value="enclosed_ground">{t("Enclosed ground (0.5 % CH₄ unburnt)")}</option>
                  <option value="pit">{t("Pit / open burn (2 % CH₄ unburnt)")}</option>
                </NativeSelect>
              </div>
              <div className="input-group mb-[0px]!">
                <label className="block text-sm font-medium text-text mb-1.5">
                  {t("CH₄ (%)")}
                  <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
                </label>
                <Input
                  id="flare-ch4-input"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={data.ch4_content !== undefined ? data.ch4_content : ""}
                  onChange={(e) => onChange("ch4_content", e.target.value)}
                  placeholder="e.g. 85.0"
                />
              </div>
              {/* measured efficiencies; blank = API Compendium 2021 defaults as corrected in December 2025
                  (96.5 % to CO2; CH4 98 %, 99.5 % at facilities registered as Downstream) */}
              <div className="input-group mb-[0px]!">
                <label className="block text-sm font-medium text-text mb-1.5">{t("Combustion efficiency (% carbon to CO₂)")}</label>
                <Input
                  id="flare-combustion-efficiency-input"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={data.combustion_efficiency != null ? data.combustion_efficiency : ""}
                  onChange={(e) => onChange("combustion_efficiency", e.target.value)}
                  placeholder={t("blank = 96.5")}
                />
              </div>
              <div className="input-group mb-[0px]!">
                <label className="block text-sm font-medium text-text mb-1.5">{t("Destruction efficiency (% CH₄ destroyed)")}</label>
                <Input
                  id="flare-destruction-efficiency-input"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={data.destruction_efficiency != null ? data.destruction_efficiency : ""}
                  onChange={(e) => onChange("destruction_efficiency", e.target.value)}
                  placeholder={t("blank = 98 (99.5 at Downstream facilities)")}
                />
              </div>
            </div>
          )}

          {/* Operating conditions: a gas volume in m3 / cf read at these conditions is
              converted to standard conditions (scf and Sm3 are already standard) */}
          <div className="form-grid-2 gap-[10px]! mt-[10px]!">
            <div className="input-group mb-[0px]!">
              <label className="block text-sm font-medium text-text mb-1.5">{t("Operating Temp (°F)")}</label>
              <Input
                type="number"
                value={data.operating_temperature !== undefined ? data.operating_temperature : ""}
                onChange={(e) => {
                  onChange("operating_temperature", e.target.value);
                  onChange("temp_unit", "F"); // the unit shown on the label
                }}
                placeholder={t("Def: 60°F")}
              />
            </div>
            <div className="input-group mb-[0px]!">
              <label className="block text-sm font-medium text-text mb-1.5">{t("Pressure (psia)")}</label>
              <Input
                type="number"
                value={data.operating_pressure !== undefined ? data.operating_pressure : ""}
                onChange={(e) => {
                  onChange("operating_pressure", e.target.value);
                  onChange("press_unit", "psia"); // the unit shown on the label
                }}
                placeholder={t("Def: 14.696")}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CombustionForm;
