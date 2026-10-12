import React from "react";
import { Input, Field } from "../../ui";
import CustomDropdown from "../CustomDropdown";
import { MARKET_INSTRUMENTS } from "./marketInstruments";
import { currentLanguage, t } from "../../i18n";

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
      {t("New Electricity Entry")}
    </h2>

    {/* 1. IDENTITY & LOCATION */}
    <div className="mb-[30px]!">
      <h4 className="section-title">{t("1. IDENTITY & LOCATION")}</h4>
      <div className="form-grid-4">
        <div className="input-group">
          <label>{t("Activity")}</label>
          <input
            type="text"
            className="mole-input readonly"
            value={activity || ""}
            disabled
          />
        </div>
        <div className="input-group">
          <label>{t("Division")}</label>
          <input
            type="text"
            className="mole-input readonly"
            value={division || ""}
            disabled
          />
        </div>
        <div className="input-group">
          <label>{t("Region")}</label>
          <CustomDropdown
            options={getFacilityOptions()}
            value={facilityId || ""}
            onChange={setFacilityId}
            placeholder={t("Select Region...")}
          />
        </div>
        <div className="input-group">
          <label>{t("Field")}</label>
          <input
            type="text"
            className="mole-input readonly"
            value={field || ""}
            disabled
          />
        </div>
      </div>
      <div className="form-grid-3">
        <Field className="input-group" label={t("Year")}>
          <Input
            type="number"
            min={1990}
            max={2100}
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

    <div className="mt-[24px]!">
      <button
        type="button"
        className={`btn-add-activity w-full ${submitting ? "[cursor:not-allowed]! [opacity:0.6]!" : "[cursor:pointer]! [opacity:1]!"}`}
        disabled={submitting}
        onClick={() => handleAddEntry("Verified")}
      >
        {submitting ? t("Processing...") : t("+ Calculate & Submit for Review")}
      </button>
    </div>
  </div>
);

export default Scope2FormNewElectricityEntry;
