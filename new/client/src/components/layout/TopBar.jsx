import React, { useState, useRef, useEffect } from 'react';
import { Bell, User, ChevronDown } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useLayout } from '../../context/LayoutContext';
import NotificationCenter from '../NotificationCenter';
import './TopBar.css';

const TopBar = () => {
    const { user, logout } = useAuth();
    const { topBarLeft, topBarRight } = useLayout();
    const [isProfileOpen, setIsProfileOpen] = useState(false);
    const profileRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (profileRef.current && !profileRef.current.contains(event.target)) {
                setIsProfileOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <header className="top-bar">
            <div className="top-bar-left-section">
                <div className="breadcrumbs">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="3" y1="12" x2="21" y2="12" />
                        <line x1="3" y1="6" x2="21" y2="6" />
                        <line x1="3" y1="18" x2="21" y2="18" />
                    </svg>
                    <span>Dashboard</span>
                </div>
                {topBarLeft && <div className="top-bar-injected-left">{topBarLeft}</div>}
            </div>

            <div className="top-actions">
                {topBarRight}

                <NotificationCenter />

                <div style={{ position: 'relative' }} ref={profileRef}>
                    <button
                        className="icon-button"
                        onClick={() => setIsProfileOpen(!isProfileOpen)}
                    >
                        <User size={20} />
                    </button>
                    {isProfileOpen && (
                        <div className="top-profile-dropdown">
                            <div className="dropdown-divider-top"></div>
                            <button className="top-drop-item logout-btn-top" onClick={logout}>Sign Out</button>
                        </div>
                    )}
                </div>
                <span className="user-name-top">{user?.fullName?.split(' ')[0] || 'User'}</span>
            </div>
        </header>
    );
};

export default TopBar;
