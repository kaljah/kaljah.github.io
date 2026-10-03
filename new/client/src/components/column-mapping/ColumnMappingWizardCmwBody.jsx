import React from "react";
import { NativeSelect } from "../../ui/NativeSelect";

// Extracted from ColumnMappingWizard.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const ColumnMappingWizardCmwBody = ({ Icons, MappingRow, activeOptional, activeRequired, file, globalFactor, headers, mapping, missingRequired, setGlobalFactor, setMapping, setShowOptional, showOptional }) => (
<div className="cmw-body">
            {/* File badge */}
            <div className="cmw-file-badge">
              <div className="cmw-file-badge-icon">
                <Icons.FileXlsx />
              </div>
              <div>
                <p className="cmw-file-name">{file?.name}</p>
                <p className="cmw-file-size">
                  {file ? (file.size / 1024).toFixed(1) + " KB" : ""}
                </p>
              </div>
              {headers.length > 0 && (
                <div className="cmw-auto-badge">
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
            <div className="cmw-mapping-container">
              <div className="cmw-mapping-group-label">Required Fields</div>
              <div className="cmw-mapping-table">
                <div className="cmw-mapping-header">
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
                className="cmw-optional-toggle"
                onClick={() => setShowOptional((v) => !v)}
              >
                <Icons.ChevronRight />
                {showOptional ? "Hide" : "Show"} optional fields (
                {activeOptional.length})
              </button>

              {showOptional && (
                <>
                  <div
                    className="cmw-mapping-group-label mt-[12px]!"
                   
                  >
                    Optional Fields
                  </div>
                  <div className="cmw-mapping-table">
                    <div className="cmw-mapping-header">
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
            <div className="cmw-factor-row">
              <label className="cmw-factor-label">
                Default factor type when not specified in file
              </label>
              <NativeSelect
                className="cmw-factor-select"
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
