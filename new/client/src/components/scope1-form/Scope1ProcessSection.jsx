import React from "react";
import { Input } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { BookOpen, PlusCircle } from "lucide-react";
import CustomDropdown from "../CustomDropdown";
import { SECTION_PROCESSES, SECTION_TIERS, sectionMethodActive } from "../scope1/methodChoices";
import { Section } from "../scope1/ui";
import { getPresetsForFuel } from "../../constants/officialFuelPresets";
import { hideApiCitation } from "./shared";

// Extracted from Scope1Form.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const Scope1ProcessSection = ({ activePresetId, currentProcessValue, dataSourceRef, formData, fuelDensity, fuelOptions, getProcessOptions, handleApplyPreset, handleFormChange, handleProcessChange, processType, renderFactorOption, resetProcessInputs, setActivePresetId, setDataSourceRef, setFuelDensity, setIsQuickAddModalOpen, setShowGasCalc, setSourceType, setSpecFactors, showsTier3Factors, sourceType, specFactors, streamType, tier2Mode }) => (
<Section n={2} title="Process & Source Details">
          <div className="[display:grid]! [grid-template-columns:1fr] [gap:16px]">
            <div className="input-group">
              <label>Process</label>
              <CustomDropdown
                options={getProcessOptions()}
                value={currentProcessValue}
                onChange={handleProcessChange}
              />
            </div>

            {/* Hoisted Emission Factor Selection — hidden for stoichiometry and dedicated downstream process forms */}
            {!["stoichiometry", "chemical_production", "nitric_acid_production", "adipic_acid_production", "asphalt_blowing"].includes(processType) && (
              <div className="input-group">
                <div className="[display:flex]! [flex-direction:column] [align-items:flex-start] [gap:6px] [margin-bottom:12px]!">
                  <label className="m-[0px]!">Method</label>
                  <div className="methodology-toggle">
                    {(SECTION_TIERS[processType]
                      ? SECTION_TIERS[processType]
                      : processType === "drilling"
                      ? [
                          {
                            key: "default",
                            tier: "Tier 1",
                            label: "Standard",
                            sub: "Catalog Defaults",
                          },
                          {
                            key: "custom",
                            tier: "Tier 2",
                            label: "Custom Factor",
                            sub: "Saved Database Factors",
                          },
                          {
                            key: "tier2_plus",
                            tier: "Tier 2+",
                            label: "Site Gas Composition",
                            sub: "Onshore EF + Site CH₄/CO₂",
                          },
                        ]
                      : processType === "completions"
                      ? [
                          { key: "default", tier: "Tier 1", label: "Defaults", sub: "Per-event factor" },
                          { key: "custom", tier: "Tier 2", label: "Operational Data", sub: "Rate, GOR or production" },
                          { key: "specific", tier: "Tier 3", label: "Direct Measurement", sub: "Metered flowback" },
                        ]
                      : processType === "unloading"
                      ? [
                          { key: "default", tier: "Tier 1", label: "Per-Well", sub: "Per-well annual factor" },
                          { key: "custom", tier: "Tier 2", label: "Event-Based", sub: "Per-event factor" },
                          { key: "specific", tier: "Tier 3", label: "Engineering", sub: "Wellbore / plunger models" },
                        ]
                      : processType === "associated_gas_venting"
                      ? [
                          {
                            key: "default",
                            tier: "Tier 1",
                            label: "Regional Default",
                            sub: "Basin average factor",
                          },
                          {
                            key: "custom",
                            tier: "Tier 2",
                            label: "GOR Balance",
                            sub: "Oil × GOR × duration",
                          },
                          {
                            key: "specific",
                            tier: "Tier 3",
                            label: "Measurement",
                            sub: "Metered vent rate / volume",
                          },
                        ]
                      : processType === "fugitive"
                      ? [
                          {
                            key: "default",
                            tier: "Tier 1",
                            label: "Facility-Level",
                            sub: "Facility average",
                          },
                          {
                            key: "custom",
                            tier: "Tier 2",
                            label: "Equipment & Component",
                            sub: "Equipment / component count",
                          },
                          {
                            key: "specific",
                            tier: "Tier 3",
                            label: "Screening / OGI / Meas.",
                            sub: "Method 21, OGI, Direct Rate",
                          },
                        ]
                      : [
                          {
                            key: "default",
                            tier: "Tier 1",
                            label: "Standard",
                            sub: "Catalog Defaults",
                          },
                          {
                            key: "custom",
                            tier: "Tier 2",
                            label: "Regional / Lab",
                            sub: "Ticket / Presets / Custom",
                          },
                          {
                            key: "specific",
                            tier: "Tier 3",
                            label: "Measurement / GC",
                            sub: "CEMS / Analysis",
                          },
                        ]
                    )
                      // Library factors (the site factor database: calculated or equipment factors) are a
                      // separate choice from the API Compendium tiers
                      .concat([{ key: "library", tier: "", label: "Library factor", sub: "Site factor database" }])
                      .filter((item) => {
                        const type = item.key;
                        if (SECTION_TIERS[processType]) return true;
                        if (
                          type === "custom" &&
                          ["drilling", "pneumatic", "tank", "tank_flashing", "tank_working", "tank_breathing",
                           "venting", "blowdown", "loading", "separation"].includes(processType)
                        )
                          return false;
                        if (processType === "drilling") return true;
                        if (processType === "loading" && type === "specific")
                          return false;
                        if (processType === "separation" && type === "specific")
                          return false;
                        if (
                          ["agr", "dehydrator"].includes(processType) &&
                          (type === "default" || type === "custom")
                        )
                          return false;
                        return true;
                      })
                      .map((item) => {
                        const type = item.key;
                        const isActive = sourceType === type;
                        return (
                          <button
                            key={type}
                            type="button"
                            className={`tier-selector-btn ${isActive ? "active" : ""}`}
                            onClick={() => {
                              if (type !== sourceType) resetProcessInputs();
                              setSourceType(type);
                              if (processType === "drilling") {
                                if (type === "default") {
                                  handleFormChange("unit", "well");
                                } else {
                                  handleFormChange("unit", "days");
                                }
                              }
                            }}
                          >
                            <span className="tier-tag">{item.tier}</span>
                            <span className="tier-label">{item.label}</span>
                          </button>
                        );
                      })}
                  </div>
                </div>


                {/* TIER 1: Standard API Tabulated Factors */}
                {sourceType === "default" && !sectionMethodActive(formData) && !SECTION_PROCESSES[processType] &&
                  !["associated_gas_venting", "completions", "unloading"].includes(processType) && (
                  <CustomDropdown
                    options={fuelOptions}
                    value={formData.fuel || ""}
                    onChange={(val) => handleFormChange("fuel", val)}
                    placeholder="Select factor"
                    renderOption={renderFactorOption}
                  />
                )}

                {/* TIER 2: Regional / Measured / Supplier Factors */}
                {((sourceType === "custom" && !["associated_gas_venting", "completions", "unloading", "fugitive"].includes(processType)) || sourceType === "library") && (
                  <div className="[margin-top:10px]! [background:#fafafa]! [border:1px_solid_#e5e7eb]! [border-radius:var(--radius-md)]! [padding:14px]!">
                    {sourceType === "custom" ? (
                      <>

                        {tier2Mode === "override" && (
                          <div className="[display:flex]! [flex-direction:column] [gap:12px]">
                            {/* Base Fuel Dropdown */}
                            <div>
                              <label className="block! text-[length:0.75rem]! font-semibold! text-[color:#374151]! mb-[4px]!">
                                Fuel
                              </label>
                              <CustomDropdown
                                options={fuelOptions}
                                value={formData.fuel || ""}
                                onChange={(val) => {
                                  handleFormChange("fuel", val);
                                  setActivePresetId("");
                                }}
                                placeholder="Select fuel"
                                renderOption={renderFactorOption}
                              />
                            </div>

                            {/* Presets Section */}
                            <div className="[background:var(--color-white)]! [border:1px_solid_#e5e7eb]! [border-radius:var(--radius-sm)]! [padding:10px_12px]!">
                              <div className="[display:flex]! [align-items:center] [justify-content:space-between] [margin-bottom:8px]!">
                                <span className="[display:flex]! [align-items:center] [gap:6px] [font-size:var(--text-sm)]! [font-weight:600]! [color:var(--color-ink-700)]!">
                                  <BookOpen size={14} className="text-[color:var(--color-link)]!" />
                                  Presets
                                </span>
                              </div>
                              <div className="[display:flex]! [flex-wrap:wrap] [gap:6px]">
                                {getPresetsForFuel(formData.fuel, streamType).map((preset) => (
                                  <button
                                    key={preset.id}
                                    type="button"
                                    className={`preset-chip ${activePresetId === preset.id ? "active" : ""}`}
                                    onClick={() => handleApplyPreset(preset)}
                                    title={preset.description}
                                  >
                                    {hideApiCitation(preset.citation) && <span className={`preset-citation-badge ${preset.citationType}`}>
                                      {hideApiCitation(preset.citation)}
                                    </span>}
                                    <span className="preset-name">{preset.shortLabel || preset.name}</span>
                                  </button>
                                ))}
                              </div>
                            </div>

                            {/* Measured Properties Grid */}
                            <div className="tier2-inputs-grid">
                              <div>
                                <label className="block! text-[length:0.75rem]! font-semibold! text-[color:#374151]! mb-[4px]!">
                                  HHV
                                </label>
                                <div className="flex! gap-[6px]!">
                                  <Input
                                    type="number"
                                    step="any"
                                   
                                    className="flex-1! p-[6px_8px]! text-[length:0.85rem]!"
                                    placeholder="e.g. 1085"
                                    value={formData.hhv || ""}
                                    onChange={(e) => {
                                      handleFormChange("hhv", e.target.value);
                                      setActivePresetId("");
                                    }}
                                  />
                                  <NativeSelect
                                    className="mole-input w-[110px]! p-[6px_8px]! text-[length:0.8rem]!"
                                   
                                    value={formData.hhv_unit || "BTU/scf"}
                                    onChange={(e) => handleFormChange("hhv_unit", e.target.value)}
                                  >
                                    <option value="BTU/scf">BTU/scf</option>
                                    <option value="MJ/m3">MJ/m³</option>
                                    <option value="kcal/m3">kcal/m³</option>
                                    <option value="BTU/gal">BTU/gal</option>
                                    <option value="BTU/lb">BTU/lb</option>
                                    <option value="MJ/kg">MJ/kg</option>
                                  </NativeSelect>
                                </div>
                              </div>

                              <div>
                                <label className="block! text-[length:0.75rem]! font-semibold! text-[color:#374151]! mb-[4px]!">
                                  Density (kg/m³)
                                </label>
                                <Input
                                  type="number"
                                  step="any"
                                 
                                  className="w-full! p-[6px_8px]! text-[length:0.85rem]!"
                                  placeholder="e.g. 840.0 for Gasoil NA 8110"
                                  value={fuelDensity}
                                  onChange={(e) => {
                                    setFuelDensity(e.target.value);
                                    setActivePresetId("");
                                  }}
                                />
                              </div>
                            </div>

                            {/* Data Source / Audit Reference Field */}
                            <div>
                              <label className="block! text-[length:0.75rem]! font-semibold! text-[color:#374151]! mb-[4px]!">
                                Ticket / lab ref
                              </label>
                              <Input
                                type="text"
                               
                                className="w-full! p-[6px_8px]! text-[length:0.85rem]!"
                                placeholder="e.g. Ticket #4902-B"
                                value={dataSourceRef}
                                onChange={(e) => setDataSourceRef(e.target.value)}
                              />
                            </div>

                                                      </div>
                        )}

                      </>
                    ) : (
                      <div>
                        <div className="flex! gap-[8px]! items-center!">
                          <div className="flex-1!">
                            <CustomDropdown
                              options={fuelOptions}
                              value={formData.fuel || ""}
                              onChange={(val) => handleFormChange("fuel", val)}
                              placeholder="Select saved factor"
                            />
                          </div>
                          <button
                            type="button"
                            className="btn btn-secondary flex! items-center! gap-[4px]! p-[8px_12px]! text-[length:0.8rem]! whitespace-nowrap!"
                            onClick={() => setIsQuickAddModalOpen(true)}
                           
                          >
                            <PlusCircle size={15} />
                            <span>New library factor</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                {showsTier3Factors && (
                    <>
                      <CustomDropdown
                        options={fuelOptions}
                        value={formData.fuel || ""}
                        onChange={(val) => handleFormChange("fuel", val)}
                        placeholder="Base factor (optional)"
                        renderOption={renderFactorOption}
                      />
                      <div className="mt-[10px]! mb-[10px]!">
                        <button
                          className="gas-calc-btn btn-secondary"
                          onClick={() => setShowGasCalc(true)}
                          style={{
                            display: processType === "agr" ? "none" : "flex",
                          }}
                        >
                          <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <rect
                              x="4"
                              y="2"
                              width="16"
                              height="20"
                              rx="2"
                              ry="2"
                            ></rect>
                            <line x1="8" y1="6" x2="16" y2="6"></line>
                            <line x1="16" y1="14" x2="16" y2="18"></line>
                            <path d="M16 10h.01"></path>
                            <path d="M12 10h.01"></path>
                            <path d="M8 10h.01"></path>
                            <path d="M12 14h.01"></path>
                            <path d="M8 14h.01"></path>
                            <path d="M12 18h.01"></path>
                            <path d="M8 18h.01"></path>
                          </svg>
                          Gas analysis
                        </button>
                      </div>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: "10px",
                          marginTop: "10px",
                        }}
                      >
                        {["co2", "ch4", "n2o"]
                          .filter((gas) =>
                            processType === "agr" ? gas !== "n2o" : true,
                          )
                          .map((gas) => (
                            <div
                              key={gas}
                              className="input-group mb-[0px]!"
                             
                            >
                              <label className="text-[length:0.75rem]!">
                                {gas.toUpperCase()} Factor
                              </label>
                              <div className="flex! gap-[5px]!">
                                <input
                                  type="number"
                                  className="mole-input flex-1!"
                                  placeholder="Value"
                                  value={specFactors[gas] || ""}
                                  onChange={(e) =>
                                    setSpecFactors((p) => ({
                                      ...p,
                                      [gas]: e.target.value,
                                    }))
                                  }
                                 
                                />
                                <NativeSelect
                                  className="component-select w-[80px]! p-[4px]!"
                                  value={specFactors[`${gas}Unit`] || ""}
                                  onChange={(e) =>
                                    setSpecFactors((p) => ({
                                      ...p,
                                      [`${gas}Unit`]: e.target.value,
                                    }))
                                  }
                                 
                                >
                                  <option value="kg/m3">kg/m³</option>
                                  <option value="kg/scf">kg/scf</option>
                                  <option value="kg/gal">kg/gal</option>
                                  <option value="lb/scf">lb/scf</option>
                                  <option value="tonne/m3">t/m³</option>
                                  <option value="kg/MMBtu">kg/MMBtu</option>
                                </NativeSelect>
                              </div>
                            </div>
                          ))}
                      </div>
                    </>
                  )}
              </div>
            )}
          </div>
        </Section>
);

export default Scope1ProcessSection;
