import React from "react";
import { NativeSelect } from "../../ui/NativeSelect";
import UploadProgress from "../UploadProgress";
import { activateOnKey } from "../../utils/a11yKeys";

// Extracted from Scope1ImportWizard.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const Scope1ImportWizardScope1Bulk = ({ FIELD_GROUPS, FieldGroup, Icon, ModeCard, PROCESS_CATALOGUE, ProcessTile, StepBar, allowedRegions, canGoNext, canSubmit, downloadTemplate, file, fileInputRef, globalFactor, handleSubmit, headers, isAdmin, isDragging, isSubmitting, jobId, mapping, missingRequired, onClose, onDrop, onFileChange, onUploadSuccess, overwrite, parseError, processScope, searchQuery, selectedProcesses, setGlobalFactor, setIsDragging, setMapping, setOverwrite, setProcessScope, setSearchQuery, setStep, setTier, step, tier, toggleProcess }) => (
<div className="[background:var(--color-white)]! [border-radius:var(--radius-lg)]! [width:100%]! [max-width:820px]! [max-height:94vh]! [display:flex]! [flex-direction:column] [box-shadow:var(--shadow-overlay)]! [animation:s1w-slide_0.28s_cubic-bezier(0.34,_1.56,_0.64,_1)]! [overflow:hidden]! [@media(max-width:600px)]:[border-radius:var(--radius-md)]!">
        {/* Header */}
        <div className="[display:flex]! [align-items:center] [justify-content:space-between] [padding:20px_24px_0]! [flex-shrink:0]">
          <div className="[display:flex]! [align-items:center] [gap:12px]">
            <div className="[width:40px]! [height:40px]! [border-radius:var(--radius-md)]! [background:var(--primary-gradient)]! [display:flex]! [align-items:center] [justify-content:center] [color:var(--color-white)]! [flex-shrink:0] [&_svg]:[width:20px]! [&_svg]:[height:20px]!"><Icon.Activity /></div>
            <div>
              <h2 className="[font-size:var(--text-lg)]! [font-weight:700]! [color:var(--color-ink-900)]! [margin:0_0_2px]! [letter-spacing:-0.3px] [font-family:inherit]!">Scope 1 Bulk Import</h2>
              <p className="[font-size:var(--text-sm)]! [color:var(--color-ink-500)]! [margin:0]!">Upload emissions data from CSV or Excel</p>
            </div>
          </div>
          <button className="[width:34px]! [height:34px]! [border-radius:var(--radius-md)]! [border:1px_solid_var(--color-ink-200)]! [background:transparent]! [cursor:pointer] [display:flex]! [align-items:center] [justify-content:center] [color:var(--color-ink-500)]! [transition:all_0.15s]! hover:[background:var(--color-ink-100)]! hover:[color:var(--color-ink-900)]! hover:[border-color:var(--color-ink-300)]! [&_svg]:[width:16px]! [&_svg]:[height:16px]!" aria-label="Close" onClick={onClose}><Icon.Close /></button>
        </div>

        {/* Step bar */}
        <StepBar current={step} />

        {/* ── STEP 1: Upload Mode ── */}
        {step === 1 && (
          <div className="s1w-body">
            <div className="[display:flex]! [align-items:center] [gap:8px] [font-size:var(--text-md)]! [font-weight:700]! [color:var(--color-ink-900)]! [margin-bottom:-6px]! [&_svg]:[width:16px]! [&_svg]:[height:16px]! [&_svg]:[color:var(--color-link)]!">
              <Icon.Settings />
              <span>Select Calculation Tier</span>
            </div>
            <p className="[font-size:var(--text-base)]! [color:var(--color-ink-500)]! [margin:0]! [line-height:1.5]">
              Choose how emissions will be calculated for each row in your file.
            </p>
            <div className="[display:grid]! [grid-template-columns:repeat(auto-fit,_minmax(220px,_1fr))] [gap:12px] [@media(max-width:600px)]:[grid-template-columns:1fr]!">
              <ModeCard
                selected={tier === "1"}
                onClick={() => setTier("1")}
                Icon={Icon.Zap}
                title="Tier 1 — Standard"
                badge={{ label: "Minimum fields", color: "blue" }}
                description="Uses API Compendium default emission factors. Only requires fuel type, quantity, and unit. Fast and simple."
              />
              <ModeCard
                selected={tier === "3"}
                onClick={() => setTier("3")}
                Icon={Icon.Settings}
                title="Tier 3 — Engineering"
                badge={{ label: "Full precision", color: "green" }}
                description="Uses actual gas composition (C1–C10), operating conditions (T/P), and process-specific parameters for maximum accuracy."
              />
              <ModeCard
                selected={tier === "auto"}
                onClick={() => setTier("auto")}
                Icon={Icon.Wand}
                title="Both Tiers — Auto Detect"
                badge={{ label: "Recommended", color: "orange" }}
                description="Mixes Tier 1 and Tier 3 rows in one file. The system detects per-row: if gas composition columns are filled, Tier 3 is used; otherwise Tier 1."
              />
            </div>
            <div className="[display:flex]! [align-items:flex-start] [gap:10px] [padding:12px_16px]! [background:var(--color-blue-50)]! [border:1px_solid_#bfdbfe]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [color:var(--color-blue-700)]! [line-height:1.5] [&_svg]:[width:16px]! [&_svg]:[height:16px]! [&_svg]:[flex-shrink:0]! [&_svg]:[margin-top:1px]!">
              <Icon.Info />
              <span>
                {tier === "1" && "Tier 1 only requires: Region, Date, Process, Fuel, Quantity, Unit."}
                {tier === "3" && "Tier 3 requires all Tier 1 fields plus gas composition and process engineering parameters."}
                {tier === "auto" && "Auto-detect is ideal when you have a mix of sources — some with gas composition data (Tier 3) and some without (Tier 1)."}
              </span>
            </div>
          </div>
        )}

        {/* ── STEP 2: Process Scope ── */}
        {step === 2 && (
          <div className="s1w-body">
            <div className="[display:flex]! [align-items:center] [gap:8px] [font-size:var(--text-md)]! [font-weight:700]! [color:var(--color-ink-900)]! [margin-bottom:-6px]! [&_svg]:[width:16px]! [&_svg]:[height:16px]! [&_svg]:[color:var(--color-link)]!"><Icon.Layers /><span>Process Scope</span></div>
            <p className="[font-size:var(--text-base)]! [color:var(--color-ink-500)]! [margin:0]! [line-height:1.5]">Does your file contain data for all process types, or a specific process?</p>
            <div className="[display:grid]! [grid-template-columns:1fr_1fr] [gap:12px] [@media(max-width:600px)]:[grid-template-columns:1fr]!">
              <ModeCard
                selected={processScope === "all"}
                onClick={() => setProcessScope("all")}
                Icon={Icon.Layers}
                title="All Processes"
                description="Your file contains a Process column that identifies the type (Combustion, Flaring, Venting, etc.) for each row."
              />
              <ModeCard
                selected={processScope === "specific"}
                onClick={() => setProcessScope("specific")}
                Icon={Icon.Activity}
                title="Specific Process(es)"
                description="Your file is dedicated to one or more specific processes. Select which ones apply to filter the column mapping to only the relevant fields."
              />
            </div>
            {processScope === "specific" && (
              <div className="[display:flex]! [flex-direction:column] [gap:10px]">
                <p className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--color-ink-700)]! [margin:0]!">Select which processes are in your file:</p>
                <div className="[display:grid]! [grid-template-columns:repeat(auto-fill,_minmax(150px,_1fr))] [gap:8px]">
                  {PROCESS_CATALOGUE.map(p => (
                    <ProcessTile
                      key={p.key}
                      process={p}
                      selected={selectedProcesses.includes(p.key)}
                      onClick={() => toggleProcess(p.key)}
                    />
                  ))}
                </div>
                {selectedProcesses.length === 0 && (
                  <div className="[display:flex]! [align-items:center] [gap:8px] [padding:8px_12px]! [background:var(--color-brand-50)]! [border:1px_solid_#fed7aa]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-sm)]! [color:var(--color-brand-700)]! [font-weight:500]! [&_svg]:[width:14px]! [&_svg]:[height:14px]!">
                    <Icon.Warning /> Select at least one process type to continue.
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── STEP 3: File Upload ── */}
        {step === 3 && (
          <div className="s1w-body">
            <div className="[display:flex]! [align-items:center] [gap:8px] [font-size:var(--text-md)]! [font-weight:700]! [color:var(--color-ink-900)]! [margin-bottom:-6px]! [&_svg]:[width:16px]! [&_svg]:[height:16px]! [&_svg]:[color:var(--color-link)]!"><Icon.Upload /><span>Select File</span></div>

            {/* ── Region access banner ── */}
            {!isAdmin && allowedRegions !== null && (
              <div className="[padding:14px_16px]! [background:linear-gradient(135deg,_var(--color-brand-50)_0%,_#fff1e6_100%)]! [border:1.5px_solid_#fed7aa]! [&&]:[border-radius:var(--radius-md)]! [display:flex]! [flex-direction:column] [gap:10px]">
                <div className="[display:flex]! [align-items:center] [gap:8px] [font-size:var(--text-base)]! [color:#7c3a00]! [font-weight:700]! [&_svg]:[width:16px]! [&_svg]:[height:16px]! [&_svg]:[color:var(--color-brand-700)]! [&_svg]:[flex-shrink:0]!">
                  <Icon.Info />
                  <strong>Your upload is restricted to the following regions:</strong>
                </div>
                {allowedRegions.length > 0 ? (
                  <div className="[display:flex]! [flex-wrap:wrap] [gap:6px]">
                    {allowedRegions.map(r => (
                      <span key={r} className="[padding:4px_12px]! [background:var(--color-white)]! [border:1.5px_solid_var(--color-brand-400)]! [&&]:[border-radius:var(--radius-lg)]! [font-size:var(--text-sm)]! [font-weight:700]! [color:var(--color-brand-700)]! [white-space:nowrap]">{r}</span>
                    ))}
                  </div>
                ) : (
                  <p className="[font-size:var(--text-base)]! [color:var(--color-red-700)]! [margin:0]! [font-weight:500]!">
                    Your account has no assigned regions. Contact an administrator before uploading.
                  </p>
                )}
              </div>
            )}
            <div role="button" tabIndex={0} onKeyDown={activateOnKey}
              className={`[border:2px_dashed_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-lg)]! [padding:40px_24px]! [display:flex]! [flex-direction:column]! [align-items:center]! [gap:10px]! [cursor:pointer]! [transition:all_0.2s]! [background:var(--color-ink-50)]! [text-align:center]! hover:[border-color:var(--color-brand-500)]! hover:[background:#fff7f0]! hover:[box-shadow:0_0_0_4px_rgba(255,_102,_0,_0.08)]! [&.dragging]:[border-color:var(--color-brand-500)]! [&.dragging]:[background:#fff7f0]! [&.dragging]:[box-shadow:0_0_0_4px_rgba(255,_102,_0,_0.08)]! ${isDragging ? "dragging" : ""}`}
              onClick={() => fileInputRef.current.click()}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
            >
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx" className="hidden!" onChange={onFileChange} />
              <div className="[width:56px]! [height:56px]! [border-radius:var(--radius-lg)]! [background:var(--primary-gradient)]! [color:var(--color-white)]! [display:flex]! [align-items:center] [justify-content:center] [margin-bottom:4px]! [&_svg]:[width:26px]! [&_svg]:[height:26px]!"><Icon.Upload /></div>
              <p className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--color-ink-700)]! [margin:0]! [&_span]:[color:var(--color-link)]! [&_span]:[text-decoration:underline]!">Drag & drop your file here, or <span>click to browse</span></p>
              <p className="[font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [margin:0]!">Supports .xlsx and .csv — optimised for millions of rows</p>
              {parseError && (
                <div className="[display:flex]! [align-items:center] [gap:8px] [padding:8px_14px]! [background:#fee2e2]! [border:1px_solid_#fecaca]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-sm)]! [color:var(--color-red-700)]! [font-weight:500]! [&_svg]:[width:14px]! [&_svg]:[height:14px]!"><Icon.Warning />{parseError}</div>
              )}
            </div>

            <div className="[display:flex]! [flex-direction:column] [gap:10px]">
              <p className="[font-size:var(--text-sm)]! [color:var(--color-ink-500)]! [margin:0]! [font-weight:500]!">Don't have a file? Download a pre-configured template:</p>
              <div className="[display:flex]! [gap:10px] [flex-wrap:wrap] [@media(max-width:600px)]:[flex-direction:column]!">
                <button className="[display:flex]! [align-items:center] [gap:12px] [padding:12px_18px]! [border:1.5px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [background:var(--color-ink-50)]! [cursor:pointer] [transition:all_0.18s]! [flex:1] [min-width:200px] [text-align:left]! hover:[border-color:var(--color-brand-500)]! hover:[background:#fff7f0]! [&:hover_.s1w-template-btn-icon]:[background:var(--color-primary)]! [&:hover_.s1w-template-btn-icon]:[color:var(--color-white)]! [&_strong]:[display:block]! [&_strong]:[font-size:var(--text-base)]! [&_strong]:[color:var(--color-ink-900)]! [&_strong]:[margin-bottom:2px]! [&_small]:[display:block]! [&_small]:[font-size:var(--text-sm)]! [&_small]:[color:var(--color-ink-500)]!" onClick={() => downloadTemplate("excel")}>
                  <span className="s1w-template-btn-icon [width:36px]! [height:36px]! [border-radius:var(--radius-md)]! [background:var(--color-ink-200)]! [display:flex]! [align-items:center] [justify-content:center] [color:var(--color-ink-600)]! [flex-shrink:0] [&_svg]:[width:18px]! [&_svg]:[height:18px]!"><Icon.FileExcel /></span>
                  <span>
                    <strong>Excel Template</strong>
                    <small>With dropdowns, sample data & engineering sheets</small>
                  </span>
                </button>
                <button className="[display:flex]! [align-items:center] [gap:12px] [padding:12px_18px]! [border:1.5px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [background:var(--color-ink-50)]! [cursor:pointer] [transition:all_0.18s]! [flex:1] [min-width:200px] [text-align:left]! hover:[border-color:var(--color-brand-500)]! hover:[background:#fff7f0]! [&:hover_.s1w-template-btn-icon]:[background:var(--color-primary)]! [&:hover_.s1w-template-btn-icon]:[color:var(--color-white)]! [&_strong]:[display:block]! [&_strong]:[font-size:var(--text-base)]! [&_strong]:[color:var(--color-ink-900)]! [&_strong]:[margin-bottom:2px]! [&_small]:[display:block]! [&_small]:[font-size:var(--text-sm)]! [&_small]:[color:var(--color-ink-500)]!" onClick={() => downloadTemplate("csv")}>
                  <span className="s1w-template-btn-icon [width:36px]! [height:36px]! [border-radius:var(--radius-md)]! [background:var(--color-ink-200)]! [display:flex]! [align-items:center] [justify-content:center] [color:var(--color-ink-600)]! [flex-shrink:0] [&_svg]:[width:18px]! [&_svg]:[height:18px]!"><Icon.File /></span>
                  <span>
                    <strong>CSV Template</strong>
                    <small>Lightweight flat file — best for large datasets</small>
                  </span>
                </button>
              </div>
            </div>

            {/* Config summary pill */}
            <div className="[display:flex]! [gap:8px] [flex-wrap:wrap]">
              <span className={`[padding:4px_12px]! [border-radius:var(--radius-lg)]! [font-size:var(--text-sm)]! [font-weight:700]! [letter-spacing:0.3px]! s1w-config-pill--${tier === "1" ? "blue" : tier === "3" ? "green" : "orange"}`}>
                {tier === "1" ? "Tier 1" : tier === "3" ? "Tier 3" : "Auto-detect"}
              </span>
              <span className="[padding:4px_12px]! [border-radius:var(--radius-lg)]! [font-size:var(--text-sm)]! [font-weight:700]! [letter-spacing:0.3px] [background:var(--color-ink-100)]! [color:var(--color-ink-600)]!">
                {processScope === "all"
                  ? "All Processes"
                  : `${selectedProcesses.length} process${selectedProcesses.length !== 1 ? "es" : ""} selected`}
              </span>
            </div>
          </div>
        )}

        {/* ── STEP 4: Column Mapping ── */}
        {step === 4 && (
          <div className="s1w-body">
            {/* ── Region access banner ── */}
            {!isAdmin && allowedRegions !== null && allowedRegions.length > 0 && (
              <div className="[padding:14px_16px]! [background:linear-gradient(135deg,_var(--color-brand-50)_0%,_#fff1e6_100%)]! [border:1.5px_solid_#fed7aa]! [&&]:[border-radius:var(--radius-md)]! [display:flex]! [flex-direction:column]! [gap:10px]! [flex-direction:row] [align-items:center] [gap:8px] [padding:10px_14px]! [&_svg]:[width:16px]! [&_svg]:[height:16px]! [&_svg]:[color:var(--color-brand-700)]! [&_svg]:[flex-shrink:0]! [&_span]:[font-size:var(--text-sm)]! [&_span]:[color:#7c3a00]! [&_span]:[line-height:1.4]!">
                <Icon.Info />
                <span>
                  <strong>Allowed regions:</strong>{" "}
                  {allowedRegions.join(" · ")}
                </span>
              </div>
            )}
            {!isAdmin && allowedRegions !== null && allowedRegions.length === 0 && (
              <div className="[display:flex]! [align-items:flex-start] [gap:10px] [padding:12px_16px]! [background:var(--color-brand-50)]! [border:1px_solid_#fed7aa]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [color:var(--color-brand-700)]! [line-height:1.5] [&_svg]:[width:16px]! [&_svg]:[height:16px]! [&_svg]:[flex-shrink:0]! [&_svg]:[margin-top:1px]!">
                <Icon.Warning />
                <span><strong>No accessible regions.</strong> Your account has no assigned regions. All rows will be rejected. Contact an administrator.</span>
              </div>
            )}
            {file && (
              <div className="[display:flex]! [align-items:center] [gap:12px] [padding:12px_16px]! [background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]!">
                <div className="[width:36px]! [height:36px]! [border-radius:var(--radius-md)]! [background:var(--color-ink-200)]! [display:flex]! [align-items:center] [justify-content:center] [color:var(--color-ink-600)]! [flex-shrink:0] [&_svg]:[width:18px]! [&_svg]:[height:18px]!"><Icon.File /></div>
                <div className="s1w-file-badge-info">
                  <p className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--color-ink-900)]! [margin:0_0_2px]!">{file.name}</p>
                  <p className="[font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [margin:0]!">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
                {headers.length > 0 && (
                  <div className="[margin-left:auto]! [display:flex]! [align-items:center] [gap:6px] [padding:4px_10px]! [background:var(--color-green-50)]! [border:1px_solid_#a7f3d0]! [&&]:[border-radius:var(--radius-lg)]! [font-size:var(--text-sm)]! [font-weight:600]! [color:#047857]! [&_svg]:[width:13px]! [&_svg]:[height:13px]!"><Icon.Wand /><span>{Object.keys(mapping).length} auto-detected</span></div>
                )}
              </div>
            )}

            {headers.length === 0 && (
              <div className="[display:flex]! [align-items:flex-start] [gap:10px] [padding:12px_16px]! [background:var(--color-blue-50)]! [border:1px_solid_#bfdbfe]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [color:var(--color-blue-700)]! [line-height:1.5] [&_svg]:[width:16px]! [&_svg]:[height:16px]! [&_svg]:[flex-shrink:0]! [&_svg]:[margin-top:1px]!">
                <Icon.Info />
                <span>Excel file — processed server-side. Type column names exactly as they appear in your file, or leave blank to skip that field.</span>
              </div>
            )}

            {headers.length > 0 && missingRequired.length > 0 && (
              <div className="[display:flex]! [align-items:flex-start] [gap:10px] [padding:12px_16px]! [background:var(--color-brand-50)]! [border:1px_solid_#fed7aa]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [color:var(--color-brand-700)]! [line-height:1.5] [&_svg]:[width:16px]! [&_svg]:[height:16px]! [&_svg]:[flex-shrink:0]! [&_svg]:[margin-top:1px]!">
                <Icon.Warning />
                <span><strong>{missingRequired.length} required field{missingRequired.length > 1 ? "s" : ""} not mapped:</strong> {missingRequired.map(f => f.label).join(", ")}</span>
              </div>
            )}

            {/* Search bar */}
            <div className="[position:relative] [display:flex]! [align-items:center]">
              <div className="[position:absolute] [left:12px] [color:var(--color-ink-600)]! [display:flex]! [align-items:center] [&_svg]:[width:16px]! [&_svg]:[height:16px]!"><Icon.Search /></div>
              <input
                className="[width:100%]! [padding:10px_12px_10px_38px]! [border:1.5px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [background:var(--color-ink-50)]! [font-size:var(--text-base)]! [color:var(--color-ink-900)]! [outline:none]! [transition:border-color_0.15s]! [font-family:inherit]! focus:[border-color:var(--color-brand-500)]! focus:[background:var(--color-white)]! focus:[box-shadow:0_0_0_3px_rgba(255,102,0,0.08)]! placeholder:[color:var(--color-ink-400)]!"
                type="text"
                placeholder="Search fields by name, key, or description…"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button className="[position:absolute] [right:10px] [background:transparent]! [border:none]! [cursor:pointer] [color:var(--color-ink-600)]! [display:flex]! [align-items:center] [padding:4px]! [&&]:[border-radius:var(--radius-sm)]! [transition:color_0.15s]! hover:[color:var(--color-ink-700)]! [&_svg]:[width:14px]! [&_svg]:[height:14px]!" onClick={() => setSearchQuery("")}><Icon.Close /></button>
              )}
            </div>

            {/* Factor selector */}
            <div className="[display:flex]! [align-items:center] [gap:12px] [flex-wrap:wrap]">
              <label className="[font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [font-weight:500]! [flex-shrink:0]">Default factor when not specified in file:</label>
              <NativeSelect className="[flex:1] [min-width:200px] [padding:8px_12px]! [border:1.5px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [background:var(--color-ink-50)]! [font-size:var(--text-sm)]! [color:var(--color-ink-900)]! [outline:none]! [cursor:pointer] [font-family:inherit]! [transition:border-color_0.15s]! focus:[border-color:var(--color-brand-500)]!" value={globalFactor} onChange={e => setGlobalFactor(e.target.value)}>
                <option value="auto">Auto-detect from file</option>
                <option value="default">Force Standard (API Compendium)</option>
                <option value="custom">Force Custom Factors</option>
                <option value="specific">Force Tier 3 (site data)</option>
              </NativeSelect>
            </div>

            <label className="[display:flex]! [align-items:center] [gap:12px] [flex-wrap:wrap] gap-[8px]! cursor-pointer!">
              <input type="checkbox" checked={overwrite} onChange={e => setOverwrite(e.target.checked)} />
              <span className="[font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [font-weight:500]! [flex-shrink:0]">
                Overwrite records that already exist (same facility, month and source). Overwritten records go back to Pending review.
              </span>
            </label>

            {/* Field groups */}
            <div className="[display:flex]! [flex-direction:column] [gap:10px]">
              {FIELD_GROUPS.map(group => (
                <FieldGroup
                  key={group.id}
                  group={group}
                  headers={headers}
                  mapping={mapping}
                  setMapping={setMapping}
                  searchQuery={searchQuery}
                  tier={tier}
                  processScope={processScope}
                  selectedProcesses={selectedProcesses}
                />
              ))}
            </div>
          </div>
        )}

        {/* ── STEP 5: Processing ── */}
        {step === 5 && jobId && (
          <div className="s1w-body [padding:0]!">
            <UploadProgress
              jobId={jobId}
              onComplete={() => { if (onUploadSuccess) onUploadSuccess(); onClose(); }}
              onCancel={onClose}
            />
          </div>
        )}

        {/* ── Footer ── */}
        {step !== 5 && (
          <div className="[display:flex]! [align-items:center] [justify-content:space-between] [padding:14px_24px]! [border-top:1px_solid_var(--color-ink-200)]! [background:var(--color-ink-50)]! [flex-shrink:0]">
            <button
              className="[display:flex]! [align-items:center] [gap:6px] [padding:9px_18px]! [background:transparent]! [border:1.5px_solid_var(--color-ink-200)]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [font-weight:600]! [color:var(--color-ink-500)]! [cursor:pointer] [transition:all_0.15s]! [font-family:inherit]! hover:[background:var(--color-ink-100)]! hover:[border-color:var(--color-ink-300)]! hover:[color:var(--color-ink-700)]! [&_svg]:[width:15px]! [&_svg]:[height:15px]!"
              onClick={step === 1 ? onClose : () => setStep(s => s - 1)}
            >
              {step === 1 ? <><Icon.Close /> Cancel</> : <><Icon.ArrowLeft /> Back</>}
            </button>

            <div className="[display:flex]! [align-items:center] [gap:10px]">
              {step < 4 && (
                <button
                  className="[display:flex]! [align-items:center] [gap:6px] [padding:9px_22px]! [background:var(--primary-gradient)]! [border:none]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [font-weight:700]! [color:var(--color-white)]! [cursor:pointer] [transition:all_0.18s]! [box-shadow:0_2px_8px_rgba(255,_102,_0,_0.3)]! [font-family:inherit]! hover:[background:var(--primary-gradient)]! hover:[box-shadow:0_4px_12px_rgba(255,_102,_0,_0.4)]! hover:[transform:translateY(-1px)] disabled:[background:var(--color-ink-200)]! disabled:[color:var(--color-ink-400)]! disabled:[cursor:not-allowed] disabled:[box-shadow:none]! disabled:[transform:none] [&_svg]:[width:15px]! [&_svg]:[height:15px]!"
                  onClick={() => setStep(s => s + 1)}
                  disabled={!canGoNext()}
                >
                  Next <Icon.ChevronRight />
                </button>
              )}
              {step === 4 && (
                <button
                  className="[display:flex]! [align-items:center] [gap:6px] [padding:9px_22px]! [background:var(--primary-gradient)]! [border:none]! [&&]:[border-radius:var(--radius-md)]! [font-size:var(--text-base)]! [font-weight:700]! [color:var(--color-white)]! [cursor:pointer] [transition:all_0.18s]! [box-shadow:0_2px_8px_rgba(255,_102,_0,_0.3)]! [font-family:inherit]! hover:[background:var(--primary-gradient)]! hover:[box-shadow:0_4px_12px_rgba(255,_102,_0,_0.4)]! hover:[transform:translateY(-1px)] disabled:[background:var(--color-ink-200)]! disabled:[color:var(--color-ink-400)]! disabled:[cursor:not-allowed] disabled:[box-shadow:none]! disabled:[transform:none] [&_svg]:[width:15px]! [&_svg]:[height:15px]!"
                  onClick={handleSubmit}
                  disabled={isSubmitting || (!canSubmit && headers.length > 0) || (!isAdmin && allowedRegions !== null && allowedRegions.length === 0)}
                >
                  {isSubmitting ? <span className="[width:15px]! [height:15px]! [border-radius:50%]! [border:2px_solid_rgba(255,255,255,0.4)]! [&&]:[border-top-color:var(--color-white)]! [animation:s1w-spin_0.7s_linear_infinite]! [display:inline-block]!" /> : <Icon.Processing />}
                  {isSubmitting ? "Starting…" : "Start Import"}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
);

export default Scope1ImportWizardScope1Bulk;
