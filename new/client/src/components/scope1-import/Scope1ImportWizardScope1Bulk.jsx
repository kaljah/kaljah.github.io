import React from "react";
import { NativeSelect } from "../../ui/NativeSelect";
import UploadProgress from "../UploadProgress";
import { activateOnKey } from "../../utils/a11yKeys";

// Extracted from Scope1ImportWizard.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const Scope1ImportWizardScope1Bulk = ({ FIELD_GROUPS, FieldGroup, Icon, ModeCard, PROCESS_CATALOGUE, ProcessTile, StepBar, allowedRegions, canGoNext, canSubmit, downloadTemplate, file, fileInputRef, globalFactor, handleSubmit, headers, isAdmin, isDragging, isSubmitting, jobId, mapping, missingRequired, onClose, onDrop, onFileChange, onUploadSuccess, overwrite, parseError, processScope, searchQuery, selectedProcesses, setGlobalFactor, setIsDragging, setMapping, setOverwrite, setProcessScope, setSearchQuery, setStep, setTier, step, tier, toggleProcess }) => (
<div className="s1w-modal">
        {/* Header */}
        <div className="s1w-header">
          <div className="s1w-header-left">
            <div className="s1w-header-icon"><Icon.Activity /></div>
            <div>
              <h2 className="s1w-title">Scope 1 Bulk Import</h2>
              <p className="s1w-subtitle">Upload emissions data from CSV or Excel</p>
            </div>
          </div>
          <button className="s1w-close" onClick={onClose}><Icon.Close /></button>
        </div>

        {/* Step bar */}
        <StepBar current={step} />

        {/* ── STEP 1: Upload Mode ── */}
        {step === 1 && (
          <div className="s1w-body">
            <div className="s1w-section-title">
              <Icon.Settings />
              <span>Select Calculation Tier</span>
            </div>
            <p className="s1w-section-desc">
              Choose how emissions will be calculated for each row in your file.
            </p>
            <div className="s1w-mode-grid">
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
            <div className="s1w-info-banner">
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
            <div className="s1w-section-title"><Icon.Layers /><span>Process Scope</span></div>
            <p className="s1w-section-desc">Does your file contain data for all process types, or a specific process?</p>
            <div className="s1w-scope-cards">
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
              <div className="s1w-process-grid-wrap">
                <p className="s1w-process-grid-label">Select which processes are in your file:</p>
                <div className="s1w-process-grid">
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
                  <div className="s1w-warn-inline">
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
            <div className="s1w-section-title"><Icon.Upload /><span>Select File</span></div>

            {/* ── Region access banner ── */}
            {!isAdmin && allowedRegions !== null && (
              <div className="s1w-access-banner">
                <div className="s1w-access-banner-header">
                  <Icon.Info />
                  <strong>Your upload is restricted to the following regions:</strong>
                </div>
                {allowedRegions.length > 0 ? (
                  <div className="s1w-access-region-list">
                    {allowedRegions.map(r => (
                      <span key={r} className="s1w-access-region-pill">{r}</span>
                    ))}
                  </div>
                ) : (
                  <p className="s1w-access-no-regions">
                    Your account has no assigned regions. Contact an administrator before uploading.
                  </p>
                )}
              </div>
            )}
            <div role="button" tabIndex={0} onKeyDown={activateOnKey}
              className={`s1w-dropzone ${isDragging ? "dragging" : ""}`}
              onClick={() => fileInputRef.current.click()}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
            >
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx" className="hidden!" onChange={onFileChange} />
              <div className="s1w-dropzone-icon"><Icon.Upload /></div>
              <p className="s1w-dropzone-text">Drag & drop your file here, or <span>click to browse</span></p>
              <p className="s1w-dropzone-sub">Supports .xlsx and .csv — optimised for millions of rows</p>
              {parseError && (
                <div className="s1w-inline-error"><Icon.Warning />{parseError}</div>
              )}
            </div>

            <div className="s1w-template-section">
              <p className="s1w-template-label">Don't have a file? Download a pre-configured template:</p>
              <div className="s1w-template-btns">
                <button className="s1w-template-btn" onClick={() => downloadTemplate("excel")}>
                  <span className="s1w-template-btn-icon"><Icon.FileExcel /></span>
                  <span>
                    <strong>Excel Template</strong>
                    <small>With dropdowns, sample data & engineering sheets</small>
                  </span>
                </button>
                <button className="s1w-template-btn" onClick={() => downloadTemplate("csv")}>
                  <span className="s1w-template-btn-icon"><Icon.File /></span>
                  <span>
                    <strong>CSV Template</strong>
                    <small>Lightweight flat file — best for large datasets</small>
                  </span>
                </button>
              </div>
            </div>

            {/* Config summary pill */}
            <div className="s1w-config-summary">
              <span className={`s1w-config-pill s1w-config-pill--${tier === "1" ? "blue" : tier === "3" ? "green" : "orange"}`}>
                {tier === "1" ? "Tier 1" : tier === "3" ? "Tier 3" : "Auto-detect"}
              </span>
              <span className="s1w-config-pill s1w-config-pill--neutral">
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
              <div className="s1w-access-banner s1w-access-banner--compact">
                <Icon.Info />
                <span>
                  <strong>Allowed regions:</strong>{" "}
                  {allowedRegions.join(" · ")}
                </span>
              </div>
            )}
            {!isAdmin && allowedRegions !== null && allowedRegions.length === 0 && (
              <div className="s1w-warn-banner">
                <Icon.Warning />
                <span><strong>No accessible regions.</strong> Your account has no assigned regions. All rows will be rejected. Contact an administrator.</span>
              </div>
            )}
            {file && (
              <div className="s1w-file-badge">
                <div className="s1w-file-badge-icon"><Icon.File /></div>
                <div className="s1w-file-badge-info">
                  <p className="s1w-file-name">{file.name}</p>
                  <p className="s1w-file-size">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
                {headers.length > 0 && (
                  <div className="s1w-auto-badge"><Icon.Wand /><span>{Object.keys(mapping).length} auto-detected</span></div>
                )}
              </div>
            )}

            {headers.length === 0 && (
              <div className="s1w-info-banner">
                <Icon.Info />
                <span>Excel file — processed server-side. Type column names exactly as they appear in your file, or leave blank to skip that field.</span>
              </div>
            )}

            {headers.length > 0 && missingRequired.length > 0 && (
              <div className="s1w-warn-banner">
                <Icon.Warning />
                <span><strong>{missingRequired.length} required field{missingRequired.length > 1 ? "s" : ""} not mapped:</strong> {missingRequired.map(f => f.label).join(", ")}</span>
              </div>
            )}

            {/* Search bar */}
            <div className="s1w-search-bar">
              <div className="s1w-search-icon"><Icon.Search /></div>
              <input
                className="s1w-search-input"
                type="text"
                placeholder="Search fields by name, key, or description…"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button className="s1w-search-clear" onClick={() => setSearchQuery("")}><Icon.Close /></button>
              )}
            </div>

            {/* Factor selector */}
            <div className="s1w-factor-row">
              <label className="s1w-factor-label">Default factor when not specified in file:</label>
              <NativeSelect className="s1w-factor-select" value={globalFactor} onChange={e => setGlobalFactor(e.target.value)}>
                <option value="auto">Auto-detect from file</option>
                <option value="default">Force Standard (API Compendium)</option>
                <option value="custom">Force Custom Factors</option>
                <option value="specific">Force Tier 3 (site data)</option>
              </NativeSelect>
            </div>

            <label className="s1w-factor-row gap-[8px]! cursor-pointer!">
              <input type="checkbox" checked={overwrite} onChange={e => setOverwrite(e.target.checked)} />
              <span className="s1w-factor-label">
                Overwrite records that already exist (same facility, month and source). Overwritten records go back to Pending review.
              </span>
            </label>

            {/* Field groups */}
            <div className="s1w-field-groups">
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
          <div className="s1w-body s1w-body--progress">
            <UploadProgress
              jobId={jobId}
              onComplete={() => { if (onUploadSuccess) onUploadSuccess(); onClose(); }}
              onCancel={onClose}
            />
          </div>
        )}

        {/* ── Footer ── */}
        {step !== 5 && (
          <div className="s1w-footer">
            <button
              className="s1w-btn-ghost"
              onClick={step === 1 ? onClose : () => setStep(s => s - 1)}
            >
              {step === 1 ? <><Icon.Close /> Cancel</> : <><Icon.ArrowLeft /> Back</>}
            </button>

            <div className="s1w-footer-right">
              {step < 4 && (
                <button
                  className="s1w-btn-primary"
                  onClick={() => setStep(s => s + 1)}
                  disabled={!canGoNext()}
                >
                  Next <Icon.ChevronRight />
                </button>
              )}
              {step === 4 && (
                <button
                  className="s1w-btn-primary"
                  onClick={handleSubmit}
                  disabled={isSubmitting || (!canSubmit && headers.length > 0) || (!isAdmin && allowedRegions !== null && allowedRegions.length === 0)}
                >
                  {isSubmitting ? <span className="s1w-spinner" /> : <Icon.Processing />}
                  {isSubmitting ? "Starting…" : "Start Import"}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
);

export default Scope1ImportWizardScope1Bulk;
