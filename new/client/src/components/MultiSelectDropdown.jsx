
import React, { useState, useRef, useEffect } from 'react';

const MultiSelectDropdown = ({ options, selectedValues, onChange, label = "Select..." }) => {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef(null);

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const toggleOption = (value) => {
        const newSelected = selectedValues.includes(value)
            ? selectedValues.filter(v => v !== value)
            : [...selectedValues, value];
        onChange(newSelected);
    };

    const handleSelectAll = () => {
        if (selectedValues.length === options.length) {
            onChange([]);
        } else {
            onChange(options.map(o => o.value));
        }
    };

    return (
        <div className="custom-dropdown" ref={dropdownRef} style={{ width: '100%', position: 'relative' }}>
            <div
                className="dropdown-selected"
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    padding: '10px 12px',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    background: 'var(--bg-card)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    minHeight: '42px'
                }}
            >
                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {selectedValues.length === 0
                        ? label
                        : selectedValues.length === options.length
                            ? "All Selected"
                            : `${selectedValues.length} Selected`}
                </span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M6 9l6 6 6-6" />
                </svg>
            </div>

            {isOpen && (
                <div className="dropdown-options" style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    zIndex: 100,
                    maxHeight: '250px',
                    overflowY: 'auto',
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-card)',
                    borderRadius: '6px',
                    marginTop: '4px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}>
                    <div
                        className="dropdown-option"
                        onClick={handleSelectAll}
                        style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-color)', fontWeight: 600, cursor: 'pointer' }}
                    >
                        {selectedValues.length === options.length ? "Deselect All" : "Select All"}
                    </div>
                    {options.map(opt => (
                        <div
                            key={opt.value}
                            className="dropdown-option"
                            onClick={() => toggleOption(opt.value)}
                            style={{
                                padding: '8px 12px',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                background: selectedValues.includes(opt.value) ? 'var(--bg-hover)' : 'transparent'
                            }}
                        >
                            <input
                                type="checkbox"
                                checked={selectedValues.includes(opt.value)}
                                readOnly
                                style={{ cursor: 'pointer' }}
                            />
                            <span>
                                {opt.label}
                                {opt.subLabel && <span style={{
                                    fontSize: '0.72rem',
                                    color: '#94a3b8',
                                    marginLeft: '4px',
                                    fontWeight: 500
                                }}> - {opt.subLabel}</span>}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default MultiSelectDropdown;
