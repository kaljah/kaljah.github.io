import React from "react";
import { Input, Field } from "../../ui";
import ColumnMappingWizard from "../ColumnMappingWizard";
import CustomDropdown from "../CustomDropdown";
import { NativeSelect } from "../../ui/NativeSelect";
import { activateOnKey } from "../../utils/a11yKeys";

// Extracted from Scope3Form.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const Scope3FormNewScope3 = ({ UNIT_MULTIPLIERS, activityType, amount, baseUnit, category, eeioNaics, eeioResult, eeioSpend, emissionFactor, facilityId, getActivityOptions, getCategoryOptions, getFacilityOptions, handleAddEntry, handleCalculateEeio, handleImportSuccess, handleUnitChange, importModal, month, naicsOptions, searchNaics, setActivityType, setAmount, setCategory, setEeioNaics, setEeioSpend, setEmissionFactor, setFacilityId, setImportModal, setMonth, setShowEeioCalc, setYear, showEeioCalc, submitting, unit, year }) => (
<div className="calc-panel">

        {/* EEIO Quick Spend Calculator */}
        <div style={{ marginTop: "20px", marginBottom: "10px", padding: "16px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px" }}>
          <div role="button" tabIndex={0} onKeyDown={activateOnKey} className="flex! justify-between! items-center! cursor-pointer!" onClick={() => setShowEeioCalc(!showEeioCalc)}>
            <div className="flex! items-center! gap-[8px]!">
              <span className="text-[length:1.2rem]!">💰</span>
              <strong className="text-[color:#334155]!">EEIO Quick Spend Calculator</strong>
              <span className="text-[length:0.8rem]! text-[color:#64748b]! ml-[10px]!">Convert financial spend to CO₂e using NAICS factors</span>
            </div>
            <span>{showEeioCalc ? "▲" : "▼"}</span>
          </div>
          
          {showEeioCalc && (
            <div className="mt-[16px]! flex! gap-[16px]! items-end!">
              <div className="input-group flex-1!">
                <label>NAICS Code (6 digits)</label>
                <Input
                  type="text"
                 
                  placeholder="e.g. 331110 or steel"
                  value={eeioNaics}
                  list="eeio-naics-options"
                  onChange={(e) => {
                    setEeioNaics(e.target.value);
                    searchNaics(e.target.value);
                  }}
                />
                <datalist id="eeio-naics-options">
                  {naicsOptions.map((o) => (
                    <option key={o.naics} value={o.naics}>{`${o.name} (${o.kg_co2e_per_usd} kg CO2e/USD)`}</option>
                  ))}
                </datalist>
              </div>
              <div className="input-group flex-1!">
                <label>Spend Amount (USD)</label>
                <Input
                  type="number"
                 
                  placeholder="0.00"
                  value={eeioSpend}
                  onChange={(e) => setEeioSpend(e.target.value)}
                />
              </div>
              <button 
                className="action-btn h-[38px]! p-[0_16px]! bg-[color:#3b82f6]! text-[color:white]!" 
               
                onClick={handleCalculateEeio}
              >
                Calculate & Auto-fill
              </button>
            </div>
          )}
          {eeioResult && showEeioCalc && (
            <div style={{ marginTop: "12px", padding: "12px", background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: "6px" }}>
              <div className="text-[length:0.85rem]! text-[color:#1e3a8a]!">
                <strong>Industry:</strong> {eeioResult.industry_name} <br/>
                <strong>Factor:</strong> {eeioResult.emission_factor} {eeioResult.ef_unit} <br/>
                <strong>Estimated Emissions:</strong> <span className="text-[length:1.1rem]! [font-weight:bold]!">{eeioResult.co2e.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span> tCO₂e
              </div>
            </div>
          )}
        </div>

        <div
          className="flex! justify-between! items-center! mb-[20px]!"
        >
          <h3 className="m-[0px]!">New Scope 3 Entry</h3>
          <div className="text-right!">
            <span
              className="text-[color:#6d28d9]! font-semibold! text-[length:0.9rem]!"
            >
              Scope 3: Other Indirect
            </span>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "20px",
            marginBottom: "20px",
          }}
        >
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
                  {new Date(0, i).toLocaleString("default", { month: "long" })}
                </option>
              ))}
            </NativeSelect>
</Field>
          <div className="input-group">
            <label>Facility</label>
            <CustomDropdown
              options={getFacilityOptions()}
              value={facilityId || ""}
              onChange={setFacilityId}
            />
          </div>
          <div className="input-group">
            <label>Category</label>
            <CustomDropdown
              options={getCategoryOptions()}
              value={category}
              onChange={setCategory}
            />
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "20px",
          }}
        >
          <div className="input-group">
            <label>Activity Type</label>
            <CustomDropdown
              options={getActivityOptions()}
              value={activityType}
              onChange={setActivityType}
            />
          </div>
          <Field className="input-group" label="Amount">
<Input
              type="number"
             
              value={amount || ""}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              step="0.01"
            />
</Field>
          <div className="input-group">
            <label>Unit</label>
            {UNIT_MULTIPLIERS[baseUnit] ? (
              <NativeSelect
                className="component-select"
                value={unit}
                onChange={(e) => handleUnitChange(e.target.value)}
              >
                {Object.keys(UNIT_MULTIPLIERS[baseUnit]).map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </NativeSelect>
            ) : (
              <Input
                type="text"
               
                value={unit}
                readOnly
                className="bg-[color:rgba(255,255,255,0.03)]! cursor-not-allowed!"
              />
            )}
          </div>
          <Field className="input-group" label="EF (kg CO₂e/unit)">
<Input
              type="number"
             
              value={emissionFactor || ""}
              onChange={(e) => setEmissionFactor(e.target.value)}
              step="0.01"
            />
</Field>
        </div>


        <div
          className="flex! gap-[12px]! mt-[30px]! justify-end!"
        >
          <button
            className="action-btn secondary"
            disabled={submitting}
            onClick={() => handleAddEntry("Draft")}
            style={{
              padding: "12px 20px",
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
              flex: 1.5,
              padding: "12px",
              cursor: submitting ? "not-allowed" : "pointer",
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? "Processing..." : "+ Calculate & Submit for Review"}
          </button>
        </div>

        {importModal.isOpen && (
          <ColumnMappingWizard
            onClose={() => setImportModal({ ...importModal, isOpen: false })}
            onUploadSuccess={handleImportSuccess}
            type={importModal.type}
          />
        )}
      </div>
);

export default Scope3FormNewScope3;
