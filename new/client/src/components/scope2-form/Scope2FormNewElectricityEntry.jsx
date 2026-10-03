import React from "react";
import { Input, Field } from "../../ui";
import CustomDropdown from "../CustomDropdown";
import { NativeSelect } from "../../ui/NativeSelect";

// Extracted from Scope2Form.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const Scope2FormNewElectricityEntry = ({ activity, allocationMethod, amount, boilerEff, division, facilityId, field, getFacilityOptions, getGridOptions, gridRegion, handleAddEntry, handleSourceTypeChange, heatEff, heatOutput, month, powerEff, powerOutput, setAllocationMethod, setAmount, setBoilerEff, setFacilityId, setGridRegion, setHeatEff, setHeatOutput, setMonth, setPowerEff, setPowerOutput, setTransLoss, setUnit, setYear, sourceType, submitting, transLoss, unit, unitOptions, year }) => (
<div
        className="calc-panel"
        style={{
          background: "white",
          borderRadius: "8px",
          padding: "25px",
          boxShadow: "0 2px 10px rgba(0,0,0,0.05)",
        }}
      >
        <h2
          style={{
            fontSize: "1.2rem",
            fontWeight: "bold",
            marginBottom: "25px",
            color: "#333",
          }}
        >
          New Electricity Entry
        </h2>

        {/* 1. IDENTITY & LOCATION */}
        <div className="mb-[30px]!">
          <h4 className="section-title">1. IDENTITY &amp; LOCATION</h4>
          <div className="form-grid-4">
            <div className="input-group">
              <label>Activity</label>
              <input
                type="text"
                className="mole-input readonly"
                value={activity || ""}
                disabled
              />
            </div>
            <div className="input-group">
              <label>Division</label>
              <input
                type="text"
                className="mole-input readonly"
                value={division || ""}
                disabled
              />
            </div>
            <div className="input-group">
              <label>Region</label>
              <CustomDropdown
                options={getFacilityOptions()}
                value={facilityId || ""}
                onChange={setFacilityId}
                placeholder="Select Region..."
              />
            </div>
            <div className="input-group">
              <label>Field</label>
              <input
                type="text"
                className="mole-input readonly"
                value={field || ""}
                disabled
              />
            </div>
          </div>
          <div className="form-grid-3">
            <Field className="input-group" label="Year">
<Input
                type="number"
               
                value={year || ""}
                onChange={(e) => setYear(e.target.value)}
              />
</Field>
            <Field className="input-group" label="Month">
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
          <h4 className="section-title">2. GRID &amp; SOURCE DETAILS</h4>
          <div className="form-grid-2">
            <div className="input-group">
              <label>Source Type</label>
              <CustomDropdown
                options={[
                  {
                    value: "electricity",
                    label: "Purchased Electricity (Grid)",
                  },
                  { value: "indirect_steam", label: "Indirect Steam / Heat" },
                  {
                    value: "cogen_allocation",
                    label: "CHP / Cogeneration Allocation",
                  },
                ]}
                value={sourceType}
                onChange={handleSourceTypeChange}
              />
            </div>
            {sourceType === "electricity" && (
              <div className="input-group">
                <label>Grid Region</label>
                <CustomDropdown
                  options={getGridOptions()}
                  value={gridRegion}
                  onChange={setGridRegion}
                  placeholder="Select Grid..."
                />
              </div>
            )}
            {sourceType === "indirect_steam" && (
              <div className="form-grid-2" style={{ gridColumn: "span 2" }}>
                <Field className="input-group" label="Boiler Efficiency (0.0 - 1.0)">
<Input
                    type="number"
                   
                    value={boilerEff}
                    onChange={(e) => setBoilerEff(e.target.value)}
                  />
</Field>
                <Field className="input-group" label="Transmission Loss (0.0 - 1.0)">
<Input
                    type="number"
                   
                    value={transLoss}
                    onChange={(e) => setTransLoss(e.target.value)}
                  />
</Field>
              </div>
            )}
            {sourceType === "cogen_allocation" && (
              <div className="form-grid-3" style={{ gridColumn: "span 2" }}>
                <Field className="input-group" label="Heat Output (MMBtu)">
<Input
                    type="number"
                   
                    value={heatOutput}
                    onChange={(e) => setHeatOutput(e.target.value)}
                  />
</Field>
                <Field className="input-group" label="Power Output (MWh)">
<Input
                    type="number"
                   
                    value={powerOutput}
                    onChange={(e) => setPowerOutput(e.target.value)}
                  />
</Field>
                <Field className="input-group" label="Method">
<NativeSelect
                    className="component-select"
                    value={allocationMethod}
                    onChange={(e) => setAllocationMethod(e.target.value)}
                  >
                    <option value="wri_efficiency">WRI Efficiency</option>
                    <option value="energy_content">Energy Content</option>
                  </NativeSelect>
</Field>
                {allocationMethod === "wri_efficiency" && (
                  <>
                    <Field className="input-group" label="Heat Efficiency (%)">
<Input type="number" min="1" max="100" placeholder="80"
                        value={heatEff} onChange={(e) => setHeatEff(e.target.value)} />
</Field>
                    <Field className="input-group" label="Power Efficiency (%)">
<Input type="number" min="1" max="100" placeholder="35"
                        value={powerEff} onChange={(e) => setPowerEff(e.target.value)} />
</Field>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 3. ACTIVITY DATA */}
        <div className="mb-[10px]!">
          <h4 className="section-title">3. ACTIVITY DATA</h4>
          <div className="form-grid-2">
            <Field className="input-group" label={<>{sourceType === "cogen_allocation"
                  ? "Total Facility Emissions (tCO2e)"
                  : "Usage Amount"}</>}>
<Input
                type="number"
               
                value={amount || ""}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
              />
</Field>
            <div className="input-group">
              <label>Unit</label>
              <CustomDropdown
                options={unitOptions}
                value={unit}
                onChange={setUnit}
              />
            </div>
          </div>
        </div>

        <div
          className="flex! gap-[12px]! mt-[24px]! justify-end!"
        >
          <button
            className="action-btn secondary"
            disabled={submitting}
            onClick={() => handleAddEntry("Draft")}
            style={{
              padding: "10px 20px",
              cursor: submitting ? "not-allowed" : "pointer",
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? "Saving..." : "Save as Draft (Maker Mode)"}
          </button>
          <button
            className="btn-add-activity"
            disabled={submitting}
            onClick={() => handleAddEntry("Verified")}
            style={{
              padding: "10px 24px",
              cursor: submitting ? "not-allowed" : "pointer",
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? "Processing..." : "+ Calculate & Submit for Review"}
          </button>
        </div>
      </div>
);

export default Scope2FormNewElectricityEntry;
