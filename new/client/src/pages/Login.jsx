import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import './Login.css';

const Login = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const { login } = useAuth();
    const navigate = useNavigate();

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        try {
            await login(email, password);
            navigate('/');
        } catch (err) {
            setError(err.response?.data?.error || 'Invalid credentials');
        }
    };

    return (
        <div className="login-body">
            {/* Left Panel: Branding */}
            <div className="brand-panel">
                <div className="brand-content">
                    <h1 className="brand-title">GHG Reporting Platform</h1>
                    <p className="brand-subtitle">Oil & Gas | ISO 14064 | API | IPCC</p>
                    <p className="brand-description">
                        Automated, auditable greenhouse gas emissions reporting for regulated energy operations.
                    </p>

                    <div className="compliance-grid-login">
                        {/* EPA 98 */}
                        <div className="status-card">
                            <div className="status-header">
                                <div>
                                    <div className="score-large">100%</div>
                                    <div className="score-label">EPA Subparts A, C, W</div>
                                </div>
                                <div className="status-icon" style={{ background: 'rgba(255, 102, 0, 0.15)', color: '#ff6600' }}>
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                                    </svg>
                                </div>
                            </div>
                            <h3 className="card-title">EPA 40 CFR Part 98</h3>
                            <p className="card-sub">Ready for Reporting</p>
                        </div>

                        {/* ISO 14064 */}
                        <div className="status-card">
                            <div className="status-header">
                                <div>
                                    <div className="score-large">100%</div>
                                    <div className="score-label">GHG Inventory Framework</div>
                                </div>
                                <div className="status-icon" style={{ background: 'rgba(255, 102, 0, 0.15)', color: '#ff6600' }}>
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                                    </svg>
                                </div>
                            </div>
                            <h3 className="card-title">ISO 14064 Compliance</h3>
                            <p className="card-sub">Full Protocol Alignment</p>
                        </div>

                        {/* GHG Protocol */}
                        <div className="status-card">
                            <div className="status-header">
                                <div>
                                    <div className="score-large">100%</div>
                                    <div className="score-label">Scope 1 & 2 Tracking</div>
                                </div>
                                <div className="status-icon" style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd' }}>
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                        <circle cx="12" cy="12" r="10"></circle>
                                        <line x1="2" y1="12" x2="22" y2="12"></line>
                                        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                                    </svg>
                                </div>
                            </div>
                            <h3 className="card-title">GHG Protocol</h3>
                            <p className="card-sub" style={{ color: '#93c5fd' }}>Corporate Standard</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Panel: Login */}
            <div className="login-panel">

                {/* Login Form */}
                <div className="login-card fade-in" id="login-form-container">
                    <div className="login-header">
                        <h2>Sign in</h2>
                        <p>Access your emissions inventory</p>
                    </div>

                    {error && (
                        <div className="error-message">
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleLogin}>
                        <div className="form-group">
                            <div className="input-wrapper">
                                <span className="input-icon">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                                        <polyline points="22,6 12,13 2,6"></polyline>
                                    </svg>
                                </span>
                                <input
                                    type="text"
                                    className="form-control"
                                    required
                                    placeholder="Email Address"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    autoComplete="username"
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <div className="input-wrapper">
                                <span className="input-icon">
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                                    </svg>
                                </span>
                                <input
                                    type="password"
                                    className="form-control"
                                    required
                                    placeholder="Password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    autoComplete="current-password"
                                />
                            </div>
                        </div>

                        <button type="submit" className="btn-primary">Sign In</button>
                    </form>

                    <div className="form-footer" style={{ marginTop: '1.5rem', textAlign: 'center' }}>
                        <p style={{ color: '#6b7280', fontSize: '14px' }}>
                            Need an account? Please contact your IT administrator for access.
                        </p>
                    </div>
                </div>



                <div className="footer-compliance">
                    <p>Compliant with:</p>
                    <div className="mini-badges">
                        <div className="mini-badge">API</div>
                        <div className="mini-badge">ISO 14064</div>
                        <div className="mini-badge">GRI 305</div>
                    </div>
                    <p style={{ marginTop: '15px', fontSize: '0.75rem', opacity: '0.7' }}>All activity is logged for audit and verification purposes.</p>
                </div>
            </div>
        </div>
    );
};

export default Login;
