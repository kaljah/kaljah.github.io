import React from 'react';
import './LoadingSpinner.css';

const LoadingSpinner = ({ size = 'medium', fullScreen = false, message = 'Loading System Resources...' }) => {
    const sizeClass = `spinner-${size}`;

    const LoaderContent = () => (
        <>
            <div className={`modern-loader ${sizeClass}`}>
                <div className="loader-inner"></div>
                <div className="loader-logo">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                    </svg>
                </div>
            </div>
            {message && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                    <div className="loading-message">{message}</div>
                </div>
            )}
        </>
    );

    if (fullScreen) {
        return (
            <div className="loading-fullscreen">
                <LoaderContent />
            </div>
        );
    }

    return (
        <div className="loading-inline">
            <LoaderContent />
        </div>
    );
};

export default LoadingSpinner;
