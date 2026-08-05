import React, { useState, useEffect } from 'react';
import './Settings.css';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/Toast';
import api from '../api';
import '../pages/Dashboard.css';

const Settings = () => {
    const { user, preferences, updatePreferences } = useAuth();
    const toast = useToast();
    const [activeTab, setActiveTab] = useState('general');
    const [loading, setLoading] = useState(true);

    // Settings State
    const [settings, setSettings] = useState({
        language: 'en',
        theme: 'dark',
        timezone: 'UTC',
        gwpModel: 'AR4',
        consolidation: 'Control',
        notifWeekly: true,
        notifTargets: true,
        notifAudit: false
    });

    // Password Change State
    const [passwordData, setPasswordData] = useState({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
    });

    useEffect(() => {
        // Initialize from global preferences
        if (preferences && Object.keys(preferences).length > 0) {
            setSettings(prev => ({ ...prev, ...preferences }));
        }
        setLoading(false);
    }, [preferences]);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setSettings(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handlePasswordChange = (e) => {
        const { name, value } = e.target;
        setPasswordData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleSave = async () => {
        try {
            await updatePreferences(settings);
            toast.success('Settings saved successfully!');
        } catch (err) {
            console.error("Failed to save settings", err);
            toast.error('Failed to save settings.');
        }
    };

    const handleSavePassword = async () => {
        if (passwordData.newPassword !== passwordData.confirmPassword) {
            toast.error("New passwords do not match.");
            return;
        }
        if (passwordData.newPassword.length < 10) {
            toast.error("Password must be at least 10 characters.");
            return;
        }

        try {
            await api.post('/auth/change-password', {
                currentPassword: passwordData.currentPassword,
                newPassword: passwordData.newPassword
            });
            toast.success('Password changed successfully!');
            setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
        } catch (err) {
            console.error("Failed to change password", err);
            toast.error(err.response?.data?.error || 'Failed to change password.');
        }
    };

    if (loading) return <div className="loading-spinner"></div>;

    return (
        <div className="settings-page">
            <header className="top-bar">
                <div className="breadcrumbs">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '8px' }}>
                        <circle cx="12" cy="12" r="3" />
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                    </svg>
                    <span>Dashboard</span>
                    <span style={{ margin: '0 8px', color: 'var(--text-secondary)' }}>/</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Settings</span>
                </div>
                <div className="top-actions">
                    <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{user?.fullName || 'User'}</span>
                </div>
            </header>

            <div className="settings-container">
                <div className="settings-layout">
                    {/* Sidebar */}
                    <aside className="settings-nav">
                        <div className={`nav-item ${activeTab === 'general' ? 'active' : ''}`} onClick={() => setActiveTab('general')}>
                            <span>General Settings</span>
                        </div>
                        <div className={`nav-item ${activeTab === 'reporting' ? 'active' : ''}`} onClick={() => setActiveTab('reporting')}>
                            <span>Reporting Prefs</span>
                        </div>
                        <div className={`nav-item ${activeTab === 'notifications' ? 'active' : ''}`} onClick={() => setActiveTab('notifications')}>
                            <span>Notifications</span>
                        </div>
                        <div className={`nav-item ${activeTab === 'security' ? 'active' : ''}`} onClick={() => setActiveTab('security')}>
                            <span>Security</span>
                        </div>
                    </aside>

                    {/* Content */}
                    <section>
                        {/* General Tab */}
                        {activeTab === 'general' && (
                            <div className="settings-card">
                                <div className="settings-header">
                                    <h2 className="settings-title">General Settings</h2>
                                    <p className="settings-subtitle">Personalize your experience and application behavior.</p>
                                </div>

                                <div className="grid-forms">
                                    <div className="input-group">
                                        <label>Language</label>
                                        <select name="language" value={settings.language} onChange={handleChange} className="component-select">
                                            <option value="en">English (US)</option>
                                            <option value="fr">French</option>
                                        </select>
                                    </div>
                                    <div className="input-group">
                                        <label>Interface Theme</label>
                                        <select name="theme" value={settings.theme} onChange={handleChange} className="component-select">
                                            <option value="dark">Dark Mode</option>
                                            <option value="light">Light Mode</option>
                                        </select>
                                    </div>
                                    <div className="input-group">
                                        <label>Timezone</label>
                                        <select name="timezone" value={settings.timezone} onChange={handleChange} className="component-select">
                                            <option value="UTC">UTC</option>
                                            <option value="EST">EST</option>
                                        </select>
                                    </div>
                                </div>
                                <button className="btn-save" onClick={handleSave}>Save Preferences</button>
                            </div>
                        )}

                        {/* Reporting Prefs Tab */}
                        {activeTab === 'reporting' && (
                            <div className="settings-card">
                                <div className="settings-header">
                                    <h2 className="settings-title">Calculation & Reporting</h2>
                                    <p className="settings-subtitle">Set global defaults for calculation models and units.</p>
                                </div>

                                <div className="grid-forms">
                                    <div className="input-group">
                                        <label>GWP Assessment Model</label>
                                        <select name="gwpModel" className="input-field" value={settings.gwpModel} onChange={handleChange}>
                                            <option value="AR4">IPCC AR4 (2007)</option>
                                            <option value="AR5">IPCC AR5 (2013)</option>
                                            <option value="AR6">IPCC AR6 (2021)</option>
                                        </select>
                                    </div>
                                    <div className="input-group">
                                        <label>Inventory Consolidation Approach</label>
                                        <select name="consolidation" value={settings.consolidation} onChange={handleChange} className="component-select">
                                            <option value="Control">Operational Control</option>
                                            <option value="Financial">Financial Control</option>
                                            <option value="Equity">Equity Share</option>
                                        </select>
                                    </div>
                                </div>
                                <button className="btn-save" onClick={handleSave}>Save Preferences</button>
                            </div>
                        )}

                        {/* Notifications Tab */}
                        {activeTab === 'notifications' && (
                            <div className="settings-card">
                                <div className="settings-header">
                                    <h2 className="settings-title">Notification Settings</h2>
                                    <p className="settings-subtitle">Control how and when you receive alerts and reports.</p>
                                </div>

                                <div className="settings-group">
                                    <label className="checkbox-label">
                                        <input type="checkbox" name="notifWeekly" checked={settings.notifWeekly} onChange={handleChange} />
                                        Weekly Emissions Summary
                                    </label>
                                    <label className="checkbox-label">
                                        <input type="checkbox" name="notifTargets" checked={settings.notifTargets} onChange={handleChange} />
                                        Target Exceedance Alerts
                                    </label>
                                    <label className="checkbox-label">
                                        <input type="checkbox" name="notifAudit" checked={settings.notifAudit} onChange={handleChange} />
                                        New Audit Log Entry Notifications
                                    </label>
                                </div>
                                <button className="btn-save" onClick={handleSave}>Save Notifications</button>
                            </div>
                        )}

                        {/* Security Tab */}
                        {activeTab === 'security' && (
                            <div className="settings-card">
                                <div className="settings-header">
                                    <h2 className="settings-title">Security Settings</h2>
                                    <p className="settings-subtitle">Manage your password and account security.</p>
                                </div>

                                <div className="grid-forms">
                                    <div className="input-group">
                                        <label>Current Password</label>
                                        <input
                                            type="password"
                                            name="currentPassword"
                                            value={passwordData.currentPassword}
                                            onChange={handlePasswordChange}
                                            className="component-input"
                                            placeholder="Enter current password"
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>New Password</label>
                                        <input
                                            type="password"
                                            name="newPassword"
                                            value={passwordData.newPassword}
                                            onChange={handlePasswordChange}
                                            className="component-input"
                                            placeholder="Minimum 10 characters"
                                        />
                                    </div>
                                    <div className="input-group">
                                        <label>Confirm New Password</label>
                                        <input
                                            type="password"
                                            name="confirmPassword"
                                            value={passwordData.confirmPassword}
                                            onChange={handlePasswordChange}
                                            className="component-input"
                                            placeholder="Re-enter new password"
                                        />
                                    </div>
                                </div>
                                <button className="btn-save" onClick={handleSavePassword}>Change Password</button>
                            </div>
                        )}

                    </section>
                </div>
            </div>
        </div>
    );
};

export default Settings;
