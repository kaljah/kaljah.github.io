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

            <div className="csv-uploader-entry" style={{ display: 'inline-block' }}>
                <button
                    className="action-btn"
                    style={{ background: '#10b981', padding: '6px 14px', fontSize: '0.82rem', whiteSpace: 'nowrap', marginLeft: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                    onClick={() => setShowWizard(true)}
                >
                    {/* Upload icon SVG */}
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: '14px', height: '14px' }}>
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
