import React from "react";
import { Input, Field } from "../../ui";
import CustomDropdown from "../CustomDropdown";
import { NativeSelect } from "../../ui/NativeSelect";
import { MARKET_INSTRUMENTS } from "./marketInstruments";
import { t } from "../../i18n";

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
            value={year || ""}
            onChange={(e) => setYear(e.target.value)}
          />
        </Field>
        <Field className="input-group" label={t("Month")}>
          <NativeSelect
            className="component-select"
            value={month || 1}
            onChange={(e) => setMonth(e.target.value)}
          >
            {[...Array(12)].map((_, i) => (
              <option key={i + 1} value={i + 1}>
                {String(i + 1).padStart(2, "0")}
              </option>
            ))}
          </NativeSelect>
        </Field>
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
            <Field className="input-group" label={t("Market instrument (market-based)")}>
              <NativeSelect value={marketInstrument} onChange={(e) => setMarketInstrument(e.target.value)}>
                {MARKET_INSTRUMENTS.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </NativeSelect>
            </Field>
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
                value={boilerEff}
                onChange={(e) => setBoilerEff(e.target.value)}
              />
            </Field>
            <Field className="input-group" label={t("Transmission Loss (0.0 - 1.0)")}>
              <Input
                type="number"
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
                value={heatOutput}
                onChange={(e) => setHeatOutput(e.target.value)}
              />
            </Field>
            <Field className="input-group" label={t("Power Output (MWh)")}>
              <Input
                type="number"
                value={powerOutput}
                onChange={(e) => setPowerOutput(e.target.value)}
              />
            </Field>
            <Field className="input-group" label={t("Method")}>
              <NativeSelect
                className="component-select"
                value={allocationMethod}
                onChange={(e) => setAllocationMethod(e.target.value)}
              >
                <option value="wri_efficiency">{t("WRI Efficiency")}</option>
                <option value="energy_content">{t("Energy Content")}</option>
              </NativeSelect>
            </Field>
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

    <div className="flex! gap-[12px]! mt-[24px]! justify-end!">
      <button
        type="button"
        className={`action-btn secondary [padding:10px_20px]! ${submitting ? "[cursor:not-allowed]!" : "[cursor:pointer]!"} ${submitting ? "[opacity:0.6]!" : "[opacity:1]!"}`}
        disabled={submitting}
        onClick={() => handleAddEntry("Draft")}
      >
        {submitting ? t("Saving...") : t("Save as Draft (Maker Mode)")}
      </button>
      <button
        type="button"
        className={`btn-add-activity [padding:10px_24px]! ${submitting ? "[cursor:not-allowed]!" : "[cursor:pointer]!"} ${submitting ? "[opacity:0.6]!" : "[opacity:1]!"}`}
        disabled={submitting}
        onClick={() => handleAddEntry("Verified")}
      >
        {submitting ? t("Processing...") : t("+ Calculate & Submit for Review")}
      </button>
    </div>
  </div>
);

export default Scope2FormNewElectricityEntry;
