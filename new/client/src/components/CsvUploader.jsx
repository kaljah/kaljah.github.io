import React, { useState } from "react";
import ColumnMappingWizard from "./ColumnMappingWizard";
import { Upload } from "lucide-react";

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

      <div className="[align-items:center] inline-block!">
        <button
          className="action-btn bg-[color:#10b981]! p-[6px_14px]! text-[length:0.82rem]! whitespace-nowrap! ml-[12px]! flex! items-center! gap-[6px]!"
         
          onClick={() => setShowWizard(true)}
        >
          {/* Upload icon SVG */}
          <Upload className="w-[14px]! h-[14px]!" aria-hidden="true" />
          Bulk Import CSV
        </button>
      </div>
    </>
  );
};

export default CsvUploader;
