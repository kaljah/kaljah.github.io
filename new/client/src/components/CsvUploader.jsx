import React, { useState } from "react";
import ColumnMappingWizard from "./ColumnMappingWizard";

/**
 * CsvUploader — Entry point for the bulk data import flow.
 * Shows two buttons:
 *   1. Upload File  → opens the ColumnMappingWizard modal
 *   2. Download Templates → direct API download
 *
 * All mapping + progress logic lives inside ColumnMappingWizard.
 */
const CsvUploader = ({ onUploadSuccess }) => {
  const [showWizard, setShowWizard] = useState(false);

  return (
    <>
      {showWizard && (
        <ColumnMappingWizard
          onClose={() => setShowWizard(false)}
          onUploadSuccess={() => {
            setShowWizard(false);
            if (onUploadSuccess) onUploadSuccess();
          }}
        />
      )}

      <div className="[display:inline-flex]! [align-items:center] inline-block!">
        <button
          className="action-btn bg-[color:#10b981]! p-[6px_14px]! text-[length:0.82rem]! whitespace-nowrap! ml-[12px]! flex! items-center! gap-[6px]!"
         
          onClick={() => setShowWizard(true)}
        >
          {/* Upload icon SVG */}
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="w-[14px]! h-[14px]!"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          Bulk Import CSV
        </button>
      </div>
    </>
  );
};

export default CsvUploader;
