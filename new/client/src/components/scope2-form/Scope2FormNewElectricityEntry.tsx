import React from "react";
import { Lock } from "lucide-react";
import { Input, Field, Badge } from "../../ui";
import CustomDropdown from "../CustomDropdown";
import { MARKET_INSTRUMENTS } from "./marketInstruments";
import { currentLanguage, t } from "../../i18n";
import { ACTIVITY_YEAR_MIN, activityYearMax } from "../../constants";

export interface Scope2FormNewElectricityEntryProps {
  activity: string;
  allocationMethod: string;
  amount: string | number;
  boilerEff: string | number;
  division: string;
  facilityId: string | number;
  field: string;
  getFacilityOptions: () => Array<{ value: string | number; label: string }>;
  getGridOptions: () => Array<{ value: string; label: string }>;
  gridRegion: string;
  handleAddEntry: (status: "Draft" | "Verified") => void;
  handleSourceTypeChange: (type: string) => void;
  heatEff: string | number;
  heatOutput: string | number;
  marketFactor: string;
  marketInstrument: string;
  month: number | string;
  powerEff: string | number;
  powerOutput: string | number;
  setAllocationMethod: (m: string) => void;
  setAmount: (a: string) => void;
  setBoilerEff: (b: string) => void;
  setFacilityId: (id: string) => void;
  setGridRegion: (g: string) => void;
  setHeatEff: (h: string) => void;
  setHeatOutput: (h: string) => void;
  setMarketFactor: (f: string) => void;
  setMarketInstrument: (m: string) => void;
  setMonth: (m: any) => void;
  setPowerEff: (p: string) => void;
  setPowerOutput: (p: string) => void;
  setTransLoss: (t: string) => void;
  setUnit: (u: string) => void;
  setYear: (y: any) => void;
  sourceType: string;
  submitting: boolean;
  transLoss: string | number;
  unit: string;
  unitOptions: Array<{ value: string; label: string }>;
  year: number | string;
}

