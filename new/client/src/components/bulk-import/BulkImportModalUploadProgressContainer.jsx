import React from "react";
import { AlertCircle, FileText, Loader2 } from "lucide-react";

// Extracted from BulkImportModal.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const BulkImportModalUploadProgressContainer = ({ file, handleImport, loading, onClose, onImportSuccess, setStep, uploadJobId, uploadStatus }) => (
<div className="upload-progress-container">
            <div
              className="[display:flex]! [align-items:center] [justify-content:center] [gap:12px] [padding:12px]! [background:white]! [border-radius:var(--radius-md)]! [border:1px_solid_rgba(0,_0,_0,_0.1)]! mb-[24px]! p-[16px]! bg-[color:#f8fafc]! rounded-[8px]! flex! items-center! gap-[12px]!"
             
            >
              <FileText size={24} className="text-[color:#2e7d32]!" />
              <div>
                <strong
                  className="block! text-[color:var(--text-primary)]!"
                >
                  {file?.name}
                </strong>
                <span
                  className="text-[length:0.85rem]! text-[color:var(--text-secondary)]!"
                >
                  Ready for import
                </span>
              </div>
            </div>

            {!uploadJobId ? (
              <div
                className="[display:flex]! [justify-content:flex-end] [gap:12px] [margin-top:20px]! flex! justify-center! gap-[12px]!"
               
              >
                <button
                  className="action-btn secondary"
                  onClick={() => setStep(1)}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  className="action-btn bg-[color:#10b981]!"
                  onClick={handleImport}
                  disabled={loading}
                 
                >
                  {loading ? (
                    <Loader2 size={16} className="spin" />
                  ) : (
                    "Start Background Import"
                  )}
                </button>
              </div>
            ) : (
              <div className="[width:100%]! [margin-top:16px]! [display:flex]! [flex-direction:column] [align-items:center]">
                {uploadStatus ? (
                  <>
                    <div
                      className="flex! justify-between! w-full! mb-[8px]!"
                    >
                      <span className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--text-primary)]!">
                        {uploadStatus.status === "completed"
                          ? "Import Complete!"
                          : uploadStatus.status === "failed"
                            ? "Import Failed"
                            : "Processing..."}
                      </span>
                      <span className="[font-size:var(--text-base)]! [font-weight:600]! [color:var(--text-primary)]!">
                        {Math.round(uploadStatus.progress)}%
                      </span>
                    </div>
                    <div className="[width:100%]! [height:12px]! [background:#e5e7eb]! [border-radius:var(--radius-sm)]! [overflow:hidden]! [margin-top:4px]!">
                      <div
                        className="[height:100%]! [border-radius:var(--radius-sm)]! [transition:width_0.3s_ease]!"
                        style={{
                          width: `${uploadStatus.progress}%`,
                          background:
                            uploadStatus.status === "failed"
                              ? "#ef4444"
                              : "#10b981",
                        }}
                      ></div>
                    </div>
                    <div
                      className="[font-size:var(--text-sm)]! [color:var(--text-secondary)]! mt-[8px]! text-center!"
                     
                    >
                      Processed {uploadStatus.processed} of {uploadStatus.total}{" "}
                      rows
                    </div>

                    {uploadStatus.skipped_count > 0 && (
                      <div
                        style={{
                          marginTop: "16px",
                          padding: "12px",
                          background: "#fff1f2",
                          borderRadius: "8px",
                          border: "1px solid #fecdd3",
                          width: "100%",
                        }}
                      >
                        <h5
                          className="text-[color:#be123c]! m-[0_0_8px_0]! flex! items-center! gap-[6px]!"
                        >
                          <AlertCircle size={16} />
                          Skipped Rows ({uploadStatus.skipped_count})
                        </h5>
                        <ul
                          style={{
                            margin: 0,
                            paddingLeft: "20px",
                            fontSize: "0.85rem",
                            color: "#9f1239",
                            maxHeight: "100px",
                            overflowY: "auto",
                          }}
                        >
                          {uploadStatus.skipped_preview
                            ?.slice(0, 5)
                            .map((skip, idx) => (
                              <li key={idx}>
                                Row {skip.row}: {skip.reason}
                              </li>
                            ))}
                          {uploadStatus.skipped_count > 5 && (
                            <li>
                              ...and {uploadStatus.skipped_count - 5} more
                              skipped rows
                            </li>
                          )}
                        </ul>
                      </div>
                    )}

                    {(uploadStatus.status === "completed" ||
                      uploadStatus.status === "failed") && (
                      <div className="mt-[24px]! text-center!">
                        <button
                          className="action-btn"
                          onClick={() => {
                            if (onImportSuccess) onImportSuccess();
                            onClose();
                          }}
                        >
                          Done
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <div
                    className="flex! flex-col! items-center! gap-[12px]!"
                  >
                    <Loader2
                      size={32}
                      className="spin text-[color:#2e7d32]!"
                     
                    />
                    <span className="text-[color:var(--text-secondary)]!">
                      Initializing background job...
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
);

export default BulkImportModalUploadProgressContainer;
