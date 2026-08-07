import React, { useState, useRef, useEffect } from 'react';
import { NavLink, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './Sidebar.css';

const Sidebar = () => {
    const { logout, user } = useAuth();
    const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
    const accountMenuRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (accountMenuRef.current && !accountMenuRef.current.contains(event.target)) {
                setIsAccountMenuOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleLogout = () => {
        setIsAccountMenuOpen(false);
        logout();
    };

    return (
        <aside className="sidebar">
            {/* Header */}
            <div className="sidebar-header">
                <div className="logo-box">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 20V10M18 20V4M6 20v-4" />
                    </svg>
                </div>
                <span className="brand-text">GHG Reporting</span>
            </div>

            <nav style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
                <ul className="nav-links">
                    {user?.role !== 'it_admin' && (
                        <>
                            <li className="nav-item">
                                <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title="Dashboard">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                                        <rect x="3" y="3" width="7" height="7"></rect>
                                        <rect x="14" y="3" width="7" height="7"></rect>
                                        <rect x="14" y="14" width="7" height="7"></rect>
                                        <rect x="3" y="14" width="7" height="7"></rect>
                                    </svg>
                                    <span className="nav-label">Dashboard</span>
                                </NavLink>
                            </li>
                            <li className="nav-item">
                                <NavLink to="/carbon-intensity" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title="Carbon Intensity">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                                        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                                    </svg>
                                    <span className="nav-label">Carbon Intensity</span>
                                </NavLink>
                            </li>
                            <li className="nav-item">
                                <NavLink to="/methane-intensity" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title="Methane Intensity">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                                        <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2" />
                                    </svg>
                                    <span className="nav-label">Methane Intensity</span>
                                </NavLink>
                            </li>
                            <li className="nav-item">
                                <NavLink to="/emissions" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title="Calculations">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                                        <rect x="4" y="2" width="16" height="20" rx="2" />
                                        <line x1="8" y1="6" x2="16" y2="6" />
                                        <line x1="8" y1="10" x2="16" y2="10" />
                                        <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01M16 18h.01" />
                                    </svg>
                                    <span className="nav-label">Calculations</span>
                                </NavLink>
                            </li>
                            <li className="nav-item">
                                <NavLink to="/methane-explorer" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title="Emissions Map">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                                        <circle cx="12" cy="12" r="10"></circle>
                                        <line x1="2" y1="12" x2="22" y2="12"></line>
                                        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                                    </svg>
                                    <span className="nav-label">Emissions Map</span>
                                </NavLink>
                            </li>
                            <li className="nav-item">
                                <NavLink to="/manage-data" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title="Manage Data">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                                        <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                                        <line x1="12" y1="22.08" x2="12" y2="12" />
                                    </svg>
                                    <span className="nav-label">Manage Data</span>
                                </NavLink>
                            </li>
                            <li className="nav-item">
                                <NavLink to="/reports" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title="Reports">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                                        <polyline points="13 2 13 9 20 9" />
                                    </svg>
                                    <span className="nav-label">Reports</span>
                                </NavLink>
                            </li>
                            <li className="nav-item">
                                <NavLink to="/reference-data" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title="Reference Data">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                                        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                                        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                                    </svg>
                                    <span className="nav-label">Reference Data</span>
                                </NavLink>
                            </li>
                            <li className="nav-item">
                                <NavLink to="/uncertainty" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title="Uncertainty">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                                        <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path>
                                        <path d="M12 18v.01"></path>
                                        <path d="M12 14a2 2 0 0 0 .914-3.782 1.98 1.98 0 0 0-2.414.483"></path>
                                    </svg>
                                    <span className="nav-label">Uncertainty</span>
                                </NavLink>
                            </li>
                        </>
                    )}
                    {user?.role === 'admin' && (
                        <li className="nav-item">
                            <NavLink to="/audit-trail" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title="Audit Trail">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                                    <path d="M9 11l3 3L22 4"></path>
                                    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
                                </svg>
                                <span className="nav-label">Audit Trail</span>
                            </NavLink>
                        </li>
                    )}
                    {user?.role === 'it_admin' && (
                        <li className="nav-item">
                            <NavLink to="/user-management" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} title="IT Management">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                                    <circle cx="9" cy="7" r="4"></circle>
                                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                                    <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                                </svg>
                                <span className="nav-label">IT Management</span>
                            </NavLink>
                        </li>
                    )}
                </ul>
            </nav>

            {/* Settings & Standards Link Right Above User Profile */}
            <div className="sidebar-settings-pin">
                <NavLink 
                    to="/settings" 
                    className={({ isActive }) => `nav-link sidebar-settings-btn ${isActive ? 'active' : ''}`}
                    title="Settings & Standards"
                    id="sidebar-settings-link"
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="nav-icon">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                    </svg>
                    <span className="nav-label">Settings</span>
                </NavLink>
            </div>

            {/* Account area */}
            <div className="account-wrapper" ref={accountMenuRef}>
                <div
                    className={`user-profile-sidebar ${isAccountMenuOpen ? 'active' : ''}`}
                    onClick={(e) => { e.stopPropagation(); setIsAccountMenuOpen(o => !o); }}
                    id="profile-toggle"
                >
                    <div className="avatar-small" id="user-avatar">
                        {user?.fullName ? user.fullName[0].toUpperCase() : 'U'}
                    </div>
                    <div className="user-info">
                        <div className="user-name" id="user-name-sidebar">{user?.fullName || 'User Name'}</div>
                        <div className="user-role" id="user-role-sidebar">{user?.jobTitle || 'Sustainability Manager'}</div>
                    </div>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="chevron-icon">
                        <polyline points="18 15 12 9 6 15"></polyline>
                    </svg>
                </div>

                <div className={`account-dropdown ${isAccountMenuOpen ? 'visible' : ''}`} id="account-menu">
                    <div className="dropdown-header">
                        <div className="user-name-full" id="user-name-drop">{user?.fullName || 'User Name'}</div>
                        <div className="user-email-drop">{user?.email || 'manager@sustainability.com'}</div>
                    </div>
                    <div className="dropdown-divider"></div>
                    <Link to="/settings" className="dropdown-item" onClick={() => setIsAccountMenuOpen(false)}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="3"></circle>
                            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                        </svg>
                        Settings & Standards
                    </Link>
                    <Link to="/audit-trail" className="dropdown-item" onClick={() => setIsAccountMenuOpen(false)}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                            <line x1="16" y1="13" x2="8" y2="13"></line>
                            <line x1="16" y1="17" x2="8" y2="17"></line>
                        </svg>
                        Audit Trail
                    </Link>
                    <div className="dropdown-divider"></div>
                    <button id="logout-btn-drop" className="dropdown-item logout-item" onClick={handleLogout}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                            <polyline points="16 17 21 12 16 7"></polyline>
                            <line x1="21" y1="12" x2="9" y2="12"></line>
                        </svg>
                        Sign Out
                    </button>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
