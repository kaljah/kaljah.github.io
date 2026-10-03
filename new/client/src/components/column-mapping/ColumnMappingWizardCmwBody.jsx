import React from "react";
import { NativeSelect } from "../../ui/NativeSelect";

// Extracted from ColumnMappingWizard.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const ColumnMappingWizardCmwBody = ({ Icons, MappingRow, activeOptional, activeRequired, file, globalFactor, headers, mapping, missingRequired, setGlobalFactor, setMapping, setShowOptional, showOptional }) => (
<div className="cmw-body">
            {/* File badge */}
            <div className="[display:flex]! [align-items:center] [gap:12px] [background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [padding:12px_16px]! [margin-bottom:16px]!">
              <div className="[width:36px]! [height:36px]! [background:#e0fce7]! [border-radius:var(--radius-md)]! [display:flex]! [align-items:center] [justify-content:center] [color:var(--color-green-700)]! [flex-shrink:0] [&_svg]:[width:18px]! [&_svg]:[height:18px]!">
                <Icons.FileXlsx />
              </div>
              <div>
                <p className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--color-ink-900)]! [margin:0_0_2px]!">{file?.name}</p>
                <p className="[font-size:var(--text-sm)]! [color:var(--color-ink-600)]! [margin:0]!">
                  {file ? (file.size / 1024).toFixed(1) + " KB" : ""}
                </p>
              </div>
              {headers.length > 0 && (
                <div className="[margin-left:auto]! [display:flex]! [align-items:center] [gap:6px] [background:var(--color-blue-50)]! [color:var(--color-blue-600)]! [border-radius:var(--radius-lg)]! [padding:4px_12px]! [font-size:var(--text-sm)]! [font-weight:600]! [&_svg]:[width:14px]! [&_svg]:[height:14px]!">
                  <Icons.Wand />
                  <span>
                    {Object.keys(mapping).length} columns auto-detected
                  </span>
                </div>
              )}
            </div>

            {/* Excel note */}
            {headers.length === 0 && (
              <div className="cmw-info-banner">
                <Icons.Warning />
                <span>
                  Excel files are processed server-side. If your column names
                  match the template exactly, mapping is automatic. Otherwise,
                  use the table below to tell us what each column should map to.
                </span>
              </div>
            )}

            {/* Missing required fields warning */}
            {headers.length > 0 && missingRequired.length > 0 && (
              <div className="cmw-warning-banner">
                <Icons.Warning />
                <span>
                  <strong>
                    {missingRequired.length} required field
                    {missingRequired.length > 1 ? "s" : ""} not mapped:
                  </strong>{" "}
                  {missingRequired.map((f) => f.label).join(", ")}
                </span>
              </div>
            )}

            {/* Mapping table */}
            <div className="[margin-bottom:16px]!">
              <div className="[font-size:var(--text-sm)]! [font-weight:700]! [text-transform:uppercase]! [letter-spacing:0.06em] [color:var(--color-ink-500)]! [margin-bottom:8px]!">Required Fields</div>
              <div className="[border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [overflow:hidden]!">
                <div className="[display:grid]! [grid-template-columns:1.8fr_2fr_2fr_60px] [gap:12px] [padding:10px_16px]! [background:var(--color-ink-50)]! [border-bottom:1px_solid_var(--color-ink-200)]! [font-size:var(--text-xs)]! [font-weight:700]! [text-transform:uppercase]! [letter-spacing:0.05em] [color:var(--color-ink-600)]!">
                  <span>System Field</span>
                  <span>Description</span>
                  <span>Your Column</span>
                  <span>Status</span>
                </div>

                {activeRequired.map((field) => (
                  <MappingRow
                    key={field.key}
                    field={field}
                    headers={headers}
                    value={mapping[field.key] || ""}
                    onChange={(val) =>
                      setMapping((m) => ({ ...m, [field.key]: val }))
                    }
                  />
                ))}
              </div>

              <button
                className="[display:flex]! [align-items:center] [gap:6px] [padding:8px_12px]! [margin-top:10px]! [background:transparent]! [border:none]! [color:var(--color-ink-500)]! [font-size:var(--text-sm)]! [font-weight:500]! [cursor:pointer] [border-radius:var(--radius-sm)]! [transition:all_0.15s]! [&_svg]:[width:16px]! [&_svg]:[height:16px]! hover:[background:var(--color-ink-100)]! hover:[color:var(--color-ink-700)]!"
                onClick={() => setShowOptional((v) => !v)}
              >
                <Icons.ChevronRight />
                {showOptional ? "Hide" : "Show"} optional fields (
                {activeOptional.length})
              </button>

              {showOptional && (
                <>
                  <div
                    className="[font-size:var(--text-sm)]! [font-weight:700]! [text-transform:uppercase]! [letter-spacing:0.06em] [color:var(--color-ink-500)]! [margin-bottom:8px]! mt-[12px]!"
                   
                  >
                    Optional Fields
                  </div>
                  <div className="[border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [overflow:hidden]!">
                    <div className="[display:grid]! [grid-template-columns:1.8fr_2fr_2fr_60px] [gap:12px] [padding:10px_16px]! [background:var(--color-ink-50)]! [border-bottom:1px_solid_var(--color-ink-200)]! [font-size:var(--text-xs)]! [font-weight:700]! [text-transform:uppercase]! [letter-spacing:0.05em] [color:var(--color-ink-600)]!">
                      <span>System Field</span>
                      <span>Description</span>
                      <span>Your Column</span>
                      <span>Status</span>
                    </div>
                    {activeOptional.map((field) => (
                      <MappingRow
                        key={field.key}
                        field={field}
                        headers={headers}
                        value={mapping[field.key] || ""}
                        onChange={(val) =>
                          setMapping((m) => ({ ...m, [field.key]: val }))
                        }
                      />
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Factor type override */}
            <div className="[display:flex]! [align-items:center] [gap:16px] [padding:14px_16px]! [background:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! [border-radius:var(--radius-md)]! [margin-top:4px]!">
              <label className="[font-size:var(--text-sm)]! [font-weight:500]! [color:var(--color-ink-600)]! [flex:1]">
                Default factor type when not specified in file
              </label>
              <NativeSelect
                className="[padding:7px_12px]! [border:1.5px_solid_var(--color-ink-200)]! [border-radius:var(--radius-sm)]! [font-size:var(--text-sm)]! [color:var(--color-ink-700)]! [background:var(--color-white)]! [outline:none]! [min-width:220px] [transition:border-color_0.15s]! focus:[border-color:var(--color-blue-600)]!"
                value={globalFactor}
                onChange={(e) => setGlobalFactor(e.target.value)}
              >
                <option value="auto">Auto-detect from file</option>
                <option value="default">Force Standard (API Compendium)</option>
                <option value="custom">Force Custom Factors</option>
              </NativeSelect>
            </div>
          </div>
);

export default ColumnMappingWizardCmwBody;