// Extracted from Scope2Form.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const Scope2FormNewElectricityEntry: React.FC<Scope2FormNewElectricityEntryProps> = ({
  activity,
  allocationMethod,
  amount,
  boilerEff,
  division,
  facilityId,
  field,
  getFacilityOptions,
  getGridOptions,
  gridRegion,
  handleAddEntry,
  handleSourceTypeChange,
  heatEff,
  heatOutput,
  marketFactor,
  marketInstrument,
  month,
  powerEff,
  powerOutput,
  setAllocationMethod,
  setAmount,
  setBoilerEff,
  setFacilityId,
  setGridRegion,
  setHeatEff,
  setHeatOutput,
  setMarketFactor,
  setMarketInstrument,
  setMonth,
  setPowerEff,
  setPowerOutput,
  setTransLoss,
  setUnit,
  setYear,
  sourceType,
  submitting,
  transLoss,
  unit,
  unitOptions,
  year,
}) => (
  <div
    className={`calc-panel [background:white]! [border-radius:8px]! [padding:25px]! [box-shadow:0_2px_10px_rgba(0,0,0,0.05)]!`}
  >
    <h2
      className="text-[length:1.2rem]! [font-weight:bold]! mb-[25px]! text-[color:var(--color-legacy-333333)]!"
    >
      {t("Scope 2 Indirect Energy Emissions")}
    </h2>

    {/* 1. IDENTITY & LOCATION */}
    <div className="mb-[30px]!">
      <h4 className="section-title">{t("1. IDENTITY & LOCATION")}</h4>
      <div className="form-grid-4">
        <div className="input-group">
          <label className="flex items-center gap-1.5 text-sm font-medium text-text">
            <Lock className="size-3.5 text-text-secondary" aria-hidden="true" />
            <span>{t("Activity")}</span>
          </label>
          <input
            type="text"
            className="mole-input readonly bg-ink-50/80! border border-border text-ink-700! disabled:cursor-not-allowed text-sm"
            value={activity || ""}
            placeholder={facilityId ? t("Not specified") : t("Select a region first")}
            disabled
          />
          <span className="text-xs text-text-secondary">
            {facilityId ? t("Auto-filled from Region") : t("Select a region first")}
          </span>
        </div>
        <div className="input-group">
          <label className="flex items-center gap-1.5 text-sm font-medium text-text">
            <Lock className="size-3.5 text-text-secondary" aria-hidden="true" />
            <span>{t("Division")}</span>
          </label>
          <input
            type="text"
            className="mole-input readonly bg-ink-50/80! border border-border text-ink-700! disabled:cursor-not-allowed text-sm"
            value={division || ""}
            placeholder={facilityId ? t("Not specified") : t("Select a region first")}
            disabled
          />
          <span className="text-xs text-text-secondary">
            {facilityId ? t("Auto-filled from Region") : t("Select a region first")}
          </span>
        </div>
        <div className="input-group">
          <label className="text-sm font-medium text-text">{t("Region")}</label>
          <CustomDropdown
            options={getFacilityOptions()}
            value={facilityId || ""}
            onChange={setFacilityId}
            placeholder={t("Select Region...")}
          />
        </div>
        <div className="input-group">
          <label className="flex items-center gap-1.5 text-sm font-medium text-text">
            <Lock className="size-3.5 text-text-secondary" aria-hidden="true" />
            <span>{t("Field")}</span>
          </label>
          <input
            type="text"
            className="mole-input readonly bg-ink-50/80! border border-border text-ink-700! disabled:cursor-not-allowed text-sm"
            value={field || ""}
            placeholder={facilityId ? t("Not specified") : t("Select a region first")}
            disabled
          />
          <span className="text-xs text-text-secondary">
            {facilityId ? t("Auto-filled from Region") : t("Select a region first")}
          </span>
        </div>
      </div>
      <div className="form-grid-3">
        <Field className="input-group" label={t("Year")}>
          <Input
            type="number"
            min={ACTIVITY_YEAR_MIN}
            max={activityYearMax()}
            value={year || ""}
            onChange={(e) => setYear(e.target.value)}
          />
        </Field>
        <div className="input-group">
          <label>{t("Month")}</label>
          <CustomDropdown
            options={[...Array(12)].map((_, i) => ({
              value: i + 1,
              label: new Date(2025, i, 1).toLocaleString(currentLanguage() === "fr" ? "fr-FR" : "en-US", { month: "long" }),
            }))}
            value={Number(month) || 1}
            onChange={(val) => setMonth(Number(val))}
            placeholder={t("Select Month...")}
          />
        </div>
      </div>
    </div>

    {/* 2. GRID & SOURCE DETAILS */}
    <div className="mb-[30px]!">
      <h4 className="section-title">{t("2. GRID & SOURCE DETAILS")}</h4>
      <div className="form-grid-2">
        <div className="input-group">
          <label>{t("Source Type")}</label>
          <CustomDropdown
            options={[
              {
                value: "electricity",
                label: t("Purchased Electricity (Grid)"),
              },
              { value: "indirect_steam", label: t("Indirect Steam / Heat") },
              {
                value: "cogen_allocation",
                label: t("CHP / Cogeneration Allocation"),
              },
            ]}
            value={sourceType}
            onChange={handleSourceTypeChange}
          />
        </div>
        {sourceType === "electricity" && (
          <div className="input-group">
            <label>{t("Grid Region")}</label>
            <CustomDropdown
              options={getGridOptions()}
              value={gridRegion}
              onChange={setGridRegion}
              placeholder={t("Select Grid...")}
            />
          </div>
        )}
        {sourceType === "electricity" && (
          // market-based Scope 2 (dual reporting): contract instrument and its factor; blank = location-based
          <div className={`form-grid-2 [grid-column:span_2]!`}>
            <div className="input-group">
              <label>{t("Market instrument (market-based)")}</label>
              <CustomDropdown
                options={MARKET_INSTRUMENTS}
                value={marketInstrument || ""}
                onChange={(val) => setMarketInstrument(String(val))}
                placeholder={t("None (location-based fallback)")}
              />
            </div>
            <Field className="input-group" label={t("Contract emission factor (kg CO2e/kWh)")}>
              <Input
                type="number"
                step="any"
                min={0}
                value={marketFactor}
                onChange={(e) => setMarketFactor(e.target.value)}
                placeholder={marketInstrument === "REC" ? t("blank = 0 (zero-carbon)") : t("blank = grid factor")}
                disabled={!marketInstrument}
              />
            </Field>
          </div>
        )}
        {sourceType === "indirect_steam" && (
          <div className={`form-grid-2 [grid-column:span_2]!`}>
            <Field className="input-group" label={t("Boiler Efficiency (0.0 - 1.0)")}>
              <Input
                type="number"
                min="0"
                max="1"
                step="any"
                value={boilerEff}
                onChange={(e) => setBoilerEff(e.target.value)}
              />
            </Field>
            <Field className="input-group" label={t("Transmission Loss (0.0 - 1.0)")}>
              <Input
                type="number"
                min="0"
                max="1"
                step="any"
                value={transLoss}
                onChange={(e) => setTransLoss(e.target.value)}
              />
            </Field>
          </div>
        )}
        {sourceType === "cogen_allocation" && (
          <div className={`form-grid-3 [grid-column:span_2]!`}>
            <Field className="input-group" label={t("Heat Output (MMBtu)")}>
              <Input
                type="number"
                min="0"
                step="any"
                value={heatOutput}
                onChange={(e) => setHeatOutput(e.target.value)}
              />
            </Field>
            <Field className="input-group" label={t("Power Output (MWh)")}>
              <Input
                type="number"
                min="0"
                step="any"
                value={powerOutput}
                onChange={(e) => setPowerOutput(e.target.value)}
              />
            </Field>
            <div className="input-group">
              <label>{t("Method")}</label>
              <CustomDropdown
                options={[
                  { value: "wri_efficiency", label: t("WRI Efficiency") },
                  { value: "energy_content", label: t("Energy Content") },
                ]}
                value={allocationMethod}
                onChange={(val) => setAllocationMethod(String(val))}
              />
            </div>
            {allocationMethod === "wri_efficiency" && (
              <>
                <Field className="input-group" label={t("Heat Efficiency (%)")}>
                  <Input
                    type="number"
                    min="1"
                    max="100"
                    placeholder="80"
                    value={heatEff}
                    onChange={(e) => setHeatEff(e.target.value)}
                  />
                </Field>
                <Field className="input-group" label={t("Power Efficiency (%)")}>
                  <Input
                    type="number"
                    min="1"
                    max="100"
                    placeholder="35"
                    value={powerEff}
                    onChange={(e) => setPowerEff(e.target.value)}
                  />
                </Field>
              </>
            )}
          </div>
        )}
      </div>
    </div>

    {/* 3. ACTIVITY DATA */}
    <div className="mb-[10px]!">
      <h4 className="section-title">{t("3. ACTIVITY DATA")}</h4>
      <div className="form-grid-2">
        <Field
          className="input-group"
          label={
            sourceType === "cogen_allocation"
              ? t("Total Facility Emissions (tCO2e)")
              : t("Usage Amount")
          }
        >
          <Input
            type="number"
            min="0"
            value={amount || ""}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="0.00"
          />
        </Field>
        <div className="input-group">
          <label>{t("Unit")}</label>
          <CustomDropdown
            options={unitOptions}
            value={unit}
            onChange={setUnit}
          />
        </div>
      </div>
    </div>

    {/* Live Calculation Preview Card (A6) */}
    <div className="live-calc-preview rounded-lg border border-border bg-ink-50/80 p-3 mt-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold text-text uppercase tracking-wider">
          {t("Live Result Preview")}
        </span>
        {amount && Number(amount) > 0 ? (
          <Badge tone="success" className="font-mono text-xs font-bold">
            {t("Ready to calculate")}
          </Badge>
        ) : (
          <span className="text-xs text-text-secondary italic">
            {t("Enter electricity/heat consumption to preview")}
          </span>
        )}
      </div>
      <div className="mt-1.5 flex flex-wrap items-center justify-between text-xs text-text-secondary">
        <span>
          {t("Scope 2 Method:")}{" "}
          <strong className="text-text font-medium">{sourceType === "location" ? t("Location-based (Grid)") : t("Market-based (Contractual)")}</strong>
        </span>
        <span>
          {t("Quantity:")}{" "}
          <strong className="text-text font-medium">{amount ? `${amount} ${unit}` : "—"}</strong>
        </span>
      </div>
    </div>

    <div className="mt-[16px]!">
      <button
        type="button"
        className={`btn-add-activity w-full ${submitting ? "[cursor:not-allowed]! [opacity:0.6]!" : "[cursor:pointer]! [opacity:1]!"}`}
        disabled={submitting}
        onClick={() => handleAddEntry("Verified")}
      >
        {submitting ? t("Calculating & submitting...") : t("+ Calculate & Submit for Review")}
      </button>
    </div>
  </div>
);

export default Scope2FormNewElectricityEntry;
