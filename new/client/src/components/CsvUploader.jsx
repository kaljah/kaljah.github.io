import React, { useState, useRef } from 'react';
import api from '../api';
import ColumnMappingWizard from './ColumnMappingWizard';

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

            <div className="csv-uploader-entry">
                <button
                    className="csv-upload-trigger"
                    onClick={() => setShowWizard(true)}
                >
                    {/* Upload cloud SVG */}
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="16 16 12 12 8 16" />
                        <line x1="12" y1="12" x2="12" y2="21" />
                        <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
                    </svg>
                    Import Data File
                </button>
            </div>
        </>
    );
};

export default CsvUploader;
